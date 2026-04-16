import os
from dataclasses import asdict
from typing import Optional

from optimizer.state.models import SessionState
from optimizer.utils.yaml_io import dump_yaml


class SessionStateStore:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def save(self, state: SessionState, filename: str = "session_state.yaml") -> str:
        path = os.path.join(self.output_dir, filename)
        data = asdict(state)
        data["current_state"] = state.current_state.name
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(dump_yaml(data))
        return path

    def load(self, filename: str = "session_state.yaml") -> Optional[SessionState]:
        path = os.path.join(self.output_dir, filename)
        if not os.path.exists(path):
            return None
        return None
