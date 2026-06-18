# DIVER: Dynamic Interactive Value Linking and Evidence Reasoning

Source: https://arxiv.org/pdf/2602.12064
Local PDF: `diver_dynamic_value_linking_evidence_reasoning.pdf`

## Why this matters for Beacon

Beacon failures include value grounding gaps such as Apple Pay, social media, organic search, overstock, and geography terms.

## Key points

- DIVER targets the performance collapse that happens when expert evidence is missing.
- It dynamically links values from the database instead of relying only on static schema linking.
- It uses generated evidence to help the model reason about filters, joins, and business terms.
- The paper reports sizable gains when expert evidence is absent.

## Contributions and achievements

- Frames value linking as an interactive retrieval problem, not just a static prompt field.
- Adds evidence reasoning so retrieved values can guide SQL construction.
- Demonstrates that value evidence can compensate for missing human hints.

## Evaluation

- Benchmarks used: Text-to-SQL benchmarks with execution-based metrics, centered on robustness when expert evidence is missing.
- Reported scores: DIVER improved existing Text-to-SQL models by up to 10.82 percentage points in Execution Accuracy (EX) and 16.09 percentage points in Valid Efficiency Score (VES).
- Metrics: EX and VES.

## Problems it solves

- User terms that are values rather than schema names.
- Questions where the right table is only implied by a value.
- Fragile keyword rules that miss synonyms or surface forms.

## Practical takeaways for Beacon

- Add simple value lookup before SQL generation: search compact sample values and top categorical values for terms in the question.
- If a value is found in a column, add that table and column to retrieval context.
- Keep it small: exact and fuzzy matching over semantic profiles is enough for the next pass.
