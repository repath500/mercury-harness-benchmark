from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any, override

from harbor.agents.capabilities import AgentCapabilities
from harbor.agents.installed.base import BaseInstalledAgent, with_prompt_template
from harbor.agents.model_connection import ModelConnectionSpec
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from .common import parse_pi_jsonl, set_context


_OMP_VERSION = "18.1.5"
_BUN_VERSION = "1.3.14"
_MODEL = "openrouter/inception/mercury-2.5-preview"


class OhMyPi(BaseInstalledAgent):
    """Headless Oh My Pi adapter for one isolated Harbor trial."""

    capabilities = AgentCapabilities()
    MODEL_CONNECTION = ModelConnectionSpec(passthrough=True)

    @staticmethod
    @override
    def name() -> str:
        return "oh-my-pi"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("version", _OMP_VERSION)
        super().__init__(*args, **kwargs)

    @override
    def get_version_command(self) -> str | None:
        return "command -v omp && omp --version"

    @override
    def parse_version(self, stdout: str) -> str:
        match = re.search(r"\b\d+\.\d+\.\d+\b", stdout)
        return match.group(0) if match else stdout.strip().splitlines()[-1].strip()

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        await self.ensure_system_dependencies(
            environment,
            (
                "curl",
                "bash",
                "coreutils",
                "ca_certificates",
                "git",
                "nodejs",
                "npm",
                "unzip",
            ),
        )
        version = self._version or _OMP_VERSION
        command = (
            "set -euo pipefail; "
            "export BUN_INSTALL=/opt/bun; "
            "if [ ! -x /opt/bun/bin/bun ]; then "
            f"mkdir -p /opt/bun; curl -fsSL https://bun.sh/install | bash -s -- bun-v{_BUN_VERSION}; "
            "fi; "
            "ln -sf /opt/bun/bin/bun /usr/local/bin/bun; "
            "npm install -g --ignore-scripts --legacy-peer-deps --no-audit --no-fund "
            f"@oh-my-pi/pi-coding-agent@{shlex.quote(version)}; "
            "omp --version"
        )
        await self.exec_as_root(environment, command=command)

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
            raise ValueError("Oh My Pi requires OPENROUTER_API_KEY for this benchmark.")

        env = dict(access.env)
        env.update(
            {
                "PI_CODING_AGENT_DIR": "/tmp/omp-agent",
                "XDG_CONFIG_HOME": "/tmp/omp-xdg/config",
                "XDG_DATA_HOME": "/tmp/omp-xdg/data",
                "XDG_STATE_HOME": "/tmp/omp-xdg/state",
                "OMP_NO_UPDATE_CHECK": "1",
            }
        )
        output_dir = "/logs/agent/oh-my-pi"
        prompt = shlex.quote(instruction)
        command = (
            "export PATH=/opt/bun/bin:/usr/local/bin:$PATH; "
            f"mkdir -p {output_dir}; "
            f"omp --print --mode json --no-session --auto-approve --model {_MODEL} -- {prompt} "
            f"2>&1 </dev/null | tee {output_dir}/omp.jsonl"
        )
        await self.exec_as_agent(environment, command=command, env=env)

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        output_path = self.logs_dir / "oh-my-pi" / "omp.jsonl"
        stats = parse_pi_jsonl(output_path)
        if not stats["events"]:
            return
        set_context(
            context,
            input_tokens=stats["input_tokens"],
            output_tokens=stats["output_tokens"],
            cache_tokens=stats["cache_tokens"],
            cost_usd=stats["cost_usd"],
            metadata={
                "model_calls": stats["model_calls"],
                "tool_calls": stats["tool_calls"],
                "failed_tool_calls": stats["failed_tool_calls"],
                "normalized_tools": stats["normalized_tools"],
                "reasoning_tokens": stats["reasoning_tokens"],
                "native_trajectory": "oh-my-pi/omp.jsonl",
                "native_event_count": stats["events"],
            },
        )
