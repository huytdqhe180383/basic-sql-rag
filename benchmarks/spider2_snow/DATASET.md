# Spider 2.0-Snow Dataset Notes

This note summarizes the local Spider 2.0-Snow snapshot installed under
`benchmarks/vendor/Spider2/spider2-snow`. It is intended to help Beacon work
with the benchmark without mixing benchmark assets into Beacon's original
e-commerce dataset.

## What Spider 2.0-Snow Is

Spider 2.0-Snow is the Snowflake-hosted variant of Spider 2.0 for traditional
text-to-SQL evaluation. The broader Spider 2.0 benchmark includes tasks from
multiple database systems and workflow settings. The Snow variant moves the
non-DBT text-to-SQL tasks into Snowflake so systems can focus on one SQL
dialect while still facing large, realistic schemas and enterprise-style
analytics questions.

For Beacon, this matters because Spider 2.0-Snow is a much harder target than
Spider 1.0. It stresses schema discovery, context selection, external
documentation use, date/window logic, geospatial functions, aggregation, set
difference, ranking, and domain-specific calculations. It is not a simple
single-schema benchmark.

## Local Snapshot

The installed benchmark file is:

`benchmarks/vendor/Spider2/spider2-snow/spider2-snow.jsonl`

Local counts from this snapshot:

| Item | Count |
|---|---:|
| Tasks | 547 |
| Distinct database IDs | 152 |
| Tasks with external knowledge | 107 |
| Tasks without external knowledge | 440 |
| Document files in `resource/documents` | 69 |
| Distinct external-knowledge docs referenced by tasks | 63 |
| Database resource files | 8,132 |
| Gold execution-result CSV files | 1,544 |
| Gold SQL files | 120 |

Instruction lengths are non-trivial:

| Metric | Characters |
|---|---:|
| Minimum | 56 |
| Median | 304 |
| 90th percentile | 607 |
| Maximum | 1,219 |

These longer prompts often encode several constraints at once, such as a time
window, a top-k condition, a set exclusion, and a requested output format.

## Task Families

Instance IDs reveal the source family of each task:

| Family | Count | Notes |
|---|---:|---|
| `sf_bq*` | 369 | BigQuery-origin tasks ported to Snowflake |
| `sf_local*` | 135 | Local-database-origin tasks ported to Snowflake |
| `sf_ga*` | 25 | Google Analytics-style tasks |
| `sf###` | 18 | Plain Snowflake task IDs |

The benchmark is therefore mostly BigQuery-origin analytics tasks translated
into Snowflake, with a meaningful local-database slice and a smaller
Google-Analytics-specific slice.

## Database Coverage

The dataset spans 152 database IDs. The most common database IDs in the local
snapshot are:

| Database ID | Tasks |
|---|---:|
| `CRYPTO` | 20 |
| `THELOOK_ECOMMERCE` | 19 |
| `GA4` | 17 |
| `PATENTS` | 15 |
| `GITHUB_REPOS` | 15 |
| `STACKOVERFLOW` | 15 |
| `IDC` | 15 |
| `BANK_SALES_TRADING` | 15 |
| `GA360` | 12 |
| `NOAA_DATA` | 12 |
| `IPL` | 11 |
| `CITY_LEGISLATION` | 10 |
| `FIREBASE` | 9 |
| `F1` | 9 |
| `BRAZILIAN_E_COMMERCE` | 8 |
| `ORACLE_SQL` | 8 |
| `CMS_DATA` | 7 |
| `SDOH` | 7 |
| `MODERN_DATA` | 7 |
| `SQLITE_SAKILA` | 7 |

The mix is broad: e-commerce, web analytics, patents, public data, finance,
geography, sports, health, transport, and developer/platform datasets.

## Resource Layout

The main local resource folders are:

| Path | Purpose |
|---|---|
| `resource/databases` | Per-database schema and metadata resources |
| `resource/documents` | External knowledge documents referenced by some tasks |
| `evaluation_suite/gold/exec_result` | Gold result CSVs used for execution-result comparison |
| `evaluation_suite/gold/sql` | Gold SQL for a subset of tasks |
| `evaluation_suite/gold/spider2snow_eval.jsonl` | Per-task evaluation configuration |

Database resource files by suffix:

| Suffix | Count |
|---|---:|
| `.json` | 7,860 |
| `.csv` | 272 |

In practice, a task folder may contain a copied Snowflake credential template,
one database metadata folder, and optionally one external knowledge document.
The copied resources are enough for prompt construction and Spider-Agent style
runs, but real SQL execution still requires Snowflake credentials.

