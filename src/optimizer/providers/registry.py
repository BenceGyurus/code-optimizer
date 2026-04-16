from typing import Dict, List, Optional

from optimizer.providers.base import Provider

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, Provider] = {}

    def register_provider(self, provider: Provider):
        self._providers[provider.name] = provider

    def get_provider(self, name: str) -> Optional[Provider]:
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        return sorted(self._providers.keys())

    @classmethod
    def discover_providers(cls):
        registry = cls()
        from .mock import MockProvider
        from .gemini_api import GeminiProvider
        from .openai_api import OpenAIProvider
        from .anthropic_api import AnthropicProvider
        from .openrouter_api import OpenRouterProvider
        from .openai_codex_cli import OpenAICodexCliProvider
        from .ollama_cli import OllamaCliProvider
        from .gemini_cli import GeminiCliProvider
        from .github_copilot_cli import GitHubCopilotCliProvider

        registry.register_provider(MockProvider())
        registry.register_provider(GeminiProvider())
        registry.register_provider(OpenAIProvider())
        registry.register_provider(AnthropicProvider())
        registry.register_provider(OpenRouterProvider())
        registry.register_provider(OpenAICodexCliProvider())
        registry.register_provider(OllamaCliProvider())
        registry.register_provider(GeminiCliProvider())
        registry.register_provider(GitHubCopilotCliProvider())
        return registry

# Global registry instance
registry = ProviderRegistry.discover_providers()
