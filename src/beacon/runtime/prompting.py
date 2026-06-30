"""Prompt assembly for SQL generation."""

from __future__ import annotations

from beacon.linking.metadata_grounding import format_matched_evidence


def build_sql_prompt(question: str, context: dict) -> str:
    """Build the SQL-generation prompt from linked retrieval context."""
    sections = [
        "\n".join(
            [
                "SQL RULES:",
                "- Use only the tables and columns shown below.",
                "- Use column names exactly as shown in the schema context.",
                "- Do not quote column names unless the schema text itself shows quotes.",
                "- Use one read-only PostgreSQL SELECT or WITH query.",
            ]
        )
    ]
    evidence = context.get("evidence", context.get("matched_evidence", []))
    evidence_text = format_matched_evidence(evidence)
    if evidence_text:
        sections.append(evidence_text)
    if context.get("join_paths"):
        sections.append(
            "JOIN PATHS:\n" + "\n".join(f"- {path}" for path in context["join_paths"])
        )
    sections.append("RELEVANT SCHEMA:")
    sections.extend(doc["text"] for doc in context.get("schema_docs", []))
    if context.get("example_docs"):
        sections.append("EXAMPLE QUERIES:")
        sections.extend(format_example_doc(doc) for doc in context["example_docs"])
    sections.extend([f"QUESTION: {question}", "SQL:"])
    return "\n\n---\n\n".join(sections)


def format_example_doc(doc: dict) -> str:
    """Return prompt text for an example document or raw example dict."""
    if doc.get("text"):
        return doc["text"]
    return f"Question: {doc.get('question')}\nSQL: {doc.get('sql')}"
