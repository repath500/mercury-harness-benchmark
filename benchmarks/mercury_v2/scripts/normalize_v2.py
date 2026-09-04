#!/usr/bin/env python3
"""Normalize V2 Harbor trials into reproducible, secret-free study artifacts."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from benchmarks.mercury_v1.agents.common import normalized_tool, number, parse_pi_jsonl, read_json_lines


V2_ROOT = ROOT / "benchmarks" / "mercury_v2"
TASK_ROOT = V2_ROOT / "tasks" / "featbench"
RESULT_ROOT = V2_ROOT / "results" / "mercury-v2"
TRIALS_ROOT = RESULT_ROOT / "trials"
CANONICAL_ROOT = RESULT_ROOT / "canonical"
REPORT_ROOT = ROOT / "reports" / "mercury-v2"
USAGE_PATH = RESULT_ROOT / "openrouter-generation-usage.json"
MODEL = "z-ai/glm-5.3-flash"
HARNESS_ORDER = (
    "pi", "oh-my-pi", "claude-code", "codex", "deepseek-harness", "critique-code", "opencode"
)
HARNESS_LABELS = {
    "pi": "Pi (vanilla)", "oh-my-pi": "Oh My Pi", "claude-code": "Claude Code",
    "codex": "Codex", "deepseek-harness": "DeepSeek Harness", "critique-code": "CritiqueCode",
    "opencode": "OpenCode",
}
TEST_COMMAND_RE = re.compile(
    r"(?:pytest|py\.test|npm\s+(?:test|run\s+test)|pnpm\s+(?:test|run\s+test)|"
    r"bun\s+test|cargo\s+test|go\s+test|mvn\s+test|gradle\s+test)", re.I
)


def read_json(path: Path, fallback: Any = None) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def parse_time(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def duration_ms(block: Any) -> int | None:
    if not isinstance(block, dict):
        return None
    start = parse_time(block.get("started_at"))
    finish = parse_time(block.get("finished_at"))
    return max(0, int((finish - start).total_seconds() * 1000)) if start and finish else None


def tasks() -> list[str]:
    return [
        line.strip() for line in (V2_ROOT / "tasks" / "mercury-v2.txt").read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def labels() -> dict[str, str]:
    selection = read_json(V2_ROOT / "selection.json", {}) or {}
    result: dict[str, str] = {}
    for difficulty in ("easy", "hard", "very_hard"):
        for item in selection.get(difficulty, []):
            if isinstance(item, dict) and item.get("instance_id"):
                result[str(item["instance_id"])] = difficulty.replace("_", "-")
    return result


def expected_test_counts(task: str) -> tuple[int, int]:
    config = read_json(TASK_ROOT / task / "tests" / "config.json", {}) or {}
    return len(config.get("FAIL_TO_PASS", [])), len(config.get("PASS_TO_PASS", []))


def infer_harness(raw: dict[str, Any]) -> str | None:
    info = raw.get("agent_info") or {}
    name = str(info.get("name") or "").lower()
    aliases = {
        "ohmypi": "oh-my-pi", "omp": "oh-my-pi", "oh-my-pi": "oh-my-pi",
        "claude": "claude-code", "claude_code": "claude-code", "claude-code": "claude-code",
        "open-code": "opencode", "opencode": "opencode", "dsh": "deepseek-harness",
        "deepseek": "deepseek-harness", "deepseek-harness": "deepseek-harness",
    }
    if name in HARNESS_ORDER:
        return name
    if name in aliases:
        return aliases[name]
    config = raw.get("config", {}).get("agent", {}) or {}
    import_path = str(config.get("import_path") or "").lower()
    for key in HARNESS_ORDER:
        if key.replace("-", "_") in import_path or key in import_path:
            return key
    config_name = str(config.get("name") or "").lower()
    return aliases.get(config_name, config_name if config_name in HARNESS_ORDER else None)


def all_raw_results() -> list[tuple[Path, dict[str, Any]]]:
    result = []
    for path in sorted(TRIALS_ROOT.rglob("result.json")) if TRIALS_ROOT.exists() else []:
        raw = read_json(path)
        if isinstance(raw, dict):
            result.append((path.parent, raw))
    return result


def select_latest(plan_tasks: list[str]) -> dict[tuple[str, str], tuple[Path, dict[str, Any]]]:
    candidates: dict[tuple[str, str], list[tuple[Path, dict[str, Any]]]] = {}
    wanted = set(plan_tasks)
    for raw_dir, raw in all_raw_results():
        # Only the canonical Harbor directory is eligible for publication.
        # Retry/stall directories are intentionally retained as evidence, but
        # must never win a "latest" search or contaminate the task matrix.
        # Recovery envelopes can retain the source template's task_name or
        # agent_info. The immutable Harbor directory is authoritative for the
        # matrix key, so match it against the frozen plan rather than trusting
        # those copied envelope fields.
        for task in wanted:
            for harness in HARNESS_ORDER:
                expected_name = f"{task}__{harness}__v2-agents"
                if raw_dir.name == expected_name:
                    candidates.setdefault((task, harness), []).append((raw_dir, raw))
                    break
            else:
                continue
            break
    return {
        key: max(values, key=lambda item: parse_time(item[1].get("finished_at")) or datetime.min.replace(tzinfo=timezone.utc))
        for key, values in candidates.items()
    }


def directory_size(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                pass
    return total


def patch_stats(raw_dir: Path | None) -> dict[str, Any]:
    path = raw_dir / "agent" / "patch.diff" if raw_dir else None
    if not path or not path.exists():
        return {"files_changed": None, "lines_added": None, "lines_deleted": None}
    lines = path.read_text(errors="replace").splitlines()
    return {
        "files_changed": sum(line.startswith("diff --git ") for line in lines),
        "lines_added": sum(line.startswith("+") and not line.startswith("+++") for line in lines),
        "lines_deleted": sum(line.startswith("-") and not line.startswith("---") for line in lines),
    }


def raw_text(raw_dir: Path | None) -> str:
    if not raw_dir or not (raw_dir / "agent").exists():
        return ""
    chunks: list[str] = []
    for path in sorted((raw_dir / "agent").rglob("*")):
        if not path.is_file() or path.suffix not in {".txt", ".log", ".json", ".jsonl"}:
            continue
        try:
            chunks.append(path.read_text(errors="replace")[-30_000:])
        except OSError:
            pass
    return "\n".join(chunks)[-100_000:]


def claim_metrics(text: str) -> dict[str, Any]:
    pattern = r"\b(?:done|completed|implemented|fixed|resolved|finished|all\s+tests?\s+(?:now\s+)?pass(?:ed|ing)?)\b"
    claims = re.findall(pattern, text, re.IGNORECASE)
    return {"claimed_success": bool(claims), "claim_count": len(claims)}


def atif_tools(path: Path) -> dict[str, Any]:
    trajectory = read_json(path)
    if not isinstance(trajectory, dict):
        return {"model_calls": 0, "tool_calls": 0, "failed_tool_calls": 0, "normalized": {}}
    model_calls = tool_calls = failed = test_runs = 0
    normalized: dict[str, int] = {}
    for step in trajectory.get("steps", []):
        if not isinstance(step, dict):
            continue
        if step.get("source") == "agent":
            model_calls += int(step.get("llm_call_count") or 0)
        results = (step.get("observation") or {}).get("results", [])
        failed_ids = {
            str(item.get("source_call_id")) for item in results if isinstance(item, dict)
            and re.search(r"\b(?:error|failed|failure|exception|traceback)\b", str(item.get("content", "")), re.I)
        }
        for call in step.get("tool_calls", []) or []:
            if not isinstance(call, dict):
                continue
            tool_calls += 1
            name = str(call.get("function_name") or call.get("name") or "tool")
            category = normalized_tool(name, call.get("arguments"))
            normalized[category] = normalized.get(category, 0) + 1
            if TEST_COMMAND_RE.search(_content_text(call.get("arguments"))):
                test_runs += 1
            failed += str(call.get("tool_call_id")) in failed_ids
    return {"model_calls": model_calls, "tool_calls": tool_calls, "failed_tool_calls": failed, "normalized": normalized, "test_runs": test_runs}


def native_rows(raw_dir: Path | None) -> list[dict[str, Any]]:
    if not raw_dir:
        return []
    paths = list((raw_dir / "agent").rglob("*.jsonl")) if (raw_dir / "agent").exists() else []
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(read_json_lines(path))
    return rows


def _content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True)
    except TypeError:
        return str(value)


def structured_native_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Read Pi-style session JSONL without counting prose or stream chunks."""
    model_calls = tool_calls = failed = test_count = 0
    normalized: dict[str, int] = {}
    request_times: list[datetime] = []
    tool_times: list[datetime] = []
    request_inputs: list[int] = []
    seen_tool_results: set[str] = set()
    for row in rows:
        parsed = parse_time(row.get("timestamp") or row.get("time") or row.get("createdAt"))
        message = row.get("message") if isinstance(row.get("message"), dict) else None
        if str(row.get("type") or "").lower() == "message" and message:
            if message.get("role") == "assistant":
                usage = message.get("usage")
                if isinstance(usage, dict):
                    model_calls += 1
                    request_times.append(parsed) if parsed else None
                    value = usage.get("inputTokens", usage.get("input", usage.get("promptTokens")))
                    if value is not None:
                        request_inputs.append(int(number(value)))
            content = message.get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    block_type = str(block.get("type") or "").lower()
                    if block_type in {"toolcall", "tool_use", "tool_call"}:
                        tool_calls += 1
                        tool_times.append(parsed) if parsed else None
                        name = str(block.get("name") or block.get("toolName") or "tool")
                        args = block.get("arguments", block.get("input"))
                        category = normalized_tool(name, args)
                        normalized[category] = normalized.get(category, 0) + 1
                        if TEST_COMMAND_RE.search(_content_text(args)):
                            test_count += 1
                    elif block_type in {"toolresult", "tool_result"}:
                        call_id = str(block.get("toolCallId") or block.get("tool_call_id") or "")
                        if block.get("isError") or block.get("is_error") or block.get("error"):
                            if call_id not in seen_tool_results:
                                failed += 1
                                seen_tool_results.add(call_id)

        # Preserve support for Pi's older explicit event names.
        row_type = str(row.get("type") or "").lower()
        if row_type == "message_end" and isinstance(row.get("message"), dict) and row["message"].get("role") == "assistant":
            if not isinstance(row["message"].get("usage"), dict):
                model_calls += 1
                request_times.append(parsed) if parsed else None
        if row_type == "tool_execution_start":
            tool_calls += 1
            tool_times.append(parsed) if parsed else None
            args = row.get("args")
            category = normalized_tool(str(row.get("toolName") or row.get("tool") or "tool"), args)
            normalized[category] = normalized.get(category, 0) + 1
            if TEST_COMMAND_RE.search(_content_text(args)):
                test_count += 1
        if row_type == "tool_execution_end" and (row.get("isError") or row.get("error")):
            failed += 1
    return {
        "model_calls": model_calls,
        "tool_calls": tool_calls,
        "failed_tool_calls": failed,
        "normalized_tools": normalized,
        "test_runs": test_count,
        "request_times": request_times,
        "tool_times": tool_times,
        "request_inputs": request_inputs,
    }


