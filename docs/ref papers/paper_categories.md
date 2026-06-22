# Beacon Paper Categories

The reference folder now keeps 14 high-performing and cost-effective papers (each meeting the evaluation threshold: Spider >= 75%, Spider-Lite >= 55%, BIRD >= 60%), categorized by active problem area. Highly expensive papers (multi-agent, multi-turn loops, huge context overhead) have been filtered out.

## Categories

1. [Semantic Metadata and Value Grounding](1_semantic_metadata_value_grounding/summary.md)
   - Metadata, profiles, sample values, sample rows, data ambiguity, and value linking.

2. [Schema Linking and Retrieval](2_schema_linking_retrieval/summary.md)
   - Table/column retrieval, schema pruning, recall-first linking, and example-aware retrieval.

3. [Prompting, Examples, and Candidate Generation](3_prompting_examples_candidates/summary.md)
   - Prompt layout, dynamic examples, multi-path SQL candidates, and larger pipeline maps.

4. [SQL Validation, Result Review, and Retry](4_validation_review_retry/summary.md)
   - Executed-result review, semantic SQL errors, execution consistency, and retry feedback.

5. [Abstention, Ambiguity, and Clarification](5_abstention_ambiguity_clarification/summary.md)
   - Off-domain questions, insufficient schema coverage, ambiguity, abstention, and user clarification.

## Removed in the pruning pass (Failed Evaluation Threshold or High Cost)

These papers did not meet the evaluation criteria, did not report standard generation metrics, or required excessive API calls/context:

- **High Cost / Multi-Agent / Multi-Turn:**
  - `diver_dynamic_value_linking_evidence_reasoning.*` (Expensive Thought-Verify-Refine multi-turn DB exploration loop)
  - `rsl_sql_robust_schema_linking.*` (Expensive multi-turn self-correction loop)
  - `opensearch_sql_dynamic_few_shot_consistency.*` (Expensive multi-agent consistency alignment)
  - `chase_sql_multi_path_candidate_selection.*` (High test-time compute multi-path candidates)
  - `chess_contextual_harnessing_sql_synthesis.*` (Heavy multi-agent architecture with retrieval, selection, generation, testing agents)
  - `flex_sql_execution_exploration.*` (Multi-turn dynamic database exploration and plan repair)

- **Failed Evaluation Threshold (<75% Spider / <55% Spider-Lite / <60% BIRD):**
  - `data_ambiguity_documentation_text_to_sql.*` (KaggleDBQA focus, no BIRD/Spider scores)
  - `nl2sql_bugs_semantic_errors.*` (Diagnostic error detection benchmark, no standard generation scores >= threshold)
  - `sqldriller_execution_consistency.*` (Diagnostic validation benchmark, no standard generation scores >= threshold)
  - `know_what_i_do_not_know_unknown_questions.*` (WTQ/WikiSQL focus on unanswerable queries, no standard generation scores >= threshold)
  - `sphinteract_user_interaction_ambiguities.*` (Interaction-based improvement, absolute scores below thresholds)

- **Previously Pruned:**
  - `automatic_database_description_generation.*`
  - `resdsql_schema_linking_skeleton_parsing.*`
  - `in_context_rl_rag_text_to_sql.*`
  - `din_sql_decomposed_self_correction.*`
  - `i_need_help_user_support.*`
  - `text_to_sql_calibration.*`
  - `agentsm_semantic_memory_agentic_text_to_sql.*`

## Manual download candidates

These blocked papers are still worth considering if you can download them manually:

- SNAILS: likely useful for schema naming and synonym problems.
- Generating Succinct Descriptions of Database Schemata: likely useful for compact schema prompt context.
- AID-SQL: likely useful for adaptive retrieval and difficulty-aware prompting.


