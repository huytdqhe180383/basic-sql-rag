# Arctic-Text2SQL-R1: Simple Rewards, Strong Reasoning in Text-to-SQL

Source: https://arxiv.org/abs/2505.20315
Local PDF: `arctic_text2sql_r1_reasoning.pdf`

## Why this matters for Beacon

Beacon's pipeline relies on generating correct SQL and reviewing it before execution. Arctic-Text2SQL-R1 proves that training models with simple, execution-correctness rewards (rather than complex, shaped rewards or intermediate syntax guides) produces models with superior SQL reasoning and self-correction capabilities.

## Key points

- Focuses on training models to generate executable, semantically correct SQL queries using **Reinforcement Learning (RL)**.
- Uses a **simple, lightweight reward signal** based *only* on execution correctness (checking if the executed result matches the gold database output).
- Bypasses intermediate supervision (like AST matching or skeleton parsing) to let the model naturally develop reasoning paths.
- Demonstrates strong generalization across different database engines (SQLite, Snowflake, PostgreSQL).

## Contributions and achievements

- Proves that execution correctness is a sufficient and highly effective reward for RL training in Text-to-SQL.
- Shows that models trained with simple execution rewards naturally learn how to perform schema linking, joins, and self-correction.
- Achieved top ranks on the BIRD leaderboard at the time of its release.

## Evaluation

- Benchmarks used: BIRD dev/test, Spider-test.
- Reported scores (for the 7B parameter version):
  - **BIRD-dev:** **68.9% Execution Accuracy (EX)**.
  - **BIRD-test:** **68.5% Execution Accuracy (EX)**.
  - **Spider-test:** **88.8% Execution Accuracy (EX)**.
- Scaling result: Higher parameter versions (such as the 32B model) achieved scores reaching **71.8% to 73.9% EX** on BIRD depending on the evaluation setup.
- Metrics: Execution Accuracy (EX).

## Problems it solves

- Brittle, over-engineered reward functions in Text-to-SQL training.
- Models generating SQL that is syntactically valid but semantically incorrect.
- Lack of self-correction capabilities when execution fails.

## Practical takeaways for Beacon

- Use execution correctness as the ultimate validation gate. If a generated SQL runs successfully and returns data, it has a high probability of being correct.
- If execution returns an error, feed the exact error back to the model; models trained with execution feedback are highly capable of fixing themselves.
- Keep the prompts simple and let the model do the reasoning rather than constraining it with overly rigid structural instructions.