def tool_metrics(raw_dir: Path | None, raw: dict[str, Any]) -> dict[str, Any]:
    metadata = ((raw.get("agent_result") or {}).get("metadata") or {})
    metadata = metadata if isinstance(metadata, dict) else {}
    normalized = metadata.get("normalized_tools") if isinstance(metadata.get("normalized_tools"), dict) else {}
    model_calls = metadata.get("model_calls")
    tool_calls = metadata.get("tool_calls")
    failed = metadata.get("failed_tool_calls")
    trajectory = raw_dir / "agent" / "trajectory.json" if raw_dir else Path("/nonexistent")
    if not isinstance(tool_calls, int) and trajectory.exists():
        fallback = atif_tools(trajectory)
        model_calls, tool_calls, failed = fallback["model_calls"], fallback["tool_calls"], fallback["failed_tool_calls"]
        normalized = normalized or fallback["normalized"]
    if not isinstance(tool_calls, int):
        rows = native_rows(raw_dir)
        structured = structured_native_metrics(rows)
        native = next(iter((raw_dir / "agent").rglob("omp.jsonl")), None) if raw_dir else None
        stats = parse_pi_jsonl(native) if native else {"model_calls": 0, "tool_calls": 0, "failed_tool_calls": 0, "normalized_tools": {}}
        model_calls = stats["model_calls"] or structured["model_calls"] or sum(bool(row.get("usage")) for row in rows)
        tool_calls = stats["tool_calls"] or structured["tool_calls"] or sum("tool" in str(row.get("type", "")).lower() for row in rows)
        failed = stats["failed_tool_calls"] or structured["failed_tool_calls"]
        normalized = normalized or stats["normalized_tools"] or structured["normalized_tools"]
    elif raw_dir and "__pi__" in raw_dir.name:
        # Vanilla Pi exposes no Harbor metadata; its assistant messages and
        # tool calls live in the persisted session JSONL.
        structured = structured_native_metrics(native_rows(raw_dir))
        model_calls = structured["model_calls"] or model_calls
        tool_calls = structured["tool_calls"] or tool_calls
        failed = structured["failed_tool_calls"]
        normalized = structured["normalized_tools"] or normalized
    # DeepSeek Harness records streaming tool-call chunks as well as one
    # tool/call event per invocation. Recompute from the native call/result
    # events so the normalized total is not inflated by stream fragments and
    # so tool names nested under data are classified correctly.
    if raw_dir and "__deepseek-harness__" in raw_dir.name:
        direct = raw_dir / "agent" / "deepseek-harness" / "trajectory.jsonl"
        rows = read_json_lines(direct) if direct.exists() else native_rows(raw_dir)
        calls = [row for row in rows if str(row.get("type", "")).lower() == "tool/call"]
        results = set()
        for row in rows:
            if str(row.get("type", "")).lower() != "tool/result":
                continue
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            message = data.get("message") if isinstance(data.get("message"), dict) else {}
            for block in message.get("content", []) if isinstance(message.get("content"), list) else []:
                if isinstance(block, dict) and isinstance(block.get("content"), list):
                    for item in block["content"]:
                        if isinstance(item, dict) and (item.get("isError") or item.get("error")):
                            results.add(str(item.get("toolCallId")))
        normalized = {}
        for row in calls:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            name = str(data.get("name") or data.get("tool") or row.get("name") or "tool")
            category = normalized_tool(name, data.get("arguments"))
            normalized[category] = normalized.get(category, 0) + 1
        tool_calls = len(calls)
        failed = sum(
            str((row.get("data") or {}).get("callId")) in results
            for row in calls
            if isinstance(row.get("data"), dict)
        )
    return {
        "model_calls": int(model_calls or 0), "tool_calls": int(tool_calls or 0),
        "failed_tool_calls": int(failed or 0), "normalized_tools": {str(k): int(v) for k, v in normalized.items()},
    }


