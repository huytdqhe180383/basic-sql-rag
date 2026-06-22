# Abstention, Ambiguity, and Clarification

This category covers when Beacon should not force an SQL answer: missing schema coverage, unsupported concepts, off-domain questions, or ambiguous user intent.

## Papers

- [Reliable Text-to-SQL with Adaptive Abstention](reliable_text_to_sql_adaptive_abstention.md)
  - Focus: abstaining or asking for help when context is insufficient.
  - Beacon use: supports readable failure behavior before retries become guesswork.

- [TrustSQL: Reliability with Penalty-Based Scoring](trustsql_reliability_penalty_scoring.md)
  - Focus: evaluating feasible and infeasible questions with reliability penalties.
  - Beacon use: supports tests where the right behavior is to refuse or explain missing data.

- [SOMA-SQL: Resolving Multi-Source Ambiguity](../1_semantic_metadata_value_grounding/soma_sql_ambiguity_probing.md)
  - Focus: resolving multi-source ambiguity in queries and schemas via synthetic query logs and execution probing.
  - Beacon use: supports techniques to ground schemas with synthetic historical logs and verify intent using safe database checks.

