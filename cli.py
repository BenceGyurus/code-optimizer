import os
import yaml
import typer
import subprocess
import textwrap
import datetime
import requests
from typing import Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, IntPrompt
from rich.table import Table
from rich.panel import Panel

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

def run_tests(test_cmd: str) -> Dict[str, object]:
    try:
        console.print(f"[dim]Running tests: {test_cmd}...[/dim]")
        result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout or "",
            "stderr": result.stderr or ""
        }
    except:
        return {"ok": False, "stdout": "", "stderr": ""}

def get_python_files(path: str) -> List[str]:
    p = Path(path)
    ignore_dirs = {".venv", "venv", "env", ".git", "__pycache__", ".ruff_cache", ".opticode_cache"}
    if p.is_file():
        return [str(p)] if p.suffix == ".py" else []
    elif p.is_dir():
        files = []
        for f in p.rglob("*.py"):
            if not any(part in ignore_dirs for part in f.parts):
                files.append(str(f))
        return files
    return []

def fetch_github_models(token: str) -> List[str]:
    """Fetches available models from GitHub Marketplace."""
    fallbacks = ["github/gpt-4o", "github/gpt-4o-mini", "github/claude-3-5-sonnet"]
    try:
        response = requests.get(
            "https://api.github.com/models",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            models = response.json()
            fetched = [f"github/{m['name']}" for m in models]
            return fetched if fetched else fallbacks
        return fallbacks
    except:
        return fallbacks

def fetch_copilot_models() -> List[str]:
    """Models available via the official Copilot Chat API."""
    env_models = os.getenv("COPILOT_MODELS")
    if env_models:
        models = [m.strip() for m in env_models.split(",") if m.strip()]
        if models:
            return models
    return ["copilot/gpt-4o", "copilot/claude-3.5-sonnet", "copilot/gpt-5.2-codex"]

def fetch_ollama_models() -> List[str]:
    """Fetches locally installed Ollama models."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            return [f"ollama/{m['name']}" for m in response.json().get("models", [])]
        return []
    except:
        return []

def fetch_gemini_models() -> List[str]:
    return ["gemini/gemini-1.5-flash-latest", "gemini/gemini-1.5-pro-latest", "gemini/gemini-2.0-flash-exp", "gemini/gemini-2-flash-lite"]

@app.command()
def optimize(
    path: str = typer.Argument(..., help="Path to a Python file or directory"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Explicit model ID"),
    remote_model: Optional[str] = typer.Option(None, "--remote-model", help="Remote model ID for escalation"),
    decision_models: Optional[str] = typer.Option(None, "--decision-models", help="Comma-separated models for rerank/verify"),
    allow_edit: bool = typer.Option(False, "--allow-edit", "-y", help="Automatically apply all optimizations"),
    focus: str = typer.Option("all", "--focus", "-f", help="Specific optimization rule to focus on"),
    skip_linter: bool = typer.Option(False, "--skip-linter", help="Skip Ruff static analysis"),
    max_passes: int = typer.Option(3, "--max-passes", help="Maximum number of optimization passes"),
    test_cmd: Optional[str] = typer.Option(None, "--test-cmd", help="Command to run tests"),
    git_branch: bool = typer.Option(False, "--git-branch", help="Create a git branch"),
    allow_remote: bool = typer.Option(False, "--allow-remote", help="Allow remote LLM escalation"),
    max_remote_file_percent: int = typer.Option(20, "--max-remote-file-percent", help="Max percent of file to send remotely"),
    recursive_max_steps: int = typer.Option(2, "--recursive-max-steps", help="Recursive small-model attempts"),
    rollback_on_fail: bool = typer.Option(False, "--rollback-on-fail", help="Auto-rollback when tests fail"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable optimization cache"),
    repair_mode: bool = typer.Option(False, "--repair-mode", help="Attempt test-driven repairs on failure"),
    safe_only: bool = typer.Option(False, "--safe-only", help="Use deterministic safe optimizations only"),
    micro_steps: int = typer.Option(2, "--micro-steps", help="Max recursive micro-steps per snippet"),
    max_slice_lines: int = typer.Option(50, "--max-slice-lines", help="Max lines sent to LLM per snippet"),
    debug_matches: bool = typer.Option(False, "--debug-matches", help="Print rule matches and skip reasons"),
    retrieval_top_k: int = typer.Option(3, "--retrieval-top-k", help="Top-k rule candidates from heuristics"),
    ci: bool = typer.Option(False, "--ci", help="CI Pipeline mode")
):
    """Hybrid Code Optimizer with Dynamic Model Selection."""
    
    # --- DYNAMIC MODEL SELECTION ---
    if not model and not ci:
        console.print(Panel("[bold cyan]Step 1: Select Provider[/bold cyan]\n"
                            "1. [magenta]Gemini[/magenta]\n"
                            "2. [green]GitHub Marketplace Models[/green] (Needs 'models' PAT permission)\n"
                            "3. [blue]GitHub Copilot Chat[/blue] (Use your existing Copilot token)\n"
                            "4. [yellow]Ollama (Local)[/yellow]", title="OptiCode Engine"))
        p_choice = IntPrompt.ask("Choice", default=1)
        
        candidates = []
        if p_choice == 1:
            if not os.getenv("GEMINI_API_KEY"):
                os.environ["GEMINI_API_KEY"] = typer.prompt("Enter Gemini API Key")
            candidates = fetch_gemini_models()
        elif p_choice == 2:
            token = os.getenv("GITHUB_TOKEN")
            if not token:
                from auth import github_login
                token = github_login()
                os.environ["GITHUB_TOKEN"] = token
            with console.status("[bold green]Fetching Marketplace models..."):
                candidates = fetch_github_models(token)
        elif p_choice == 3:
            if not os.getenv("GITHUB_TOKEN"):
                from auth import github_login
                os.environ["GITHUB_TOKEN"] = github_login()
            candidates = fetch_copilot_models()
        elif p_choice == 4:
            with console.status("[bold yellow]Fetching Ollama models..."):
                candidates = fetch_ollama_models()

        if not candidates:
            console.print("[red]No models found. Falling back to Gemini.[/red]")
            model = "gemini/gemini-1.5-flash-latest"
        else:
            console.print(f"\n[bold cyan]Step 2: Select Model[/bold cyan]")
            for idx, c in enumerate(candidates, 1):
                console.print(f"{idx}. {c}")
            m_choice = IntPrompt.ask("Choice", default=1)
            model = candidates[m_choice-1] if 1 <= m_choice <= len(candidates) else candidates[0]

    console.print(f"[bold green]Running with: {model}[/bold green]\n")

    files = get_python_files(path)
    if not files:
        console.print(f"[bold red]Error: No Python files found at {path}.[/bold red]")
        raise typer.Exit(1)

    rules_config = load_rules()
    decision_model_list = [m.strip() for m in decision_models.split(",") if m.strip()] if decision_models else []

    optimizer = Optimizer(
        provider=model or "gemini/gemini-1.5-flash-latest",
        rules_config=rules_config,
        allow_remote=allow_remote,
        max_remote_file_percent=max_remote_file_percent,
        remote_model=remote_model,
        decision_models=decision_model_list,
        recursive_max_steps=micro_steps,
        use_cache=not no_cache
    )
    any_changes_overall = False
    modified_files_count = 0
    rollback_count = 0
    noop_count = 0
    skipped_count = 0

    for file_path in files:
        # Skip optimizing the tool itself to avoid recursive complexity
        if any(tool_file in file_path for tool_file in ["cli.py", "optimizer.py", "patcher.py", "hunter.py", "auth.py", "linter.py"]):
            continue

        console.print(f"\n[bold cyan]Processing: {file_path}[/bold cyan]")
        current_pass = 1
        file_changed = False
        
        with open(file_path, "r") as f:
            total_lines = len(f.readlines())

        while current_pass <= max_passes:
            console.print(f"[dim]Pass {current_pass}/{max_passes}[/dim]")
            matches = scan_file(file_path, rules_config)
            if not skip_linter:
                matches.extend(run_ruff_linter(file_path))
            
            if focus != "all":
                matches = [m for m in matches if focus in m.rule_id]

            console.print(f"[dim]Matches found: {len(matches)}[/dim]")
            if debug_matches:
                for m in matches:
                    snippet_lines = len(m.snippet.splitlines())
                    console.print(f"[dim]- {m.rule_id} (lines {m.start_line}-{m.end_line}, snippet {snippet_lines} lines)[/dim]")

            if not matches:
                break

            patcher = CodePatcher(file_path)
            changes_in_pass = 0
            restart_pass = False

            # --- RERANKING LOGIC ---
            grouped_matches = {}
            for m in matches:
                key = (m.start_line, m.end_line)
                if key not in grouped_matches: grouped_matches[key] = []
                grouped_matches[key].append(m)

            for key, candidates in grouped_matches.items():
                best_match = candidates[0]
                if len(candidates) > 1:
                    with Progress(SpinnerColumn(), TextColumn("[dim]Reranking...[/dim]"), transient=True) as progress:
                        progress.add_task(description="Reranking", total=None)
                        best_match_id = optimizer.rerank_rules(best_match.snippet, [c.rule_id for c in candidates])
                        for c in candidates:
                            if c.rule_id == best_match_id:
                                best_match = c
                                break

                if best_match.rule_id == "loop_invariant_redundancy" and test_cmd and safe_only:
                    skipped_count += 1
                    console.print("[dim]Skipped loop_invariant_redundancy (safe-only).[/dim]")
                    continue

                opt_data = None
                if safe_only:
                    opt_data = optimizer.deterministic_optimize(best_match)
                else:
                    snippet_lines = best_match.snippet.splitlines()
                    if max_slice_lines and len(snippet_lines) > max_slice_lines:
                        skipped_count += 1
                        console.print(f"[dim]Skipped {best_match.rule_id} (slice {len(snippet_lines)} > {max_slice_lines}).[/dim]")
                        continue
                    candidates = optimizer.retrieve_candidates(best_match.snippet, top_k=retrieval_top_k)
                    if best_match.rule_id not in candidates:
                        skipped_count += 1
                        console.print(f"[dim]Skipped {best_match.rule_id} (retrieval mismatch).[/dim]")
                        continue
                    with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as progress:
                        progress.add_task(description=f"Optimizing {best_match.rule_id}...", total=None)
                        opt_data = optimizer.optimize_snippet(
                            best_match,
                            file_path=file_path,
                            total_lines=total_lines
                        )

                if not opt_data or not opt_data.get("code"):
                    skipped_count += 1
                    console.print(f"[dim]Skipped {best_match.rule_id} (no optimization).[/dim]")
                    continue
                if optimizer.is_noop_alias_change(best_match.snippet, opt_data.get("code", "")):
                    noop_count += 1
                    console.print(f"[dim]Skipped {best_match.rule_id} (no-op alias).[/dim]")
                    continue
                if textwrap.dedent(opt_data["code"]).strip() == textwrap.dedent(best_match.snippet).strip(): continue

                if not ci:
                    if opt_data.get("cached"): console.print("[dim]Using cached...[/dim]")
                    patcher.show_diff(best_match, opt_data)
                
                if ci or allow_edit or patcher.ask_confirmation():
                    if patcher.apply_patch(best_match, opt_data["code"]):
                        if not ci: console.print(f"[green]Applied {best_match.rule_id}[/green]")
                        if test_cmd:
                            test_result = run_tests(test_cmd)
                            if not test_result.get("ok", False):
                                if ci or rollback_on_fail or Confirm.ask("[bold red]Tests failed! Rollback?[/bold red]", default=True):
                                    rollback_count += 1
                                    console.print("[yellow]Rollback applied after test failure.[/yellow]")
                                    patcher.rollback()
                                    optimizer.mark_failed(textwrap.dedent(best_match.snippet), best_match.rule_id, opt_data.get("model", ""))
                                    test_stdout = str(test_result.get("stdout", ""))
                                    test_stderr = str(test_result.get("stderr", ""))
                                    if test_stdout or test_stderr:
                                        console.print(Panel(
                                            (test_stdout + "\n" + test_stderr).strip(),
                                            title="Test Output",
                                            border_style="red"
                                        ))
                                    if repair_mode:
                                        with open(file_path, "r") as f:
                                            file_content = f.read()
                                        repair = optimizer.repair_file(
                                            file_content,
                                            (test_stdout + "\n" + test_stderr).strip()
                                        )
                                        if repair and repair.get("code"):
                                            if patcher.apply_full_rewrite(repair["code"]):
                                                if not ci:
                                                    console.print("[green]Applied repair mode rewrite[/green]")
                                                repair_tests = run_tests(test_cmd)
                                                if not repair_tests.get("ok", False):
                                                    rollback_count += 1
                                                    console.print("[yellow]Rollback applied after repair failure.[/yellow]")
                                                    patcher.rollback()
                                                    optimizer.mark_failed(file_content, "repair_mode", repair.get("model", ""))
                                                else:
                                                    changes_in_pass += 1
                                                    file_changed = True
                                                    any_changes_overall = True
                                                    patcher = CodePatcher(file_path)
                                    continue
                        
                        if git_branch:
                            git_command(["add", file_path])
                            git_command(["commit", "-m", f"OptiCode: {best_match.rule_id} in {file_path}"])

                        changes_in_pass += 1
                        file_changed = True
                        any_changes_overall = True
                        patcher = CodePatcher(file_path)
                        restart_pass = True
                        break

            if restart_pass:
                current_pass += 1
                continue

            if changes_in_pass == 0: break
            current_pass += 1
        
        if file_changed:
            modified_files_count += 1
            final_patcher = CodePatcher(file_path)
            final_patcher.finalize_imports()

    table = Table(title="Session Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Total Tokens", str(optimizer.total_tokens))
    table.add_row("Total Cost", f"${optimizer.total_cost:.4f}")
    table.add_row("Files Modified", str(modified_files_count))
    table.add_row("No-op Skipped", str(noop_count))
    table.add_row("Rules Skipped", str(skipped_count))
    table.add_row("Rollbacks", str(rollback_count))
    table.add_row("Local Calls", str(optimizer.local_calls))
    table.add_row("Remote Calls", str(optimizer.remote_calls))
    table.add_row("Verify Calls", str(optimizer.verify_calls))
    table.add_row("Remote Skipped (%)", str(optimizer.remote_skipped_due_to_percent))
    table.add_row("Decision Calls", str(optimizer.decision_calls))
    console.print(table)

if __name__ == "__main__":
    app()
