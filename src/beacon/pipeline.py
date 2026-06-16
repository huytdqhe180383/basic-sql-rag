"""Core Beacon NL-to-SQL pipeline."""

from __future__ import annotations

import re
import sys
from textwrap import dedent

from openai import OpenAI

from beacon.config import load_settings
from beacon.retrieval import build_prompt, retrieve_context
from beacon.sql import SqlValidationError, clean_sql, format_results, run_query, validate_sql


SQL_SYSTEM_PROMPT = dedent(
    """\
    You are a PostgreSQL expert. Return exactly one read-only SQL query.
    Use only the schema in the prompt. Return SQL only, no markdown.
    """
).strip()


def split_questions(question: str) -> list[str]:
    """Split obviously independent requests while keeping dependent reasoning together."""
    normalized = " ".join(question.split())
    lowered = normalized.lower()
    dependent_words = {"subtract", "difference", "compare", "versus", " vs ", "second", "2nd"}
    if any(word in lowered for word in dependent_words):
        return [normalized]

    parts = re.split(r"\s+and\s+(?=(?:show|list|what|which|how|give|find)\b)", normalized, flags=re.IGNORECASE)
    return [part.strip(" .?") for part in parts if part.strip(" .?")] or [normalized]


def generate_sql(prompt: str, settings: dict) -> str:
    """Call the configured OpenAI-compatible model to produce SQL."""
    if not settings.get("openai_api_key") or not settings.get("model"):
        raise RuntimeError("Missing OpenAI settings.")
    client = OpenAI(
        api_key=settings["openai_api_key"],
        base_url=settings.get("openai_api_base"),
    )
    response = client.chat.completions.create(
        model=settings["model"],
        messages=[
            {"role": "system", "content": SQL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        timeout=30,
    )
    return response.choices[0].message.content or ""


def answer_question(question: str) -> dict:
    """Answer a natural-language analytics question with SQL-backed sections."""
    normalized = question.strip()
    if not normalized:
        return {"status": "failed", "question": question, "message": "Please enter a question.", "sections": []}

    settings = load_settings()
    sections: list[dict] = []
    for part in split_questions(normalized):
        sections.append(answer_section(part, settings))

    statuses = {section["status"] for section in sections}
    status = "completed" if statuses == {"completed"} else "partial" if "completed" in statuses else "failed"
    return {"status": status, "question": normalized, "sections": sections}


def answer_section(question: str, settings: dict) -> dict:
    """Run retrieval, prompting, SQL validation, execution, and formatting."""
    context = retrieve_context(question)
    needs = context["question_needs"]
    if not needs["tables"]:
        return {
            "title": question,
            "status": "failed",
            "answer": "I could not map this question to the known schema.",
            "sql": None,
            "error": "No relevant tables found.",
        }
    if not context["schema_coverage"]["is_sufficient"]:
        return {
            "title": question,
            "status": "failed",
            "answer": "Retrieved schema context was incomplete.",
            "sql": None,
            "error": str(context["schema_coverage"]["missing"]),
        }

    prompt = build_prompt(question, context)
    try:
        sql = validate_sql(clean_sql(generate_sql(prompt, settings)), needs["tables"])
        result = run_query(sql, settings)
    except (RuntimeError, SqlValidationError, Exception) as exc:
        return {
            "title": question,
            "status": "failed",
            "answer": "SQL generation or execution failed.",
            "sql": locals().get("sql"),
            "error": str(exc),
        }

    return {
        "title": question,
        "status": "completed",
        "answer": format_results(result["columns"], result["rows"], result.get("total")),
        "sql": sql,
        "error": None,
    }


def ask_database(question: str) -> tuple[str, str | None]:
    """Return the original UI-friendly `(answer, sql)` tuple."""
    report = answer_question(question)
    answer_parts = []
    sql_parts = []
    for section in report["sections"]:
        answer_parts.append(f"[{section['title']}]\n{section['answer']}")
        if section.get("sql"):
            sql_parts.append(section["sql"])
    return "\n\n".join(answer_parts), "\n\n---\n\n".join(sql_parts) or None


def main() -> None:
    """CLI entry point."""
    question = " ".join(sys.argv[1:]).strip() or input("Enter your question: ").strip()
    answer, _sql = ask_database(question)
    print(answer)


if __name__ == "__main__":
    main()
