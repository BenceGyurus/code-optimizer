import json

from optimizer.llm.context_builder import ContextBuilder
from optimizer.orchestrator.state_machine import State


def test_context_builder_summarizes_large_latest_result() -> None:
    builder = ContextBuilder("heavy_compute.py")
    latest_result = {
        "patch": "diff --git a/x b/x\n" + "\n".join(f"+line {index}" for index in range(40)),
        "test": {
            "success": True,
            "output": "\n".join(f"test line {index}" for index in range(30)),
            "error": "",
        },
        "benchmark": {
            "average_duration": 1.5,
            "runs": [
                {"success": True, "duration": 1.0, "output": "run output " * 40, "error": ""}
                for _ in range(10)
            ],
        },
    }

    context = builder.build_context(
        current_state=State.BASELINE_READY,
        allowed_actions=["profile_execution"],
        latest_result=latest_result,
    )
    payload = json.loads(context["latest_result"])

    assert "patch" not in payload
    assert payload["patch_summary"]["present"] is True
    assert payload["patch_summary"]["lines"] >= 10
    assert payload["test"]["output"]["truncated"] is True
    assert payload["benchmark"]["runs"]["count"] == 10
    assert payload["benchmark"]["runs"]["duration_summary"]["average"] == 1.0
