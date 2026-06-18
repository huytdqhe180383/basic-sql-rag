"""Helpers for stateful SQL attempts, review, and final answer composition."""

from __future__ import annotations

import json
from textwrap import dedent
from typing import Callable

from openai import OpenAI


MAX_SQL_ATTEMPTS = 3

SECTION_SYSTEM_PROMPT = dedent(
    """\
    You are Beacon, a careful PostgreSQL analytics assistant.
    Use the retrieved schema context only. Work within this single question session.
    Keep track of SQL attempts, execution feedback, and review feedback in this chat.
    Do not rely on memory from other users, questions, or sessions.
    """
).strip()


def call_llm(messages: list[dict], settings: dict) -> str:
    """Call the configured OpenAI-compatible chat model with message memory."""
    if not settings.get("openai_api_key") or not settings.get("model"):
        raise RuntimeError("Missing OpenAI settings.")
    client = OpenAI(
        api_key=settings["openai_api_key"],
        base_url=settings.get("openai_api_base"),
    )
    response = client.chat.completions.create(
        model=settings["model"],
        messages=messages,
        temperature=0,
        timeout=30,
    )
    return response.choices[0].message.content or ""


def create_section_messages(question: str, prompt: str) -> list[dict]:
    """Create in-request memory for one independent question section."""
    return [
        {"role": "system", "content": SECTION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Question:\n"
                f"{question}\n\n"
                "Retrieved schema and examples:\n"
                f"{prompt}\n\n"
                "We will generate SQL, inspect the result or error, and retry only if needed."
            ),
        },
    ]


def request_sql(
    messages: list[dict],
    settings: dict,
    attempt_number: int,
    chat: Callable[[list[dict], dict], str],
) -> str:
    """Ask the LLM for one SQL attempt while preserving message history."""
    messages.append(
        {
            "role": "user",
            "content": (
                f"SQL attempt {attempt_number} of {MAX_SQL_ATTEMPTS}: "
                "Return exactly one read-only PostgreSQL SELECT or WITH query. "
                "Return SQL only, no markdown."
            ),
        }
    )
    sql = chat(messages, settings)
    messages.append({"role": "assistant", "content": sql})
    return sql


def review_attempt(
    messages: list[dict],
    settings: dict,
    question: str,
    attempt: dict,
    result: dict | None,
    chat: Callable[[list[dict], dict], str],
) -> dict:
    """Ask the LLM whether the latest SQL attempt answered the question."""
    messages.append(
        {
            "role": "user",
            "content": (
                "Review the latest SQL attempt for the original question.\n"
                f"Question: {question}\n"
                f"Attempt status: {attempt['status']}\n"
                f"SQL: {attempt.get('sql')}\n"
                f"Error: {attempt.get('error')}\n"
                f"Result summary: {json.dumps(summarize_result(result), ensure_ascii=False)}\n\n"
                "Return strict JSON only with these keys: "
                'satisfied (boolean), reason (string), retry_instructions (string).'
            ),
        }
    )
    raw_review = chat(messages, settings)
    messages.append({"role": "assistant", "content": raw_review})
    review = parse_review(raw_review)
    if attempt["status"] != "completed":
        review["satisfied"] = False
    return review


def compose_final_answer(
    messages: list[dict],
    settings: dict,
    question: str,
    attempt: dict,
    result: dict | None,
    attempts: list[dict],
    chat: Callable[[list[dict], dict], str],
) -> str:
    """Ask the LLM to compose the final natural-language answer."""
    messages.append(
        {
            "role": "user",
            "content": (
                "Compose the final answer for the user in natural language.\n"
                f"Question: {question}\n"
                f"Final attempt status: {attempt['status']}\n"
                f"Final SQL: {attempt.get('sql')}\n"
                f"Final error: {attempt.get('error')}\n"
                f"Reviewer reason: {attempt.get('review_reason')}\n"
                f"Attempt count: {len(attempts)}\n"
                f"Result summary: {json.dumps(summarize_result(result), ensure_ascii=False)}\n\n"
                "If the SQL was accepted, answer directly from the result. "
                "If no accepted SQL exists, explain the failure plainly."
            ),
        }
    )
    answer = chat(messages, settings).strip()
    messages.append({"role": "assistant", "content": answer})
    return answer


def parse_review(raw_review: str) -> dict:
    """Parse reviewer JSON, failing closed when the response is malformed."""
    text = strip_json_fence(raw_review)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return invalid_review()
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return invalid_review()

    return {
        "satisfied": bool(data.get("satisfied")),
        "reason": str(data.get("reason") or ""),
        "retry_instructions": str(data.get("retry_instructions") or ""),
    }


def invalid_review() -> dict:
    """Return a retryable review when the reviewer did not return JSON."""
    return {
        "satisfied": False,
        "reason": "Reviewer response was not valid JSON.",
        "retry_instructions": "Return corrected SQL and keep the next review JSON-valid.",
    }


def strip_json_fence(text: str) -> str:
    """Strip optional markdown fences around a JSON response."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
    if stripped.endswith("```"):
        stripped = stripped.rsplit("```", 1)[0]
    return stripped.strip()


def summarize_result(result: dict | None, row_limit: int = 5) -> dict:
    """Return a compact JSON-friendly result sample for review prompts."""
    if not result:
        return {}
    rows = result.get("rows", [])[:row_limit]
    return {
        "columns": result.get("columns", []),
        "rows": [[stringify_value(value) for value in row] for row in rows],
        "shown_rows": len(rows),
        "total": result.get("total"),
    }


def stringify_value(value) -> str | None:
    """Convert database values to JSON-friendly prompt strings."""
    return None if value is None else str(value)


def public_attempt(attempt: dict) -> dict:
    """Return the compact attempt shape exposed in section debug output."""
    return {
        "sql": attempt.get("sql"),
        "status": attempt.get("status"),
        "error": attempt.get("error"),
        "review_reason": attempt.get("review_reason"),
        "satisfied": attempt.get("satisfied", False),
    }
