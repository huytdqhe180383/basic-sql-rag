"""Core Beacon NL-to-SQL pipeline."""

from __future__ import annotations

import os
import re
import sys
from textwrap import dedent

from beacon.config import FEEDBACK_EXAMPLES_PATH, load_settings
from beacon.feedback_examples import candidate_from_attempt, save_candidate_example
from beacon.pipeline_tools import (
    MAX_SQL_ATTEMPTS,
    call_llm,
    compose_final_answer,
    create_section_messages,
    public_attempt,
    request_sql,
    review_attempt,
)
from beacon.retrieval import build_prompt, retrieve_context
from beacon.retry import classify_retry_need, format_retry_context_update, repair_linked_context
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
    dependent_words = {
        "subtract",
        "difference",
        "compare",
        "versus",
        " vs ",
        "second",
        "2nd",
        "that period",
        "those",
        "these",
        "they",
        "them",
        "their",
        "specific buyers",
        "corresponding",
    }
    if any(word in lowered for word in dependent_words):
        return [normalized]

    parts = re.split(r"\s+and\s+(?=(?:show|list|what|which|how|give|find)\b)", normalized, flags=re.IGNORECASE)
    return [part.strip(" .?") for part in parts if part.strip(" .?")] or [normalized]


def generate_sql(prompt: str, settings: dict) -> str:
    """Call the configured OpenAI-compatible model to produce SQL."""
    messages = [
        {"role": "system", "content": SQL_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    return call_llm(messages, settings)


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
    messages = create_section_messages(question, prompt)
    attempts: list[dict] = []
    last_attempt: dict | None = None
    last_result: dict | None = None

    for attempt_number in range(1, MAX_SQL_ATTEMPTS + 1):
        attempt, result = run_sql_attempt(question, settings, needs, messages, attempt_number)
        attempts.append(public_attempt(attempt))
        last_attempt = attempt
        last_result = result
        if attempt["satisfied"]:
            maybe_save_feedback_example(question, attempt, result, context)
            answer, answer_error = safe_compose_final_answer(
                messages,
                settings,
                question,
                attempt,
                result,
                attempts,
            )
            return {
                "title": question,
                "status": "completed",
                "answer": answer,
                "sql": attempt.get("sql"),
                "error": answer_error,
                "attempt_count": len(attempts),
                "attempts": attempts,
            }
        if attempt_number < MAX_SQL_ATTEMPTS:
            apply_retry_repair(context, needs, messages, attempt)

    answer, answer_error = safe_compose_final_answer(
        messages,
        settings,
        question,
        last_attempt or {},
        last_result,
        attempts,
    )
    error = final_attempt_error(last_attempt) or answer_error

    return {
        "title": question,
        "status": "failed",
        "answer": answer,
        "sql": (last_attempt or {}).get("sql"),
        "error": error,
        "attempt_count": len(attempts),
        "attempts": attempts,
    }


def run_sql_attempt(
    question: str,
    settings: dict,
    needs: dict,
    messages: list[dict],
    attempt_number: int,
) -> tuple[dict, dict | None]:
    """Generate, validate, execute, and review one SQL attempt."""
    raw_sql = request_sql(messages, settings, attempt_number, call_llm)
    attempt = {
        "sql": clean_sql(raw_sql),
        "status": "generated",
        "error": None,
        "review_reason": None,
        "satisfied": False,
    }
    result = None

    try:
        attempt["sql"] = validate_sql(attempt["sql"], needs["tables"])
        result = run_query(attempt["sql"], settings)
        attempt["status"] = "completed"
    except SqlValidationError as exc:
        attempt["status"] = "validation_error"
        attempt["error"] = str(exc)
    except Exception as exc:
        attempt["status"] = "execution_error"
        attempt["error"] = str(exc)

    review = review_attempt(messages, settings, question, attempt, result, call_llm)
    attempt["review_reason"] = review["reason"]
    attempt["satisfied"] = review["satisfied"]
    return attempt, result


def apply_retry_repair(
    context: dict,
    needs: dict,
    messages: list[dict],
    attempt: dict,
) -> None:
    """Update retry messages and linked context when repair evidence is available."""
    semantic_model = context.get("semantic_model", [])
    known_schema = {
        "tables": {table.get("source_table") for table in semantic_model if table.get("source_table")},
        "selected_tables": set(needs.get("tables", set())),
    }
    decision = classify_retry_need(attempt, known_schema)
    if decision["action"] == "retrieval_repair" and semantic_model and context.get("linked_context"):
        repaired = repair_linked_context(context["linked_context"], decision, semantic_model)
        context["linked_context"] = repaired
        context["schema_docs"] = repaired["schema_docs"]
        context["join_paths"] = repaired["join_paths"]
        context["schema_coverage"] = repaired["coverage"]
        needs["tables"] = set(repaired["selected_tables"])
        needs["columns"] = {item["column"] for item in repaired.get("selected_columns", [])}
        needs["relations"] = set(repaired.get("join_paths", []))
        messages.append(
            {
                "role": "user",
                "content": format_retry_context_update(repaired, decision),
            }
        )
    elif decision["action"] == "value_repair":
        messages.append(
            {
                "role": "user",
                "content": format_retry_context_update(context.get("linked_context", {}), decision),
            }
        )


def maybe_save_feedback_example(
    question: str,
    attempt: dict,
    result: dict | None,
    context: dict,
) -> None:
    """Optionally save accepted SQL as a future example candidate."""
    if os.getenv("BEACON_SAVE_EXAMPLE_CANDIDATES") != "1":
        return
    linked_context = context.get("linked_context")
    if not linked_context:
        return
    candidate = candidate_from_attempt(question, attempt, result, linked_context)
    save_candidate_example(FEEDBACK_EXAMPLES_PATH, candidate)


def safe_compose_final_answer(
    messages: list[dict],
    settings: dict,
    question: str,
    attempt: dict,
    result: dict | None,
    attempts: list[dict],
) -> tuple[str, str | None]:
    """Compose a final answer, falling back if the LLM answer call fails."""
    try:
        answer = compose_final_answer(messages, settings, question, attempt, result, attempts, call_llm)
        return answer, None
    except Exception as exc:
        if result and attempt.get("status") == "completed":
            return format_results(result["columns"], result["rows"], result.get("total")), str(exc)
        return "SQL generation or execution failed.", str(exc)


def final_attempt_error(attempt: dict | None) -> str | None:
    """Return the clearest final failure reason for a section."""
    if not attempt:
        return None
    return attempt.get("review_reason") or attempt.get("error")


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
