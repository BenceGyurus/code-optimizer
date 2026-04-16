import json
import time
from typing import Any, Dict


class JsonlLogger:
    def __init__(self, path: str):
        self.path = path

    def log(self, event: str, payload: Dict[str, Any]) -> None:
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"timestamp": time.time(), "event": event, "payload": payload}, default=str) + "\n")
