# Beacon - Natural Language to SQL

Ask questions about your e-commerce data in plain English. Beacon retrieves only the relevant schema context, asks an LLM to generate PostgreSQL, executes the query, and returns formatted results.

For a fresh local machine setup, read `setup.md` first. It covers the non-repo prerequisites such as PostgreSQL, the `.env` file, and the extra dev dependency used for testing.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up environment

Copy `.env.example` to `.env` and fill in your credentials:

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

### 3. Build the retrieval indices

```powershell
$env:PYTHONPATH="src"
python -m beacon.indexing
```

This creates Beacon's local schema vector files under `data/indices/local_vectors/`.
To also rebuild the legacy LlamaIndex schema and few-shot indices, set `BEACON_BUILD_LEGACY_LLAMA_INDEX=1`.

### 4. Load the data

Run the loader after PostgreSQL is available:

```powershell
$env:PYTHONPATH="src"
python -m beacon.load_db
```

### 5. Launch the web UI

```powershell
$env:PYTHONPATH="src"
python -m beacon.ui
```

Open `http://127.0.0.1:7860` in your browser.

### CLI mode

```powershell
$env:PYTHONPATH="src"
python -m beacon.pipeline "How many orders were placed last month?"
```

## Source Layout

The implementation lives under `src/beacon/` as a small set of modules:

- `src/beacon/pipeline.py` for public question answering entry points
- `src/beacon/schema_linking.py` for the hybrid schema linking workflow
- `src/beacon/question_signals.py` for generic question signals
- `src/beacon/metadata_grounding.py` for value/entity grounding and confidence scoring
- `src/beacon/schema_graph.py` for join-path expansion
- `src/beacon/vector_store.py` and `src/beacon/embeddings.py` for local vector retrieval
- `src/beacon/example_retrieval.py` for structurally ranked few-shot examples
- `src/beacon/feedback_examples.py` for semi-automatic example candidates
- `src/beacon/prompting.py` for SQL prompt assembly
- `src/beacon/retry.py` for SQL, value, and retrieval retry decisions
- `src/beacon/retrieval.py` for compatibility retrieval entry points used by the pipeline
- `src/beacon/retrieval_tools.py` for original demo-schema fallback rules and legacy ranking helpers
- `src/beacon/sql.py` for SQL validation, execution, and result formatting
- `src/beacon/indexing.py` for the index-building workflow
- `src/beacon/indexing_tools.py` for semantic profiles and retrieval document construction
- `src/beacon/profiler.py` for offline semantic profile refresh
- `src/beacon/config.py` for paths, environment, and database settings
- `src/beacon/ui.py` for the Gradio interface
- `src/beacon/load_db.py` for loading processed CSVs into PostgreSQL

There are no duplicate root-level wrapper scripts; run the package modules with `PYTHONPATH=src` as shown above.

`data/semantic_model/` is the main semantic layer. It has one JSON file per table, each with descriptions, relations, three sample rows, and compact column profiles such as min/max/mean, date ranges, null counts, distinct counts, and common categorical values.

`data/few_shot_queries.json` stays small and readable. During indexing, Beacon adds lightweight signals such as important columns, metrics, filters, and time grain to help retrieve better examples.

## Database Schema

| Table | Description | Key Columns |
|---|---|---|
| `customers` | Customer profiles | customer_id, zip, signup_date, acquisition_channel |
| `orders` | Order records | order_id, customer_id, zip, order_status, device_type |
| `order_items` | Line items per order | order_item_id, order_id, product_id, quantity, unit_price |
| `products` | Product catalog | product_id, category, segment, price, cogs |
| `geography` | Zip-to-location lookup | zip, city, region, district |
| `sales` | Daily revenue and COGS aggregates | Date, Revenue, COGS |
| `inventory` | Product inventory snapshots | snapshot_date, product_id, fill_rate, reorder_flag |

Key relationships connect customers to orders, orders to line items, line items and inventory to products, and customer/order zip codes to geography.

## How It Works

1. You enter a question in the UI or CLI.
2. Beacon extracts generic question signals such as metrics, dates, grouping, ranking, and likely entity phrases.
3. Beacon grounds user terms against semantic profiles, aliases, and sample values.
4. Beacon searches the local schema vector index and combines those hits with grounded evidence and weak lexical fallback signals.
5. Beacon expands selected tables through the schema graph so join keys and bridge tables are available.
6. Beacon ranks few-shot examples by structural overlap with selected tables, metrics, filters, and time grain.
7. Beacon builds a SQL-only prompt from matched evidence, join paths, schema docs, examples, and the original question.
8. The LLM returns one read-only PostgreSQL query.
9. Beacon validates and executes the query in a read-only transaction.
10. Beacon reviews the result or error and retries with SQL, value, or retrieval repair guidance when useful.
11. Accepted queries can optionally be saved as future example candidates.

See `docs/pipeline.md` for the full Mermaid diagram and module-level flow. See `docs/evaluation.md` for the latest focused-test and 10-question evaluation notes.
