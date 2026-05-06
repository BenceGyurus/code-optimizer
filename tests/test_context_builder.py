import json

from optimizer.llm.context_builder import ContextBuilder
from optimizer.orchestrator.state_machine import State


def test_context_builder_summarizes_large_latest_result() -> None:
    builder = ContextBuilder("sample_project.py")
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


def test_context_builder_summarizes_function_profile_runs() -> None:
    builder = ContextBuilder("sample_project.py")
    latest_result = {
        "function_profile_runs": [
            {
                "success": True,
                "duration": 3.0,
                "stdout": "\n".join(f"profile line {index}" for index in range(200)),
                "profile": {
                    "entries": [
                        {"function": f"hot_{index}", "cumtime": float(index)}
                        for index in range(20)
                    ]
                },
            }
        ],
        "function_hotspots": [{"function": "hot_19", "average_cumtime": 19.0}],
    }

    context = builder.build_context(
        current_state=State.PROFILE_READY,
        allowed_actions=["analyze_candidate"],
        latest_result=latest_result,
    )
    payload = json.loads(context["latest_result"])

    assert payload["function_profile_runs"]["count"] == 1
    assert payload["function_profile_runs"]["duration_summary"]["average"] == 3.0
    assert "stdout" not in payload["function_profile_runs"]["samples"][0]
    assert payload["function_profile_runs"]["samples"][0]["profile"]["entries"]["count"] == 20
    assert payload["function_hotspots"][0]["function"] == "hot_19"
