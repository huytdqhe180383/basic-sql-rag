# LitE-SQL: A Lightweight and Efficient Text-to-SQL Framework with Vector-based Schema Linking and Execution-Guided Self-Correction

Source: https://arxiv.org/abs/2510.09014
Local PDF: `lite_sql_schema_linking_correction.pdf`

## Why this matters for Beacon

Beacon needs high accuracy in schema linking and query repair while maintaining lightweight deployments (avoiding reliance on massive, costly APIs for simple operations). LitE-SQL shows how a vector-based retriever and execution-guided self-correction can achieve state-of-the-art results with a highly efficient parameter footprint.

## Key points

- Focuses on efficiency and deployment feasibility by utilizing smaller, fine-tuned models (e.g., 7B-32B parameters).
- Uses a **Vector-based Schema Retriever** that matches user questions against pre-computed schema embeddings to perform efficient schema linking.
- Employs a **two-stage training process**: supervised fine-tuning (SFT) followed by execution-guided reinforcement learning (RL).
- Implements **Execution-Guided Self-Correction** within the model itself, allowing it to interpret database execution errors and repair SQL syntax and logic in a single context without complex multi-candidate voting.

## Contributions and achievements

- Demonstrates that vector-based schema linking is highly efficient for pruning complex schemas.
- Integrates self-correction directly into smaller models through execution-grounded training.
- Shows that smaller, specialized models can match or outperform naive implementations of giant proprietary LLMs.

## Evaluation

- Benchmarks used: BIRD dev, Spider 1.0.
- Reported scores:
  - **BIRD-dev:** **68.45% Execution Accuracy (EX)**.
  - **Spider 1.0:** **88.45% Execution Accuracy (EX)**.
- Efficiency result: Reached these scores using models that are 2x to 30x smaller in parameter size than competing commercial systems, reducing token usage and latency.
- Metrics: Execution Accuracy (EX).

## Problems it solves

- High API costs and latency of proprietary models.
- Missing required tables/columns during vector search.
- Brittle error handling that fails to recover from database syntax or runtime errors.

## Practical takeaways for Beacon

- Keep schema linking vector-based and simple, matching user terms against a vector index of table/column semantic descriptions.
- Use execution error messages (like database syntax exceptions) to feed a structured correction prompt.
- Fine-tuned, smaller models (like Qwen-Coder or CodeS) can achieve extremely high performance when paired with a good retrieval and validation loop.
