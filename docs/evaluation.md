# Beacon Evaluation Notes

Last updated: 2026-06-30.

## Commands

Run from the repository root:

```powershell
uv run pytest tests -q
uv run beacon-index
uv run python tests/test_cases/run_master_plan_tests.py
uv run python tests/test_cases/generate_report.py
```

The 10-question runner writes `tests/test_results/master_plan_evaluation_results.json`. The HTML renderer writes `tests/test_results/report.html`.

## Focused Tests

The focused test suite covers retrieval, semantic profiles, prompting, SQL validation, dynamic retry, feedback examples, schema graph behavior, vector storage, and smoke-level pipeline behavior.

The current report preserves the previous focused-test note of `47 passed`. Run `uv run pytest tests -q` before publishing a new measured test count.

## Latest 10-Question Rerun

The latest rerun was executed on 2026-06-30 with:

```powershell
uv run python tests/test_cases/run_master_plan_tests.py
uv run python tests/test_cases/generate_report.py
```

The English run produced 7 completed questions and 3 top-level API/model-channel errors. The errors were external `503 model_not_found` responses for `qwen3-coder-480b-a35b-instruct` under the configured proxy group.

The Vietnamese run produced 6 completed questions, 2 failed questions, and 2 top-level API/model-channel errors. The failures are recorded in `tests/test_results/master_plan_evaluation_results.json`; the visible pattern is schema-context validation around `order_date` on the affected Vietnamese questions.

Because the latest rerun includes external model-channel errors, it should be treated as the latest pipeline run record, not as a clean semantic-accuracy measurement.

## Best Recorded Result

The best achieved benchmark-planning result is 55% accuracy on the BIRD-dev set.

This result is separate from the local 10-question e-commerce run. The BIRD-dev note is useful because it shows the next method pressure point: table recall can become strong, but schema focus, projection discipline, and output exactness still matter.

## Historical 10-Question Note

An earlier complete English run finished all 10 English questions and was manually judged 9/10 fully correct. The main caveat was Q9, where the SQL used average `discount_amount` as the discount basis. Metadata and examples were then updated to teach discount rate as `discount_amount / NULLIF(quantity * unit_price, 0)`.

That historical result remains useful as a sanity check, while the 2026-06-30 JSON/HTML files are the latest generated artifacts.
