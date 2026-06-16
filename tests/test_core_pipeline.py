"""Core tests for the simplified Beacon pipeline."""

import pytest

from beacon import pipeline
from beacon.retrieval import assess_coverage, build_prompt, extract_question_needs
from beacon.sql import SqlValidationError, validate_sql


def test_question_understanding_selects_relevant_schema_needs():
    signup = extract_question_needs("How many customers signed up in 2025?")
    assert signup["tables"] == {"customers"}
    assert "signup_date" in signup["columns"]

    revenue = extract_question_needs("What is total revenue by product category?")
    assert {"orders", "order_items", "products"}.issubset(revenue["tables"])
    assert {"quantity", "unit_price", "discount_amount", "category"}.issubset(
        revenue["columns"]
    )

    daily = extract_question_needs("What was daily Revenue and COGS last week?")
    assert daily["tables"] == {"sales"}

    inventory = extract_question_needs("Show fill rate by month")
    assert inventory["tables"] == {"inventory"}
    assert {"fill_rate", "month"}.issubset(inventory["columns"])


def test_coverage_reports_missing_schema_parts():
    needs = {
        "tables": {"orders", "order_items"},
        "columns": {"order_id", "quantity"},
        "relations": {"orders.order_id -> order_items.order_id"},
        "example_patterns": set(),
    }
    docs = [
        {
            "text": "Table: orders\nColumns:\n  - order_id",
            "metadata": {"table": "orders", "columns": ["order_id"], "relations": []},
        }
    ]

    coverage = assess_coverage(needs, docs)

    assert coverage["is_sufficient"] is False
    assert "order_items" in coverage["missing"]["tables"]
    assert "quantity" in coverage["missing"]["columns"]


def test_prompt_includes_schema_profiles_rows_and_examples():
    context = {
        "schema_docs": [
            {
                "text": (
                    "Table: products\n"
                    "Columns:\n"
                    "  - price (NUMERIC): List price | min=10, max=99, mean=40\n"
                    "Sample rows:\n"
                    "  - product_id=1, category=Electronics"
                ),
                "metadata": {"table": "products", "columns": ["price"]},
            }
        ],
        "example_docs": [{"text": "Question: top products\nSQL: SELECT * FROM products"}],
    }

    prompt = build_prompt("Top products by price", context)

    assert "min=10" in prompt
    assert "Sample rows" in prompt
    assert "SELECT * FROM products" in prompt


def test_sql_validation_rejects_unsafe_sql_and_accepts_cte():
    with pytest.raises(SqlValidationError):
        validate_sql("DELETE FROM orders", {"orders"})

    with pytest.raises(SqlValidationError):
        validate_sql("SELECT * FROM orders; SELECT * FROM customers", {"orders"})

    with pytest.raises(SqlValidationError):
        validate_sql("SELECT * FROM customers", {"orders"})

    sql = validate_sql(
        "WITH recent AS (SELECT order_id FROM orders) SELECT * FROM recent",
        {"orders"},
    )
    assert sql.startswith("WITH recent")


def test_answer_question_uses_core_pipeline_with_mocks(monkeypatch):
    def fake_retrieve_context(question):
        return {
            "question_needs": {
                "tables": {"orders"},
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

    monkeypatch.setattr(pipeline, "retrieve_context", fake_retrieve_context)
    monkeypatch.setattr(pipeline, "generate_sql", lambda prompt, settings: "SELECT order_id FROM orders")
    monkeypatch.setattr(
        pipeline,
        "run_query",
        lambda sql, settings: {"columns": ["order_id"], "rows": [[1], [2]], "total": 2},
    )
    monkeypatch.setattr(pipeline, "load_settings", lambda: {"model": "test"})

    report = pipeline.answer_question("How many orders?")

    assert report["status"] == "completed"
    assert report["sections"][0]["sql"] == "SELECT order_id FROM orders"
    assert "order_id" in report["sections"][0]["answer"]


def test_answer_question_splits_independent_questions(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "retrieve_context",
        lambda question: {
            "question_needs": {
                "tables": {"orders"},
                "columns": {"order_id"},
                "relations": set(),
                "example_patterns": set(),
            },
            "schema_coverage": {"is_sufficient": True, "missing": {}},
            "schema_docs": [{"text": "Table: orders", "metadata": {"table": "orders"}}],
            "example_docs": [],
        },
    )
    monkeypatch.setattr(pipeline, "generate_sql", lambda prompt, settings: "SELECT order_id FROM orders")
    monkeypatch.setattr(
        pipeline,
        "run_query",
        lambda sql, settings: {"columns": ["order_id"], "rows": [[1]], "total": 1},
    )
    monkeypatch.setattr(pipeline, "load_settings", lambda: {"model": "test"})

    report = pipeline.answer_question("How many orders and show revenue")

    assert len(report["sections"]) == 2
