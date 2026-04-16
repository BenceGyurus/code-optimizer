from typing import List

from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult


class RollbackToCheckpointTool(Tool):
    """Records rollback intent. Concrete checkpoint restore is handled by the runner layer."""

    @property
    def name(self) -> str:
        return "rollback_to_checkpoint"

    @property
    def allowed_states(self) -> List[State]:
        return [State.PATCH_PROPOSED]

    def execute(self, checkpoint_id: str = "latest", reason: str = "", **_: object) -> ToolResult:
        output = {"checkpoint_id": checkpoint_id, "reason": reason, "rollback_performed": False}
        return ToolResult(success=True, output=output, next_state=State.ANALYSIS_READY, metadata=output)
