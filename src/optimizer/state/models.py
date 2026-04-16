from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from optimizer.orchestrator.state_machine import State


@dataclass
class SessionConfig:
    project_path: str
    provider: str = "mock"
    model: Optional[str] = None
    prompt_pack: str = "default"
    build_command: Optional[str] = None
    test_command: Optional[str] = None
    benchmark_command: Optional[str] = None
    profile_command: Optional[str] = None
    allow_all_changes: bool = False
    interactive_approval: bool = True
    runtime_repetitions: int = 1
    hardware_repetitions: int = 1
    output_dir: str = "results"


@dataclass
class SessionState:
    current_state: State = State.INIT
    current_target: Optional[str] = None
    best_result: Optional[Dict[str, Any]] = None
    latest_result: Optional[Dict[str, Any]] = None
    counters: Dict[str, int] = field(default_factory=dict)
    checkpoint_metadata: Dict[str, Any] = field(default_factory=dict)
    approval_policy: Dict[str, Any] = field(default_factory=dict)
