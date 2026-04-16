from optimizer.providers.static import CommandProvider


class GitHubCopilotCliProvider(CommandProvider):
    provider_name = "github-copilot-cli"
    executable = "gh"
    default_models = ["copilot/gpt-4o", "copilot/claude-3.5-sonnet"]

    def supports_tool_use(self) -> bool:
        return True
