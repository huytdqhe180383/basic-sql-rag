"""Rule-based question understanding, coverage, and retrieval ranking helpers."""

from __future__ import annotations

import re


QUESTION_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "by",
    "for",
    "how",
    "in",
    "is",
    "me",
    "of",
    "on",
    "show",
    "the",
    "to",
    "what",
    "which",
    "with",
}

RELATIONS = {
    ("customers", "orders"): "customers.customer_id -> orders.customer_id",
    ("customers", "geography"): "customers.zip -> geography.zip",
    ("orders", "geography"): "orders.zip -> geography.zip",
    ("order_items", "orders"): "orders.order_id -> order_items.order_id",
    ("order_items", "products"): "order_items.product_id -> products.product_id",
    ("inventory", "products"): "inventory.product_id -> products.product_id",
}

TABLE_RULES = [
    (
        {
            "customer",
            "customers",
            "signup",
            "signed up",
            "acquisition",
            "gender",
            "age group",
        },
        {"customers"},
    ),
    ({"order", "orders", "placed", "device", "mobile", "payment", "order status"}, {"orders"}),
    ({"product", "products", "category", "segment", "size", "color"}, {"products"}),
    ({"city", "region", "district", "location", "geography"}, {"geography"}),
    (
        {
            "inventory",
            "stock",
            "fill rate",
            "reorder",
            "reordering",
            "stockout",
            "sell through",
            "days of supply",
        },
        {"inventory"},
    ),
]

COLUMN_RULES = [
    ({"signup", "signed up"}, {"signup_date"}),
    ({"acquisition"}, {"acquisition_channel"}),
    ({"gender"}, {"gender"}),
    ({"age group"}, {"age_group"}),
    ({"device", "mobile"}, {"device_type"}),
    ({"payment"}, {"payment_method"}),
    ({"order status"}, {"order_status"}),
    ({"category"}, {"category"}),
    ({"segment"}, {"segment"}),
    ({"size"}, {"size"}),
    ({"color"}, {"color"}),
    ({"product name"}, {"product_name"}),
    ({"city"}, {"city"}),
    ({"region"}, {"region"}),
    ({"district"}, {"district"}),
    ({"stock"}, {"stock_on_hand"}),
    ({"fill rate"}, {"fill_rate"}),
    ({"reorder", "reordering"}, {"reorder_flag"}),
    ({"stockout"}, {"stockout_flag"}),
    ({"sell through"}, {"sell_through_rate"}),
    ({"days of supply"}, {"days_of_supply"}),
]

PATTERN_RULES = [
    ({"how many", "count of", "total number of"}, {"single_table_count"}),
    ({"top", "most", "highest", "largest"}, {"top_n"}),
    ({"by", "per", "breakdown"}, {"group_by_category"}),
]

