import requests
import time
import webbrowser
from rich.console import Console
from rich.panel import Panel

console = Console()

def github_login() -> str:
    """Handles guidance for GitHub Models authentication."""
    console.print(Panel("[bold cyan]GitHub Models (Marketplace) Authentication[/bold cyan]\n\n"
                        "To use models like GPT-4o or Claude 3.5 via GitHub, you need a \n"
                        "Personal Access Token (PAT) with access to 'GitHub Models'.\n\n"
                        "1. I will open the GitHub token creation page for you.\n"
                        "2. [bold red]CRITICAL:[/bold] If using Fine-grained tokens, you MUST enable:\n"
                        "   [white]Account permissions -> GitHub Models -> Read-only[/white].\n"
                        "3. If using Classic tokens, ensure you joined the preview at:\n"
                        "   [underline]https://github.com/marketplace/models[/underline]\n"
                        "4. Generate the token and paste it here.", 
                        border_style="cyan"))

    time.sleep(2)
    # Direct link to fine-grained tokens which is safer and recommended now
    url = "https://github.com/settings/personal-access-tokens/new"
    console.print(f"\n[dim]Opening: {url}[/dim]")
    webbrowser.open(url)

    console.print("\n[bold green]Paste your GitHub Token here:[/bold green]")
    token = input("> ").strip()
    return token
