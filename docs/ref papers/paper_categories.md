# Beacon Paper Categories

The reference folder now keeps 20 papers: 4 papers in each active problem area.

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

## Removed in the pruning pass

These papers were useful but less central, older, or heavier than Beacon needs right now:

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

The blocked few-shot prompt-learning paper is lower priority because DAIL-SQL and OpenSearch-SQL already cover the example-selection area well enough.
