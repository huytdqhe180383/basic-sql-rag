"""
Tests for coverage.py and retriever.py.

Run with: pytest tests/ -v
"""

import sys
import os
from unittest.mock import patch, MagicMock

import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coverage import (
    extract_question_needs,
    assess_coverage,
    RELATION_GRAPH,
    _get_required_relations,
)
from retriever import _format_schema_text, _format_example_text


# ============================================================================
# question_needs extraction tests
# ============================================================================

class TestExtractQuestionNeeds:
    """Tests for extract_question_needs with various question types."""

    def test_customer_signup_count(self):
        """Signup/customer-count questions should require customers."""
        result = extract_question_needs("How many customers signed up in 2025?")
        assert "customers" in result["required_tables"]
        assert "signup_date" in result["required_columns"]
        assert "customer_count" in result["question_families"]
        assert result["needs_aggregation"] is True

    def test_mobile_order_count(self):
        """Mobile device order count should require orders."""
        result = extract_question_needs(
            "How many orders were placed via mobile last month?"
        )
        assert "orders" in result["required_tables"]
        assert "device_type" in result["required_columns"]
        assert "device_analysis" in result["question_families"]
        assert result["needs_aggregation"] is True

    def test_product_revenue_question(self):
        """Revenue questions with product dimensions should use orders + order_items + products."""
        result = extract_question_needs(
            "What is total revenue by product category?"
        )
        # Revenue by category should pull in products and not prefer sales
        assert "products" in result["required_tables"]
        assert "order_items" in result["required_tables"]
        assert "orders" in result["required_tables"]
        assert "category_analysis" in result["question_families"]
        assert {"quantity", "unit_price", "discount_amount", "category"}.issubset(
            result["required_columns"]
        )

    def test_city_level_customer_question(self):
        """City-level customer questions should require geography + customers."""
        result = extract_question_needs("Which city has the most customers?")
        assert "geography" in result["required_tables"]
        assert "customers" in result["required_tables"]
        assert "city_analysis" in result["question_families"]

    def test_inventory_reorder_question(self):
        """Inventory reorder questions should require inventory + products."""
        result = extract_question_needs(
            "Which products need reordering and what is their stock on hand?"
        )
        assert "inventory" in result["required_tables"]
        assert "products" in result["required_tables"]
        assert "orders" not in result["required_tables"]
        assert "reorder_analysis" in result["question_families"]

    def test_daily_revenue_prefers_sales(self):
        """Daily revenue with no business dimensions should prefer sales."""
        result = extract_question_needs(
            "What was daily Revenue and COGS last week?"
        )
        assert result["required_tables"] == ["sales"]
        assert {"Date", "Revenue", "COGS"}.issubset(result["required_columns"])
        assert "cogs" not in result["required_columns"]
        assert "daily_sales_aggregate" in result["question_families"]

    def test_revenue_by_customer_ignores_sales(self):
        """Revenue with customer dimensions should not use sales table."""
        result = extract_question_needs(
            "What is total revenue per customer?"
        )
        assert "orders" in result["required_tables"]
        assert "order_items" in result["required_tables"]
        assert "sales" not in result["required_tables"]

    def test_no_keywords_returns_empty(self):
        """Questions with no matching keywords should have empty requirements."""
        result = extract_question_needs("What time is it?")
        assert result["required_tables"] == []
        assert result["required_columns"] == []

    def test_pattern_detection(self):
        """Patterns should be detected from keywords."""
        result = extract_question_needs("How many customers are there?")
        assert "single_table_count" in result["example_patterns"]
        assert result["needs_example_query"] is True

    def test_top_n_pattern(self):
        """Top-n keywords should detect top_n pattern."""
        result = extract_question_needs("What are the top 5 products?")
        assert "top_n" in result["example_patterns"]

    def test_geography_requires_business_table(self):
        """Geography-only keyword should pull in a business table that owns zip."""
        result = extract_question_needs("Show sales by city")
        assert "geography" in result["required_tables"]
        assert "orders" in result["required_tables"]
        assert "order_items" in result["required_tables"]
        assert "orders.zip -> geography.zip" in result["required_relations"]

    def test_reorder_word_does_not_trigger_orders(self):
        """Inventory wording must not trigger order analysis by substring."""
        result = extract_question_needs("Show products with the reorder flag")
        assert "inventory" in result["required_tables"]
        assert "orders" not in result["required_tables"]


