# Spider 2.0-Snow Benchmark

This directory keeps Spider 2.0-Snow separate from Beacon's original dataset.
The upstream benchmark is vendored at `benchmarks/vendor/Spider2`.

See `DATASET.md` for a fuller summary of the local Snow dataset snapshot,
resource layout, evaluation shape, and Beacon-specific implications.

## Subsets

- `subsets/smoke/smoke.jsonl`: 5 tasks for quick checks, about 50 model calls at 10 calls/task.
- `subsets/occasional/occasional.jsonl`: 50 tasks for regression checks, about 500 model calls at 10 calls/task.
- Full benchmark source: `benchmarks/vendor/Spider2/spider2-snow/spider2-snow.jsonl` with 547 tasks.

Regenerate subsets:

```powershell
python benchmarks\spider2_snow\prepare_subsets.py
```

## Isolated Python Environment

The local benchmark venv lives at `benchmarks\.venv_spider2_snow`.

Recreate it if needed:

```powershell
python -m venv benchmarks\.venv_spider2_snow
benchmarks\.venv_spider2_snow\Scripts\python.exe -m pip install -r benchmarks\spider2_snow\requirements-spider2-snow.txt
```

## Credentials

Spider 2.0-Snow uses the benchmark team's Snowflake-hosted databases. Follow
their current Snowflake guideline and replace the placeholder
`snowflake_credential.json` files before running agent or SQL evaluation.

Primary places that need credentials:

- `benchmarks/vendor/Spider2/methods/spider-agent-snow/snowflake_credential.json`
- `benchmarks/vendor/Spider2/spider2-snow/evaluation_suite/snowflake_credential.json`
- regenerated subset task folders under `benchmarks/spider2_snow/subsets/*/<instance_id>/`

## Run Spider-Agent on a Subset

From the vendor agent directory:

```powershell
cd benchmarks\vendor\Spider2\methods\spider-agent-snow
python run.py --model gpt-5.4-nano -s beacon-smoke --test_path ..\..\..\spider2_snow\subsets\smoke\smoke.jsonl --max_steps 10
```

For the occasional set, change the test path to:

```text
..\..\..\spider2_snow\subsets\occasional\occasional.jsonl
```

## Run the Lightweight Direct SQL Baseline

This simple runner is useful before wiring the full Beacon pipeline into
Spider2-Snow. It makes one OpenAI call per task and writes SQL files that the
official evaluator can consume.

```powershell
python benchmarks\spider2_snow\run_direct_sql.py `
  --test-path benchmarks\spider2_snow\subsets\smoke\smoke.jsonl `
  --output-dir benchmarks\spider2_snow\results\smoke_direct `
  --model gpt-5.4-nano `
  --max-calls 5
```

Dry-run without API calls:

```powershell
python benchmarks\spider2_snow\run_direct_sql.py `
  --test-path benchmarks\spider2_snow\subsets\smoke\smoke.jsonl `
  --output-dir benchmarks\spider2_snow\results\smoke_dry_run `
  --dry-run `
  --overwrite
```

## Evaluate SQL Predictions

Put one predicted SQL file per task in a result directory, named like
`sf_bq011.sql`. Then run the upstream evaluator from:

```powershell
cd benchmarks\vendor\Spider2\spider2-snow\evaluation_suite
$env:PYTHONUTF8='1'
..\..\..\..\.venv_spider2_snow\Scripts\python.exe evaluate.py --mode sql --result_dir <your_predicted_sql_folder>
```

The evaluator reports both the score over files present and the real score
against all 547 tasks. For subset runs, use the score over files present.
