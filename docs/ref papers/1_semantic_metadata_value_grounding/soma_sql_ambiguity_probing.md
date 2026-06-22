# SOMA-SQL: Resolving Multi-Source Ambiguity in NL-to-SQL via Synthetic Log and Execution Probing

Source: https://arxiv.org/abs/2606.11424
Local PDF: `soma_sql_ambiguity_probing.pdf`

## Why this matters for Beacon

Beacon needs a robust way to handle underspecified questions and ambiguous schema metadata. SOMA-SQL provides a roadmap for using execution probing and synthetic history to resolve ambiguities without requiring human intervention.

## Key points

- Focuses on "multi-source ambiguity" where both the user query and the database schema are unclear or poorly described.
- Introduces an ambiguity-first resolution framework that does not rely on static rules.
- Uses **synthetic query logs** to contextualize and ground schema interpretations based on how tables/columns would realistically be queried.
- Generates multiple candidate SQL queries that represent different interpretations, exposing semantic disagreements.
- Performs **targeted execution probing** on the database (running safe diagnostic queries) to gather factual evidence to select or repair the final SQL.

## Contributions and achievements

- Establishes a systematic way to ground schema elements using synthetic historical logs.
- Combines candidate-based disagreement exposure with active execution probing.
- Demonstrates that active database interaction can autonomously resolve user intent.

## Evaluation

- Benchmarks used: Spider 2.0-Lite, BIRD.
- Reported scores: Achieved a state-of-the-art **72.02% Execution Accuracy (EX)** on the highly challenging **Spider 2.0-Lite** benchmark (using Gemini-2.5-Pro/GPT-4o).
- Improvement: Showed an average improvement of **13.0%** in execution accuracy over existing non-interactive baselines.
- Metrics: Execution Accuracy (EX) and Valid Efficiency Score (VES).

## Problems it solves

- Underspecified user questions that could map to multiple schemas.
- Brittle schema descriptions that lack usage context.
- Silent semantic errors where the generated SQL runs but returns incorrect results due to misinterpretation.

## Practical takeaways for Beacon

- Use sample values and synthetic "queries" as metadata to help the LLM understand how columns are used.
- When ambiguity is detected (e.g., a term matches multiple tables/columns), generate candidate variants and inspect their differences.
- Execution probing (running counts or checking for null values in candidates) can help verify which query is semantically appropriate.
