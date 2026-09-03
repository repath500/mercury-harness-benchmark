#!/usr/bin/env python3
"""Index raw Harbor trial directories without publishing generated caches."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
RESULT_ROOT = ROOT / "benchmarks" / "mercury_v1" / "results" / "mercury-v1"
RAW_ROOT = RESULT_ROOT / "trials"
OUTPUT = RESULT_ROOT / "raw-trials-manifest.json"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def directory_size(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                pass
    return total


def main() -> None:
    rows = []
    for result_path in sorted(RAW_ROOT.glob("*/result.json")):
        raw_dir = result_path.parent
        raw = read_json(result_path)
        verifier = raw.get("verifier_result") or {}
        rewards = verifier.get("rewards") if isinstance(verifier, dict) else {}
        rows.append(
            {
                "directory": str(raw_dir.relative_to(RESULT_ROOT)),
                "bytes": directory_size(raw_dir),
                "task": raw.get("task_name"),
                "trial_name": raw.get("trial_name"),
                "agent": (raw.get("agent_info") or {}).get("name"),
                "reward": (rewards or {}).get("reward") if isinstance(rewards, dict) else None,
                "exception": bool(raw.get("exception_info")),
            }
        )

    value = {
        "schema_version": "mercury-v1-raw-manifest",
        "raw_trial_directories": len(rows),
        "raw_bytes": sum(row["bytes"] for row in rows),
        "public_bundle_policy": "The public bundle contains source, oracle evidence, canonical normalized trial artifacts, and launcher logs. Raw directories are indexed here but omitted because they contain duplicated package/container caches and setup retries.",
        "rows": rows,
    }
    OUTPUT.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
