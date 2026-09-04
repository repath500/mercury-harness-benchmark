#!/usr/bin/env python3
"""Run Mercury V2 as one Harbor trial process per harness/task pair."""

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
TASK_ROOT = ROOT / "benchmarks" / "mercury_v2" / "tasks" / "featbench"
TASK_LIST = ROOT / "benchmarks" / "mercury_v2" / "tasks" / "mercury-v2.txt"
RESULT_ROOT = ROOT / "benchmarks" / "mercury_v2" / "results" / "mercury-v2"
TRIALS_DIR = RESULT_ROOT / "trials"
LAUNCH_DIR = RESULT_ROOT / "launcher"
HARBOR_PROJECT = Path(os.environ.get("HARBOR_SOURCE_DIR", "/tmp/critique-harbor-src-20260903"))
MODEL_ID = "z-ai/glm-5.3-flash"
OPENROUTER_MODEL = f"openrouter/{MODEL_ID}"
INPUT_USD_PER_MILLION = "0.075"
OUTPUT_USD_PER_MILLION = "0.25"
HARNESS_ORDER = (
    "pi",
    "oh-my-pi",
    "claude-code",
    "codex",
    "deepseek-harness",
    "critique-code",
    "opencode",
)
AGENT_SPECS = {
    "pi": "pi",
    "oh-my-pi": "benchmarks.mercury_v1.agents.oh_my_pi:OhMyPi",
    "claude-code": "claude-code",
    "codex": "codex",
    "deepseek-harness": "benchmarks.mercury_v2.agents.deepseek_harness:DeepSeekHarness",
    "critique-code": "benchmarks.mercury_v1.agents.critique_code:CritiqueCode",
    "opencode": "opencode",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_tasks() -> list[str]:
    tasks = [line.strip() for line in TASK_LIST.read_text().splitlines()]
    tasks = [line for line in tasks if line and not line.startswith("#")]
    if len(tasks) != 20:
        raise RuntimeError(f"Expected exactly 20 frozen tasks, found {len(tasks)}")
    missing = [task for task in tasks if not (TASK_ROOT / task).is_dir()]
    if missing:
        raise RuntimeError(f"Missing generated FeatBench task directories: {missing}")
    return tasks


def build_plan(tasks: list[str], mode: str) -> list[dict[str, Any]]:
    harnesses = ("oracle",) if mode == "oracle" else HARNESS_ORDER
    plan: list[dict[str, Any]] = []
    sequence = 0
    for task_index, task in enumerate(tasks):
        for offset in range(len(harnesses)):
            if mode == "oracle":
                harness = "oracle"
            else:
                harness = HARNESS_ORDER[(task_index + offset) % len(HARNESS_ORDER)]
            plan.append(
                {
                    "sequence": sequence,
                    "task_index": task_index,
                    "task": task,
                    "harness": harness,
                    "model": MODEL_ID,
                    "agent_spec": "oracle" if mode == "oracle" else AGENT_SPECS[harness],
                    "trial_name": f"{task}__{harness}__v2-{mode}",
                    "mode": mode,
                }
            )
            sequence += 1
    return plan


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def preserve_existing_trial_dir(trial_name: str) -> Path | None:
    """Move an old attempt aside before a retry so raw trials stay immutable.

    Harbor writes into a deterministic trial directory. Reusing that directory
    after an interrupted run can create a hybrid of two attempts, which is much
    worse than retaining an explicit incomplete attempt. Retries therefore move
    the previous directory to a timestamped ``__attempt-rerun-*`` sibling.
    """
    target = TRIALS_DIR / trial_name
    if not target.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    preserved = TRIALS_DIR / f"{trial_name}__attempt-rerun-{stamp}-{os.getpid()}"
    counter = 1
    while preserved.exists():
        preserved = TRIALS_DIR / f"{trial_name}__attempt-rerun-{stamp}-{os.getpid()}-{counter}"
        counter += 1
    target.rename(preserved)
    return preserved


async def wait_for_harbor_process(process: asyncio.subprocess.Process) -> int:
    """Wait without getting stuck if an E2B-side failure removes the child.

    On macOS, a failed ``uv run``/Harbor child can disappear before asyncio's
    child watcher observes the exit.  Polling the PID lets the launcher record
    the attempt and release its concurrency slot instead of waiting forever.
    """
    wait_task = asyncio.create_task(process.wait())
    try:
        while not wait_task.done():
            await asyncio.sleep(2)
            if wait_task.done():
                break
            try:
                os.kill(process.pid, 0)
            except ProcessLookupError:
                wait_task.cancel()
                return 125
            except PermissionError:
                # The child is still present but cannot be probed; keep waiting.
                pass
        try:
            return await wait_task
        except ChildProcessError:
            # macOS can report that a wrapper already disappeared before the
            # child watcher reaped it. Treat this as an infrastructure failure
            # and keep the matrix moving.
            return 125
    finally:
        if not wait_task.done():
            wait_task.cancel()


def harbor_command(item: dict[str, Any]) -> list[str]:
    command = [
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
        "--trial-name",
        item["trial_name"],
        "--trials-dir",
        str(TRIALS_DIR),
        "--agent-timeout",
        "3600",
        "--agent-setup-timeout",
        "1800",
        "--verifier-timeout",
        "1800",
        "--delete",
    ]
    if item["mode"] != "oracle":
        model = MODEL_ID if item["harness"] == "claude-code" else OPENROUTER_MODEL
        command.extend(["--model", model])
        if item["harness"] == "pi":
            command.extend(["--agent-kwarg", "model_api=openai-completions"])
    return command


def child_environment(item: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(ROOT), env.get("PYTHONPATH", "")])
    )
    if item["mode"] == "oracle":
        return env

    env["HARNESS_BENCHMARK_MODEL"] = OPENROUTER_MODEL
    env["HARNESS_BENCHMARK_MODEL_ID"] = MODEL_ID
    env["HARNESS_BENCHMARK_INPUT_USD_PER_MILLION"] = INPUT_USD_PER_MILLION
    env["HARNESS_BENCHMARK_OUTPUT_USD_PER_MILLION"] = OUTPUT_USD_PER_MILLION
    openrouter_key = env.get("OPENROUTER_API_KEY")
    openrouter_base_url = env.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    # Harbor's Pi adapter requires a configured base URL when model_api is
    # supplied. Set the default explicitly so openrouter/* uses its custom
    # provider config inside the sandbox.
    env["OPENROUTER_BASE_URL"] = openrouter_base_url
    if item["harness"] == "claude-code":
        if not openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for Claude Code")
        env["ANTHROPIC_API_KEY"] = openrouter_key
        env["ANTHROPIC_BASE_URL"] = "https://openrouter.ai/api"
    if item["harness"] == "codex":
        if not openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for Codex")
        env["OPENAI_API_KEY"] = openrouter_key
        env["OPENAI_BASE_URL"] = openrouter_base_url
    return env


