"""Harbor recovery agent that replays a completed agent's saved patch.

It is deliberately not part of the benchmark harness set. It exists only to
re-run a verifier when Harbor lost the result envelope after the real agent
had already finished.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import override

from harbor.agents.base import BaseAgent
from harbor.agents.capabilities import AgentCapabilities
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


class ReplayPatchAgent(BaseAgent):
    capabilities = AgentCapabilities()

    @staticmethod
    @override
    def name() -> str:
        return "replay-patch"

    @override
    def version(self) -> str:
        return "1.0.0"

    @override
    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    @override
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        patch_path = Path(os.environ["MERCURY_V2_REPLAY_PATCH"])
        if not patch_path.is_file():
            raise RuntimeError(f"Replay patch not found: {patch_path}")
        await environment.upload_file(patch_path, "/tmp/mercury-v2-replay.patch")
        result = await environment.exec(
            "set -e; git apply --binary /tmp/mercury-v2-replay.patch; "
            "mkdir -p /logs/agent/replay-patch; "
            "git diff --binary > /logs/agent/replay-patch/patch.diff",
            cwd="/testbed",
        )
        if result.return_code != 0:
            raise RuntimeError(result.stderr or result.stdout or "git apply failed")
