# Semantic Metadata and Value Grounding

This category covers the metadata Beacon needs before SQL generation: table descriptions, column meanings, compact profiles, sample values, sample rows, and value evidence.

## Papers

- [Automatic Metadata Extraction for Text-to-SQL](automatic_metadata_extraction_for_text_to_sql.md)
  - Focus: automatically extracting useful metadata from profiling, query logs, and SQL-to-text generation.
  - Beacon use: supports the current semantic layer direction without building a large metadata platform.

- [Data Ambiguity Strikes Back](data_ambiguity_documentation_text_to_sql.md)
  - Focus: data ambiguity, including value consistency, data coverage, and data granularity.
  - Beacon use: explains why compact documentation matters for business terms and grain-sensitive questions.

- [DIVER: Dynamic Interactive Value Linking and Evidence Reasoning](diver_dynamic_value_linking_evidence_reasoning.md)
  - Focus: dynamic value linking when expert evidence is missing.
  - Beacon use: helps map question terms like "Apple Pay" or "organic search" to actual table values.

- [E-SQL: Direct Schema Linking via Question Enrichment](e_sql_question_enrichment_schema_linking.md)
  - Focus: adding linked tables, columns, values, and predicates directly into the question context.
  - Beacon use: suggests a simple `matched evidence` prompt block from retrieved metadata.

---

## Synthesis & Beacon Improvement Plan

Based on the findings from these four papers, we outline a practical, scalable plan to improve the Beacon system's accuracy and performance.

### Papers Reference Index:
1. **Paper 1:** *Automatic Metadata Extraction for Text-to-SQL*
2. **Paper 2:** *Data Ambiguity Strikes Back: How Documentation Improves GPT's Text-to-SQL*
3. **Paper 3:** *DIVER: Dynamic Interactive Value Linking and Evidence Reasoning*
4. **Paper 4:** *E-SQL: Direct Schema Linking via Question Enrichment*

---

## 1. Key Findings & Lessons Learned

### Paper 1: Automatic Metadata Extraction for Text-to-SQL
*   **Lesson:** Detailed database profiling (distinct counts, formats, null presence, sample values) is crucial for accurate SQL. Doing this offline once and caching it is highly efficient.
*   **Key Technique:** Schema linking can be done in two stages. First, generate drafts using a **Minimal Profile** (short descriptions) to avoid context bloat. Second, generate the final SQL using a **Maximal Profile** (detailed descriptions) *only* for the selected tables/columns (Focused Schema).

### Paper 2: Data Ambiguity Strikes Back
*   **Lesson:** Data ambiguity (value consistency, table coverage, row granularity) is a major source of errors in real-world databases.
*   **Key Technique:**
    *   **Data Coverage:** Clarify what timeframe or geographical subset a table covers to prevent incorrect JOINs or UNIONs.
    *   **Data Granularity:** Explicitly document what a single row represents (e.g., unique event vs. pre-aggregated summary) to guide the LLM on whether to use `COUNT(*)` or `COUNT(DISTINCT)`.
    *   **Column Selection:** Only show rich documentation (like value consistency formats) for the top 5 relevant columns to save tokens, while keeping the rest of the schema in basic form.

### Paper 3: DIVER: Dynamic Interactive Value Linking and Evidence Reasoning
*   **Lesson:** Text-to-SQL models experience a severe "performance collapse" (over 10% drop in accuracy) in real-world settings where offline expert-written evidence is unavailable.
*   **Key Technique:**
    *   **Automated Expert Exploration:** Simulate an expert exploring the database using a **Chain of Thoughts and Facts (CoTF)** workspace.
    *   **Thought-Verify-Refine Loop:** Decompose the query into sub-clauses, formulate hypotheses (Thoughts), query the database using a toolbox (Verify), and refine the hypotheses based on raw data feedback (Refine) to map complex synonyms or abbreviations (e.g. mapping "State Special School" to `"SSS"`).

### Paper 4: E-SQL: Direct Schema Linking via Question Enrichment
*   **Lesson:** For advanced LLMs, filtering or pruning the schema actually **degrades accuracy** due to information loss and cascading errors.
*   **Key Technique:**
    *   **Question Enrichment (QE):** Instead of pruning the schema, keep the full schema and enrich the natural language question with explicit database elements (tables, columns, exact values) and a natural language SQL construction plan. This guides the LLM directly to the correct tables without getting lost.
    *   **Candidate Predicate Generation (CPG):** Parse initial SQL drafts to extract filter values, run a wildcard `LIKE` search on the database to find exact database values (value grounding), and feed these correct values back to the LLM.

---

## 2. Beacon System Improvement Plan

Beacon's current schema is small (7 tables), making it the perfect target for these improvements. We will implement these changes without breaking backwards compatibility.

### Phase 1: Semantic Layer Upgrade (`data/semantic_model/*.json`)
*   **Hierarchical Columns:** Split descriptions in semantic JSON files into `description_minimal` (used for RAG indexing/retrieval) and `description_maximal` (loaded dynamically only for retrieved columns) (Paper 1 & 2).
*   **Table Properties:** Add `data_granularity` and `data_coverage` to all table JSON metadata files (Paper 2).
*   **Value Profiles:** Store `sample_values` and null indicators in the column profiles (Paper 1 & 2).
*   **Automated Profiler:** Write an offline script `src/beacon/profiler.py` to auto-profile databases and generate/update these JSON files automatically, ensuring scalability to large benchmarks like Spider/BIRD (Paper 1).

### Phase 2: Local Value Grounding & Verification (`src/beacon/retrieval.py`)
*   **Interactive Value Grounding:** Implement a Python helper that extracts terms from the user's question and matches them against `sample_values` in the JSON metadata or runs a fast database `LIKE` query (Paper 3 & 4).
*   **Verified Facts Promotion:** If a match is found, promote it as a "Verified Fact" and inject it as a `MATCHED EVIDENCE` block in the prompt (e.g., `User term 'organic' -> sales.source = 'organic_search'`). This maps synonyms/literals to exact database values before calling the LLM, preventing value hallucinations (Paper 3 & 4).

### Phase 3: Generation & Verification Upgrade (`src/beacon/pipeline.py`)
*   **SQL Construction Plan:** Update `SQL_SYSTEM_PROMPT` to enforce that the LLM generates a short, natural language construction plan (CoT) before outputting the SQL (Paper 4).
*   **Candidate Predicate Generation (CPG) in Retry Loop:** When an SQL attempt fails or returns empty, parse the query predicates and run a database `LIKE` wildcard search to find the correct value spelling. Inject this correct spelling into the retry prompt (Paper 4).
*   **Static Semantic Checks:** Add check rules to verify nullable columns in `ORDER BY` or `MIN/MAX` statements have `IS NOT NULL` filters (Paper 1).
*   **Majority Voting:** Generate 3 candidates (shuffling schema fields / changing seed) and run majority voting on their output datasets (Paper 1).
