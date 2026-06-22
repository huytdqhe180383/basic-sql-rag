# E-SQL: Direct Schema Linking via Question Enrichment

Source: https://arxiv.org/pdf/2409.16751
Local PDF: `e_sql_question_enrichment_schema_linking.pdf`

## Why this matters for Beacon

It enriches the user question with tables, columns, values, and candidate predicates before SQL construction.

## Key points

- E-SQL adds schema and value hints directly into the natural language question.
- It uses direct schema linking and candidate predicate augmentation.
- The goal is to make SQL construction see the intended database items explicitly.
- It targets ambiguity in complex schemas and complex SQL structures.

## Contributions and achievements

- Shows a simple interface between retrieval and generation: enrich the question with retrieved evidence.
- Uses candidate predicates as explicit hints for WHERE and JOIN logic.
- Connects value linking to prompt construction.

## Evaluation

- Benchmarks used: BIRD development and test sets.
- Reported scores: E-SQL achieved 66.29% execution accuracy on the BIRD test set. With DeepSeek Coder 7B Instruct 1.5, enriched-question single-prompt generation reached 56.45% execution accuracy on the BIRD development set.
- Metrics: Execution Accuracy (EX).

## Problems it solves

- Questions where the model misses the intended table or filter.
- Ambiguous wording that needs schema/value hints.
- Prompt context that lists schema but does not connect it to question terms.

## Practical takeaways for Beacon

- Add a short `Matched evidence` block in the prompt: question term -> table.column/value.
- Do not overbuild a separate enrichment model; derive hints from retrieval matches.
- This would help cases like Apple Pay -> `orders.payment_method`.
