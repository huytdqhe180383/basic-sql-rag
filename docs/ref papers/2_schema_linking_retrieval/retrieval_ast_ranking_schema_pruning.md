# Improving Retrieval-augmented Text-to-SQL with AST-based Ranking and Schema Pruning

Source: https://arxiv.org/pdf/2407.03227
Local PDF: `retrieval_ast_ranking_schema_pruning.pdf`

## Why this matters for Beacon

It informs Beacon's example retrieval and schema pruning, especially the need to retrieve examples that match query structure.

## Key points

- The paper improves retrieval-augmented Text-to-SQL by ranking demonstrations using SQL AST similarity.
- It combines example retrieval with schema and value selection.
- It studies both monolingual and cross-lingual settings.
- The core claim is that example similarity should reflect SQL structure, not only question text.

## Contributions and achievements

- Introduces AST-based ranking for selecting useful few-shot examples.
- Shows that schema/value selection and example selection can support each other.
- Provides evidence that retrieval quality matters even with strong LLMs.

## Evaluation

- Benchmarks used: Spider dev, Spider variants (Spider-DK, Spider-Realistic, Spider-Syn), and CSpider.
- Reported scores: on Spider dev, GPT-4 with ASTRES using Graphix-T5 reached 86.6% EX and 77.3% EM. With GPT-3.5 and Graphix-T5, AST + schema/value selection reached 83.0% EX and 68.8% EM.
- Efficiency result: the paper reports filtering out more than 70% of the original schema on average while improving accuracy.
- Metrics: Execution Accuracy (EX), Exact Match (EM), and schema-shortening/recall measures.

## Problems it solves

- Irrelevant examples in prompt context.
- Example retrieval based only on surface wording.
- Missing value evidence during schema pruning.

## Practical takeaways for Beacon

- Enrich example docs with tables, columns, filters, metrics, and time grain before any AST work.
- If SQL examples are available, rank examples by overlapping tables and intent signals, not only text match.
- AST ranking is future work after simple example metadata fails.
