from optimizer.providers.static import CommandProvider


class GeminiCliProvider(CommandProvider):
    provider_name = "gemini-cli"
    executable = "gemini"
    default_models = ["gemini-2.5-pro", "gemini-2.5-flash"]

    def supports_streaming(self) -> bool:
        return True
