"""Ground user terms to semantic table, column, and value evidence."""

from __future__ import annotations

import re
import unicodedata

from beacon.retrieval_tools import required_relations


DEFAULT_VALUE_ALIASES = {
    ("orders", "order_status"): {
        "refunded": "returned",
        "refund": "returned",
        "returned": "returned",
        "canceled": "cancelled",
        "cancelled": "cancelled",
    },
    ("orders", "payment_method"): {
        "apple pay": "apple_pay",
        "cash on delivery": "cod",
    },
    ("customers", "gender"): {
        "guys": "male",
        "men": "male",
        "male customers": "male",
    },
    ("inventory", "overstock_flag"): {
        "overstock": True,
        "overstocked": True,
        "flagged as overstock": True,
    },
    ("inventory", "stockout_flag"): {
        "stockout": True,
        "stocked out": True,
        "ran out of stock": True,
        "out of stock": True,
    },
}


def ground_question_metadata(question: str, semantic_model: list[dict]) -> list[dict]:
    """Return matched metadata evidence for values mentioned in a question."""
    question_text = normalize_text(question)
    evidence: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()

    for table in semantic_model:
        table_name = table["source_table"]
        for column in table.get("columns", []):
            column_name = column["name"]
            for candidate in grounding_candidates(table_name, column):
                term = candidate["term"]
                if not term or not phrase_matches(question_text, term):
                    continue
                key = (term, table_name, column_name, str(candidate["value"]))
                if key in seen:
                    continue
                seen.add(key)
                evidence.append(
                    {
                        "term": term,
                        "table": table_name,
                        "column": column_name,
                        "value": candidate["value"],
                        "value_sql": sql_literal(candidate["value"]),
                        "source": candidate["source"],
                        "score": candidate["score"],
                    }
                )

    return evidence


def apply_grounding_to_needs(needs: dict, evidence: list[dict]) -> dict:
    """Expand inferred question needs with grounded tables and columns."""
    grounded = {
        "tables": set(needs.get("tables", set())),
        "columns": set(needs.get("columns", set())),
        "example_patterns": set(needs.get("example_patterns", set())),
    }
    for item in evidence:
        grounded["tables"].add(item["table"])
        grounded["columns"].add(item["column"])
    grounded["relations"] = required_relations(grounded["tables"])
    return grounded


def format_matched_evidence(evidence: list[dict]) -> str:
    """Format matched value evidence for the SQL prompt."""
    if not evidence:
        return ""
    lines = ["MATCHED EVIDENCE:"]
    for item in sorted(evidence, key=evidence_sort_key):
        lines.append(
            f"- \"{item['term']}\" -> "
            f"{item['table']}.{item['column']} = {item['value_sql']}"
        )
    return "\n".join(lines)


def grounding_candidates(table_name: str, column: dict) -> list[dict]:
    """Collect profile values and manual aliases for one semantic column."""
    candidates: list[dict] = []
    profile = column.get("profile", {})
    column_type = column.get("type", "").upper()

    if "TEXT" in column_type:
        for value in profile.get("sample_values", []):
            add_candidate(candidates, value, value, "profile", 80)
        for item in profile.get("top_values", []):
            add_candidate(candidates, item.get("value"), item.get("value"), "profile", 90)

    aliases = column.get("grounding", {}).get("value_aliases", {})
    aliases = {
        **DEFAULT_VALUE_ALIASES.get((table_name, column["name"]), {}),
        **aliases,
    }
    for alias, value in aliases.items():
        add_candidate(candidates, alias, value, "alias", 100)

    return candidates


def add_candidate(
    candidates: list[dict],
    term_value,
    exact_value,
    source: str,
    score: int,
) -> None:
    """Append one normalized candidate when it has a usable term."""
    if term_value is None:
        return
    term = normalize_text(str(term_value))
    if not term:
        return
    candidates.append(
        {
            "term": term,
            "value": exact_value,
            "source": source,
            "score": score,
        }
    )


def normalize_text(value: str) -> str:
    """Normalize text for robust metadata phrase matching."""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = ascii_text.lower().replace("_", " ").replace("-", " ")
    cleaned = re.sub(r"[^a-z0-9+#]+", " ", lowered)
    return " ".join(cleaned.split())


def phrase_matches(question_text: str, term: str) -> bool:
    """Return whether a normalized term appears as a phrase in a question."""
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", question_text))


def sql_literal(value) -> str:
    """Format one grounded value as a SQL literal hint."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def evidence_sort_key(item: dict) -> tuple:
    """Keep prompt evidence deterministic and easy to scan."""
    return (-int(item.get("score", 0)), item["table"], item["column"], item["term"])
