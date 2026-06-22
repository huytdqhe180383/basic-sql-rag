# Abstention, Ambiguity, and Clarification

This category covers when Beacon should not force an SQL answer: missing schema coverage, unsupported concepts, off-domain questions, or ambiguous user intent.

## Papers

- [Reliable Text-to-SQL with Adaptive Abstention](reliable_text_to_sql_adaptive_abstention.md)
  - Focus: abstaining or asking for help when context is insufficient.
  - Beacon use: supports readable failure behavior before retries become guesswork.

- [TrustSQL: Reliability with Penalty-Based Scoring](trustsql_reliability_penalty_scoring.md)
  - Focus: evaluating feasible and infeasible questions with reliability penalties.
  - Beacon use: supports tests where the right behavior is to refuse or explain missing data.

- [Know What I Don't Know](know_what_i_do_not_know_unknown_questions.md)
  - Focus: categories of ambiguous and unanswerable Text-to-SQL questions.
  - Beacon use: helps design negative tests and coverage failure messages.

- [Sphinteract: Resolving Ambiguities Through User Interaction](sphinteract_user_interaction_ambiguities.md)
  - Focus: minimal user interaction for ambiguous NL2SQL questions.
  - Beacon use: future pattern for asking one targeted clarification question.
