from optimizer.providers.static import UnavailableApiProvider


class AnthropicProvider(UnavailableApiProvider):
    provider_name = "anthropic"
    env_var = "ANTHROPIC_API_KEY"
    default_models = ["claude-sonnet-4.5", "claude-haiku-4.5"]

    def supports_structured_output(self) -> bool:
        return True

    def supports_tool_use(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True
