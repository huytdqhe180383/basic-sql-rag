# SQL Validation, Result Review, and Retry

This category covers validating generated SQL statements, checking execution results, and correcting queries using feedback loops.

## Papers

- [CycleSQL: Data-Based Self-Explanations](cyclesql_data_based_self_explanations.md)
  - Focus: using data-grounded natural language explanations to validate SQL results.
  - Beacon use: supports the LLM reviewer that checks executed results before final answer composition.

- [Memo-SQL: Structured Decomposition and Experience-Driven Self-Correction](memo_sql_self_correction.md)
  - Focus: using decomposition and error-fix experience for self-correction.
  - Beacon use: supports keeping retry history inside one request and turning fixed failures into future examples.

- [LitE-SQL: Lightweight and Efficient Text-to-SQL](../2_schema_linking_retrieval/lite_sql_schema_linking_correction.md)
  - Focus: execution-guided self-correction built directly into smaller fine-tuned models.
  - Beacon use: models can learn to recover from database syntax and execution errors during retry.

- [Arctic-Text2SQL-R1: Simple Rewards, Strong Reasoning](../3_prompting_examples_candidates/arctic_text2sql_r1_reasoning.md)
  - Focus: reinforcement learning using execution correctness to develop robust SQL reasoning.
  - Beacon use: highlights execution validation as the primary metric for correctness.

- [RoboPhD: Self-Improving Text-to-SQL](../3_prompting_examples_candidates/robophd_agent_evolution.md)
  - Focus: closed-loop agent prompt evolution and performance-based ELO selection.
  - Beacon use: outlines using execution feedback to improve the prompts dynamically.

- [SOMA-SQL: Resolving Multi-Source Ambiguity](../1_semantic_metadata_value_grounding/soma_sql_ambiguity_probing.md)
  - Focus: candidate disagreement exposure and safe targeted execution probing.
  - Beacon use: supports running diagnostic check queries on database instances during validation.


