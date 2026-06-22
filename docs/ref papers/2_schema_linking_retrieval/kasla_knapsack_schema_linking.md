# KaSLA: Knapsack Optimization-based Schema Linking

Source: https://arxiv.org/pdf/2502.12911
Local PDF: `kasla_knapsack_schema_linking.pdf`

## Why this matters for Beacon

Beacon needs high recall in schema retrieval while keeping prompt context compact.

## Key points

- The paper argues that ordinary precision and recall do not fully capture schema linking failures for Text-to-SQL.
- It introduces Recall+ and Precision+ to better account for missing relevant schema elements.
- KaSLA formulates table and column selection as a constrained optimization problem.
- It emphasizes the cost of missing required elements, which matches Beacon validator lock-in failures.

## Contributions and achievements

- Provides a useful way to think about schema linking as recall-first under a context budget.
- Proposes hierarchical linking over tables and columns.
- Shows that better schema linking can improve existing Text-to-SQL systems without replacing the generator.

## Evaluation

- Benchmarks used: BIRD-dev and Spider-dev.
- Reported scores: as a plug-in schema linker, KaSLA improved CodeS-15B on BIRD-dev from 57.63% EX / 63.22% VES to 60.17% EX / 64.52% VES. On Spider-dev, the same setup reported 84.82% EX / 84.46% VES.
- Schema-linking metrics: on BIRD-dev, KaSLA reported 99.15 table Recall+ and 85.14 column Recall+.
- Metrics: Execution Accuracy (EX), Valid Efficiency Score (VES), Recall+, Precision+, and F1+.

## Problems it solves

- Missing required tables or columns.
- Overly large schema context.
- Metrics that hide catastrophic recall errors.

## Practical takeaways for Beacon

- Rank by usefulness but avoid hard-blocking the LLM when retrieval may have missed a table.
- Coverage checks should explain missing likely tables rather than pretending the retrieved set is final truth.
- Use recall-oriented tests: did retrieval include all tables needed for the intended SQL?
