# Data Ambiguity Strikes Back: How Documentation Improves GPT's Text-to-SQL

Source: https://openreview.net/pdf?id=FflKTuIRTD
Local PDF: `data_ambiguity_documentation_text_to_sql.pdf`

## Why this matters for Beacon

Beacon questions often depend on domain value meaning, data coverage, and data granularity, not just table names.

## Key points

- The paper distinguishes query ambiguity from data ambiguity.
- It identifies value consistency, data coverage, and data granularity as common sources of Text-to-SQL errors.
- It shows that documentation written for humans can also improve GPT Text-to-SQL performance.
- It reports a large improvement when useful data documentation is provided.

## Contributions and achievements

- Moves attention from only parsing language to documenting data semantics.
- Gives concrete ambiguity categories that affect SQL generation.
- Demonstrates that lightweight documentation can resolve many errors.

## Evaluation

- Benchmarks used: KaggleDBQA, a real-world Text-to-SQL benchmark with 8 Kaggle databases, 18 tables, and 272 natural language queries.
- Reported scores: adding documentation for data ambiguity improved GPT-4 Text-to-SQL performance by 28.9%.
- Metrics: task performance on KaggleDBQA Text-to-SQL questions; the paper reports the result as an improvement from documentation rather than as a single leaderboard score.

## Problems it solves

- Business terms with unclear data representation.
- Values that are inconsistent or unexpectedly granular.
- Questions that require knowing what the data does and does not cover.

## Practical takeaways for Beacon

- Column profiles should include value examples and top categories, not only types.
- Semantic docs should explain granularity, such as order-level vs item-level vs inventory snapshot.
- When tests fail, ask whether the missing context is data documentation rather than SQL ability.
- Adding data coverage & granularity to each table
- Do an offline value consistency profiling
- Prune the unecessary columns in retrieved tables (by giving only the name + data type)
