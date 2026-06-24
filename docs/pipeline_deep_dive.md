# Beacon Pipeline Deep Dive

Project root:

`E:\AI Thuc Chien\VSF\basic-mvp`

Main package:

`E:\AI Thuc Chien\VSF\basic-mvp\src\beacon`

## Correct Commands

Run commands from the repo root and set `PYTHONPATH` for the current PowerShell session:

```powershell
Set-Location -LiteralPath 'E:\AI Thuc Chien\VSF\basic-mvp'
$env:PYTHONPATH = 'E:\AI Thuc Chien\VSF\basic-mvp\src'
```

Build indices:

```powershell
python -m beacon.indexing
```

Load local PostgreSQL data:

```powershell
python -m beacon.load_db
```

Run the UI:

```powershell
python -m beacon.ui
```

Run the CLI:

```powershell
python -m beacon.pipeline 'How much revenue did we make by category?'
```

Run tests:

```powershell
pytest tests -v
```

## High-Level Flow

```mermaid
flowchart TD
    A["UI or CLI question"] --> B["pipeline.answer_question"]
    B --> C["pipeline.split_questions"]
    C --> D["pipeline.answer_section"]
    D --> E["retrieval.retrieve_context"]
    E --> F["schema_linking.link_schema"]
    F --> G["question_signals.extract_question_signals"]
    F --> H["metadata_grounding.ground_question_metadata"]
    F --> I["vector_store schema search"]
    F --> J["schema_graph.relation_paths"]
    F --> K["example_retrieval.rank_examples"]
    K --> L["prompting.build_sql_prompt"]
    L --> M["pipeline_tools.create_section_messages"]
    M --> N["pipeline.run_sql_attempt"]
    N --> O["pipeline_tools.request_sql"]
    O --> P["sql.clean_sql and sql.validate_sql"]
    P --> Q["sql.run_query"]
    Q --> R["pipeline_tools.review_attempt"]
    R --> S{"Satisfied?"}
    S -->|No| T["retry.classify_retry_need"]
    T -->|SQL retry| N
    T -->|Value repair| N
    T -->|Retrieval repair| U["retry.repair_linked_context"]
    U --> N
    S -->|Yes| V["pipeline_tools.compose_final_answer"]
    V --> W["UI answer + SQL"]
```

## Runtime Entry Points

`src/beacon/ui.py`

- `handle_question(question)` calls `beacon.pipeline.ask_database(question)`.
- `main()` launches Gradio.

`src/beacon/pipeline.py`

- `answer_question(question)` is the main structured API.
- `ask_database(question)` returns the UI-friendly `(answer, sql)` tuple.
- `main()` reads the CLI question and prints the answer.

## Configuration

`src/beacon/config.py` owns repo paths and environment-backed settings.

Important paths:

- `data/semantic_model/`
- `data/few_shot_queries.json`
- `data/indices/schema/`
- `data/indices/few_shot/`
- `data/indices/local_vectors/`
- `data/example_candidates.json`

Important environment variables:

- `OPENAI_API_KEY`
- `OPENAI_API_BASE`
- `SQL_AGENT_LLM_STRONG_MODEL`
- `PGHOST`
- `PGPORT`
- `PGUSER`
- `PGPASSWORD`
- `PGDATABASE`
- `BEACON_SAVE_EXAMPLE_CANDIDATES`
- `BEACON_EMBEDDING_MODEL`
- `BEACON_USE_HASH_EMBEDDINGS`

## Indexing Pipeline

Entry file:

`src/beacon/indexing.py`

Indexing always builds Beacon's local schema vector artifact:

- Beacon local schema vectors under `data/indices/local_vectors/`.

Set `BEACON_BUILD_LEGACY_LLAMA_INDEX=1` to also rebuild the older LlamaIndex artifacts:

- LlamaIndex schema docs under `data/indices/schema/`.
- LlamaIndex few-shot docs under `data/indices/few_shot/`.

