# Reliable Text-to-SQL with Adaptive Abstention

Source: https://arxiv.org/pdf/2501.10858
Local PDF: `reliable_text_to_sql_adaptive_abstention.pdf`

## Why this matters for Beacon

Beacon needs readable failure behavior when schema coverage is missing or the question is ambiguous.

## Key points

- The paper introduces a framework that can abstain or ask for human input when context is insufficient.
- It focuses on schema linking as a critical reliability point.
- It uses branching-point prediction to detect where generation may go wrong.
- The central idea is that reliable systems should not always force an SQL answer.

## Contributions and achievements

- Adds abstention and human-in-the-loop mechanisms to Text-to-SQL.
- Treats ambiguity and insufficient context as first-class outcomes.
- Connects schema linking confidence to answer reliability.

## Evaluation

- Benchmarks used: BIRD, Spider-dev, and Spider-test.
- Reported schema-linking scores: mBPP-Abstention reported 98.89% table EM and 97.38% column EM on BIRD; 99.86% table EM and 97.73% column EM on Spider-dev; and 99.67% table EM and 97.52% column EM on Spider-test.
- Downstream SQL scores: with RTS schema, DeepSeek-7B reported 64.72% EX on BIRD, 88.90% on Spider-dev, and 88.20% on Spider-test. CodeS-15B with RTS schema reported 65.19% EX on BIRD, 89.10% on Spider-dev, and 88.68% on Spider-test.
- Metrics: schema-linking Exact Match (EM), TAR/FAR abstention measures, and Execution Accuracy (EX).

## Problems it solves

- Forced answers for off-domain questions.
- Ambiguous questions with multiple plausible SQL interpretations.
- No confidence-aware failure path.

## Practical takeaways for Beacon

- Preserve readable failure messages instead of over-retrying missing schema coverage.
- If coverage is clearly insufficient, ask for clarification or state the missing context.
- A later version could add confidence to coverage assessment.
