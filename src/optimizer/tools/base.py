from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from optimizer.orchestrator.state_machine import State

@dataclass
class ToolResult:
    success: bool
    output: Any
    next_state: Optional[State] = None
    metadata: Optional[Dict[str, Any]] = None

class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tool."""
        pass

    @property
    @abstractmethod
    def allowed_states(self) -> List[State]:
        """States in which this tool is allowed to run."""
        pass

    @property
    def description(self) -> str:
        return self.__class__.__doc__ or ""

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool's action."""
        pass
