"""Consistency tests for schema sources and index documents."""

import csv
import json
import re
from pathlib import Path

from build_index import build_schema_docs


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EXPECTED_TABLES = {
    "customers",
    "orders",
    "order_items",
    "products",
    "geography",
    "sales",
    "inventory",
}


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_semantic_model_matches_csv_headers():
    """Every semantic table should exactly describe its local CSV columns."""
    model = _load_json(DATA / "semantic_model.json")
    assert {entry["source_table"] for entry in model} == EXPECTED_TABLES

    for entry in model:
        csv_path = DATA / "processed" / f"{entry['source_table']}.csv"
        with csv_path.open(encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle))
        assert [column["name"] for column in entry["columns"]] == header


def test_few_shot_examples_use_supported_shape_and_patterns():
    """The curated example set should stay small and use the planned vocabulary."""
    examples = _load_json(DATA / "few_shot_queries.json")
    allowed_patterns = {
        "single_table_count",
        "single_table_date_filter",
        "group_by_category",
        "customer_orders_join",
        "orders_items_join",
        "revenue_calculation",
        "top_n",
        "geography_breakdown",
        "product_breakdown",
        "inventory_health",
        "daily_sales_aggregate",
    }

    assert 10 <= len(examples) <= 16
    for example in examples:
        assert set(example) == {
            "question",
            "sql",
            "tables",
            "pattern",
            "question_families",
        }
        assert example["pattern"] in allowed_patterns
        assert set(example["tables"]).issubset(EXPECTED_TABLES)
        for table in example["tables"]:
            assert re.search(
                rf"\b(?:FROM|JOIN)\s+{re.escape(table)}\b",
                example["sql"],
                flags=re.IGNORECASE,
            )


def test_schema_documents_keep_structured_columns_and_relations():
    """Index documents should expose coverage data as metadata."""
    model = _load_json(DATA / "semantic_model.json")
    docs = build_schema_docs(model)

    assert len(docs) == 7
    for entry, doc in zip(model, docs):
        assert doc.metadata["columns"] == [c["name"] for c in entry["columns"]]
        assert doc.metadata["relations"] == [
            f"{relation['from']} -> {relation['to']}"
            for relation in entry["relations"]
        ]


def test_sql_schema_declares_the_expected_foreign_keys():
    """The public SQL schema should encode the documented relation graph."""
    sql = (ROOT / "sql" / "00_simple_schema.sql").read_text(encoding="utf-8")
    expected_references = {
        "REFERENCES public.geography(zip)",
        "REFERENCES public.customers(customer_id)",
        "REFERENCES public.orders(order_id)",
        "REFERENCES public.products(product_id)",
    }
    for reference in expected_references:
        assert reference in sql
