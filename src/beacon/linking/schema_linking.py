"""Hybrid metadata-grounded schema linking."""

from __future__ import annotations

from pathlib import Path

from beacon.config import LOCAL_VECTOR_INDEX_DIR
from beacon.indexing.profiles import build_schema_docs
from beacon.linking.compatibility import extract_question_needs
from beacon.linking.embeddings import HashEmbeddingAdapter, default_embedding_adapter
from beacon.linking.example_retrieval import rank_examples
from beacon.linking.metadata_grounding import ground_question_metadata
from beacon.linking.question_signals import extract_question_signals
from beacon.linking.schema_graph import build_schema_graph, relation_paths
from beacon.linking.schema_index import build_schema_records
from beacon.linking.vector_store import load_vector_index, search_vector_index, vector_index_exists


__all__ = ["link_schema"]


def link_schema(
    question: str,
    semantic_model: list[dict],
    vector_index_dir: Path = LOCAL_VECTOR_INDEX_DIR,
    embedder=None,
    few_shot_examples: list[dict] | None = None,
    top_k: int = 12,
) -> dict:
    """Return linked schema context for SQL generation."""
    signals = extract_question_signals(question, semantic_model)
    evidence = ground_question_metadata(question, semantic_model)
    fallback_needs = filtered_fallback_needs(question, semantic_model)
    vector_hits = retrieve_vector_hits(
        question,
        semantic_model,
        vector_index_dir=vector_index_dir,
        embedder=embedder,
        top_k=top_k,
    )

    selected_tables: set[str] = set()
    selected_columns: list[dict] = []
    warnings: list[str] = []

    add_evidence_selection(evidence, selected_tables, selected_columns)
    add_signal_selection(signals, selected_tables, selected_columns)
    add_vector_selection(vector_hits, selected_tables, selected_columns)
    add_fallback_selection(fallback_needs, selected_tables, selected_columns)

    ambiguous = [item for item in evidence if item.get("status") == "ambiguous"]
    if ambiguous:
        warnings.append("Grounding has ambiguous candidates; evidence was not pinned.")

    graph = build_schema_graph(semantic_model)
    joins = relation_paths(graph, selected_tables, max_hops=3)
    add_join_columns(joins, selected_tables, selected_columns)

    schema_docs = docs_for_tables(build_schema_docs(semantic_model), selected_tables)
    linked = {
        "question": question,
        "signals": signals,
        "evidence": evidence,
        "selected_tables": sorted(selected_tables),
        "selected_columns": dedupe_columns(selected_columns),
        "join_paths": joins,
        "schema_docs": schema_docs,
        "example_docs": [],
        "coverage": assess_linked_coverage(selected_tables, selected_columns, joins, warnings),
        "fallback_needs": fallback_needs,
    }
    linked["example_docs"] = rank_examples(question, few_shot_examples or [], linked, limit=2)
    return linked


def retrieve_vector_hits(
    question: str,
    semantic_model: list[dict],
    vector_index_dir: Path,
    embedder=None,
    top_k: int = 12,
) -> list[dict]:
    """Search persisted vectors, falling back to an in-memory hash index."""
    records = build_schema_records(semantic_model)
    if not records:
        return []

    if embedder is not None:
        return search_records(question, records, embedder, vector_index_dir, top_k)

    if vector_index_exists(vector_index_dir):
        try:
            return search_records(question, records, default_embedding_adapter(), vector_index_dir, top_k)
        except Exception:
            pass

    return search_ephemeral_records(question, records, top_k)


def search_records(
    question: str,
    records: list[dict],
    embedder,
    vector_index_dir: Path,
    top_k: int,
) -> list[dict]:
    """Search a persisted index when present, otherwise build an in-memory one."""
    if vector_index_exists(vector_index_dir):
        index = load_vector_index(vector_index_dir)
        try:
            return search_vector_index(index, embedder.embed_text(question), top_k=top_k)
        except ValueError:
            return search_ephemeral_records(question, records, top_k)
    vectors = embedder.embed_texts([record["text"] for record in records])
    index = {"records": records, "vectors": vectors, "manifest": {"model": embedder.model_name}}
    return search_vector_index(index, embedder.embed_text(question), top_k=top_k)