DATE_WORDS = {"today", "yesterday", "last week", "last month", "last year", "this year"}
DAILY_WORDS = {"daily", "by day", "per day", "each day"}
REVENUE_WORDS = {"revenue", "sales", "total sales"}
BUSINESS_DIMENSION_WORDS = {
    "customer",
    "customers",
    "order",
    "orders",
    "product",
    "category",
    "city",
    "region",
    "district",
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

    apply_rules(q, TABLE_RULES, tables)
    apply_rules(q, COLUMN_RULES, columns)
    apply_rules(q, PATTERN_RULES, patterns)
    apply_date_rules(q, tables, columns, patterns)
    apply_revenue_rules(q, tables, columns, patterns)
    apply_geography_rules(q, tables, patterns)
    apply_inventory_rules(q, tables, columns, patterns)

    return {
        "tables": tables,
        "columns": columns,
        "relations": required_relations(tables),
        "example_patterns": patterns,
    }


def apply_rules(text: str, rules: list[tuple[set[str], set[str]]], output: set[str]) -> None:
    """Apply phrase-triggered additions to an output set."""
    for phrases, values in rules:
        if has_any(text, phrases):
            output.update(values)


def apply_date_rules(text: str, tables: set[str], columns: set[str], patterns: set[str]) -> None:
    """Add date columns when a question includes a date filter."""
    has_date = bool(re.search(r"\b(?:19|20)\d{2}\b", text)) or has_any(text, DATE_WORDS)
    if has_date and "orders" in tables:
        columns.add("order_date")
    if has_date and {"orders", "customers", "sales"} & tables:
        patterns.add("single_table_date_filter")


def apply_revenue_rules(
    text: str,
    tables: set[str],
    columns: set[str],
    patterns: set[str],
) -> None:
    """Route revenue questions to either daily sales or line-item revenue."""
    wants_daily_sales = (
        has_any(text, DAILY_WORDS)
        and has_any(text, REVENUE_WORDS | {"cogs"})
        and not has_any(text, BUSINESS_DIMENSION_WORDS)
    )
    if wants_daily_sales:
        tables.clear()
        tables.add("sales")
        columns.add("Date")
        add_when(text, {"revenue", "sales"}, columns, "Revenue")
        add_when(text, {"cogs"}, columns, "COGS")
        patterns.add("daily_sales_aggregate")
        return

    if has_any(text, REVENUE_WORDS):
        tables.update({"orders", "order_items"})
        columns.update({"quantity", "unit_price", "discount_amount"})
        patterns.add("revenue_calculation")


def apply_geography_rules(text: str, tables: set[str], patterns: set[str]) -> None:
    """Ensure geography questions include a table that owns the zip code."""
    if "geography" in tables and not {"orders", "customers"} & tables:
        tables.add("orders" if has_any(text, REVENUE_WORDS) else "customers")
    if "geography" in tables:
        patterns.add("geography_breakdown")


def apply_inventory_rules(text: str, tables: set[str], columns: set[str], patterns: set[str]) -> None:
    """Add inventory date-grain columns that depend on table routing."""
    if "month" in text and "inventory" in tables:
        columns.add("month")
    if "inventory" in tables:
        patterns.add("inventory_health")


def add_when(text: str, phrases: set[str], output: set[str], value: str) -> None:
    """Add one value when any trigger phrase matches."""
    if has_any(text, phrases):
        output.add(value)


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


def rank_docs(
    question: str,
    docs: list[dict],
    needs: dict | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Rank plain retrieval docs with simple metadata and keyword scoring."""
    scored = [
        (score_doc(question, doc, needs), index, doc)
        for index, doc in enumerate(docs)
    ]
    ranked = [doc for _score, _index, doc in sorted(scored, key=lambda item: (-item[0], item[1]))]
    return ranked[:limit] if limit else ranked


def score_doc(question: str, doc: dict, needs: dict | None = None) -> int:
    """Score one retrieval doc using visible metadata instead of hidden logic."""
    needs = needs or {}
    metadata = doc.get("metadata", {})
    text = doc.get("text", "").lower()
    score = token_overlap(question, text)

    score += 5 * len(needs.get("tables", set()) & metadata_values(metadata, "table", "tables"))
    score += 3 * len(needs.get("columns", set()) & metadata_values(metadata, "columns"))
    score += 4 * len(needs.get("example_patterns", set()) & metadata_values(metadata, "pattern"))
    score += 2 * len(question_terms(question) & metadata_values(metadata, "question_families", "metrics", "filters"))
    return score


def token_overlap(question: str, text: str) -> int:
    """Count how many meaningful question terms appear in a document."""
    return sum(1 for term in question_terms(question) if term in text)


def question_terms(question: str) -> set[str]:
    """Return simple lowercase question terms for scoring."""
    return {
        term
        for term in re.findall(r"[a-z_][a-z0-9_]*", question.lower())
        if term not in QUESTION_STOPWORDS and len(term) > 1
    }


def metadata_values(metadata: dict, *keys: str) -> set[str]:
    """Collect scalar or list metadata values as strings."""
    values: set[str] = set()
    for key in keys:
        value = metadata.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            values.update(str(item) for item in value)
        else:
            values.add(str(value))
    return values


def matching_examples(
    example_docs: list[dict],
    patterns: set[str],
    question: str = "",
) -> list[dict]:
    """Keep examples that match inferred question patterns."""
    if not patterns:
        return []
    ranked_docs = rank_docs(question, example_docs, {"example_patterns": patterns})
    return [
        doc
        for doc in ranked_docs
        if doc.get("metadata", {}).get("pattern") in patterns
    ]
