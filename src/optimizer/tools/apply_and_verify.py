import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from optimizer.execution.runners import run_command
from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult
from optimizer.tools.deterministic_heavy_compute import apply_change_for_target, infer_target_from_text


@dataclass(frozen=True)
class _StructuredPatchOperation:
    kind: str
    path: str
    move_to: Optional[str]
    hunks: list[list[tuple[str, str]]]


class ApplyAndVerifyTool(Tool):
    """Applies a unified diff and verifies it with build/test commands."""

    @property
    def name(self) -> str:
        return "apply_and_verify"

    @property
    def allowed_states(self) -> List[State]:
        return [State.PATCH_PROPOSED, State.PATCH_APPLIED]

    def execute(
        self,
        patch: str = "",
        build_cmd: Optional[str] = None,
        test_cmd: Optional[str] = None,
        project_path: str = ".",
        current_state: Optional[str] = None,
        patch_cwd: Optional[str] = None,
        allow_deterministic_fallback: bool = False,
        **_: object,
    ) -> ToolResult:
        patch = self._clean_patch(patch)
        verification = {
            "build_success": build_cmd is None,
            "test_success": test_cmd is None,
            "failing_tests": [],
            "short_error_summary": [],
            "rollback_performed": False,
            "patch_applied": False,
            "noop_patch": False,
            "fallback_allowed": bool(allow_deterministic_fallback),
        }
        patch_cwd = patch_cwd or self._patch_cwd(project_path, patch)

        if current_state == State.PATCH_APPLIED.name:
            return self._verify(project_path, build_cmd, test_cmd, verification, patch, patch_cwd)

        if not patch.strip():
            verification["noop_patch"] = True
            verification["short_error_summary"].append("No patch was provided; no files were changed.")
            return ToolResult(
                success=True,
                output={"message": "No patch provided; returning to analysis.", "verification_result": verification},
                next_state=State.ANALYSIS_READY,
                metadata=verification,
            )

        if patch:
            apply_error = self._apply_patch(patch, project_path, patch_cwd)
            if apply_error is not None:
                verification["short_error_summary"].append(apply_error)
                fallback_applied = False
                if allow_deterministic_fallback:
                    fallback_applied = self._try_known_safe_fallback(project_path, patch, verification)
                else:
                    verification["short_error_summary"].append("Deterministic fallback disabled; measuring model patch only.")
                if not fallback_applied:
                    return ToolResult(
                        success=True,
                        output={"message": "Patch could not be applied; returning to analysis.", "verification_result": verification},
                        next_state=State.ANALYSIS_READY,
                        metadata=verification,
                    )
            verification["patch_applied"] = True

        return ToolResult(
            success=True,
            output={"message": "Patch applied. Run apply_and_verify again from PATCH_APPLIED to verify.", "verification_result": verification},
            next_state=State.PATCH_APPLIED,
            metadata=verification,
        )

    def _verify(
        self,
        project_path: str,
        build_cmd: Optional[str],
        test_cmd: Optional[str],
        verification: dict,
        patch: str = "",
        patch_cwd: Optional[str] = None,
    ) -> ToolResult:
        if build_cmd:
            build = run_command(build_cmd, cwd=project_path)
            verification["build_success"] = build.returncode == 0
            if build.returncode != 0:
                verification["short_error_summary"].append((build.stderr or build.stdout).strip()[:1000])
                self._rollback_patch(project_path, patch, verification, patch_cwd)
                return ToolResult(success=False, output={"verification_result": verification}, metadata=verification)

        if test_cmd:
            test = run_command(test_cmd, cwd=project_path)
            verification["test_success"] = test.returncode == 0
            if test.returncode != 0:
                verification["short_error_summary"].append((test.stderr or test.stdout).strip()[:1000])
                self._rollback_patch(project_path, patch, verification, patch_cwd)
                return ToolResult(success=False, output={"verification_result": verification}, metadata=verification)

        return ToolResult(success=True, output={"verification_result": verification}, next_state=State.VERIFIED, metadata=verification)

    def _rollback_patch(self, project_path: str, patch: str, verification: dict, patch_cwd: Optional[str] = None) -> None:
        if not patch:
            return
        if self._is_structured_patch(patch):
            rollback_error = self._apply_structured_patch(
                patch_cwd or self._patch_cwd(project_path, patch),
                patch,
                reverse=True,
            )
            verification["rollback_performed"] = rollback_error is None
            if rollback_error:
                verification["short_error_summary"].append(f"Rollback failed: {rollback_error}")
            return
        rollback = subprocess.run(
            ["git", "apply", "-R", "-"],
            input=patch,
            text=True,
            capture_output=True,
            cwd=patch_cwd or self._patch_cwd(project_path, patch),
            check=False,
        )
        verification["rollback_performed"] = rollback.returncode == 0

    def _patch_cwd(self, project_path: str, patch: str) -> str:
        if os.path.isdir(project_path):
            return project_path
        repo_root = self._git_root(project_path)
        if repo_root:
            return repo_root
        return os.path.dirname(os.path.abspath(project_path)) or "."

    def _git_root(self, path: str) -> Optional[str]:
        cwd = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
        process = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            capture_output=True,
            cwd=cwd or ".",
            check=False,
        )
        if process.returncode == 0:
            return process.stdout.strip()
        return None

    def _clean_patch(self, patch: str) -> str:
        text = (patch or "").strip()
        if "```diff" in text:
            text = text.split("```diff", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            fenced = text.split("```", 1)[1].split("```", 1)[0].strip()
            if "diff --git" in fenced or fenced.startswith("--- "):
                text = fenced
        if "*** Begin Patch" in text:
            text = text[text.find("*** Begin Patch") :]
            end = text.rfind("*** End Patch")
            if end >= 0:
                text = text[: end + len("*** End Patch")]
        elif "diff --git" in text:
            text = text[text.find("diff --git") :]
        elif "--- " in text and "+++ " in text:
            text = text[text.find("--- ") :]
        return text.rstrip() + "\n" if text else ""

    def _can_retry_with_recount(self, stderr: str) -> bool:
        lowered = (stderr or "").lower()
        return "corrupt patch" in lowered or "patch does not apply" in lowered

    def _try_known_safe_fallback(self, project_path: str, patch: str, verification: dict) -> bool:
        target = infer_target_from_text(patch)
        if not target:
            return False

        change = apply_change_for_target(project_path, target)
        if change is None:
            verification["short_error_summary"].append(f"Fallback could not build deterministic patch for {target}.")
            return False
        if not change.changed:
            verification["noop_patch"] = True
            verification["short_error_summary"].append(f"{target} is already optimized by deterministic fallback.")
            return False

        verification["short_error_summary"].append(f"Applied deterministic fallback for {target}.")
        verification["fallback_applied"] = True
        return True

    def _apply_patch(self, patch: str, project_path: str, patch_cwd: str) -> Optional[str]:
        if self._is_structured_patch(patch):
            return self._apply_structured_patch(patch_cwd, patch)

        apply_result = subprocess.run(
            ["git", "apply", "--whitespace=fix", "-"],
            input=patch,
            text=True,
            capture_output=True,
            cwd=patch_cwd,
            check=False,
        )
        if apply_result.returncode != 0 and self._can_retry_with_recount(apply_result.stderr):
            apply_result = subprocess.run(
                ["git", "apply", "--recount", "--whitespace=fix", "-"],
                input=patch,
                text=True,
                capture_output=True,
                cwd=patch_cwd,
                check=False,
            )
        if apply_result.returncode == 0:
            return None
        return apply_result.stderr.strip() or "Patch application failed."

    def _is_structured_patch(self, patch: str) -> bool:
        return patch.lstrip().startswith("*** Begin Patch")

    def _apply_structured_patch(self, root: str, patch: str, reverse: bool = False) -> Optional[str]:
        try:
            operations = self._parse_structured_patch(patch)
            ordered_operations = list(reversed(operations)) if reverse else operations
            for operation in ordered_operations:
                self._apply_structured_operation(root, operation, reverse=reverse)
        except ValueError as exc:
            return str(exc)
        return None

    def _parse_structured_patch(self, patch: str) -> list[_StructuredPatchOperation]:
        lines = (patch or "").splitlines()
        if not lines or lines[0].strip() != "*** Begin Patch":
            raise ValueError("Structured patch must start with *** Begin Patch.")

        operations: list[_StructuredPatchOperation] = []
        index = 1
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if not stripped:
                index += 1
                continue
            if stripped == "*** End Patch":
                index += 1
                while index < len(lines):
                    if lines[index].strip() not in {"", "*** End Patch"}:
                        raise ValueError("Unexpected trailing content after structured patch.")
                    index += 1
                return operations

            kind: Optional[str] = None
            path: Optional[str] = None
            move_to: Optional[str] = None
            if line.startswith("*** Update File: "):
                kind = "update"
                path = line[len("*** Update File: ") :].strip()
                index += 1
                if index < len(lines) and lines[index].startswith("*** Move to: "):
                    move_to = lines[index][len("*** Move to: ") :].strip()
                    index += 1
            elif line.startswith("*** Add File: "):
                kind = "add"
                path = line[len("*** Add File: ") :].strip()
                index += 1
            elif line.startswith("*** Delete File: "):
                kind = "delete"
                path = line[len("*** Delete File: ") :].strip()
                index += 1
            else:
                raise ValueError(f"Unsupported structured patch line: {line}")

            hunks, index = self._parse_structured_hunks(lines, index)
            operations.append(_StructuredPatchOperation(kind=kind, path=path, move_to=move_to, hunks=hunks))

        raise ValueError("Structured patch is missing *** End Patch.")

    def _parse_structured_hunks(self, lines: list[str], start: int) -> tuple[list[list[tuple[str, str]]], int]:
        hunks: list[list[tuple[str, str]]] = []
        current_hunk: list[tuple[str, str]] = []
        index = start

        while index < len(lines):
            line = lines[index]
            if line.startswith("*** ") and not line.startswith("*** End of File"):
                break
            if line == "@@" or line.startswith("@@ "):
                if current_hunk:
                    hunks.append(current_hunk)
                    current_hunk = []
                index += 1
                continue
            if line == "*** End of File":
                index += 1
                continue
            if not line:
                raise ValueError("Structured patch contains an invalid blank line.")

            prefix = line[0]
            if prefix not in {"+", "-", " "}:
                raise ValueError(f"Unsupported structured hunk line: {line}")
            current_hunk.append((prefix, line[1:]))
            index += 1

        if current_hunk:
            hunks.append(current_hunk)
        return hunks, index

    def _apply_structured_operation(self, root: str, operation: _StructuredPatchOperation, reverse: bool = False) -> None:
        current_path = self._resolve_structured_path(root, operation.move_to if reverse and operation.move_to else operation.path)
        final_path = self._resolve_structured_path(root, operation.path if reverse else (operation.move_to or operation.path))
        should_exist_after = operation.kind != "delete"
        if reverse:
            should_exist_after = operation.kind != "add"

        if operation.kind == "add" and not reverse and os.path.exists(current_path):
            raise ValueError(f"Structured add file already exists: {operation.path}")
        if operation.kind == "delete" and reverse and os.path.exists(final_path):
            raise ValueError(f"Structured delete rollback would overwrite existing file: {operation.path}")

        if os.path.exists(current_path):
            with open(current_path, "r", encoding="utf-8") as handle:
                current_lines = handle.read().splitlines()
        else:
            current_lines = []

        if operation.kind in {"update", "delete"} and not reverse and not os.path.exists(current_path):
            raise ValueError(f"Structured patch file not found: {operation.path}")
        if operation.kind == "add" and reverse and not os.path.exists(current_path):
            raise ValueError(f"Structured rollback file not found: {operation.path}")

        updated_lines = self._apply_structured_hunks(current_lines, operation.hunks, reverse=reverse)

        if not should_exist_after:
            if os.path.exists(current_path):
                os.remove(current_path)
            if current_path != final_path and os.path.exists(final_path):
                os.remove(final_path)
            return

        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        with open(final_path, "w", encoding="utf-8") as handle:
            handle.write(self._join_lines(updated_lines))
        if current_path != final_path and os.path.exists(current_path):
            os.remove(current_path)

    def _apply_structured_hunks(
        self,
        source_lines: list[str],
        hunks: list[list[tuple[str, str]]],
        reverse: bool = False,
    ) -> list[str]:
        updated_lines = list(source_lines)
        search_start = 0
        for hunk in hunks:
            old_lines = [
                line
                for kind, line in hunk
                if kind in ((" ", "+") if reverse else (" ", "-"))
            ]
            new_lines = [
                line
                for kind, line in hunk
                if kind in ((" ", "-") if reverse else (" ", "+"))
            ]
            start = self._find_hunk_start(updated_lines, old_lines, search_start)
            if start is None:
                raise ValueError("Structured patch hunk did not match the current file contents.")
            updated_lines[start : start + len(old_lines)] = new_lines
            search_start = start + len(new_lines)
        return updated_lines

    def _find_hunk_start(self, lines: list[str], old_lines: list[str], search_start: int) -> Optional[int]:
        if not old_lines:
            return min(search_start, len(lines))

        limit = len(lines) - len(old_lines) + 1
        for start in range(max(0, search_start), max(0, limit)):
            if lines[start : start + len(old_lines)] == old_lines:
                return start
        for start in range(0, max(0, limit)):
            if lines[start : start + len(old_lines)] == old_lines:
                return start
        return None

    def _resolve_structured_path(self, root: str, relative_path: str) -> str:
        candidate = os.path.abspath(os.path.join(root, relative_path))
        root_abs = os.path.abspath(root)
        if candidate != root_abs and not candidate.startswith(root_abs + os.sep):
            raise ValueError(f"Structured patch path escapes workspace: {relative_path}")
        return candidate

    def _join_lines(self, lines: list[str]) -> str:
        if not lines:
            return ""
        return "\n".join(lines) + "\n"
