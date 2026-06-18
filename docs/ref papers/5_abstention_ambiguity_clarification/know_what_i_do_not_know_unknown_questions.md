# Know What I Don't Know: Handling Ambiguous and Unanswerable Questions for Text-to-SQL

Source: https://aclanthology.org/2023.findings-acl.352.pdf
Local PDF: `know_what_i_do_not_know_unknown_questions.pdf`

## Why this matters for Beacon

Beacon should not generate SQL when the question is ambiguous, unsupported, or unanswerable from the available schema.

## Key points

- The paper studies ambiguous and unanswerable Text-to-SQL questions.
- It categorizes common problematic questions and their causes.
- It proposes counterfactual example generation to help models learn when not to answer directly.
- It makes the case that Text-to-SQL systems need an uncertainty/failure mode.

## Contributions and achievements

- Defines categories for problematic user questions.
- Builds training/evaluation data for ambiguous and unanswerable cases.
- Shows that handling unknowns is a separate capability from SQL generation.

## Evaluation

- Benchmarks used: NOISY SP, generated from WikiSQL and WTQ, plus real-world ambiguous/unanswerable examples.
- Dataset size: NOISY SP contains 4,760 ambiguous and 10,673 unanswerable training examples, plus 2,332 ambiguous and 2,560 unanswerable test examples.
- Reported scores: DTE+BERT-large reached sequence-labeling accuracy of 89.4 on COL, 95.7 on VAL, 83.2 on AMB, 80.3 on UNK, and 92.4 on O. For grounding accuracy, it reached 75.1 on COL, 80.7 on VAL, and 82.4 on AMB.
- Metrics: sequence-labeling accuracy and grounding accuracy.

## Problems it solves

- Questions with no valid SQL answer.
- Questions missing required constraints or definitions.
- Systems that always return a plausible query.

## Practical takeaways for Beacon

- Coverage assessment should return a readable failure when no relevant schema is found.
- Add local tests for unsupported concepts and missing business definitions.
- Retry should not try to solve missing schema coverage unless retrieval can expand context.
