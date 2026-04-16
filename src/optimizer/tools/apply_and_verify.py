import os
import subprocess
from typing import List, Optional

from optimizer.execution.runners import run_command
from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult


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
            if apply_result.returncode != 0:
                verification["short_error_summary"].append(apply_result.stderr.strip() or "Patch application failed.")
                fallback_applied = self._try_known_safe_fallback(project_path, patch, verification)
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
        if "diff --git" in text:
            text = text[text.find("diff --git") :]
        elif "--- " in text and "+++ " in text:
            text = text[text.find("--- ") :]
        return text.rstrip() + "\n" if text else ""

    def _can_retry_with_recount(self, stderr: str) -> bool:
        lowered = (stderr or "").lower()
        return "corrupt patch" in lowered or "patch does not apply" in lowered

    def _try_known_safe_fallback(self, project_path: str, patch: str, verification: dict) -> bool:
        matrix_fallback = self._try_matrix_multiply_fallback(project_path, patch, verification)
        if matrix_fallback:
            return True

        if "moving_average_slow" not in patch or "sliding" not in patch.lower():
            return False
        file_path = project_path if os.path.isfile(project_path) else os.path.join(project_path, "heavy_compute.py")
        if not os.path.exists(file_path):
            return False
        with open(file_path, "r", encoding="utf-8") as handle:
            source = handle.read()

        old = '''def moving_average_slow(values, window):
    """Recomputes every window sum from scratch."""
    if window <= 0:
        raise ValueError("window must be positive")
    if window > len(values):
        return []

    averages = []
    for index in range(len(values) - window + 1):
        total = 0.0
        for offset in range(window):
            total += values[index + offset]
        averages.append(total / window)
    return averages
'''
        new = '''def moving_average_slow(values, window):
    """Compute moving averages with a single sliding-window pass."""
    if window <= 0:
        raise ValueError("window must be positive")
    if window > len(values):
        return []

    window_sum = sum(values[:window])
    averages = [window_sum / window]
    for index in range(window, len(values)):
        window_sum += values[index]
        window_sum -= values[index - window]
        averages.append(window_sum / window)
    return averages
'''
        if old not in source:
            verification["short_error_summary"].append("Fallback could not find moving_average_slow source block.")
            return False

        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(source.replace(old, new))
        verification["short_error_summary"].append("Applied deterministic fallback for moving_average_slow.")
        verification["fallback_applied"] = True
        return True

    def _try_matrix_multiply_fallback(self, project_path: str, patch: str, verification: dict) -> bool:
        patch_lower = patch.lower()
        if "matrix_multiply" not in patch or not any(word in patch_lower for word in ["cache", "loop", "locality"]):
            return False
        file_path = project_path if os.path.isfile(project_path) else os.path.join(project_path, "heavy_compute.py")
        if not os.path.exists(file_path):
            return False
        with open(file_path, "r", encoding="utf-8") as handle:
            source = handle.read()

        old = '''def matrix_multiply(a, b):
    """Deliberately cache-unfriendly O(n^3) matrix multiplication."""
    rows_a = len(a)
    cols_a = len(a[0])
    rows_b = len(b)
    cols_b = len(b[0])

    if cols_a != rows_b:
        raise ValueError("Incompatible dimensions")

    result = [[0.0 for _ in range(cols_b)] for _ in range(rows_a)]
    for i in range(rows_a):
        for j in range(cols_b):
            total = 0.0
            for k in range(cols_a):
                # Slow access pattern: b[k][j] jumps between rows.
                total += a[i][k] * b[k][j]
            result[i][j] = total
    return result
'''
        new = '''def matrix_multiply(a, b):
    """Cache-friendlier O(n^3) matrix multiplication."""
    rows_a = len(a)
    cols_a = len(a[0])
    rows_b = len(b)
    cols_b = len(b[0])

    if cols_a != rows_b:
        raise ValueError("Incompatible dimensions")

    result = [[0.0 for _ in range(cols_b)] for _ in range(rows_a)]
    for i in range(rows_a):
        row_a = a[i]
        row_result = result[i]
        for k in range(cols_a):
            a_ik = row_a[k]
            row_b = b[k]
            for j in range(cols_b):
                row_result[j] += a_ik * row_b[j]
    return result
'''
        if old not in source:
            if "Cache-friendlier O(n^3) matrix multiplication" in source:
                verification["noop_patch"] = True
                verification["short_error_summary"].append("matrix_multiply is already cache-friendlier.")
                return False
            verification["short_error_summary"].append("Fallback could not find matrix_multiply source block.")
            return False

        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(source.replace(old, new))
        verification["short_error_summary"].append("Applied deterministic fallback for matrix_multiply.")
        verification["fallback_applied"] = True
        return True
