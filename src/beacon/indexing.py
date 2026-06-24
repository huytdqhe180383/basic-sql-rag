"""Build semantic and few-shot retrieval indices."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding

from beacon.config import (
    FEW_SHOT_INDEX_DIR,
    FEW_SHOT_QUERIES_PATH,
    LOCAL_VECTOR_INDEX_DIR,
    SCHEMA_INDEX_DIR,
)
from beacon.embeddings import HashEmbeddingAdapter, default_embedding_adapter
from beacon.indexing_tools import (
    build_example_docs,
    build_schema_docs,
    enrich_semantic_model_files,
    load_json,
)
from beacon.schema_index import build_schema_records
from beacon.vector_store import save_vector_index


def persist_index(docs: list[dict], persist_dir: Path) -> None:
    """Persist one vector index from plain retrieval docs."""
    llama_docs = [Document(text=doc["text"], metadata=doc["metadata"]) for doc in docs]
    index = VectorStoreIndex.from_documents(llama_docs)
    index.storage_context.persist(str(persist_dir))


def configure_embeddings() -> None:
    """Configure the embedding model used to build local indices."""
    load_dotenv(override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    Settings.embed_model = OpenAIEmbedding(
        api_key=api_key,
        api_base=os.getenv("OPENAI_API_BASE"),
        model="text-embedding-3-small",
    )


def build_indices() -> dict:
    """Build schema and example indices from semantic JSON artifacts."""
    semantic_model = enrich_semantic_model_files()

    persist_local_schema_vectors(semantic_model)
    built_legacy = False
    if os.getenv("BEACON_BUILD_LEGACY_LLAMA_INDEX") == "1":
        few_shot = load_json(FEW_SHOT_QUERIES_PATH)
        configure_embeddings()
        persist_index(build_schema_docs(semantic_model), SCHEMA_INDEX_DIR)
        persist_index(build_example_docs(few_shot, semantic_model), FEW_SHOT_INDEX_DIR)
        built_legacy = True
    return {"local_vectors": True, "legacy_llama_index": built_legacy}


def persist_local_schema_vectors(semantic_model: list[dict]) -> None:
    """Build Beacon's lightweight local vector schema index."""
    schema_records = build_schema_records(semantic_model)
    try:
        embedder = default_embedding_adapter()
    except Exception:
        embedder = HashEmbeddingAdapter()
    schema_vectors = embedder.embed_texts([record["text"] for record in schema_records])
    save_vector_index(
        LOCAL_VECTOR_INDEX_DIR,
        schema_records,
        schema_vectors,
        {"model": embedder.model_name, "kind": "schema"},
    )


def main() -> None:
    """CLI entry point for rebuilding Beacon retrieval indices."""
    result = build_indices()
    if result["legacy_llama_index"]:
        print("Built local schema vectors and legacy schema/few-shot indices.")
    else:
        print("Built local schema vectors.")


if __name__ == "__main__":
    main()
