"""Tests for compact semantic profiling."""

import shutil
from pathlib import Path

from beacon.indexing import build_schema_docs, load_semantic_model, profile_table_rows


def test_load_semantic_model_reads_one_file_per_table():
    """Semantic metadata should live as small per-table JSON files."""
    model_dir = Path("tests") / "_tmp_semantic_model"
    if model_dir.exists():
        shutil.rmtree(model_dir)
    try:
        model_dir.mkdir()
        (model_dir / "orders.json").write_text(
            '{"source_table": "orders", "columns": []}',
            encoding="utf-8",
        )
        (model_dir / "customers.json").write_text(
            '{"source_table": "customers", "columns": []}',
            encoding="utf-8",
        )

        model = load_semantic_model(model_dir)

        assert [entry["source_table"] for entry in model] == ["customers", "orders"]
    finally:
        if model_dir.exists():
            shutil.rmtree(model_dir)


def test_profile_table_rows_summarizes_common_column_types():
    columns = [
        {"name": "id", "type": "INTEGER", "description": "Identifier"},
        {"name": "amount", "type": "NUMERIC(14,2)", "description": "Amount"},
        {"name": "status", "type": "TEXT", "description": "Status"},
        {"name": "created_at", "type": "DATE", "description": "Created date"},
        {"name": "is_active", "type": "BOOLEAN", "description": "Active flag"},
    ]
    rows = [
        {"id": "1", "amount": "10.0", "status": "new", "created_at": "2025-01-01", "is_active": "true"},
        {"id": "2", "amount": "20.0", "status": "new", "created_at": "2025-01-03", "is_active": "false"},
        {"id": "3", "amount": "", "status": "done", "created_at": "2025-01-02", "is_active": "true"},
    ]

    profile = profile_table_rows(rows, columns)

    assert len(profile["sample_rows"]) == 3
    assert profile["columns"]["amount"]["min"] == 10.0
    assert profile["columns"]["amount"]["max"] == 20.0
    assert profile["columns"]["amount"]["mean"] == 15.0
    assert profile["columns"]["amount"]["null_count"] == 1
    assert profile["columns"]["status"]["top_values"][0] == {"value": "new", "count": 2}
    assert profile["columns"]["created_at"]["min"] == "2025-01-01"
    assert profile["columns"]["created_at"]["max"] == "2025-01-03"
    assert profile["columns"]["is_active"]["value_counts"] == {"false": 1, "true": 2}


def test_build_schema_docs_includes_profiles_and_sample_rows():
    semantic_model = [
        {
            "source_table": "products",
            "semantic_name": "Products",
            "grain": "one row per product",
            "description": "Product table",
            "sample_rows": [{"product_id": "1", "category": "Electronics"}],
            "columns": [
                {
                    "name": "category",
                    "type": "TEXT",
                    "description": "Product category",
                    "profile": {
                        "null_count": 0,
                        "distinct_count": 2,
                        "sample_values": ["Electronics", "Clothing"],
                        "top_values": [{"value": "Electronics", "count": 10}],
                    },
                }
            ],
            "relations": [],
            "question_families": ["product_breakdown"],
        }
    ]

    docs = build_schema_docs(semantic_model)

    assert "top_values=Electronics:10" in docs[0]["text"]
    assert "Sample rows" in docs[0]["text"]
    assert docs[0]["metadata"]["table"] == "products"
