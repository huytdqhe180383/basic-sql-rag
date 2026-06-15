"""Tests for prompt assembly and pipeline orchestration."""

from types import SimpleNamespace
from unittest.mock import patch

from pipeline import _build_prompt, _build_retry_prompt, answer_question, ask_database
from question_engine import ExecutionReport, PlannedGroup, QuestionPlan, ResultSection


class _DummyCursor:
    """Tiny context-manager cursor used by fake connections in unit tests."""

    def __init__(self, commands: list[tuple[str, object]]):
        self.commands = commands

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql: str, params=None):
        self.commands.append((sql, params))


class _DummyConnection:
    """Minimal connection object that records savepoint commands."""

    def __init__(self):
        self.commands: list[tuple[str, object]] = []
        self.closed = False

    def cursor(self):
        return _DummyCursor(self.commands)

    def rollback(self):
        self.commands.append(("ROLLBACK", None))

    def close(self):
        self.closed = True


class _FakeExecutor:
    """Small stand-in for DatabaseExecutor so orchestration tests stay local."""

    def __init__(self):
        self.connection = _DummyConnection()
        self.executed_sql: list[str] = []

    def validate_sql(self, sql: str, allowed_tables=None):
        return SimpleNamespace(normalized_sql=sql, referenced_tables=set(allowed_tables or []))

    def open_connection(self):
        return self.connection

    def begin_readonly_transaction(self, conn):
        conn.commands.append(("BEGIN READ ONLY", None))

    def execute_statement(self, conn, sql: str, allowed_tables=None):
        self.executed_sql.append(sql)
        return SimpleNamespace(
            columns=["city", "revenue"],
            rows=[["Hanoi", 123.0]],
            total_rows_found=1,
            rows_returned=1,
        )


@patch("pipeline.retrieve_context")
def test_prompt_contains_only_retrieved_schema(mock_retrieve_context):
    """Prompt assembly must not reintroduce the full schema dump."""
    mock_retrieve_context.return_value = {
        "prompt_context": {
            "schema_text": "Table: customers\nColumns:\n  - customer_id",
            "example_text": "",
        }
    }

    prompt = _build_prompt("How many customers are there?")

    assert "Table: customers" in prompt
    assert "Table: inventory" not in prompt
    assert "EXAMPLE QUERIES:" not in prompt
    assert "QUESTION:" in prompt


@patch("pipeline.retrieve_context")
def test_prompt_includes_accepted_examples(mock_retrieve_context):
    """A matched example should appear in its own prompt section."""
    mock_retrieve_context.return_value = {
        "prompt_context": {
            "schema_text": "Table: sales",
            "example_text": "Question: Daily revenue?\nSQL: SELECT Date, Revenue FROM sales",
        }
    }

    prompt = _build_prompt("Show daily revenue")

    assert "EXAMPLE QUERIES:" in prompt
    assert "SELECT Date, Revenue FROM sales" in prompt


def test_retry_prompt_preserves_retrieved_context():
    """A SQL correction request should retain the covered schema and question."""
    base_prompt = (
        "RELEVANT SCHEMA:\n\nTable: customers\n\n"
        "QUESTION: How many customers?\n\nSQL:"
    )

    prompt = _build_retry_prompt(
        base_prompt,
        error="column does not exist",
        failed_sql="SELECT missing FROM customers",
    )

    assert "Table: customers" in prompt
    assert "QUESTION: How many customers?" in prompt
    assert "column does not exist" in prompt
    assert "SELECT missing FROM customers" in prompt


@patch("pipeline.DatabaseExecutor")
@patch("pipeline._generate_sql_for_group")
@patch("pipeline._plan_question")
@patch("pipeline._load_runtime_settings")
def test_answer_question_returns_partial_report_for_mixed_sections(
    mock_load_runtime_settings,
    mock_plan_question,
    mock_generate_sql_for_group,
    mock_database_executor,
):
    """A valid section should still run when a sibling needs clarification."""
    fake_executor = _FakeExecutor()
    mock_database_executor.return_value = fake_executor
    mock_load_runtime_settings.return_value = (
        SimpleNamespace(client=object(), model="test-model", connection_kwargs={}),
        None,
    )
    mock_plan_question.return_value = QuestionPlan(
        question="Revenue by city and repeat purchase rate",
        groups=[
            PlannedGroup(
                id="g1",
                title="Revenue by city",
                question="Revenue by city",
                measures=["revenue"],
                dimensions=["city"],
                operations=[],
            ),
            PlannedGroup(
                id="g2",
                title="Repeat purchase rate",
                question="Repeat purchase rate",
                measures=["repeat purchase rate"],
                dimensions=[],
                operations=["ratio"],
            ),
        ],
    )
    mock_generate_sql_for_group.return_value = "SELECT city, 123.0 AS revenue"

    report = answer_question("Revenue by city and repeat purchase rate")

    assert report.status == "partial"
    assert [section.status for section in report.sections] == [
        "completed",
        "clarification_required",
    ]
    assert fake_executor.executed_sql == ["SELECT city, 123.0 AS revenue"]
    assert report.sections[0].formatted_answer.endswith("(1 row)")
    assert "Average orders per customer" in report.sections[1].clarification_options


@patch("pipeline._plan_question")
@patch("pipeline._load_runtime_settings")
def test_answer_question_blocks_groups_beyond_limit(
    mock_load_runtime_settings,
    mock_plan_question,
):
    """Only the first four groups should be considered in one request."""
    mock_load_runtime_settings.return_value = (
        SimpleNamespace(client=object(), model="test-model", connection_kwargs={}),
        None,
    )
    mock_plan_question.return_value = QuestionPlan(
        question="many questions",
        groups=[
            PlannedGroup(
                id=f"g{i}",
                title=f"Question {i}",
                question=f"Question {i}",
                measures=["weather"],
                dimensions=[],
                operations=[],
            )
            for i in range(1, 6)
        ],
    )

    report = answer_question("many questions")

    assert len(report.sections) == 5
    assert report.sections[-1].status == "blocked"
    assert "Only the first 4 groups" in report.sections[-1].error


@patch("pipeline.answer_question")
def test_ask_database_formats_structured_reports(mock_answer_question):
    """The old wrapper should still return `(answer, sql)` for the UI and CLI."""
    mock_answer_question.return_value = ExecutionReport(
        status="partial",
        question="Revenue by city and repeat purchase rate",
        message="One section completed and one needs clarification.",
        sections=[
            ResultSection(
                id="g1",
                title="Revenue by city",
                status="completed",
                columns=["city", "revenue"],
                rows=[["Hanoi", 123.0]],
                total_rows_found=1,
                rows_returned=1,
                formatted_answer="city  | revenue\nHanoi | 123.0\n\n(1 row)",
                sql="SELECT city, 123.0 AS revenue",
            ),
            ResultSection(
                id="g2",
                title="Repeat purchase rate",
                status="clarification_required",
                clarification="Repeat purchase rate is not defined.",
                clarification_options=["Average orders per customer"],
            ),
        ],
    )

    answer, sql = ask_database("Revenue by city and repeat purchase rate")

    assert "Revenue by city" in answer
    assert "Repeat purchase rate" in answer
    assert "SELECT city, 123.0 AS revenue" in sql
