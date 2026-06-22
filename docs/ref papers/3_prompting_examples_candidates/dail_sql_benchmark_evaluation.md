# DAIL-SQL: Text-to-SQL Empowered by Large Language Models

Source: https://arxiv.org/pdf/2308.15363
Local PDF: `dail_sql_benchmark_evaluation.pdf`

## Why this matters for Beacon

It gives practical evidence for prompt design and example selection choices in LLM-based Text-to-SQL.

## Key points

- The paper evaluates question representation, example selection, and example organization.
- It proposes DAIL-SQL as an integrated prompting solution.
- It reports strong Spider execution accuracy at the time of publication.
- The practical takeaway is that demonstration selection and prompt layout matter a lot.

## Contributions and achievements

- Provides empirical guidance for prompt engineering instead of relying only on intuition.
- Shows how selected examples can improve zero/few-shot SQL generation.
- Separates representation, selection, and organization as tunable prompt components.

## Evaluation

- Benchmarks used: Spider, Spider-Realistic, and BIRD.
- Reported scores: DAIL-SQL reported 86.6% execution accuracy on Spider, refreshing the Spider leaderboard at the time. On BIRD, it outperformed DIN-SQL by 4.4 percentage points on dev and 1.8 percentage points on test in execution accuracy.
- Metrics: Execution Accuracy (EX).

## Problems it solves

- Weak prompts that bury useful schema context.
- Random or poorly organized examples.
- Lack of benchmarked prompt design decisions.

## Practical takeaways for Beacon

- Keep prompt context ordered: question, relevant schema, profiles/sample rows, examples, then SQL instruction.
- Examples should be short and structurally relevant.
- Prompt experiments should be tied to the local test cases, not abstract style preferences.
