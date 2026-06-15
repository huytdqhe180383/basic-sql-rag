"""Structured NL-to-SQL pipeline with multi-intent orchestration.

This module keeps the public entry points small:

- ``answer_question(question)`` returns a typed ``ExecutionReport``.
- ``ask_database(question)`` stays as a compatibility wrapper for the UI/CLI.

The implementation favors simple, explicit steps over clever abstraction so the
planning, grounding, SQL generation, and execution flow is easy to trace.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from textwrap import dedent

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI

from database_executor import DatabaseExecutor, SqlValidationError
from db_config import get_postgres_connection_kwargs
from question_engine import (
    ExecutionReport,
    GroundedGroup,
    PlannedGroup,
    QuestionPlan,
    ResultSection,
    SemanticGrounder,
    format_report_for_legacy_callers,
)
from retriever import retrieve_context


SEMANTIC_REGISTRY_PATH = "data/semantic_registry.json"
MAX_GROUPS = 4
ROW_LIMIT = 200
REQUEST_TIMEOUT = 30  # seconds
SECTION_REPAIR_ATTEMPTS = 1

PLANNER_SYSTEM_PROMPT = dedent(
    """\
    You plan analytics questions for a PostgreSQL NL-to-SQL agent.

    Return structured JSON that matches the provided schema exactly.

    Planning rules:
    - Split independent user requests into separate groups.
    - Keep dependent reasoning in the same group when one result needs the
      other, for example ranking then subtracting second place from first.
    - Never create more than 4 groups.
    - Preserve uncertain business terms literally instead of guessing a metric.
    - Use depends_on only when a later group truly depends on a previous group's
      output. Cross-group data handoff is usually unsupported.
    """
).strip()

SQL_SYSTEM_PROMPT = dedent(
    """\
    You are a PostgreSQL expert. Your task is to convert one grounded question
    section into a SINGLE valid SQL query.

    CRITICAL RULES:
    - Return ONLY the SQL query. No markdown fences. No explanations.
    - The query must be syntactically correct PostgreSQL.
    - Use only the tables described in the provided schema context.
    - Use exactly one statement. CTEs and window functions are allowed.
    - Only SELECT statements. Never write to the database.
    - If you cannot generate a query, return: CANNOT_GENERATE
    """
).strip()

RETRY_PROMPT = dedent(
    """\
    Your previous SQL query failed validation or execution.

    Error message: {error}

    The query you wrote:
    {failed_sql}

    Please fix the query. Return ONLY the corrected SQL, no markdown fences.
    """
).strip()


@dataclass
class RuntimeSettings:
    """Runtime dependencies loaded from environment variables."""

    client: OpenAI
    model: str
    connection_kwargs: dict[str, str]


def clean_sql(raw: str) -> str:
    """Strip markdown fences and whitespace from model output."""
    sql = raw.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1] if "\n" in sql else ""
    if sql.endswith("```"):
        sql = sql.rsplit("```", 1)[0]
    return sql.strip()


def format_results(
    columns: list[str],
    rows: list[list] | list[tuple],
    total_rows_found: int | None = None,
) -> str:
    """Pretty-print query results as a simple text table.

    ``total_rows_found`` lets the caller distinguish between the number of rows
    shown and the total matching rows when the executor applies a hard limit.
    """
    if not columns:
        return "Query executed successfully (no rows returned)."

    if not rows:
        return "No results found."

    col_widths = [len(column) for column in columns]
    for row in rows:
        for index, value in enumerate(row):
            col_widths[index] = max(col_widths[index], len(str(value)))

    def format_row(values) -> str:
        return " | ".join(
            str(value).ljust(col_widths[index]) for index, value in enumerate(values)
        )

    separator = "-+-".join("-" * width for width in col_widths)
    lines = [format_row(columns), separator]
    for row in rows:
        lines.append(format_row(row))

    shown_rows = len(rows)
    total_rows = total_rows_found if total_rows_found is not None else shown_rows
    if total_rows > shown_rows:
        lines.append(f"\n({shown_rows} of {total_rows} rows shown)")
    else:
        lines.append(f"\n({total_rows} row{'s' if total_rows != 1 else ''})")
    return "\n".join(lines)


def _build_prompt(question: str) -> str:
    """Build the legacy single-question SQL prompt from retrieved context."""
    context = retrieve_context(question)
    schema_text = context["prompt_context"]["schema_text"]
    example_text = context["prompt_context"].get("example_text", "")

    sections = ["RELEVANT SCHEMA:", schema_text]
    if example_text:
        sections.append("EXAMPLE QUERIES:")
        sections.append(example_text)
    sections.append(f"QUESTION: {question}")
    sections.append("SQL:")
    return "\n\n".join(sections)


def _build_group_prompt(group: GroundedGroup) -> str:
    """Build a SQL-generation prompt for one grounded execution group."""
    context = retrieve_context(group.question)
    schema_text = context["prompt_context"]["schema_text"]
    example_text = context["prompt_context"].get("example_text", "")

    grounded_lines = [
        f"SECTION TITLE: {group.title}",
        f"SECTION QUESTION: {group.question}",
        f"MEASURES: {_format_list(group.measures)}",
        f"DIMENSIONS: {_format_list(group.dimensions)}",
        f"FILTERS: {_format_list(group.filters)}",
        f"OPERATIONS: {_format_list(group.operations)}",
        f"ALLOWED TABLES: {_format_list(group.required_tables)}",
        f"REQUIRED COLUMNS: {_format_list(group.required_columns)}",
        f"REQUIRED RELATIONS: {_format_list(group.required_relations)}",
        "Use one PostgreSQL SELECT statement. Use CTEs/window functions when "
        "the section needs multiple reasoning steps.",
    ]

    sections = ["RELEVANT SCHEMA:", schema_text]
    if example_text:
        sections.append("EXAMPLE QUERIES:")
        sections.append(example_text)
    sections.append("GROUNDED SEMANTICS:")
    sections.append("\n".join(grounded_lines))
    sections.append("SQL:")
    return "\n\n".join(sections)


def _build_retry_prompt(base_prompt: str, error: str, failed_sql: str) -> str:
    """Build a correction prompt while retaining the retrieved context."""
    correction = RETRY_PROMPT.format(error=error, failed_sql=failed_sql)
    return f"{base_prompt}\n\n{correction}\n\nSQL:"


def _load_runtime_settings() -> tuple[RuntimeSettings | None, str | None]:
    """Load OpenAI and PostgreSQL settings from ``.env`` / process env."""
    load_dotenv(override=True)

    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    model = os.getenv("SQL_AGENT_LLM_STRONG_MODEL")

    missing = [
        name
        for name, value in (
            ("OPENAI_API_KEY", api_key),
            ("OPENAI_API_BASE", api_base),
            ("SQL_AGENT_LLM_STRONG_MODEL", model),
        )
        if not value
    ]
    if missing:
        return None, (
            "Missing OpenAI config in .env "
            f"({', '.join(missing)})."
        )

    settings = RuntimeSettings(
        client=OpenAI(api_key=api_key, base_url=api_base),
        model=model,
        connection_kwargs=get_postgres_connection_kwargs(os.environ),
    )
    return settings, None


def _build_planner_prompt(question: str, registry: dict) -> str:
    """Provide the planner with supported vocabulary and grouping rules."""
    return "\n\n".join(
        [
            "SUPPORTED SEMANTICS:",
            _build_registry_summary(registry),
            f"USER QUESTION: {question}",
            "Return a QuestionPlan.",
        ]
    )


def _build_registry_summary(registry: dict) -> str:
    """Render the semantic registry into a compact planner hint."""
    parts: list[str] = []
    for section_name in ("measures", "dimensions", "operations"):
        parts.append(f"{section_name.upper()}:")
        entries = registry.get(section_name, {})
        for canonical_name, entry in entries.items():
            aliases = ", ".join(entry.get("aliases", [])) or "none"
            parts.append(f"- {canonical_name} (aliases: {aliases})")
    return "\n".join(parts)


def _plan_question(
    question: str,
    client: OpenAI,
    model: str,
    grounder: SemanticGrounder,
) -> QuestionPlan:
    """Ask the LLM for a structured execution plan.

    A deterministic fallback planner keeps the system moving when structured
    output parsing fails or the planning request is unavailable.
    """
    prompt = _build_planner_prompt(question, grounder.registry)
    try:
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format=QuestionPlan,
            temperature=0,
            timeout=REQUEST_TIMEOUT,
        )
        message = completion.choices[0].message
        if getattr(message, "parsed", None):
            return message.parsed
        if getattr(message, "refusal", None):
            raise RuntimeError(message.refusal)
        raise RuntimeError("Planner returned no structured plan.")
    except Exception:
        return _fallback_plan(question)


def _fallback_plan(question: str) -> QuestionPlan:
    """Small deterministic fallback when structured planning is unavailable."""
    normalized_question = " ".join(question.split())
    if not normalized_question:
        return QuestionPlan(question=question, groups=[])

    group_questions = _split_independent_questions(normalized_question)
    groups = [
        PlannedGroup(
            id=f"g{index}",
            title=_make_group_title(group_question, index),
            question=group_question,
            measures=_infer_measure_terms(group_question),
            dimensions=_infer_dimension_terms(group_question),
            filters=[],
            operations=_infer_operation_terms(group_question),
            depends_on=[],
        )
        for index, group_question in enumerate(group_questions, start=1)
    ]
    return QuestionPlan(question=question, groups=groups)


def _split_independent_questions(question: str) -> list[str]:
    """Split likely independent intents while keeping linked reasoning together."""
    lowered = question.lower()
    if any(
        signal in lowered
        for signal in (
            " subtract ",
            " difference ",
            " compare ",
            " versus ",
            " vs ",
            " second ",
            " 2nd ",
            " its ",
            " their ",
            " those ",
            " that ",
        )
    ):
        return [question]

    candidates = re.split(r"\s*(?:,?\s+and\s+|\?\s+|;\s+)\s*", question)
    cleaned = [candidate.strip(" ,.") for candidate in candidates if candidate.strip(" ,.")]
    return cleaned[:MAX_GROUPS] if cleaned else [question]


def _make_group_title(question: str, index: int) -> str:
    """Create a stable, human-readable section title for fallback planning."""
    trimmed = question.strip()
    if not trimmed:
        return f"Group {index}"
    if len(trimmed) <= 60:
        return trimmed
    return trimmed[:57].rstrip() + "..."


def _infer_measure_terms(question: str) -> list[str]:
    """Infer canonical or literal metric terms for fallback planning."""
    lowered = " ".join(question.lower().split())
    measures: list[str] = []

    if any(signal in lowered for signal in ("revenue", "sales amount", "total sales")):
        measures.append("revenue")
    if "cogs" in lowered or "cost of goods sold" in lowered:
        measures.append("cogs")
    if "fill rate" in lowered or "fillrate" in lowered:
        measures.append("fill_rate")
    if "days of supply" in lowered:
        measures.append("days_of_supply")
    if re.search(r"\b(how many orders|number of orders|order count|count of orders)\b", lowered):
        measures.append("order_count")

    for candidate in _extract_unknown_metric_candidates(lowered):
        if candidate not in measures:
            measures.append(candidate)
    return measures


def _extract_unknown_metric_candidates(lowered_question: str) -> list[str]:
    """Extract user-supplied metric phrases we should clarify instead of guess."""
    candidates: list[str] = []
    patterns = (
        r"\b([a-z][a-z\s]{1,40}? rate)\b",
        r"\b([a-z][a-z\s]{1,40}? margin)\b",
        r"\b([a-z][a-z\s]{1,40}? growth)\b",
    )
    known_literals = {
        "fill rate",
    }

    for pattern in patterns:
        for match in re.finditer(pattern, lowered_question):
            candidate = " ".join(match.group(1).split())
            if candidate not in known_literals and candidate not in candidates:
                candidates.append(candidate)
    return candidates


def _infer_dimension_terms(question: str) -> list[str]:
    """Infer dimension vocabulary for fallback planning."""
    lowered = " ".join(question.lower().split())
    dimensions: list[str] = []

    if "city" in lowered or "cities" in lowered:
        dimensions.append("city")
    if "region" in lowered or "regions" in lowered:
        dimensions.append("region")
    if "district" in lowered or "districts" in lowered:
        dimensions.append("district")
    if "category" in lowered or "product category" in lowered:
        dimensions.append("category")
    return dimensions


def _infer_operation_terms(question: str) -> list[str]:
    """Infer operation hints for fallback planning."""
    lowered = " ".join(question.lower().split())
    operations: list[str] = []

    if any(signal in lowered for signal in ("highest", "top ", "largest", "most ")):
        operations.append("rank_desc")
    if any(signal in lowered for signal in ("subtract", "difference", "second", "2nd")):
        operations.append("difference_top_two")
    if any(signal in lowered for signal in (" rate", " ratio", " percentage")):
        operations.append("ratio")
    return operations


def _apply_group_limit(
    groups: list[PlannedGroup],
    max_groups: int = MAX_GROUPS,
) -> tuple[list[PlannedGroup], list[ResultSection]]:
    """Keep only the first ``max_groups`` groups and block the rest."""
    kept_groups = groups[:max_groups]
    blocked_sections: list[ResultSection] = []

    for group in groups[max_groups:]:
        blocked_sections.append(
            ResultSection(
                id=group.id,
                title=group.title,
                status="blocked",
                error=(
                    f"Only the first {max_groups} groups can be handled in one request. "
                    "Please ask the remaining sections separately."
                ),
            )
        )
    return kept_groups, blocked_sections


def _ground_groups(
    groups: list[PlannedGroup],
    grounder: SemanticGrounder,
) -> tuple[list[GroundedGroup], dict[str, ResultSection], list[GroundedGroup]]:
    """Ground each planned group and pre-build non-executable result sections."""
    grounded_groups: list[GroundedGroup] = []
    section_map: dict[str, ResultSection] = {}
    ready_groups: list[GroundedGroup] = []

    for group in groups:
        grounded = grounder.ground_group(group)
        grounded_groups.append(grounded)

        if grounded.depends_on:
            section_map[grounded.id] = ResultSection(
                id=grounded.id,
                title=grounded.title,
                status="blocked",
                error=(
                    "This section depends on another group's result. Cross-group "
                    "handoff is not supported yet, so the logic must be merged "
                    "into one SQL statement."
                ),
            )
            continue

        if grounded.status == "ready":
            ready_groups.append(grounded)
            continue

        if grounded.status == "clarification_required":
            section_map[grounded.id] = ResultSection(
                id=grounded.id,
                title=grounded.title,
                status="clarification_required",
                clarification=grounded.clarification,
                clarification_options=grounded.clarification_options,
            )
            continue

        section_map[grounded.id] = ResultSection(
            id=grounded.id,
            title=grounded.title,
            status="unsupported",
            error=grounded.clarification
            or "This section is outside the supported analytics domain.",
        )

    return grounded_groups, section_map, ready_groups


def _generate_sql_for_group(
    client: OpenAI,
    model: str,
    group: GroundedGroup,
    prompt: str | None = None,
) -> str:
    """Generate SQL for one grounded group."""
    sql_prompt = prompt or _build_group_prompt(group)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SQL_SYSTEM_PROMPT},
            {"role": "user", "content": sql_prompt},
        ],
        temperature=0,
        timeout=REQUEST_TIMEOUT,
    )
    return clean_sql(response.choices[0].message.content or "")


def _prepare_sql_for_group(
    group: GroundedGroup,
    settings: RuntimeSettings,
    executor: DatabaseExecutor,
) -> tuple[str | None, ResultSection | None]:
    """Generate and validate SQL for a ready group before opening the DB."""
    base_prompt: str | None = None
    sql = _generate_sql_for_group(settings.client, settings.model, group)
    if sql.upper() == "CANNOT_GENERATE":
        return None, ResultSection(
            id=group.id,
            title=group.title,
            status="failed",
            error="The model could not generate SQL for this section.",
        )

    for attempt in range(SECTION_REPAIR_ATTEMPTS + 1):
        try:
            validated = executor.validate_sql(sql, allowed_tables=set(group.required_tables))
            return validated.normalized_sql, None
        except SqlValidationError as exc:
            if attempt >= SECTION_REPAIR_ATTEMPTS:
                return None, ResultSection(
                    id=group.id,
                    title=group.title,
                    status="failed",
                    error=str(exc),
                    sql=sql,
                )
            if base_prompt is None:
                base_prompt = _build_group_prompt(group)
            retry_prompt = _build_retry_prompt(base_prompt, str(exc), sql)
            sql = _generate_sql_for_group(
                settings.client,
                settings.model,
                group,
                retry_prompt,
            )
            if sql.upper() == "CANNOT_GENERATE":
                break

    return None, ResultSection(
        id=group.id,
        title=group.title,
        status="failed",
        error="The model could not repair the SQL for this section.",
        sql=sql if sql else None,
    )


def _execute_ready_group(
    conn,
    executor: DatabaseExecutor,
    settings: RuntimeSettings,
    group: GroundedGroup,
    sql: str,
) -> ResultSection:
    """Execute one validated group query with a savepoint and one repair attempt."""
    savepoint_name = _savepoint_name(group.id)
    _create_savepoint(conn, savepoint_name)

    try:
        result = executor.execute_statement(
            conn,
            sql,
            allowed_tables=set(group.required_tables),
        )
        return ResultSection(
            id=group.id,
            title=group.title,
            status="completed",
            columns=result.columns,
            rows=result.rows,
            total_rows_found=result.total_rows_found,
            rows_returned=result.rows_returned,
            formatted_answer=format_results(
                result.columns,
                result.rows,
                total_rows_found=result.total_rows_found,
            ),
            sql=sql,
        )
    except Exception as exc:
        _rollback_to_savepoint(conn, savepoint_name)

        base_prompt = _build_group_prompt(group)
        retry_prompt = _build_retry_prompt(base_prompt, str(exc), sql)
        repaired_sql = _generate_sql_for_group(
            settings.client,
            settings.model,
            group,
            retry_prompt,
        )
        if repaired_sql.upper() == "CANNOT_GENERATE":
            return ResultSection(
                id=group.id,
                title=group.title,
                status="failed",
                error=str(exc),
                sql=sql,
            )

        try:
            repaired_sql = executor.validate_sql(
                repaired_sql,
                allowed_tables=set(group.required_tables),
            ).normalized_sql
            _create_savepoint(conn, savepoint_name)
            result = executor.execute_statement(
                conn,
                repaired_sql,
                allowed_tables=set(group.required_tables),
            )
            return ResultSection(
                id=group.id,
                title=group.title,
                status="completed",
                columns=result.columns,
                rows=result.rows,
                total_rows_found=result.total_rows_found,
                rows_returned=result.rows_returned,
                formatted_answer=format_results(
                    result.columns,
                    result.rows,
                    total_rows_found=result.total_rows_found,
                ),
                sql=repaired_sql,
            )
        except Exception as retry_exc:
            _rollback_to_savepoint(conn, savepoint_name)
            return ResultSection(
                id=group.id,
                title=group.title,
                status="failed",
                error=str(retry_exc),
                sql=repaired_sql,
            )


def _savepoint_name(group_id: str) -> str:
    """Create a simple SQL-safe savepoint name from a group id."""
    safe_group_id = re.sub(r"[^a-zA-Z0-9_]", "_", group_id)
    return f"beacon_{safe_group_id}"


def _create_savepoint(conn, savepoint_name: str) -> None:
    """Create a savepoint so one section failure does not kill siblings."""
    with conn.cursor() as cur:
        cur.execute(f"SAVEPOINT {savepoint_name}")


def _rollback_to_savepoint(conn, savepoint_name: str) -> None:
    """Rollback only the current section work."""
    with conn.cursor() as cur:
        cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")


def _build_execution_report(
    question: str,
    grounded_groups: list[GroundedGroup],
    section_map: dict[str, ResultSection],
    blocked_sections: list[ResultSection],
    message: str | None = None,
) -> ExecutionReport:
    """Assemble the final report in planned order."""
    ordered_sections = [section_map[group.id] for group in grounded_groups if group.id in section_map]
    ordered_sections.extend(blocked_sections)

    return ExecutionReport(
        status=_derive_report_status(ordered_sections),
        question=question,
        message=message or _default_report_message(ordered_sections),
        sections=ordered_sections,
    )


def _derive_report_status(sections: list[ResultSection]) -> str:
    """Map section-level outcomes to the top-level report status."""
    if not sections:
        return "failed"

    statuses = {section.status for section in sections}
    if statuses == {"completed"}:
        return "completed"
    if "completed" in statuses:
        return "partial"
    if statuses <= {"clarification_required"}:
        return "clarification_required"
    if statuses <= {"unsupported", "blocked"}:
        return "unsupported"
    if "clarification_required" in statuses:
        return "clarification_required"
    return "failed"


def _default_report_message(sections: list[ResultSection]) -> str | None:
    """Provide a short user-facing summary when one helps."""
    if not sections:
        return None

    completed = sum(section.status == "completed" for section in sections)
    clarification = sum(
        section.status == "clarification_required" for section in sections
    )
    unsupported = sum(section.status == "unsupported" for section in sections)
    blocked = sum(section.status == "blocked" for section in sections)
    failed = sum(section.status == "failed" for section in sections)

    if completed and (clarification or unsupported or blocked or failed):
        return "Some sections completed, while others need clarification or follow-up."
    if clarification and not completed:
        return "Some requested metrics are not defined yet. Please clarify one of the suggested options."
    if unsupported and not completed and not clarification:
        return "This request is outside the supported analytics domain."
    if blocked and not completed:
        return "Some sections could not be executed in the current multi-step flow."
    if failed and not completed:
        return "The request was understood, but SQL generation or execution failed."
    return None


def answer_question(question: str) -> ExecutionReport:
    """Plan, ground, execute, and format a natural-language analytics request."""
    normalized_question = question.strip()
    if not normalized_question:
        return ExecutionReport(
            status="clarification_required",
            question=question,
            message="Please enter a question.",
            sections=[],
        )

    grounder = SemanticGrounder(SEMANTIC_REGISTRY_PATH)
    settings, settings_error = _load_runtime_settings()

    if settings is None:
        plan = _fallback_plan(normalized_question)
    else:
        plan = _plan_question(normalized_question, settings.client, settings.model, grounder)

    limited_groups, blocked_sections = _apply_group_limit(plan.groups, MAX_GROUPS)
    grounded_groups, section_map, ready_groups = _ground_groups(limited_groups, grounder)

    if not ready_groups:
        return _build_execution_report(
            normalized_question,
            grounded_groups,
            section_map,
            blocked_sections,
            message=_default_report_message(
                [section_map[group.id] for group in grounded_groups if group.id in section_map]
                + blocked_sections
            ),
        )

    if settings is None:
        for group in ready_groups:
            section_map[group.id] = ResultSection(
                id=group.id,
                title=group.title,
                status="failed",
                error=settings_error or "Missing runtime configuration.",
            )
        return _build_execution_report(
            normalized_question,
            grounded_groups,
            section_map,
            blocked_sections,
            message=settings_error,
        )

    allowed_tables = {
        table_name
        for group in ready_groups
        for table_name in group.required_tables
    }
    executor = DatabaseExecutor(
        connection_kwargs=settings.connection_kwargs,
        allowed_tables=allowed_tables,
        row_limit=ROW_LIMIT,
    )

    prepared_queries: list[tuple[GroundedGroup, str]] = []
    for group in ready_groups:
        sql, failed_section = _prepare_sql_for_group(group, settings, executor)
        if failed_section is not None:
            section_map[group.id] = failed_section
            continue
        prepared_queries.append((group, sql))

    if not prepared_queries:
        return _build_execution_report(
            normalized_question,
            grounded_groups,
            section_map,
            blocked_sections,
        )

    conn = None
    try:
        conn = executor.open_connection()
        executor.begin_readonly_transaction(conn)

        for group, sql in prepared_queries:
            section_map[group.id] = _execute_ready_group(
                conn,
                executor,
                settings,
                group,
                sql,
            )
    except Exception as exc:
        for group, _ in prepared_queries:
            if group.id not in section_map:
                section_map[group.id] = ResultSection(
                    id=group.id,
                    title=group.title,
                    status="failed",
                    error=str(exc),
                )
    finally:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    return _build_execution_report(
        normalized_question,
        grounded_groups,
        section_map,
        blocked_sections,
    )


def ask_database(question: str) -> tuple[str, str | None]:
    """Compatibility wrapper used by the current UI and CLI."""
    report = answer_question(question)
    return format_report_for_legacy_callers(report)


def main():
    """CLI entry point."""
    user_query = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""
    if not user_query:
        user_query = input("Enter your question: ").strip()
    if not user_query:
        print("No question provided. Exiting.")
        sys.exit(0)

    answer, _sql = ask_database(user_query)
    print(answer)


def _format_list(values: list[str]) -> str:
    """Render a list for prompts without adding extra syntax noise."""
    return ", ".join(values) if values else "none"


if __name__ == "__main__":
    main()
