"""Retry policy for SQL, retrieval, and value repair."""

from __future__ import annotations

import re

from beacon.indexing_tools import build_schema_docs
from beacon.schema_graph import build_schema_graph, relation_paths


def classify_retry_need(attempt: dict, known_schema: dict) -> dict:
    """Classify whether the next attempt needs SQL, retrieval, or value repair."""
    error = attempt.get("error") or ""
    review = attempt.get("review_reason") or ""
    outside = re.search(r"outside (?:retrieved )?context:\s*([A-Za-z0-9_, ]+)\.?", error)
    if outside:
        requested = [item.strip().strip(".") for item in outside.group(1).split(",") if item.strip()]
        known = set(known_schema.get("tables", set()))
        missing_known = [table for table in requested if table in known]
        if missing_known:
            return {
                "action": "retrieval_repair",
                "reason": error,
                "requested_tables": missing_known,
                "requested_columns": [],
                "value_terms": [],
            }

    if "no rows" in review.lower() or "empty" in review.lower():
        values = re.findall(r"=\s*'([^']+)'", attempt.get("sql") or "")
        if values:
            return {
                "action": "value_repair",
                "reason": review,
                "requested_tables": [],
                "requested_columns": [],
                "value_terms": values,
            }

    if attempt.get("status") in {"validation_error", "execution_error"}:
        return {
            "action": "sql_retry",
            "reason": error or review,
            "requested_tables": [],
            "requested_columns": [],
            "value_terms": [],
        }

    return {
        "action": "sql_retry",
        "reason": review,
        "requested_tables": [],
        "requested_columns": [],
        "value_terms": [],
    }


def repair_linked_context(context: dict, decision: dict, semantic_model: list[dict]) -> dict:
    """Return linked context with requested known tables and join paths added."""
    if decision.get("action") != "retrieval_repair":
        return context

    selected_tables = set(context.get("selected_tables", []))
    selected_tables.update(decision.get("requested_tables", []))
    graph = build_schema_graph(semantic_model)
    joins = relation_paths(graph, selected_tables, max_hops=3)
    for relation in joins:
        for side in relation.split(" -> "):
            if "." in side:
                selected_tables.add(side.split(".", 1)[0])
    requested = set(decision.get("requested_tables", []))
    schema_docs = [
        doc
        for doc in build_schema_docs(semantic_model)
        if doc.get("metadata", {}).get("table") in selected_tables
    ]
    schema_docs = sorted(
        schema_docs,
        key=lambda doc: (doc.get("metadata", {}).get("table") not in requested, doc.get("metadata", {}).get("table", "")),
    )
    repaired = dict(context)
    repaired["selected_tables"] = sorted(selected_tables)
    repaired["join_paths"] = joins
    repaired["schema_docs"] = schema_docs
    repaired["coverage"] = {
        **context.get("coverage", {}),
        "is_sufficient": bool(selected_tables),
        "confidence": context.get("coverage", {}).get("confidence", "medium"),
        "warnings": context.get("coverage", {}).get("warnings", [])
        + ["retrieval repair added requested schema"],
    }
    return repaired


def format_retry_context_update(context: dict, decision: dict) -> str:
    """Format repaired retrieval context for the next SQL attempt."""
    if decision.get("action") == "value_repair":
        values = ", ".join(decision.get("value_terms", []))
        return (
            "Value repair note: the last SQL may have used an imprecise literal. "
            f"Reconsider exact database value spelling for: {values}."
        )

    lines = ["Retrieval repair updated the available schema context."]
    if decision.get("requested_tables"):
        lines.append("Added tables: " + ", ".join(decision["requested_tables"]))
    if context.get("join_paths"):
        lines.append("Join paths:")
        lines.extend(f"- {path}" for path in context["join_paths"])
    if context.get("schema_docs"):
        lines.append("Additional schema:")
        lines.extend(doc["text"] for doc in context["schema_docs"])
    return "\n".join(lines)
