# Prompting, Examples, and Candidate Generation

This category covers prompt layout, example retrieval, candidate SQL generation, and heavier multi-path systems that Beacon may borrow from later.

## Papers

- [DAIL-SQL: Text-to-SQL Empowered by Large Language Models](dail_sql_benchmark_evaluation.md)
  - Focus: prompt representation, example selection, and example organization.
  - Beacon use: supports keeping prompt context ordered and examples structurally relevant.

- [OpenSearch-SQL: Dynamic Few-shot and Consistency Alignment](opensearch_sql_dynamic_few_shot_consistency.md)
  - Focus: dynamic few-shot examples and keeping information aligned across pipeline stages.
  - Beacon use: supports keeping retrieved context stable through generation and review.

- [CHASE-SQL: Multi-Path Reasoning and Candidate Selection](chase_sql_multi_path_candidate_selection.md)
  - Focus: generating multiple SQL candidates through different reasoning paths.
  - Beacon use: future reference if the current 3-attempt retry loop needs more candidate diversity.

- [CHESS: Contextual Harnessing for Efficient SQL Synthesis](chess_contextual_harnessing_sql_synthesis.md)
  - Focus: a larger system with retrieval, schema selection, candidate generation, and validation agents.
  - Beacon use: useful as a conceptual map, but too heavy to copy directly.
