import json
from pathlib import Path

from optimizer.llm.prompt_loader import PromptLoader
from optimizer.orchestrator.guardrails import GuardrailsConfig
from optimizer.orchestrator.orchestrator import Orchestrator
from optimizer.orchestrator.state_machine import State
from optimizer.providers.mock import MockProvider
from optimizer.tools.analyze_candidate import AnalyzeCandidateTool


def _prompt_pack():
    return PromptLoader().get_pack("default")


def _project_file(tmp_path):
    path = tmp_path / "sample_project.py"
    path.write_text("def placeholder():\n    return 1\n", encoding="utf-8")
    return path


def test_repeated_inspect_in_init_falls_back_to_baseline(tmp_path):
    project_path = _project_file(tmp_path)
    provider = MockProvider(
        responses=[
            json.dumps({"action": "inspect_codebase", "args": {}, "reason": "inspect"}),
            json.dumps({"action": "inspect_codebase", "args": {}, "reason": "inspect"}),
        ]
    )
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=provider,
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_repeated_signatures=1, max_llm_calls=4, max_tool_calls=4),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )

    orchestrator._step()
    assert orchestrator.state_machine.current_state == State.INIT

    orchestrator._step()
    assert orchestrator.state_machine.current_state == State.BASELINE_READY
    assert orchestrator.session_state.latest_result["message"] == "Baseline established"


def test_repeated_inspect_in_baseline_ready_falls_back_to_profile(tmp_path):
    project_path = _project_file(tmp_path)
    provider = MockProvider(
        responses=[
            json.dumps({"action": "run_baseline", "args": {}, "reason": "baseline"}),
            json.dumps({"action": "inspect_codebase", "args": {}, "reason": "inspect"}),
            json.dumps({"action": "inspect_codebase", "args": {}, "reason": "inspect"}),
        ]
    )
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=provider,
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_repeated_signatures=1, max_llm_calls=5, max_tool_calls=5),
        interactive=False,
        profile_command='python -c "print(1)"',
        output_dir=str(tmp_path / "results"),
    )

    orchestrator._step()
    assert orchestrator.state_machine.current_state == State.BASELINE_READY

    orchestrator._step()
    assert orchestrator.state_machine.current_state == State.BASELINE_READY

    orchestrator._step()
    assert orchestrator.state_machine.current_state == State.PROFILE_READY
    assert orchestrator.session_state.latest_result["profiler"]["source"] == "custom"


def test_parse_decision_repairs_malformed_apply_and_verify_response(tmp_path):
    project_path = _project_file(tmp_path)
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )

    decision, recovery_note = orchestrator._parse_decision_response(
        '{\n{""":"action","action":"apply_and_verify","args":{}","}',
        ["apply_and_verify", "rollback_to_checkpoint"],
        State.PATCH_PROPOSED,
    )

    assert decision["action"] == "apply_and_verify"
    assert decision["args"] == {}
    assert recovery_note == "Recovered malformed JSON response."


def test_parse_error_fallback_uses_apply_and_verify_when_patch_exists(tmp_path):
    project_path = _project_file(tmp_path)
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )
    orchestrator.pending_patch = "diff --git a/sample_project.py b/sample_project.py\n"

    decision, recovery_note = orchestrator._parse_decision_response(
        "{ not-json",
        ["apply_and_verify", "rollback_to_checkpoint"],
        State.PATCH_PROPOSED,
    )

    assert decision["action"] == "apply_and_verify"
    assert decision["args"] == {}
    assert recovery_note == "Parse fallback selected apply_and_verify."


def test_parse_error_fallback_builds_deterministic_propose_change(tmp_path):
    source = (
        Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    ).read_text(encoding="utf-8")
    project_path = tmp_path / "sample_project.py"
    project_path.write_text(source, encoding="utf-8")

    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )
    orchestrator.session_state.current_target = "matrix_multiply"

    decision, recovery_note = orchestrator._parse_decision_response(
        "{ not-json",
        ["propose_change"],
        State.ANALYSIS_READY,
    )

    assert decision["action"] == "propose_change"
    assert decision["args"]["target"] == "matrix_multiply"
    assert decision["args"]["patch"].startswith("diff --git ")
    assert recovery_note == "Parse fallback selected propose_change."


def test_parse_error_fallback_can_choose_default_target_without_filename_hint(tmp_path):
    source = (
        Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    ).read_text(encoding="utf-8")
    project_path = tmp_path / "sample_project.py"
    project_path.write_text(source, encoding="utf-8")

    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )

    decision, recovery_note = orchestrator._parse_decision_response(
        "{ not-json",
        ["propose_change"],
        State.ANALYSIS_READY,
    )

    assert decision["action"] == "propose_change"
    assert decision["args"]["target"] == "matrix_multiply"
    assert decision["args"]["patch"].startswith("diff --git ")
    assert recovery_note == "Parse fallback selected propose_change."