# ============================================================================
# Relation graph tests
# ============================================================================

class TestRelationGraph:
    """Tests for the relation graph and relation extraction."""

    def test_single_table_no_relations(self):
        """A single table needs no join relations."""
        assert _get_required_relations({"customers"}) == []

    def test_customers_orders_relation(self):
        """customers + orders should require the customer_id relation."""
        rels = _get_required_relations({"customers", "orders"})
        assert any("customers.customer_id" in r for r in rels)

    def test_unrelated_no_relations(self):
        """Two unrelated tables should not produce relations."""
        rels = _get_required_relations({"customers", "sales"})
        assert rels == []

    def test_full_chain_relations(self):
        """customers -> orders -> order_items -> products chain."""
        rels = _get_required_relations(
            {"customers", "orders", "order_items", "products"}
        )
        assert len(rels) == 3  # customers-orders, orders-order_items, order_items-products


# ============================================================================
# coverage checking tests
# ============================================================================

def _make_needs(tables=None, columns=None, relations=None, families=None,
                needs_example=False, example_patterns=None):
    """Helper to build a question_needs dict."""
    return {
        "question_families": families or [],
        "required_tables": tables or [],
        "required_columns": columns or [],
        "required_relations": relations or [],
        "needs_aggregation": False,
        "needs_example_query": needs_example,
        "example_patterns": example_patterns or [],
    }


def _make_schema_doc(source_table, columns=None, families=None, relations=None):
    """Helper to build a schema doc dict as returned by retriever."""
    text_lines = [f"Table: {source_table}", "", "Columns:"]
    for col in (columns or []):
        text_lines.append(f"  - {col} (TEXT): description")
    text_lines.append("")
    text_lines.append("Relations:")
    for rel in (relations or []):
        text_lines.append(f"  - {rel}")
    return {
        "text": "\n".join(text_lines),
        "metadata": {
            "source_table": source_table,
            "question_families": families or [],
            "grain": "one row per thing",
            "columns": columns or [],
        },
    }


