from optimizer.providers.static import UnavailableApiProvider


class OpenAIProvider(UnavailableApiProvider):
    provider_name = "openai"
    env_var = "OPENAI_API_KEY"
    default_models = ["gpt-5.4", "gpt-5.4-mini", "gpt-5.3-codex"]

    def supports_structured_output(self) -> bool:
        return True

    def supports_tool_use(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True
