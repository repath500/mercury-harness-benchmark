#!/usr/bin/env python3
"""Build compact, secret-free chart data from the canonical V2 report."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports" / "mercury-v2" / "mercury-v2.json"
OUT = ROOT / "benchmarks" / "mercury_v2" / "charts" / "data"
TASK_LIST = ROOT / "benchmarks" / "mercury_v2" / "tasks" / "mercury-v2.txt"
HARNESS_ORDER = (
    "pi", "oh-my-pi", "claude-code", "codex", "deepseek-harness", "critique-code", "opencode"
)
HARNESS_LABELS = {
    "pi": "Pi (vanilla)", "oh-my-pi": "Oh My Pi", "claude-code": "Claude Code",
    "codex": "Codex", "deepseek-harness": "DeepSeek Harness", "critique-code": "CritiqueCode",
    "opencode": "OpenCode",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def complete(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("status") == "complete"]


def aggregate_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = []
    for harness in HARNESS_ORDER:
        rows = complete([r for r in records if r["harness"] == harness])
        solved = sum(bool(r["result"]["resolved"]) for r in rows)
        costs = [r["cost_usd"] for r in rows if isinstance(r.get("cost_usd"), (int, float))]
        times = [r["timing"].get("agent_ms") for r in rows if isinstance(r["timing"].get("agent_ms"), (int, float))]
        first_requests = [r["timing"].get("first_model_request_ms") for r in rows if isinstance(r["timing"].get("first_model_request_ms"), (int, float))]
        first_tools = [r["timing"].get("first_tool_call_ms") for r in rows if isinstance(r["timing"].get("first_tool_call_ms"), (int, float))]
        active_shares = [r["timing"].get("active_time_share") for r in rows if isinstance(r["timing"].get("active_time_share"), (int, float))]
        contexts = [r["timing"].get("context_growth", {}).get("ratio") for r in rows if isinstance(r["timing"].get("context_growth", {}).get("ratio"), (int, float))]
        model_calls = sum(r.get("model_requests") or 0 for r in rows)
        tools = sum(r["tools"].get("total") or 0 for r in rows)
        summary.append({
            "id": harness,
            "label": HARNESS_LABELS[harness],
            "runs": len(rows),
            "solved": solved,
            "resolved_rate": solved / len(rows) if rows else None,
            "total_cost_usd": round(sum(costs), 8),
            "cost_per_resolved_usd": round(sum(costs) / solved, 8) if solved else None,
            "total_tokens": sum(r["tokens"].get("total") or 0 for r in rows),
            "median_agent_ms": int(median(times)) if times else None,
            "median_first_model_request_ms": int(median(first_requests)) if first_requests else None,
            "median_first_tool_call_ms": int(median(first_tools)) if first_tools else None,
            "median_active_time_share": median(active_shares) if active_shares else None,
            "median_context_growth_ratio": median(contexts) if contexts else None,
            "regressions": sum(r["result"].get("verifier_suite_gap") == "regression_p2p_failure" for r in rows),
            "false_completions": sum(bool(r["termination"].get("claimed_success") and not r["result"]["resolved"]) for r in rows),
            "timeouts": sum(bool(r["termination"].get("timeout")) for r in rows),
            "crashes": sum(bool(r["termination"].get("crash")) for r in rows),
            "compatibility_errors": sum(bool(r["termination"].get("compatibility_error")) for r in rows),
            "model_requests": model_calls,
            "tool_calls": tools,
            "failed_tool_calls": sum(r["tools"].get("failed") or 0 for r in rows),
            "tool_calls_per_model_request": tools / model_calls if model_calls else None,
            "test_runs": sum(r["observations"].get("test_runs") or 0 for r in rows),
            "files_changed": sum(r["patch"].get("files_changed") or 0 for r in rows),
            "lines_added": sum(r["patch"].get("lines_added") or 0 for r in rows),
            "lines_deleted": sum(r["patch"].get("lines_deleted") or 0 for r in rows),
            "provider_reconciled_trials": sum(bool(r.get("provider_accounting", {}).get("complete")) for r in rows),
        })
    return summary


def task_matrix(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = [line.strip() for line in TASK_LIST.read_text().splitlines() if line.strip() and not line.startswith("#")]
    matrix = []
    for task in order:
        rows = {r["harness"]: r for r in complete([x for x in records if x["task"] == task])}
        first = next(iter(rows.values()), None)
        if not first:
            matrix.append({"task": task, "difficulty": None, "results": {}})
            continue
        result = {}
        for harness in HARNESS_ORDER:
            row = rows.get(harness)
            if not row:
                continue
            result[harness] = {
                "resolved": bool(row["result"]["resolved"]),
                "f2p_passed": row["result"].get("f2p_passed"), "f2p_total": row["result"].get("f2p_total"),
                "p2p_passed": row["result"].get("p2p_passed"), "p2p_total": row["result"].get("p2p_total"),
                "cost_usd": row.get("cost_usd"), "agent_ms": row["timing"].get("agent_ms"),
                "claimed_success": bool(row["termination"].get("claimed_success")),
                "tool_calls": row["tools"].get("total"),
            }
        matrix.append({
            "task": task, "difficulty": first.get("difficulty"),
            "tests": {"f2p_total": first["result"].get("f2p_total"), "p2p_total": first["result"].get("p2p_total")},
            "results": result,
        })
    return matrix


def difficulty_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for harness in HARNESS_ORDER:
        for difficulty in ("easy", "hard", "very-hard"):
            rows = complete([r for r in records if r["harness"] == harness and r.get("difficulty") == difficulty])
            solved = sum(bool(r["result"]["resolved"]) for r in rows)
            out.append({"harness": harness, "label": HARNESS_LABELS[harness], "difficulty": difficulty, "runs": len(rows), "solved": solved, "resolved_rate": solved / len(rows) if rows else None})
    return out


def main() -> None:
    report = load(REPORT)
    records = report["records"]
    summary = aggregate_rows(records)
    write(OUT / "summary.json", {"benchmark": report["benchmark"], "model": report["model"], "environment": report["environment"], "harnesses": summary})
    write(OUT / "task-matrix.json", {"tasks": task_matrix(records), "harness_order": list(HARNESS_ORDER), "harness_labels": HARNESS_LABELS})
    write(OUT / "difficulty.json", {"rows": difficulty_summary(records), "difficulty_order": ["easy", "hard", "very-hard"]})
    write(OUT / "efficiency.json", {"harnesses": summary, "note": "Aggregates use completed canonical trials only."})
    print(json.dumps({"completed": sum(row.get("status") == "complete" for row in records), "out": str(OUT)}))


if __name__ == "__main__":
    main()
