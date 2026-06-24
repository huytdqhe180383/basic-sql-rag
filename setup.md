# Beacon Local Setup

This file is the practical machine-setup guide for Beacon.

Use it when you are setting up the repo on a new PC, or when a coding agent needs to know what must exist outside the repo itself.

## What Is Already In The Repo

These inputs are already checked in:

- `src/` application code
- `requirements.txt` runtime Python dependencies
- `data/processed/*.csv` source CSV files for local loading
- `data/semantic_model/*.json` semantic metadata
- `data/few_shot_queries.json` few-shot examples
- `sql/00_simple_schema.sql` local PostgreSQL schema
- `.env.example` template environment variables

## What You Must Install On Your PC

Install these outside the repo:

1. `Git`
2. `Python`
   Recommended: Python `3.11` or `3.12` 64-bit
3. `PostgreSQL`
   Any recent local version is fine. The app expects a reachable database on the values in `.env`.
4. Python dev/test tooling that is not in `requirements.txt`
   Install `pytest` for local testing.

## Windows PowerShell Setup

From the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pytest
```

`requirements.txt` includes the runtime embedding stack used by the local schema vector index, including `numpy` and `sentence-transformers`.

## Environment File

Create `.env` from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Current required variables:

```env
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1
SQL_AGENT_LLM_STRONG_MODEL=gpt-4
SQL_AGENT_LLM_WEAK_MODEL=gpt-4

PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=yourpassword
PGDATABASE=postgres
```

Notes:

- `OPENAI_API_KEY` is required for SQL generation and for legacy LlamaIndex rebuilds.
- Normal local schema-vector indexing can run without OpenAI by using the local embedding adapter or `BEACON_USE_HASH_EMBEDDINGS=1`.
- `PGDATABASE` can stay `postgres`, or you can point it to a dedicated local database.
- The loader creates tables using `sql/00_simple_schema.sql` and then bulk-loads the CSVs from `data/processed/`.

## PostgreSQL Expectations

Your configured PostgreSQL user should be able to:

- connect to the target database
- create tables
- truncate or overwrite existing local test tables if needed
- run `COPY ... FROM STDIN`

The app uses these local tables:

- `geography`
- `products`
- `customers`
- `orders`
- `order_items`
- `sales`
- `inventory`

## First-Time Repo Commands

Run these from the repo root after the virtual environment is active.

Set the import path for the current PowerShell session:

```powershell
$env:PYTHONPATH = "src"
```

Build the retrieval indices:

```powershell
python -m beacon.indexing
```

If your machine cannot download the configured sentence-transformer model yet, build with deterministic local hash embeddings:

```powershell
$env:BEACON_USE_HASH_EMBEDDINGS = "1"
python -m beacon.indexing
```

Load the local CSV data into PostgreSQL:

```powershell
python -m beacon.load_db
```

Launch the UI:

```powershell
python -m beacon.ui
```

Run the CLI:

```powershell
python -m beacon.pipeline "How many orders were placed last month?"
```

Run the test suite:

```powershell
pytest tests -v
```

## Optional Spider2-Snow Benchmark Setup

Only do this if you plan to run the benchmark helpers under `benchmarks/spider2_snow/`.

Create a separate benchmark virtual environment:

```powershell
python -m venv benchmarks\.venv_spider2_snow
benchmarks\.venv_spider2_snow\Scripts\python.exe -m pip install --upgrade pip
benchmarks\.venv_spider2_snow\Scripts\python.exe -m pip install -r benchmarks\spider2_snow\requirements-spider2-snow.txt
```

That benchmark environment installs additional tools such as:

- `google-cloud-bigquery`
- `pandas`
- `snowflake-connector-python`
- `tqdm`

The Snow benchmark also needs Snowflake credentials that are not stored in this repo.

## Sanity Checklist

You are set up correctly when all of these are true:

- the virtual environment is active
- `pip install -r requirements.txt` succeeded
- `pip install pytest` succeeded
- `.env` exists
- PostgreSQL is running
- `python -m beacon.indexing` creates `data/indices/local_vectors/`
- `python -m beacon.load_db` prints `Schema created.` and loads the CSV-backed tables
- `pytest tests -v` starts without `ModuleNotFoundError: beacon`

## Common Problems

`ModuleNotFoundError: beacon`

- Set `PYTHONPATH` for the current shell:

```powershell
$env:PYTHONPATH = "src"
```

`OPENAI_API_KEY is not set`

- Make sure `.env` exists in the repo root.
- Make sure the current shell can read it.
- This is only expected during SQL generation or legacy LlamaIndex indexing.

`Missing data\processed\*.csv`

- The repo expects the checked-in CSV files under `data/processed/`.
- If they are missing on your machine, your clone is incomplete.

`psycopg2.OperationalError`

- Check that PostgreSQL is running.
- Check `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, and `PGDATABASE` in `.env`.

`pytest` not found

- Install it separately:

```powershell
pip install pytest
```

## For Coding Agents

Before changing dependencies or startup commands:

1. Read `AGENTS.md`.
2. Read this file.
3. Keep `README.md`, `.env.example`, and this file aligned.

Assume these repo-specific facts unless the user says otherwise:

- this repo is run from source with `PYTHONPATH=src`
- there is no packaged editable install flow yet
- `requirements.txt` is runtime-focused, not full dev tooling
- the local vector index is part of the normal indexing command
- PostgreSQL and the OpenAI-compatible API are external prerequisites
