from beacon.linking.embeddings import HashEmbeddingAdapter
from beacon.linking.schema_index import build_schema_records
from beacon.linking.schema_linking import link_schema
from beacon.linking.vector_store import save_vector_index


SEMANTIC_MODEL = [
    {
        "source_table": "orders",
        "semantic_name": "Orders",
        "grain": "one row per order",
        "description": "Customer orders and payment methods.",
        "columns": [
            {"name": "order_id", "type": "INTEGER", "description": "Order id.", "profile": {}},
            {
                "name": "payment_method",
                "type": "TEXT",
                "description": "Payment method.",
                "profile": {"sample_values": ["apple_pay"]},
            },
        ],
        "relations": [{"from": "orders.order_id", "to": "order_items.order_id"}],
    },
    {
        "source_table": "order_items",
        "semantic_name": "Order Items",
        "grain": "one row per line item",
        "description": "Products purchased in orders.",
        "columns": [
            {"name": "order_id", "type": "INTEGER", "description": "Order id.", "profile": {}},
            {"name": "quantity", "type": "INTEGER", "description": "Quantity purchased.", "profile": {}},
        ],
        "relations": [],
    },
]


def test_link_schema_combines_grounding_vector_and_join_paths(tmp_path):
    embedder = HashEmbeddingAdapter(dimensions=32)
    records = build_schema_records(SEMANTIC_MODEL)
    vectors = embedder.embed_texts([record["text"] for record in records])
    save_vector_index(tmp_path, records, vectors, {"model": "hash-test"})

    context = link_schema(
        "How many Apple Pay purchases?",
        SEMANTIC_MODEL,
        vector_index_dir=tmp_path,
        embedder=embedder,
    )

    assert "orders" in context["selected_tables"]
    assert "payment_method" in {item["column"] for item in context["selected_columns"]}
    assert context["coverage"]["is_sufficient"] is True
    assert context["evidence"][0]["term"] == "apple pay"
