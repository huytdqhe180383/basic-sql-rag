"""Build retrieval documents and compact semantic profiles."""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding

from beacon.config import (
    FEW_SHOT_INDEX_DIR,
    FEW_SHOT_QUERIES_PATH,
    PROCESSED_DATA_DIR,
    SCHEMA_INDEX_DIR,
    SEMANTIC_MODEL_DIR,
)


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
    return [
        load_json(path)
        for path in sorted(model_dir.glob("*.json"))
    ]


def read_csv_rows(path: Path) -> list[dict[str, str | None]]:
    """Read a processed CSV as dictionaries with empty strings mapped to None."""
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            {key: (value if value != "" else None) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def profile_table_rows(rows: list[dict], columns: list[dict]) -> dict:
    """Return three sample rows and compact per-column value profiles."""
    return {
        "sample_rows": rows[:3],
        "columns": {
            column["name"]: profile_column(rows, column)
            for column in columns
        },
    }


def profile_column(rows: list[dict], column: dict) -> dict:
    """Summarize one column with nulls, distincts, samples, and compact stats."""
    name = column["name"]
    values = [row.get(name) for row in rows]
    present = [value for value in values if value not in (None, "")]
    profile = {
        "null_count": len(values) - len(present),
        "distinct_count": len(set(present)),
        "sample_values": first_unique_values(present, limit=5),
    }

    column_type = column.get("type", "").upper()
    lowered_name = name.lower()
    if "BOOL" in column_type:
        counts = Counter(str(value).lower() for value in present)
        profile["value_counts"] = dict(sorted(counts.items()))
    elif "DATE" in column_type:
        profile["min"] = min(present) if present else None
        profile["max"] = max(present) if present else None
    elif is_numeric_type(column_type):
        numbers = [float(value) for value in present if is_number(value)]
        if numbers:
            profile["min"] = round(min(numbers), 4)
            profile["max"] = round(max(numbers), 4)
            if "id" not in lowered_name and lowered_name not in {"zip", "year", "month"}:
                profile["mean"] = round(sum(numbers) / len(numbers), 4)
    else:
        counts = Counter(str(value) for value in present)
        profile["top_values"] = [
            {"value": value, "count": count}
            for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]
        ]
    return profile


def first_unique_values(values: list, limit: int) -> list:
    """Return the first unique non-null values as strings."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if text not in seen:
            seen.add(text)
            result.append(text)
        if len(result) >= limit:
            break
    return result


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


def build_example_docs(few_shot: list[dict]) -> list[dict]:
    """Convert few-shot examples into plain retrieval documents."""
    docs: list[dict] = []
    for example in few_shot:
        docs.append(
            {
                "text": (
                    f"Question: {example['question']}\n"
                    f"SQL: {example['sql']}\n"
                    f"Tables used: {', '.join(example['tables'])}\n"
                    f"Pattern: {example['pattern']}"
                ),
                "metadata": {
                    "pattern": example["pattern"],
                    "tables": example["tables"],
                    "question_families": example.get("question_families", []),
                },
            }
        )
    return docs


def persist_index(docs: list[dict], persist_dir: Path) -> None:
    """Persist one vector index from plain docs."""
    llama_docs = [Document(text=doc["text"], metadata=doc["metadata"]) for doc in docs]
    index = VectorStoreIndex.from_documents(llama_docs)
    index.storage_context.persist(str(persist_dir))


def main() -> None:
    """Build schema and example indices from semantic JSON artifacts."""
    load_dotenv(override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    Settings.embed_model = OpenAIEmbedding(
        api_key=api_key,
        api_base=os.getenv("OPENAI_API_BASE"),
        model="text-embedding-3-small",
    )
    semantic_model = enrich_semantic_model_files()
    persist_index(build_schema_docs(semantic_model), SCHEMA_INDEX_DIR)
    persist_index(build_example_docs(load_json(FEW_SHOT_QUERIES_PATH)), FEW_SHOT_INDEX_DIR)
    print("Built schema and few-shot indices.")
