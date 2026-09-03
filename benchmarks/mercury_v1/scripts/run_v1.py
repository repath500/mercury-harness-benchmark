#!/usr/bin/env python3
"""Run Mercury V1 as one Harbor trial process per harness/task pair."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TASK_ROOT = ROOT / "benchmarks" / "mercury_v1" / "tasks" / "featbench"
TASK_LIST = ROOT / "benchmarks" / "mercury_v1" / "tasks" / "mercury-v1.txt"
RESULT_ROOT = ROOT / "benchmarks" / "mercury_v1" / "results" / "mercury-v1"
TRIALS_DIR = RESULT_ROOT / "trials"
LAUNCH_DIR = RESULT_ROOT / "launcher"
HARBOR_PROJECT = Path(
    os.environ.get("HARBOR_SOURCE_DIR", "/tmp/harbor-source")
)
MODEL = "inception/mercury-2.5-preview"
OPENROUTER_MODEL = f"openrouter/{MODEL}"
HARNESS_ORDER = ("critique-code", "claude-code", "oh-my-pi", "opencode")
AGENT_SPECS = {
    "critique-code": "benchmarks.mercury_v1.agents.critique_code:CritiqueCode",
    "claude-code": "claude-code",
    "oh-my-pi": "benchmarks.mercury_v1.agents.oh_my_pi:OhMyPi",
    "opencode": "opencode",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_tasks() -> list[str]:
    tasks = [line.strip() for line in TASK_LIST.read_text().splitlines()]
    tasks = [line for line in tasks if line and not line.startswith("#")]
    if len(tasks) != 10:
        raise RuntimeError(f"Expected exactly 10 frozen tasks, found {len(tasks)}")
    missing = [task for task in tasks if not (TASK_ROOT / task).is_dir()]
    if missing:
        raise RuntimeError(f"Missing generated FeatBench task directories: {missing}")
    return tasks


def build_plan(tasks: list[str]) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    sequence = 0
    for task_index, task in enumerate(tasks):
        for offset in range(len(HARNESS_ORDER)):
            harness = HARNESS_ORDER[(task_index + offset) % len(HARNESS_ORDER)]
            plan.append(
                {
                    "sequence": sequence,
                    "task_index": task_index,
                    "task": task,
                    "harness": harness,
                    "model": MODEL,
                    "agent_spec": AGENT_SPECS[harness],
                    "trial_name": f"{task}__{harness}__v1",
                }
            )
            sequence += 1
    return plan


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def harbor_command(item: dict[str, Any]) -> list[str]:
    model = MODEL if item["harness"] == "claude-code" else OPENROUTER_MODEL
    return [
        "uv",
        "run",
        "--no-dev",
        "--extra",
        "e2b",
        "--project",
        str(HARBOR_PROJECT),
        "harbor",
        "trial",
        "start",
        "--path",
        str(TASK_ROOT / item["task"]),
        "--agent",
        item["agent_spec"],
        "--env",
        "e2b",
        "--model",
        model,
        "--trial-name",
        item["trial_name"],
        "--trials-dir",
        str(TRIALS_DIR),
        "--agent-timeout",
        "3600",
        "--agent-setup-timeout",
        "1800",
        "--delete",
    ]


async def run_item(item: dict[str, Any], state: dict[str, Any], lock: asyncio.Lock) -> None:
    sequence = item["sequence"]
    log_path = LAUNCH_DIR / f"{sequence:03d}__{item['task']}__{item['harness']}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    child_env = os.environ.copy()
    # Claude Code's native adapter uses Anthropic naming. OpenRouter's
    # Anthropic-compatible endpoint keeps the benchmark model unchanged.
    if item["harness"] == "claude-code":
        key = child_env.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is required")
        child_env["ANTHROPIC_API_KEY"] = key
        child_env["ANTHROPIC_BASE_URL"] = "https://openrouter.ai/api"
    child_env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(ROOT), child_env.get("PYTHONPATH", "")])
    )

    started = utc_now()
    print(
        f"START {sequence + 1:02d}/40 {item['task']} {item['harness']}",
        flush=True,
    )
    with log_path.open("w") as log_file:
        log_file.write(f"started_at={started}\n")
        log_file.write("command=" + " ".join(harbor_command(item)) + "\n")
        log_file.flush()
        process = await asyncio.create_subprocess_exec(
            *harbor_command(item),
            cwd=ROOT,
            env=child_env,
            stdout=log_file,
            stderr=asyncio.subprocess.STDOUT,
        )
        return_code = await process.wait()
        finished = utc_now()

    async with lock:
        state[str(sequence)] = {
            **item,
            "status": "finished" if return_code == 0 else "failed",
            "return_code": return_code,
            "started_at": started,
            "finished_at": finished,
            "launcher_log": str(log_path),
        }
        write_json(RESULT_ROOT / "launcher" / "state.json", state)
    print(
        f"DONE  {sequence + 1:02d}/40 {item['task']} {item['harness']} rc={return_code}",
        flush=True,
    )


async def run_plan(plan: list[dict[str, Any]], concurrency: int) -> None:
    state: dict[str, Any] = {}
    state_path = RESULT_ROOT / "launcher" / "state.json"
    if state_path.exists():
        try:
            loaded = json.loads(state_path.read_text())
            if isinstance(loaded, dict):
                state = loaded
        except json.JSONDecodeError:
            pass

    lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(concurrency)

    async def guarded(item: dict[str, Any]) -> None:
        async with semaphore:
            await run_item(item, state, lock)

    await asyncio.gather(*(guarded(item) for item in plan))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-seq", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()
    if args.start_seq < 0 or args.start_seq >= 40:
        parser.error("--start-seq must be between 0 and 39")
    if args.concurrency < 1:
        parser.error("--concurrency must be positive")

    tasks = read_tasks()
    plan = build_plan(tasks)
    write_json(RESULT_ROOT / "launcher" / "run-plan.json", plan)
    selected = plan[args.start_seq :]
    if args.limit is not None:
        selected = selected[: args.limit]
    if not selected:
        raise RuntimeError("No trials selected")
    print(
        f"Launching {len(selected)} trial(s), concurrency={args.concurrency}; "
        f"fresh E2B sandbox per trial; sequence {selected[0]['sequence']}..{selected[-1]['sequence']}",
        flush=True,
    )
    asyncio.run(run_plan(selected, args.concurrency))
    return 0


if __name__ == "__main__":
    sys.exit(main())

