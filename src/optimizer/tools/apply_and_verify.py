import os
import subprocess
from typing import List, Optional

from optimizer.execution.runners import run_command
from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult
from optimizer.tools.deterministic_heavy_compute import apply_change_for_target, infer_target_from_text


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
