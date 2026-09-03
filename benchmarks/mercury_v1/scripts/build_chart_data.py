#!/usr/bin/env python3
"""Build small, secret-free data files for the published study charts."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports" / "mercury-v1" / "mercury-v1.json"
OUT = ROOT / "benchmarks" / "mercury_v1" / "charts" / "data"
HARNESS_ORDER = ("critique-code", "claude-code", "oh-my-pi", "opencode")
HARNESS_LABELS = {
    "critique-code": "CritiqueCode",
    "claude-code": "Claude Code",
    "oh-my-pi": "Oh My Pi",
    "opencode": "OpenCode",
}
TASK_LABELS = {
    "huggingface__smolagents-783": "Custom final_answer tool",
    "encode__starlette-2806": "Flexible UUID paths",
    "jpadilla__pyjwt-913": "Multiple JWT issuers",
    "tox-dev__tox-3288": "Parameterized config types",
    "dynaconf__dynaconf-1295": "Environment-less file load",
    "stanfordnlp__dspy-7964": "BestOfN failure tolerance",
    "projectmesa__mesa-2296": "Named cell connections",
    "openai__openai-agents-python-508": "referenceable_id → response_id",
    "aiogram__aiogram-1594": "Storage get_value API",
    "huggingface__smolagents-1442": "XML prompts and instructions",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    report = load(REPORT)
    records = report["records"]
    by_harness = {h: [r for r in records if r["harness"] == h] for h in HARNESS_ORDER}

    summary = []
    for harness in HARNESS_ORDER:
        rows = by_harness[harness]
        solved = sum(bool(r["result"]["resolved"]) for r in rows)
        costs = [float(r["cost_usd"]) for r in rows if r.get("cost_usd") is not None]
        agent_ms = [r["timing"]["agent_ms"] for r in rows if r["timing"].get("agent_ms") is not None]
        summary.append(
            {
                "id": harness,
                "label": HARNESS_LABELS[harness],
                "runs": len(rows),
                "solved": solved,
                "resolved_rate": solved / len(rows),
                "total_cost_usd": round(sum(costs), 6),
                "cost_per_resolved_usd": round(sum(costs) / solved, 6) if solved else None,
                "total_tokens": sum(r["tokens"].get("total") or 0 for r in rows),
                "median_agent_ms": int(median(agent_ms)),
                "regressions": sum(
                    bool(r["result"]["f2p_passed"] == r["result"]["f2p_total"]
                         and r["result"]["p2p_passed"] != r["result"]["p2p_total"])
                    for r in rows
                ),
                "false_completions": sum(
                    bool(r["termination"].get("claimed_success") and not r["result"]["resolved"])
                    for r in rows
                ),
                "model_requests": sum(r.get("model_requests") or 0 for r in rows),
                "tool_calls": sum(r["tools"].get("total") or 0 for r in rows),
                "failed_tool_calls": sum(r["tools"].get("failed") or 0 for r in rows),
                "provider_reconciled_trials": sum(
                    bool(r.get("provider_accounting", {}).get("complete")) for r in rows
                ),
                "estimated_trials": sum(
                    not bool(r.get("provider_accounting", {}).get("complete")) for r in rows
                ),
            }
        )

    task_order = [
        line.strip()
        for line in (ROOT / "benchmarks" / "mercury_v1" / "tasks" / "mercury-v1.txt")
        .read_text()
        .splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    matrix = []
    for task in task_order:
        task_rows = {r["harness"]: r for r in records if r["task"] == task}
        first = next(iter(task_rows.values()))
        matrix.append(
            {
                "task": task,
                "label": TASK_LABELS[task],
                "difficulty": first["difficulty"],
                "tests": {
                    "f2p_total": first["result"]["f2p_total"],
                    "p2p_total": first["result"]["p2p_total"],
                },
                "results": {
                    harness: {
                        "resolved": bool(task_rows[harness]["result"]["resolved"]),
                        "f2p_passed": task_rows[harness]["result"]["f2p_passed"],
                        "f2p_total": task_rows[harness]["result"]["f2p_total"],
                        "p2p_passed": task_rows[harness]["result"]["p2p_passed"],
                        "p2p_total": task_rows[harness]["result"]["p2p_total"],
                        "claimed_success": bool(task_rows[harness]["termination"].get("claimed_success")),
                        "compatibility_error": bool(task_rows[harness]["termination"].get("compatibility_error")),
                    }
                    for harness in HARNESS_ORDER
                },
            }
        )

    efficiency = []
    for harness in HARNESS_ORDER:
        rows = by_harness[harness]
        efficiency.append(
            {
                "id": harness,
                "label": HARNESS_LABELS[harness],
                "input_tokens": sum(r["tokens"].get("input") or 0 for r in rows),
                "output_tokens": sum(r["tokens"].get("output") or 0 for r in rows),
                "cached_tokens": sum(r["tokens"].get("cached") or 0 for r in rows),
                "reasoning_tokens": sum(r["tokens"].get("reasoning") or 0 for r in rows),
                "model_requests": sum(r.get("model_requests") or 0 for r in rows),
                "tool_calls": sum(r["tools"].get("total") or 0 for r in rows),
                "failed_tool_calls": sum(r["tools"].get("failed") or 0 for r in rows),
                "files_changed": sum(r["patch"].get("files_changed") or 0 for r in rows),
                "lines_added": sum(r["patch"].get("lines_added") or 0 for r in rows),
                "lines_deleted": sum(r["patch"].get("lines_deleted") or 0 for r in rows),
                "setup_ms": sum(r["timing"].get("sandbox_setup_ms") or 0 for r in rows),
                "agent_ms": sum(r["timing"].get("agent_ms") or 0 for r in rows),
                "verification_ms": sum(r["timing"].get("verification_ms") or 0 for r in rows),
            }
        )

    write(
        OUT / "summary.json",
        {
            "benchmark": report["benchmark"],
            "model": report["model"],
            "environment": report["environment"],
            "harnesses": summary,
        },
    )
    write(
        OUT / "task-matrix.json",
        {
            "tasks": matrix,
            "harness_order": list(HARNESS_ORDER),
            "harness_labels": HARNESS_LABELS,
        },
    )
    write(
        OUT / "efficiency.json",
        {
            "harnesses": efficiency,
            "note": "Aggregates are sums across the ten canonical trials for each harness.",
        },
    )


if __name__ == "__main__":
    main()
