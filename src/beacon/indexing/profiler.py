"""CLI entry point for refreshing Beacon semantic profiles."""

from __future__ import annotations

from beacon.indexing.profiles import enrich_semantic_model_files


def main() -> None:
    """Refresh per-table semantic JSON profiles from processed CSV files."""
    tables = enrich_semantic_model_files()
    print(f"Profiled {len(tables)} semantic tables.")


if __name__ == "__main__":
    main()
