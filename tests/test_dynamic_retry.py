from beacon.retry import classify_retry_need, repair_linked_context


def test_classify_retry_need_requests_retrieval_repair_for_known_table_outside_context():
    attempt = {
        "status": "validation_error",
        "error": "SQL references tables outside context: customers.",
    }
    known_schema = {"tables": {"orders", "customers"}, "selected_tables": {"orders"}}

    decision = classify_retry_need(attempt, known_schema)

    assert decision["action"] == "retrieval_repair"
    assert decision["requested_tables"] == ["customers"]


def test_classify_retry_need_requests_value_repair_for_empty_string_filter_result():
    attempt = {
        "status": "completed",
        "sql": "SELECT * FROM orders WHERE payment_method = 'apple pay'",
        "review_reason": "No rows returned.",
    }
    known_schema = {"tables": {"orders"}, "selected_tables": {"orders"}}

    decision = classify_retry_need(attempt, known_schema)

    assert decision["action"] == "value_repair"
    assert decision["value_terms"] == ["apple pay"]


def test_repair_linked_context_adds_requested_known_table_schema_doc():
    context = {"selected_tables": ["orders"], "schema_docs": [], "join_paths": []}
    decision = {
        "action": "retrieval_repair",
        "requested_tables": ["customers"],
        "requested_columns": [],
        "value_terms": [],
    }
    semantic_model = [
        {
            "source_table": "orders",
            "semantic_name": "Orders",
            "grain": "one row per order",
            "description": "Orders.",
            "columns": [],
            "relations": [],
        },
        {
            "source_table": "customers",
            "semantic_name": "Customers",
            "grain": "one row per customer",
            "description": "Customers.",
            "columns": [],
            "relations": [],
        },
    ]

    repaired = repair_linked_context(context, decision, semantic_model)

    assert repaired["selected_tables"] == ["customers", "orders"]
    assert repaired["schema_docs"][0]["metadata"]["table"] == "customers"
