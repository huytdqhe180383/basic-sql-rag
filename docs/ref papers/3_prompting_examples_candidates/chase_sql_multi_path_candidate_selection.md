# CHASE-SQL: Multi-Path Reasoning and Candidate Selection

Source: https://arxiv.org/pdf/2410.01943
Local PDF: `chase_sql_multi_path_candidate_selection.pdf`

## Why this matters for Beacon

It is a stronger but heavier version of retry, candidate generation, and result checking.

## Key points

- CHASE-SQL generates multiple SQL candidates through different reasoning paths.
- It uses divide-and-conquer, execution-plan reasoning, and synthetic examples to diversify candidates.
- It then uses preference-optimized selection to choose among candidates.
- The design spends more test-time compute to improve difficult Text-to-SQL cases.

## Contributions and achievements

- Combines multiple generation strategies instead of relying on one SQL attempt.
- Separates candidate generation from candidate selection.
- Shows the value of diverse candidates for complex questions.

## Evaluation

- Benchmarks used: BIRD and Spider.
- Reported scores: CHASE-SQL with Gemini 1.5 reported 73.01% EX on BIRD dev and 73.0% EX on BIRD test. On Spider test, it reported 87.6% EX.
- Metrics: Execution Accuracy (EX).

## Problems it solves

- Single-shot SQL generation failures.
- Near-identical retries that do not explore alternatives.
- No principled candidate selection.

## Practical takeaways for Beacon

- Beacon should not copy the full multi-agent design now.
- The useful small idea is diversity: retry prompts should include concrete feedback so the next attempt changes meaningfully.
- If the 3-attempt loop still fails often, candidate selection may become worth considering.
