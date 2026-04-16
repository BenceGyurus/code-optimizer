import os
from typing import List

from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult

class InspectCodebaseTool(Tool):
    """Project structure inspection."""
    @property
    def name(self) -> str:
        return "inspect_codebase"

    @property
    def allowed_states(self) -> List[State]:
        return [State.INIT, State.BASELINE_READY]

    def execute(self, project_path: str = ".", **_: object) -> ToolResult:
        try:
            if os.path.isfile(project_path):
                return ToolResult(
                    success=True,
                    output={"files": [os.path.basename(project_path)], "count": 1},
                    metadata={"project_path": project_path, "project_kind": "file"},
                )

            files = []
            for root, dirs, filenames in os.walk(project_path):
                # Simple ignore list
                if any(ignored in root for ignored in [".git", "__pycache__", ".venv", ".pytest_cache", "results"]):
                    continue
                for f in filenames:
                    files.append(os.path.relpath(os.path.join(root, f), project_path))
            
            return ToolResult(
                success=True,
                output={"files": files, "count": len(files)},
                metadata={"project_path": project_path}
            )
        except Exception as e:
            return ToolResult(success=False, output=str(e))
