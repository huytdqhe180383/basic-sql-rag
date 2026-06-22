# Semantic Metadata and Value Grounding

This category covers the metadata Beacon needs before SQL generation: table descriptions, column meanings, compact profiles, sample values, sample rows, and value evidence.

## Papers

- [Automatic Metadata Extraction for Text-to-SQL](automatic_metadata_extraction_for_text_to_sql.md)
  - Focus: automatically extracting useful metadata from profiling, query logs, and SQL-to-text generation.
  - Beacon use: supports the current semantic layer direction without building a large metadata platform.

- [SOMA-SQL: Resolving Multi-Source Ambiguity](soma_sql_ambiguity_probing.md)
  - Focus: resolving multi-source ambiguity in queries and schemas via synthetic query logs and execution probing.
  - Beacon use: provides techniques to ground schemas with synthetic historical logs and verify intent using safe database checks.

- [E-SQL: Direct Schema Linking via Question Enrichment](e_sql_question_enrichment_schema_linking.md)
  - Focus: adding linked tables, columns, values, and predicates directly into the question context.
  - Beacon use: suggests a simple `matched evidence` prompt block from retrieved metadata.

---

## Synthesis & Beacon Improvement Plan

Based on the findings from these three papers, we outline a practical, scalable plan to improve the Beacon system's accuracy and performance.

### Papers Reference Index:
1. **Paper 1:** *Automatic Metadata Extraction for Text-to-SQL*
2. **Paper 2:** *SOMA-SQL: Resolving Multi-Source Ambiguity in NL-to-SQL via Synthetic Log and Execution Probing*
3. **Paper 3:** *E-SQL: Direct Schema Linking via Question Enrichment*

---

## 1. Key Findings & Lessons Learned

### Paper 1: Automatic Metadata Extraction for Text-to-SQL
*   **Lesson:** Detailed database profiling (distinct counts, formats, null presence, sample values) is crucial for accurate SQL. Doing this offline once and caching it is highly efficient.
*   **Key Technique:** Schema linking can be done in two stages. First, generate drafts using a **Minimal Profile** (short descriptions) to avoid context bloat. Second, generate the final SQL using a **Maximal Profile** (detailed descriptions) *only* for the selected tables/columns (Focused Schema).

### Paper 2: SOMA-SQL: Resolving Multi-Source Ambiguity
*   **Lesson:** When both user queries and schemas are ambiguous, we should ground interpretations using usage patterns (logs) and database facts rather than static rules.
*   **Key Technique:**
    *   **Synthetic Query Logs:** Ground schema meanings by generating and embedding synthetic historical query logs to show how tables and columns are realistically queried.
    *   **Execution Probing:** Expose semantic disagreements by generating candidate SQLs and executing safe diagnostic checks (e.g. counting rows, checking nulls) to gather factual evidence.

### Paper 3: E-SQL: Direct Schema Linking via Question Enrichment
*   **Lesson:** For advanced LLMs, filtering or pruning the schema actually **degrades accuracy** due to information loss and cascading errors.
*   **Key Technique:**
    *   **Question Enrichment (QE):** Instead of pruning the schema, keep the full schema and enrich the natural language question with explicit database elements (tables, columns, exact values) and a natural language SQL construction plan. This guides the LLM directly to the correct tables without getting lost.
    *   **Candidate Predicate Generation (CPG):** Parse initial SQL drafts to extract filter values, run a wildcard `LIKE` search on the database to find exact database values (value grounding), and feed these correct values back to the LLM.

---

## 2. Beacon System Improvement Plan

Beacon's current schema is small (7 tables), making it the perfect target for these improvements. We will implement these changes without breaking backwards compatibility.

### Phase 1: Semantic Layer Upgrade (`data/semantic_model/*.json`)
*   **Hierarchical Columns:** Split descriptions in semantic JSON files into `description_minimal` (used for RAG indexing/retrieval) and `description_maximal` (loaded dynamically only for retrieved columns) (Paper 1).
*   **Synthetic Log Grounding:** Generate and store 2-3 sample queries/usage contexts for each table to help ground ambiguous schemas (Paper 2).
*   **Value Profiles:** Store `sample_values` and null indicators in the column profiles (Paper 1).
*   **Automated Profiler:** Write an offline script `src/beacon/profiler.py` to auto-profile databases and generate/update these JSON files automatically, ensuring scalability to large benchmarks like Spider/BIRD (Paper 1).

### Phase 2: Local Value Grounding & Verification (`src/beacon/retrieval.py`)
*   **Interactive Value Grounding:** Implement a Python helper that extracts terms from the user's question and matches them against `sample_values` in the JSON metadata or runs a fast database `LIKE` query (Paper 3).
*   **Verified Facts Promotion:** If a match is found, promote it as a "Verified Fact" and inject it as a `MATCHED EVIDENCE` block in the prompt (e.g., `User term 'organic' -> sales.source = 'organic_search'`). This maps synonyms/literals to exact database values before calling the LLM, preventing value hallucinations (Paper 3).

### Phase 3: Generation & Verification Upgrade (`src/beacon/pipeline.py`)
*   **SQL Construction Plan:** Update `SQL_SYSTEM_PROMPT` to enforce that the LLM generates a short, natural language construction plan (CoT) before outputting the SQL (Paper 3).
*   **Execution Probing & Disagreement Resolution:** Generate multiple SQL candidate drafts when ambiguity is high. Perform execution probing (checking for empty sets or column value ranges) to identify which plan is semantically valid (Paper 2).
*   **Candidate Predicate Generation (CPG) in Retry Loop:** When an SQL attempt fails or returns empty, parse the query predicates and run a database `LIKE` wildcard search to find the correct value spelling. Inject this correct spelling into the retry prompt (Paper 3).
*   **Static Semantic Checks:** Add check rules to verify nullable columns in `ORDER BY` or `MIN/MAX` statements have `IS NOT NULL` filters (Paper 1).
*   **Majority Voting:** Generate 3 candidates (shuffling schema fields / changing seed) and run majority voting on their output datasets (Paper 1).


