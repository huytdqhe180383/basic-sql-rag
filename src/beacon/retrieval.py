"""Question understanding, schema retrieval, coverage, and prompt assembly."""

from __future__ import annotations

import os
import re

from llama_index.core import Settings, StorageContext, load_index_from_storage
from llama_index.embeddings.openai import OpenAIEmbedding

from beacon.config import FEW_SHOT_INDEX_DIR, SCHEMA_INDEX_DIR


SCHEMA_K_START = 2
SCHEMA_K_MAX = 5
EXAMPLE_K_START = 1
EXAMPLE_K_MAX = 2

RELATIONS = {
    ("customers", "orders"): "customers.customer_id -> orders.customer_id",
    ("customers", "geography"): "customers.zip -> geography.zip",
    ("orders", "geography"): "orders.zip -> geography.zip",
    ("order_items", "orders"): "orders.order_id -> order_items.order_id",
    ("order_items", "products"): "order_items.product_id -> products.product_id",
    ("inventory", "products"): "inventory.product_id -> products.product_id",
}


def has_any(text: str, phrases: set[str]) -> bool:
    """Return whether any phrase appears as a simple word-boundary match."""
    return any(re.search(rf"(?<!\w){re.escape(p)}(?!\w)", text) for p in phrases)


def extract_question_needs(question: str) -> dict:
    """Infer needed tables, columns, joins, and examples using simple rules."""
    q = " ".join(question.lower().split())
    tables: set[str] = set()
    columns: set[str] = set()
    patterns: set[str] = set()

    has_date = bool(re.search(r"\b(?:19|20)\d{2}\b", q)) or has_any(
        q,
        {"today", "yesterday", "last week", "last month", "last year", "this year"},
    )
    wants_daily = has_any(q, {"daily", "by day", "per day", "each day"})
    wants_revenue = has_any(q, {"revenue", "sales", "total sales"})
    business_dimension = has_any(
        q,
        {"customer", "customers", "order", "orders", "product", "category", "city", "region", "district"},
    )

    if has_any(q, {"customer", "customers", "signup", "signed up", "acquisition", "gender", "age group"}):
        tables.add("customers")
    if has_any(q, {"signup", "signed up"}):
        columns.add("signup_date")
    if "acquisition" in q:
        columns.add("acquisition_channel")
    if "gender" in q:
        columns.add("gender")
    if "age group" in q:
        columns.add("age_group")

    if has_any(q, {"order", "orders", "placed", "device", "mobile", "payment", "order status"}):
        tables.add("orders")
    if has_date and "orders" in tables:
        columns.add("order_date")
    if has_any(q, {"device", "mobile"}):
        columns.add("device_type")
    if "payment" in q:
        columns.add("payment_method")
    if "order status" in q:
        columns.add("order_status")

    if wants_daily and has_any(q, {"revenue", "sales", "cogs"}) and not business_dimension:
        tables = {"sales"}
        columns.update({"Date"})
        if has_any(q, {"revenue", "sales"}):
            columns.add("Revenue")
        if "cogs" in q:
            columns.add("COGS")
        patterns.add("daily_sales_aggregate")
    elif wants_revenue:
        tables.update({"orders", "order_items"})
        columns.update({"quantity", "unit_price", "discount_amount"})
        patterns.add("revenue_calculation")

    if has_any(q, {"product", "products", "category", "segment", "size", "color"}):
        tables.add("products")
    for phrase, column in {
        "category": "category",
        "segment": "segment",
        "size": "size",
        "color": "color",
        "product name": "product_name",
    }.items():
        if phrase in q:
            columns.add(column)

    if has_any(q, {"city", "region", "district", "location", "geography"}):
        tables.add("geography")
        if not {"orders", "customers"} & tables:
            tables.add("orders" if wants_revenue else "customers")
    for column in ("city", "region", "district"):
        if column in q:
            columns.add(column)

    if has_any(q, {"inventory", "stock", "fill rate", "reorder", "stockout", "sell through", "days of supply"}):
        tables.add("inventory")
    inventory_columns = {
        "stock": "stock_on_hand",
        "fill rate": "fill_rate",
        "reorder": "reorder_flag",
        "stockout": "stockout_flag",
        "sell through": "sell_through_rate",
        "days of supply": "days_of_supply",
    }
    for phrase, column in inventory_columns.items():
        if phrase in q:
            columns.add(column)
    if "month" in q and "inventory" in tables:
        columns.add("month")
    if "inventory" in tables and "products" in tables:
        pass

    if has_any(q, {"how many", "count of", "total number of"}):
        patterns.add("single_table_count")
    if has_any(q, {"top", "most", "highest", "largest"}):
        patterns.add("top_n")
    if has_any(q, {"by", "per", "breakdown"}):
        patterns.add("group_by_category")

    relations = required_relations(tables)
    return {
        "tables": tables,
        "columns": columns,
        "relations": relations,
        "example_patterns": patterns,
    }


