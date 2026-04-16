import json
import os
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field

from optimizer.utils.yaml_io import dump_yaml

@dataclass
class Artifact:
    name: str
    tool_name: str
    content: Any
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ArtifactStore:
    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        self.session_id = f"session_{int(time.time())}"
        self.session_dir = os.path.join(self.output_dir, self.session_id)
        os.makedirs(self.session_dir, exist_ok=True)
        self._artifacts: List[Dict[str, Any]] = []

    def save_artifact(self, name: str, tool_name: str, content: Any, metadata: Dict[str, Any] = None):
        artifact = {
            "name": name,
            "tool_name": tool_name,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        self._artifacts.append(artifact)
        
        # Save to disk as well
        file_path = os.path.join(self.session_dir, f"{name}_{int(time.time())}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(artifact, f, indent=2)
        except Exception as e:
            print(f"Failed to save artifact to disk: {e}")
        
        return file_path

    def save_named_yaml(self, filename: str, content: Dict[str, Any]) -> str:
        file_path = os.path.join(self.session_dir, filename)
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(dump_yaml(content))
        return file_path

    def get_artifacts(self, tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        if tool_name:
            return [a for a in self._artifacts if a["tool_name"] == tool_name]
        return self._artifacts

    def get_latest_artifact(self, name: str) -> Optional[Dict[str, Any]]:
        matching = [a for a in self._artifacts if a["name"] == name]
        if not matching:
            return None
        return sorted(matching, key=lambda x: x["timestamp"])[-1]