class TestAssessCoverage:
    """Tests for assess_coverage function."""

    def test_missing_tables_fails(self):
        """Coverage should fail when required tables are missing."""
        needs = _make_needs(tables=["customers", "orders"])
        docs = [_make_schema_doc("customers")]  # missing orders
        result = assess_coverage(needs, docs)
        assert result["is_sufficient"] is False
        assert result["schema_coverage"]["tables_ok"] is False

    def test_missing_relations_fails(self):
        """Coverage should fail when required relations are missing."""
        needs = _make_needs(
            tables=["customers", "orders"],
            relations=["customers.customer_id -> orders.customer_id"],
        )
        docs = [
            _make_schema_doc("customers", columns=["customer_id"]),
            _make_schema_doc("orders", columns=["order_id"]),
            # Neither doc has the relation text
        ]
        result = assess_coverage(needs, docs)
        assert result["schema_coverage"]["relations_ok"] is False
        assert result["is_sufficient"] is False

    def test_correct_subset_passes(self):
        """A correctly covered subset should pass all checks."""
        needs = _make_needs(
            tables=["customers"],
            columns=["signup_date", "customer_id"],
            families=["customer_count"],
        )
        docs = [
            _make_schema_doc(
                "customers",
                columns=["customer_id", "signup_date", "gender"],
                families=["customer_count"],
            ),
        ]
        result = assess_coverage(needs, docs)
        assert result["is_sufficient"] is True
        assert result["schema_coverage"]["tables_ok"] is True
        assert result["schema_coverage"]["columns_ok"] is True

    def test_example_miss_does_not_fail(self):
        """Missing example pattern should not block overall sufficiency."""
        needs = _make_needs(
            tables=["customers"],
            columns=["customer_id"],
            needs_example=True,
            example_patterns=["top_n"],
        )
        docs = [_make_schema_doc("customers", columns=["customer_id"])]
        example_docs = [
            {
                "text": "Question: X\nSQL: SELECT 1",
                "metadata": {"pattern": "single_table_count"},
            }
        ]
        result = assess_coverage(needs, docs, example_docs)
        # Schema coverage is fine, so overall should pass
        assert result["is_sufficient"] is True
        # Example pattern didn't match, but that's ok
        assert result["example_coverage"]["pattern_match_ok"] is False

    def test_example_match_detected(self):
        """Matching example pattern should be detected."""
        needs = _make_needs(
            tables=["customers"],
            columns=["customer_id"],
            needs_example=True,
            example_patterns=["top_n"],
        )
        docs = [_make_schema_doc("customers", columns=["customer_id"])]
        example_docs = [
            {
                "text": "Question: Top 5 ...",
                "metadata": {"pattern": "top_n"},
            }
        ]
        result = assess_coverage(needs, docs, example_docs)
        assert result["is_sufficient"] is True
        assert result["example_coverage"]["pattern_match_ok"] is True

    def test_question_family_ok(self):
        """At least one question family from needs should be covered."""
        needs = _make_needs(
            tables=["customers"],
            families=["customer_count", "signup_analysis"],
        )
        docs = [
            _make_schema_doc(
                "customers",
                families=["customer_count"],
            ),
        ]
        result = assess_coverage(needs, docs)
        assert result["schema_coverage"]["question_family_ok"] is True

    def test_empty_needs_always_sufficient(self):
        """Empty requirements should always be sufficient."""
        needs = _make_needs()
        result = assess_coverage(needs, [])
        assert result["is_sufficient"] is True

    def test_missing_columns_fails(self):
        """Coverage should fail when required columns are missing."""
        needs = _make_needs(
            tables=["customers"],
            columns=["signup_date", "nonexistent_col"],
        )
        docs = [_make_schema_doc("customers", columns=["customer_id", "signup_date"])]
        result = assess_coverage(needs, docs)
        assert result["schema_coverage"]["columns_ok"] is False
        assert result["is_sufficient"] is False

    def test_metadata_columns_and_relations_are_counted(self):
        """Coverage should use structured metadata without parsing display text."""
        needs = _make_needs(
            tables=["orders", "order_items"],
            columns=["order_id", "quantity"],
            relations=["orders.order_id -> order_items.order_id"],
        )
        docs = [
            {
                "text": "Order schema",
                "metadata": {
                    "source_table": "orders",
                    "columns": ["order_id"],
                    "relations": ["orders.order_id -> order_items.order_id"],
                },
            },
            {
                "text": "Line-item schema",
                "metadata": {
                    "source_table": "order_items",
                    "columns": ["quantity"],
                    "relations": [],
                },
            },
        ]
        result = assess_coverage(needs, docs)
        assert result["is_sufficient"] is True

    def test_required_example_without_match_reports_miss(self):
        """An empty optional-example result should be reported as no match."""
        needs = _make_needs(
            tables=["customers"],
            needs_example=True,
            example_patterns=["single_table_count"],
        )
        docs = [_make_schema_doc("customers")]
        result = assess_coverage(needs, docs, [])
        assert result["is_sufficient"] is True
        assert result["example_coverage"]["pattern_match_ok"] is False


# ============================================================================
# Prompt formatting tests
# ============================================================================

class TestPromptFormatting:
    """Tests for prompt text assembly."""

    def test_schema_text_formatting(self):
        """Schema docs should be formatted with separators."""
        docs = [
            {"text": "Table: customers\nColumns:\n  - id"},
            {"text": "Table: orders\nColumns:\n  - order_id"},
        ]
        result = _format_schema_text(docs)
        assert "customers" in result
        assert "orders" in result
        assert "\n\n---\n\n" in result

    def test_empty_example_text(self):
        """Empty example list should produce empty string."""
        assert _format_example_text([]) == ""

    def test_example_text_formatting(self):
        """Example docs should be formatted."""
        docs = [
            {"text": "Question: X?\nSQL: SELECT 1"},
        ]
        result = _format_example_text(docs)
        assert "Question: X?" in result
        assert "SELECT 1" in result


# ============================================================================
# Adaptive retrieval tests (mocked indices)
# ============================================================================

