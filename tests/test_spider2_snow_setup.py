import importlib.util
import json
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "benchmarks" / "spider2_snow" / "prepare_subsets.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_subsets", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_balanced_subset_spreads_across_databases():
    module = load_module()
    tasks = [
        {"instance_id": "a1", "db_id": "alpha"},
        {"instance_id": "a2", "db_id": "alpha"},
        {"instance_id": "b1", "db_id": "beta"},
        {"instance_id": "c1", "db_id": "gamma"},
    ]

    subset = module.choose_balanced_subset(tasks, 3)

    assert [task["instance_id"] for task in subset] == ["a1", "b1", "c1"]


def test_write_jsonl_round_trips_utf8():
    module = load_module()
    temp_dir = PROJECT_ROOT / "benchmarks" / "spider2_snow" / ".test_tmp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    path = temp_dir / "tasks.jsonl"
    rows = [{"instance_id": "sf_test", "instruction": "Return café revenue"}]

    try:
        module.write_jsonl(path, rows)
        assert module.load_jsonl(path) == rows
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_prepare_subset_writes_manifest_and_resources():
    module = load_module()
    temp_dir = PROJECT_ROOT / "benchmarks" / "spider2_snow" / ".test_tmp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()

    try:
        (temp_dir / "databases" / "demo_db").mkdir(parents=True)
        (temp_dir / "databases" / "demo_db" / "DDL.csv").write_text(
            "table,column\norders,order_id\n",
            encoding="utf-8",
        )
        credential = temp_dir / "snowflake_credential.json"
        credential.write_text('{"user":"your_username"}\n', encoding="utf-8")

        module.SUBSET_DIR = temp_dir / "subsets"
        module.SOURCE_JSONL = temp_dir / "source.jsonl"
        module.DATABASE_DIR = temp_dir / "databases"
        module.DOCUMENT_DIR = temp_dir / "documents"

        tasks = [{"instance_id": "sf_demo", "db_id": "demo_db", "instruction": "List orders"}]
        subset_jsonl = module.prepare_subset("demo", tasks, 1, credential)
        subset_dir = subset_jsonl.parent
        manifest_path = subset_dir / "manifest.json"

        assert manifest_path.exists()
        assert (subset_dir / "sf_demo" / "snowflake_credential.json").exists()
        assert (subset_dir / "sf_demo" / "demo_db" / "DDL.csv").exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = module.load_jsonl(subset_jsonl)

        assert manifest["task_count"] == len(rows)
        assert manifest["instance_ids"] == [row["instance_id"] for row in rows]
        assert manifest["db_ids"] == ["demo_db"]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_direct_runner_builds_prompt_from_subset_resources():
    runner_path = PROJECT_ROOT / "benchmarks" / "spider2_snow" / "run_direct_sql.py"
    spec = importlib.util.spec_from_file_location("run_direct_sql", runner_path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    temp_dir = PROJECT_ROOT / "benchmarks" / "spider2_snow" / ".test_tmp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    instance_dir = temp_dir / "sf_demo" / "demo_db"
    instance_dir.mkdir(parents=True)
    (instance_dir / "DDL.csv").write_text("table,column\norders,order_id\n", encoding="utf-8")
    task = {"instance_id": "sf_demo", "db_id": "demo_db", "instruction": "List orders"}

    try:
        prompt = runner.build_prompt(task, temp_dir, max_context_chars=4000)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    assert task["instruction"] in prompt
    assert task["db_id"] in prompt
    assert "Schema and documentation" in prompt
    assert "orders,order_id" in prompt
