from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

@dataclass
class LLMRequest:
    prompt: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 4096
    stop_sequences: Optional[List[str]] = None
    structured_output: bool = False

@dataclass
class LLMResponse:
    content: str
    model_name: str
    provider_name: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: str = "stop"

class Provider(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the provider is configured and reachable."""
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """Returns a list of available models for this provider."""
        pass

    def resolve_default_model(self) -> Optional[str]:
        """Returns the default model for this provider."""
        models = self.list_models()
        return models[0] if models else None

    @abstractmethod
    def send_prompt(self, request: LLMRequest) -> LLMResponse:
        """Sends a prompt to the LLM and returns the response."""
        pass

    def supports_structured_output(self) -> bool:
        return False

    def supports_tool_use(self) -> bool:
        return False

    def supports_streaming(self) -> bool:
        return False

    def provider_kind(self) -> str:
        return "api"

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'gemini', 'openai', 'ollama')."""
        pass
