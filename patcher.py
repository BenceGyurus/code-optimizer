import difflib
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.prompt import Confirm
from hunter import CodeMatch

console = Console()

class CodePatcher:
    def __init__(self, file_path: str):
        self.file_path = file_path
        with open(file_path, "r") as f:
            self.lines = f.readlines()

    def show_diff(self, match: CodeMatch, opt_data: dict):
        optimized_code = opt_data["code"]
        original = match.snippet
        
        # Metadata panel
        console.print(Panel(
            f"[bold cyan]Focus:[/bold cyan] {opt_data.get('focus', 'N/A')}\n"
            f"[bold green]Estimated Speedup:[/bold green] [bold yellow]{opt_data.get('speedup', 'N/A')}[/bold yellow]\n\n"
            f"[italic]{opt_data.get('reasoning', 'N/A')}[/italic]",
            title="Analysis",
            border_style="blue"
        ))

        # Diff panel
        diff = difflib.ndiff(original.splitlines(), optimized_code.splitlines())
        diff_text = "\n".join(diff)
        
        console.print(Panel(
            Syntax(diff_text, "diff", theme="monokai", line_numbers=False),
            title=f"Optimization Suggestion: [bold cyan]{match.rule_id}[/bold cyan] (Lines {match.start_line}-{match.end_line})",
            subtitle=f"File: {self.file_path}"
        ))

    def apply_patch(self, match: CodeMatch, optimized_code: str) -> bool:
        """Replace the lines in the original file, ensuring correct base indentation."""
        start_idx = match.start_line - 1
        end_idx = match.end_line
        
        # Split the optimized code into lines
        opt_lines = optimized_code.splitlines()
        
        # Heuristic: Find the minimum indentation in the LLM's response (ignoring empty lines)
        non_empty_opt_lines = [l for l in opt_lines if l.strip()]
        if not non_empty_opt_lines:
            return False
            
        min_opt_indent = min(len(l) - len(l.lstrip()) for l in non_empty_opt_lines)
        
        # We want to adjust the code so that its base indentation is match.indent
        indented_lines = []
        for line in opt_lines:
            if not line.strip():
                indented_lines.append("\n")
                continue
                
            # Relative indentation within the LLM's block
            relative_indent = (len(line) - len(line.lstrip())) - min_opt_indent
            # Final indentation = base match.indent + relative
            final_line = (" " * (match.indent + relative_indent)) + line.lstrip()
            indented_lines.append(final_line + "\n")
            
        self.lines[start_idx:end_idx] = indented_lines
        
        try:
            with open(self.file_path, "w") as f:
                f.writelines(self.lines)
            return True
        except Exception as e:
            console.print(f"[bold red]Error writing to file: {e}[/bold red]")
            return False

    def ask_confirmation(self) -> bool:
        return Confirm.ask("Apply this optimization?", default=False)
