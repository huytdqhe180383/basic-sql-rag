# OpenSearch-SQL: Dynamic Few-shot and Consistency Alignment

Source: https://arxiv.org/pdf/2502.14913
Local PDF: `opensearch_sql_dynamic_few_shot_consistency.pdf`

## Why this matters for Beacon

It is relevant to example retrieval and multi-step workflow, though the full system is more complex than Beacon needs.

## Key points

- OpenSearch-SQL uses preprocessing, extraction, generation, refinement, and alignment modules.
- It dynamically selects few-shot examples and aligns information across agents to reduce hallucination and information loss.
- It uses an SQL-like intermediate representation and self-taught Query-CoT-SQL examples.
- It reports strong BIRD benchmark performance.

## Contributions and achievements

- Shows that dynamic few-shot retrieval can materially help Text-to-SQL.
- Introduces consistency alignment to keep stages from drifting.
- Demonstrates a strong modular system for benchmark performance.

## Evaluation

- Benchmarks used: BIRD and Spider.
- Reported scores: OpenSearch-SQL reported 69.3% EX on BIRD dev, 72.28% EX on BIRD test, and 69.36 R-VES on BIRD test.
- Metrics: Execution Accuracy (EX) and Reward-based Valid Efficiency Score (R-VES).

## Problems it solves

- Information loss between pipeline stages.
- Hallucination from weak intermediate context.
- Static examples that do not match the question.

## Practical takeaways for Beacon

- Keep retrieved context stable and visible through SQL generation and review.
- Do not add an intermediate SQL-like language now.
- Example retrieval should stay plain dictionaries/lists with useful metadata.
