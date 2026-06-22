# The Death of Schema Linking? Text-to-SQL in the Age of Well-Reasoned Language Models

Source: https://arxiv.org/pdf/2408.07702
Local PDF: `death_of_schema_linking.pdf`

## Why this matters for Beacon

It is a useful caution against over-pruning Beacon context when the database is small enough for the model to handle broader schema.

## Key points

- The paper questions whether aggressive schema linking is still necessary for modern LLMs when schemas fit in context.
- It finds that newer models can often ignore irrelevant schema better than older models.
- It argues that filtering out required schema is more damaging than including some irrelevant schema.
- It prefers augmentation, selection, and correction over hard exclusion in some settings.

## Contributions and achievements

- Reframes schema linking as a risk tradeoff rather than a required preprocessing step.
- Shows that recall loss from pruning can dominate context-size savings.
- Provides support for softer retrieval and retry designs.

## Evaluation

- Benchmarks used: BIRD.
- Reported scores: the paper reports 71.83% accuracy on the BIRD benchmark, ranking first at the time discussed in the paper.
- Metrics: BIRD execution accuracy / leaderboard accuracy.

## Problems it solves

- Hard schema pruning that removes required tables.
- Validator lock-in caused by incomplete retrieval.
- Over-engineered retrieval on small or medium schemas.

## Practical takeaways for Beacon

- Keep retrieval simple and recall-friendly for now.
- For this small project, include extra nearby tables when uncertainty is high rather than rejecting SQL too early.
- Use validation for safety, not as a rigid schema-linking oracle.
