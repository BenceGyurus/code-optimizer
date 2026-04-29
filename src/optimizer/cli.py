import os
import sys
from typing import Optional

if __package__ in {None, ""}:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(script_dir)
    sys.path = [path for path in sys.path if os.path.abspath(path or os.getcwd()) != script_dir]
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from optimizer.evaluation.evaluator import Evaluator
from optimizer.llm.prompt_loader import PromptLoader
from optimizer.orchestrator.guardrails import GuardrailsConfig
from optimizer.orchestrator.orchestrator import Orchestrator
from optimizer.providers.registry import registry as provider_registry
from optimizer.tools.registry import tool_registry

load_dotenv()

app = typer.Typer(help="LLM-driven optimization and evaluation framework.")
providers_app = typer.Typer(help="Provider commands.")
models_app = typer.Typer(help="Model commands.")
prompt_packs_app = typer.Typer(help="Prompt pack commands.")
console = Console()

app.add_typer(providers_app, name="providers")
app.add_typer(models_app, name="models")
app.add_typer(prompt_packs_app, name="prompt-packs")


@app.command()
def run(
    project: str = typer.Option(".", "--project", help="Path to the project to optimize."),
    provider: Optional[str] = typer.Option(None, "--provider", help="LLM provider name."),
    model: Optional[str] = typer.Option(None, "--model", help="Model name."),
    prompt_pack: str = typer.Option("default", "--prompt-pack", help="Prompt pack name."),
    build_command: Optional[str] = typer.Option(None, "--build-command", help="Build command."),
    test_command: Optional[str] = typer.Option(None, "--test-command", help="Test command."),
    benchmark_command: Optional[str] = typer.Option(None, "--benchmark-command", help="Benchmark command."),
    profile_command: Optional[str] = typer.Option(None, "--profile-command", help="Profiler command."),
    allow_all_changes: bool = typer.Option(False, "--allow-all-changes", help="Apply all proposed changes automatically."),
    interactive_approval: bool = typer.Option(True, "--interactive-approval/--no-interactive-approval", help="Ask before changes."),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Disable prompts and use defaults."),
    max_tool_calls: int = typer.Option(50, "--max-tool-calls", help="Maximum tool calls."),
    max_llm_calls: int = typer.Option(20, "--max-llm-calls", help="Maximum LLM calls."),
    max_iterations: int = typer.Option(5, "--max-iterations", help="Maximum optimization iterations."),
    runtime_repetitions: int = typer.Option(1, "--runtime-repetitions", help="Benchmark repetitions."),
    hardware_repetitions: int = typer.Option(1, "--hardware-repetitions", help="Profiler repetitions."),
    allow_deterministic_fallback: bool = typer.Option(False, "--allow-deterministic-fallback/--no-deterministic-fallback", help="Allow deterministic fallback patches after model patch failures."),
    output_dir: str = typer.Option("results", "--output-dir", help="Output directory."),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Print state, LLM and tool progress."),
):
    """Run one optimization session."""
    provider_name = provider or ("mock" if non_interactive else _choose_provider())
    p = provider_registry.get_provider(provider_name)
    if not p:
        console.print(f"[bold red]Provider not found:[/bold red] {provider_name}")
        raise typer.Exit(1)

    loader = PromptLoader()
    pack = loader.get_pack(prompt_pack)
    if not pack:
        console.print(f"[bold red]Prompt pack not found:[/bold red] {prompt_pack}")
        raise typer.Exit(1)
    missing = pack.validate()
    if missing:
        console.print(f"[bold red]Prompt pack is incomplete:[/bold red] {', '.join(missing)}")
        raise typer.Exit(1)

    config = GuardrailsConfig(
        max_tool_calls=max_tool_calls,
        max_llm_calls=max_llm_calls,
        max_iterations=max_iterations,
    )

    orchestrator = Orchestrator(
        project_path=project,
        provider=p,
        prompt_pack=pack,
        guardrails_config=config,
        interactive=interactive_approval and not allow_all_changes and not non_interactive,
        build_command=build_command,
        test_command=test_command,
        benchmark_command=benchmark_command,
        profile_command=profile_command,
        runtime_repetitions=runtime_repetitions,
        hardware_repetitions=hardware_repetitions,
        allow_deterministic_fallback=allow_deterministic_fallback,
        output_dir=output_dir,
        model=model,
        verbose=verbose,
    )

    console.print(f"[bold green]Optimizer session started[/bold green] project={project} provider={p.name}")
    final_state = orchestrator.run()
    console.print(f"[bold cyan]Session finished:[/bold cyan] {final_state.name}")


