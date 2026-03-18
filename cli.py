import os
import yaml
import typer
from typing import Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from hunter import scan_file
from linter import run_ruff_linter
from optimizer import Optimizer
from patcher import CodePatcher

# Load environment variables
load_dotenv()

app = typer.Typer(help="OptiCode: Hybrid (AST + LLM) Code Optimizer CLI")
console = Console()

def load_rules():
    rules_path = "rules.yaml"
    if not os.path.exists(rules_path):
        return {"rules": {}}
    with open(rules_path, "r") as f:
        return yaml.safe_load(f)

@app.command()
def optimize(
    file_path: str = typer.Argument(..., help="Path to the Python file to optimize"),
    allow_edit: bool = typer.Option(False, "--allow-edit", "-y", help="Automatically apply all optimizations"),
    focus: str = typer.Option("all", "--focus", "-f", help="Specific optimization rule to focus on"),
    skip_linter: bool = typer.Option(False, "--skip-linter", help="Skip Ruff static analysis"),
    max_passes: int = typer.Option(3, "--max-passes", help="Maximum number of optimization passes")
):
    """
    Scans a Python file for optimization opportunities and applies them using LLM.
    Iteratively re-scans if changes are made.
    """
    if not os.path.exists(file_path):
        console.print(f"[bold red]Error: File {file_path} not found.[/bold red]")
        raise typer.Exit(1)

    rules_config = load_rules()
    
    current_pass = 1
    any_changes_in_session = False

    while current_pass <= max_passes:
        console.print(f"\n[bold magenta]=== Pass {current_pass} / {max_passes} ===[/bold magenta]")
        
        # --- PHASE 1: SCANNING ---
        console.print(f"[bold blue]Scanning {file_path}...[/bold blue]")
        
        # AST Scanning
        matches = scan_file(file_path, rules_config)
        
        # Static Analysis Scanning (Ruff)
        if not skip_linter:
            console.print("[dim]Running Ruff static analysis...[/dim]")
            linter_matches = run_ruff_linter(file_path)
            matches.extend(linter_matches)
        
        # Filter if focus is set
        if focus != "all":
            matches = [m for m in matches if focus in m.rule_id]

        if not matches:
            console.print("[green]No more optimization opportunities found.[/green]")
            break

        console.print(f"[bold blue]Found {len(matches)} potential hotspots. Consulting Optimizer...[/bold blue]")
        
        optimizer = Optimizer(provider="gemini", rules_config=rules_config)
        patcher = CodePatcher(file_path)
        
        changes_made_in_pass = 0

        # Process each match
        for i, match in enumerate(matches):
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                progress.add_task(description=f"Optimizing {match.rule_id}...", total=None)
                opt_data = optimizer.optimize_snippet(match)

            if not opt_data or not opt_data.get("code"):
                console.print(f"[red]Failed to optimize snippet {i+1}.[/red]")
                continue

            patcher.show_diff(match, opt_data)
            
            if allow_edit or patcher.ask_confirmation():
                if patcher.apply_patch(match, opt_data["code"]):
                    console.print(f"[bold green]Applied optimization {i+1}![/bold green]")
                    changes_made_in_pass += 1
                    any_changes_in_session = True
                    # Refresh patcher for subsequent matches in the same pass
                    patcher = CodePatcher(file_path)
                else:
                    console.print(f"[bold red]Failed to apply optimization {i+1}.[/bold red]")
            else:
                console.print(f"[yellow]Skipped optimization {i+1}.[/yellow]")

        if changes_made_in_pass == 0:
            console.print("[yellow]No changes were applied in this pass. Stopping.[/yellow]")
            break
        
        current_pass += 1

    if any_changes_in_session:
        console.print("\n[bold green]Iterative optimization finished! Your code is now multi-pass optimized.[/bold green]")
    else:
        console.print("\n[bold green]Optimization finished (no changes made).[/bold green]")

if __name__ == "__main__":
    app()
