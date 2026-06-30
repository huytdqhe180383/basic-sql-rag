"""Build vector-searchable schema records from semantic metadata."""

from __future__ import annotations


def build_schema_records(semantic_model: list[dict]) -> list[dict]:
    """Return table and column records suitable for local vector indexing."""
    records: list[dict] = []
    for table in semantic_model:
        table_name = table["source_table"]
        records.append(
            {
                "id": table_name,
                "kind": "table",
                "text": " ".join(
                    str(part)
                    for part in [
                        table_name,
                        table.get("semantic_name", ""),
                        table.get("grain", ""),
                        table.get("description", ""),
                        " ".join(table.get("question_families", [])),
                    ]
                    if part
                ),
                "metadata": {"table": table_name, "column": None},
            }
        )
        for column in table.get("columns", []):
            records.append(column_record(table_name, column))
    return records


def column_record(table_name: str, column: dict) -> dict:
    """Return one vector record for a semantic column."""
    profile = column.get("profile", {})
    profile_values: list[str] = []
    profile_values.extend(map(str, profile.get("sample_values", [])))
    profile_values.extend(str(item.get("value")) for item in profile.get("top_values", []))
    profile_values.extend(map(str, profile.get("value_counts", {}).keys()))
    text = " ".join(
        str(part)
        for part in [
            table_name,
            column.get("name", ""),
            column.get("type", ""),
            column.get("description", ""),
            " ".join(profile_values),
        ]
        if part
    )
    return {
        "id": f"{table_name}.{column['name']}",
        "kind": "column",
        "text": text,
        "metadata": {"table": table_name, "column": column["name"]},
    }
