# TrustSQL: Benchmarking Text-to-SQL Reliability with Penalty-Based Scoring

Source: https://arxiv.org/pdf/2403.15879
Local PDF: `trustsql_reliability_penalty_scoring.pdf`

## Why this matters for Beacon

Beacon must distinguish answerable questions from infeasible or off-domain ones.

## Key points

- TrustSQL evaluates reliability, not only correctness on answerable questions.
- It considers feasible and infeasible questions and penalizes unsafe or overconfident behavior.
- It supports abstention as an important behavior for trustworthy systems.
- It is useful for thinking about failure handling in NL-to-SQL tools.

## Contributions and achievements

- Introduces penalty-based scoring for reliability-oriented Text-to-SQL evaluation.
- Encourages systems to avoid hallucinated SQL on infeasible requests.
- Provides a benchmark framing for deployment safety.

## Evaluation

- Benchmarks used: TrustSQL, built from ATIS, Advising, EHRSQL, and Spider with feasible and infeasible questions.
- Dataset scores/statistics: the test sets contain equal answerable and unanswerable questions. For Spider, the benchmark uses 527 feasible test questions and 527 infeasible test questions; the full Spider-derived TrustSQL set contains 8,561 questions.
- Reported model scores: under the lenient phi_0 reliability score, API pipelines reached up to 88.9 on ATIS, 88.7 on Advising, 85.3 on EHRSQL, and 75.0 on Spider depending on the pipeline. Under stricter penalties, many methods received large negative scores, showing that ordinary high accuracy does not imply reliability.
- Metrics: penalty-based reliability score phi_c with c = 0, 10, and N.

## Problems it solves

- Overconfident generated SQL for impossible questions.
- Evaluation metrics that reward only answerable benchmark cases.
- No cost assigned to misleading answers.

## Practical takeaways for Beacon

- Keep the off-domain failure path in the pipeline; do not hide it behind retries.
- Use small negative tests where no relevant table should be retrieved.
- Final answers should be honest when data cannot answer the question.
