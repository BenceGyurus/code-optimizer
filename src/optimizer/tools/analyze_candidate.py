from typing import List

from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult


class AnalyzeCandidateTool(Tool):
    """Records the selected target and strategy after LLM analysis."""

    @property
    def name(self) -> str:
        return "analyze_candidate"

    @property
    def allowed_states(self) -> List[State]:
        return [State.BASELINE_READY, State.PROFILE_READY]

    def execute(self, target: str = "unspecified", strategy: str = "inspect hot path", rationale: str = "", **_: object) -> ToolResult:
        output = {
            "target": target,
            "strategy": strategy,
            "rationale": rationale,
        }
        return ToolResult(success=True, output=output, next_state=State.ANALYSIS_READY, metadata=output)
