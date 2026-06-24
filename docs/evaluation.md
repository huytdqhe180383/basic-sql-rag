# Beacon Evaluation Notes

Last updated: 2026-06-24.

## Commands

Run from the repo root:

```powershell
$env:PYTHONPATH = "src"
$env:BEACON_USE_HASH_EMBEDDINGS = "1"
pytest tests -q
python -m beacon.indexing
python "tests\test cases\run_master_plan_tests.py"
python "tests\test cases\generate_report.py"
```

## Unit And Smoke Tests

Latest focused test run:

- `47 passed`
- Command: `pytest tests -q`

Latest local index build:

- Command: `python -m beacon.indexing`
- Result: `Built local schema vectors.`

## English 10-Question Result

The last complete model-backed English run completed all 10 English questions:

- Execution status: `10 / 10 completed`
- Strict manual semantic review: `9 / 10 fully correct`
- Main caveat: Q9 executed, but used average `discount_amount` as the discount basis. The metadata and examples were then updated to teach discount rate as `discount_amount / NULLIF(quantity * unit_price, 0)`.

After that Q9 fix, a final rerun completed Q1-Q5 but the configured API account ran out of quota at Q6:

- Completed before quota: Q1-Q5 English, `5 / 5`
- Blocked by API quota: Q6-Q10 English and Vietnamese
- Error: `403 insufficient_user_quota`

Because the last run was externally blocked, do not treat the partial `tests/test results/master_plan_evaluation_results.json` as an accuracy regression.

## Strict Review Notes

Validated improvements in the complete run and follow-up diagnostics:

- Q2 now uses the latest inventory snapshot before excluding `overstock_flag = TRUE`.
- Q3 now preserves the dependent time phrase and computes total period COGS from `sales.cogs`.
- Q6 no longer fails on `generate_series`; the validator recognizes it as a safe PostgreSQL table-valued function.
- Q7 and Q10 stay as single dependent sections, so filters are not dropped during question splitting.
- Q9 retrieval now ranks the `latest_snapshot_discount_rate` example first after the metadata/example update.

Remaining limitation:

- The final Q9 SQL after the discount-rate fix could not be fully measured because the LLM API quota was exhausted.
