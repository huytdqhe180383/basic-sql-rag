# RoboPhD: Self-Improving Text-to-SQL Through Autonomous Agent Evolution

Source: https://arxiv.org/abs/2601.01126
Local PDF: `robophd_agent_evolution.pdf`

## Why this matters for Beacon

Beacon's pipeline represents a multi-step agent workflow. RoboPhD shows that agent behaviors (such as database analysis, prompt selection, and error recovery) can be evolved and optimized autonomously, providing a template for building adaptive database agents.

## Key points

- Focuses on **autonomous evolution** of LLM agents for database querying.
- Uses a closed-loop evolutionary process involving two coordinated agent roles:
  - **SQL Generation Agent:** Performs database analysis, retrieves schema elements, and writes the query.
  - **Evolution Agent:** Reviews the performance of the generator on a validation set and designs improved prompts and instructions.
- Implements an **ELO-based selection mechanism** to track version performance and filter out weak strategies.
- Enables **"skip-a-tier" deployment** where evolved smaller models (like Claude Haiku) outperform naive larger models (like Claude Sonnet).

## Contributions and achievements

- Eliminates manual prompt engineering by allowing agents to discover their own optimal instructions.
- Discovers complex database analysis strategies autonomously (e.g., size-adaptive profiling where the model adjusts how deep it inspects a database based on schema size).
- Outperforms naive pipelines on standard benchmarks.

## Evaluation

- Benchmarks used: BIRD, DS-1000, ARC-AGI.
- Reported scores:
  - **BIRD test set:** **73.67% Execution Accuracy (EX)** (using evolved agents).
  - **BIRD dev set:** **71.30% Execution Accuracy (EX)**.
- Metrics: Execution Accuracy (EX), optimization budget efficiency.

## Problems it solves

- Tedious, time-consuming manual prompt tuning.
- Fixed-size database analysis that fails on very large or very small schemas.
- Brittle instructions that do not generalize across different database structures.

## Practical takeaways for Beacon

- The system should be adaptive: the amount of schema context and detail included in the prompt should adjust based on database size (size-adaptive analysis).
- Store historical pipeline attempts and errors, as they provide critical feedback for self-correction.
- Structure agent prompts to perform analysis of the database before attempting to construct the SQL query.