```mermaid
flowchart TD
    A["semantic_model JSON"] --> B["indexing_tools.enrich_semantic_model_files"]
    B --> C["build_schema_docs"]
    B --> D["build_example_docs"]
    B --> E["schema_index.build_schema_records"]
    E --> F["embeddings adapter"]
    F --> G["vector_store.save_vector_index"]
    B --> J{"BEACON_BUILD_LEGACY_LLAMA_INDEX=1?"}
    J -->|Yes| C
    J -->|Yes| D
    C --> H["schema LlamaIndex"]
    D --> I["few-shot LlamaIndex"]
```

The local vector index uses `sentence-transformers` by default. Tests and offline runs can use `BEACON_USE_HASH_EMBEDDINGS=1`.

## Retrieval Pipeline

Entry file:

`src/beacon/retrieval.py`

Primary implementation:

`src/beacon/schema_linking.py`

Call path:

1. Load semantic model.
2. Build few-shot example docs.
3. Call `schema_linking.link_schema(...)`.
4. Return compatibility fields expected by `pipeline.py`: `question_needs`, `schema_docs`, `example_docs`, `schema_coverage`, and `matched_evidence`.

```mermaid
flowchart TD
    A["Question"] --> B["question_signals"]
    A --> C["metadata_grounding"]
    A --> D["local vector retrieval"]
    A --> E["filtered extract_question_needs fallback"]
    B --> F["schema_linking"]
    C --> F
    D --> F
    E --> F
    F --> G["schema_graph join expansion"]
    G --> H["schema docs"]
    H --> I["example_retrieval"]
    I --> J["linked context"]
```

The old `retrieval_tools.extract_question_needs()` remains as a compatibility fallback while the hybrid linker is evaluated. It should not receive new database-specific Spider-Snow table rules.

## Metadata Grounding

`src/beacon/metadata_grounding.py` maps question terms to table/column/value evidence.

Evidence status:

- `pinned`: strong enough to force schema inclusion.
- `ambiguous`: shown to the LLM but not pinned.
- `candidate`: useful context, not forced.

```mermaid
flowchart TD
    A["Question text"] --> B["Normalize"]
    C["Profiles and aliases"] --> D["Candidates"]
    B --> D
    D --> E["Score confidence"]
    E --> F{"Pinned?"}
    F -->|Yes| G["Force table/column"]
    F -->|No| H["Prompt-only evidence"]
```

## SQL Attempt Loop

`pipeline.answer_section()` retrieves context once, then loops through up to `MAX_SQL_ATTEMPTS = 3`.

One attempt:

1. Request SQL only.
2. Clean SQL.
3. Validate read-only safety and table grounding.
4. Execute in PostgreSQL read-only transaction.
5. Review result or error with strict JSON.
6. Retry only if needed.

Retry repair:

- SQL retry keeps the same context.
- Value repair asks the model to reconsider exact literal spelling.
- Retrieval repair adds known missing tables and join paths to the linked context before the next SQL attempt.

## SQL Safety

`src/beacon/sql.py` still validates with readable regex-based checks:

- only `SELECT` or `WITH`
- single statement
- no write/admin keywords
- no unsafe server functions
- no referenced tables outside selected schema context

Execution uses:

- PostgreSQL read-only transaction
- repeatable read isolation
- local statement timeout
- count query plus bounded preview rows

## Feedback Examples

If `BEACON_SAVE_EXAMPLE_CANDIDATES=1`, accepted SQL attempts are written to `data/example_candidates.json`.

These are candidate examples only. They should be reviewed before promotion to `data/few_shot_queries.json`.

## Design Decisions

Beacon still uses plain dictionaries and small modules. The new retrieval stack is modular, but it deliberately avoids Pydantic, large orchestration layers, and framework-heavy abstractions.

The important architectural shift is that hardcoded keyword rules are no longer the primary retrieval layer. They are filtered fallback signals; generalization comes from semantic metadata, vector schema records, evidence confidence, and schema graph expansion.
