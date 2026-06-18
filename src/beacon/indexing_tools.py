"""Helpers for semantic profiling and retrieval document construction."""

from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter
from pathlib import Path

from beacon.config import PROCESSED_DATA_DIR, SEMANTIC_MODEL_DIR


SIGNAL_RULES = {
    "metrics": [
        ("revenue", {"revenue", "sales"}),
        ("cogs", {"cogs", "cost of goods"}),
        ("count", {"count(", "how many", "num_customers", "order_count"}),
        ("average", {"avg(", "average", "avg_"}),
        ("quantity", {"quantity sold", "total_quantity", "quantity"}),
        ("discount", {"discount", "discount_amount"}),
        ("fill_rate", {"fill rate", "fill_rate"}),
        ("sell_through_rate", {"sell-through", "sell through", "sell_through"}),
        ("stock_on_hand", {"stock", "stock_on_hand"}),
    ],
    "filters": [
        (
            "date_filter",
            {"where", "current_date", "date_trunc", "2025-", "last month", "last quarter", "current year"},
        ),
        ("device_filter", {"device_type", "mobile"}),
        ("customer_filter", {"customer_id =", "customer 12345"}),
        ("promo_filter", {"promo_id"}),
        ("reorder_filter", {"reorder_flag"}),
        ("status_filter", {"order_status"}),
        ("payment_filter", {"payment_method"}),
    ],
    "time_grain": [
        ("day", {"daily", " by day", " date,"}),
        ("month", {" by month", " month"}),
        ("quarter", {"quarter"}),
        ("year", {" current year", " 2025", " year"}),
        ("rolling_window", {"last week", "last 30 days"}),
    ],
}

SQL_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
SQL_WORDS = {
    "as",
    "and",
    "asc",
    "avg",
    "by",
    "case",
    "count",
    "current_date",
    "date_trunc",
    "desc",
    "distinct",
    "false",
    "from",
    "group",
    "in",
    "interval",
    "is",
    "join",
    "limit",
    "max",
    "min",
    "not",
    "null",
    "on",
    "or",
    "order",
    "select",
    "sum",
    "then",
    "true",
    "where",
}


def load_json(path: str | os.PathLike[str]):
    """Load JSON from disk."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: str | os.PathLike[str], value) -> None:
    """Write pretty JSON to disk."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_semantic_model(model_dir: Path = SEMANTIC_MODEL_DIR) -> list[dict]:
    """Load one semantic table definition per JSON file."""
    return [load_json(path) for path in sorted(model_dir.glob("*.json"))]


def profile_table_rows(rows: list[dict], columns: list[dict]) -> dict:
    """Return three sample rows and compact per-column value profiles."""
    state = {column["name"]: new_profile_state(column) for column in columns}
    sample_rows = [
        {key: (value if value != "" else None) for key, value in row.items()}
        for row in rows[:3]
    ]
    for row in rows:
        normalized = {key: (value if value != "" else None) for key, value in row.items()}
        for column in columns:
            update_profile_state(state[column["name"]], normalized.get(column["name"]))

    return {
        "sample_rows": sample_rows,
        "columns": {
            column["name"]: finish_profile_state(state[column["name"]])
            for column in columns
        },
    }


def is_numeric_type(column_type: str) -> bool:
    """Return whether a semantic type should be treated as numeric."""
    return any(token in column_type for token in ("INT", "NUMERIC", "FLOAT", "DOUBLE", "DECIMAL"))


def is_number(value) -> bool:
    """Return whether a value can be converted to float."""
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def enrich_semantic_model(model: list[dict], data_dir: Path = PROCESSED_DATA_DIR) -> list[dict]:
    """Add sample rows and compact column profiles to semantic model entries."""
    enriched: list[dict] = []
    for table in model:
        entry = dict(table)
        profile = profile_csv_file(data_dir / f"{entry['source_table']}.csv", entry["columns"])
        entry["sample_rows"] = profile["sample_rows"]
        entry["columns"] = [
            {**column, "profile": profile["columns"][column["name"]]}
            for column in entry["columns"]
        ]
        enriched.append(entry)
    return enriched


def enrich_semantic_model_files(
    model_dir: Path = SEMANTIC_MODEL_DIR,
    data_dir: Path = PROCESSED_DATA_DIR,
) -> list[dict]:
    """Enrich per-table semantic JSON files in place and return the model."""
    model = load_semantic_model(model_dir)
    enriched = enrich_semantic_model(model, data_dir)
    for table in enriched:
        save_json(model_dir / f"{table['source_table']}.json", table)
    return enriched


