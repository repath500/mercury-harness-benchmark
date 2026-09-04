#!/usr/bin/env python3
"""Merge a verifier-replay result with the original completed Pi evidence."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: merge_replayed_trial.py ORIGINAL_STALL FINAL_REPLAY")
    original = Path(sys.argv[1])
    final = Path(sys.argv[2])
    original_result = json.loads((original / "result.json").read_text())
    final_result = json.loads((final / "result.json").read_text())

    # The verifier outcome and verifier timing come from the fresh replay
    # sandbox. Agent identity, usage, execution timing, and native transcript
    # come only from the original Pi run.
    for key in (
        "task_name",
        "trial_name",
        "trial_uri",
        "task_id",
        "task_checksum",
        "config",
        "source",
        "agent_info",
        "agent_result",
        "started_at",
        "agent_execution",
    ):
        if key in original_result:
            final_result[key] = original_result[key]
    final_result["recovery"] = {
        "kind": "verifier_replay_after_harbor_collector_stall",
        "original_trial_dir": str(original),
        "agent_inference_rerun": False,
        "verifier_rerun": True,
    }

    source_agent = original / "agent"
    if source_agent.is_dir():
        shutil.copytree(source_agent, final / "agent", dirs_exist_ok=True)
    (final / "result.json").write_text(json.dumps(final_result, indent=4) + "\n")
    print(
        json.dumps(
            {
                "trial": str(final),
                "resolved": final_result.get("verifier_result", {}).get("rewards", {}).get("reward"),
                "recovery": final_result["recovery"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
