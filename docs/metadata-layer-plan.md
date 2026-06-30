# Simple Metadata Layer Improvements for Beacon

## Summary
Improve Beacon's metadata just enough to make the core question-to-SQL pipeline more reliable.

The goal is not to build a general metadata platform. The goal is to help the existing pipeline do a better job at:

`question -> retrieve schema/examples -> coverage check -> prompt -> SQL -> validate -> execute -> answer`

Keep the implementation small, readable, and easy to change. Prefer plain dictionaries, lists, and simple helper functions over framework-style abstractions.

## Key Changes

### Keep The Existing Shape
- Keep `data/semantic_model/*.json` as the main source of schema metadata.
- Keep `data/few_shot_queries.json` as the main source of example SQL.
- Keep the current root commands and package entrypoints:
  - `python -m beacon.indexing`
  - `python -m beacon.pipeline`
  - `python -m beacon.ui`
  - `python -m beacon.load_db`
- Keep implementation details inside the ordered source layers:
  - `src/beacon/indexing/` builds schema/example documents and local vectors.
  - `src/beacon/linking/` finds relevant schema, values, joins, and examples.
  - `src/beacon/runtime/` assembles prompts, validates SQL, executes SQL, and handles retry.
  - `src/beacon/app/` keeps UI and local database loading code.

### Improve Metadata Where It Helps Retrieval
- Make table and column descriptions clearer when they are vague.
- Keep compact column profiles in the semantic JSON files:
  - null counts
  - distinct counts
  - sample values
  - numeric min, max, and mean where useful
  - date min and max
  - categorical top values
- Keep three sample rows per table so prompts can show realistic values without dumping the dataset.
- Add only small example-query signals when useful:
  - tables used
  - important columns
  - metric names
  - filters
  - time grain

### Keep Retrieval Simple
- Use deterministic scoring before adding any model-based selector.
- Prefer clear keyword and metadata matching over hidden ranking logic.
- Keep retrieval output close to the current shape:
  - question needs
  - schema docs
  - example docs
  - coverage result
- Build prompt context from retrieved schema docs, column profiles, sample rows, and matching examples.
- Keep the context compact enough that it helps SQL generation instead of becoming a data dump.

### Avoid Overbuilding For Now
Do not add these in this pass:

- large `data/metadata/` artifact trees
- SQL masking pipelines
- generic AST extraction modules
- learned selector models
- fused metadata reports
- BIRD-scale caching systems
- Pydantic models for retrieval internals
- compatibility layers for old internal APIs

If the simple approach fails on concrete questions, revisit one improvement at a time.

## Interfaces
- `beacon.indexing` should continue to expose simple helpers for building local retrieval artifacts.
- `beacon.linking.retrieval` should continue to return plain dict/list data that `beacon.runtime.pipeline` can use directly.
- Root modules such as `beacon.pipeline` and `beacon.retrieval` should remain thin compatibility entrypoints.
- Any new metadata fields should be optional so older table JSON files still load cleanly.
- Keep all new structures JSON-friendly and easy to inspect by hand.

## Test Plan
Add or update only small tests that protect the core pipeline:

- Schema docs include table descriptions, column profiles, sample values, and sample rows.
- Example retrieval returns useful examples for common question types.
- Common questions retrieve the expected tables:
  - signup and customer questions
  - revenue by category
  - daily revenue
  - inventory and fill-rate questions
- Prompt context includes relevant schema metadata without becoming too large.
- Mocked pipeline smoke tests still pass for:
  - a single normal question
  - a simple multi-step question
  - an off-domain question with a readable failure

No coverage target is required for this pass. Passing the core tests matters more than broad test volume.

## Design Decisions
- Manual semantic JSON remains the source of truth because it is readable and already fits this project.
- Generated metadata should stay compact and should be checked into the same per-table files only when it clearly helps prompting.
- Retrieval should stay deterministic until there is evidence that a model-based selector is needed.
- SQLGlot, query masking, and BIRD-scale metadata extraction are future options, not current requirements.

## Assumptions
- This plan rewrites the metadata direction only; it does not implement the metadata changes yet.
- `references.md` and reference papers remain untouched.
- Current uncommitted changes in the working tree are intentional.
- The project should stay at a graduate-student level: clear, practical, and easy to debug.
