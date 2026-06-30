from beacon.linking.schema_index import build_schema_records


def test_build_schema_records_creates_table_and_column_records():
    semantic_model = [
        {
            "source_table": "orders",
            "semantic_name": "Orders",
            "grain": "one row per order",
            "description": "Customer order records.",
            "columns": [
                {
                    "name": "payment_method",
                    "type": "TEXT",
                    "description": "How the customer paid.",
                    "profile": {
                        "sample_values": ["apple_pay"],
                        "top_values": [{"value": "cod", "count": 3}],
                    },
                }
            ],
        }
    ]

    records = build_schema_records(semantic_model)

    assert [record["kind"] for record in records] == ["table", "column"]
    assert records[0]["id"] == "orders"
    assert records[1]["id"] == "orders.payment_method"
    assert "apple_pay" in records[1]["text"]
    assert records[1]["metadata"]["table"] == "orders"