def test_runs(raw_dir: Path | None) -> int:
    if not raw_dir:
        return 0
    trajectory = raw_dir / "agent" / "trajectory.json"
    if trajectory.exists():
        return int(atif_tools(trajectory).get("test_runs", 0))
    rows = native_rows(raw_dir)
    if rows:
        structured = structured_native_metrics(rows)
        if structured["model_calls"] or structured["tool_calls"]:
            return int(structured["test_runs"])
    count = 0
    for path in (raw_dir / "agent").rglob("*") if (raw_dir / "agent").exists() else []:
        if not path.is_file() or path.suffix not in {".log", ".txt", ".jsonl", ".json"}:
            continue
        text = path.read_text(errors="replace")
        count += len(re.findall(r"(?:pytest|py\.test|npm\s+(?:test|run\s+test)|pnpm\s+(?:test|run\s+test)|bun\s+test|cargo\s+test|go\s+test|mvn\s+test|gradle\s+test)", text, re.I))
    return count


def event_metrics(raw_dir: Path | None, raw: dict[str, Any]) -> dict[str, Any]:
    rows = native_rows(raw_dir)
    structured = structured_native_metrics(rows)
    timestamps: list[datetime] = []
    request_inputs: list[int] = []
    tool_times: list[datetime] = []
    for row in rows:
        value = row.get("timestamp") or row.get("time") or row.get("createdAt")
        parsed = parse_time(value)
        if parsed:
            timestamps.append(parsed)
        usage = row.get("usage") if isinstance(row.get("usage"), dict) else (row.get("data") or {}).get("usage")
        if isinstance(usage, dict):
            value = usage.get("inputTokens", usage.get("input"))
            if value is not None:
                request_inputs.append(int(number(value)))
        row_type = str(row.get("type") or row.get("kind") or row.get("event") or "").lower()
        if "tool" in row_type and any(word in row_type for word in ("start", "call", "use")) and parsed:
            tool_times.append(parsed)
    agent_start = parse_time(raw.get("agent_execution", {}).get("started_at"))
    first_request = min(structured["request_times"]) if structured["request_times"] else (min(timestamps) if timestamps else None)
    first_tool = min(structured["tool_times"]) if structured["tool_times"] else (min(tool_times) if tool_times else None)
    first_request_ms = int((first_request - agent_start).total_seconds() * 1000) if first_request and agent_start else None
    first_tool_ms = int((first_tool - agent_start).total_seconds() * 1000) if first_tool and agent_start else None
    active_ms = duration_ms(raw.get("agent_execution"))
    setup_ms = duration_ms(raw.get("environment_setup"))
    verify_ms = duration_ms(raw.get("verifier"))
    wall_ms = sum(value or 0 for value in (setup_ms, active_ms, verify_ms)) or None
    return {
        "first_model_request_ms": max(0, first_request_ms) if first_request_ms is not None else None,
        "first_tool_call_ms": max(0, first_tool_ms) if first_tool_ms is not None else None,
        "active_agent_ms": active_ms,
        "active_time_share": (active_ms / wall_ms) if active_ms is not None and wall_ms else None,
        "context_growth": {
            "first_input_tokens": (structured["request_inputs"] or request_inputs)[0] if (structured["request_inputs"] or request_inputs) else None,
            "max_input_tokens": max(structured["request_inputs"] or request_inputs) if (structured["request_inputs"] or request_inputs) else None,
            "ratio": (max(structured["request_inputs"] or request_inputs) / (structured["request_inputs"] or request_inputs)[0]) if (structured["request_inputs"] or request_inputs) and (structured["request_inputs"] or request_inputs)[0] else None,
        },
    }


