import itertools
import os
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass
class ExperimentConfig:
    provider: str
    model: Optional[str]
    prompt_pack: str
    repetition: int


class ExperimentManager:
    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir

    def create_run_dir(self) -> str:
        path = os.path.join(self.output_dir, f"eval_{int(time.time())}")
        os.makedirs(os.path.join(path, "per_run"), exist_ok=True)
        os.makedirs(os.path.join(path, "charts"), exist_ok=True)
        return path

    def matrix(
        self,
        providers: Iterable[str],
        models: Iterable[Optional[str]],
        prompt_packs: Iterable[str],
        repetitions: int,
    ) -> List[ExperimentConfig]:
        configs = []
        for provider, model, prompt_pack, repetition in itertools.product(providers, models, prompt_packs, range(1, repetitions + 1)):
            configs.append(ExperimentConfig(provider=provider, model=model, prompt_pack=prompt_pack, repetition=repetition))
        return configs
