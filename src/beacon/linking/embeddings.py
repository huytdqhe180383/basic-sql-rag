"""Small embedding adapters used by Beacon retrieval."""

from __future__ import annotations

import hashlib
import os
import re

import numpy as np


DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class HashEmbeddingAdapter:
    """Deterministic local embeddings for tests and offline smoke checks."""

    def __init__(self, dimensions: int = 128):
        self.dimensions = dimensions
        self.model_name = f"hash-{dimensions}"

    def embed_text(self, text: str) -> np.ndarray:
        """Embed one text string."""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed many text strings with stable token hashing."""
        rows = []
        for text in texts:
            vector = np.zeros(self.dimensions, dtype="float32")
            for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()):
                digest = hashlib.md5(token.encode("utf-8")).hexdigest()
                index = int(digest[:8], 16) % self.dimensions
                vector[index] += 1.0
            rows.append(normalize_vector(vector))
        return np.vstack(rows) if rows else np.zeros((0, self.dimensions), dtype="float32")


class SentenceTransformerEmbeddingAdapter:
    """Production local embedding adapter backed by sentence-transformers."""

    def __init__(self, model_name: str | None = None):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name or os.getenv("BEACON_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        self.model = SentenceTransformer(self.model_name)

    def embed_text(self, text: str) -> np.ndarray:
        """Embed one text string."""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed many text strings with normalized sentence-transformer vectors."""
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype="float32")


def default_embedding_adapter():
    """Return the configured production embedder, with an explicit hash opt-in."""
    if os.getenv("BEACON_USE_HASH_EMBEDDINGS") == "1":
        return HashEmbeddingAdapter()
    return SentenceTransformerEmbeddingAdapter()


def normalize_vector(vector: np.ndarray) -> np.ndarray:
    """Return a safely normalized float32 vector."""
    norm = float(np.linalg.norm(vector)) or 1.0
    return (vector / norm).astype("float32")
