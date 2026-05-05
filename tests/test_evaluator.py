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


def test_collect_run_details_prefers_embedded_hardware_summary_from_final_summary(tmp_path: Path) -> None:
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
                "hardware_before": {"cache_miss_rate": 0.15},
                "hardware_after": {"cache_miss_rate": 0.09},
            },
        },
    )
    _write_artifact(
        session_dir / "tool_output_profile_execution_100.json",
        "profile_execution",
        {"hardware_summary": {"cache_miss_rate": {"average": 0.25}}},
        timestamp=100.0,
    )
    _write_artifact(
        session_dir / "tool_output_terminal_remeasure_200.json",
        "terminal_remeasure",
        {"hardware_summary": {"cache_miss_rate": {"average": 0.18}}},
        timestamp=200.0,
    )

    details = Evaluator()._collect_run_details(str(session_dir))

    assert details["hardware_before"] == {"cache_miss_rate": 0.15}
    assert details["hardware_after"] == {"cache_miss_rate": 0.09}


def test_collect_run_details_reports_fallback_and_patch_failures(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_yaml(
        session_dir / "final_summary.yaml",
        {
            "tool_calls": 4,
            "llm_calls": 3,
            "iterations": 1,
            "latest_result": {},
        },
    )
    _write_artifact(
        session_dir / "tool_output_apply_and_verify_100.json",
        "apply_and_verify",
        {
            "verification_result": {
                "patch_applied": True,
                "fallback_applied": True,
                "short_error_summary": ["bad patch", "fallback applied"],
            }
        },
        timestamp=100.0,
    )
    _write_artifact(
        session_dir / "tool_output_apply_and_verify_200.json",
        "apply_and_verify",
        {
            "verification_result": {
                "patch_applied": False,
                "short_error_summary": ["bad patch"],
            }
        },
        timestamp=200.0,
    )

    details = Evaluator()._collect_run_details(str(session_dir))

    assert details["fallback_applied"] is True
    assert details["fallback_count"] == 1
    assert details["patch_apply_failures"] == 1
    assert details["verification_failures"] == 0
    assert details["performance_rollbacks"] == 0
    assert details["verified_patch_applied"] is False
    assert details["patch_application_count"] == 0


def test_collect_run_details_detects_verified_model_patch(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_yaml(
        session_dir / "final_summary.yaml",
        {
            "tool_calls": 4,
            "llm_calls": 3,
            "iterations": 1,
            "latest_result": {},
        },
    )
    _write_artifact(
        session_dir / "tool_output_apply_and_verify_100.json",
        "apply_and_verify",
        {
            "verification_result": {
                "patch_applied": True,
                "fallback_applied": False,
                "noop_patch": False,
                "short_error_summary": [],
            }
        },
        timestamp=100.0,
    )
    _write_artifact(
        session_dir / "tool_output_apply_and_verify_200.json",
        "apply_and_verify",
        {
            "verification_result": {
                "patch_applied": False,
                "build_success": True,
                "test_success": True,
                "short_error_summary": [],
            }
        },
        timestamp=200.0,
    )

    details = Evaluator()._collect_run_details(str(session_dir))

    assert details["verified_patch_applied"] is True
    assert details["patch_application_count"] == 1


def test_collect_run_details_separates_verification_failures_from_apply_failures(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_yaml(
        session_dir / "final_summary.yaml",
        {
            "tool_calls": 4,
            "llm_calls": 3,
            "iterations": 1,
            "latest_result": {},
        },
    )
    _write_artifact(
        session_dir / "tool_output_apply_and_verify_100.json",
        "apply_and_verify",
        {
            "verification_result": {
                "patch_applied": True,
                "short_error_summary": [],
            }
        },
        timestamp=100.0,
    )
    _write_artifact(
        session_dir / "tool_output_apply_and_verify_200.json",
        "apply_and_verify",
        {
            "verification_result": {
                "patch_applied": False,
                "verification_failed": True,
                "rollback_performed": True,
                "test_success": False,
                "short_error_summary": ["tests failed"],
            }
        },
        timestamp=200.0,
    )

    details = Evaluator()._collect_run_details(str(session_dir))

    assert details["patch_apply_failures"] == 0
    assert details["verification_failures"] == 1
    assert details["verified_patch_applied"] is False


def test_collect_run_details_treats_performance_rollback_as_no_verified_patch(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    _write_yaml(
        session_dir / "final_summary.yaml",
        {
            "tool_calls": 4,
            "llm_calls": 3,
            "iterations": 1,
            "latest_result": {},
        },
    )
    _write_artifact(
        session_dir / "tool_output_apply_and_verify_100.json",
        "apply_and_verify",
        {
            "verification_result": {
                "patch_applied": True,
                "fallback_applied": False,
                "noop_patch": False,
                "short_error_summary": [],
            }
        },
        timestamp=100.0,
    )
    _write_artifact(
        session_dir / "tool_output_apply_and_verify_200.json",
        "apply_and_verify",
        {
            "verification_result": {
                "patch_applied": False,
                "build_success": True,
                "test_success": True,
                "short_error_summary": [],
            }
        },
        timestamp=200.0,
    )
    _write_artifact(
        session_dir / "tool_output_performance_rollback_300.json",
        "performance_rollback",
        {
            "rollback_performed": True,
            "relative_speedup": 0.95,
            "short_error_summary": [],
        },
        timestamp=300.0,
    )

    details = Evaluator()._collect_run_details(str(session_dir))

    assert details["performance_rollbacks"] == 1
    assert details["verified_patch_applied"] is False
    assert details["patch_application_count"] == 1


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
