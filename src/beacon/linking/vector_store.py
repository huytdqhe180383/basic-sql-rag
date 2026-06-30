"""Tiny NumPy-backed vector store for local schema retrieval."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


RECORDS_FILE = "schema_records.json"
VECTORS_FILE = "schema_vectors.npy"
MANIFEST_FILE = "schema_manifest.json"


def save_vector_index(index_dir: Path, records: list[dict], vectors, manifest: dict) -> None:
    """Persist records, vectors, and a small manifest under one directory."""
    index_dir.mkdir(parents=True, exist_ok=True)
    matrix = normalize_rows(np.asarray(vectors, dtype="float32"))
    with (index_dir / RECORDS_FILE).open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with (index_dir / MANIFEST_FILE).open("w", encoding="utf-8") as handle:
        json.dump(
            {**manifest, "record_count": len(records), "dimensions": vector_dimensions(matrix)},
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
    np.save(index_dir / VECTORS_FILE, matrix)


def load_vector_index(index_dir: Path) -> dict:
    """Load a vector index persisted by `save_vector_index`."""
    with (index_dir / RECORDS_FILE).open(encoding="utf-8") as handle:
        records = json.load(handle)
    with (index_dir / MANIFEST_FILE).open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    vectors = np.load(index_dir / VECTORS_FILE)
    return {"records": records, "vectors": vectors, "manifest": manifest}


def vector_index_exists(index_dir: Path) -> bool:
    """Return whether all vector index files exist."""
    return all(
        (index_dir / name).exists()
        for name in (RECORDS_FILE, VECTORS_FILE, MANIFEST_FILE)
    )


def search_vector_index(index: dict, query_vector, top_k: int = 10) -> list[dict]:
    """Return top vector records by cosine similarity."""
    vectors = normalize_rows(np.asarray(index["vectors"], dtype="float32"))
    if vectors.size == 0:
        return []
    query = np.asarray(query_vector, dtype="float32")
    query = query / (float(np.linalg.norm(query)) or 1.0)
    scores = vectors @ query
    order = np.argsort(-scores)[:top_k]
    return [
        {"record": index["records"][int(i)], "score": float(scores[int(i)])}
        for i in order
    ]


def normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """Normalize vector rows for cosine search."""
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    if matrix.size == 0:
        return matrix.astype("float32")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype("float32")


def vector_dimensions(matrix: np.ndarray) -> int:
    """Return vector dimension count for manifest metadata."""
    if matrix.ndim == 1:
        return int(matrix.shape[0])
    if matrix.ndim == 2 and matrix.shape:
        return int(matrix.shape[1])
    return 0
