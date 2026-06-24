# Prompting Module

## Purpose

`src/beacon/prompting.py` owns the SQL-generation prompt layout.

## Inputs

- Original question.
- Linked context with evidence, join paths, schema docs, and examples.

## Outputs

A plain-text prompt ending with `SQL:`.

## Important Functions

- `build_sql_prompt(question, context)`
- `format_example_doc(doc)`

## Diagram

```mermaid
flowchart TD
    A["Matched evidence"] --> E["Prompt"]
    B["Join paths"] --> E
    C["Schema docs"] --> E
    D["Ranked examples"] --> E
    F["Original question"] --> E
    E --> G["SQL-only LLM request"]
```

## Failure Behavior

Missing evidence or examples are simply omitted. The schema section is always present, even if empty, so prompt shape remains stable.

## Tests

Protected by `tests/test_prompting.py`.