## External Knowledge

Only 107 of 547 tasks reference external knowledge, but those tasks are
important because they test whether the system can use non-schema definitions.
Commonly referenced docs include:

| Document | Task references |
|---|---:|
| `google_analytics_sample.ga_sessions.md` | 7 |
| `functions_st_dwithin.md` | 7 |
| `patents_info.md` | 6 |
| `functions_st_within.md` | 6 |
| `retention_rate.md` | 6 |
| `ga4_page_category.md` | 4 |
| `tokenize_func.md` | 3 |
| `sliding_windows_calculation_cpc.md` | 2 |
| `functions_st_distance.md` | 2 |
| `functions_st_contains.md` | 2 |
| `taxi_tip_rate.md` | 2 |
| `persistent_udfs_routines.md` | 2 |
| `Comprehensive_Guide_to_Copy_Number_Variations_in_Cancer_Genomics.md` | 2 |
| `ga4_dimensions_and_metrics.md` | 2 |
| `haversine_formula.md` | 2 |

These documents often define calculations or functions that are not obvious
from schema alone. Beacon should treat them as part of retrieval context rather
than as optional prose.

## Evaluation Shape

The upstream evaluator supports two modes:

| Mode | Input | Notes |
|---|---|---|
| `sql` | One `.sql` file per task | Executes predictions against Snowflake, then compares result CSVs |
| `exec_result` | One `.csv` file per task | Compares provided result CSVs directly against gold CSVs |

The evaluator reports:

- Score over the files present in the submitted result directory.
- "Real score" over all 547 tasks.

For Beacon's smoke and occasional subsets, use the score over files present.
The full 547-task score only makes sense for a complete full-benchmark run.

On Windows, set `PYTHONUTF8=1` before running the upstream evaluator. Without
that setting, Python may read `spider2-snow.jsonl` using a legacy code page and
fail on Unicode text in benchmark questions.

## Local Beacon Subsets

Beacon keeps narrower local subsets under:

`benchmarks/spider2_snow/subsets`

These subsets are generated by:

`benchmarks/spider2_snow/prepare_subsets.py`

Current subset design:

| Subset | Tasks | Intended use | Approximate call budget at 10 calls/task |
|---|---:|---|---:|
| `smoke` | 5 | Fast local sanity check after benchmark or prompt changes | 50 |
| `occasional` | 50 | Periodic regression check after schema-linking or retrieval changes | 500 |
| full source | 547 | Main Spider 2.0-Snow benchmark run | 5,470 |

The subset generator chooses tasks deterministically and spreads early picks
across database IDs. This avoids a smoke set that accidentally covers only one
domain.

## Implications For Beacon

Spider 2.0-Snow is a strong fit for evaluating Beacon's next phase, but not for
the current e-commerce-only retrieval assumptions.

Expected pressure points:

- Schema linking must handle hundreds of possible database folders instead of
  one fixed semantic model.
- Context selection must be selective; dumping full database resources into
  prompts will be expensive and noisy.
- External knowledge documents need to be retrieved alongside schema.
- SQL generation must target Snowflake syntax, not PostgreSQL.
- Validation must understand Snowflake read-only SQL and avoid rejecting valid
  Snowflake constructs.
- Evaluation requires Snowflake credentials from the benchmark maintainers.

The current lightweight direct SQL runner is only a baseline. A stronger Beacon
adapter should eventually add a Spider2-Snow retrieval layer that indexes
database metadata and external docs per task, then passes compact context into
the SQL generator.

## Useful Commands

Regenerate local subsets:

```powershell
python benchmarks\spider2_snow\prepare_subsets.py
```

Run the dry-run direct baseline without API calls:

```powershell
benchmarks\.venv_spider2_snow\Scripts\python.exe benchmarks\spider2_snow\run_direct_sql.py `
  --test-path benchmarks\spider2_snow\subsets\smoke\smoke.jsonl `
  --output-dir benchmarks\spider2_snow\results\smoke_dry_run `
  --dry-run `
  --overwrite `
  --max-calls 5
```

Run upstream evaluator from the evaluation suite:

```powershell
cd benchmarks\vendor\Spider2\spider2-snow\evaluation_suite
$env:PYTHONUTF8='1'
..\..\..\..\.venv_spider2_snow\Scripts\python.exe evaluate.py --mode sql --result_dir <your_predicted_sql_folder>
```
