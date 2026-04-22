from pathlib import Path

from optimizer.orchestrator.state_machine import State
from optimizer.tools.apply_and_verify import ApplyAndVerifyTool


def test_apply_and_verify_uses_deterministic_matrix_fallback_for_begin_patch(tmp_path):
    source_path = Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    project_path = tmp_path / "heavy_compute.py"
    project_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    patch = """*** Begin Patch
*** Update File: heavy_compute.py
@@
-def matrix_multiply(a, b):
+def matrix_multiply(a, b):
*** End Patch
"""

    result = ApplyAndVerifyTool().execute(
        patch=patch + "\n# matrix_multiply cache locality loop reorder",
        project_path=str(project_path),
        current_state=State.PATCH_PROPOSED.name,
    )

    updated = project_path.read_text(encoding="utf-8")
    assert result.success is True
    assert result.next_state == State.PATCH_APPLIED
    assert result.output["verification_result"]["patch_applied"] is True
    assert result.output["verification_result"]["fallback_applied"] is True
    assert "row_result[j] += a_ik * row_b[j]" in updated