def profile_csv_file(path: Path, columns: list[dict]) -> dict:
    """Profile a CSV without loading the whole file into memory."""
    state = {column["name"]: new_profile_state(column) for column in columns}
    sample_rows: list[dict] = []

    with path.open(encoding="utf-8", newline="") as handle:
        for raw_row in csv.DictReader(handle):
            row = {
                key: (value if value != "" else None)
                for key, value in raw_row.items()
            }
            if len(sample_rows) < 3:
                sample_rows.append(row)
            for column in columns:
                update_profile_state(state[column["name"]], row.get(column["name"]))

    return {
        "sample_rows": sample_rows,
        "columns": {
            column["name"]: finish_profile_state(state[column["name"]])
            for column in columns
        },
    }


def new_profile_state(column: dict) -> dict:
    """Create mutable streaming profile state for one column."""
    column_type = column.get("type", "").upper()
    return {
        "name": column["name"],
        "type": column_type,
        "total": 0,
        "null_count": 0,
        "distinct_values": set(),
        "sample_values": [],
        "counts": Counter(),
        "numeric_values": [],
        "date_min": None,
        "date_max": None,
    }


def update_profile_state(state: dict, value) -> None:
    """Update streaming profile state with one value."""
    state["total"] += 1
    if value in (None, ""):
        state["null_count"] += 1
        return

    text = str(value)
    state["distinct_values"].add(text)
    if text not in state["sample_values"] and len(state["sample_values"]) < 5:
        state["sample_values"].append(text)

    column_type = state["type"]
    if "DATE" in column_type:
        state["date_min"] = text if state["date_min"] is None else min(state["date_min"], text)
        state["date_max"] = text if state["date_max"] is None else max(state["date_max"], text)
    elif is_numeric_type(column_type) and is_number(value):
        state["numeric_values"].append(float(value))
    elif "BOOL" in column_type:
        state["counts"][text.lower()] += 1
    else:
        state["counts"][text] += 1


def finish_profile_state(state: dict) -> dict:
    """Convert mutable profile state into the compact JSON shape."""
    profile = {
        "null_count": state["null_count"],
        "distinct_count": len(state["distinct_values"]),
        "sample_values": state["sample_values"],
    }
    column_type = state["type"]
    lowered_name = state["name"].lower()
    if "DATE" in column_type:
        profile["min"] = state["date_min"]
        profile["max"] = state["date_max"]
    elif is_numeric_type(column_type):
        numbers = state["numeric_values"]
        if numbers:
            profile["min"] = round(min(numbers), 4)
            profile["max"] = round(max(numbers), 4)
            if "id" not in lowered_name and lowered_name not in {"zip", "year", "month"}:
                profile["mean"] = round(sum(numbers) / len(numbers), 4)
    elif "BOOL" in column_type:
        profile["value_counts"] = dict(sorted(state["counts"].items()))
    else:
        profile["top_values"] = [
            {"value": value, "count": count}
            for value, count in sorted(
                state["counts"].items(),
                key=lambda item: (-item[1], item[0]),
            )[:5]
        ]
    return profile


def build_schema_docs(semantic_model: list[dict]) -> list[dict]:
    """Convert semantic model entries into plain retrieval documents."""
    docs: list[dict] = []
    for entry in semantic_model:
        lines = [
            f"Table: {entry['source_table']}",
            f"Name: {entry['semantic_name']}",
            f"Grain: {entry['grain']}",
            f"Description: {entry['description']}",
            "",
            "Columns:",
        ]
        for column in entry["columns"]:
            lines.append(format_column(column))
        if entry.get("relations"):
            lines.append("")
            lines.append("Relations:")
            for relation in entry["relations"]:
                lines.append(f"  - {relation['from']} -> {relation['to']}")
        if entry.get("sample_rows"):
            lines.append("")
            lines.append("Sample rows:")
            for row in entry["sample_rows"]:
                lines.append("  - " + ", ".join(f"{key}={value}" for key, value in row.items()))
        docs.append(
            {
                "text": "\n".join(lines),
                "metadata": {
                    "table": entry["source_table"],
                    "columns": [column["name"] for column in entry["columns"]],
                    "relations": [
                        f"{relation['from']} -> {relation['to']}"
                        for relation in entry.get("relations", [])
                    ],
                    "question_families": entry.get("question_families", []),
                },
            }
        )
    return docs


