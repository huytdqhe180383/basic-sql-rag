from pathlib import Path

from beacon import config
from beacon.embeddings import HashEmbeddingAdapter
from beacon.indexing import persist_local_schema_vectors
from beacon.vector_store import load_vector_index, save_vector_index, search_vector_index


def test_local_vector_paths_are_defined_under_data_indices():
    assert config.LOCAL_VECTOR_INDEX_DIR == config.INDEX_DIR / "local_vectors"
    assert config.SCHEMA_VECTOR_RECORDS_PATH == config.LOCAL_VECTOR_INDEX_DIR / "schema_records.json"
    assert config.SCHEMA_VECTOR_MATRIX_PATH == config.LOCAL_VECTOR_INDEX_DIR / "schema_vectors.npy"
    assert config.SCHEMA_VECTOR_MANIFEST_PATH == config.LOCAL_VECTOR_INDEX_DIR / "schema_manifest.json"


def test_numpy_vector_store_round_trips_and_searches(tmp_path: Path):
    records = [
        {
            "id": "orders.order_id",
            "text": "orders order id primary key",
            "metadata": {"table": "orders", "column": "order_id"},
        },
        {
            "id": "products.category",
            "text": "products category clothing segment",
            "metadata": {"table": "products", "column": "category"},
        },
    ]
    embedder = HashEmbeddingAdapter(dimensions=16)
    vectors = embedder.embed_texts([record["text"] for record in records])

    save_vector_index(tmp_path, records, vectors, {"model": "hash-test"})
    loaded = load_vector_index(tmp_path)
    results = search_vector_index(loaded, embedder.embed_text("clothing category"), top_k=1)

    assert results[0]["record"]["id"] == "products.category"
    assert results[0]["score"] > 0


def test_persist_local_schema_vectors_writes_expected_files(monkeypatch, tmp_path: Path):
    semantic_model = [
        {
            "source_table": "orders",
            "semantic_name": "Orders",
            "grain": "one row per order",
            "description": "Orders.",
            "columns": [{"name": "order_id", "type": "INTEGER", "description": "Order id."}],
        }
    ]

    monkeypatch.setattr("beacon.indexing.LOCAL_VECTOR_INDEX_DIR", tmp_path)
    monkeypatch.setattr("beacon.indexing.default_embedding_adapter", lambda: HashEmbeddingAdapter(dimensions=16))

    persist_local_schema_vectors(semantic_model)

    assert (tmp_path / "schema_records.json").exists()
    assert (tmp_path / "schema_vectors.npy").exists()
    assert (tmp_path / "schema_manifest.json").exists()
