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

```bash
python build_index.py
```

This creates separate schema and few-shot indices under `data/indices/`.

### 4. Load the data

Run `sql/00_simple_schema.sql`, then import the CSVs from `data/processed/` into PostgreSQL.

### 5. Launch the web UI

```bash
python app.py
```

Open `http://127.0.0.1:7860` in your browser.

### CLI mode

```bash
python pipeline.py "How many orders were placed last month?"
```

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
4. Matching example queries are added as optional prompt enrichment.
5. The covered prompt is sent to an OpenAI-compatible LLM.
6. The generated `SELECT` query runs against PostgreSQL with up to three retries.
7. Results are displayed with the SQL that was executed.
