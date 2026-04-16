from dataclasses import dataclass
from typing import Optional


@dataclass
class CommandSpec:
    command: str
    cwd: Optional[str] = None
    timeout: int = 300
