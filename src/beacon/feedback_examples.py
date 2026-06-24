"""Save verified SQL attempts as future example candidates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def candidate_from_attempt(
    question: str,
    attempt: dict,
    result: dict | None,
    linked_context: dict,
) -> dict:
    """Build a JSON-friendly example candidate from an accepted attempt."""
    signals = linked_context.get("signals", {})
    sql = attempt.get("sql") or ""
    fingerprint = hashlib.sha256(
        f"{normalize(question)}\n{normalize(sql)}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "fingerprint": fingerprint,
        "status": "candidate",
        "question": question,
        "sql": sql,
        "tables": sorted(linked_context.get("selected_tables", [])),
        "metrics": sorted(signals.get("metrics", set())),
        "filters": sorted(signals.get("filters", set())),
        "time_grain": signals.get("time_grain"),
        "row_count": None if result is None else result.get("total"),
        "review_reason": attempt.get("review_reason"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def save_candidate_example(path: Path, candidate: dict) -> None:
    """Append or replace one candidate by fingerprint."""
    rows = []
    if path.exists():
        rows = json.loads(path.read_text(encoding="utf-8"))
    by_fingerprint = {row["fingerprint"]: row for row in rows}
    by_fingerprint[candidate["fingerprint"]] = candidate
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(list(by_fingerprint.values()), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def normalize(value: str) -> str:
    """Normalize values for stable fingerprints."""
    return " ".join(value.lower().split())
