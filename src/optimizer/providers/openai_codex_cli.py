from optimizer.providers.static import CommandProvider


class OpenAICodexCliProvider(CommandProvider):
    provider_name = "openai-codex-cli"
    executable = "codex"
    default_models = ["gpt-5.3-codex", "gpt-5.2-codex", "gpt-5.1-codex-mini"]

    def supports_tool_use(self) -> bool:
        return True
