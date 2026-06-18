"""Core tests for the simplified Beacon pipeline."""

import pytest

from beacon import pipeline
from beacon.retrieval import (
    assess_coverage,
    build_prompt,
    extract_question_needs,
    matching_examples,
    rank_docs,
)
from beacon.sql import SqlValidationError, validate_sql


def test_question_understanding_selects_relevant_schema_needs():
    signup = extract_question_needs("How many customers signed up in 2025?")
    assert signup["tables"] == {"customers"}
    assert "signup_date" in signup["columns"]
    assert "single_table_date_filter" in signup["example_patterns"]

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
    assert "inventory_health" in inventory["example_patterns"]

    city_revenue = extract_question_needs("Which city generated the most revenue?")
    assert {"orders", "order_items", "geography"}.issubset(city_revenue["tables"])
    assert "city" in city_revenue["columns"]
    assert "orders.zip -> geography.zip" in city_revenue["relations"]
    assert "geography_breakdown" in city_revenue["example_patterns"]

    product_stock = extract_question_needs("Show products with the reorder flag")
    assert {"inventory", "products"}.issubset(product_stock["tables"])
    assert "orders" not in product_stock["tables"]


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


def test_retrieval_ranks_plain_docs_with_visible_metadata():
    docs = [
        {
            "text": "Table: orders\nColumns:\n  - order_id",
            "metadata": {"table": "orders", "columns": ["order_id"]},
        },
        {
            "text": "Table: products\nColumns:\n  - category",
            "metadata": {"table": "products", "columns": ["category"]},
        },
    ]
    needs = {
        "tables": {"products"},
        "columns": {"category"},
        "relations": set(),
        "example_patterns": set(),
    }

    ranked = rank_docs("revenue by product category", docs, needs)

    assert ranked[0]["metadata"]["table"] == "products"


def test_matching_examples_prefers_matching_patterns_after_ranking():
    docs = [
        {
            "text": "Question: count orders\nPattern: single_table_count",
            "metadata": {"pattern": "single_table_count", "metrics": ["count"]},
        },
        {
            "text": "Question: revenue by category\nPattern: revenue_calculation",
            "metadata": {"pattern": "revenue_calculation", "metrics": ["revenue"]},
        },
    ]

    matches = matching_examples(docs, {"revenue_calculation"}, "revenue by category")

    assert matches == [docs[1]]


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
    responses = iter(
        [
            "SELECT order_id FROM orders",
            '{"satisfied": true, "reason": "The result answers the question.", "retry_instructions": ""}',
            "There are 2 orders.",
        ]
    )
    monkeypatch.setattr(pipeline, "call_llm", lambda messages, settings: next(responses))
    monkeypatch.setattr(
        pipeline,
        "run_query",
        lambda sql, settings: {"columns": ["order_id"], "rows": [[1], [2]], "total": 2},
    )
    monkeypatch.setattr(pipeline, "load_settings", lambda: {"model": "test"})

    report = pipeline.answer_question("How many orders?")

    assert report["status"] == "completed"
    assert report["sections"][0]["sql"] == "SELECT order_id FROM orders"
    assert report["sections"][0]["answer"] == "There are 2 orders."


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
    responses = iter(
        [
            "SELECT order_id FROM orders",
            '{"satisfied": true, "reason": "The result answers the question.", "retry_instructions": ""}',
            "First answer.",
            "SELECT order_id FROM orders",
            '{"satisfied": true, "reason": "The result answers the question.", "retry_instructions": ""}',
            "Second answer.",
        ]
    )
    monkeypatch.setattr(pipeline, "call_llm", lambda messages, settings: next(responses))
    monkeypatch.setattr(
        pipeline,
        "run_query",
        lambda sql, settings: {"columns": ["order_id"], "rows": [[1]], "total": 1},
    )
    monkeypatch.setattr(pipeline, "load_settings", lambda: {"model": "test"})

    report = pipeline.answer_question("How many orders and show revenue")

    assert len(report["sections"]) == 2
