"""Tests for retrieval-based prompt assembly."""

from unittest.mock import patch

from pipeline import _build_prompt, _build_retry_prompt


@patch("pipeline.retrieve_context")
def test_prompt_contains_only_retrieved_schema(mock_retrieve_context):
    """Prompt assembly must not reintroduce the full schema dump."""
    mock_retrieve_context.return_value = {
        "prompt_context": {
            "schema_text": "Table: customers\nColumns:\n  - customer_id",
            "example_text": "",
        }
    }

    prompt = _build_prompt("How many customers are there?")

    assert "Table: customers" in prompt
    assert "Table: inventory" not in prompt
    assert "EXAMPLE QUERIES:" not in prompt
    assert "QUESTION:" in prompt


@patch("pipeline.retrieve_context")
def test_prompt_includes_accepted_examples(mock_retrieve_context):
    """A matched example should appear in its own prompt section."""
    mock_retrieve_context.return_value = {
        "prompt_context": {
            "schema_text": "Table: sales",
            "example_text": "Question: Daily revenue?\nSQL: SELECT Date, Revenue FROM sales",
        }
    }

    prompt = _build_prompt("Show daily revenue")

    assert "EXAMPLE QUERIES:" in prompt
    assert "SELECT Date, Revenue FROM sales" in prompt


def test_retry_prompt_preserves_retrieved_context():
    """A SQL correction request should retain the covered schema and question."""
    base_prompt = (
        "RELEVANT SCHEMA:\n\nTable: customers\n\n"
        "QUESTION: How many customers?\n\nSQL:"
    )

    prompt = _build_retry_prompt(
        base_prompt,
        error="column does not exist",
        failed_sql="SELECT missing FROM customers",
    )

    assert "Table: customers" in prompt
    assert "QUESTION: How many customers?" in prompt
    assert "column does not exist" in prompt
    assert "SELECT missing FROM customers" in prompt
