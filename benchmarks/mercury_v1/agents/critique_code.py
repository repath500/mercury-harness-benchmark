from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any, override

from harbor.agents.capabilities import AgentCapabilities
from harbor.agents.installed.base import BaseInstalledAgent, with_prompt_template
from harbor.agents.installed.node_install import nvm_node_install_snippet
from harbor.agents.model_connection import ModelConnectionSpec
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from .common import number, read_json_lines, set_context


_MODEL_ID = "inception/mercury-2.5-preview"
_RUNTIME_DIR = Path(__file__).resolve().parents[3] / "e2b-templates" / "critique-pi-v1"


class CritiqueCode(BaseInstalledAgent):
    """Harbor adapter for CritiqueCode's Pi-based author/repair runtime."""

    capabilities = AgentCapabilities()
    MODEL_CONNECTION = ModelConnectionSpec(passthrough=True)

    @staticmethod
    @override
    def name() -> str:
        return "critique-code"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("version", "0.1.13+bench")
        super().__init__(*args, **kwargs)

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        await self.ensure_system_dependencies(
            environment,
            (
                "bash",
                "ca_certificates",
                "git",
                "build_tools",
                "nodejs",
                "npm",
            ),
        )
        if not _RUNTIME_DIR.is_dir():
            raise RuntimeError(f"CritiqueCode runtime directory is missing: {_RUNTIME_DIR}")

        await self.exec_as_root(
            environment,
            command="mkdir -p /opt/critique/verify /opt/critique/pi/agent /workspace",
        )
        for filename in (
            "package.json",
            "runner.mjs",
            "critique-code-extension.mjs",
            "critique-code-policy.mjs",
        ):
            await environment.upload_file(
                _RUNTIME_DIR / filename,
                f"/opt/critique/verify/{filename}",
            )
        await self.exec_as_root(
            environment,
            command=(
                "set -euo pipefail; "
                f"{nvm_node_install_snippet()} && "
                "cd /opt/critique/verify && "
                "npm install --omit=dev --ignore-scripts --no-audit --no-fund"
            ),
        )

    @override
    @with_prompt_template
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        access = self.model_connection
        if not access.api_key:
            raise ValueError("CritiqueCode requires OPENROUTER_API_KEY for this benchmark.")

        base_sha_result = await environment.exec(
            "git rev-parse HEAD",
            cwd="/testbed",
        )
        base_sha = (base_sha_result.stdout or "").strip() or "unknown"
        task = {
            "repository": {"fullName": "featbench", "baseSha": base_sha},
            "request": instruction,
            "model": {
                "id": _MODEL_ID,
                "pricing": {
                    "inputUsdPerMillion": 0.04,
                    "outputUsdPerMillion": 0.15,
                },
            },
            "plan": "standard",
            "budget": {
                "agentMs": 3_600_000,
                "wallClockMs": 3_660_000,
                "maxToolCalls": 1_000,
                "maxWorkUnits": 10_000,
                "verificationMs": 120_000,
            },
        }
        task_path = Path("/tmp/critique-bench-task.json")
        local_task_path = self.logs_dir / "critique-code" / "task.json"
        local_task_path.parent.mkdir(parents=True, exist_ok=True)
        local_task_path.write_text(json.dumps(task, indent=2))
        await environment.upload_file(local_task_path, task_path.as_posix())

        env = dict(access.env)
        env.update(
            {
                "VERIFY_MODEL_TOKEN": access.api_key,
                "VERIFY_MODEL_ID": _MODEL_ID,
                "VERIFY_MODEL_ENDPOINT": "https://openrouter.ai/api/v1",
                "VERIFY_RUN_ID": self.session_id or "mercury-v1",
            }
        )
        command = (
            "set +e; "
            "export NVM_DIR=\"$HOME/.nvm\"; "
            "[ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" || true; "
            "ln -sfn /testbed /workspace/repo; "
            "mkdir -p /logs/agent/critique-code; "
            "node /opt/critique/verify/runner.mjs "
            f"--task {shlex.quote(task_path.as_posix())} "
            "2>&1 | tee /logs/agent/critique-code/agent.log; "
            "rc=${PIPESTATUS[0]}; "
            "cp /tmp/critique-verify-events.jsonl /logs/agent/critique-code/trajectory.jsonl 2>/dev/null || true; "
            "cp /tmp/critique-verify-pi-result.json /logs/agent/critique-code/runtime-result.json 2>/dev/null || true; "
            "git -C /testbed diff --binary > /logs/agent/critique-code/patch.diff 2>/dev/null || true; "
            "exit $rc"
        )
        # Do not pass /workspace/repo as Harbor's command cwd: E2B validates
        # that path before the shell can create the symlink above. The runtime
        # itself uses /workspace/repo after the first command in the script.
        await self.exec_as_agent(environment, command=command, env=env)

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        result_path = self.logs_dir / "critique-code" / "runtime-result.json"
        events_path = self.logs_dir / "critique-code" / "trajectory.jsonl"
        try:
            result = json.loads(result_path.read_text()) if result_path.exists() else {}
        except (OSError, json.JSONDecodeError):
            result = {}
        events = read_json_lines(events_path)
        usage = result.get("usage") if isinstance(result, dict) else {}
        usage = usage if isinstance(usage, dict) else {}
        input_tokens = int(number(usage.get("inputTokens")))
        output_tokens = int(number(usage.get("outputTokens")))
        reasoning_tokens = int(number(usage.get("reasoningTokens")))
        cost_usd = number(usage.get("costUsd"))
        model_calls = sum(1 for row in events if row.get("kind") == "usage")
        tool_calls = int(number(result.get("toolCalls"))) if isinstance(result, dict) else 0
        if not model_calls:
            model_calls = sum(1 for row in events if row.get("kind") == "agent.status")
        normalized: dict[str, int] = {}
        failed_tool_calls = 0
        for row in events:
            if row.get("kind") not in {"tool.started", "tool.failed", "tool.completed"}:
                continue
            activity = row.get("activity") or {}
            name = str(activity.get("tool") or "tool")
            category = self._normalized_tool(name, activity.get("inputPreview"))
            if row.get("kind") == "tool.started":
                normalized[category] = normalized.get(category, 0) + 1
            if row.get("kind") == "tool.failed":
                failed_tool_calls += 1

        if not result and not events:
            return
        set_context(
            context,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_tokens=0,
            cost_usd=cost_usd,
            metadata={
                "model_calls": model_calls,
                "tool_calls": tool_calls,
                "failed_tool_calls": failed_tool_calls,
                "normalized_tools": normalized,
                "reasoning_tokens": reasoning_tokens,
                "checks": result.get("checks", 0) if isinstance(result, dict) else 0,
                "claims": result.get("claims", 0) if isinstance(result, dict) else 0,
                "runtime_status": result.get("status") if isinstance(result, dict) else None,
                "native_trajectory": "critique-code/trajectory.jsonl",
                "native_event_count": len(events),
            },
        )

    @staticmethod
    def _normalized_tool(name: str, args: Any = None) -> str:
        value = f"{name} {args or ''}".lower()
        if any(word in value for word in ("read", "ls", "file")):
            return "READ"
        if any(word in value for word in ("grep", "find", "search")):
            return "SEARCH"
        if any(word in value for word in ("edit", "write", "patch")):
            return "EDIT"
        if any(word in value for word in ("lsp", "diagnostic")):
            return "LSP"
        if any(word in value for word in ("subagent", "delegate")):
            return "SUBAGENT"
        if any(word in value for word in ("check", "test", "pytest")):
            return "TEST"
        if "bash" in value or "shell" in value:
            return "SHELL"
        return "OTHER"
