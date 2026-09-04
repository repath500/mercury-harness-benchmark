#!/usr/bin/env python3
"""Create a truthful Harbor result envelope for a trial stalled after the agent.

This is only for recovery of a run whose agent completed and whose logs/patch
were downloaded, but Harbor crashed before writing result.json. It never
invents a verifier result; ``harbor trial regrade`` supplies that result.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def iso_from_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def event_timestamp(value: object) -> tuple[int, str] | None:
    if isinstance(value, (int, float)):
        integer = int(value)
        return integer, iso_from_ms(integer)
    if isinstance(value, str):
        text = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        integer = int(parsed.timestamp() * 1000)
        return integer, parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return None


def atif_timestamps(trajectory: object) -> list[tuple[int, str]]:
    if not isinstance(trajectory, dict):
        return []
    result = []
    for step in trajectory.get("steps", []):
        if isinstance(step, dict):
            parsed = event_timestamp(step.get("timestamp"))
            if parsed:
                result.append(parsed)
    return result


def atif_agent_metrics(trajectory: object) -> dict[str, object] | None:
    """Extract the metrics Harbor's ATIF trajectory already recorded."""
    if not isinstance(trajectory, dict):
        return None
    agent = trajectory.get("agent") if isinstance(trajectory.get("agent"), dict) else {}
    final = trajectory.get("final_metrics") if isinstance(trajectory.get("final_metrics"), dict) else {}
    steps = [step for step in trajectory.get("steps", []) if isinstance(step, dict)]
    model_calls = sum(int(step.get("llm_call_count") or 0) for step in steps if step.get("source") == "agent")
    tool_calls = sum(len(step.get("tool_calls") or []) for step in steps)
    reasoning = 0
    for step in steps:
        metrics = step.get("metrics") if isinstance(step.get("metrics"), dict) else {}
        extra = metrics.get("extra") if isinstance(metrics.get("extra"), dict) else {}
        reasoning += int(extra.get("reasoning_tokens") or 0)
    return {
        "agent": agent,
        "input": int(final.get("total_prompt_tokens") or 0),
        "output": int(final.get("total_completion_tokens") or 0),
        "cached": int(final.get("total_cached_tokens") or 0),
        "cost": final.get("total_cost_usd"),
        "model_calls": model_calls,
        "tool_calls": tool_calls,
        "reasoning": reasoning,
    }


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: seed_regrade_source.py STALLED_DIR TEMPLATE_RESULT")
    stalled = Path(sys.argv[1])
    template = Path(sys.argv[2])
    source = json.loads(template.read_text())
    config = json.loads((stalled / "config.json").read_text())

    rows = []
    session_paths = sorted((stalled / "agent").rglob("*.jsonl"))
    for path in session_paths:
        for line in path.read_text(errors="replace").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(row)

    usage = {key: 0 for key in ("input", "output", "cacheRead", "cacheWrite", "reasoning")}
    assistant_messages = []
    for row in rows:
        message = row.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        value = message.get("usage")
        if not isinstance(value, dict):
            continue
        assistant_messages.append(row)
        for key in usage:
            usage[key] += int(value.get(key, 0) or 0)

    parsed_timestamps = [
        parsed
        for row in rows
        if (parsed := event_timestamp(row.get("timestamp") or row.get("at"))) is not None
    ]
    trajectory_path = stalled / "agent" / "trajectory.json"
    trajectory = None
    if trajectory_path.exists():
        try:
            trajectory = json.loads(trajectory_path.read_text())
        except json.JSONDecodeError:
            trajectory = None
    atif = atif_agent_metrics(trajectory)
    runtime_result_path = stalled / "agent" / "critique-code" / "runtime-result.json"
    runtime_result = None
    if runtime_result_path.exists():
        try:
            loaded = json.loads(runtime_result_path.read_text())
            runtime_result = loaded if isinstance(loaded, dict) else None
        except json.JSONDecodeError:
            runtime_result = None
    if atif:
        usage = {
            "input": int(atif["input"]),
            "output": int(atif["output"]),
            "cacheRead": int(atif["cached"]),
            "cacheWrite": 0,
            "reasoning": int(atif["reasoning"]),
        }
        timestamps = atif_timestamps(trajectory)
    elif runtime_result:
        runtime_usage = runtime_result.get("usage") if isinstance(runtime_result.get("usage"), dict) else {}
        usage = {
            "input": int(runtime_usage.get("inputTokens") or 0),
            "output": int(runtime_usage.get("outputTokens") or 0),
            "cacheRead": 0,
            "cacheWrite": 0,
            "reasoning": int(runtime_usage.get("reasoningTokens") or 0),
        }
        timestamps = parsed_timestamps
    else:
        timestamps = parsed_timestamps
    if not timestamps:
        raise SystemExit("no timestamped native trajectory events found")
    timestamp_values = [value[0] for value in timestamps]
    timestamp_text = [value[1] for value in timestamps]

    task_name = str(source["task_name"])
    trial_name = stalled.name.split("__attempt-", 1)[0]
    native_agent = (atif or {}).get("agent") if atif else {}
    native_agent = native_agent if isinstance(native_agent, dict) else {}
    agent_name = str(native_agent.get("name") or "pi")
    agent_version = str(native_agent.get("version") or "unknown")
    model_name = str(native_agent.get("model_name") or "z-ai/glm-5.3-flash")
    model_provider, _, model_id = model_name.partition("/")
    model_provider = model_provider if model_id else "openrouter"
    model_id = model_id or model_name
    if atif:
        agent_result = {
            "n_input_tokens": usage["input"],
            "n_cache_tokens": usage["cacheRead"],
            "n_output_tokens": usage["output"],
            "cost_usd": atif.get("cost"),
            "rollout_details": None,
            "metadata": {
                "model_calls": int(atif["model_calls"]),
                "tool_calls": int(atif["tool_calls"]),
                "runtime_status": "completed",
                "native_trajectory": "trajectory.json",
                "reasoning_tokens": usage["reasoning"],
            },
        }
    elif runtime_result:
        native_tool_calls = sum(row.get("kind") == "tool.started" for row in rows)
        native_failed_tools = sum(row.get("kind") == "tool.failed" for row in rows)
        native_model_calls = sum(row.get("kind") == "usage" for row in rows)
        agent_result = {
            "n_input_tokens": usage["input"],
            "n_cache_tokens": usage["cacheRead"],
            "n_output_tokens": usage["output"],
            "cost_usd": runtime_result.get("usage", {}).get("costUsd"),
            "rollout_details": None,
            "metadata": {
                "model_calls": native_model_calls,
                "tool_calls": native_tool_calls,
                "failed_tool_calls": native_failed_tools,
                "runtime_status": runtime_result.get("status", "completed"),
                "native_trajectory": "critique-code/trajectory.jsonl",
                "reasoning_tokens": usage["reasoning"],
                "native_tool_events": True,
            },
        }
    else:
        agent_result = {
            "n_input_tokens": usage["input"],
            "n_cache_tokens": usage["cacheRead"],
            "n_output_tokens": usage["output"],
            "cost_usd": None,
            "rollout_details": None,
            "metadata": {
                "model_calls": len(assistant_messages),
                "runtime_status": "completed",
                "native_trajectory": (
                    f"pi/sessions/{session_paths[0].name}" if session_paths else None
                ),
                "reasoning_tokens": usage["reasoning"],
            },
        }
    source.update(
        {
            "task_name": task_name,
            "trial_name": trial_name,
            "trial_uri": stalled.resolve().as_uri(),
            "config": config,
            "source": None,
            "agent_info": {
                "name": agent_name,
                "version": agent_version,
                "model_info": {
                    "name": model_id,
                    "provider": model_provider,
                },
            },
            "agent_result": agent_result,
            "verifier_result": None,
            "exception_info": None,
            "started_at": min(timestamp_text),
            "finished_at": max(timestamp_text),
            "agent_execution": {
                "started_at": min(timestamp_text),
                "finished_at": max(timestamp_text),
            },
            "verifier": None,
        }
    )
    (stalled / "result.json").write_text(json.dumps(source, indent=4) + "\n")
    print(
        json.dumps(
            {
                "result": str(stalled / "result.json"),
                "model_calls": len(assistant_messages),
                "input_tokens": usage["input"],
                "cache_tokens": usage["cacheRead"],
                "output_tokens": usage["output"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
