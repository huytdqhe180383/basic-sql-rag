from beacon.example_retrieval import rank_examples


def test_rank_examples_prefers_structural_overlap():
    examples = [
        {
            "question": "Count orders",
            "sql": "SELECT COUNT(*) FROM orders",
            "tables": ["orders"],
            "pattern": "count",
            "metrics": ["count"],
            "filters": [],
            "time_grain": None,
        },
        {
            "question": "Revenue by category",
            "sql": "SELECT category, SUM(revenue) FROM x",
            "tables": ["orders", "products"],
            "pattern": "group_by",
            "metrics": ["revenue"],
            "filters": ["date_filter"],
            "time_grain": "year",
        },
    ]
    linked_context = {
        "selected_tables": ["orders", "products"],
        "signals": {
            "metrics": {"revenue"},
            "filters": {"date_filter"},
            "time_grain": "year",
            "intents": {"group_by"},
            "terms": ["revenue", "category"],
        },
    }

    ranked = rank_examples("Show revenue by category in 2020", examples, linked_context, limit=1)

    assert ranked[0]["question"] == "Revenue by category"


def test_rank_examples_prefers_metric_shape_over_broad_table_overlap():
    examples = [
        {
            "question": "Revenue by product segment",
            "tables": ["orders", "order_items", "products"],
            "metrics": ["revenue"],
            "filters": ["date_filter"],
            "time_grain": "year",
        },
        {
            "question": "Total COGS for a period",
            "tables": ["sales"],
            "metrics": ["cogs"],
            "filters": ["date_filter"],
            "time_grain": "year",
        },
    ]
    linked_context = {
        "selected_tables": ["orders", "order_items", "products", "sales"],
        "signals": {
            "metrics": {"cogs"},
            "filters": {"date_filter"},
            "time_grain": "year",
            "intents": {"aggregation"},
            "terms": ["total", "cogs", "period"],
        },
    }

    ranked = rank_examples("What was total COGS for that period?", examples, linked_context, limit=1)

    assert ranked[0]["question"] == "Total COGS for a period"


def test_rank_examples_uses_fallback_pattern_as_shape_hint():
    examples = [
        {
            "question": "Profit by product",
            "tables": ["orders", "order_items", "products", "inventory"],
            "pattern": "profit_calculation",
            "metrics": ["cogs"],
            "filters": ["date_filter"],
            "time_grain": None,
        },
        {
            "question": "Daily COGS aggregate",
            "tables": ["sales"],
            "pattern": "daily_sales_aggregate",
            "metrics": ["cogs"],
            "filters": ["date_filter"],
            "time_grain": "year",
        },
    ]
    linked_context = {
        "selected_tables": ["orders", "order_items", "products", "inventory", "sales"],
        "signals": {
            "metrics": {"cogs"},
            "filters": {"date_filter"},
            "time_grain": "year",
            "intents": {"aggregation"},
            "terms": ["total", "cogs", "period"],
        },
        "fallback_needs": {"example_patterns": {"daily_sales_aggregate"}},
    }

    ranked = rank_examples("What was total COGS for that period?", examples, linked_context, limit=1)

    assert ranked[0]["question"] == "Daily COGS aggregate"
