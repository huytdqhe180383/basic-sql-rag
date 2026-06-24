# Agent Preferences

## Coding Style
- Keep Beacon simple, readable, and graduate-student-level.
- Prioritize the working core pipeline before polish or broad stability work.
- Prefer plain Python dictionaries, lists, and small functions over framework-heavy abstractions.
- Do not introduce Pydantic models, compatibility layers, report objects, selectors, or large orchestration layers unless explicitly requested.
- Keep workflow files easy to read. Put helper details in focused tool modules when a file starts hiding the pipeline.
- Avoid generic `tools.py` junk drawers when two focused helper modules make the code easier to navigate.


## Testing
- Keep tests small and meaningful.
- Prefer core pipeline, retrieval, semantic profile, prompt, SQL validation, and smoke tests.
- Do not add broad corporate-style suites just to increase coverage.
- Passing focused tests matters more than hitting a coverage target.

## Documentation
- Keep documentation practical and current.
- Preserve `references.md` and reference papers.
- Document important design decisions in plain language.
- Keep `setup.md` current when dependencies, environment variables, or local startup commands change.