@app.command()
def evaluate(
    project: str = typer.Option(".", "--project", help="Path to the project to evaluate."),
    providers: str = typer.Option("mock", "--provider", "--providers", help="Comma-separated providers."),
    models: Optional[str] = typer.Option(None, "--model", "--models", help="Comma-separated models."),
    provider_models: Optional[str] = typer.Option(None, "--provider-models", help="Comma-separated provider=model pairs."),
    prompt_packs: str = typer.Option("default", "--prompt-pack", "--prompt-packs", help="Comma-separated prompt packs."),
    build_command: Optional[str] = typer.Option(None, "--build-command", help="Build command."),
    test_command: Optional[str] = typer.Option(None, "--test-command", help="Test command."),
    benchmark_command: Optional[str] = typer.Option(None, "--benchmark-command", help="Benchmark command."),
    profile_command: Optional[str] = typer.Option(None, "--profile-command", help="Profiler command."),
    repetitions: int = typer.Option(1, "--repetitions", help="Repetitions per configuration."),
    runtime_repetitions: int = typer.Option(5, "--runtime-repetitions", help="Benchmark repetitions."),
    hardware_repetitions: int = typer.Option(10, "--hardware-repetitions", help="Profiler repetitions."),
    output_dir: str = typer.Option("results", "--output-dir", help="Output directory."),
    max_tool_calls: int = typer.Option(50, "--max-tool-calls", help="Maximum tool calls."),
    max_llm_calls: int = typer.Option(20, "--max-llm-calls", help="Maximum LLM calls."),
    max_iterations: int = typer.Option(5, "--max-iterations", help="Maximum optimization iterations."),
    allow_deterministic_fallback: bool = typer.Option(False, "--allow-deterministic-fallback/--no-deterministic-fallback", help="Allow deterministic fallback patches after model patch failures."),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Print per-run optimizer progress."),
):
    """Run an experiment matrix across providers, models and prompt packs."""
    prompt_pack_names = _split_csv(prompt_packs)
    _validate_prompt_packs(prompt_pack_names)

    parsed_provider_models = _parse_provider_models_csv(provider_models) if provider_models else None
    provider_names = [provider for provider, _ in parsed_provider_models] if parsed_provider_models else _split_csv(providers)
    _validate_providers(provider_names)

    evaluator = Evaluator(output_dir=output_dir)
    result_dir = evaluator.run(
        project=project,
        providers=_split_csv(providers),
        models=_split_csv(models) if models else [None],
        prompt_packs=prompt_pack_names,
        repetitions=repetitions,
        provider_models=parsed_provider_models,
        build_command=build_command,
        test_command=test_command,
        benchmark_command=benchmark_command,
        profile_command=profile_command,
        runtime_repetitions=runtime_repetitions,
        hardware_repetitions=hardware_repetitions,
        max_tool_calls=max_tool_calls,
        max_llm_calls=max_llm_calls,
        max_iterations=max_iterations,
        allow_deterministic_fallback=allow_deterministic_fallback,
        verbose=verbose,
    )
    console.print(f"[bold cyan]Evaluation finished:[/bold cyan] {result_dir}")
    console.print(f"[dim]Report:[/dim] {result_dir}/report.md")
    console.print(f"[dim]Results:[/dim] {result_dir}/aggregated_results.yaml")
    console.print(f"[dim]Charts:[/dim] {result_dir}/charts/")


@providers_app.command("list")
def list_providers():
    table = Table(title="Available Providers")
    table.add_column("Name", style="cyan")
    table.add_column("Kind")
    table.add_column("Available")
    table.add_column("Default Model")
    for name in provider_registry.list_providers():
        provider = provider_registry.get_provider(name)
        table.add_row(name, provider.provider_kind(), "yes" if provider.is_available() else "no", provider.resolve_default_model() or "")
    console.print(table)


@models_app.command("list")
def list_models(provider: Optional[str] = typer.Option(None, "--provider", help="Provider filter.")):
    table = Table(title="Available Models")
    table.add_column("Provider", style="cyan")
    table.add_column("Model")
    names = [provider] if provider else provider_registry.list_providers()
    for name in names:
        p = provider_registry.get_provider(name)
        if not p:
            continue
        for model in p.list_models():
            table.add_row(name, model)
    console.print(table)


@prompt_packs_app.command("list")
def list_prompt_packs():
    loader = PromptLoader()
    table = Table(title="Available Prompt Packs")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Status")
    for name in loader.list_packs():
        pack = loader.get_pack(name)
        missing = pack.validate()
        table.add_row(name, pack.config.get("description", ""), "ok" if not missing else f"missing: {', '.join(missing)}")
    console.print(table)


@app.command()
def doctor():
    """Check providers, prompt packs and tool registry."""
    console.print("[bold]Tool registry[/bold]")
    console.print(", ".join(tool_registry.list_tools()))
    list_providers()
    list_prompt_packs()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_provider_models_csv(value: str) -> list[tuple[str, Optional[str]]]:
    pairs: list[tuple[str, Optional[str]]] = []
    for item in _split_csv(value):
        if "=" not in item:
            raise typer.BadParameter(
                "Each --provider-models entry must use provider=model syntax, for example "
                "`openrouter=openai/gpt-oss-120b`."
            )
        provider, model = item.split("=", 1)
        provider = provider.strip()
        model = model.strip() or None
        if not provider:
            raise typer.BadParameter("Provider name cannot be empty in --provider-models.")
        pairs.append((provider, model))
    return pairs


def _validate_prompt_packs(prompt_packs: list[str]) -> None:
    loader = PromptLoader()
    for name in prompt_packs:
        pack = loader.get_pack(name)
        if not pack:
            raise typer.BadParameter(f"Prompt pack not found: {name}")
        missing = pack.validate()
        if missing:
            raise typer.BadParameter(f"Prompt pack {name} is incomplete: {', '.join(missing)}")


def _validate_providers(provider_names: list[str]) -> None:
    unique_names = []
    for name in provider_names:
        if name not in unique_names:
            unique_names.append(name)
    for name in unique_names:
        provider = provider_registry.get_provider(name)
        if not provider:
            raise typer.BadParameter(f"Provider not found: {name}")
        if not provider.is_available():
            raise typer.BadParameter(f"Provider is not available in the current environment: {name}")


def _choose_provider() -> str:
    if provider_registry.get_provider("mock"):
        return "mock"
    available = [name for name in provider_registry.list_providers() if provider_registry.get_provider(name).is_available()]
    return available[0] if available else "mock"


if __name__ == "__main__":
    app()
