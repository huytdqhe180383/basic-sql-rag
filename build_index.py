"""
Build LlamaIndex vector indices from semantic model and few-shot queries.

Produces two indices under data/indices/:
  - schema/   (from data/semantic_model.json)
  - few_shot/ (from data/few_shot_queries.json)

Run once after updating the source JSON files:
  python build_index.py
"""

import json
import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.embeddings.openai import OpenAIEmbedding


def load_json(path: str) -> list[dict]:
    """Load and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_schema_docs(semantic_model: list[dict]) -> list[Document]:
    """Convert semantic model entries into LlamaIndex Documents.

    Each document represents one table with its columns, relations,
    question families, and description as plain text.
    """
    docs = []
    for entry in semantic_model:
        lines = [
            f"Table: {entry['source_table']}",
            f"Name: {entry['semantic_name']}",
            f"Grain: {entry['grain']}",
            f"Description: {entry['description']}",
            f"Question families: {', '.join(entry['question_families'])}",
            "",
            "Columns:",
        ]
        for col in entry["columns"]:
            expr = f" (expression: {col['expression']})" if col.get("expression") else ""
            lines.append(f"  - {col['name']} ({col['type']}){expr}: {col['description']}")

        lines.append("")
        lines.append("Relations:")
        for rel in entry["relations"]:
            lines.append(f"  - {rel['from']} -> {rel['to']} ({rel['type']})")

        text = "\n".join(lines)
        doc = Document(
            text=text,
            metadata={
                "source_table": entry["source_table"],
                "semantic_name": entry["semantic_name"],
                "question_families": entry["question_families"],
                "grain": entry["grain"],
                "columns": [c["name"] for c in entry["columns"]],
                "relations": [
                    f"{relation['from']} -> {relation['to']}"
                    for relation in entry["relations"]
                ],
            },
        )
        docs.append(doc)
    return docs


def build_example_docs(few_shot: list[dict]) -> list[Document]:
    """Convert few-shot examples into LlamaIndex Documents.

    Each document represents one question/SQL example pair with its
    pattern and question families.
    """
    docs = []
    for ex in few_shot:
        text = (
            f"Question: {ex['question']}\n"
            f"SQL: {ex['sql']}\n"
            f"Tables used: {', '.join(ex['tables'])}\n"
            f"Pattern: {ex['pattern']}\n"
            f"Question families: {', '.join(ex['question_families'])}"
        )
        doc = Document(
            text=text,
            metadata={
                "question": ex["question"],
                "pattern": ex["pattern"],
                "tables": ex["tables"],
                "question_families": ex["question_families"],
            },
        )
        docs.append(doc)
    return docs


def main():
    load_dotenv(override=True)

    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in .env")

    embed_model = OpenAIEmbedding(
        api_key=api_key,
        api_base=api_base,
        model="text-embedding-3-small",
    )
    Settings.embed_model = embed_model

    # Build schema index
    print("Building schema index...")
    semantic_model = load_json("data/semantic_model.json")
    schema_docs = build_schema_docs(semantic_model)
    schema_index = VectorStoreIndex.from_documents(schema_docs)
    schema_index.storage_context.persist("data/indices/schema")
    print(f"  Schema index built with {len(schema_docs)} documents.")

    # Build few-shot index
    print("Building few-shot index...")
    few_shot = load_json("data/few_shot_queries.json")
    example_docs = build_example_docs(few_shot)
    example_index = VectorStoreIndex.from_documents(example_docs)
    example_index.storage_context.persist("data/indices/few_shot")
    print(f"  Few-shot index built with {len(example_docs)} documents.")

    print("Done.")


if __name__ == "__main__":
    main()
