# Schema Linking and Retrieval

This category covers how Beacon finds the relevant tables, columns, examples, and values before the LLM writes SQL.

## Papers

- [KaSLA: Knapsack Optimization-based Schema Linking](kasla_knapsack_schema_linking.md)
  - Focus: recall-first schema linking under a context budget.
  - Beacon use: reminds us that missing one required table is worse than including a little extra context.

- [RSL-SQL: Robust Schema Linking in Text-to-SQL Generation](rsl_sql_robust_schema_linking.md)
  - Focus: robust schema linking with contextual augmentation and self-correction.
  - Beacon use: supports soft retrieval expansion when the first pass misses a table.

- [The Death of Schema Linking?](death_of_schema_linking.md)
  - Focus: whether modern LLMs still need aggressive schema pruning.
  - Beacon use: warns against over-pruning small schemas and causing validator lock-in.

- [Improving Retrieval-augmented Text-to-SQL with AST-based Ranking and Schema Pruning](retrieval_ast_ranking_schema_pruning.md)
  - Focus: AST-aware example ranking plus schema/value pruning.
  - Beacon use: supports richer example metadata before any heavy AST machinery.

- [LitE-SQL: Lightweight and Efficient Text-to-SQL](lite_sql_schema_linking_correction.md)
  - Focus: vector-based schema linking and model-level execution-guided self-correction.
  - Beacon use: supports simple vector database index matching for schemas combined with execution feedback loops.

