import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from question_engine import (
    ExecutionReport,
    PlannedGroup,
    ResultSection,
    SemanticGrounder,
    format_report_for_legacy_callers,
)


def test_grounder_marks_supported_multi_step_group_ready():
    grounder = SemanticGrounder("data/semantic_registry.json")
    group = PlannedGroup(
        id="g1",
        title="Revenue gap",
        question="What is the highest revenue city, and subtract it with the 2nd highest?",
        measures=["revenue"],
        dimensions=["city"],
        operations=["rank_desc", "difference_top_two"],
    )

    grounded = grounder.ground_group(group)

    assert grounded.status == "ready"
    assert grounded.required_tables == ["geography", "order_items", "orders"]
    assert "city" in grounded.required_columns
    assert "quantity" in grounded.required_columns
    assert "unit_price" in grounded.required_columns
    assert "discount_amount" in grounded.required_columns


def test_grounder_requests_clarification_for_undefined_metric():
    grounder = SemanticGrounder("data/semantic_registry.json")
    group = PlannedGroup(
        id="g1",
        title="Repeat purchase rate",
        question="What is the repeat purchase rate?",
        measures=["repeat purchase rate"],
        dimensions=[],
        operations=["ratio"],
    )

    grounded = grounder.ground_group(group)

    assert grounded.status == "clarification_required"
    assert grounded.clarification
    assert grounded.clarification_options


def test_grounder_marks_off_domain_requests():
    grounder = SemanticGrounder("data/semantic_registry.json")
    group = PlannedGroup(
        id="g1",
        title="Weather",
        question="What is the weather today?",
        measures=["weather"],
        dimensions=[],
        operations=[],
    )

    grounded = grounder.ground_group(group)

    assert grounded.status == "off_domain"
    assert grounded.required_tables == []


def test_legacy_formatter_handles_multiple_sections():
    report = ExecutionReport(
        status="partial",
        question="Revenue by city and reorder list",
        message="One request completed and one needs clarification.",
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
                columns=[],
                rows=[],
                total_rows_found=0,
                rows_returned=0,
                formatted_answer="",
                clarification="Repeat purchase rate is not defined in the semantic registry.",
                clarification_options=[
                    "Average orders per customer",
                    "Share of customers with more than one order",
                ],
            ),
        ],
    )

    answer, sql = format_report_for_legacy_callers(report)

    assert "Revenue by city" in answer
    assert "Repeat purchase rate" in answer
    assert "Average orders per customer" in answer
    assert "SELECT city, 123.0 AS revenue" in sql
