# Automatic Metadata Extraction for Text-to-SQL

Source: https://arxiv.org/abs/2505.19988
Local PDF: `Automatic_Metadata_Extraction_for_Text-to-SQL.pdf`

## Why this matters for Beacon

This is directly relevant because Beacon's semantic layer is now built around table descriptions, column profiles, sample values, sample rows, and examples.

## Key points

- The paper argues that practical Text-to-SQL depends heavily on understanding database contents.
- It studies automatic metadata extraction when human-authored metadata is missing or expensive.
- The extraction signals include data profiling, query log analysis, and SQL-to-text generation with an LLM.
- It treats metadata as operational context for SQL generation, not as a separate catalog product.

## Contributions and achievements

- Provides a practical taxonomy of metadata signals that can be generated from the database itself.
- Shows that profiling and query history can fill gaps that plain schema names cannot cover.
- Connects metadata quality to Text-to-SQL performance on realistic benchmarks.

## Evaluation

- Benchmarks used: BIRD, with dev/minidev experiments and BIRD test leaderboard submissions.
- Reported scores: without oracle hints, the system reported 67.41% on BIRD test versus 57.13% for the next best non-oracle submission at the time. With oracle hints, it reported 77.14 and the #1 leaderboard position at the time of writing.
- Metrics: BIRD score / execution-oriented leaderboard score.

## Problems it solves

- Missing or weak table and column descriptions.
- Schema names that do not expose business meaning.
- Lack of value-level context for disambiguating user language.

## Practical takeaways for Beacon

- 1 time offline auto-profiling 
- Use SQLglot for validation
- Check anti-patterns for logical errors
- Use minimal profiles for sql scalping (no reasoning), maximal profiles for final prompt gen
- Majority voting (3 output) by changing seed, order
- For categorical columns: Fetch a list of frequent keywords. Then use exact/fuzzy match to see whether a word in the question matches with any column's list. 
