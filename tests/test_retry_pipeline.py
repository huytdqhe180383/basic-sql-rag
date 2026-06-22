"""Tests for the stateful SQL retry loop."""

from __future__ import annotations

import pytest

from beacon import pipeline


def make_context(tables: set[str] | None = None) -> dict:
    """Return sufficient retrieval context for retry tests."""
    tables = tables or {"orders"}
    return {
        "question_needs": {
            "tables": tables,
            "columns": {"order_id"},
            "relations": set(),
            "example_patterns": set(),
        },
        "schema_coverage": {"is_sufficient": True, "missing": {}},
        "schema_docs": [
            {
                "text": "Table: orders\nColumns:\n  - order_id (INTEGER)",
                "metadata": {"table": "orders", "columns": ["order_id"]},
            }
        ],
        "example_docs": [],
    }


def test_answer_section_retries_after_sql_validation_error(monkeypatch):
    responses = iter(
        [
            "DELETE FROM orders",
            '{"satisfied": false, "reason": "Unsafe write SQL.", "retry_instructions": "Use SELECT only."}',
            "SELECT order_id FROM orders",
            '{"satisfied": true, "reason": "The result answers the question.", "retry_instructions": ""}',
            "There are 2 orders.",
        ]
    )

    monkeypatch.setattr(pipeline, "retrieve_context", lambda question: make_context())
    monkeypatch.setattr(pipeline, "call_llm", lambda messages, settings: next(responses), raising=False)
    monkeypatch.setattr(pipeline, "generate_sql", lambda prompt, settings: "DELETE FROM orders")
    monkeypatch.setattr(
        pipeline,
        "run_query",
        lambda sql, settings: {"columns": ["order_id"], "rows": [[1], [2]], "total": 2},
    )

    section = pipeline.answer_section("How many orders?", {"model": "test"})

    assert section["status"] == "completed"
    assert section["sql"] == "SELECT order_id FROM orders"
    assert section["answer"] == "There are 2 orders."
    assert section["attempt_count"] == 2
    assert section["attempts"][0]["status"] == "validation_error"
    assert section["attempts"][0]["satisfied"] is False


def test_answer_section_retries_when_reviewer_rejects_successful_result(monkeypatch):
    responses = iter(
        [
            "SELECT order_id FROM orders",
            '{"satisfied": false, "reason": "This lists orders instead of counting them.", "retry_instructions": "Return a count."}',
            "SELECT COUNT(*) AS order_count FROM orders",
            '{"satisfied": true, "reason": "This gives the requested count.", "retry_instructions": ""}',
            "There are 2 orders.",
        ]
    )
    executed_sql: list[str] = []

    def fake_run_query(sql, settings):
        executed_sql.append(sql)
        if "COUNT" in sql:
            return {"columns": ["order_count"], "rows": [[2]], "total": 1}
        return {"columns": ["order_id"], "rows": [[1], [2]], "total": 2}

    monkeypatch.setattr(pipeline, "retrieve_context", lambda question: make_context())
    monkeypatch.setattr(pipeline, "call_llm", lambda messages, settings: next(responses), raising=False)
    monkeypatch.setattr(pipeline, "generate_sql", lambda prompt, settings: "SELECT order_id FROM orders")
    monkeypatch.setattr(pipeline, "run_query", fake_run_query)

    section = pipeline.answer_section("How many orders?", {"model": "test"})

    assert section["status"] == "completed"
    assert section["sql"] == "SELECT COUNT(*) AS order_count FROM orders"
    assert section["attempt_count"] == 2
    assert executed_sql == ["SELECT order_id FROM orders", "SELECT COUNT(*) AS order_count FROM orders"]
    assert section["attempts"][0]["review_reason"] == "This lists orders instead of counting them."


def test_answer_section_feeds_execution_error_into_next_attempt(monkeypatch):
    responses = iter(
        [
            "SELECT missing_column FROM orders",
            '{"satisfied": false, "reason": "The SQL referenced a missing column.", "retry_instructions": "Use order_id."}',
            "SELECT order_id FROM orders",
            '{"satisfied": true, "reason": "The corrected SQL runs.", "retry_instructions": ""}',
            "The corrected query returned 2 orders.",
        ]
    )

    def fake_run_query(sql, settings):
        if "missing_column" in sql:
            raise RuntimeError("column missing_column does not exist")
        return {"columns": ["order_id"], "rows": [[1], [2]], "total": 2}

    monkeypatch.setattr(pipeline, "retrieve_context", lambda question: make_context())
    monkeypatch.setattr(pipeline, "call_llm", lambda messages, settings: next(responses), raising=False)
    monkeypatch.setattr(pipeline, "generate_sql", lambda prompt, settings: "SELECT missing_column FROM orders")
    monkeypatch.setattr(pipeline, "run_query", fake_run_query)

    section = pipeline.answer_section("List orders", {"model": "test"})

    assert section["status"] == "completed"
    assert section["attempts"][0]["status"] == "execution_error"
    assert "missing_column" in section["attempts"][0]["error"]
    assert section["sql"] == "SELECT order_id FROM orders"


def test_answer_section_returns_readable_failure_after_three_attempts(monkeypatch):
    responses = iter(
        [
            "DELETE FROM orders",
            '{"satisfied": false, "reason": "Unsafe SQL.", "retry_instructions": "Use SELECT."}',
            "UPDATE orders SET order_id = order_id",
            '{"satisfied": false, "reason": "Still unsafe.", "retry_instructions": "Use SELECT."}',
            "DROP TABLE orders",
            '{"satisfied": false, "reason": "Still unsafe.", "retry_instructions": "Use SELECT."}',
            "I could not produce a safe SQL query after 3 attempts.",
        ]
    )

    monkeypatch.setattr(pipeline, "retrieve_context", lambda question: make_context())
    monkeypatch.setattr(pipeline, "call_llm", lambda messages, settings: next(responses), raising=False)
    monkeypatch.setattr(pipeline, "generate_sql", lambda prompt, settings: "DELETE FROM orders")

    section = pipeline.answer_section("Delete orders?", {"model": "test"})

    assert section["status"] == "failed"
    assert section["answer"] == "I could not produce a safe SQL query after 3 attempts."
    assert section["attempt_count"] == 3
    assert section["error"] == "Still unsafe."


def test_answer_question_uses_separate_memory_per_section(monkeypatch):
    responses = iter(
        [
            "SELECT order_id FROM orders",
            '{"satisfied": true, "reason": "Answered.", "retry_instructions": ""}',
            "First answer.",
            "SELECT order_id FROM orders",
            '{"satisfied": true, "reason": "Answered.", "retry_instructions": ""}',
            "Second answer.",
        ]
    )
    message_refs: list[list[dict]] = []

    def fake_call_llm(messages, settings):
        message_refs.append(messages)
        return next(responses)

    monkeypatch.setattr(pipeline, "retrieve_context", lambda question: make_context())
    monkeypatch.setattr(pipeline, "call_llm", fake_call_llm, raising=False)
    monkeypatch.setattr(pipeline, "generate_sql", lambda prompt, settings: "SELECT order_id FROM orders")
    monkeypatch.setattr(
        pipeline,
        "run_query",
        lambda sql, settings: {"columns": ["order_id"], "rows": [[1]], "total": 1},
    )
    monkeypatch.setattr(pipeline, "load_settings", lambda: {"model": "test"})

    report = pipeline.answer_question("How many orders and show revenue")

    assert report["status"] == "completed"
    assert [section["answer"] for section in report["sections"]] == ["First answer.", "Second answer."]
    assert len({id(messages) for messages in message_refs}) == 2
    assert len(message_refs) == 6
