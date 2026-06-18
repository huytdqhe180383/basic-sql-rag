# Sphinteract: Resolving Ambiguities in NL2SQL Through User Interaction

Source: https://www.vldb.org/pvldb/vol18/p1145-zhao.pdf
Local PDF: `sphinteract_user_interaction_ambiguities.pdf`

## Why this matters for Beacon

It is a future direction for Beacon when a question has multiple plausible interpretations.

## Key points

- Sphinteract resolves NL2SQL ambiguity through minimal user feedback.
- It introduces a Summarize, Review, Ask paradigm for deciding what to clarify.
- It focuses on matching SQL answers to user intent rather than only producing syntactically valid SQL.
- The design tries to ask targeted questions instead of burdening the user.

## Contributions and achievements

- Defines an interaction pattern for ambiguity resolution.
- Shows how LLMs can produce better SQL with small amounts of user feedback.
- Connects explanation and clarification in the generation loop.

## Evaluation

- Benchmarks used: KaggleDBQA and BIRD, plus a user study with 11 participants.
- Reported scores: using at most four user interactions, Sphinteract improved execution accuracy by 42.3 percentage points on KaggleDBQA and 26.86 percentage points on BIRD in the zero-shot setting. In the few-shot setting, improvements were 30.03 percentage points on KaggleDBQA and 32 percentage points on BIRD.
- Metrics: Execution Accuracy (EX) and interaction-limited improvement.

## Problems it solves

- Ambiguous natural language questions.
- Multiple valid SQL interpretations.
- Insufficient context to infer user intent confidently.

## Practical takeaways for Beacon

- Beacon does not need this full interaction loop yet.
- Useful future pattern: summarize inferred intent, review uncertainty, ask one concrete question.
- For now, keep failures readable and direct.
