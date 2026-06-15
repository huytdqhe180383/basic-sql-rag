# Handoff Prompt for Another Coding Agent

```text
You are working in:

E:\AI Thuc Chien\VSF\basic-mvp

Your job is to implement a simple, traceable retrieval-and-coverage layer for the NL-to-SQL pipeline.

Important constraints:
- Keep the code easy to read and easy to debug.
- Do not over-engineer this.
- Use plain functions, small classes only when clearly helpful, and simple data structures.
- Add sufficient comments and short docstrings so another engineer can follow the logic quickly.
- No LLM fallback is allowed for coverage checking.
- Human readability is more important than cleverness.

Goal
----
Replace the current â€œdump the whole schema into the promptâ€ approach with:
1. a semantic schema index,
2. a few-shot/example-query index,
3. a deterministic adaptive coverage loop,
4. prompt assembly from only the covered context.

Current source of truth
-----------------------
Treat the dataset as a 7-table MVP

Use these tables:

1. customers
2. orders
3. order_items
4. products
5. geography
6. sales
7. inventory

The local CSV files already exist under:
- data/processed/customers.csv
- data/processed/orders.csv
- data/processed/order_items.csv
- data/processed/products.csv
- data/processed/geography.csv
- data/processed/sales.csv
- data/processed/inventory.csv

Observed column hints from local files:
- geography: zip, city, region, district
- products: product_id, product_name, category, segment, size, color, price, cogs
- sales: Date, Revenue, COGS
- inventory: snapshot_date, product_id, stock_on_hand, units_received, units_sold, stockout_days, days_of_supply, fill_rate, stockout_flag, overstock_flag, reorder_flag, sell_through_rate, year, month

Implement against the actual local files and update stale schema artifacts as part of the work.

Expected table relationships
----------------------------
Use this relation graph unless the local files clearly contradict it:

- customers.customer_id -> orders.customer_id
- customers.zip -> geography.zip
- orders.zip -> geography.zip
- orders.order_id -> order_items.order_id
- order_items.product_id -> products.product_id
- inventory.product_id -> products.product_id
- sales is standalone daily aggregate data

Behavioral intent by table
--------------------------
Use these semantics in the retrieval and coverage logic:

- customers:
  customer demographics, signup analysis, acquisition analysis

- orders:
  order-level behavior, status, payment method, device, order source, date-based order analysis

- order_items:
  line-item revenue logic, quantity, discounts, promo usage

- products:
  product attributes and product/category/segment analysis

- geography:
  zip-to-city/region/district lookup

- sales:
  pre-aggregated daily Revenue/COGS table; prefer this for daily total revenue/COGS questions that do not require customer/product/order-level joins

- inventory:
  stock, fill rate, reorder, stockout, sell-through analysis

What to build
-------------
Implement the following in a simple, traceable way.

1. Update schema source files
- Align the stale schema-facing artifacts with the 7-table MVP.
- At minimum, update:
  - data/schema_llm.txt
  - data/schema_dicts.json
  - sql/00_simple_schema.sql
- Keep the schema flat in the public schema, matching the MVP style already in the repo.
- Do not introduce staging/core/mart layers.

2. Add a semantic schema source file
Create:
- data/semantic_model.json

This should be the main source for schema retrieval.

For each of the 7 tables, store:
- semantic_name
- source_table
- grain
- description
- columns
- relations
- question_families

Columns should support:
- name
- type
- description
- optional expression

Keep this very readable. Do not invent a large schema DSL.

3. Add few-shot query source file
Create:
- data/few_shot_queries.json

Store a small curated example set, around 10-16 examples.

Each example should include:
- question
- sql
- tables
- pattern
- question_families

Use a small pattern vocabulary such as:
- single_table_count
- single_table_date_filter
- group_by_category
- customer_orders_join
- orders_items_join
- revenue_calculation
- top_n
- geography_breakdown
- product_breakdown
- inventory_health
- daily_sales_aggregate

4. Add index builder
Create:
- build_index.py

This script should:
- read data/semantic_model.json
- read data/few_shot_queries.json
- build two separate LlamaIndex vector indices:
  - schema index
  - few-shot index
- persist them under:
  - data/indices/schema/
  - data/indices/few_shot/

Keep this file straightforward and readable.

5. Add deterministic coverage logic
Create:
- coverage.py

This module must contain two main public functions:

- extract_question_needs(question: str) -> dict
- assess_coverage(question_needs: dict, schema_docs: list[dict], example_docs: list[dict] | None = None) -> dict

A. extract_question_needs(question)
This is a rule-based analyzer only. No LLM.

Return a plain dict like:

{
  "question_families": [...],
  "required_tables": [...],
  "required_columns": [...],
  "required_relations": [...],
  "needs_aggregation": bool,
  "needs_example_query": bool,
  "example_patterns": [...]
}

Keep rules simple and explicit.

Examples of expected behavior:
- signup/customer-count questions -> customers
- order status / device / payment / order source questions -> orders
- revenue / discount / promo questions -> order_items + orders
- product/category/segment questions -> products, plus order_items if revenue is involved
- geography questions -> geography + whichever business table owns the zip used in the question
- stock/fill-rate/reorder questions -> inventory + products if product attributes are requested
- daily revenue/cogs totals by date -> prefer sales
- revenue by customer/product/order dimensions -> prefer orders + order_items, not sales

Use simple keyword rules and small helper functions.
Do not build a mini parser.

B. assess_coverage(...)
This must be a hard-coded rule checker.

Return a structure like:

{
  "is_sufficient": bool,
  "schema_coverage": {
    "tables_ok": bool,
    "columns_ok": bool,
    "relations_ok": bool,
    "question_family_ok": bool
  },
  "example_coverage": {
    "required": bool,
    "pattern_match_ok": bool
  },
  "missing": [...]
}

Coverage rules:
- tables_ok:
  all required tables are present in retrieved schema docs

- columns_ok:
  all required columns are present in the union of retrieved schema doc columns

- relations_ok:
  all required relations are present in the retrieved relation graph

- question_family_ok:
  at least one retrieved schema doc should match the important families implied by the question

- example_coverage:
  examples are optional enrichment only
  they should never block overall sufficiency

Overall sufficiency:
- is_sufficient is true only when:
  - tables_ok is true
  - columns_ok is true
  - relations_ok is true
- example query coverage must not block completion

6. Add retriever with adaptive expansion
Create:
- retriever.py

This should load the two indices and expose one main entry point:
- retrieve_context(question: str) -> dict

Behavior:
- retrieve schema docs first
- assess schema coverage
- if insufficient, increase schema k and try again
- once schema coverage is sufficient, retrieve example queries separately
- examples are optional boost only

Use bounded adaptive retrieval:
- schema_k starts at 2
- schema_k grows by 1
- schema_k max = 5
- example_k starts at 1
- example_k max = 2

Why 5 max for schema:
- 7 total tables now exist, but most questions should only need a small connected subset
- keep context tight

The returned context object should be explicit and easy to inspect, for example:

{
  "question_needs": {...},
  "schema_docs": [...],
  "schema_coverage": {...},
  "example_docs": [...],
  "prompt_context": {
    "schema_text": "...",
    "example_text": "..."
  }
}

7. Integrate into pipeline.py
Update pipeline.py so that:
- it no longer reads the full schema blob into every prompt at runtime
- it uses the retriever output instead
- it composes prompt sections from:
  - retrieved schema context
  - optional example queries
  - the user question

Keep app.py unchanged unless absolutely necessary.

Prompt behavior requirements
----------------------------
The runtime prompt should be simple and readable.

Suggested shape:

SYSTEM: existing SQL-only safety rules

RELEVANT SCHEMA:
{retrieved semantic schema docs only}

EXAMPLE QUERIES:
{0-2 example queries only if accepted}

QUESTION:
{user question}

Do not include the full 7-table schema unless adaptive retrieval actually pulled it all in.

Implementation style requirements
---------------------------------
This is important.

Write code that is:
- clear
- small
- easy to trace in a debugger
- lightly commented
- properly docstringed

Specifically:
- every public function should have a short docstring
- comments should explain non-obvious rule choices
- avoid deep abstractions
- avoid inheritance-heavy designs
- avoid clever metaprogramming
- prefer plain dicts or dataclasses
- keep helper functions short and single-purpose

Do not build:
- a plugin architecture
- a generic rule engine framework
- a second ranking system beyond what is necessary
- an LLM-based judge

Testing requirements
--------------------
Add focused local tests. If the tests folder is sparse, create the needed pytest tests.

Test these areas:

1. question_needs extraction
- customer signup count question
- mobile order count question
- product revenue question
- city-level customer question
- inventory reorder question
- daily revenue question that should prefer sales

2. coverage checking
- missing tables fails
- missing relations fails
- correct connected subset passes
- example-query miss does not fail overall coverage

3. adaptive retrieval
- simple customer question stops early
- revenue-by-product question expands to the needed subset
- inventory question reaches inventory + products
- daily sales question prefers sales over orders+order_items
- retrieval never exceeds configured max k

4. prompt composition
- only retrieved schema docs appear
- example queries appear only when matched
- full schema dump is gone from runtime path

5. light end-to-end smoke scenarios
- â€œHow many customers signed up in 2025?â€
- â€œHow many orders were placed via mobile last month?â€
- â€œWhat is total revenue by product category?â€
- â€œWhich city generated the most revenue?â€
- â€œWhat is the fill rate trend by month?â€
- â€œWhat was daily Revenue and COGS last week?â€

Acceptance criteria
-------------------
The work is complete when:

- the repo has a 7-table semantic retrieval setup
- stale schema artifacts are aligned with the 7-table MVP
- runtime prompt assembly uses retrieved context, not the full schema blob
- adaptive coverage is deterministic and rule-based
- no LLM fallback exists in coverage logic
- example queries are optional enrichment only
- code stays simple and human-readable
- local tests cover the core retrieval and coverage behavior

Please implement this directly in the repo, keeping the code as human-readable as possible.
```
