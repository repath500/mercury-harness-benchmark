#!/usr/bin/env python3
"""Create a secret-free index of omitted raw Harbor trial directories."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "results" / "mercury-v2"
TRIALS = ROOT / "trials"
OUTPUT = ROOT / "raw-trials-manifest.json"


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def main() -> None:
    rows: list[dict] = []
    raw_bytes = 0
    for directory in sorted(TRIALS.iterdir() if TRIALS.exists() else []):
        if not directory.is_dir():
            continue
        size = sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())
        raw_bytes += size
        config = read_json(directory / "config.json")
        result = read_json(directory / "result.json")
        task_config = config.get("task") if isinstance(config.get("task"), dict) else {}
        agent_config = config.get("agent") if isinstance(config.get("agent"), dict) else {}
        task_path = str(task_config.get("path") or "")
        task = Path(task_path).name if task_path else directory.name.split("__")[0]
        agent = str(agent_config.get("name") or "unknown")
        verifier = result.get("verifier_result") if isinstance(result.get("verifier_result"), dict) else {}
        rewards = verifier.get("rewards") if isinstance(verifier.get("rewards"), dict) else {}
        rows.append(
            {
                "directory": str(directory.relative_to(ROOT)),
                "bytes": size,
                "task": task,
                "agent": agent,
                "reward": rewards.get("reward"),
                "has_verifier_result": (directory / "verifier" / "result.json").exists()
                or (directory / "verifier" / "reward.txt").exists(),
                "has_trajectory": (directory / "agent" / "trajectory.json").exists(),
                "has_patch": (directory / "agent" / "patch.diff").exists(),
            }
        )
    payload = {
        "public_bundle_policy": "Raw Harbor directories are indexed here but omitted because they contain duplicated package/container caches, setup retries, and provider-specific runtime noise. Canonical bundles retain the audit evidence.",
        "raw_bytes": raw_bytes,
        "raw_trial_directories": len(rows),
        "rows": rows,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"output": str(OUTPUT), "raw_trial_directories": len(rows), "raw_bytes": raw_bytes}))


if __name__ == "__main__":
    main()
