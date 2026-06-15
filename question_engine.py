"""Planning and grounding models for multi-intent NL-to-SQL questions.

The code in this module stays intentionally explicit. It defines the structured
objects that move through the pipeline and provides a deterministic semantic
grounder that decides whether a planned intent is ready, needs clarification,
or is off-domain.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class PlannedGroup(BaseModel):
    """A planner-produced execution group for one user intent."""

    id: str
    title: str
    question: str
    measures: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    operations: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)


class QuestionPlan(BaseModel):
    """Structured plan returned by the LLM planner."""

    question: str
    groups: list[PlannedGroup] = Field(default_factory=list)


class GroundedGroup(BaseModel):
    """A planned group after deterministic semantic grounding."""

    id: str
    title: str
    question: str
    status: Literal["ready", "clarification_required", "off_domain", "blocked"]
    measures: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    operations: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    required_tables: list[str] = Field(default_factory=list)
    required_columns: list[str] = Field(default_factory=list)
    required_relations: list[str] = Field(default_factory=list)
    question_families: list[str] = Field(default_factory=list)
    example_patterns: list[str] = Field(default_factory=list)
    clarification: str | None = None
    clarification_options: list[str] | None = None
    unsupported_terms: list[str] = Field(default_factory=list)


class ResultSection(BaseModel):
    """One rendered answer section in the public execution report."""

    id: str
    title: str
    status: Literal[
        "completed",
        "clarification_required",
        "unsupported",
        "failed",
        "blocked",
    ]
    columns: list[str] = Field(default_factory=list)
    rows: list[list] = Field(default_factory=list)
    total_rows_found: int = 0
    rows_returned: int = 0
    formatted_answer: str = ""
    sql: str | None = None
    error: str | None = None
    clarification: str | None = None
    clarification_options: list[str] | None = None


class ExecutionReport(BaseModel):
    """Structured result returned by the new question-answering API."""

    status: Literal[
        "completed",
        "partial",
        "clarification_required",
        "unsupported",
        "failed",
    ]
    question: str
    message: str | None = None
    sections: list[ResultSection] = Field(default_factory=list)


@dataclass
class RegistryMatch:
    """A resolved semantic registry entry."""

    canonical_name: str
    entry: dict


class SemanticGrounder:
    """Map planned measures, dimensions, and operations to known semantics."""

    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)
        self.registry = json.loads(self.registry_path.read_text(encoding="utf-8"))

    def _match_term(self, section_name: str, term: str) -> RegistryMatch | None:
        entries = self.registry.get(section_name, {})
        normalized_term = self._normalize_term(term)

        for canonical_name, entry in entries.items():
            aliases = [canonical_name, *entry.get("aliases", [])]
            normalized_aliases = {self._normalize_term(alias) for alias in aliases}
            if normalized_term in normalized_aliases:
                return RegistryMatch(canonical_name=canonical_name, entry=entry)

        alias_index: dict[str, str] = {}
        for canonical_name, entry in entries.items():
            for alias in [canonical_name, *entry.get("aliases", [])]:
                alias_index[self._normalize_term(alias)] = canonical_name

        closest = get_close_matches(normalized_term, alias_index.keys(), n=1, cutoff=0.88)
        if not closest:
            return None

        canonical_name = alias_index[closest[0]]
        return RegistryMatch(canonical_name=canonical_name, entry=entries[canonical_name])

    def ground_group(self, group: PlannedGroup) -> GroundedGroup:
        """Ground one planned execution group against the semantic registry."""
        unsupported_terms: list[str] = []
        required_tables: set[str] = set()
        required_columns: set[str] = set()
        required_relations: set[str] = set()
        question_families: set[str] = set()
        example_patterns: set[str] = set()
        matched_measures: list[str] = []
        matched_dimensions: list[str] = []
        matched_operations: list[str] = []

        for term in group.measures:
            match = self._match_term("measures", term)
            if match is None:
                unsupported_terms.append(term)
                continue
            matched_measures.append(match.canonical_name)
            self._collect_entry_requirements(
                match.entry,
                required_tables,
                required_columns,
                required_relations,
                question_families,
                example_patterns,
            )

        for term in group.dimensions:
            match = self._match_term("dimensions", term)
            if match is None:
                unsupported_terms.append(term)
                continue
            matched_dimensions.append(match.canonical_name)
            self._collect_entry_requirements(
                match.entry,
                required_tables,
                required_columns,
                required_relations,
                question_families,
                example_patterns,
            )

        for term in group.operations:
            match = self._match_term("operations", term)
            if match is None:
                unsupported_terms.append(term)
                continue
            matched_operations.append(match.canonical_name)

        status, clarification, clarification_options = self._classify_group(
            group,
            matched_measures,
            matched_dimensions,
            matched_operations,
            unsupported_terms,
        )

        return GroundedGroup(
            id=group.id,
            title=group.title,
            question=group.question,
            status=status,
            measures=matched_measures,
            dimensions=matched_dimensions,
            filters=group.filters,
            operations=matched_operations,
            depends_on=group.depends_on,
            required_tables=sorted(required_tables),
            required_columns=sorted(required_columns),
            required_relations=sorted(required_relations),
            question_families=sorted(question_families),
            example_patterns=sorted(example_patterns),
            clarification=clarification,
            clarification_options=clarification_options,
            unsupported_terms=unsupported_terms,
        )

    def _classify_group(
        self,
        group: PlannedGroup,
        matched_measures: list[str],
        matched_dimensions: list[str],
        matched_operations: list[str],
        unsupported_terms: list[str],
    ) -> tuple[str, str | None, list[str] | None]:
        if matched_measures or matched_dimensions or matched_operations:
            if unsupported_terms:
                clarification_options = self._clarification_options_for_terms(
                    unsupported_terms
                )
                clarification = (
                    "I could not map every requested metric or operation to a supported "
                    f"semantic definition: {', '.join(unsupported_terms)}."
                )
                return "clarification_required", clarification, clarification_options

            return "ready", None, None

        if unsupported_terms:
            clarification_options = self._clarification_options_for_terms(
                unsupported_terms
            )
            if clarification_options:
                clarification = (
                    "This request references a metric that is not defined in the "
                    "semantic registry yet."
                )
                return "clarification_required", clarification, clarification_options

        return "off_domain", "This request does not map to the supported analytics domain.", None

    def _clarification_options_for_terms(
        self, unsupported_terms: list[str]
    ) -> list[str] | None:
        normalized_terms = " ".join(self._normalize_term(term) for term in unsupported_terms)

        if "repeat purchase" in normalized_terms:
            return [
                "Average orders per customer",
                "Share of customers with more than one order",
            ]
        if "margin" in normalized_terms:
            return [
                "Revenue minus product COGS",
                "Gross margin percentage",
            ]
        if "growth" in normalized_terms:
            return [
                "Absolute change over time",
                "Percent change over time",
            ]
        return None

    @staticmethod
    def _normalize_term(term: str) -> str:
        return " ".join(term.lower().replace("_", " ").split())

    @staticmethod
    def _collect_entry_requirements(
        entry: dict,
        required_tables: set[str],
        required_columns: set[str],
        required_relations: set[str],
        question_families: set[str],
        example_patterns: set[str],
    ) -> None:
        required_tables.update(entry.get("required_tables", []))
        required_columns.update(entry.get("required_columns", []))
        required_relations.update(entry.get("required_relations", []))
        question_families.update(entry.get("question_families", []))
        example_patterns.update(entry.get("example_patterns", []))


def format_report_for_legacy_callers(
    report: ExecutionReport,
) -> tuple[str, str | None]:
    """Format a structured report into the original `(answer, sql)` shape."""
    answer_sections: list[str] = []
    sql_sections: list[str] = []

    if report.message:
        answer_sections.append(report.message)

    for section in report.sections:
        answer_sections.append(_format_answer_section(section))
        if section.sql:
            sql_sections.append(f"{section.title}\n{section.sql}")

    answer = "\n\n".join(part for part in answer_sections if part).strip()
    sql = "\n\n---\n\n".join(sql_sections).strip() or None
    return answer, sql


def _format_answer_section(section: ResultSection) -> str:
    """Render one structured section into readable plain text."""
    header = f"[{section.title}]"
    if section.status == "completed":
        return f"{header}\n{section.formatted_answer}".strip()
    if section.status == "clarification_required":
        options = ""
        if section.clarification_options:
            options = "\nOptions: " + " | ".join(section.clarification_options)
        return f"{header}\n{section.clarification or 'Clarification required.'}{options}".strip()
    if section.status == "unsupported":
        return f"{header}\n{section.error or 'Unsupported request.'}".strip()
    if section.status == "blocked":
        return f"{header}\n{section.error or 'Blocked by an earlier section.'}".strip()
    return f"{header}\n{section.error or 'Request failed.'}".strip()
