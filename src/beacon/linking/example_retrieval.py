"""Structural few-shot example retrieval."""

from __future__ import annotations


def rank_examples(
    question: str,
    examples: list[dict],
    linked_context: dict,
    limit: int = 2,
) -> list[dict]:
    """Return examples ranked by schema and query-shape overlap."""
    scored = [
        (score_example(example, linked_context), index, example)
        for index, example in enumerate(examples)
    ]
    return [
        example
        for score, _index, example in sorted(scored, key=lambda item: (-item[0], item[1]))
        if score > 0
    ][:limit]


def score_example(example: dict, linked_context: dict) -> int:
    """Score one example using selected schema and question signals."""
    signals = linked_context.get("signals", {})
    selected_tables = set(linked_context.get("selected_tables", []))
    metadata = example.get("metadata", example)
    fallback_patterns = set(
        linked_context.get("fallback_needs", {}).get("example_patterns", set())
    )
    score = 0
    score += 3 * len(selected_tables & set(metadata.get("tables", [])))
    score += 8 * len(set(signals.get("metrics", set())) & set(metadata.get("metrics", [])))
    score += 3 * len(set(signals.get("filters", set())) & set(metadata.get("filters", [])))
    if signals.get("time_grain") and signals.get("time_grain") == metadata.get("time_grain"):
        score += 3
    if metadata.get("pattern") in fallback_patterns:
        score += 10
    if metadata.get("pattern") in signals.get("intents", set()):
        score += 2
    if set(signals.get("terms", [])) & text_terms(example_text(example)):
        score += 1
    return score


def example_text(example: dict) -> str:
    """Return visible example text for weak lexical overlap."""
    return " ".join(str(part) for part in [example.get("text"), example.get("question"), example.get("sql")] if part)


def text_terms(text: str) -> set[str]:
    """Return lower lexical terms from example text."""
    import re

    return set(re.findall(r"[a-z][a-z0-9_]*", text.lower()))
