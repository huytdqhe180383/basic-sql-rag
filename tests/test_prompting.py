from beacon.prompting import build_sql_prompt


def test_build_sql_prompt_orders_evidence_schema_examples_and_question():
    context = {
        "evidence": [
            {
                "term": "apple pay",
                "table": "orders",
                "column": "payment_method",
                "value_sql": "'apple_pay'",
                "status": "pinned",
            }
        ],
        "schema_docs": [{"text": "Table: orders\nColumns:\n  - payment_method (TEXT)"}],
        "example_docs": [{"text": "Question: Apple Pay orders\nSQL: SELECT * FROM orders"}],
    }

    prompt = build_sql_prompt("Apple Pay orders", context)

    assert prompt.index("MATCHED EVIDENCE") < prompt.index("RELEVANT SCHEMA")
    assert prompt.index("RELEVANT SCHEMA") < prompt.index("EXAMPLE QUERIES")
    assert prompt.endswith("SQL:")