def test_parse_error_fallback_can_choose_deterministic_analysis_candidate(tmp_path):
    source = (
        Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    ).read_text(encoding="utf-8")
    project_path = tmp_path / "sample_project.py"
    project_path.write_text(source, encoding="utf-8")

    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )

    decision, recovery_note = orchestrator._parse_decision_response(
        "{ not-json",
        ["analyze_candidate"],
        State.PROFILE_READY,
    )

    assert decision["action"] == "analyze_candidate"
    assert decision["args"]["target"] == "matrix_multiply"
    assert decision["args"]["strategy"]
    assert recovery_note == "Parse fallback selected analyze_candidate."


def test_analyze_candidate_replaces_generic_target_with_deterministic_fallback(tmp_path):
    source = (
        Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    ).read_text(encoding="utf-8")
    project_path = tmp_path / "sample_project.py"
    project_path.write_text(source, encoding="utf-8")

    result = AnalyzeCandidateTool().execute(
        project_path=str(project_path),
        target="unspecified",
        strategy="inspect hot path",
        rationale="",
    )

    assert result.output["target"] == "matrix_multiply"
    assert result.output["strategy"]
    assert result.output["rationale"]


def test_analyze_candidate_avoids_rejected_target(tmp_path):
    source = (
        Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    ).read_text(encoding="utf-8")
    project_path = tmp_path / "sample_project.py"
    project_path.write_text(source, encoding="utf-8")

    result = AnalyzeCandidateTool().execute(
        project_path=str(project_path),
        target="matrix_multiply",
        strategy="loop reorder",
        rationale="",
        rejected_targets=["matrix_multiply"],
    )

    assert result.output["target"] != "matrix_multiply"
    assert result.output["target"] in {"join_events_to_users_slow", "category_totals_slow", "moving_average_slow"}


def test_finalize_summary_prefers_best_evaluation_snapshot(tmp_path):
    project_path = _project_file(tmp_path)
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )
    best_snapshot = {
        "baseline_runtime": 10.0,
        "optimized_runtime": 8.0,
        "relative_speedup": 1.25,
        "hardware_before": {"cache_miss_rate": 0.2},
        "hardware_after": {"cache_miss_rate": 0.1},
    }
    orchestrator.session_state.latest_result = {"decision": "stop"}
    orchestrator.session_state.checkpoint_metadata["best_evaluation"] = best_snapshot

    assert orchestrator._finalize_latest_result_for_summary() == best_snapshot
    assert orchestrator.session_state.latest_result == best_snapshot


def test_console_tool_start_summary_hides_long_commands(tmp_path):
    project_path = _project_file(tmp_path)
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )

    summary = orchestrator._format_tool_start(
        "profile_execution",
        {
            "project_path": "/very/long/workspace/path/sample_project.py",
            "test_cmd": "python -m unittest discover -s . -p sample_project.py",
            "profile_cmd": "perf stat -e cache-misses -- python sample_project.py",
            "hardware_repetitions": 30,
        },
        State.BASELINE_READY,
    )

    assert summary == "(profile x30)"
    assert "project_path" not in summary
    assert "unittest" not in summary
    assert "perf stat" not in summary


def test_console_hardware_summary_is_compact(tmp_path):
    project_path = _project_file(tmp_path)
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )

    summary = orchestrator._format_hardware_summary(
        {
            "cache_hit_rate": {"average": 0.9618},
            "cache_miss_rate": {"average": 0.0382},
            "l1_dcache_load_hit_rate": {"average": 0.9783},
            "branch_miss_rate": {"average": 0.00147},
        }
    )

    assert summary == "cache hit=96.18%, cache miss=3.82%, L1 hit=97.83%, branch miss=0.15%"
    assert "average" not in summary
    assert "{" not in summary


def test_orchestrator_marks_regressed_target_as_rejected(tmp_path):
    project_path = _project_file(tmp_path)
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )
    orchestrator.session_state.current_target = "matrix_multiply"

    orchestrator._update_session_state(
        "evaluate_result",
        {
            "baseline_runtime": 10.0,
            "optimized_runtime": 11.0,
            "relative_speedup": 0.9,
            "decision": "continue",
        },
    )

    assert orchestrator._rejected_targets() == ["matrix_multiply"]
    assert "matrix_multiply" in orchestrator._action_guidance(State.ANALYSIS_READY)
