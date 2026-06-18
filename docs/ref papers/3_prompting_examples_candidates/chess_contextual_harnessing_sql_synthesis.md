# CHESS: Contextual Harnessing for Efficient SQL Synthesis

Source: https://arxiv.org/pdf/2405.16755
Local PDF: `chess_contextual_harnessing_sql_synthesis.pdf`

## Why this matters for Beacon

It maps closely to Beacon concerns: retrieval, schema selection, candidate SQL, and validation, but at a heavier scale.

## Key points

- CHESS uses specialized agents for information retrieval, schema selection, candidate generation, and unit testing.
- It targets large catalogs, database values, SQL validity, and natural language ambiguity.
- It validates candidates using LLM-based natural language unit tests.
- It is a high-performing but more complex architecture.

## Contributions and achievements

- Provides a clear decomposition of Text-to-SQL system responsibilities.
- Highlights value retrieval and schema pruning as separate problems.
- Uses test-like validation to improve confidence in generated SQL.

## Evaluation

- Benchmarks used: BIRD and Spider.
- Reported scores: CHESS(IR,CG,UT) reported 68.31% EX on BIRD dev and 71.10% EX on BIRD test. On Spider test, CHESS(IR,SS,CG) reported 87.2% EX.
- Efficiency result: the paper reports being within about 2 percentage points of the leading proprietary method on BIRD test while using about 83% fewer LLM calls.
- Metrics: Execution Accuracy (EX).

## Problems it solves

- Large schema and value spaces.
- Ambiguous user intent.
- Need for candidate validation beyond syntax.

## Practical takeaways for Beacon

- Use CHESS as a map, not a blueprint: Beacon should keep one simple pipeline file and focused helper modules.
- The most useful part for now is the validation mindset: verify generated SQL against the question and result.
- Avoid multi-agent architecture until simple retrieval and retry fail on concrete cases.
