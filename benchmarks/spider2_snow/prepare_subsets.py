"""Prepare isolated Spider 2.0-Snow benchmark subsets.

This keeps Spider assets under benchmarks/ and leaves Beacon's original
application data untouched.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path


BENCHMARK_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BENCHMARK_DIR.parents[1]
VENDOR_DIR = PROJECT_ROOT / "benchmarks" / "vendor" / "Spider2"
SNOW_DIR = VENDOR_DIR / "spider2-snow"
SOURCE_JSONL = SNOW_DIR / "spider2-snow.jsonl"
DATABASE_DIR = SNOW_DIR / "resource" / "databases"
DOCUMENT_DIR = SNOW_DIR / "resource" / "documents"
DEFAULT_CREDENTIAL_TEMPLATE = (
    VENDOR_DIR / "methods" / "spider-agent-snow" / "snowflake_credential.json"
)
SUBSET_DIR = BENCHMARK_DIR / "subsets"


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL records from a path."""
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """Write JSONL rows with stable UTF-8 formatting."""
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def choose_balanced_subset(tasks: list[dict], size: int) -> list[dict]:
    """Choose a deterministic subset spread across database ids."""
    if size <= 0:
        return []
    if size >= len(tasks):
        return list(tasks)

    buckets: dict[str, list[dict]] = defaultdict(list)
    for task in tasks:
        buckets[task["db_id"]].append(task)

    selected: list[dict] = []
    db_ids = sorted(buckets)
    while len(selected) < size:
        changed = False
        for db_id in db_ids:
            bucket = buckets[db_id]
            if bucket:
                selected.append(bucket.pop(0))
                changed = True
                if len(selected) == size:
                    break
        if not changed:
            break

    original_order = {task["instance_id"]: index for index, task in enumerate(tasks)}
    return sorted(selected, key=lambda task: original_order[task["instance_id"]])


def copy_task_resources(task: dict, subset_path: Path, credential_template: Path) -> None:
    """Copy the files Spider-Agent expects next to a subset JSONL."""
    instance_dir = subset_path / task["instance_id"]
    if instance_dir.exists():
        shutil.rmtree(instance_dir)
    instance_dir.mkdir(parents=True)

    credential_target = instance_dir / "snowflake_credential.json"
    shutil.copy2(credential_template, credential_target)

    knowledge = task.get("external_knowledge")
    if knowledge:
        shutil.copy2(DOCUMENT_DIR / knowledge, instance_dir / Path(knowledge).name)

    db_source = DATABASE_DIR / task["db_id"]
    db_target = instance_dir / task["db_id"]
    if db_source.exists():
        shutil.copytree(db_source, db_target)


def prepare_subset(
    name: str,
    tasks: list[dict],
    size: int,
    credential_template: Path = DEFAULT_CREDENTIAL_TEMPLATE,
) -> Path:
    """Create one subset folder and return its JSONL path."""
    subset_path = SUBSET_DIR / name
    if subset_path.exists():
        shutil.rmtree(subset_path)
    subset_path.mkdir(parents=True)

    subset_tasks = choose_balanced_subset(tasks, size)
    subset_jsonl = subset_path / f"{name}.jsonl"
    write_jsonl(subset_jsonl, subset_tasks)

    for task in subset_tasks:
        copy_task_resources(task, subset_path, credential_template)

    manifest = {
        "name": name,
        "source": str(SOURCE_JSONL.relative_to(PROJECT_ROOT)),
        "task_count": len(subset_tasks),
        "instance_ids": [task["instance_id"] for task in subset_tasks],
        "db_ids": sorted({task["db_id"] for task in subset_tasks}),
    }
    (subset_path / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return subset_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Spider 2.0-Snow subsets.")
    parser.add_argument("--smoke-size", type=int, default=5)
    parser.add_argument("--occasional-size", type=int, default=50)
    parser.add_argument("--source-jsonl", type=Path, default=SOURCE_JSONL)
    parser.add_argument("--credential-template", type=Path, default=DEFAULT_CREDENTIAL_TEMPLATE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = load_jsonl(args.source_jsonl)
    smoke_jsonl = prepare_subset("smoke", tasks, args.smoke_size, args.credential_template)
    occasional_jsonl = prepare_subset(
        "occasional",
        tasks,
        args.occasional_size,
        args.credential_template,
    )
    print(f"Prepared {smoke_jsonl.relative_to(PROJECT_ROOT)}")
    print(f"Prepared {occasional_jsonl.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
