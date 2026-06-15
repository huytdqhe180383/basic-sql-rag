"""Database execution helpers for structured NL-to-SQL sections.

This module keeps SQL validation and read-only execution logic separate from
the LLM orchestration code so the data path stays easy to reason about.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import psycopg2


class SqlValidationError(ValueError):
    """Raised when generated SQL violates the read-only safety rules."""


@dataclass
class SqlValidationResult:
    """Normalized SQL plus the real tables referenced by the statement."""

    normalized_sql: str
    referenced_tables: set[str]


@dataclass
class QueryExecutionResult:
    """Result metadata returned for one executed statement."""

    columns: list[str]
    rows: list[list]
    total_rows_found: int
    rows_returned: int


class DatabaseExecutor:
    """Validate and execute read-only PostgreSQL queries."""

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
        "comment",
        "copy",
        "call",
        "vacuum",
        "analyze",
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

    def __init__(
        self,
        connection_kwargs: dict[str, str],
        allowed_tables: set[str],
        row_limit: int = 200,
        statement_timeout_ms: int = 30000,
    ):
        self.connection_kwargs = connection_kwargs
        self.allowed_tables = allowed_tables
        self.row_limit = row_limit
        self.statement_timeout_ms = statement_timeout_ms

    def validate_sql(
        self, sql: str, allowed_tables: set[str] | None = None
    ) -> SqlValidationResult:
        """Validate one generated statement against the read-only policy."""
        normalized_sql = self._normalize_sql(sql)
        lowered_sql = normalized_sql.lower()

        if self._contains_multiple_statements(normalized_sql):
            raise SqlValidationError("Only one SQL statement is allowed per section.")
        if not re.match(r"^(select|with)\b", lowered_sql):
            raise SqlValidationError("Only SELECT or WITH queries are allowed.")
        if re.search(r"\bselect\b.*\binto\b", lowered_sql, re.DOTALL):
            raise SqlValidationError("SELECT INTO is not allowed.")

        for keyword in self.WRITE_KEYWORDS:
            if re.search(rf"\b{keyword}\b", lowered_sql):
                raise SqlValidationError(f"The keyword `{keyword}` is not allowed.")

        for function_name in self.UNSAFE_FUNCTIONS:
            if re.search(rf"\b{function_name}\s*\(", lowered_sql):
                raise SqlValidationError(
                    f"The function `{function_name}` is not allowed."
                )

        referenced_tables = self._extract_referenced_tables(normalized_sql)
        allowed = allowed_tables or self.allowed_tables
        disallowed_tables = referenced_tables - allowed
        if disallowed_tables:
            tables = ", ".join(sorted(disallowed_tables))
            raise SqlValidationError(
                f"Query references tables outside the grounded allow-list: {tables}."
            )

        return SqlValidationResult(
            normalized_sql=normalized_sql,
            referenced_tables=referenced_tables,
        )

    def build_count_query(self, normalized_sql: str) -> str:
        """Wrap a validated query so PostgreSQL counts its result rows."""
        return f"SELECT COUNT(*) FROM ({normalized_sql}) AS beacon_count"

    def build_limited_query(self, normalized_sql: str) -> str:
        """Wrap a validated query and apply the configured row limit."""
        return (
            f"SELECT * FROM ({normalized_sql}) AS beacon_result "
            f"LIMIT {self.row_limit}"
        )

    def open_connection(self):
        """Create a psycopg2 connection using the configured kwargs."""
        return psycopg2.connect(**self.connection_kwargs)

    def begin_readonly_transaction(self, conn) -> None:
        """Start the shared read-only transaction used for section execution."""
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("BEGIN READ ONLY ISOLATION LEVEL REPEATABLE READ")
            cur.execute(
                "SET LOCAL statement_timeout = %s",
                (f"{self.statement_timeout_ms}ms",),
            )

    def execute_statement(
        self, conn, sql: str, allowed_tables: set[str] | None = None
    ) -> QueryExecutionResult:
        """Validate and execute one section query inside an open transaction."""
        validated = self.validate_sql(sql, allowed_tables=allowed_tables)
        count_sql = self.build_count_query(validated.normalized_sql)
        limited_sql = self.build_limited_query(validated.normalized_sql)

        with conn.cursor() as cur:
            cur.execute(count_sql)
            total_rows_found = cur.fetchone()[0]

            cur.execute(limited_sql)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = [list(row) for row in cur.fetchall()]

        return QueryExecutionResult(
            columns=columns,
            rows=rows,
            total_rows_found=total_rows_found,
            rows_returned=len(rows),
        )

    @staticmethod
    def _normalize_sql(sql: str) -> str:
        cleaned = sql.strip()
        cleaned = cleaned.rstrip(";").strip()
        return cleaned

    @staticmethod
    def _contains_multiple_statements(sql: str) -> bool:
        return ";" in sql

    @staticmethod
    def _extract_referenced_tables(sql: str) -> set[str]:
        cte_names = {
            match.group(1).lower()
            for match in re.finditer(r"(?:with|,)\s*([a-z_][\w]*)\s+as\s*\(", sql, re.IGNORECASE)
        }
        referenced_tables: set[str] = set()
        for match in re.finditer(r"\b(?:from|join)\s+([a-z_][\w\.]*)", sql, re.IGNORECASE):
            table_name = match.group(1).split(".")[-1].lower()
            if table_name not in cte_names:
                referenced_tables.add(table_name)
        return referenced_tables
