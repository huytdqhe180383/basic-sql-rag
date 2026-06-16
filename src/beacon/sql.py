"""SQL cleanup, validation, execution, and result formatting."""

from __future__ import annotations

import re

import psycopg2


class SqlValidationError(ValueError):
    """Raised when generated SQL is not safe for the core read-only pipeline."""


WRITE_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "grant",
    "revoke",
    "truncate",
    "copy",
    "call",
    "merge",
    "lock",
}
UNSAFE_FUNCTIONS = {
    "pg_read_file",
    "pg_ls_dir",
    "pg_stat_file",
    "dblink",
    "lo_import",
    "lo_export",
    "pg_execute_server_program",
}


def clean_sql(raw: str) -> str:
    """Strip markdown fences and extra whitespace from model output."""
    sql = raw.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1] if "\n" in sql else ""
    if sql.endswith("```"):
        sql = sql.rsplit("```", 1)[0]
    return sql.strip().rstrip(";").strip()


def validate_sql(sql: str, allowed_tables: set[str]) -> str:
    """Validate one generated SELECT statement and return normalized SQL."""
    normalized = clean_sql(sql)
    lowered = normalized.lower()

    if not normalized:
        raise SqlValidationError("The model did not return SQL.")
    if ";" in normalized:
        raise SqlValidationError("Only one SQL statement is allowed.")
    if not re.match(r"^(select|with)\b", lowered):
        raise SqlValidationError("Only SELECT or WITH queries are allowed.")
    if re.search(r"\bselect\b.*\binto\b", lowered, re.DOTALL):
        raise SqlValidationError("SELECT INTO is not allowed.")

    for keyword in WRITE_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise SqlValidationError(f"The keyword `{keyword}` is not allowed.")
    for function_name in UNSAFE_FUNCTIONS:
        if re.search(rf"\b{function_name}\s*\(", lowered):
            raise SqlValidationError(f"The function `{function_name}` is not allowed.")

    referenced_tables = extract_referenced_tables(normalized)
    outside_context = referenced_tables - allowed_tables
    if outside_context:
        tables = ", ".join(sorted(outside_context))
        raise SqlValidationError(f"SQL references tables outside context: {tables}.")
    return normalized


def extract_referenced_tables(sql: str) -> set[str]:
    """Return real table names referenced by FROM/JOIN clauses."""
    cte_names = {
        match.group(1).lower()
        for match in re.finditer(
            r"(?:with|,)\s*([a-z_][\w]*)\s+as\s*\(",
            sql,
            re.IGNORECASE,
        )
    }
    tables: set[str] = set()
    for match in re.finditer(r"\b(?:from|join)\s+([a-z_][\w\.]*)", sql, re.IGNORECASE):
        table = match.group(1).split(".")[-1].lower()
        if table not in cte_names:
            tables.add(table)
    return tables


def run_query(sql: str, settings: dict, row_limit: int = 200) -> dict:
    """Run validated SQL in a read-only transaction and return rows."""
    conn = psycopg2.connect(**settings["db"])
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("BEGIN READ ONLY ISOLATION LEVEL REPEATABLE READ")
            cur.execute("SET LOCAL statement_timeout = %s", ("30000ms",))
            cur.execute(f"SELECT COUNT(*) FROM ({sql}) AS beacon_count")
            total = cur.fetchone()[0]
            cur.execute(f"SELECT * FROM ({sql}) AS beacon_result LIMIT {row_limit}")
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = [list(row) for row in cur.fetchall()]
        conn.rollback()
        return {"columns": columns, "rows": rows, "total": total}
    finally:
        conn.close()


def format_results(columns: list[str], rows: list[list], total: int | None = None) -> str:
    """Format query rows as a compact text table."""
    if not columns:
        return "Query executed successfully."
    if not rows:
        return "No results found."

    widths = [len(column) for column in columns]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))

    def fmt(values: list) -> str:
        return " | ".join(str(value).ljust(widths[i]) for i, value in enumerate(values))

    lines = [fmt(columns), "-+-".join("-" * width for width in widths)]
    lines.extend(fmt(row) for row in rows)
    total_rows = len(rows) if total is None else total
    lines.append(f"\n({len(rows)} of {total_rows} rows shown)" if total_rows > len(rows) else f"\n({total_rows} row{'s' if total_rows != 1 else ''})")
    return "\n".join(lines)
