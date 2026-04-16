import os
from typing import Dict, Any, Optional, List

from optimizer.utils.yaml_io import load_yaml

class PromptPack:
    def __init__(self, name: str, base_path: str):
        self.name = name
        self.base_path = base_path
        self.config = self._load_config()
        self.prompts: Dict[str, str] = self._load_prompts()

    def _load_config(self) -> Dict[str, Any]:
        config_path = os.path.join(self.base_path, "config.yaml")
        if os.path.exists(config_path):
            return load_yaml(config_path)
        return {}

    def _load_prompts(self) -> Dict[str, str]:
        prompts = {}
        for f in os.listdir(self.base_path):
            if f.endswith(".md"):
                prompt_name = f[:-3]
                with open(os.path.join(self.base_path, f), "r", encoding="utf-8") as file:
                    prompts[prompt_name] = file.read()
        return prompts

    def get_prompt(self, name: str) -> Optional[str]:
        return self.prompts.get(name)

    def validate(self) -> List[str]:
        required = ["master", "decision", "analyze_candidate", "propose_change", "evaluate_result"]
        return [name for name in required if name not in self.prompts]

class PromptLoader:
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = prompts_dir
        self.packs: Dict[str, PromptPack] = self._discover_packs()

    def _discover_packs(self) -> Dict[str, PromptPack]:
        packs = {}
        if not os.path.exists(self.prompts_dir):
            return packs
        for item in os.listdir(self.prompts_dir):
            item_path = os.path.join(self.prompts_dir, item)
            if os.path.isdir(item_path):
                packs[item] = PromptPack(item, item_path)
        return packs

    def get_pack(self, name: str) -> Optional[PromptPack]:
        return self.packs.get(name)

    def list_packs(self) -> List[str]:
        return list(self.packs.keys())
