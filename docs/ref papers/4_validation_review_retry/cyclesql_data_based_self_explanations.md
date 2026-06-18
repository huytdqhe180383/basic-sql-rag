# CycleSQL: Data-Based Self-Explanations for Text-to-SQL

Source: https://arxiv.org/pdf/2411.02948
Local PDF: `cyclesql_data_based_self_explanations.pdf`

## Why this matters for Beacon

Beacon now has a retry loop where the model reviews executed SQL results before answering.

## Key points

- CycleSQL validates Text-to-SQL outputs using data-grounded natural language explanations of query results.
- It creates a feedback loop where result explanations help judge whether SQL matches the question.
- It is plug-and-play with existing Text-to-SQL models.
- Reported results improve RESDSQL performance on Spider validation and test sets.

## Contributions and achievements

- Introduces data-based self-explanations as a validation signal.
- Shows that result interpretation can catch errors beyond SQL syntax.
- Improves transparency by explaining what the SQL result means.

## Evaluation

- Benchmarks used: Spider validation/test, Spider-Realistic, Spider-Syn, Spider-DK, and ScienceBenchmark.
- Reported scores: applying CycleSQL to RESDSQL reached 82.0% translation accuracy on Spider validation (+2.6) and 81.6% on Spider test (+3.2).
- Metrics: Exact Match (EM), Execution Accuracy (EX), Test Suite Accuracy (TS), and benchmark-specific execution metrics.

## Problems it solves

- SQL that executes but answers the wrong question.
- Lack of semantic validation after execution.
- Opaque final answers with no link to actual query results.

## Practical takeaways for Beacon

- Retry review should include result samples and ask whether they answer the exact section question.
- A future improvement could ask the model to summarize result meaning before deciding satisfaction.
- Keep the current version simple: JSON `satisfied`, `reason`, and `retry_instructions` is enough.
