# Beacon - Natural Language to SQL

Beacon is a small metadata-grounded natural-language-to-SQL research MVP. It turns an analytics question into grounded schema context, asks an LLM for one PostgreSQL query, validates that query as read-only SQL, executes it, reviews the result, and retries when the failure mode is repairable.

The project is intentionally simple. The core pipeline uses plain Python functions and dictionaries, with the implementation split into indexing, linking, runtime, and app entrypoints.

## What To Read First

Start with `setup.md` if the machine is new. It covers PostgreSQL, `uv`, the `.env` file, and local dependency setup.

Use `docs/source_layout.md` as the codebase map. Use `docs/pipeline.md` for the compact pipeline diagram, `docs/pipeline_deep_dive.md` for the deeper runtime explanation, and `docs/evaluation.md` for the latest test and evaluation notes.

The submission-ready method report is generated at `docs/reports/beacon_method_report_submission_repo_paths.docx` and `docs/reports/beacon_method_report_submission_repo_paths.pdf`.

## Prerequisites

Install Python 3.11 or newer, `uv`, and PostgreSQL. Create a database that Beacon can write during setup and read during question answering. The default local settings assume PostgreSQL on `localhost:5432`.

Copy `.env.example` to `.env`, then fill in the model and database settings:

```env
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1
SQL_AGENT_LLM_STRONG_MODEL=gpt-4

PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=yourpassword
PGDATABASE=postgres
```

## Install

From the repository root:

```powershell
uv sync --extra dev
```

This installs the package in editable form and exposes the console commands declared in `pyproject.toml`.

## Build The Local Retrieval Artifacts

Run the indexer before asking questions:

```powershell
uv run beacon-index
```

Equivalent module form:

```powershell
uv run python -m beacon.indexing
```

The indexer reads `data/semantic_model/*.json` and `data/processed/*.csv`, enriches the semantic model with compact profiles, builds prompt-ready schema documents, enriches few-shot examples, and writes local vector artifacts under `data/indices/local_vectors/`.

## Load The Database

Start PostgreSQL, make sure `.env` points to the target database, then run:

```powershell
uv run beacon-load-db
```

Equivalent module form:

```powershell
uv run python -m beacon.load_db
```

The loader creates the local e-commerce tables and inserts the CSV data used by the MVP.

## Run The UI

Launch the Gradio app:

```powershell
uv run beacon-ui
```

Equivalent module form:

```powershell
uv run python -m beacon.ui
```

Open `http://127.0.0.1:7860` in a browser. The UI sends the question to `beacon.runtime.pipeline.ask_database`, then shows the final answer and SQL.

## Run One CLI Question

Use `beacon-ask` for a direct command-line run:

```powershell
uv run beacon-ask "For paid Apple Pay orders in the East region during 2022, what are the top 5 product categories by net revenue, discount rate, and profit margin?"
```

Equivalent module form:

```powershell
uv run python -m beacon.pipeline "How many orders were placed last month?"
```

## Run Tests And Evaluation

Run focused tests:

```powershell
uv run pytest tests -v
```

Run the 10-question evaluation harness:

```powershell
uv run python tests/test_cases/run_master_plan_tests.py
uv run python tests/test_cases/generate_report.py
```

The latest 10-question outputs are written to `tests/test_results/master_plan_evaluation_results.json` and `tests/test_results/report.html`. The current notes are summarized in `docs/evaluation.md`.

## Source Layout

`src/beacon/indexing/` builds semantic profiles, schema docs, few-shot docs, and local schema vectors.

`src/beacon/linking/` turns a question into grounded schema context through question signals, metadata grounding, vector retrieval, schema graph expansion, and example retrieval.

`src/beacon/runtime/` builds the SQL prompt, calls the model, validates and executes SQL, handles retry repair, and composes the final answer.

`src/beacon/app/` holds user-facing entrypoints such as the Gradio UI and local PostgreSQL loader.

The package root stays small. `src/beacon/config.py` owns paths, environment, and database settings. `src/beacon/pipeline.py`, `src/beacon/retrieval.py`, `src/beacon/retrieval_tools.py`, `src/beacon/load_db.py`, and `src/beacon/ui.py` are compatibility wrappers for older imports and module commands.

## Pipeline Summary

The UI or CLI receives a natural-language analytics question. Beacon extracts generic question signals, grounds user terms against semantic profiles and value aliases, searches the local schema vector index, expands join paths through the schema graph, retrieves structurally similar examples, and assembles a SQL-only prompt.

The model returns one PostgreSQL query. Beacon strips formatting, validates that the SQL is one read-only statement using selected schema context, executes it inside a read-only transaction, reviews the result or error, and retries with SQL repair, value repair, or retrieval repair when useful.

Accepted attempts produce the final answer. When `BEACON_SAVE_EXAMPLE_CANDIDATES=1`, accepted attempts can also be saved as candidate few-shot examples for manual review.
