"""Run a small direct SQL-generation baseline for Spider 2.0-Snow subsets."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


SYSTEM_PROMPT = """You are a careful Snowflake SQL expert.
Return exactly one read-only Snowflake SQL query.
Use only the schema and documentation in the prompt.
Return SQL only, with no markdown fences or explanation."""


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def clean_sql(raw: str) -> str:
    sql = raw.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1] if "\n" in sql else ""
    if sql.endswith("```"):
        sql = sql.rsplit("```", 1)[0]
    if sql.lower().startswith("sql\n"):
        sql = sql.split("\n", 1)[1]
    return sql.strip().rstrip(";").strip()


def collect_context(instance_dir: Path, db_id: str, max_chars: int) -> str:
    """Collect bounded docs/schema context for one Spider2-Snow task."""
    parts: list[str] = []

    for doc_path in sorted(instance_dir.glob("*.md")):
        parts.append(f"# Document: {doc_path.name}\n{read_limited(doc_path, max_chars)}")

    db_dir = instance_dir / db_id
    if db_dir.exists():
        for path in sorted(db_dir.rglob("*")):
            if not path.is_file() or path.name == "snowflake_credential.json":
                continue
            if path.suffix.lower() not in {".csv", ".json", ".md", ".sql", ".txt"}:
                continue
            relative = path.relative_to(instance_dir)
            parts.append(f"# Schema file: {relative}\n{read_limited(path, max_chars)}")
            if len("\n\n".join(parts)) >= max_chars:
                break

    return "\n\n".join(parts)[:max_chars]


def read_limited(path: Path, max_chars: int) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]


def build_prompt(task: dict, subset_dir: Path, max_context_chars: int) -> str:
    instance_dir = subset_dir / task["instance_id"]
    context = collect_context(instance_dir, task["db_id"], max_context_chars)
    return (
        f"Task id: {task['instance_id']}\n"
        f"Database id: {task['db_id']}\n\n"
        f"Question:\n{task['instruction']}\n\n"
        f"Schema and documentation:\n{context}\n\n"
        "SQL:"
    )


def call_openai(prompt: str, model: str, temperature: float) -> str:
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE") or None,
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        timeout=60,
    )
    return response.choices[0].message.content or ""


def run_subset(args: argparse.Namespace) -> None:
    load_dotenv(override=True)
    tasks = load_jsonl(args.test_path)
    subset_dir = args.test_path.parent
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    calls = 0
    for task in tasks:
        if calls >= args.max_calls:
            print(f"Stopping at max call budget: {args.max_calls}")
            break

        sql_path = output_dir / f"{task['instance_id']}.sql"
        if sql_path.exists() and not args.overwrite:
            print(f"Skipping existing {sql_path.name}")
            continue

        prompt = build_prompt(task, subset_dir, args.max_context_chars)
        if args.dry_run:
            sql_path.write_text(
                f"-- DRY RUN for {task['instance_id']}\n-- Prompt chars: {len(prompt)}\n",
                encoding="utf-8",
            )
            print(f"Wrote dry-run placeholder {sql_path.name}")
        else:
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY is required unless --dry-run is set.")
            raw_sql = call_openai(prompt, args.model, args.temperature)
            sql_path.write_text(clean_sql(raw_sql) + "\n", encoding="utf-8")
            print(f"Wrote {sql_path.name}")
            time.sleep(args.sleep_seconds)
        calls += 1

    manifest = {
        "test_path": str(args.test_path),
        "output_dir": str(output_dir),
        "model": args.model,
        "dry_run": args.dry_run,
        "calls_used": calls,
        "max_calls": args.max_calls,
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Spider2-Snow SQL predictions.")
    parser.add_argument("--test-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.4-nano")
    parser.add_argument("--max-calls", type=int, default=50)
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--max-context-chars", type=int, default=60000)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    run_subset(parse_args())


if __name__ == "__main__":
    main()
