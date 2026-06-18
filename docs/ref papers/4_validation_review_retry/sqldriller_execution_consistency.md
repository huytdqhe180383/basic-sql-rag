# SQLDriller: Validating and Fixing Text-to-SQL with Execution Consistency

Source: https://ipads.se.sjtu.edu.cn/zh/publications/SQLDriller.pdf
Local PDF: `sqldriller_execution_consistency.pdf`

## Why this matters for Beacon

It focuses on detecting semantically wrong SQL, not just syntax errors.

## Key points

- SQLDriller uses execution consistency and counterexample database instances to validate and fix NL-SQL pairs.
- It finds that many benchmark query mappings contain errors.
- It improves multiple Text-to-SQL models after fixing detected issues.
- The main lesson is that passing execution on one database is not proof of semantic correctness.

## Contributions and achievements

- Provides an execution-based way to expose wrong SQL semantics.
- Shows benchmark annotation errors can be substantial.
- Demonstrates that validation and repair can improve downstream model quality.

## Evaluation

- Benchmarks used: Spider and BIRD.
- Reported dataset findings: in 500 sampled training mappings, SQLDriller found 183/500 errors on Spider train (36.6%) and 272/500 errors on BIRD train (54.4%). It also reports 37.7% errors in Spider test mappings and 50.1% in BIRD development mappings.
- Reported scores: SQLDriller improved evaluated Text-to-SQL model accuracy by 3.6 to 13.6 percentage points. Its NL execution micro-benchmark reached up to 91.0% accuracy on Spider-derived instances and 83.2% on BIRD-derived instances.
- Metrics: error rate, model accuracy improvement, and NL execution accuracy.

## Problems it solves

- Executable but semantically incorrect SQL.
- False confidence from one successful run.
- No automated repair feedback.

## Practical takeaways for Beacon

- Keep result review separate from SQL validation: syntax safety and logical correctness are different checks.
- For now, use the LLM reviewer on executed results; counterexample generation is future work.
- Store failed cases as examples after manual correction.
