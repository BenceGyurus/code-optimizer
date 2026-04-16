from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Decision:
    action: str
    args: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
