# Master Plan: Multi-Intent and Unknown-Question Handling

## 1. Summary
Replace the flat question-family validity check with a robust, structured planner and deterministic semantic grounder.

Beacon will support up to four independent result sections per request. Dependent reasoning (such as ranking cities and subtracting second place from first) must compile into **one PostgreSQL statement** using CTEs/window functions. Independent intents will execute as separate read-only statements.

To keep codebase complexity low, the pipeline will heavily leverage **Structured LLM Outputs (e.g., Pydantic/Instructor)**, a **Linear Functional Pipeline**, and a tightly encapsulated **Database Executor**.

## 2. Key Changes & Architecture
- **LLM Planning Stage:** An initial LLM stage that returns validated JSON (enforced via Pydantic/Structured Outputs to avoid repair loops) containing execution groups, measures, dimensions, filters, operations, and requested output shape.
- **Extended Semantic Model:** A YAML/JSON configuration containing canonical measures, dimensions, aliases, formulas, required columns, joins, and source preferences. Keep `question_families` only as retrieval tags.
- **Fuzzy Grounding Fallback:** Before marking an intent as `clarification_required`, the grounder will attempt lightweight fuzzy/vector matching against the semantic model aliases to gracefully handle minor terminology deviations.
- **Classification:** Each group is classified as `ready`, `clarification_required`, or `off_domain`.
- **Partial Understanding:** Treat unresolved metrics (e.g., an undefined "margin" or "repeat purchase rate") as partial understanding rather than silently guessing.
- **Off-Domain Rejection:** Reject off-domain requests. Execute valid independent sibling groups and report unsupported siblings separately.
- **Max 4 Groups (Partial Execution):** If planning produces over four independent groups, execute the first 4 valid groups. Any groups beyond 4 will be returned as a separate section with `status: blocked` asking the user to submit them separately, rather than rejecting the entire prompt.

## 3. Interfaces and Flow

### API Definitions
Introduce a structured API leveraging Pydantic models for type safety and LLM output extraction:

```python
def answer_question(question: str) -> ExecutionReport:
```

```python
class ExecutionReport(BaseModel):
    status: Literal['completed', 'partial', 'clarification_required', 'unsupported', 'failed']
    question: str
    message: Optional[str]
    sections: list[ResultSection]

class ResultSection(BaseModel):
    id: str
    title: str
    status: Literal['completed', 'clarification_required', 'unsupported', 'failed', 'blocked']
    columns: list[str]
    rows: list[list]
    total_rows_found: int         # Replaces `truncated: bool`
    rows_returned: int
    formatted_answer: str
    sql: Optional[str]
    error: Optional[str]
    clarification: Optional[str]
    clarification_options: Optional[list[str]]  # Provided for UI button rendering
```

### Pipeline Flow (Linear & Functional)
1. **Plan:** LLM planner creates the execution groups.
2. **Ground:** Map planned metrics to the Semantic Model.
3. **Generate:** Generate exactly one SQL statement per `ready` group.
4. **Execute:** Execute via the isolated `DatabaseExecutor` (no database logic leaks into the LLM pipeline).
5. **Format:** Retain `ask_database()` as a compatibility wrapper that formats sections and SQL into the existing response format for backward compatibility.

## 4. Execution Safety & Database Isolation
To ensure the LLM cannot harm the database and errors are handled gracefully, all database operations will be encapsulated inside a `DatabaseExecutor` class.

- **AST Validation:** Parse generated SQL with a PostgreSQL-aware AST parser (e.g., `pglast` or `sqlglot`). Strictly reject multiple statements, writes, unknown tables, `SELECT INTO`, transaction commands, and unsafe functions.
- **Read-Only Transactions:** Generate and validate all SQL before opening a read-only `REPEATABLE READ` transaction.
- **Database-Level Timeouts:** Explicitly run `SET LOCAL statement_timeout = '...'` at the beginning of the transaction to catch rogue LLM queries (like infinite cross-joins) at the database engine level.
- **Savepoints:** Execute groups with savepoints so one failure does not discard valid sibling results.
- **Row Limits:** Enforce configurable result-row limits at the database cursor level. Provide `total_rows_found` vs `rows_returned` back to the UI.

## 5. Clarifications & Error Handling
- **Stateless Clarifications:** Clarifications remain entirely stateless on the backend. However, the API provides `clarification_options` so the frontend UI can provide one-click buttons to the user instead of making them retype their prompt.
- **SQL Execution Retries:** If the AST-validated SQL fails at runtime (e.g., a `psycopg2` syntax or join error), the pipeline catches the error, feeds the specific error message back to the SQL Generator for that specific group, and attempts **one repair attempt**.
- **Result Pattern:** Functions will return `Result` objects or handle failures internally per group, avoiding nested `try/except` blocks crashing the entire request.

## 6. Edge Cases
- **â€œHighest revenue city, subtract the second highestâ€:** One group, one SQL, ranking plus difference.
- **â€œHighest revenue city and its top productâ€:** One linked group and one SQL.
- **â€œRevenue by city and products needing reorderâ€:** Two independent groups and two sections.
- **Valid intent plus weather request:** Execute the valid section and mark weather off-domain.
- **Recognized dimension plus undefined measure:** Return a targeted clarification for that specific section.
- **Unsupported Hand-offs:** A requested comparison requiring unsupported cross-query handoff must be merged into one SQL group or rejected as unsupported; intermediate query results are never passed into later SQL.

## 7. Test Plan
- **Request Types:** Recognized, partial, off-domain, ambiguous, and empty questions.
- **Grouping:** Multi-intent decomposition, linked-intent grouping, pronoun-linked requests, and the >4 group limit boundary.
- **SQL Logic:** Top-two ranking difference and other multi-operation single-SQL scenarios.
- **Partial Success:** Partial sibling success, blocked dependent operations, and stateless clarification output (including `clarification_options`).
- **Resilience:** SQL AST rejection for writes, multiple statements, ungrounded tables, unsafe functions, and `SELECT INTO`.
- **Database Safety:** Read-only transaction, savepoint isolation, DB-level timeout, truncation/row-counts, and per-section LLM retries on DB errors.
- **Compatibility:** Structured API plus compatibility-wrapper behavior for single and multiple sections. Preserve existing retrieval, coverage, prompt, artifact, and acceptance tests.

## 8. Assumptions
- LLM reasoning is allowed for intent planning, but coverage, semantic grounding, and SQL safety remain deterministic (with a slight fuzzy fallback before failing).
- No application-level scalar or tabular handoff between SQL executions.
- The semantic model is the authoritative definition of supported metrics; unsupported formulas are never invented.
- Generated schema indices must be rebuilt after semantic metadata changes.
