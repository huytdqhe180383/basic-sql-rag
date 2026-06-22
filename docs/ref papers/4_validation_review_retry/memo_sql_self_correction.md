# Memo-SQL: Structured Decomposition and Experience-Driven Self-Correction

Source: https://www.arxiv.org/pdf/2601.10011
Local PDF: `memo_sql_self_correction.pdf`

## Why this matters for Beacon

It is relevant to retry memory because it uses prior error-fix experience to guide self-correction.

## Key points

- Memo-SQL argues that correct examples alone miss useful signals from historical mistakes and fixes.
- It uses structured decomposition strategies to produce more diverse reasoning paths.
- It builds experience-aware self-correction from error-fix pairs.
- It is training-free but uses more machinery than Beacon currently needs.

## Contributions and achievements

- Treats failures as reusable experience, not just discarded attempts.
- Separates decomposition strategies to improve candidate diversity.
- Connects memory and self-correction in Text-to-SQL.

## Evaluation

- Benchmarks used: BIRD dev, BIRD dev-new, Spider dev, and CHESS-SDS.
- Reported scores: Memo-SQL with Qwen3-Coder-30B-A3B reported 67.6% EX on BIRD dev and 68.5% EX on BIRD dev-new. On Spider dev, it reported 86.5% EX. On CHESS-SDS with Qwen2.5-Coder-32B, it reached 57.6% EX while using far fewer tokens and less latency than Alpha-SQL.
- Metrics: Execution Accuracy (EX), token count, and latency.

## Problems it solves

- Retries that repeat the same mistake.
- Lack of learning from previous errors.
- Accuracy/efficiency tradeoffs in test-time scaling.

## Practical takeaways for Beacon

- Beacon should not persist cross-session memory yet, per current design.
- The lightweight analogue is curated examples derived from fixed failures.
- Within a single request, the message history should include all attempts and feedback.
