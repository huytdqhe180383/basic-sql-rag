# NL2SQL-BUGs: A Benchmark for Detecting Semantic Errors in NL2SQL Translation

Source: https://arxiv.org/pdf/2503.11984
Local PDF: `nl2sql_bugs_semantic_errors.pdf`

## Why this matters for Beacon

Several local failures were semantic errors even when SQL executed successfully.

## Key points

- The paper argues that detecting common NL2SQL errors is separate from generating correct SQL.
- It focuses on semantically incorrect SQL translations produced by modern systems.
- It builds a benchmark around error detection rather than only exact-match or execution accuracy.
- A wrong answer can be worse than a visible failure.

## Contributions and achievements

- Defines a benchmark for semantic error detection in NL2SQL.
- Collects and categorizes common bug patterns.
- Pushes evaluation toward reliability and debugging, not only generation scores.

## Evaluation

- Benchmarks used: Spider and BIRD, converted into an NL2SQL semantic-error detection benchmark.
- Reported scores: the paper reports around 75% average detection accuracy for distinguishing correct vs incorrect SQL, with about 70% accuracy on the harder BIRD benchmark. It also notes that identifying the specific error type remains much harder, often below 50% accuracy.
- Metrics: semantic error detection accuracy and error-type classification accuracy.

## Problems it solves

- Silent wrong SQL.
- Lack of structured error categories.
- No focused test suite for semantic validation.

## Practical takeaways for Beacon

- Build a small bug taxonomy: missed table, wrong grain, wrong join, wrong filter, wrong aggregation.
- The retry reviewer should mention the suspected bug type in `reason`.
- Tests should include successful execution with reviewer rejection.
