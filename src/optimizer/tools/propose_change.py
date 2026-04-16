from typing import List

from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult


class ProposeChangeTool(Tool):
    """Stores a concrete patch proposal for approval and application."""

    @property
    def name(self) -> str:
        return "propose_change"

    @property
    def allowed_states(self) -> List[State]:
        return [State.ANALYSIS_READY]

    def execute(self, target: str = "unspecified", strategy: str = "", patch: str = "", rationale: str = "", **_: object) -> ToolResult:
        patch = patch or ""
        output = {
            "target": target,
            "strategy": strategy,
            "patch": patch,
            "has_patch": bool(patch.strip()),
            "rationale": rationale,
            "patch_signature": str(hash(patch or f"{target}:{strategy}")),
        }
        return ToolResult(success=True, output=output, next_state=State.PATCH_PROPOSED, metadata=output)
