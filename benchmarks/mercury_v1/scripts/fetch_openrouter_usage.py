#!/usr/bin/env python3
"""Fetch provider-side OpenRouter generation accounting for Mercury V1."""

from __future__ import annotations

import argparse
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[3]
RESULT_ROOT = ROOT / "benchmarks" / "mercury_v1" / "results" / "mercury-v1"
TRIALS_ROOT = RESULT_ROOT / "trials"
OUTPUT = RESULT_ROOT / "openrouter-generation-usage.json"
GENERATION_RE = re.compile(r"\bgen-[A-Za-z0-9_-]+\b")
TEXT_SUFFIXES = {".json", ".jsonl", ".log", ".txt"}
PROVIDER_FIELDS = (
    "id",
    "model",
    "provider_name",
    "total_cost",
    "tokens_prompt",
    "tokens_completion",
    "native_tokens_prompt",
    "native_tokens_completion",
    "native_tokens_reasoning",
    "generation_time",
    "created_at",
)


def read_generation_ids(trial_dir: Path) -> list[str]:
    found: set[str] = set()
    agent_dir = trial_dir / "agent"
    if not agent_dir.exists():
        return []
    for path in agent_dir.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            found.update(GENERATION_RE.findall(path.read_text(errors="replace")))
        except OSError:
            continue
    return sorted(found)


def trial_id_map() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for result_path in sorted(TRIALS_ROOT.rglob("result.json")):
        trial_dir = result_path.parent
        ids = read_generation_ids(trial_dir)
        if ids:
            mapping[str(trial_dir.relative_to(RESULT_ROOT))] = ids
    return mapping


def fetch_generation(generation_id: str) -> tuple[str, dict[str, Any]]:
    request = Request(
        f"https://openrouter.ai/api/v1/generation?id={generation_id}",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            return generation_id, {"status": "invalid_response"}
        return generation_id, {
            "status": "ok",
            **{field: data.get(field) for field in PROVIDER_FIELDS if field in data},
        }
    except HTTPError as error:
        return generation_id, {"status": "http_error", "http_status": error.code}
    except (OSError, URLError, TimeoutError, json.JSONDecodeError, KeyError) as error:
        return generation_id, {"status": "error", "error_type": type(error).__name__}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY is required")

    mapping = trial_id_map()
    ids = sorted({generation_id for values in mapping.values() for generation_id in values})
    generations: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(fetch_generation, generation_id): generation_id for generation_id in ids}
        for future in as_completed(futures):
            generation_id, result = future.result()
            generations[generation_id] = result

    summary: dict[str, Any] = {"ids": len(ids)}
    for status in sorted({str(item.get("status")) for item in generations.values()}):
        summary[status] = sum(1 for item in generations.values() if item.get("status") == status)
    output = {
        "schema_version": "openrouter-generation-usage-v1",
        "model": "inception/mercury-2.5-preview",
        "endpoint": "https://openrouter.ai/api/v1/generation",
        "summary": summary,
        "trial_ids": mapping,
        "generations": dict(sorted(generations.items())),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
