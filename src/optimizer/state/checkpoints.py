import os
import shutil
import time
from typing import Iterable


class CheckpointStore:
    def __init__(self, project_path: str, output_dir: str):
        self.project_path = project_path
        self.output_dir = output_dir
        self.checkpoint_dir = os.path.join(output_dir, "checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def create(self, label: str = "checkpoint") -> str:
        checkpoint_id = f"{label}_{int(time.time())}"
        destination = os.path.join(self.checkpoint_dir, checkpoint_id)
        shutil.copytree(self.project_path, destination, ignore=self._ignore)
        return checkpoint_id

    def restore(self, checkpoint_id: str) -> None:
        source = os.path.join(self.checkpoint_dir, checkpoint_id)
        if not os.path.isdir(source):
            raise FileNotFoundError(checkpoint_id)
        for item in os.listdir(source):
            source_path = os.path.join(source, item)
            dest_path = os.path.join(self.project_path, item)
            if os.path.isdir(source_path):
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                shutil.copytree(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)

    def _ignore(self, directory: str, names: Iterable[str]):
        ignored = {".git", ".venv", "__pycache__", ".pytest_cache", "results"}
        return {name for name in names if name in ignored}