async def run_item(
    item: dict[str, Any],
    state: dict[str, Any],
    lock: asyncio.Lock,
    force: bool,
    state_path: Path,
) -> None:
    sequence = item["sequence"]
    state_key = str(sequence)
    prior = state.get(state_key)
    if not force and isinstance(prior, dict) and prior.get("status") == "finished":
        print(f"SKIP  {sequence + 1:03d} already finished", flush=True)
        return

    log_path = LAUNCH_DIR / f"{item['mode']}__{sequence:03d}__{item['task']}__{item['harness']}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    print(
        f"START {sequence + 1:03d} {item['mode']} {item['task']} {item['harness']}",
        flush=True,
    )
    preserved = preserve_existing_trial_dir(item["trial_name"])
    if preserved:
        print(f"PRESERVE {preserved.name}", flush=True)
    command = harbor_command(item)
    child_env = child_environment(item)
    with log_path.open("w") as log_file:
        log_file.write(f"started_at={started}\n")
        log_file.write("command=" + " ".join(command) + "\n")
        log_file.flush()
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=ROOT,
            env=child_env,
            stdout=log_file,
            stderr=asyncio.subprocess.STDOUT,
        )
        return_code = await wait_for_harbor_process(process)
    finished = utc_now()

    async with lock:
        state[state_key] = {
            **item,
            "status": "finished" if return_code == 0 else "failed",
            "return_code": return_code,
            "started_at": started,
            "finished_at": finished,
            "launcher_log": str(log_path),
        }
        write_json(state_path, state)
    print(
        f"DONE  {sequence + 1:03d} {item['mode']} {item['task']} {item['harness']} rc={return_code}",
        flush=True,
    )


async def run_plan(
    plan: list[dict[str, Any]], mode: str, concurrency: int, force: bool,
    state_path: Path | None = None,
) -> None:
    state_path = state_path or (LAUNCH_DIR / f"{mode}-state.json")
    state: dict[str, Any] = {}
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
            await run_item(item, state, lock, force, state_path)

    await asyncio.gather(*(guarded(item) for item in plan))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("oracle", "agents"), default="agents")
    parser.add_argument("--start-seq", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--seq",
        action="append",
        type=int,
        default=None,
        help="Run only these zero-based plan sequences; may be repeated",
    )
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument(
        "--state-file",
        type=Path,
        default=None,
        help="Use an independent launcher state file (for disjoint parallel lanes)",
    )
    parser.add_argument("--force", action="store_true", help="rerun sequences recorded as finished")
    args = parser.parse_args()

    tasks = read_tasks()
    plan = build_plan(tasks, args.mode)
    total = len(plan)
    if args.start_seq < 0 or args.start_seq >= total:
        parser.error(f"--start-seq must be between 0 and {total - 1}")
    if args.concurrency < 1:
        parser.error("--concurrency must be positive")
    write_json(LAUNCH_DIR / f"{args.mode}-run-plan.json", plan)
    if args.seq:
        invalid = [value for value in args.seq if value < 0 or value >= total]
        if invalid:
            parser.error(f"--seq values must be between 0 and {total - 1}: {invalid}")
        requested = set(args.seq)
        selected = [item for item in plan if item["sequence"] in requested]
    else:
        selected = plan[args.start_seq :]
        if args.limit is not None:
            selected = selected[: args.limit]
    if not selected:
        raise RuntimeError("No trials selected")
    print(
        f"Launching {len(selected)} {args.mode} trial(s), concurrency={args.concurrency}; "
        f"fresh E2B sandbox per trial; sequence {selected[0]['sequence']}..{selected[-1]['sequence']}",
        flush=True,
    )
    asyncio.run(run_plan(selected, args.mode, args.concurrency, args.force, args.state_file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
