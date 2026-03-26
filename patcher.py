import difflib
import ast
import os
import re
from typing import Dict, Optional
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
        self.backup_lines = list(self.lines)

    def rollback(self) -> bool:
        """Restores the file to the previous state."""
        try:
            with open(self.file_path, "w") as f:
                f.writelines(self.backup_lines)
            self.lines = list(self.backup_lines)
            return True
        except Exception as e:
            console.print(f"[bold red]Rollback failed: {e}[/bold red]")
            return False

    def show_diff(self, match: CodeMatch, opt_data: dict):
        optimized_code = opt_data["code"]
        indented_opt = self._indent_code(optimized_code, match.indent)
        original = match.snippet
        
        console.print(Panel(
            f"[bold cyan]Focus:[/bold cyan] {opt_data.get('focus', 'N/A')}\n"
            f"[bold green]Estimated Speedup:[/bold green] [bold yellow]{opt_data.get('speedup', 'N/A')}[/bold yellow]\n\n"
            f"[italic]{opt_data.get('reasoning', 'N/A')}[/italic]",
            title="Analysis",
            border_style="blue"
        ))

        diff = difflib.ndiff(original.splitlines(), indented_opt.splitlines())
        diff_text = "\n".join(diff)
        
        console.print(Panel(
            Syntax(diff_text, "diff", theme="monokai", line_numbers=False),
            title=f"Optimization Suggestion: [bold cyan]{match.rule_id}[/bold cyan] (Lines {match.start_line}-{match.end_line})",
            subtitle=f"File: {self.file_path}"
        ))

    def _indent_code(self, code: str, indent_level: int) -> str:
        lines = code.splitlines()
        indented = [(" " * indent_level) + line if line.strip() else "" for line in lines]
        return "\n".join(indented)

    def unfold_code(self, code: str, folded_parts: Dict[str, str]) -> str:
        """Replaces folded block markers with original code blocks."""
        unfolded = code
        # Pattern to match the string constant placeholder we used in _fold_snippet
        # The pattern looks for '[OPTICODE_FOLDED_BLOCK: <UUID>]'
        # We need to find the line that contains it, and replace it with the original lines,
        # preserving the indentation of the placeholder.
        
        lines = unfolded.splitlines()
        new_lines = []
        for line in lines:
            # Pattern to match '[OPTICODE_FOLDED_BLOCK: <UUID>]' or "[OPTICODE_FOLDED_BLOCK: <UUID>]"
            match = re.search(r"[\'\"]\[OPTICODE_FOLDED_BLOCK:\s*([\w-]+)\][\'\"]", line)
            
            if match:
                u_id = match.group(1)
                if u_id in folded_parts:
                    # Capture the indentation before the placeholder
                    indent_match = re.match(r"^\s*", line)
                    indent_str = indent_match.group(0) if indent_match else ""
                    
                    original_block = folded_parts[u_id]
                    # Indent each line of the original block to match the placeholder
                    # Note: original_block might already have some internal relative indentation
                    indented_lines = []
                    for b_line in original_block.splitlines():
                        if b_line.strip():
                            indented_lines.append(indent_str + b_line)
                        else:
                            indented_lines.append("")
                    new_lines.append("\n".join(indented_lines))
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        return "\n".join(new_lines)

    def apply_patch(self, match: CodeMatch, optimized_code: str, folded_parts: Optional[Dict[str, str]] = None) -> bool:
        self.backup_lines = list(self.lines)
        start_idx = match.start_line - 1
        end_idx = match.end_line
        
        final_code = optimized_code
        if folded_parts:
            final_code = self.unfold_code(final_code, folded_parts)

        indented_lines = [l + "\n" for l in self._indent_code(final_code, match.indent).splitlines()]
        
        temp_lines = list(self.lines)
        temp_lines[start_idx:end_idx] = indented_lines
        temp_source = "".join(temp_lines)
        
        try:
            ast.parse(temp_source)
            self.lines = temp_lines
            with open(self.file_path, "w") as f:
                f.writelines(self.lines)
            return True
        except SyntaxError as e:
            console.print(f"[bold red]Safety check failed: LLM generated invalid Python code ({e}). Skipping.[/bold red]")
            return False

    def apply_full_rewrite(self, optimized_code: str) -> bool:
        self.backup_lines = list(self.lines)
        temp_source = optimized_code
        try:
            ast.parse(temp_source)
            with open(self.file_path, "w") as f:
                f.write(temp_source if temp_source.endswith("\n") else temp_source + "\n")
            self.lines = temp_source.splitlines(keepends=True)
            return True
        except SyntaxError as e:
            console.print(f"[bold red]Safety check failed: LLM generated invalid Python code ({e}). Skipping.[/bold red]")
            return False

    def finalize_imports(self):
        """Moves all nested imports to the top of the file, following PEP8."""
        source = "".join(self.lines)
        try:
            tree = ast.parse(source)
        except:
            return

        found_imports = []
        lines_to_remove = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_stmt = ast.get_source_segment(source, node)
                if import_stmt:
                    found_imports.append(import_stmt)
                    node_start = node.lineno or 1
                    node_end = node.end_lineno or node_start
                    for i in range(node_start, node_end + 1):
                        lines_to_remove.add(i - 1)

        if not found_imports:
            return

        # Deduplicate while preserving order
        unique_imports = []
        for imp in found_imports:
            if imp not in unique_imports:
                unique_imports.append(imp)

        # Remove old import lines and clean up the code
        new_lines = [line for i, line in enumerate(self.lines) if i not in lines_to_remove]
        
        # Add them to the top (with a newline)
        final_code = [imp + "\n" for imp in unique_imports] + ["\n"] + new_lines
        
        try:
            with open(self.file_path, "w") as f:
                f.writelines(final_code)
            self.lines = final_code
        except Exception as e:
            console.print(f"[bold red]Failed to finalize imports: {e}[/bold red]")

    def ask_confirmation(self) -> bool:
        return Confirm.ask("Apply this optimization?", default=False)
