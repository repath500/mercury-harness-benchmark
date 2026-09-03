from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def number(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed >= 0 else 0.0


def read_json_lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def usage_values(usage: Any) -> tuple[float, float, float, float, float]:
    if not isinstance(usage, dict):
        return 0.0, 0.0, 0.0, 0.0, 0.0

    input_tokens = number(
        usage.get("input", usage.get("inputTokens", usage.get("promptTokens")))
    )
    output_tokens = number(
        usage.get("output", usage.get("outputTokens", usage.get("completionTokens")))
    )
    cache_read = number(
        usage.get("cacheRead", usage.get("cache_read", usage.get("cached")))
    )
    reasoning_tokens = number(
        usage.get("reasoning", usage.get("reasoningTokens", usage.get("reasoning_tokens")))
    )
    cost = usage.get("cost", 0.0)
    if isinstance(cost, dict):
        cost = cost.get("total", cost.get("totalUsd", 0.0))
    return input_tokens, output_tokens, cache_read, reasoning_tokens, number(cost)


def tool_name(row: dict[str, Any]) -> str:
    return str(
        row.get("toolName")
        or row.get("tool")
        or (row.get("part") or {}).get("tool")
        or (row.get("toolCall") or {}).get("name")
        or "tool"
    )


def normalized_tool(name: str, args: Any = None) -> str:
    value = f"{name} {args or ''}".lower()
    if re.search(r"\b(?:read|cat|head|tail|view|open|file)\b", value):
        return "READ"
    if re.search(r"\b(?:grep|rg|find|glob|search|ripgrep)\b", value):
        return "SEARCH"
    if re.search(r"\b(?:edit|write|patch|apply_patch|replace|insert)\b", value):
        return "EDIT"
    if re.search(r"\b(?:lsp|language.server|diagnostic|definition|references)\b", value):
        return "LSP"
    if re.search(r"\b(?:subagent|delegate|task|agent)\b", value):
        return "SUBAGENT"
    if re.search(r"\b(?:test|pytest|npm|pnpm|yarn|cargo|go.test|jest|vitest)\b", value):
        return "TEST"
    if re.search(r"\b(?:bash|shell|exec|run|command|terminal|sh)\b", value):
        return "SHELL"
    return "OTHER"


def set_context(
    context: Any,
    *,
    input_tokens: int,
    output_tokens: int,
    cache_tokens: int,
    cost_usd: float | None,
    metadata: dict[str, Any],
) -> None:
    context.n_input_tokens = input_tokens + cache_tokens
    context.n_output_tokens = output_tokens
    context.n_cache_tokens = cache_tokens
    context.cost_usd = cost_usd if cost_usd and cost_usd > 0 else None
    context.metadata = metadata


def parse_pi_jsonl(path: Path) -> dict[str, Any]:
    rows = read_json_lines(path)
    input_tokens = 0.0
    output_tokens = 0.0
    cache_tokens = 0.0
    reasoning_tokens = 0.0
    cost_usd = 0.0
    model_calls = 0
    tool_calls = 0
    failed_tool_calls = 0
    normalized: dict[str, int] = {}

    for row in rows:
        row_type = row.get("type")
        if row_type == "message_end" and (row.get("message") or {}).get("role") == "assistant":
            model_calls += 1
            values = usage_values((row.get("message") or {}).get("usage"))
            input_tokens += values[0]
            output_tokens += values[1]
            cache_tokens += values[2]
            reasoning_tokens += values[3]
            cost_usd += values[4]
        elif row_type == "tool_execution_start":
            tool_calls += 1
            category = normalized_tool(tool_name(row), row.get("args"))
            normalized[category] = normalized.get(category, 0) + 1
        elif row_type == "tool_execution_end":
            result = row.get("result")
            if row.get("isError") or row.get("error") or (
                isinstance(result, dict) and result.get("isError")
            ):
                failed_tool_calls += 1

    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "cache_tokens": int(cache_tokens),
        "reasoning_tokens": int(reasoning_tokens),
        "cost_usd": cost_usd,
        "model_calls": model_calls,
        "tool_calls": tool_calls,
        "failed_tool_calls": failed_tool_calls,
        "normalized_tools": normalized,
        "events": len(rows),
    }

