# Relevant Text-to-SQL Papers for Beacon

This folder contains a small, categorized reference set for Beacon's current pipeline:

`question -> retrieve schema/examples -> coverage check -> prompt -> SQL -> validate -> execute -> answer`

Start with [paper_categories.md](paper_categories.md), then open the `summary.md` inside each category folder.

## Categories

- [Semantic Metadata and Value Grounding](1_semantic_metadata_value_grounding/summary.md)
- [Schema Linking and Retrieval](2_schema_linking_retrieval/summary.md)
- [Prompting, Examples, and Candidate Generation](3_prompting_examples_candidates/summary.md)
- [SQL Validation, Result Review, and Retry](4_validation_review_retry/summary.md)
- [Abstention, Ambiguity, and Clarification](5_abstention_ambiguity_clarification/summary.md)

## Manual download needed

These papers looked relevant, but the crawler could not access a real PDF directly.

### SNAILS: Schema Naming Assessments for Improved LLM-Based SQL Inference
- Source: https://dl.acm.org/doi/10.1145/3709727
- Access issue: ACM direct PDF returned `403 Forbidden`.
- Why it matters: schema naming, synonyms, and how schema labels affect LLM SQL inference.

### Generating Succinct Descriptions of Database Schemata for Cost-Efficient Prompting of Large Language Models
- Source: https://dl.acm.org/doi/abs/10.14778/3681954.3682017
- Access issue: ACM direct PDF returned `403 Forbidden`.
- Why it matters: compact schema descriptions and keeping Beacon prompt context small.

### Few-shot Text-to-SQL Translation using Structure and Content Prompt Learning
- Source: https://dl.acm.org/doi/abs/10.1145/3589292
- Access issue: ACM direct PDF returned `403 Forbidden`.
- Why it matters: example selection and prompt demonstration structure.

### AID-SQL: Adaptive In-Context Learning of Text-to-SQL with Difficulty-Aware Instruction and Retrieval-Augmented Generation
- Source: https://www.computer.org/csdl/proceedings-article/icde/2025/360300d945/26FZCc99mg0
- Access issue: the IEEE/Computer Society page did not expose a direct PDF through the crawler.
- Why it matters: adaptive retrieval and difficulty-aware prompting.

## Notes

- `references.md` is kept untouched as the broad source bibliography.
- `references.md` appears to have the RSL-SQL and TrustSQL links swapped. The local summaries use the actual downloaded paper contents and corrected source links.
- The summaries are short by design. They are meant to guide implementation decisions, not replace the papers.
