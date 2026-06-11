# Beacon — Natural Language to SQL

Ask questions about your e-commerce data in plain English. Beacon uses an LLM to generate SQL queries, executes them against a PostgreSQL database, and returns formatted results.

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

### 3. Load the data

Run the schema SQL to create the tables, then import the CSVs from `data/processed/` into PostgreSQL.

### 4. Launch the web UI

```bash
python app.py
```

Open `http://127.0.0.1:7860` in your browser. Ask any question about your data and Beacon will generate the SQL, execute it, and display both the answer and the query.

### CLI mode

You can also use the command line:

```bash
python pipeline.py "How many orders were placed last month?"
```

## Database Schema

| Table | Description | Key Columns |
|---|---|---|
| `customers` | Customer profiles | customer_id, zip, age_group, acquisition_channel |
| `orders` | Order records | order_id, customer_id, order_status, payment_method |
| `order_items` | Line items per order | order_item_id, order_id, product_id, quantity, unit_price |

Relationships: `customers → orders → order_items` (1:N via foreign keys).

## How It Works

1. You type a question in the UI (or CLI)
2. The prompt (schema + question) is sent to an OpenAI-compatible LLM
3. The LLM generates a PostgreSQL `SELECT` query
4. The query runs against your database — up to 3 automatic retries on error
5. Results are formatted and displayed, along with the SQL that was executed
