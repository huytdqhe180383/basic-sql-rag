"""
Deterministic coverage analysis for NL-to-SQL questions.

Rule-based extraction of question needs and hard-coded coverage
assessment. No LLM fallback is used anywhere in this module.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Relation graph: for any pair of connected tables, defines the join path.
# Each key is a sorted tuple of table names for consistent lookup.
# ---------------------------------------------------------------------------

RELATION_GRAPH = {
    ("customers", "orders"): {
        "description": "customers.customer_id -> orders.customer_id",
        "from_table": "customers",
        "to_table": "orders",
        "join_columns": ("customer_id", "customer_id"),
    },
    ("customers", "geography"): {
        "description": "customers.zip -> geography.zip",
        "from_table": "customers",
        "to_table": "geography",
        "join_columns": ("zip", "zip"),
    },
    ("orders", "geography"): {
        "description": "orders.zip -> geography.zip",
        "from_table": "orders",
        "to_table": "geography",
        "join_columns": ("zip", "zip"),
    },
    ("order_items", "orders"): {
        "description": "orders.order_id -> order_items.order_id",
        "from_table": "orders",
        "to_table": "order_items",
        "join_columns": ("order_id", "order_id"),
    },
    ("order_items", "products"): {
        "description": "order_items.product_id -> products.product_id",
        "from_table": "order_items",
        "to_table": "products",
        "join_columns": ("product_id", "product_id"),
    },
    ("inventory", "products"): {
        "description": "inventory.product_id -> products.product_id",
        "from_table": "inventory",
        "to_table": "products",
        "join_columns": ("product_id", "product_id"),
    },
}


def _get_required_relations(tables: set[str]) -> list[str]:
    """Find the relations needed to connect a set of tables.

    Returns the description strings for each relation where both
    tables in the pair are present in the required set.
    """
    if len(tables) <= 1:
        return []

    required = []
    for (ta, tb), rel in RELATION_GRAPH.items():
        if ta in tables and tb in tables:
            required.append(rel["description"])
    return sorted(required)


# ---------------------------------------------------------------------------
# Pattern signals for matching example query patterns.
# ---------------------------------------------------------------------------

PATTERN_SIGNALS = {
    "single_table_count": ["how many", "count of", "total number of"],
    "single_table_date_filter": [
        "in 2025", "last month", "last year", "this year", "last week",
        "last quarter",
    ],
    "group_by_category": [
        "by ", "per ", "breakdown", "break down", "for each",
        "by each",
    ],
    "customer_orders_join": ["customer", "order"],
    "orders_items_join": ["order", "item"],
    "revenue_calculation": ["revenue", "total sales", "total amount"],
    "top_n": ["top", "most", "highest", "best", "largest"],
    "geography_breakdown": [
        "city", "region", "district", "geography", "location",
    ],
    "product_breakdown": ["product", "category", "segment"],
    "inventory_health": [
        "stock", "fill rate", "inventory", "reorder", "stockout",
    ],
    "daily_sales_aggregate": [
        "daily", "by day", "per day", "each day", "day-level",
    ],
}

# ---------------------------------------------------------------------------
# Aggregation keywords
# ---------------------------------------------------------------------------

AGG_KEYWORDS = {
    "how many", "total", "sum", "average", "avg", "count", "count of",
    "maximum", "max ", "minimum", "min ", "most", "highest", "lowest",
    "top ", "breakdown", "by ", "per ", "trend",
}


def _contains_phrase(text: str, phrase: str) -> bool:
    """Return whether a word or phrase appears on word boundaries."""
    phrase = phrase.strip()
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def _contains_any(text: str, phrases: list[str] | set[str]) -> bool:
    """Return whether any phrase appears in text."""
    return any(_contains_phrase(text, phrase) for phrase in phrases)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_question_needs(question: str) -> dict:
    """Analyze a question and extract required tables, columns, relations,
    and patterns using keyword-based rules only.

    No LLM call is made by this function.

    Args:
        question: Natural language question string.

    Returns:
        A dict with keys:
          - question_families: list[str]
          - required_tables: list[str]
          - required_columns: list[str]
          - required_relations: list[str]
          - needs_aggregation: bool
          - needs_example_query: bool
          - example_patterns: list[str]
    """
    q = " ".join(question.lower().split())
    required_tables: set[str] = set()
    question_families: list[str] = []
    required_columns: list[str] = []
    example_patterns: list[str] = []

    def add_families(*families: str) -> None:
        for family in families:
            if family not in question_families:
                question_families.append(family)

    def add_columns(*columns: str) -> None:
        for column in columns:
            if column not in required_columns:
                required_columns.append(column)

    has_date_filter = bool(re.search(r"\b(?:19|20)\d{2}\b", q)) or _contains_any(
        q,
        {
            "today", "yesterday", "last week", "last month", "last quarter",
            "last year", "this week", "this month", "this year",
            "current month", "current quarter", "current year",
        },
    )
    is_daily = _contains_any(q, {"daily", "by day", "per day", "each day", "day-level"})

    # Customer rules
    has_customer = _contains_any(
        q,
        {
            "customer", "customers", "signup", "signed up", "acquisition",
            "demographic", "demographics", "gender", "age group",
        },
    )
    if has_customer:
        required_tables.add("customers")
    if _contains_any(q, {"customer", "customers"}):
        add_families("customer_count")
    if _contains_any(q, {"signup", "signed up"}):
        add_families("signup_analysis")
        add_columns("signup_date")
    if _contains_phrase(q, "acquisition"):
        add_families("acquisition_analysis")
        add_columns("acquisition_channel")
    if _contains_any(q, {"demographic", "demographics", "gender", "age group"}):
        add_families("demographics_breakdown")
    if _contains_phrase(q, "gender"):
        add_columns("gender")
    if _contains_phrase(q, "age group"):
        add_columns("age_group")

    # Order rules. Boundary matching prevents "reorder" from meaning "order".
    has_order = _contains_any(
        q,
        {
            "order", "orders", "placed", "device", "device type", "mobile",
            "payment", "payment method", "order source", "order status",
            "shipped", "delivered", "cancelled", "returned",
        },
    )
    if has_order:
        required_tables.add("orders")
    if _contains_any(q, {"order", "orders", "placed"}):
        add_families("order_count")
    if _contains_any(q, {"device", "device type", "mobile"}):
        add_families("device_analysis")
        add_columns("device_type")
    if _contains_any(q, {"payment", "payment method"}):
        add_families("payment_analysis")
        add_columns("payment_method")
    if _contains_phrase(q, "order source"):
        add_families("order_source_analysis")
        add_columns("order_source")
    if _contains_any(
        q, {"order status", "shipped", "delivered", "cancelled", "returned"}
    ):
        add_families("order_status_analysis")
        add_columns("order_status")
    if "orders" in required_tables and has_date_filter:
        add_families("date_based_orders")
        add_columns("order_date")

    # Product rules. COGS alone does not imply products; daily COGS uses sales.
    has_product = _contains_any(
        q,
        {"product", "products", "product name", "category", "segment", "size", "color"},
    )
    if has_product:
        required_tables.add("products")
        add_families("product_breakdown")
    if _contains_phrase(q, "category"):
        add_families("category_analysis")
        add_columns("category")
    if _contains_phrase(q, "segment"):
        add_families("segment_analysis")
        add_columns("segment")
    for phrase, column in (("size", "size"), ("color", "color"), ("product name", "product_name")):
        if _contains_phrase(q, phrase):
            add_families("product_attributes")
            add_columns(column)
    if has_product and _contains_any(q, {"which product", "which products", "top product", "top products"}):
        add_columns("product_name")
    if has_product and _contains_phrase(q, "cogs"):
        add_columns("cogs")

    # Inventory rules
    inventory_signals = {
        "stock", "inventory", "fill rate", "fillrate", "reorder", "reordering",
        "stockout", "overstock", "sell through", "sell-through", "sellthrough",
        "days of supply", "stock on hand", "reorder flag", "stockout flag",
        "units received", "units sold",
    }
    if _contains_any(q, inventory_signals):
        required_tables.add("inventory")
        add_families("inventory_health")
    inventory_columns = (
        ({"stock", "stock on hand"}, "stock_on_hand"),
        ({"fill rate", "fillrate"}, "fill_rate"),
        ({"reorder", "reordering", "reorder flag"}, "reorder_flag"),
        ({"stockout", "stockout flag"}, "stockout_flag"),
        ({"overstock"}, "overstock_flag"),
        ({"sell through", "sell-through", "sellthrough"}, "sell_through_rate"),
        ({"days of supply"}, "days_of_supply"),
        ({"units received"}, "units_received"),
        ({"units sold"}, "units_sold"),
    )
    for phrases, column in inventory_columns:
        if _contains_any(q, phrases):
            add_columns(column)
    if _contains_any(q, {"reorder", "reordering", "reorder flag"}):
        add_families("reorder_analysis")
    if _contains_any(q, {"stockout", "stockout flag"}):
        add_families("stockout_analysis")
    if _contains_any(q, {"fill rate", "fillrate"}):
        add_families("fill_rate_analysis")
    if _contains_any(q, {"sell through", "sell-through", "sellthrough"}):
        add_families("sell_through_analysis")
    if "inventory" in required_tables and _contains_phrase(q, "month"):
        add_columns("year", "month")

    # Geography rules
    geography_columns = (("city", "city"), ("region", "region"), ("district", "district"))
    if _contains_any(q, {"city", "region", "district", "location", "geographic", "geography"}):
        required_tables.add("geography")
        add_families("geography_breakdown")
    for phrase, column in geography_columns:
        if _contains_phrase(q, phrase):
            add_columns(column)
            add_families(f"{phrase}_analysis")

    # Revenue and line-item rules
    has_revenue = _contains_any(q, {"revenue", "sales", "total sales", "monetary"})
    has_discount = _contains_phrase(q, "discount")
    has_promo = _contains_any(q, {"promo", "promo code"})
    has_quantity = _contains_any(q, {"quantity", "units sold"}) and "inventory" not in required_tables
    business_dimensions = _contains_any(
        q,
        {
            "product", "products", "category", "segment", "customer", "customers",
            "city", "region", "district", "order", "orders",
        },
    )

    if is_daily and _contains_any(q, {"revenue", "cogs", "sales"}) and not business_dimensions:
        required_tables.difference_update({"orders", "order_items", "products"})
        required_tables.add("sales")
        required_columns[:] = [
            column
            for column in required_columns
            if column not in {"order_date", "quantity", "unit_price", "discount_amount", "cogs"}
        ]
        add_columns("Date")
        if _contains_any(q, {"revenue", "sales"}):
            add_columns("Revenue")
            add_families("daily_revenue")
        if _contains_phrase(q, "cogs"):
            add_columns("COGS")
            add_families("daily_cogs")
        add_families("daily_sales_aggregate")
    else:
        if has_revenue:
            required_tables.update({"orders", "order_items"})
            add_columns("quantity", "unit_price", "discount_amount")
            add_families("revenue_calculation")
        if has_discount:
            required_tables.update({"orders", "order_items"})
            add_columns("discount_amount")
            add_families("discount_analysis")
        if has_promo:
            required_tables.update({"orders", "order_items"})
            add_columns("promo_id")
            add_families("promo_analysis")
        if has_quantity:
            required_tables.add("order_items")
            add_columns("quantity")
            add_families("quantity_analysis")
        if is_daily and "orders" in required_tables:
            add_columns("order_date")

    # Geography must be joined to the business table that owns the relevant zip.
    if "geography" in required_tables and not {"orders", "customers"} & required_tables:
        required_tables.add("orders" if has_revenue else "customers")

    # Inventory questions asking for product attributes need the catalog relation.
    if "inventory" in required_tables and has_product:
        required_tables.add("products")

    # Match example-query patterns with the same boundary-aware behavior.
    for pattern, signal_phrases in PATTERN_SIGNALS.items():
        if pattern == "customer_orders_join":
            matched = has_customer and has_order
        elif pattern == "orders_items_join":
            matched = has_order and (has_discount or has_promo or has_quantity)
        else:
            matched = _contains_any(q, signal_phrases)
        if matched:
            example_patterns.append(pattern)

    needs_aggregation = _contains_any(q, AGG_KEYWORDS)

    # Compute the join edges after all routing decisions are final.
    required_relations = _get_required_relations(required_tables)
    needs_example_query = len(example_patterns) > 0

    return {
        "question_families": question_families,
        "required_tables": sorted(required_tables),
        "required_columns": required_columns,
        "required_relations": required_relations,
        "needs_aggregation": needs_aggregation,
        "needs_example_query": needs_example_query,
        "example_patterns": example_patterns,
    }


def assess_coverage(
    question_needs: dict,
    schema_docs: list[dict],
    example_docs: Optional[list[dict]] = None,
) -> dict:
    """Assess whether the retrieved schema and example documents are sufficient
    to answer the question.

    Rules are hard-coded, no LLM fallback.

    - tables_ok:  all required tables appear in schema docs
    - columns_ok: all required columns appear in the union of doc columns
    - relations_ok: all required relations appear in the docs
    - question_family_ok: at least one needed family matches a doc
    - is_sufficient: true only when tables, columns, AND relations are all ok
    - Example miss does NOT block overall sufficiency.

    Args:
        question_needs: Dict from extract_question_needs.
        schema_docs: List of dicts with keys 'metadata' and 'text'.
        example_docs: Optional list of example dicts.

    Returns:
        A dict with is_sufficient, schema_coverage, example_coverage, missing.
    """
    if example_docs is None:
        example_docs = []

    # Collect coverage from schema docs
    covered_tables: set[str] = set()
    covered_columns: set[str] = set()
    covered_relations: set[str] = set()
    covered_families: set[str] = set()

    for doc in schema_docs:
        meta = doc.get("metadata", {}) if isinstance(doc, dict) else {}
        text = doc.get("text", "") if isinstance(doc, dict) else str(doc)

        table = meta.get("source_table", "")
        if table:
            covered_tables.add(table)

        for fam in meta.get("question_families", []):
            covered_families.add(fam)

        for column in meta.get("columns", []):
            covered_columns.add(column)

        for relation in meta.get("relations", []):
            covered_relations.add(re.sub(r"\s*->\s*", " -> ", relation.strip()))

        # Extract column names from doc text lines like "  - col_name (TYPE): ..."
        for m in re.finditer(r"  - (\w+)\s*\([^)]*\)", text):
            covered_columns.add(m.group(1))

        # Extract relations from doc text lines like "table.col -> other.col"
        for m in re.finditer(r"(\w+\.\w+\s*->\s*\w+\.\w+)", text):
            covered_relations.add(re.sub(r"\s*->\s*", " -> ", m.group(1)))

    required_tables = set(question_needs.get("required_tables", []))
    required_columns = set(question_needs.get("required_columns", []))
    required_relations = set(question_needs.get("required_relations", []))

    tables_ok = required_tables.issubset(covered_tables)
    columns_ok = required_columns.issubset(covered_columns)
    relations_ok = required_relations.issubset(covered_relations)

    # At least one question family from needs must be covered
    needed_families = set(question_needs.get("question_families", []))
    question_family_ok = (
        len(needed_families & covered_families) > 0 if needed_families else True
    )

    # Example coverage (optional, never blocks is_sufficient)
    example_required = question_needs.get("needs_example_query", False)
    pattern_match_ok = not example_required
    if example_required:
        needed_patterns = set(question_needs.get("example_patterns", []))
        covered_patterns: set[str] = set()
        for doc in example_docs:
            meta = doc.get("metadata", {}) if isinstance(doc, dict) else {}
            p = meta.get("pattern", "")
            if p:
                covered_patterns.add(p)
        pattern_match_ok = bool(needed_patterns & covered_patterns) if needed_patterns else True

    # Overall: tables, columns, AND relations must all be covered.
    # Example query misses never fail this.
    is_sufficient = tables_ok and columns_ok and relations_ok

    missing: list[str] = []
    if not tables_ok:
        missing.append(
            f"Missing tables: {sorted(required_tables - covered_tables)}"
        )
    if not columns_ok:
        missing.append(
            f"Missing columns: {sorted(required_columns - covered_columns)}"
        )
    if not relations_ok:
        missing.append(
            f"Missing relations: {sorted(required_relations - covered_relations)}"
        )

    return {
        "is_sufficient": is_sufficient,
        "schema_coverage": {
            "tables_ok": tables_ok,
            "columns_ok": columns_ok,
            "relations_ok": relations_ok,
            "question_family_ok": question_family_ok,
        },
        "example_coverage": {
            "required": example_required,
            "pattern_match_ok": pattern_match_ok,
        },
        "missing": missing,
    }
