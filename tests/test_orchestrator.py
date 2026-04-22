import json
from pathlib import Path

from optimizer.llm.prompt_loader import PromptLoader
from optimizer.orchestrator.guardrails import GuardrailsConfig
from optimizer.orchestrator.orchestrator import Orchestrator
from optimizer.orchestrator.state_machine import State
from optimizer.providers.mock import MockProvider


def _prompt_pack():
    return PromptLoader().get_pack("default")


def _project_file(tmp_path):
    path = tmp_path / "heavy_compute.py"
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
    orchestrator.pending_patch = "diff --git a/heavy_compute.py b/heavy_compute.py\n"

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
    project_path = tmp_path / "heavy_compute.py"
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


def test_parse_error_fallback_can_choose_default_heavy_compute_target(tmp_path):
    source = (
        Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    ).read_text(encoding="utf-8")
    project_path = tmp_path / "heavy_compute.py"
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
    assert decision["args"]["target"] in {"moving_average_slow", "matrix_multiply", "join_events_to_users_slow", "category_totals_slow"}
    assert decision["args"]["patch"].startswith("diff --git ")
    assert recovery_note == "Parse fallback selected propose_change."


def test_parse_error_fallback_can_choose_deterministic_analysis_candidate(tmp_path):
    source = (
        Path(__file__).resolve().parents[1] / "examples" / "heavy_compute.py"
    ).read_text(encoding="utf-8")
    project_path = tmp_path / "heavy_compute.py"
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
    assert decision["args"]["target"] in {"moving_average_slow", "matrix_multiply", "join_events_to_users_slow", "category_totals_slow"}
    assert decision["args"]["strategy"]
    assert recovery_note == "Parse fallback selected analyze_candidate."
