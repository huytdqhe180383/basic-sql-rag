from beacon.question_signals import extract_question_signals


def test_extract_question_signals_detects_generic_intents():
    signals = extract_question_signals("Show the top 3 cities by revenue in 2020")

    assert "top_n" in signals["intents"]
    assert "group_by" in signals["intents"]
    assert "aggregation" in signals["intents"]
    assert signals["metrics"] >= {"revenue"}
    assert signals["time_grain"] == "year"
    assert signals["numbers"][0]["value"] == 3
    assert signals["dates"][0]["value"] == 2020


def test_extract_question_signals_uses_example_metric_labels():
    signals = extract_question_signals(
        "Top profitable products by revenue minus cogs, excluding current overstock."
    )

    assert {"revenue", "cogs", "profit", "stock_on_hand"}.issubset(signals["metrics"])


def test_extract_question_signals_uses_schema_names_as_weak_matches():
    semantic_model = [
        {
            "source_table": "finance_events",
            "semantic_name": "Finance Events",
            "description": "Revenue and cost events.",
            "columns": [
                {"name": "gross_revenue", "description": "Gross revenue amount."},
                {"name": "event_date", "description": "Event date."},
            ],
        }
    ]

    signals = extract_question_signals("What revenue did we get last year?", semantic_model)

    assert signals["weak_tables"]["finance_events"] > 0
    assert signals["weak_columns"]["gross_revenue"] > 0
    assert "revenue" in signals["metrics"]