def verifier_counts(raw_dir: Path | None, task: str, reward: float | None) -> dict[str, Any]:
    f2p, p2p = expected_test_counts(task)
    report = read_json(raw_dir / "verifier" / "report.json", {}) if raw_dir else {}
    report = report.get(task, report) if isinstance(report, dict) else {}
    statuses = report.get("tests_status", {}) if isinstance(report, dict) else {}
    result = {"f2p_passed": None, "f2p_total": f2p, "p2p_passed": None, "p2p_total": p2p}
    for key, prefix in (("FAIL_TO_PASS", "f2p"), ("PASS_TO_PASS", "p2p")):
        status = statuses.get(key, {}) if isinstance(statuses, dict) else {}
        success = status.get("success") if isinstance(status, dict) else None
        failure = status.get("failure") if isinstance(status, dict) else None
        if isinstance(success, list):
            result[f"{prefix}_passed"] = len(success)
            if isinstance(failure, list):
                result[f"{prefix}_total"] = len(success) + len(failure)
    if reward == 1.0 and result["f2p_passed"] is None:
        result.update(f2p_passed=f2p, p2p_passed=p2p)
    return result


def copy_artifacts(raw_dir: Path | None, output: Path, task: str, harness: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    trajectory = raw_dir / "agent" / "trajectory.json" if raw_dir else None
    if not trajectory or not trajectory.exists():
        native = next(iter((raw_dir / "agent").rglob("*.jsonl")), None) if raw_dir and (raw_dir / "agent").exists() else None
        if native and native.exists():
            rows = [row for row in read_json_lines(native)]
            write_json(output / "trajectory.json", rows)
        else:
            write_json(output / "trajectory.json", [])
    else:
        shutil.copyfile(trajectory, output / "trajectory.json")
    patch = raw_dir / "agent" / "patch.diff" if raw_dir else None
    shutil.copyfile(patch, output / "patch.diff") if patch and patch.exists() else (output / "patch.diff").write_text("")
    logs = [p for p in sorted((raw_dir / "agent").rglob("*")) if p.is_file() and p.suffix in {".txt", ".log"}] if raw_dir and (raw_dir / "agent").exists() else []
    with (output / "agent.log").open("w") as stream:
        for path in logs:
            stream.write(f"\n===== {path.relative_to(raw_dir / 'agent')} =====\n")
            stream.write(path.read_text(errors="replace"))
    verifier = raw_dir / "verifier" / "test-stdout.txt" if raw_dir else None
    if not verifier or not verifier.exists():
        verifier = raw_dir / "verifier" / "report.json" if raw_dir else None
    if verifier and verifier.exists():
        shutil.copyfile(verifier, output / "verifier.log")
    else:
        (output / "verifier.log").write_text("")


def provider_cost(raw_dir: Path | None) -> tuple[float | None, list[str], int, bool]:
    """Use fetched OpenRouter generation accounting when the full trial ledger exists."""
    if not raw_dir:
        return None, [], 0, False
    ids = sorted(set(re.findall(r"gen-[A-Za-z0-9_-]+", raw_text(raw_dir))))
    usage = read_json(USAGE_PATH, {}) or {}
    relative = str(raw_dir.relative_to(RESULT_ROOT))
    mapped = usage.get("trial_ids", {}).get(relative, []) if isinstance(usage, dict) else []
    if isinstance(mapped, list) and mapped:
        ids = sorted(set(str(item) for item in mapped))
    generations = usage.get("generations", {}) if isinstance(usage, dict) else {}
    costs = []
    if isinstance(generations, dict):
        for generation_id in ids:
            row = generations.get(generation_id)
            if isinstance(row, dict) and isinstance(row.get("total_cost"), (int, float)):
                costs.append(float(row["total_cost"]))
    complete = bool(ids) and len(costs) == len(ids)
    return (sum(costs) if complete else None), ids, len(costs), complete


def canonical_record(task: str, harness: str, raw_dir: Path | None, raw: dict[str, Any] | None, plan_item: dict[str, Any]) -> dict[str, Any]:
    raw = raw or {}
    reward_value = ((raw.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    reward = float(reward_value) if isinstance(reward_value, (int, float)) else None
    counts = verifier_counts(raw_dir, task, reward)
    agent_result = raw.get("agent_result") or {}
    metadata = agent_result.get("metadata") or {}
    metadata = metadata if isinstance(metadata, dict) else {}
    in_tokens = agent_result.get("n_input_tokens")
    out_tokens = agent_result.get("n_output_tokens")
    cache_tokens = agent_result.get("n_cache_tokens")
    reason_tokens = metadata.get("reasoning_tokens")
    in_tokens = int(in_tokens) if isinstance(in_tokens, (int, float)) else None
    out_tokens = int(out_tokens) if isinstance(out_tokens, (int, float)) else None
    cache_tokens = int(cache_tokens) if isinstance(cache_tokens, (int, float)) else None
    reason_tokens = int(reason_tokens) if isinstance(reason_tokens, (int, float)) else None
    tools = tool_metrics(raw_dir, raw)
    text = raw_text(raw_dir)
    claim = claim_metrics(text)
    exception = raw.get("exception_info") or {}
    exception_type = str(exception.get("exception_type") or "") if isinstance(exception, dict) else ""
    exception_message = str(exception.get("exception_message") or "") if isinstance(exception, dict) else ""
    timeout = bool(re.search(r"timeout|timed out", f"{exception_type} {exception_message}", re.I))
    api_error = bool(re.search(r"api.?error|unknownapierror|malformed response", f"{exception_type} {exception_message}", re.I))
    compatibility = harness == "claude-code" and bool(re.search(r"incompatib|unsupported.{0,80}model|anthropic.{0,80}(?:required|only)|empty or malformed", f"{text}\n{exception_message}", re.I | re.S))
    resolved = reward == 1.0
    verifier_gap = "none"
    if counts["f2p_passed"] == counts["f2p_total"] and counts["p2p_passed"] != counts["p2p_total"]:
        verifier_gap = "regression_p2p_failure"
    elif counts["f2p_passed"] != counts["f2p_total"]:
        verifier_gap = "feature_f2p_failure"
    event = event_metrics(raw_dir, raw)
    provider_usd, generation_ids, provider_records, provider_complete = provider_cost(raw_dir)
    input_cost = (in_tokens * 0.075 / 1_000_000) if in_tokens is not None else 0
    output_cost = (out_tokens * 0.25 / 1_000_000) if out_tokens is not None else 0
    estimated = (input_cost + output_cost) if in_tokens is not None and out_tokens is not None else None
    cost = provider_usd if provider_usd is not None else estimated
    return {
        "schema_version": "mercury-v2",
        "sequence": plan_item.get("sequence"),
        "task": task,
        "difficulty": labels().get(task, "unlabelled"),
        "harness": harness,
        "harness_label": HARNESS_LABELS[harness],
        "harness_version": (raw.get("agent_info") or {}).get("version") if raw_dir else None,
        "model": MODEL,
        "result": {"resolved": resolved, **counts, "reward": reward, "verifier_suite_gap": verifier_gap},
        "tokens": {"input": in_tokens, "output": out_tokens, "cached": cache_tokens, "reasoning": reason_tokens, "total": (in_tokens + out_tokens) if in_tokens is not None and out_tokens is not None else None},
        "cost_usd": cost,
        "cost_source": "openrouter_generation" if provider_complete else ("estimated_from_openrouter_catalog" if estimated is not None else "unavailable"),
        "provider_accounting": {"generation_ids": generation_ids, "records_found": provider_records, "complete": provider_complete, "cost_usd": provider_usd},
        "timing": {"sandbox_setup_ms": duration_ms(raw.get("environment_setup")), "agent_ms": duration_ms(raw.get("agent_execution")), "verification_ms": duration_ms(raw.get("verifier")), **event},
        "model_requests": tools["model_calls"],
        "tools": {"total": tools["tool_calls"], "failed": tools["failed_tool_calls"], **tools["normalized_tools"]},
        "patch": {**patch_stats(raw_dir), "artifact_bytes": directory_size(raw_dir) if raw_dir else 0},
        "observations": {"test_runs": test_runs(raw_dir), "tool_efficiency": (tools["tool_calls"] / tools["model_calls"] if tools["model_calls"] else None), "output_claims": claim, "exception_type": exception_type or None},
        "termination": {"claimed_success": claim["claimed_success"], "claim_count": claim["claim_count"], "timeout": timeout, "crash": bool(exception and not timeout and not api_error), "api_error": api_error, "compatibility_error": compatibility},
        "recovery": raw.get("recovery"),
        "status": "complete" if raw_dir and raw.get("verifier_result") else ("failed" if raw_dir else "missing"),
        "raw_trial_dir": str(raw_dir) if raw_dir else None,
    }


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_harness: dict[str, Any] = {}
    for harness in HARNESS_ORDER:
        rows = [row for row in records if row["harness"] == harness]
        solved = sum(row["result"]["resolved"] for row in rows)
        costs = [row["cost_usd"] for row in rows if isinstance(row["cost_usd"], (int, float))]
        times = [row["timing"]["agent_ms"] for row in rows if isinstance(row["timing"].get("agent_ms"), (int, float))]
        regressions = sum(row["result"]["verifier_suite_gap"] == "regression_p2p_failure" for row in rows)
        by_harness[harness] = {
            "runs": len(rows), "resolved": solved, "resolved_rate": solved / len(rows) if rows else 0,
            "total_cost_usd": round(sum(costs), 8), "cost_per_resolved_usd": round(sum(costs) / solved, 8) if solved else None,
            "total_tokens": sum(row["tokens"].get("total") or 0 for row in rows),
            "median_agent_ms": int(statistics.median(times)) if times else None, "regressions": regressions,
            "false_completions": sum(row["termination"]["claimed_success"] and not row["result"]["resolved"] for row in rows),
            "timeouts": sum(row["termination"]["timeout"] for row in rows), "crashes": sum(row["termination"]["crash"] for row in rows),
            "compatibility_errors": sum(row["termination"]["compatibility_error"] for row in rows),
            "model_requests": sum(row["model_requests"] for row in rows), "tool_calls": sum(row["tools"]["total"] for row in rows),
            "failed_tool_calls": sum(row["tools"]["failed"] for row in rows), "test_runs": sum(row["observations"]["test_runs"] for row in rows),
            "provider_reconciled_trials": sum(row["provider_accounting"]["complete"] for row in rows),
        }
    return {"benchmark": "mercury-harness-v2", "model": MODEL, "tasks": len(set(row["task"] for row in records)), "trials": len(records), "completed_trials": sum(row["status"] == "complete" for row in records), "environment": "E2B; fresh single-container sandbox per trial", "concurrency": 2, "oracle_gate": "all selected tasks must pass the FeatBench reference solution before agent trials", "harnesses": by_harness, "records": records}


def fmt_ms(value: Any) -> str:
    return "—" if not isinstance(value, (int, float)) else f"{int(value)//60000}:{(int(value)//1000)%60:02d}"


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Mercury Harness Benchmark V2", "", f"Model: `{MODEL}`  ", "Environment: E2B, one fresh single-container sandbox per trial  ", f"Trials: {report['completed_trials']}/{report['trials']} completed", "", "Difficulty strata are pre-run study labels based on static FeatBench test and reference-patch surface; they are not official FeatBench difficulty labels.", "", "## Aggregate", "", "| Harness | Solved | Cost | Cost/solved | Tokens | Median agent time | Regressions | False completions |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for harness in HARNESS_ORDER:
        row = report["harnesses"][harness]
        cost = f"${row['total_cost_usd']:.6f}"
        per = f"${row['cost_per_resolved_usd']:.6f}" if row["cost_per_resolved_usd"] is not None else "—"
        lines.append(f"| {HARNESS_LABELS[harness]} | {row['resolved']}/{row['runs']} | {cost} | {per} | {row['total_tokens']:,} | {fmt_ms(row['median_agent_ms'])} | {row['regressions']} | {row['false_completions']} |")
    lines += ["", "## Task × harness results", "", "| # | Task | Stratum | Harness | Resolved | F2P | P2P | Agent time | Cost |", "|---:|---|---|---|---|---:|---:|---:|---:|"]
    for row in sorted(report["records"], key=lambda item: item.get("sequence", 0)):
        result = row["result"]
        f2p = f"{result['f2p_passed']}/{result['f2p_total']}" if result["f2p_passed"] is not None else "—"
        p2p = f"{result['p2p_passed']}/{result['p2p_total']}" if result["p2p_passed"] is not None else "—"
        cost = f"${row['cost_usd']:.6f}" if isinstance(row["cost_usd"], (int, float)) else "—"
        lines.append(f"| {(row.get('sequence') or 0)+1} | `{row['task']}` | {row['difficulty']} | {row['harness_label']} | {'PASS' if result['resolved'] else 'FAIL'} | {f2p} | {p2p} | {fmt_ms(row['timing'].get('agent_ms'))} | {cost} |")
    lines += ["", "## Added V2 measurements", "", "The canonical records add first model/tool latency, active-time share, context growth, tool efficiency, test-run counts, verifier-suite gap, output claims, artifact bytes, and provider-ledger completeness. Native transcripts and Harbor ATIF trajectories remain in each canonical trial directory.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("agents", "oracle"), default="agents")
    args = parser.parse_args()
    task_order = tasks()
    plan = read_json(RESULT_ROOT / "launcher" / f"{args.mode}-run-plan.json", []) or []
    if not isinstance(plan, list):
        plan = []
    if args.mode == "oracle":
        plan = [{"sequence": index, "task": task, "harness": "oracle"} for index, task in enumerate(task_order)]
    selected = select_latest(task_order)
    records = []
    for item in plan:
        task, harness = str(item["task"]), str(item["harness"])
        if harness == "oracle":
            continue
        raw_dir, raw = selected.get((task, harness), (None, None))
        record = canonical_record(task, harness, raw_dir, raw, item)
        output = CANONICAL_ROOT / task / harness
        copy_artifacts(raw_dir, output, task, harness)
        write_json(output / "result.json", record)
        write_json(output / "metadata.json", {"task": task, "harness": harness, "sequence": item.get("sequence"), "model": MODEL, "raw_trial_dir": str(raw_dir) if raw_dir else None})
        records.append(record)
    report = aggregate(records)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(REPORT_ROOT / "mercury-v2.json", report)
    (REPORT_ROOT / "mercury-v2.md").write_text(render_markdown(report))
    print(json.dumps({"records": len(records), "completed": report["completed_trials"], "report": str(REPORT_ROOT / "mercury-v2.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
