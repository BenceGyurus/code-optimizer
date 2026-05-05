from pathlib import Path

from optimizer.orchestrator.state_machine import State
from optimizer.tools.apply_and_verify import ApplyAndVerifyTool


MOVING_AVERAGE_PATCH = """*** Begin Patch
*** Update File: sample_project.py
@@
-def moving_average_slow(values, window):
-    \"\"\"Return fixed-width moving averages.\"\"\"
-    if window <= 0:
-        raise ValueError(\"window must be positive\")
-    if window > len(values):
-        return []
-
-    averages = []
-    for index in range(len(values) - window + 1):
-        total = 0.0
-        for offset in range(window):
-            total += values[index + offset]
-        averages.append(total / window)
-    return averages
+def moving_average_slow(values, window):
+    \"\"\"Return fixed-width moving averages.\"\"\"
+    if window <= 0:
+        raise ValueError(\"window must be positive\")
+    if window > len(values):
+        return []
+
+    window_sum = sum(values[:window])
+    averages = [window_sum / window]
+    for index in range(window, len(values)):
+        window_sum += values[index]
+        window_sum -= values[index - window]
+        averages.append(window_sum / window)
+    return averages
*** End Patch
"""


def test_apply_and_verify_applies_begin_patch_directly(tmp_path):
    source_path = Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    project_path = tmp_path / "sample_project.py"
    project_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    patch = MOVING_AVERAGE_PATCH

    result = ApplyAndVerifyTool().execute(
        patch=patch,
        project_path=str(project_path),
        current_state=State.PATCH_PROPOSED.name,
    )

    updated = project_path.read_text(encoding="utf-8")
    verification = result.output["verification_result"]
    assert result.success is True
    assert result.next_state == State.PATCH_APPLIED
    assert verification["patch_applied"] is True
    assert verification.get("fallback_applied") is not True
    assert "window_sum = sum(values[:window])" in updated


def test_apply_and_verify_rolls_back_begin_patch_on_failed_verification(tmp_path):
    source_path = Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    project_path = tmp_path / "sample_project.py"
    original = source_path.read_text(encoding="utf-8")
    project_path.write_text(original, encoding="utf-8")

    patch = MOVING_AVERAGE_PATCH

    ApplyAndVerifyTool().execute(
        patch=patch,
        project_path=str(project_path),
        current_state=State.PATCH_PROPOSED.name,
    )

    result = ApplyAndVerifyTool().execute(
        patch=patch,
        project_path=str(project_path),
        current_state=State.PATCH_APPLIED.name,
        test_cmd='python -c "import sys; sys.exit(1)"',
    )

    verification = result.output["verification_result"]
    assert result.success is True
    assert result.next_state == State.PROFILE_READY
    assert verification["verification_failed"] is True
    assert verification["rollback_performed"] is True
    assert project_path.read_text(encoding="utf-8") == original


def test_apply_and_verify_does_not_fallback_by_default(tmp_path):
    source_path = Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    project_path = tmp_path / "sample_project.py"
    original = source_path.read_text(encoding="utf-8")
    project_path.write_text(original, encoding="utf-8")

    result = ApplyAndVerifyTool().execute(
        patch="diff --git a/sample_project.py b/sample_project.py\nnot a valid patch matrix_multiply\n",
        project_path=str(project_path),
        current_state=State.PATCH_PROPOSED.name,
    )

    verification = result.output["verification_result"]
    assert result.success is True
    assert result.next_state == State.ANALYSIS_READY
    assert verification["patch_applied"] is False
    assert verification["fallback_allowed"] is False
    assert verification.get("fallback_applied") is not True
    assert "Deterministic fallback disabled" in "; ".join(verification["short_error_summary"])
    assert project_path.read_text(encoding="utf-8") == original


def test_apply_and_verify_can_fallback_when_explicitly_enabled(tmp_path):
    source_path = Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    project_path = tmp_path / "sample_project.py"
    project_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    result = ApplyAndVerifyTool().execute(
        patch="diff --git a/sample_project.py b/sample_project.py\nnot a valid patch matrix_multiply\n",
        project_path=str(project_path),
        current_state=State.PATCH_PROPOSED.name,
        allow_deterministic_fallback=True,
    )

    verification = result.output["verification_result"]
    assert result.success is True
    assert result.next_state == State.PATCH_APPLIED
    assert verification["patch_applied"] is True
    assert verification["fallback_allowed"] is True
    assert verification["fallback_applied"] is True
    assert "row_result[j] += a_ik * row_b[j]" in project_path.read_text(encoding="utf-8")
