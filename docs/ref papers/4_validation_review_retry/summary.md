# SQL Validation, Result Review, and Retry

This category covers the problem where SQL runs successfully but still answers the wrong question.

## Papers

- [CycleSQL: Data-Based Self-Explanations](cyclesql_data_based_self_explanations.md)
  - Focus: using data-grounded natural language explanations to validate SQL results.
  - Beacon use: supports the LLM reviewer that checks executed results before final answer composition.

- [SQLDriller: Execution Consistency](sqldriller_execution_consistency.md)
  - Focus: execution-based validation and repair using consistency checks.
  - Beacon use: reinforces that SQL execution success is not enough; logical result review matters.

- [NL2SQL-BUGs: Detecting Semantic Errors](nl2sql_bugs_semantic_errors.md)
  - Focus: detecting common semantic errors in generated SQL.
  - Beacon use: provides a frame for local bug categories such as missed table, wrong grain, wrong join, and wrong aggregation.

- [Memo-SQL: Structured Decomposition and Experience-Driven Self-Correction](memo_sql_self_correction.md)
  - Focus: using decomposition and error-fix experience for self-correction.
  - Beacon use: supports keeping retry history inside one request and turning fixed failures into future examples.