def search_ephemeral_records(question: str, records: list[dict], top_k: int) -> list[dict]:
    """Search semantic records with deterministic hash embeddings."""
    embedder = HashEmbeddingAdapter()
    vectors = embedder.embed_texts([record["text"] for record in records])
    index = {"records": records, "vectors": vectors, "manifest": {"model": embedder.model_name}}
    return search_vector_index(index, embedder.embed_text(question), top_k=top_k)


def filtered_fallback_needs(question: str, semantic_model: list[dict]) -> dict:
    """Return old demo classifier output filtered to tables/columns in this schema."""
    known_tables = {table["source_table"] for table in semantic_model}
    known_columns = {
        column["name"]
        for table in semantic_model
        for column in table.get("columns", [])
    }
    needs = extract_question_needs(question)
    return {
        "tables": set(needs.get("tables", set())) & known_tables,
        "columns": set(needs.get("columns", set())) & known_columns,
        "relations": set(needs.get("relations", set())),
        "example_patterns": set(needs.get("example_patterns", set())),
    }


def add_evidence_selection(evidence: list[dict], tables: set[str], columns: list[dict]) -> None:
    """Promote pinned evidence into selected tables and columns."""
    for item in evidence:
        if item.get("pin"):
            tables.add(item["table"])
            columns.append(
                {
                    "table": item["table"],
                    "column": item["column"],
                    "reason": "pinned evidence",
                    "score": item.get("score", 0),
                }
            )


def add_signal_selection(signals: dict, tables: set[str], columns: list[dict]) -> None:
    """Add weak lexical schema matches from generic question signals."""
    for table, score in signals.get("weak_tables", {}).items():
        if score >= 0.3:
            tables.add(table)
    for qualified, score in signals.get("weak_columns", {}).items():
        if score < 0.3:
            continue
        if "." in qualified:
            table, column = qualified.split(".", 1)
            tables.add(table)
        else:
            table, column = "", qualified
        columns.append({"table": table, "column": column, "reason": "weak lexical match", "score": score})


def add_vector_selection(vector_hits: list[dict], tables: set[str], columns: list[dict]) -> None:
    """Add schema candidates from vector hits."""
    for hit in vector_hits:
        metadata = hit["record"]["metadata"]
        table = metadata.get("table")
        column = metadata.get("column")
        score = hit.get("score", 0)
        if table and score >= 0.05:
            tables.add(table)
        if table and column and score >= 0.05:
            columns.append({"table": table, "column": column, "reason": "vector", "score": score})


def add_fallback_selection(needs: dict, tables: set[str], columns: list[dict]) -> None:
    """Add filtered old-classifier hints as a compatibility fallback."""
    for table in needs.get("tables", set()):
        tables.add(table)
    for column in needs.get("columns", set()):
        columns.append({"table": "", "column": column, "reason": "compatibility fallback", "score": 0.4})


def add_join_columns(joins: list[str], tables: set[str], columns: list[dict]) -> None:
    """Add bridge tables and join columns from relation strings."""
    for relation in joins:
        for side in relation.split(" -> "):
            if "." not in side:
                continue
            table, column = side.split(".", 1)
            tables.add(table)
            columns.append({"table": table, "column": column, "reason": "join path", "score": 1.0})


def docs_for_tables(schema_docs: list[dict], tables: set[str]) -> list[dict]:
    """Return schema docs for selected tables in semantic-model order."""
    return [
        doc
        for doc in schema_docs
        if doc.get("metadata", {}).get("table") in tables
    ]


def dedupe_columns(columns: list[dict]) -> list[dict]:
    """Deduplicate selected columns while preserving the strongest reason."""
    seen = set()
    output = []
    for item in sorted(
        columns,
        key=lambda value: (-float(value.get("score", 0)), value.get("table", ""), value["column"]),
    ):
        key = (item.get("table", ""), item["column"])
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def assess_linked_coverage(
    tables: set[str],
    columns: list[dict],
    joins: list[str],
    warnings: list[str] | None = None,
) -> dict:
    """Return a lightweight coverage report for linked context."""
    warnings = list(warnings or [])
    if not tables:
        warnings.append("No schema tables selected.")
    confidence = "high" if tables and columns else "medium" if tables else "low"
    return {
        "is_sufficient": bool(tables),
        "confidence": confidence,
        "missing": {"tables": [], "columns": [], "relations": []},
        "warnings": warnings,
        "join_count": len(joins),
    }