class TestAdaptiveRetrieval:
    """Tests for adaptive retrieval logic (mocked)."""

    @patch("retriever._load_indices")
    @patch("retriever._retrieve_schema")
    @patch("retriever._retrieve_examples")
    def test_simple_question_stops_early(
        self, mock_retrieve_ex, mock_retrieve_schema, mock_load
    ):
        """Simple customer question should stop at low k."""
        from retriever import retrieve_context

        mock_schema_index = MagicMock()
        mock_example_index = MagicMock()
        mock_load.return_value = (mock_schema_index, mock_example_index)

        # Return sufficient coverage at k=2
        doc = _make_schema_doc(
            "customers",
            columns=["customer_id", "signup_date"],
            families=["customer_count"],
        )
        mock_retrieve_schema.return_value = [doc, doc]
        mock_retrieve_ex.return_value = []

        result = retrieve_context("How many customers signed up in 2025?")
        assert result["schema_coverage"]["is_sufficient"] is True
        # Should have called retrieve_schema exactly once (k=2, stopped there)
        assert mock_retrieve_schema.call_count == 1

    @patch("retriever._load_indices")
    @patch("retriever._retrieve_schema")
    @patch("retriever._retrieve_examples")
    def test_revenue_by_product_expands(
        self, mock_retrieve_ex, mock_retrieve_schema, mock_load
    ):
        """Revenue-by-product question should expand to needed tables."""
        from retriever import retrieve_context

        mock_schema_index = MagicMock()
        mock_example_index = MagicMock()
        mock_load.return_value = (mock_schema_index, mock_example_index)

        # k=2: only returns orders, insufficient
        def retrieve_side_effect(idx, q, k):
            if k == 2:
                return [
                    _make_schema_doc("orders", columns=["order_id"]),
                ]
            elif k == 3:
                return [
                    _make_schema_doc(
                        "orders",
                        columns=["order_id"],
                        relations=["orders.order_id -> order_items.order_id"],
                    ),
                    _make_schema_doc(
                        "order_items",
                        columns=[
                            "order_id",
                            "product_id",
                            "quantity",
                            "unit_price",
                            "discount_amount",
                        ],
                        relations=[
                            "order_items.product_id -> products.product_id"
                        ],
                    ),
                    _make_schema_doc(
                        "products", columns=["product_id", "category"]
                    ),
                ]
            else:
                return []

        mock_retrieve_schema.side_effect = retrieve_side_effect
        mock_retrieve_ex.return_value = []

        result = retrieve_context("What is total revenue by product category?")
        assert result["schema_coverage"]["is_sufficient"] is True
        # Called twice: k=2 insufficient, k=3 sufficient
        assert mock_retrieve_schema.call_count == 2

    @patch("retriever._load_indices")
    @patch("retriever._retrieve_schema")
    @patch("retriever._retrieve_examples")
    def test_never_exceeds_max_k(
        self, mock_retrieve_ex, mock_retrieve_schema, mock_load
    ):
        """Retrieval should never exceed SCHEMA_K_MAX=5."""
        from retriever import retrieve_context
        from retriever import SCHEMA_K_MAX

        mock_schema_index = MagicMock()
        mock_example_index = MagicMock()
        mock_load.return_value = (mock_schema_index, mock_example_index)

        # Always insufficient
        mock_retrieve_schema.return_value = []
        mock_retrieve_ex.return_value = []

        retrieve_context("some complex question nobody can answer")

        max_k_used = max(call.args[2] for call in mock_retrieve_schema.call_args_list)
        assert max_k_used <= SCHEMA_K_MAX

    @patch("retriever._load_indices")
    @patch("retriever._retrieve_schema")
    @patch("retriever._retrieve_examples")
    def test_daily_sales_question_prefers_sales(
        self, mock_retrieve_ex, mock_retrieve_schema, mock_load
    ):
        """Daily sales question should retrieve sales table."""
        from retriever import retrieve_context

        mock_schema_index = MagicMock()
        mock_example_index = MagicMock()
        mock_load.return_value = (mock_schema_index, mock_example_index)

        mock_retrieve_schema.return_value = [
            _make_schema_doc(
                "sales",
                columns=["Date", "Revenue", "COGS"],
                families=["daily_sales_aggregate"],
            ),
        ]
        mock_retrieve_ex.return_value = []

        result = retrieve_context("What was daily Revenue and COGS last week?")
        assert result["question_needs"]["required_tables"] == ["sales"]
        assert result["schema_coverage"]["is_sufficient"] is True

    @patch("retriever._load_indices")
    @patch("retriever._retrieve_schema")
    @patch("retriever._retrieve_examples")
    def test_inventory_question_reaches_products(
        self, mock_retrieve_ex, mock_retrieve_schema, mock_load
    ):
        """Inventory question with product attributes should reach products."""
        from retriever import retrieve_context

        mock_schema_index = MagicMock()
        mock_example_index = MagicMock()
        mock_load.return_value = (mock_schema_index, mock_example_index)

        mock_retrieve_schema.return_value = [
            _make_schema_doc(
                "inventory",
                columns=["product_id", "reorder_flag", "stock_on_hand"],
                families=["inventory_health", "reorder_analysis"],
                relations=["inventory.product_id -> products.product_id"],
            ),
            _make_schema_doc(
                "products",
                columns=["product_id", "product_name", "category"],
                families=["product_breakdown"],
            ),
        ]
        mock_retrieve_ex.return_value = []

        result = retrieve_context(
            "Which products need reordering and what is their stock on hand?"
        )
        assert "inventory" in result["question_needs"]["required_tables"]
        assert "products" in result["question_needs"]["required_tables"]
        assert result["schema_coverage"]["is_sufficient"] is True

    @patch("retriever._load_indices")
    @patch("retriever._retrieve_schema")
    @patch("retriever._retrieve_examples")
    def test_unmatched_examples_are_not_returned(
        self, mock_retrieve_ex, mock_retrieve_schema, mock_load
    ):
        """Only examples matching an inferred pattern should enter the prompt."""
        from retriever import retrieve_context

        mock_load.return_value = (MagicMock(), MagicMock())
        mock_retrieve_schema.return_value = [
            _make_schema_doc(
                "customers",
                columns=["customer_id"],
                families=["customer_count"],
            )
        ]
        mock_retrieve_ex.return_value = [
            {
                "text": "Question: unrelated\nSQL: SELECT 1",
                "metadata": {"pattern": "inventory_health"},
            }
        ]

        result = retrieve_context("How many customers are there?")

        assert result["example_docs"] == []
        assert result["prompt_context"]["example_text"] == ""
        assert result["schema_coverage"]["example_coverage"][
            "pattern_match_ok"
        ] is False

    @patch("retriever._load_indices")
    @patch("retriever._retrieve_schema")
    @patch("retriever._retrieve_examples")
    def test_examples_are_skipped_when_schema_is_insufficient(
        self, mock_retrieve_ex, mock_retrieve_schema, mock_load
    ):
        """Optional examples should not be retrieved before schema coverage succeeds."""
        from retriever import retrieve_context

        mock_load.return_value = (MagicMock(), MagicMock())
        mock_retrieve_schema.return_value = []

        result = retrieve_context("What is total revenue by product category?")

        assert result["schema_coverage"]["is_sufficient"] is False
        mock_retrieve_ex.assert_not_called()


