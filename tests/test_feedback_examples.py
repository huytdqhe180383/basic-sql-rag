import json

from beacon.runtime.feedback_examples import candidate_from_attempt, save_candidate_example


def test_candidate_from_attempt_extracts_reviewed_query_metadata():
    attempt = {
        "sql": "SELECT COUNT(*) AS order_count FROM orders",
        "review_reason": "Correct count.",
        "status": "completed",
    }
    result = {"columns": ["order_count"], "rows": [[3]], "total": 1}
    linked_context = {
        "selected_tables": ["orders"],
        "signals": {"metrics": {"count"}, "filters": set(), "time_grain": None},
    }

    candidate = candidate_from_attempt("How many orders?", attempt, result, linked_context)

    assert candidate["question"] == "How many orders?"
    assert candidate["tables"] == ["orders"]
    assert candidate["metrics"] == ["count"]
    assert candidate["status"] == "candidate"


def test_save_candidate_example_deduplicates(tmp_path):
    path = tmp_path / "example_candidates.json"
    candidate = {"fingerprint": "abc", "question": "Q", "sql": "SELECT 1", "status": "candidate"}

    save_candidate_example(path, candidate)
    save_candidate_example(path, candidate)

    rows = json.loads(path.read_text(encoding="utf-8"))
    assert rows == [candidate]
