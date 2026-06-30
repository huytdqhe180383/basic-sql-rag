"""Schema relation graph helpers."""

from __future__ import annotations

from collections import deque


def build_schema_graph(semantic_model: list[dict]) -> dict:
    """Build an undirected table graph from semantic model relations."""
    tables = {table["source_table"]: table for table in semantic_model}
    edges: dict[str, list[dict]] = {name: [] for name in tables}
    for table in semantic_model:
        for relation in table.get("relations", []):
            left = relation["from"]
            right = relation["to"]
            left_table = left.split(".", 1)[0]
            right_table = right.split(".", 1)[0]
            text = f"{left} -> {right}"
            edges.setdefault(left_table, []).append({"to": right_table, "relation": text})
            edges.setdefault(right_table, []).append({"to": left_table, "relation": text})
    return {"tables": tables, "edges": edges}


def relation_paths(graph: dict, selected_tables: set[str], max_hops: int = 2) -> list[str]:
    """Return a deterministic set of relations connecting selected tables."""
    relations: list[str] = []
    seen: set[str] = set()
    ordered = sorted(selected_tables)
    for index, start in enumerate(ordered):
        for end in ordered[index + 1 :]:
            for relation in shortest_relation_path(graph, start, end, max_hops):
                if relation not in seen:
                    seen.add(relation)
                    relations.append(relation)
    return relations


def shortest_relation_path(graph: dict, start: str, end: str, max_hops: int) -> list[str]:
    """Return the shortest relation path between two tables, if one is bounded."""
    if start == end:
        return []
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        table, path = queue.popleft()
        if len(path) >= max_hops:
            continue
        for edge in graph.get("edges", {}).get(table, []):
            next_table = edge["to"]
            next_path = path + [edge["relation"]]
            if next_table == end:
                return next_path
            if next_table not in visited:
                visited.add(next_table)
                queue.append((next_table, next_path))
    return []


def tables_in_relations(relations: list[str]) -> set[str]:
    """Return table names mentioned by relation strings."""
    tables: set[str] = set()
    for relation in relations:
        for side in relation.split(" -> "):
            if "." in side:
                tables.add(side.split(".", 1)[0])
    return tables
