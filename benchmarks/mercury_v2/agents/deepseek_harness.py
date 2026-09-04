from __future__ import annotations

import json
import os
import re
import shlex
from pathlib import Path
from typing import Any, override

from harbor.agents.capabilities import AgentCapabilities
from harbor.agents.installed.base import BaseInstalledAgent, with_prompt_template
from harbor.agents.model_connection import ModelConnectionSpec
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.agents.installed.node_install import nvm_node_install_snippet

from benchmarks.mercury_v1.agents.common import (
    normalized_tool,
    number,
    read_json_lines,
    set_context,
)


_MODEL = os.environ.get("HARNESS_BENCHMARK_MODEL_ID", "z-ai/glm-5.3-flash")
_DSH_VERSION = "0.1.2-rc.1"


class DeepSeekHarness(BaseInstalledAgent):
    """Official DeepSeek Harness headless dsh adapter for one Harbor trial."""

    capabilities = AgentCapabilities()
    MODEL_CONNECTION = ModelConnectionSpec(passthrough=True)

    @staticmethod
    @override
    def name() -> str:
        return "deepseek-harness"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("version", _DSH_VERSION)
        super().__init__(*args, **kwargs)

    @override
    def get_version_command(self) -> str | None:
        return "dsh --version || dsh -V"

    @override
    def parse_version(self, stdout: str) -> str:
        match = re.search(r"\b\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?\b", stdout)
        return match.group(0) if match else stdout.strip().splitlines()[-1].strip()

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        await self.ensure_system_dependencies(
            environment,
            ("bash", "coreutils", "ca_certificates", "curl", "git", "nodejs", "npm"),
        )
        await self.exec_as_agent(
            environment,
            command=(
                "set -euo pipefail; "
                f"{nvm_node_install_snippet()} && "
                f"npm install -g --ignore-scripts --no-audit --no-fund "
                f"@deepseek-ai/dsh@{shlex.quote(_DSH_VERSION)}; "
                "dsh --version || dsh -V"
            ),
        )

    def _patch_text(self) -> str:
        return f"""# V2 benchmark overlay: route the official dsh headless profile through OpenRouter.
- id: llm-deepseek
  disabled: true

- id: llm-pi-ai
  config:
    providers:
      openrouter:
        apiKeyEnv: OPENROUTER_API_KEY
        api: openai-completions
        baseURL: https://openrouter.ai/api/v1
        models:
          - id: {_MODEL}
            contextWindow: 1310720
            maxTokens: 32768

- id: agent-default-model
  config:
    provider: openrouter
    model: {_MODEL}

- id: session-persistence-jsonl
  config:
    root: /logs/agent/deepseek-harness/sessions
    compression: none
"""

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
            raise ValueError("DeepSeek Harness requires OPENROUTER_API_KEY for this benchmark.")

        local_patch = self.logs_dir / "deepseek-harness" / "cordis.patch.yml"
        local_patch.parent.mkdir(parents=True, exist_ok=True)
        local_patch.write_text(self._patch_text())
        remote_patch = "/tmp/dsh-benchmark.patch.yml"
        await environment.upload_file(local_patch, remote_patch)

        env = dict(access.env)
        env.update(
            {
                "OPENROUTER_API_KEY": access.api_key,
                "DSH_HOME": "/tmp/dsh-home",
                "DSH_TOOLS_MODE": "native",
            }
        )
        output_dir = "/logs/agent/deepseek-harness"
        prompt = shlex.quote(instruction)
        command = (
            "set +e; "
            'export NVM_DIR="$HOME/.nvm"; '
            '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" || true; '
            f"mkdir -p {output_dir} /tmp/dsh-home; "
            "cd /testbed; "
            f"dsh --profile headless --patch {remote_patch} {prompt} "
            f">{output_dir}/final.txt 2>{output_dir}/stderr.log; "
            "rc=$?; "
            f"find /tmp/dsh-home -type f -maxdepth 6 -print 2>/dev/null | "
            f"while read -r file; do cp \"$file\" {output_dir}/ 2>/dev/null || true; done; "
            f"git -C /testbed diff --binary > {output_dir}/patch.diff 2>/dev/null || true; "
            "exit $rc"
        )
        await self.exec_as_agent(environment, command=command, env=env)

    @staticmethod
    def _session_rows(logs_dir: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        sessions_dir = logs_dir / "deepseek-harness" / "sessions"
        if sessions_dir.exists():
            for path in sorted(sessions_dir.rglob("*.jsonl")):
                rows.extend(read_json_lines(path))
        return rows

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        rows = self._session_rows(self.logs_dir)
        output_dir = self.logs_dir / "deepseek-harness"
        if rows:
            (output_dir / "trajectory.jsonl").write_text(
                "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n"
            )

        input_tokens = output_tokens = cache_tokens = reasoning_tokens = 0
        cost_usd = 0.0
        model_calls = tool_calls = failed_tool_calls = 0
        normalized: dict[str, int] = {}
        for row in rows:
            usage = row.get("usage")
            if not isinstance(usage, dict):
                data = row.get("data")
                usage = data.get("usage") if isinstance(data, dict) else None
            if isinstance(usage, dict):
                model_calls += 1
                input_tokens += int(number(usage.get("inputTokens", usage.get("input"))))
                output_tokens += int(number(usage.get("outputTokens", usage.get("output"))))
                cache_tokens += int(number(usage.get("cacheRead", usage.get("cached"))))
                reasoning_tokens += int(number(usage.get("reasoningTokens", usage.get("reasoning"))))
                cost_usd += number(usage.get("costUsd", usage.get("cost")))

            row_type = str(row.get("type") or row.get("kind") or row.get("event") or "").lower()
            # dsh emits both tool/call events and tool-call-chunks. Count the
            # completed call event, not the streaming chunks for that call.
            if row_type == "tool/call":
                tool_calls += 1
                data = row.get("data") if isinstance(row.get("data"), dict) else {}
                name = str(row.get("tool") or row.get("name") or data.get("tool") or data.get("name") or "tool")
                category = normalized_tool(name, row.get("input") or row.get("arguments") or data.get("arguments"))
                normalized[category] = normalized.get(category, 0) + 1
            if row_type == "tool/result":
                data = row.get("data") if isinstance(row.get("data"), dict) else {}
                failed_tool_calls += int(bool(row.get("error") or data.get("isError") or data.get("error")))

        stderr = output_dir / "stderr.log"
        if not rows and not stderr.exists():
            return
        set_context(
            context,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_tokens=cache_tokens,
            cost_usd=cost_usd,
            metadata={
                "model_calls": model_calls,
                "tool_calls": tool_calls,
                "failed_tool_calls": failed_tool_calls,
                "normalized_tools": normalized,
                "reasoning_tokens": reasoning_tokens,
                "native_trajectory": "deepseek-harness/trajectory.jsonl",
                "native_event_count": len(rows),
                "official_harness": "deepseek-ai/deepseek-harness",
                "official_harness_version": _DSH_VERSION,
            },
        )
