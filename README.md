# Beacon - Natural Language to SQL

Ask questions about your e-commerce data in plain English. Beacon retrieves only the relevant schema context, asks an LLM to generate PostgreSQL, executes the query, and returns formatted results.

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

This creates separate schema and few-shot indices under `data/indices/`.

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

- `src/beacon/pipeline.py` for question splitting, prompting, SQL generation, and answers
- `src/beacon/retrieval.py` for the retrieval workflow and prompt assembly
- `src/beacon/retrieval_tools.py` for question rules, coverage checks, and document ranking
- `src/beacon/sql.py` for SQL validation, execution, and result formatting
- `src/beacon/indexing.py` for the index-building workflow
- `src/beacon/indexing_tools.py` for semantic profiles and retrieval document construction
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
2. Deterministic rules identify the required tables, columns, and joins.
3. Schema retrieval expands until the required context is covered.
4. Matching example queries are added as optional prompt enrichment, using simple pattern and metadata signals.
5. The covered prompt is sent to an OpenAI-compatible LLM.
6. The generated `SELECT` query is validated and runs against PostgreSQL.
7. The same in-request LLM conversation reviews the result or error and can retry up to 2 times.
8. Beacon returns a final natural-language answer with the SQL that was executed.
