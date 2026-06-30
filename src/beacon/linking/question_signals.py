"""Generic question signal extraction for schema linking."""

from __future__ import annotations

import re


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "by",
    "for",
    "from",
    "get",
    "give",
    "how",
    "in",
    "is",
    "list",
    "me",
    "of",
    "on",
    "or",
    "show",
    "the",
    "to",
    "what",
    "which",
    "with",
}

INTENT_PHRASES = {
    "aggregation": {"total", "sum", "average", "avg", "count", "how many", "revenue", "sales"},
    "group_by": {"by", "per", "each", "breakdown"},
    "top_n": {"top", "most", "highest", "largest", "best"},
    "bottom_n": {"bottom", "least", "lowest", "smallest", "worst"},
    "comparison": {"compare", "versus", "vs", "difference", "more than", "less than"},
}

METRIC_PHRASES = {
    "revenue": {"revenue", "sales", "gross sales"},
    "cogs": {"cost", "cogs", "cost of goods", "expense"},
    "profit": {"profit", "profitable", "profitability"},
    "count": {"count", "how many", "number of"},
    "average": {"average", "avg", "mean"},
    "quantity": {"quantity", "sold", "units"},
    "discount": {"discount", "discounted"},
    "fill_rate": {"fill rate"},
    "sell_through_rate": {"sell through", "sell-through"},
    "stock_on_hand": {"stock", "inventory", "overstock", "overstocked", "reorder"},
}

FILTER_PHRASES = {
    "date_filter": {"today", "yesterday", "last", "current", "year", "month", "quarter", "week"},
    "status_filter": {"status", "state"},
    "payment_filter": {"payment", "pay"},
    "customer_filter": {"customer", "buyer"},
    "product_filter": {"product", "category", "segment", "color", "size"},
}

TIME_GRAIN_PHRASES = [
    ("day", {"daily", "by day", "per day", "each day"}),
    ("month", {"monthly", "by month", "per month", "month"}),
    ("quarter", {"quarterly", "quarter"}),
    ("year", {"yearly", "by year", "per year", "year", "last year", "this year", "current year"}),
]


def extract_question_signals(question: str, semantic_model: list[dict] | None = None) -> dict:
    """Return generic intent, metric, value, and weak schema signals."""
    text = normalize(question)
    terms = question_terms(text)
    intents = {label for label, phrases in INTENT_PHRASES.items() if has_any(text, phrases)}
    metrics = {label for label, phrases in METRIC_PHRASES.items() if has_any(text, phrases)}
    filters = {label for label, phrases in FILTER_PHRASES.items() if has_any(text, phrases)}
    dates = extract_dates(text)
    numbers = extract_numbers(text)
    time_grain = first_time_grain(text, dates)
    if dates or time_grain:
        filters.add("date_filter")
    entities = extract_entity_phrases(question)
    weak_tables, weak_columns = weak_schema_matches(text, semantic_model or [])
    reasons = sorted(
        [f"intent:{item}" for item in intents]
        + [f"metric:{item}" for item in metrics]
        + [f"filter:{item}" for item in filters]
        + ([f"time_grain:{time_grain}"] if time_grain else [])
    )
    return {
        "terms": sorted(terms),
        "entities": entities,
        "dates": dates,
        "numbers": numbers,
        "intents": intents,
        "metrics": metrics,
        "filters": filters,
        "time_grain": time_grain,
        "weak_tables": weak_tables,
        "weak_columns": weak_columns,
        "reasons": reasons,
    }


def normalize(value: str) -> str:
    """Normalize question/schema text for light lexical matching."""
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())


def has_any(text: str, phrases: set[str]) -> bool:
    """Return whether any phrase appears as a word-bounded phrase."""
    return any(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) for phrase in phrases)


def question_terms(text: str) -> set[str]:
    """Return meaningful lowercase terms from normalized text."""
    return {
        term
        for term in re.findall(r"[a-z][a-z0-9]*", text)
        if term not in STOPWORDS and len(term) > 1
    }


def extract_dates(text: str) -> list[dict]:
    """Extract simple year references without treating them as generic numbers."""
    return [
        {"text": match.group(0), "kind": "year", "value": int(match.group(0))}
        for match in re.finditer(r"\b(?:19|20)\d{2}\b", text)
    ]


def extract_numbers(text: str) -> list[dict]:
    """Extract numeric mentions and label obvious top/bottom limits."""
    numbers = []
    for match in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
        raw = match.group(0)
        if re.fullmatch(r"(?:19|20)\d{2}", raw):
            continue
        value = float(raw) if "." in raw else int(raw)
        before = text[max(0, match.start() - 16) : match.start()]
        role = "limit" if "top" in before or "bottom" in before else "number"
        numbers.append({"text": raw, "value": value, "role": role})
    return numbers


def first_time_grain(text: str, dates: list[dict]) -> str | None:
    """Return the first explicit time grain, falling back to year for year literals."""
    for label, phrases in TIME_GRAIN_PHRASES:
        if has_any(text, phrases):
            return label
    return "year" if dates else None


def extract_entity_phrases(question: str) -> list[str]:
    """Extract capitalized phrases that may be values or named entities."""
    entities = set(re.findall(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*\b", question))
    return sorted(entity for entity in entities if entity.lower() not in STOPWORDS)


def weak_schema_matches(text: str, semantic_model: list[dict]) -> tuple[dict, dict]:
    """Score weak lexical overlaps between question terms and semantic metadata."""
    tables: dict[str, float] = {}
    columns: dict[str, float] = {}
    terms = question_terms(text)
    for table in semantic_model:
        table_name = table.get("source_table", "")
        table_text = normalize(
            " ".join([table_name, table.get("semantic_name", ""), table.get("description", "")])
        )
        overlap = terms & question_terms(table_text)
        if overlap:
            tables[table_name] = round(min(0.2 + 0.1 * len(overlap), 0.7), 2)
        for column in table.get("columns", []):
            column_name = column.get("name", "")
            column_text = normalize(" ".join([column_name, column.get("description", "")]))
            column_overlap = terms & question_terms(column_text)
            if column_overlap:
                columns[column_name] = round(
                    min(0.2 + 0.1 * len(column_overlap), 0.7),
                    2,
                )
    return tables, columns