# ============================================================================
# Light end-to-end smoke scenarios (question_needs only)
# ============================================================================

class TestSmokeScenarios:
    """End-to-end smoke tests verifying question needs extraction for key scenarios."""

    def test_customers_signed_up_2025(self):
        result = extract_question_needs("How many customers signed up in 2025?")
        assert result["required_tables"] == ["customers"]
        assert "signup_date" in result["required_columns"]
        assert result["needs_aggregation"] is True

    def test_orders_mobile_last_month(self):
        result = extract_question_needs(
            "How many orders were placed via mobile last month?"
        )
        assert "orders" in result["required_tables"]
        assert "device_type" in result["required_columns"]

    def test_revenue_by_product_category(self):
        result = extract_question_needs("What is total revenue by product category?")
        assert "products" in result["required_tables"]
        assert "order_items" in result["required_tables"]
        assert "category" in result["required_columns"]

    def test_city_most_revenue(self):
        result = extract_question_needs("Which city generated the most revenue?")
        assert "geography" in result["required_tables"]
        assert "revenue_calculation" in result["question_families"]

    def test_fill_rate_trend_by_month(self):
        result = extract_question_needs("What is the fill rate trend by month?")
        assert "inventory" in result["required_tables"]
        assert "fill_rate" in result["required_columns"]

    def test_daily_revenue_and_cogs_last_week(self):
        result = extract_question_needs(
            "What was daily Revenue and COGS last week?"
        )
        assert result["required_tables"] == ["sales"]
        assert "Revenue" in result["required_columns"]
        assert "COGS" in result["required_columns"]
