#!/usr/bin/env python3
"""Freeze the successful FeatBench oracle gate for Mercury V2."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
V2 = ROOT / "benchmarks" / "mercury_v2"
TASK_ROOT = V2 / "tasks" / "featbench"
TRIAL_ROOT = V2 / "results" / "mercury-v2" / "trials"


def main() -> int:
    tasks = [line.strip() for line in (V2 / "tasks" / "mercury-v2.txt").read_text().splitlines() if line.strip() and not line.startswith("#")]
    rows = []
    for task in tasks:
        path = TRIAL_ROOT / f"{task}__oracle__v2-oracle" / "result.json"
        raw = json.loads(path.read_text())
        reward = ((raw.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        if raw.get("exception_info") or reward != 1.0:
            raise SystemExit(f"oracle gate failed: {task}: reward={reward!r}")
        config = json.loads((TASK_ROOT / task / "tests" / "config.json").read_text())
        rows.append({"task": task, "reward": reward, "f2p_total": len(config.get("FAIL_TO_PASS", [])), "p2p_total": len(config.get("PASS_TO_PASS", [])), "started_at": raw.get("started_at"), "finished_at": raw.get("finished_at")})
    gate = {"schema_version": "mercury-v2-oracle-gate", "frozen_at": datetime.now(timezone.utc).isoformat(), "dataset": {"name": "PGCodeLLM/FeatBench", "revision": "v1.0"}, "oracle": {"harbor_environment": "e2b", "reward_required": 1.0, "all_tasks_passed": True}, "tasks": rows}
    (V2 / "oracle-gate.json").write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"tasks": len(rows), "all_tasks_passed": True, "output": str(V2 / "oracle-gate.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
