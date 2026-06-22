"""Tests for semantic metadata and value grounding."""

from beacon.indexing_tools import load_semantic_model
from beacon.metadata_grounding import apply_grounding_to_needs, ground_question_metadata
from beacon import retrieval
from beacon.retrieval import build_prompt
from beacon.retrieval_tools import extract_question_needs


def test_grounding_maps_question_terms_to_exact_values():
    semantic_model = load_semantic_model()
    question = "Which acquisition channel brings in the most Apple Pay buyers?"

    evidence = ground_question_metadata(question, semantic_model)
    grounded = apply_grounding_to_needs(extract_question_needs(question), evidence)

    assert {
        (item["term"], item["table"], item["column"], item["value"])
        for item in evidence
    } >= {
        ("apple pay", "orders", "payment_method", "apple_pay"),
    }
    assert "orders" in grounded["tables"]
    assert "payment_method" in grounded["columns"]


def test_prompt_includes_matched_evidence_before_schema():
    context = {
        "matched_evidence": [
            {
                "term": "apple pay",
                "table": "orders",
                "column": "payment_method",
                "value": "apple_pay",
                "value_sql": "'apple_pay'",
                "source": "profile",
                "score": 90,
            }
        ],
        "schema_docs": [
            {
                "text": "Table: orders\nColumns:\n  - payment_method (TEXT)",
                "metadata": {"table": "orders", "columns": ["payment_method"]},
            }
        ],
        "example_docs": [],
    }

    prompt = build_prompt("Apple Pay orders", context)

    assert prompt.index("MATCHED EVIDENCE:") < prompt.index("RELEVANT SCHEMA:")
    assert "\"apple pay\" -> orders.payment_method = 'apple_pay'" in prompt


def test_retrieve_context_forces_schema_docs_for_grounded_tables(monkeypatch):
    semantic_model = [
        {
            "source_table": "orders",
            "semantic_name": "Orders",
            "grain": "one row per order",
            "description": "Orders and payment methods.",
            "columns": [
                {
                    "name": "payment_method",
                    "type": "TEXT",
                    "description": "Payment method.",
                    "profile": {
                        "null_count": 0,
                        "distinct_count": 1,
                        "sample_values": ["apple_pay"],
                    },
                }
            ],
            "relations": [],
            "question_families": ["payment_analysis"],
            "sample_rows": [{"payment_method": "apple_pay"}],
        }
    ]

    monkeypatch.setattr(retrieval, "load_indices", lambda: ("schema-index", "example-index"))
    monkeypatch.setattr(retrieval, "load_semantic_model", lambda: semantic_model)
    monkeypatch.setattr(retrieval, "retrieve_nodes", lambda index, question, k: [])

    context = retrieval.retrieve_context("Apple Pay buyers")

    assert context["schema_coverage"]["is_sufficient"] is True
    assert context["schema_docs"][0]["metadata"]["table"] == "orders"
    assert context["question_needs"]["tables"] == {"orders"}
    assert context["matched_evidence"][0]["value"] == "apple_pay"


def test_grounding_expands_complex_question_needs():
    semantic_model = load_semantic_model()

    checks = [
        (
            "Tell me the 3 most profitable products ever, but exclude items currently flagged as overstock.",
            {"products", "order_items", "inventory"},
            {"overstock_flag"},
        ),
        (
            "Did we get more new folks from social media or organic search in the first half of 2020? "
            "And what was the total COGS for that period?",
            {"customers", "sales"},
            {"acquisition_channel", "COGS"},
        ),
        (
            "List the top 2 cities where guys buy the most stuff and the corresponding total revenue from male customers.",
            {"customers", "orders", "order_items", "geography"},
            {"gender", "city", "quantity"},
        ),
        (
            "Which acquisition channel brings in the most Apple Pay buyers, and what is the most common age bracket?",
            {"customers", "orders"},
            {"acquisition_channel", "payment_method", "age_group"},
        ),
        (
            "We are looking at people who signed up in 2018. "
            "Which source gives us the most loyal buyers, and what color of clothing do they like to buy most?",
            {"customers", "orders", "order_items", "products"},
            {"signup_date", "acquisition_channel", "color", "quantity"},
        ),
    ]

    for question, expected_tables, expected_columns in checks:
        evidence = ground_question_metadata(question, semantic_model)
        grounded = apply_grounding_to_needs(extract_question_needs(question), evidence)

        assert expected_tables.issubset(grounded["tables"]), question
        assert expected_columns.issubset(grounded["columns"]), question
