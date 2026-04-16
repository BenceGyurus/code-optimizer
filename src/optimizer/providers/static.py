import os
import shutil
import subprocess
from typing import List, Optional

from optimizer.providers.base import LLMRequest, LLMResponse, Provider


class UnavailableApiProvider(Provider):
    env_var: str = ""
    default_models: List[str] = []
    provider_name: str = ""

    def is_available(self) -> bool:
        return bool(os.getenv(self.env_var))

    def list_models(self) -> List[str]:
        return self.default_models

    def send_prompt(self, request: LLMRequest) -> LLMResponse:
        raise RuntimeError(f"{self.name} provider is not implemented for live API calls in this MVP.")

    @property
    def name(self) -> str:
        return self.provider_name


class CommandProvider(Provider):
    executable: str = ""
    provider_name: str = ""
    default_models: List[str] = []

    def is_available(self) -> bool:
        return shutil.which(self.executable) is not None

    def list_models(self) -> List[str]:
        return self.default_models

    def send_prompt(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError(f"{self.executable} executable is not available.")

        process = subprocess.run(
            [self.executable],
            input=request.prompt,
            text=True,
            capture_output=True,
            timeout=300,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(process.stderr.strip() or f"{self.name} CLI call failed.")

        return LLMResponse(
            content=process.stdout,
            model_name=self.resolve_default_model() or self.name,
            provider_name=self.name,
        )

    def provider_kind(self) -> str:
        return "cli"

    @property
    def name(self) -> str:
        return self.provider_name

    def resolve_default_model(self) -> Optional[str]:
        return self.default_models[0] if self.default_models else None