def required_relations(tables: set[str]) -> set[str]:
    """Return known join relations needed to connect selected tables."""
    return {
        relation
        for pair, relation in RELATIONS.items()
        if pair[0] in tables and pair[1] in tables
    }


def assess_coverage(needs: dict, schema_docs: list[dict], example_docs: list[dict] | None = None) -> dict:
    """Check whether retrieved schema docs cover the inferred question needs."""
    covered_tables: set[str] = set()
    covered_columns: set[str] = set()
    covered_relations: set[str] = set()

    for doc in schema_docs:
        meta = doc.get("metadata", {})
        text = doc.get("text", "")
        table = meta.get("table") or meta.get("source_table")
        if table:
            covered_tables.add(table)
        covered_columns.update(meta.get("columns", []))
        covered_relations.update(meta.get("relations", []))
        covered_columns.update(re.findall(r"  - ([A-Za-z_]\w*)\s*\(", text))
        covered_relations.update(re.findall(r"\w+\.\w+\s*->\s*\w+\.\w+", text))

    missing = {
        "tables": sorted(needs.get("tables", set()) - covered_tables),
        "columns": sorted(needs.get("columns", set()) - covered_columns),
        "relations": sorted(needs.get("relations", set()) - covered_relations),
    }
    examples_needed = needs.get("example_patterns", set())
    example_patterns = {
        doc.get("metadata", {}).get("pattern")
        for doc in (example_docs or [])
        if doc.get("metadata", {}).get("pattern")
    }
    return {
        "is_sufficient": not any(missing.values()),
        "missing": missing,
        "example_match": not examples_needed or bool(examples_needed & example_patterns),
    }


def load_indices():
    """Load persisted schema and few-shot indices."""
    embed_model = OpenAIEmbedding(
        api_key=os.getenv("OPENAI_API_KEY"),
        api_base=os.getenv("OPENAI_API_BASE"),
        model="text-embedding-3-small",
    )
    Settings.embed_model = embed_model
    schema_index = load_index_from_storage(
        StorageContext.from_defaults(persist_dir=str(SCHEMA_INDEX_DIR))
    )
    example_index = load_index_from_storage(
        StorageContext.from_defaults(persist_dir=str(FEW_SHOT_INDEX_DIR))
    )
    return schema_index, example_index


def retrieve_nodes(index, question: str, k: int) -> list[dict]:
    """Retrieve nodes from a LlamaIndex index as plain dictionaries."""
    return [
        {"text": node.text, "metadata": node.metadata}
        for node in index.as_retriever(similarity_top_k=k).retrieve(question)
    ]


def matching_examples(example_docs: list[dict], patterns: set[str]) -> list[dict]:
    """Keep examples that match inferred question patterns."""
    if not patterns:
        return []
    return [
        doc
        for doc in example_docs
        if doc.get("metadata", {}).get("pattern") in patterns
    ]


def retrieve_context(question: str) -> dict:
    """Retrieve schema and optional example context for one question."""
    needs = extract_question_needs(question)
    schema_index, example_index = load_indices()
    schema_docs: list[dict] = []
    coverage = {"is_sufficient": False, "missing": {}}

    for k in range(SCHEMA_K_START, SCHEMA_K_MAX + 1):
        schema_docs = retrieve_nodes(schema_index, question, k)
        coverage = assess_coverage(needs, schema_docs)
        if coverage["is_sufficient"]:
            break

    example_docs: list[dict] = []
    if coverage["is_sufficient"] and needs["example_patterns"]:
        for k in range(EXAMPLE_K_START, EXAMPLE_K_MAX + 1):
            example_docs = matching_examples(
                retrieve_nodes(example_index, question, k),
                needs["example_patterns"],
            )
            if example_docs:
                break
    coverage = assess_coverage(needs, schema_docs, example_docs)
    return {
        "question_needs": needs,
        "schema_docs": schema_docs,
        "example_docs": example_docs,
        "schema_coverage": coverage,
    }


def build_prompt(question: str, context: dict) -> str:
    """Build the final SQL prompt from retrieved schema and examples."""
    sections = ["RELEVANT SCHEMA:"]
    sections.extend(doc["text"] for doc in context.get("schema_docs", []))
    if context.get("example_docs"):
        sections.append("EXAMPLE QUERIES:")
        sections.extend(doc["text"] for doc in context["example_docs"])
    sections.extend([f"QUESTION: {question}", "SQL:"])
    return "\n\n---\n\n".join(sections)
