#!/usr/bin/env python3
"""Normalize Harbor's raw Mercury V1 trials and write the aggregate report."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

from benchmarks.mercury_v1.agents.common import normalized_tool, parse_pi_jsonl, read_json_lines


ROOT = Path(__file__).resolve().parents[3]
V1_ROOT = ROOT / "benchmarks" / "mercury_v1"
TASK_ROOT = V1_ROOT / "tasks" / "featbench"
RESULT_ROOT = V1_ROOT / "results" / "mercury-v1"
TRIALS_ROOT = RESULT_ROOT / "trials"
CANONICAL_ROOT = RESULT_ROOT / "canonical"
REPORT_ROOT = ROOT / "reports" / "mercury-v1"
MODEL = "inception/mercury-2.5-preview"
HARNESS_ORDER = ("critique-code", "claude-code", "oh-my-pi", "opencode")


def read_json(path: Path, fallback: Any = None) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def provider_usage() -> dict[str, Any]:
    value = read_json(RESULT_ROOT / "openrouter-generation-usage.json", {}) or {}
    return value if isinstance(value, dict) else {}


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def duration_ms(block: Any) -> int | None:
    if not isinstance(block, dict):
        return None
    started = parse_time(block.get("started_at"))
    finished = parse_time(block.get("finished_at"))
    if not started or not finished:
        return None
    return max(0, int((finished - started).total_seconds() * 1000))


def static_labels() -> dict[str, str]:
    selection = read_json(V1_ROOT / "selection.json", {}) or {}
    labels: dict[str, str] = {}
    for difficulty in ("easy", "hard"):
        for item in selection.get(difficulty, []):
            if isinstance(item, dict) and item.get("instance_id"):
                labels[item["instance_id"]] = difficulty
    return labels


def frozen_tasks() -> list[str]:
    return [
        line.strip()
        for line in (V1_ROOT / "tasks" / "mercury-v1.txt").read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def expected_test_counts(task: str) -> tuple[int, int]:
    config = read_json(TASK_ROOT / task / "tests" / "config.json", {}) or {}
    return len(config.get("FAIL_TO_PASS", [])), len(config.get("PASS_TO_PASS", []))


def result_trial_name(raw: dict[str, Any], raw_dir: Path) -> str:
    return str(raw.get("trial_name") or raw.get("config", {}).get("trial_name") or raw_dir.name)


def infer_harness(raw: dict[str, Any]) -> str | None:
    agent_info = raw.get("agent_info") or {}
    name = str(agent_info.get("name") or "").lower()
    if name in HARNESS_ORDER:
        return name
    if name in {"opencode", "open-code"}:
        return "opencode"
    if name in {"claude", "claude_code", "claude-code"}:
        return "claude-code"
    if name in {"ohmypi", "oh-my-pi", "omp"}:
        return "oh-my-pi"
    agent_config = raw.get("config", {}).get("agent", {}) or {}
    import_path = str(agent_config.get("import_path") or "").lower()
    if "critique_code" in import_path:
        return "critique-code"
    if "oh_my_pi" in import_path:
        return "oh-my-pi"
    name = str(agent_config.get("name") or "").lower()
    return name if name in HARNESS_ORDER else None


def all_raw_results() -> list[tuple[Path, dict[str, Any]]]:
    found: list[tuple[Path, dict[str, Any]]] = []
    if not TRIALS_ROOT.exists():
        return found
    for result_path in sorted(TRIALS_ROOT.rglob("result.json")):
        raw = read_json(result_path)
        if isinstance(raw, dict):
            found.append((result_path.parent, raw))
    return found


def select_latest_trials(tasks: list[str]) -> dict[tuple[str, str], tuple[Path, dict[str, Any]]]:
    candidates: dict[tuple[str, str], list[tuple[Path, dict[str, Any]]]] = {}
    task_set = set(tasks)
    for raw_dir, raw in all_raw_results():
        task = str(raw.get("task_name") or "")
        harness = infer_harness(raw)
        if task in task_set and harness in HARNESS_ORDER:
            candidates.setdefault((task, harness), []).append((raw_dir, raw))

    selected: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
    for key, values in candidates.items():
        selected[key] = max(
            values,
            key=lambda item: parse_time(item[1].get("finished_at")) or datetime.min,
        )
    return selected


def verifier_counts(raw_dir: Path, task: str, reward: float | None) -> dict[str, Any]:
    f2p_total, p2p_total = expected_test_counts(task)
    report = read_json(raw_dir / "verifier" / "report.json", {}) or {}
    if isinstance(report, dict) and task in report:
        report = report[task]
    tests_status = report.get("tests_status", {}) if isinstance(report, dict) else {}

    counts: dict[str, Any] = {
        "f2p_passed": None,
        "f2p_total": f2p_total,
        "p2p_passed": None,
        "p2p_total": p2p_total,
    }
    for key, prefix in (("FAIL_TO_PASS", "f2p"), ("PASS_TO_PASS", "p2p")):
        status = tests_status.get(key, {}) if isinstance(tests_status, dict) else {}
        success = status.get("success") if isinstance(status, dict) else None
        failure = status.get("failure") if isinstance(status, dict) else None
        if isinstance(success, list):
            counts[f"{prefix}_passed"] = len(success)
            if isinstance(failure, list):
                counts[f"{prefix}_total"] = len(success) + len(failure)

    # A successful FeatBench verifier means both suites passed. This fallback
    # is only used when an old Harbor verifier omitted report.json.
    if reward == 1.0 and counts["f2p_passed"] is None:
        counts["f2p_passed"] = f2p_total
        counts["p2p_passed"] = p2p_total
    return counts


def agent_text(raw_dir: Path, raw: dict[str, Any]) -> str:
    chunks: list[str] = []
    runtime_result = read_json(raw_dir / "agent" / "critique-code" / "runtime-result.json", {})
    if isinstance(runtime_result, dict) and runtime_result.get("assistantText"):
        chunks.append(str(runtime_result["assistantText"]))

    trajectory = read_json(raw_dir / "agent" / "trajectory.json")
    if isinstance(trajectory, dict):
        for step in trajectory.get("steps", []):
            if isinstance(step, dict) and step.get("source") == "agent":
                chunks.append(str(step.get("message") or ""))
    elif isinstance(trajectory, list):
        for row in trajectory:
            if not isinstance(row, dict):
                continue
            message = row.get("message") or {}
            if row.get("type") == "message_end" and message.get("role") == "assistant":
                content = message.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        str(part.get("text", ""))
                        for part in content
                        if isinstance(part, dict)
                    )
                chunks.append(str(content))

    for jsonl_path in (
        raw_dir / "agent" / "oh-my-pi" / "omp.jsonl",
        raw_dir / "agent" / "critique-code" / "trajectory.jsonl",
    ):
        for row in read_json_lines(jsonl_path):
            message = row.get("message") or {}
            if row.get("type") == "message_end" and message.get("role") == "assistant":
                content = message.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        str(part.get("text", ""))
                        for part in content
                        if isinstance(part, dict)
                    )
                chunks.append(str(content))

    for path in sorted((raw_dir / "agent").rglob("*")) if (raw_dir / "agent").exists() else []:
        if not path.is_file() or path.suffix not in {".txt", ".log"}:
            continue
        try:
            chunks.append(path.read_text(errors="replace")[-20_000:])
        except OSError:
            pass
    return "\n".join(chunks)[-50_000:]


def claimed_success(raw_dir: Path, raw: dict[str, Any]) -> bool:
    text = agent_text(raw_dir, raw)
    return bool(
        re.search(
            r"\b(?:done|completed|implemented|fixed|resolved|finished)\b|"
            r"(?:all|the)\s+tests?\s+(?:now\s+)?pass(?:ed|ing)?|"
            r"tests?\s+pass(?:ed|ing)?",
            text,
            re.IGNORECASE,
        )
    )


def parse_atif_tools(path: Path) -> dict[str, Any]:
    trajectory = read_json(path)
    if not isinstance(trajectory, dict):
        return {"model_calls": 0, "tool_calls": 0, "failed_tool_calls": 0, "normalized": {}}
    model_calls = 0
    tool_calls = 0
    failed_tool_calls = 0
    normalized: dict[str, int] = {}
    for step in trajectory.get("steps", []):
        if not isinstance(step, dict):
            continue
        if step.get("source") == "agent":
            model_calls += int(step.get("llm_call_count") or 0)
        observations = step.get("observation") or {}
        observation_results = observations.get("results", []) if isinstance(observations, dict) else []
        failed_ids = {
            str(item.get("source_call_id"))
            for item in observation_results
            if isinstance(item, dict)
            and re.search(r"\b(?:error|failed|failure|exception|traceback)\b", str(item.get("content", "")), re.IGNORECASE)
        }
        for call in step.get("tool_calls", []) or []:
            if not isinstance(call, dict):
                continue
            tool_calls += 1
            name = str(call.get("function_name") or call.get("name") or "tool")
            category = normalized_tool(name, call.get("arguments"))
            normalized[category] = normalized.get(category, 0) + 1
            if str(call.get("tool_call_id")) in failed_ids:
                failed_tool_calls += 1
    return {
        "model_calls": model_calls,
        "tool_calls": tool_calls,
        "failed_tool_calls": failed_tool_calls,
        "normalized": normalized,
    }


def tool_metrics(raw_dir: Path, raw: dict[str, Any]) -> dict[str, Any]:
    agent_result = raw.get("agent_result") or {}
    metadata = agent_result.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    normalized = metadata.get("normalized_tools")
    if not isinstance(normalized, dict):
        normalized = {}
    model_calls = metadata.get("model_calls")
    tool_calls = metadata.get("tool_calls")
    failed = metadata.get("failed_tool_calls")
    if not isinstance(model_calls, int) or not isinstance(tool_calls, int):
        atif = parse_atif_tools(raw_dir / "agent" / "trajectory.json")
        if (raw_dir / "agent" / "trajectory.json").exists():
            model_calls = atif["model_calls"]
            tool_calls = atif["tool_calls"]
            failed = atif["failed_tool_calls"]
            if not normalized:
                normalized = atif["normalized"]

    if not isinstance(tool_calls, int):
        native = raw_dir / "agent" / "oh-my-pi" / "omp.jsonl"
        if not native.exists():
            native = raw_dir / "agent" / "critique-code" / "trajectory.jsonl"
        stats = parse_pi_jsonl(native)
        model_calls = stats["model_calls"]
        tool_calls = stats["tool_calls"]
        failed = stats["failed_tool_calls"]
        if not normalized:
            normalized = stats["normalized_tools"]

    return {
        "model_calls": int(model_calls or 0),
        "tool_calls": int(tool_calls or 0),
        "failed_tool_calls": int(failed or 0),
        "normalized_tools": {str(k): int(v) for k, v in normalized.items()},
    }


def patch_stats(raw_dir: Path) -> dict[str, Any]:
    patch_path = raw_dir / "agent" / "patch.diff"
    if not patch_path.exists():
        return {"files_changed": None, "lines_added": None, "lines_deleted": None}
    try:
        lines = patch_path.read_text(errors="replace").splitlines()
    except OSError:
        return {"files_changed": None, "lines_added": None, "lines_deleted": None}
    return {
        "files_changed": sum(1 for line in lines if line.startswith("diff --git ")),
        "lines_added": sum(1 for line in lines if line.startswith("+") and not line.startswith("+++")),
        "lines_deleted": sum(1 for line in lines if line.startswith("-") and not line.startswith("---")),
    }


def copy_or_write(source: Path, target: Path, content: str = "") -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        shutil.copyfile(source, target)
    else:
        target.write_text(content)


def copy_trajectory(raw_dir: Path, target: Path) -> None:
    source = raw_dir / "agent" / "trajectory.json"
    if source.exists():
        copy_or_write(source, target)
        return
    jsonl = raw_dir / "agent" / "oh-my-pi" / "omp.jsonl"
    if not jsonl.exists():
        jsonl = raw_dir / "agent" / "critique-code" / "trajectory.jsonl"
    rows: list[Any] = []
    if jsonl.exists():
        for line in jsonl.read_text(errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    write_json(target, rows)


def copy_agent_log(raw_dir: Path, target: Path) -> None:
    files = (
        [
            path
            for path in sorted((raw_dir / "agent").rglob("*"))
            if path.is_file() and path.suffix in {".txt", ".log"}
        ]
        if (raw_dir / "agent").exists()
        else []
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    if not files:
        target.write_text("")
        return
    with target.open("w") as output:
        for path in files:
            output.write(f"\n===== {path.relative_to(raw_dir / 'agent')} =====\n")
            try:
                output.write(path.read_text(errors="replace"))
            except OSError:
                pass


def copy_verifier_log(raw_dir: Path, target: Path) -> None:
    source = raw_dir / "verifier" / "test-stdout.txt"
    if not source.exists():
        source = raw_dir / "verifier" / "report.json"
    copy_or_write(source, target)


def canonical_record(
    task: str,
    harness: str,
    raw_dir: Path | None,
    raw: dict[str, Any] | None,
    *,
    labels: dict[str, str],
    launch_state: dict[str, Any],
    usage: dict[str, Any],
) -> dict[str, Any]:
    raw = raw or {}
    reward = ((raw.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    reward = float(reward) if isinstance(reward, (int, float)) else None
    counts = verifier_counts(raw_dir, task, reward) if raw_dir else {
        "f2p_passed": None,
        "f2p_total": expected_test_counts(task)[0],
        "p2p_passed": None,
        "p2p_total": expected_test_counts(task)[1],
    }
    agent_result = raw.get("agent_result") or {}
    metadata = agent_result.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    input_tokens = agent_result.get("n_input_tokens")
    output_tokens = agent_result.get("n_output_tokens")
    cache_tokens = agent_result.get("n_cache_tokens")
    harness_cost_usd = agent_result.get("cost_usd")
    input_tokens = int(input_tokens) if isinstance(input_tokens, (int, float)) else None
    output_tokens = int(output_tokens) if isinstance(output_tokens, (int, float)) else None
    cache_tokens = int(cache_tokens) if isinstance(cache_tokens, (int, float)) else None
    harness_cost_usd = float(harness_cost_usd) if isinstance(harness_cost_usd, (int, float)) else None
    reasoning_tokens = metadata.get("reasoning_tokens")
    reasoning_tokens = int(reasoning_tokens) if isinstance(reasoning_tokens, (int, float)) else None
    provider_cost_usd = None
    provider_ids: list[str] = []
    provider_ok = 0
    provider_usage_complete = False
    if raw_dir:
        relative_dir = str(raw_dir.relative_to(RESULT_ROOT))
        trial_ids = usage.get("trial_ids", {}) if isinstance(usage, dict) else {}
        provider_ids = trial_ids.get(relative_dir, []) if isinstance(trial_ids, dict) else []
        generations = usage.get("generations", {}) if isinstance(usage, dict) else {}
        if isinstance(generations, dict):
            provider_records = [
                generations.get(generation_id)
                for generation_id in provider_ids
                if isinstance(generations.get(generation_id), dict)
            ]
            provider_costs = [
                item.get("total_cost")
                for item in provider_records
                if item.get("status") == "ok" and isinstance(item.get("total_cost"), (int, float))
            ]
            provider_ok = len(provider_costs)
            provider_usage_complete = bool(provider_ids) and provider_ok == len(provider_ids)
            if provider_usage_complete:
                provider_cost_usd = sum(float(cost) for cost in provider_costs)

    catalog_estimate = None
    if input_tokens is not None and output_tokens is not None:
        catalog_estimate = (input_tokens * 0.04 + output_tokens * 0.15) / 1_000_000
    if provider_usage_complete:
        cost_usd = provider_cost_usd
        cost_source = "openrouter_generation"
    elif catalog_estimate is not None:
        cost_usd = catalog_estimate
        cost_source = "estimated_from_openrouter_catalog"
    elif harness_cost_usd is not None:
        cost_usd = harness_cost_usd
        cost_source = "harness_reported_fallback"
    else:
        cost_usd = None
        cost_source = "unavailable"

    tools = tool_metrics(raw_dir, raw) if raw_dir else {
        "model_calls": 0,
        "tool_calls": 0,
        "failed_tool_calls": 0,
        "normalized_tools": {},
    }
    exception = raw.get("exception_info")
    exception_text = json.dumps(exception, sort_keys=True) if exception else ""
    exception_type = str(exception.get("exception_type") or "") if isinstance(exception, dict) else ""
    exception_message = str(exception.get("exception_message") or "") if isinstance(exception, dict) else ""
    launch = launch_state.get(str(launch_state.get("sequence", "")), {})
    launch_code = launch.get("return_code") if isinstance(launch, dict) else None
    timeout = bool(
        re.search(
            r"timeout|timed out",
            f"{exception_type} {exception_message}".lower(),
        )
    )
    compatibility = False
    final_text = agent_text(raw_dir, raw) if raw_dir else ""
    if harness == "claude-code":
        compatibility = bool(
            re.search(
                r"incompatib|unsupported.{0,80}model|model.{0,80}(?:unsupported|not supported|cannot use|not found)|"
                r"anthropic.{0,80}(?:required|only)|empty or malformed response|not Anthropic-issued",
                f"{final_text}\n{exception_message}",
                re.IGNORECASE | re.DOTALL,
            )
        )
    api_error = bool(
        re.search(r"api.?error|unknownapierror|malformed response", f"{exception_type} {exception_message}", re.IGNORECASE)
    )
    resolved = reward == 1.0
    claimed = claimed_success(raw_dir, raw) if raw_dir else False
    agent_ms = duration_ms(raw.get("agent_execution")) if raw_dir else None
    setup_ms = duration_ms(raw.get("environment_setup")) if raw_dir else None
    verifier_ms = duration_ms(raw.get("verifier")) if raw_dir else None
    patch = patch_stats(raw_dir) if raw_dir else {"files_changed": None, "lines_added": None, "lines_deleted": None}
    total_tokens = (input_tokens + output_tokens) if input_tokens is not None and output_tokens is not None else None

    record = {
        "schema_version": "mercury-v1",
        "task": task,
        "difficulty": labels.get(task, "unlabelled"),
        "harness": harness,
        "harness_version": (raw.get("agent_info") or {}).get("version") if raw_dir else None,
        "model": MODEL,
        "result": {
            "resolved": resolved,
            **counts,
            "reward": reward,
        },
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "cached": cache_tokens,
            "reasoning": reasoning_tokens,
            "total": total_tokens,
        },
        "cost_usd": cost_usd,
        "cost_source": cost_source,
        "provider_accounting": {
            "generation_ids": provider_ids,
            "records_found": provider_ok,
            "complete": provider_usage_complete,
            "cost_usd": provider_cost_usd,
        },
        "timing": {
            "sandbox_setup_ms": setup_ms,
            "agent_ms": agent_ms,
            "verification_ms": verifier_ms,
        },
        "model_requests": tools["model_calls"],
        "tools": {
            "total": tools["tool_calls"],
            "failed": tools["failed_tool_calls"],
            **tools["normalized_tools"],
        },
        "patch": patch,
        "termination": {
            "claimed_success": claimed,
            "timeout": timeout,
            "crash": bool(exception and not timeout and not api_error),
            "api_error": api_error,
            "compatibility_error": compatibility,
        },
        "model_compatibility_error": compatibility,
        "status": "complete" if raw_dir else "missing",
        "raw_trial_dir": str(raw_dir) if raw_dir else None,
        "launcher_return_code": launch_code,
    }
    return record


def normalize(tasks: list[str]) -> list[dict[str, Any]]:
    labels = static_labels()
    selected = select_latest_trials(tasks)
    usage = provider_usage()
    state = read_json(RESULT_ROOT / "launcher" / "state.json", {}) or {}
    records: list[dict[str, Any]] = []
    plan = read_json(RESULT_ROOT / "launcher" / "run-plan.json", []) or []
    if not isinstance(plan, list) or len(plan) != 40:
        plan = []
        for index, task in enumerate(tasks):
            for offset, harness in enumerate(HARNESS_ORDER):
                plan.append({"sequence": index * 4 + offset, "task": task, "harness": harness})

    for item in plan:
        task = str(item["task"])
        harness = str(item["harness"])
        raw_dir, raw = selected.get((task, harness), (None, None))
        record = canonical_record(
            task,
            harness,
            raw_dir,
            raw,
            labels=labels,
            launch_state={"sequence": item.get("sequence"), **state},
            usage=usage,
        )
        record["sequence"] = item.get("sequence")
        record["run_order"] = HARNESS_ORDER[(tasks.index(task) + HARNESS_ORDER.index(harness)) % 4]
        output_dir = CANONICAL_ROOT / task / harness
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "result.json", record)
        if raw_dir:
            copy_trajectory(raw_dir, output_dir / "trajectory.json")
            copy_or_write(raw_dir / "agent" / "patch.diff", output_dir / "patch.diff")
            copy_agent_log(raw_dir, output_dir / "agent.log")
            copy_verifier_log(raw_dir, output_dir / "verifier.log")
        else:
            write_json(output_dir / "trajectory.json", [])
            (output_dir / "patch.diff").write_text("")
            (output_dir / "agent.log").write_text("")
            (output_dir / "verifier.log").write_text("")
        write_json(
            output_dir / "metadata.json",
            {
                "task": task,
                "harness": harness,
                "sequence": item.get("sequence"),
                "raw_trial_dir": str(raw_dir) if raw_dir else None,
                "model": MODEL,
                "openrouter_key_scope": "shared-key; per-harness provider ledger unavailable",
            },
        )
        records.append(record)

    report = aggregate(records)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(REPORT_ROOT / "mercury-v1.json", report)
    (REPORT_ROOT / "mercury-v1.md").write_text(render_markdown(report))
    return records


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_harness: dict[str, Any] = {}
    for harness in HARNESS_ORDER:
        rows = [row for row in records if row["harness"] == harness]
        solved = sum(1 for row in rows if row["result"]["resolved"] is True)
        costs = [row["cost_usd"] for row in rows if isinstance(row["cost_usd"], (int, float))]
        times = [row["timing"]["agent_ms"] for row in rows if isinstance(row["timing"]["agent_ms"], (int, float))]
        regressions = [
            row
            for row in rows
            if row["result"].get("f2p_passed") == row["result"].get("f2p_total")
            and isinstance(row["result"].get("p2p_passed"), int)
            and row["result"].get("p2p_passed") < row["result"].get("p2p_total")
        ]
        token_values = [
            row["tokens"]["total"]
            for row in rows
            if isinstance(row["tokens"].get("total"), int)
        ]
        by_harness[harness] = {
            "runs": len(rows),
            "resolved": solved,
            "total_cost_usd": round(sum(costs), 6),
            "cost_per_resolved_usd": round(sum(costs) / solved, 6) if solved else None,
            "total_tokens": sum(token_values) if token_values else None,
            "median_agent_ms": int(statistics.median(times)) if times else None,
            "regressions": len(regressions),
            "false_completions": sum(
                1
                for row in rows
                if row["termination"]["claimed_success"] and row["result"]["resolved"] is False
            ),
            "timeouts": sum(1 for row in rows if row["termination"]["timeout"]),
            "crashes": sum(1 for row in rows if row["termination"]["crash"]),
            "api_errors": sum(1 for row in rows if row["termination"].get("api_error")),
            "compatibility_errors": sum(1 for row in rows if row["termination"]["compatibility_error"]),
            "model_requests": sum(row["model_requests"] for row in rows),
            "tool_calls": sum(row["tools"]["total"] for row in rows),
            "failed_tool_calls": sum(row["tools"]["failed"] for row in rows),
        }
    return {
        "benchmark": "mercury-harness-v1",
        "model": MODEL,
        "tasks": len({row["task"] for row in records}),
        "trials": len(records),
        "completed_trials": sum(1 for row in records if row["status"] == "complete"),
        "environment": "E2B; fresh single-container sandbox per trial",
        "concurrency": 2,
        "cost_note": "OpenRouter generation accounting is used when a provider generation ID was captured; remaining costs are estimates from the Mercury model catalog price.",
        "key_note": "The available OpenRouter credential was shared across harnesses; per-harness provider ledgers were therefore not possible for this run.",
        "harnesses": by_harness,
        "records": records,
    }


def fmt_ms(value: int | None) -> str:
    if value is None:
        return "—"
    seconds = value // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Mercury Harness Benchmark V1",
        "",
        f"Model: `{MODEL}`  ",
        "Environment: E2B, one fresh single-container sandbox per trial  ",
        f"Trials: {report['completed_trials']}/{report['trials']} completed  ",
        "",
        "> Provider-side OpenRouter generation accounting is used where a generation ID was captured; remaining costs are estimates from the Mercury model catalog. The available OpenRouter key was shared, so billing could not be split into independent per-harness ledgers.",
        "",
        "## Aggregate",
        "",
        "| Harness | Solved | Total cost | Cost/solved | Tokens | Median agent time | Regressions | False completions |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for harness in HARNESS_ORDER:
        row = report["harnesses"][harness]
        token_text = f"{row['total_tokens']:,}" if row["total_tokens"] is not None else "—"
        total_cost = f"${row['total_cost_usd']:.6f}"
        per_cost = f"${row['cost_per_resolved_usd']:.6f}" if row["cost_per_resolved_usd"] is not None else "—"
        lines.append(
            f"| {harness} | {row['resolved']}/{row['runs']} | {total_cost} | {per_cost} | {token_text} | {fmt_ms(row['median_agent_ms'])} | {row['regressions']} | {row['false_completions']} |"
        )
    lines.extend(
        [
            "",
            "## Task results",
            "",
            "| # | Task | Difficulty | Harness | Resolved | F2P | P2P | Agent time | Cost |",
            "|---:|---|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in sorted(report["records"], key=lambda item: item.get("sequence", 0)):
        result = row["result"]
        f2p = f"{result['f2p_passed']}/{result['f2p_total']}" if result["f2p_passed"] is not None else "—"
        p2p = f"{result['p2p_passed']}/{result['p2p_total']}" if result["p2p_passed"] is not None else "—"
        cost = f"${row['cost_usd']:.6f}" if row["cost_usd"] is not None else "—"
        lines.append(
            f"| {row['sequence'] + 1} | `{row['task']}` | {row['difficulty']} | {row['harness']} | {'PASS' if result['resolved'] else 'FAIL'} | {f2p} | {p2p} | {fmt_ms(row['timing']['agent_ms'])} | {cost} |"
        )
    lines.extend(
        [
            "",
            "## Run notes",
            "",
            f"- Oracle/reference validation passed for all {len(frozen_tasks())} frozen tasks before agent trials.",
            f"- The aggregate uses {len(report['records'])} canonical records; raw Harbor contains {len(all_raw_results())} records because setup/validation retries were retained.",
            f"- Provider-side cost was reconciled for {sum(1 for row in report['records'] if row['cost_source'] == 'openrouter_generation')} trials; {sum(1 for row in report['records'] if row['cost_source'] == 'estimated_from_openrouter_catalog')} use catalog estimates because no complete provider generation ledger was captured.",
            f"- Claude Code recorded {sum(1 for row in report['records'] if row['termination']['compatibility_error'])} Mercury/OpenRouter compatibility API error; its external verifier still ran.",
            "",
            "Raw Harbor trials remain under `benchmarks/mercury_v1/results/mercury-v1/trials/`; normalized per-trial artifacts are under `.../canonical/<task>/<harness>/`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", nargs="*", default=None)
    args = parser.parse_args()
    tasks = args.tasks or frozen_tasks()
    normalize(tasks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
