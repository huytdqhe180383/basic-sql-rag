"""Build semantic and few-shot retrieval indices."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding

from beacon.config import FEW_SHOT_INDEX_DIR, FEW_SHOT_QUERIES_PATH, SCHEMA_INDEX_DIR
from beacon.indexing_tools import (
    build_example_docs,
    build_schema_docs,
    enrich_semantic_model_files,
    load_json,
)


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


def build_indices() -> None:
    """Build schema and example indices from semantic JSON artifacts."""
    configure_embeddings()
    semantic_model = enrich_semantic_model_files()
    few_shot = load_json(FEW_SHOT_QUERIES_PATH)

    persist_index(build_schema_docs(semantic_model), SCHEMA_INDEX_DIR)
    persist_index(build_example_docs(few_shot, semantic_model), FEW_SHOT_INDEX_DIR)


def main() -> None:
    """CLI entry point for rebuilding Beacon retrieval indices."""
    build_indices()
    print("Built schema and few-shot indices.")
