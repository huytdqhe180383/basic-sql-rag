"""Retrieve schema/examples and assemble prompts for Beacon questions."""

from __future__ import annotations

import os

from llama_index.core import Settings, StorageContext, load_index_from_storage
from llama_index.embeddings.openai import OpenAIEmbedding

from beacon.config import FEW_SHOT_INDEX_DIR, SCHEMA_INDEX_DIR
from beacon.indexing_tools import build_schema_docs, load_semantic_model
from beacon.metadata_grounding import (
    apply_grounding_to_needs,
    format_matched_evidence,
    ground_question_metadata,
)
from beacon.retrieval_tools import (
    assess_coverage,
    extract_question_needs,
    matching_examples,
    rank_docs,
)


SCHEMA_K_START = 2
SCHEMA_K_MAX = 5
EXAMPLE_K_START = 1
EXAMPLE_K_MAX = 2


def load_indices():
    """Load persisted schema and few-shot indices."""
    embed_model = OpenAIEmbedding(
        api_key=os.getenv("OPENAI_API_KEY"),
        api_base=os.getenv("OPENAI_API_BASE"),
        model="text-embedding-3-small",
    )
    Settings.embed_model = embed_model
    schema_index = load_index_from_storage(
        StorageContext.from_defaults(persist_dir=str(SCHEMA_INDEX_DIR))
    )
    example_index = load_index_from_storage(
        StorageContext.from_defaults(persist_dir=str(FEW_SHOT_INDEX_DIR))
    )
    return schema_index, example_index


def retrieve_nodes(index, question: str, k: int) -> list[dict]:
    """Retrieve nodes from a LlamaIndex index as plain dictionaries."""
    return [
        {"text": node.text, "metadata": node.metadata}
        for node in index.as_retriever(similarity_top_k=k).retrieve(question)
    ]


def retrieve_schema_until_covered(
    schema_index,
    question: str,
    needs: dict,
    forced_docs: list[dict] | None = None,
) -> tuple[list[dict], dict]:
    """Expand schema retrieval until inferred needs are covered or the limit is reached."""
    forced_docs = forced_docs or []
    schema_docs: list[dict] = []
    coverage = {"is_sufficient": False, "missing": {}}

    for k in range(SCHEMA_K_START, SCHEMA_K_MAX + 1):
        retrieved = retrieve_nodes(schema_index, question, k)
        retrieved = merge_schema_docs(retrieved, forced_docs)
        schema_docs = rank_docs(question, retrieved, needs)
        coverage = assess_coverage(needs, schema_docs)
        if coverage["is_sufficient"]:
            break
    return schema_docs, coverage


def retrieve_matching_examples(example_index, question: str, needs: dict, coverage: dict) -> list[dict]:
    """Retrieve examples only after schema coverage is sufficient."""
    if not coverage["is_sufficient"] or not needs["example_patterns"]:
        return []

    for k in range(EXAMPLE_K_START, EXAMPLE_K_MAX + 1):
        examples = matching_examples(
            retrieve_nodes(example_index, question, k),
            needs["example_patterns"],
            question,
        )
        if examples:
            return examples
    return []


def retrieve_context(question: str) -> dict:
    """Retrieve schema and optional example context for one question."""
    needs = extract_question_needs(question)
    semantic_model = load_semantic_model()
    matched_evidence = ground_question_metadata(question, semantic_model)
    needs = apply_grounding_to_needs(needs, matched_evidence)
    forced_docs = schema_docs_for_tables(build_schema_docs(semantic_model), needs["tables"])
    schema_index, example_index = load_indices()

    schema_docs, coverage = retrieve_schema_until_covered(schema_index, question, needs, forced_docs)
    example_docs = retrieve_matching_examples(example_index, question, needs, coverage)
    coverage = assess_coverage(needs, schema_docs, example_docs)

    return {
        "question_needs": needs,
        "schema_docs": schema_docs,
        "example_docs": example_docs,
        "schema_coverage": coverage,
        "matched_evidence": matched_evidence,
    }


def schema_docs_for_tables(schema_docs: list[dict], tables: set[str]) -> list[dict]:
    """Return schema docs for required tables from a full schema-doc list."""
    return [
        doc
        for doc in schema_docs
        if doc.get("metadata", {}).get("table") in tables
    ]


def merge_schema_docs(retrieved_docs: list[dict], forced_docs: list[dict]) -> list[dict]:
    """Append forced table docs while preserving first occurrence order."""
    merged: list[dict] = []
    seen_tables: set[str] = set()
    for doc in retrieved_docs + forced_docs:
        table = doc.get("metadata", {}).get("table")
        if table and table in seen_tables:
            continue
        if table:
            seen_tables.add(table)
        merged.append(doc)
    return merged


def build_prompt(question: str, context: dict) -> str:
    """Build the final SQL prompt from retrieved schema and examples."""
    sections = []
    evidence = format_matched_evidence(context.get("matched_evidence", []))
    if evidence:
        sections.append(evidence)
    sections.append("RELEVANT SCHEMA:")
    sections.extend(doc["text"] for doc in context.get("schema_docs", []))
    if context.get("example_docs"):
        sections.append("EXAMPLE QUERIES:")
        sections.extend(doc["text"] for doc in context["example_docs"])
    sections.extend([f"QUESTION: {question}", "SQL:"])
    return "\n\n---\n\n".join(sections)
