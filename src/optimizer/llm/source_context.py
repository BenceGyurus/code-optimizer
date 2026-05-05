import ast
import os
from dataclasses import dataclass
from typing import Iterable

from optimizer.orchestrator.state_machine import State


@dataclass(frozen=True)
class DefinitionSummary:
    name: str
    kind: str
    start_line: int
    end_line: int
    score: int
    tags: tuple[str, ...]
    calls: tuple[str, ...]


class SourceContextBuilder:
    """Builds compact, state-aware source context for optimization prompts."""

    def __init__(
        self,
        project_path: str,
        display_path: str | None = None,
        patch_path: str | None = None,
        max_chars: int = 12000,
    ):
        self.project_path = project_path
        self.display_path = display_path or project_path
        self.patch_path = patch_path or os.path.basename(project_path)
        self.max_chars = max_chars
        self.source = self._read_source(project_path)
        self.lines = self.source.splitlines()
        self.tree = self._parse_source(self.source)
        self.definitions = self._collect_definitions()
        self.imports = self._collect_imports()
        self.globals = self._collect_globals()

    def render(self, current_state: State, target: str | None = None) -> str:
        if not self.source:
            return "No source context provided."
        if self.tree is None:
            return self._fallback_context()

        parts = [self._outline(current_state, target)]
        target_definition = self._find_definition(target)

        if current_state in {State.ANALYSIS_READY, State.PATCH_PROPOSED}:
            top_candidates = self._top_candidates(1)
            focus = target_definition or (top_candidates[0] if top_candidates else None)
            if focus is not None:
                parts.append(self._exact_excerpt_section("Focused exact source for patching", focus))
                parts.extend(self._related_excerpt_sections(focus))
        elif current_state in {State.PROFILE_READY, State.BASELINE_READY}:
            for candidate in self._top_candidates(3):
                parts.append(self._preview_section(candidate, max_lines=42))

        return self._fit("\n\n".join(part for part in parts if part.strip()))

    def _fallback_context(self) -> str:
        content = self.source
        truncated = len(content) > self.max_chars
        if truncated:
            content = content[: self.max_chars] + "\n# ... truncated ..."
        return f"File: {self.display_path}\nPatch path: {self.patch_path}\n```python\n{content}\n```"

    def _outline(self, current_state: State, target: str | None) -> str:
        definitions = sorted(self.definitions, key=lambda item: (item.start_line, item.name))
        top = self._top_candidates(6)
        lines = [
            f"File: {self.display_path}",
            f"Patch path: {self.patch_path}",
            "Source context mode: compact AST outline plus focused excerpts.",
            f"State: {current_state.name}",
            f"Current target: {target or 'None'}",
            f"Total lines: {len(self.lines)}",
            f"Imports: {', '.join(self.imports[:12]) if self.imports else 'none'}",
            f"Globals/constants: {', '.join(self.globals[:12]) if self.globals else 'none'}",
            "Definitions:",
        ]
        for definition in definitions[:42]:
            lines.append(
                "- "
                f"{definition.kind} {definition.name} "
                f"lines {definition.start_line}-{definition.end_line} "
                f"score={definition.score} "
                f"tags={','.join(definition.tags) or 'none'} "
                f"calls={','.join(definition.calls[:8]) or 'none'}"
            )
        if len(definitions) > 42:
            lines.append(f"- ... {len(definitions) - 42} more definitions omitted")
        lines.append("Top optimization candidates:")
        for index, definition in enumerate(top, start=1):
            lines.append(
                f"{index}. {definition.name} lines {definition.start_line}-{definition.end_line} "
                f"score={definition.score} tags={','.join(definition.tags) or 'none'}"
            )
        lines.append(
            "Use exact excerpt sections for patches; do not patch code that is only present in the outline."
        )
        return "\n".join(lines)

    def _exact_excerpt_section(self, title: str, definition: DefinitionSummary) -> str:
        return (
            f"{title}:\n"
            f"File: {self.display_path}\n"
            f"Patch path: {self.patch_path}\n"
            f"Symbol: {definition.name} lines {definition.start_line}-{definition.end_line}\n"
            "```python\n"
            f"{self._definition_source(definition)}\n"
            "```"
        )

    def _preview_section(self, definition: DefinitionSummary, max_lines: int) -> str:
        source_lines = self._definition_source(definition).splitlines()
        truncated = len(source_lines) > max_lines
        preview = "\n".join(source_lines[:max_lines])
        if truncated:
            preview += "\n# ... preview truncated; select this target to receive the exact focused excerpt ..."
        return (
            "Candidate preview:\n"
            f"File: {self.display_path}\n"
            f"Patch path: {self.patch_path}\n"
            f"Symbol: {definition.name} lines {definition.start_line}-{definition.end_line}\n"
            "```python\n"
            f"{preview}\n"
            "```"
        )

    def _related_excerpt_sections(self, definition: DefinitionSummary) -> list[str]:
        sections: list[str] = []
        available = max(0, self.max_chars - len(self._exact_excerpt_section("", definition)))
        for related in self._related_definitions(definition):
            section = self._exact_excerpt_section("Related exact source", related)
            if len(section) > available or len(section) > 2200:
                continue
            sections.append(section)
            available -= len(section)
            if len(sections) >= 2:
                break
        return sections

    def _related_definitions(self, definition: DefinitionSummary) -> list[DefinitionSummary]:
        call_names = set(definition.calls)
        related: list[DefinitionSummary] = []
        for candidate in self.definitions:
            short_name = candidate.name.rsplit(".", 1)[-1]
            if candidate == definition:
                continue
            if candidate.name in call_names or short_name in call_names:
                related.append(candidate)
        return sorted(related, key=lambda item: (item.end_line - item.start_line, item.start_line))

    def _fit(self, text: str) -> str:
        if len(text) <= self.max_chars:
            return text
        marker = "\n\n# Source context truncated to fit prompt budget."
        return text[: max(0, self.max_chars - len(marker))].rstrip() + marker

    def _definition_source(self, definition: DefinitionSummary) -> str:
        return "\n".join(self.lines[definition.start_line - 1 : definition.end_line])

    def _find_definition(self, target: str | None) -> DefinitionSummary | None:
        normalized = (target or "").strip()
        if not normalized or normalized.lower() in {"none", "unspecified", "unknown", "hot path"}:
            return None
        for definition in self.definitions:
            if definition.name == normalized:
                return definition
        for definition in self.definitions:
            if definition.name.rsplit(".", 1)[-1] == normalized:
                return definition
        lowered = normalized.lower()
        for definition in self.definitions:
            if definition.name.lower() == lowered or definition.name.rsplit(".", 1)[-1].lower() == lowered:
                return definition
        return None

    def _top_candidates(self, count: int) -> list[DefinitionSummary]:
        return sorted(
            (definition for definition in self.definitions if definition.kind in {"function", "method"}),
            key=lambda item: (item.score, item.end_line - item.start_line),
            reverse=True,
        )[:count]

    def _collect_definitions(self) -> list[DefinitionSummary]:
        if self.tree is None:
            return []
        definitions: list[DefinitionSummary] = []
        for node in self.tree.body:
            if isinstance(node, ast.ClassDef):
                definitions.append(self._definition_summary(node, node.name, "class"))
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        definitions.append(self._definition_summary(child, f"{node.name}.{child.name}", "method"))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.append(self._definition_summary(node, node.name, "function"))
        return definitions

    def _definition_summary(self, node: ast.AST, name: str, kind: str) -> DefinitionSummary:
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start)
        metrics = _DefinitionMetrics()
        metrics.visit(node)
        tags = _tags_for_metrics(metrics, end - start + 1)
        score = _score_for_metrics(metrics, end - start + 1)
        return DefinitionSummary(
            name=name,
            kind=kind,
            start_line=start,
            end_line=end,
            score=score,
            tags=tuple(tags),
            calls=tuple(sorted(metrics.calls))[:14],
        )

    def _collect_imports(self) -> list[str]:
        if self.tree is None:
            return []
        imports: list[str] = []
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = "." * node.level + (node.module or "")
                imports.extend(f"{module}.{alias.name}".strip(".") for alias in node.names)
        return imports

    def _collect_globals(self) -> list[str]:
        if self.tree is None:
            return []
        names: list[str] = []
        for node in self.tree.body:
            if isinstance(node, ast.Assign):
                names.extend(_assignment_names(node.targets))
            elif isinstance(node, ast.AnnAssign):
                names.extend(_assignment_names([node.target]))
        return names

    @staticmethod
    def _read_source(path: str) -> str:
        if not os.path.isfile(path):
            return ""
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
        except UnicodeDecodeError:
            return ""

    @staticmethod
    def _parse_source(source: str) -> ast.AST | None:
        try:
            return ast.parse(source)
        except SyntaxError:
            return None


