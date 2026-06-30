"""Semantic profile and vector-index build entrypoints."""

from beacon.indexing.builder import build_indices, main, persist_local_schema_vectors

__all__ = ["build_indices", "main", "persist_local_schema_vectors"]

