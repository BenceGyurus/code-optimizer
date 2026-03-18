import os
import yaml
import typer
import subprocess
import textwrap
import datetime
from typing import Optional, List
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table

from hunter import scan_file
from linter import run_ruff_linter
from optimizer import Optimizer
from patcher import CodePatcher

# Load environment variables
load_dotenv()

app = typer.Typer(help="OptiCode: Hybrid (AST + LLM) Code Optimizer CLI")
console = Console()

def git_command(args: List[str]) -> bool:
    try:
        subprocess.run(["git"] + args, capture_output=True, check=True)
        return True
    except:
        return False

def load_rules():
    rules_path = "rules.yaml"
    if not os.path.exists(rules_path):
        return {"rules": {}}
    with open(rules_path, "r") as f:
        return yaml.safe_load(f)

def run_tests(test_cmd: str) -> bool:
    """Executes the user-provided test command."""
    try:
        console.print(f"[dim]Running tests: {test_cmd}...[/dim]")
        result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def get_python_files(path: str) -> List[str]:
    p = Path(path)
    if p.is_file():
        return [str(p)] if p.suffix == ".py" else []
    elif p.is_dir():
        return [str(f) for f in p.rglob("*.py") if "__pycache__" not in str(f)]
    return []

@app.command()
def optimize(
    path: str = typer.Argument(..., help="Path to a Python file or directory"),
    allow_edit: bool = typer.Option(False, "--allow-edit", "-y", help="Automatically apply all optimizations"),
    focus: str = typer.Option("all", "--focus", "-f", help="Specific optimization rule to focus on"),
    skip_linter: bool = typer.Option(False, "--skip-linter", help="Skip Ruff static analysis"),
    max_passes: int = typer.Option(3, "--max-passes", help="Maximum number of optimization passes"),
    test_cmd: Optional[str] = typer.Option(None, "--test-cmd", help="Command to run tests (e.g., 'pytest')"),
    git_branch: bool = typer.Option(False, "--git-branch", help="Create a new git branch for the session"),
    ci: bool = typer.Option(False, "--ci", help="CI Pipeline mode: Auto-apply if tests pass, auto-rollback if they fail. No prompts.")
):
    """
    Scans Python files for optimization opportunities and applies them using LLM.
    Features: Multi-pass, Caching, Git integration, Automated Testing, CI Mode.
    """
    files = get_python_files(path)
    if not files:
        console.print(f"[bold red]Error: No Python files found at {path}.[/bold red]")
        raise typer.Exit(1)

    # In CI mode, we must have a test command to be useful, and allow_edit is implied
    if ci and not test_cmd:
        console.print("[bold red]Error: --ci mode requires a --test-cmd to verify changes.[/bold red]")
        raise typer.Exit(1)

    rules_config = load_rules()
    optimizer = Optimizer(provider="gemini", rules_config=rules_config)
    any_changes_overall = False

    for file_path in files:
        console.print(f"\n[bold cyan]Processing: {file_path}[/bold cyan]")
        current_pass = 1
        
        while current_pass <= max_passes:
            console.print(f"[dim]Pass {current_pass}/{max_passes}[/dim]")
            matches = scan_file(file_path, rules_config)
            if not skip_linter:
                matches.extend(run_ruff_linter(file_path))
            
            if focus != "all":
                matches = [m for m in matches if focus in m.rule_id]

            if not matches:
                break

            patcher = CodePatcher(file_path)
            changes_in_pass = 0

            for match in matches:
                with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as progress:
                    progress.add_task(description=f"Optimizing {match.rule_id}...", total=None)
                    opt_data = optimizer.optimize_snippet(match)

                if not opt_data or not opt_data.get("code"):
                    continue

                if textwrap.dedent(opt_data["code"]).strip() == textwrap.dedent(match.snippet).strip():
                    continue

                # In CI mode, we don't show diffs or ask questions
                if not ci:
                    if opt_data.get("cached"):
                        console.print("[dim italic]Using cached optimization...[/dim italic]")
                    patcher.show_diff(match, opt_data)
                
                # Decision logic
                should_apply = ci or allow_edit or patcher.ask_confirmation()
                
                if should_apply:
                    if patcher.apply_patch(match, opt_data["code"]):
                        if not ci:
                            console.print(f"[green]Applied {match.rule_id}[/green]")
                        
                        if test_cmd:
                            success = run_tests(test_cmd)
                            if not success:
                                if ci:
                                    console.print(f"[yellow]Tests failed for {match.rule_id}. Auto-rolling back.[/yellow]")
                                    patcher.rollback()
                                    continue
                                elif Confirm.ask("[bold red]Tests failed! Rollback?[/bold red]", default=True):
                                    patcher.rollback()
                                    continue
                        
                        # Git Commit per change
                        if git_branch:
                            git_command(["add", file_path])
                            git_command(["commit", "-m", f"OptiCode: {match.rule_id} optimization in {file_path}"])

                        changes_in_pass += 1
                        any_changes_overall = True
                        patcher = CodePatcher(file_path)

            if changes_in_pass == 0:
                break
            current_pass += 1
        
        if any_changes_overall:
            final_patcher = CodePatcher(file_path)
            final_patcher.finalize_imports()

    # Final Stats
    table = Table(title="Session Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Total Tokens", str(optimizer.total_tokens))
    table.add_row("Total Cost", f"${optimizer.total_cost:.4f}")
    table.add_row("Files Modified", str(len(files) if any_changes_overall else 0))
    console.print(table)

if __name__ == "__main__":
    app()