class _DefinitionMetrics(ast.NodeVisitor):
    def __init__(self) -> None:
        self.loop_count = 0
        self.max_loop_depth = 0
        self.current_loop_depth = 0
        self.if_count = 0
        self.call_count = 0
        self.binop_count = 0
        self.comprehension_count = 0
        self.assignment_count = 0
        self.calls: set[str] = set()

    def visit_For(self, node: ast.For) -> None:
        self._visit_loop(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_loop(node)

    def visit_While(self, node: ast.While) -> None:
        self._visit_loop(node)

    def visit_If(self, node: ast.If) -> None:
        self.if_count += 1
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.call_count += 1
        call_name = _call_name(node.func)
        if call_name:
            self.calls.add(call_name)
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        self.binop_count += 1
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self.comprehension_count += 1
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.assignment_count += 1
        self.generic_visit(node)

    def _visit_loop(self, node: ast.AST) -> None:
        self.loop_count += 1
        self.current_loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.current_loop_depth)
        self.generic_visit(node)
        self.current_loop_depth -= 1


def _tags_for_metrics(metrics: _DefinitionMetrics, line_count: int) -> list[str]:
    tags: list[str] = []
    if metrics.max_loop_depth >= 2:
        tags.append("nested_loops")
    elif metrics.loop_count:
        tags.append("loop")
    if metrics.binop_count >= 8 and metrics.loop_count:
        tags.append("numeric_kernel")
    if metrics.comprehension_count >= 2 or metrics.assignment_count >= 10:
        tags.append("allocation_heavy")
    if metrics.if_count >= 5:
        tags.append("branch_heavy")
    if metrics.call_count >= 12:
        tags.append("call_heavy")
    if line_count >= 80:
        tags.append("large")
    return tags


def _score_for_metrics(metrics: _DefinitionMetrics, line_count: int) -> int:
    return (
        metrics.loop_count * 5
        + metrics.max_loop_depth * 8
        + metrics.binop_count
        + metrics.comprehension_count * 4
        + metrics.if_count * 2
        + min(line_count, 120) // 8
    )


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _assignment_names(targets: Iterable[ast.AST]) -> list[str]:
    names: list[str] = []
    for target in targets:
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            names.extend(_assignment_names(target.elts))
    return names
