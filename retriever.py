"""
Retriever with adaptive expansion for NL-to-SQL context assembly.

Loads schema and few-shot vector indices, retrieves context with
bounded adaptive expansion, and assembles a prompt-ready context dict.
"""

import os

from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.embeddings.openai import OpenAIEmbedding

from coverage import extract_question_needs, assess_coverage

# Configurable bounds
SCHEMA_K_START = 2
SCHEMA_K_MAX = 5
EXAMPLE_K_START = 1
EXAMPLE_K_MAX = 2

SCHEMA_INDEX_PATH = "data/indices/schema"
EXAMPLE_INDEX_PATH = "data/indices/few_shot"


def _load_indices():
    """Load schema and example indices from disk.

    Returns (schema_index, example_index) tuple.
    """
    embed_model = OpenAIEmbedding(
        api_key=os.getenv("OPENAI_API_KEY"),
        api_base=os.getenv("OPENAI_API_BASE"),
        model="text-embedding-3-small",
    )
    Settings.embed_model = embed_model

    schema_sc = StorageContext.from_defaults(persist_dir=SCHEMA_INDEX_PATH)
    schema_index = load_index_from_storage(schema_sc)

    example_sc = StorageContext.from_defaults(persist_dir=EXAMPLE_INDEX_PATH)
    example_index = load_index_from_storage(example_sc)

    return schema_index, example_index


def _retrieve_schema(
    schema_index, question: str, k: int
) -> list[dict]:
    """Retrieve top-k schema documents.

    Returns list of dicts with 'text' and 'metadata' keys.
    """
    retriever = schema_index.as_retriever(similarity_top_k=k)
    nodes = retriever.retrieve(question)
    return [
        {"text": node.text, "metadata": node.metadata}
        for node in nodes
    ]


def _retrieve_examples(
    example_index, question: str, k: int
) -> list[dict]:
    """Retrieve top-k example documents.

    Returns list of dicts with 'text' and 'metadata' keys.
    """
    retriever = example_index.as_retriever(similarity_top_k=k)
    nodes = retriever.retrieve(question)
    return [
        {"text": node.text, "metadata": node.metadata}
        for node in nodes
    ]


def _format_schema_text(schema_docs: list[dict]) -> str:
    """Convert schema docs into a readable prompt section."""
    parts = []
    for doc in schema_docs:
        parts.append(doc["text"])
    return "\n\n---\n\n".join(parts)


def _format_example_text(example_docs: list[dict]) -> str:
    """Convert example docs into a readable prompt section."""
    if not example_docs:
        return ""
    parts = []
    for doc in example_docs:
        parts.append(doc["text"])
    return "\n\n---\n\n".join(parts)


def _filter_matching_examples(
    example_docs: list[dict], needed_patterns: list[str]
) -> list[dict]:
    """Keep only examples whose pattern matches an inferred question pattern."""
    accepted_patterns = set(needed_patterns)
    return [
        doc
        for doc in example_docs
        if doc.get("metadata", {}).get("pattern") in accepted_patterns
    ]


def retrieve_context(question: str) -> dict:
    """Main entry point for context retrieval.

    Uses bounded adaptive expansion:
    - Schema k starts at 2, increments by 1 up to max 5.
    - Once schema coverage is sufficient, examples are retrieved separately.
    - Example misses never block overall sufficiency.

    Args:
        question: Natural language question.

    Returns:
        Dict with keys:
          - question_needs
          - schema_docs
          - schema_coverage
          - example_docs
          - prompt_context (schema_text, example_text)
    """
    question_needs = extract_question_needs(question)
    schema_index, example_index = _load_indices()

    # Adaptive schema retrieval
    schema_docs = []
    schema_coverage = {}
    for k in range(SCHEMA_K_START, SCHEMA_K_MAX + 1):
        schema_docs = _retrieve_schema(schema_index, question, k)
        schema_coverage = assess_coverage(
            question_needs, schema_docs, example_docs=None
        )
        if schema_coverage["is_sufficient"]:
            break

    # Example retrieval is optional and begins only after schema coverage succeeds.
    example_docs = []
    if (
        schema_coverage.get("is_sufficient")
        and question_needs.get("needs_example_query")
    ):
        needed_patterns = question_needs.get("example_patterns", [])
        for k in range(EXAMPLE_K_START, EXAMPLE_K_MAX + 1):
            candidates = _retrieve_examples(example_index, question, k)
            example_docs = _filter_matching_examples(
                candidates, needed_patterns
            )
            if example_docs:
                break

    # Return one final assessment that includes optional-example status.
    schema_coverage = assess_coverage(
        question_needs, schema_docs, example_docs
    )

    return {
        "question_needs": question_needs,
        "schema_docs": schema_docs,
        "schema_coverage": schema_coverage,
        "example_docs": example_docs,
        "prompt_context": {
            "schema_text": _format_schema_text(schema_docs),
            "example_text": _format_example_text(example_docs),
        },
    }