def format_column(column: dict) -> str:
    """Format one semantic column with its compact profile."""
    profile = column.get("profile", {})
    parts = [
        f"nulls={profile.get('null_count', 0)}",
        f"distinct={profile.get('distinct_count', 0)}",
    ]
    if "min" in profile:
        parts.append(f"min={profile['min']}")
    if "max" in profile:
        parts.append(f"max={profile['max']}")
    if "mean" in profile:
        parts.append(f"mean={profile['mean']}")
    if profile.get("top_values"):
        top_values = ", ".join(
            f"{item['value']}:{item['count']}" for item in profile["top_values"]
        )
        parts.append(f"top_values={top_values}")
    if profile.get("value_counts"):
        counts = ", ".join(
            f"{value}:{count}" for value, count in profile["value_counts"].items()
        )
        parts.append(f"value_counts={counts}")
    if profile.get("sample_values"):
        parts.append("samples=" + ", ".join(map(str, profile["sample_values"])))
    return (
        f"  - {column['name']} ({column['type']}): {column['description']} | "
        + "; ".join(parts)
    )


def build_example_docs(few_shot: list[dict], semantic_model: list[dict] | None = None) -> list[dict]:
    """Convert few-shot examples into plain retrieval documents."""
    known_columns = collect_column_names(semantic_model or [])
    docs: list[dict] = []
    for example in few_shot:
        signals = extract_example_signals(example, known_columns)
        lines = [
            f"Question: {example['question']}",
            f"SQL: {example['sql']}",
            f"Tables used: {', '.join(example['tables'])}",
            f"Pattern: {example['pattern']}",
        ]
        if signals["columns"]:
            lines.append("Important columns: " + ", ".join(signals["columns"]))
        if signals["metrics"]:
            lines.append("Metrics: " + ", ".join(signals["metrics"]))
        if signals["filters"]:
            lines.append("Filters: " + ", ".join(signals["filters"]))
        if signals["time_grain"]:
            lines.append(f"Time grain: {signals['time_grain']}")
        if example.get("question_families"):
            lines.append("Question families: " + ", ".join(example["question_families"]))
        docs.append(
            {
                "text": "\n".join(lines),
                "metadata": {
                    "pattern": example["pattern"],
                    "tables": example["tables"],
                    "question_families": example.get("question_families", []),
                    **signals,
                },
            }
        )
    return docs


def collect_column_names(semantic_model: list[dict]) -> set[str]:
    """Return all semantic column names, preserving their source spelling."""
    return {
        column["name"]
        for table in semantic_model
        for column in table.get("columns", [])
    }


def extract_example_signals(example: dict, known_columns: set[str] | None = None) -> dict:
    """Extract compact, JSON-friendly signals from one few-shot example."""
    text = f"{example.get('question', '')} {example.get('sql', '')}".lower()
    columns = sorted(example.get("columns") or infer_example_columns(example, known_columns or set()))
    metrics = matching_signal_labels(text, SIGNAL_RULES["metrics"])
    filters = matching_signal_labels(text, SIGNAL_RULES["filters"])
    return {
        "columns": columns,
        "metrics": metrics,
        "filters": filters,
        "time_grain": first_matching_signal(text, SIGNAL_RULES["time_grain"]),
    }


def infer_example_columns(example: dict, known_columns: set[str]) -> set[str]:
    """Infer important columns from SQL using known semantic names when available."""
    sql = example.get("sql", "")
    text = f"{example.get('question', '')} {sql}".lower()
    if known_columns:
        return {
            column
            for column in known_columns
            if re.search(rf"(?<!\w){re.escape(column.lower())}(?!\w)", text)
        }

    identifiers = {match.group(0) for match in SQL_IDENTIFIER_RE.finditer(sql)}
    return {
        identifier
        for identifier in identifiers
        if identifier.lower() not in SQL_WORDS and len(identifier) > 1
    }


def matching_signal_labels(text: str, rules: list[tuple[str, set[str]]]) -> list[str]:
    """Return labels whose phrases appear in the example text."""
    return [
        label
        for label, phrases in rules
        if any(phrase in text for phrase in phrases)
    ]


def first_matching_signal(text: str, rules: list[tuple[str, set[str]]]) -> str | None:
    """Return the first matching signal label, or None when no rule fires."""
    for label, phrases in rules:
        if any(phrase in text for phrase in phrases):
            return label
    return None
