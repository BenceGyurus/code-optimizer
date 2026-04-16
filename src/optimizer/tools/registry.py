from typing import Dict, List, Optional

from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self, current_state: Optional[State] = None) -> List[str]:
        if current_state is None:
            return list(self._tools.keys())
        return [name for name, tool in self._tools.items() if current_state in tool.allowed_states]

    @classmethod
    def discover_tools(cls):
        registry = cls()
        from .inspect_codebase import InspectCodebaseTool
        from .run_baseline import RunBaselineTool
        from .profile_execution import ProfileExecutionTool
        from .analyze_candidate import AnalyzeCandidateTool
        from .propose_change import ProposeChangeTool
        from .apply_and_verify import ApplyAndVerifyTool
        from .remeasure import RemeasureTool
        from .evaluate_result import EvaluateResultTool
        from .rollback_to_checkpoint import RollbackToCheckpointTool

        registry.register_tool(InspectCodebaseTool())
        registry.register_tool(RunBaselineTool())
        registry.register_tool(ProfileExecutionTool())
        registry.register_tool(AnalyzeCandidateTool())
        registry.register_tool(ProposeChangeTool())
        registry.register_tool(ApplyAndVerifyTool())
        registry.register_tool(RemeasureTool())
        registry.register_tool(EvaluateResultTool())
        registry.register_tool(RollbackToCheckpointTool())
        return registry

# Global registry instance
tool_registry = ToolRegistry.discover_tools()
