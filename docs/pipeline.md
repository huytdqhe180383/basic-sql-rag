# Beacon Pipeline

Beacon is a retrieval-augmented Text-to-SQL pipeline. The runtime path keeps the original user question intact, builds grounded schema context, asks for one read-only PostgreSQL query, validates and executes it, then reviews the result before answering.

## Full Pipeline

```mermaid
flowchart TD
    A["User question"] --> B["question_signals.extract_question_signals"]
    A --> C["metadata_grounding.ground_question_metadata"]
    A --> D["embeddings + vector_store.search_vector_index"]
    A --> E["retrieval_tools.extract_question_needs compatibility fallback"]
    B --> F["schema_linking.link_schema"]
    C --> F
    D --> F
    E --> F
    F --> G["schema_graph.relation_paths"]
    G --> H["example_retrieval.rank_examples"]
    H --> I["prompting.build_sql_prompt"]
    I --> J["pipeline_tools.request_sql"]
    J --> K["sql.clean_sql + sql.validate_sql"]
    K --> L["sql.run_query"]
    L --> M["pipeline_tools.review_attempt"]
    M --> N{"Accepted?"}
    N -->|Yes| O["pipeline_tools.compose_final_answer"]
    N -->|No| P["retry.classify_retry_need"]
    P -->|SQL retry| J
    P -->|Value repair| C
    P -->|Retrieval repair| F
    O --> Q["Answer + SQL"]
    O --> R["optional feedback_examples.save_candidate_example"]
```

## Retrieval Layers

```mermaid
flowchart LR
    A["Layer 1: Question signals"] --> D["Linked schema context"]
    B["Layer 2: Metadata grounding"] --> D
    C["Layer 3: Vector schema retrieval"] --> D
    E["Layer 4: Schema graph expansion"] --> D
    F["Layer 5: Structural example retrieval"] --> D
```

## Runtime Contract

SQL generation returns SQL only. Beacon does not ask the model to return visible chain-of-thought before SQL. Retry state is carried through the in-request message history using validation errors, execution errors, result summaries, reviewer JSON, and retrieval/value repair messages.

## Compatibility Note

`retrieval_tools.extract_question_needs()` remains available as a filtered fallback for the original demo schema. New Spider-Snow-specific table rules should not be added there; generalization belongs in semantic metadata, vector records, question signals, and schema graph expansion.
