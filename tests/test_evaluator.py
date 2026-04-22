import json
from pathlib import Path

from optimizer.evaluation.evaluator import Evaluator
from optimizer.utils.yaml_io import dump_yaml


def test_collect_run_details_uses_profile_execution_and_terminal_remeasure(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    _write_yaml(
        session_dir / "final_summary.yaml",
        {
            "tool_calls": 4,
            "llm_calls": 3,
            "iterations": 1,
            "latest_result": {
                "baseline_runtime": 12.0,
                "optimized_runtime": 9.0,
                "relative_speedup": 1.3333333333,
            },
        },
    )
    _write_artifact(
        session_dir / "tool_output_profile_execution_100.json",
        "profile_execution",
        {
            "hardware_summary": {
                "cache_miss_rate": {"average": 0.25},
                "branch_miss_rate": {"average": 0.11},
            }
        },
        timestamp=100.0,
    )
    _write_artifact(
        session_dir / "tool_output_terminal_remeasure_200.json",
        "terminal_remeasure",
        {
            "hardware_summary": {
                "cache_miss_rate": {"average": 0.18},
                "branch_miss_rate": {"average": 0.07},
            }
        },
        timestamp=200.0,
    )

    details = Evaluator()._collect_run_details(str(session_dir))

    assert details["baseline_runtime"] == 12.0
    assert details["optimized_runtime"] == 9.0
    assert details["relative_speedup"] == 1.3333333333
    assert details["hardware_before"] == {"cache_miss_rate": 0.25, "branch_miss_rate": 0.11}
    assert details["hardware_after"] == {"cache_miss_rate": 0.18, "branch_miss_rate": 0.07}


def test_load_tool_outputs_keeps_latest_artifact_per_tool(tmp_path: Path, monkeypatch) -> None:
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    newer = session_dir / "tool_output_remeasure_new.json"
    older = session_dir / "tool_output_remeasure_old.json"

    _write_artifact(
        newer,
        "remeasure",
        {"hardware_summary": {"cache_miss_rate": {"average": 0.21}}},
        timestamp=200.0,
    )
    _write_artifact(
        older,
        "remeasure",
        {"hardware_summary": {"cache_miss_rate": {"average": 0.45}}},
        timestamp=100.0,
    )

    monkeypatch.setattr(
        "optimizer.evaluation.evaluator.os.listdir",
        lambda _: [newer.name, older.name],
    )

    outputs, usage = Evaluator()._load_tool_outputs(str(session_dir))

    assert outputs["remeasure"]["hardware_summary"]["cache_miss_rate"]["average"] == 0.21
    assert usage["remeasure"] == 2


def _write_artifact(path: Path, tool_name: str, content: dict, timestamp: float) -> None:
    path.write_text(
        json.dumps(
            {
                "name": f"tool_output_{tool_name}",
                "tool_name": tool_name,
                "content": content,
                "timestamp": timestamp,
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )


def _write_yaml(path: Path, content: dict) -> None:
    path.write_text(dump_yaml(content), encoding="utf-8")
