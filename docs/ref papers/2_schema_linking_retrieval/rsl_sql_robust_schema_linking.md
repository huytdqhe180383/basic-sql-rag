# RSL-SQL: Robust Schema Linking in Text-to-SQL Generation

Source: https://arxiv.org/pdf/2411.00073
Local PDF: `rsl_sql_robust_schema_linking.pdf`

## Why this matters for Beacon

Beacon has schema retrieval failures caused by brittle rules and missing geography, order, inventory, or payment context.

## Key points

- RSL-SQL studies schema linking errors where relevant schema elements are missing or schema structure is disrupted.
- It combines bidirectional linking, contextual augmentation, binary selection, and multi-turn self-correction.
- The paper reports high strict schema-linking recall while reducing the number of input columns.
- It treats linking quality as a first-class component of Text-to-SQL reliability.

## Contributions and achievements

- Separates candidate schema discovery from final schema selection.
- Uses self-correction to recover from linking mistakes.
- Reports strong results on BIRD and Spider with modern LLMs.

## Evaluation

- Benchmarks used: BIRD and Spider.
- Reported scores: with GPT-4o, RSL-SQL reported 67.21% EX and 70.32% VES on BIRD-dev, plus 87.9% EX on Spider test.
- Schema-linking result: the paper reports 94% strict recall while reducing input columns by 83%.
- Metrics: EX, VES, and strict schema-linking recall.

## Problems it solves

- Brittle schema linking.
- False negatives in retrieved tables and columns.
- Context overload from passing too much schema.

## Practical takeaways for Beacon

- Retrieve broadly first, then rank and prune softly.
- Avoid strict validator lock-in based only on first-pass rules.
- If SQL validation says a needed table is outside context, retrieval should be allowed to expand context on retry.
