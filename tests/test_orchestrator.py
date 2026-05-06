import json
from pathlib import Path

import pytest

from optimizer.llm.prompt_loader import PromptLoader
from optimizer.orchestrator.guardrails import GuardrailsConfig
from optimizer.orchestrator.orchestrator import Orchestrator
from optimizer.orchestrator.state_machine import State
from optimizer.providers.mock import MockProvider
from optimizer.providers.base import LLMRequest, LLMResponse
from optimizer.tools.analyze_candidate import AnalyzeCandidateTool
from optimizer.tools.apply_and_verify import ApplyAndVerifyTool
from optimizer.tools.base import ToolResult


def _prompt_pack():
    return PromptLoader().get_pack("default")


def _project_file(tmp_path):
    path = tmp_path / "sample_project.py"
    path.write_text("def placeholder():\n    return 1\n", encoding="utf-8")
    return path


class CapturePromptProvider(MockProvider):
    def __init__(self, responses=None):
        super().__init__(responses=responses)
        self.last_prompt = ""

    def send_prompt(self, request: LLMRequest) -> LLMResponse:
        self.last_prompt = request.prompt
        return super().send_prompt(request)


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


def test_baseline_ready_forces_profile_before_analysis_when_profile_command_exists(tmp_path):
    project_path = _project_file(tmp_path)
    provider = MockProvider(
        responses=[
            json.dumps({"action": "run_baseline", "args": {}, "reason": "baseline"}),
            json.dumps(
                {
                    "action": "analyze_candidate",
                    "args": {"target": "placeholder", "strategy": "guess", "rationale": "skip profile"},
                    "reason": "bad shortcut",
                }
            ),
        ]
    )
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=provider,
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=5, max_tool_calls=5),
        interactive=False,
        profile_command='python -c "print(1)"',
        output_dir=str(tmp_path / "results"),
    )

    orchestrator._step()
    assert orchestrator.state_machine.current_state == State.BASELINE_READY

    orchestrator._step()
    assert orchestrator.state_machine.current_state == State.PROFILE_READY
    assert orchestrator.session_state.checkpoint_metadata["baseline_profile"]["profiler"]["source"] == "custom"


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
        allow_deterministic_fallback=True,
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


def test_parse_error_fallback_does_not_invent_patch_by_default(tmp_path):
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

    with pytest.raises(ValueError):
        orchestrator._parse_decision_response(
            "{ not-json",
            ["propose_change"],
            State.ANALYSIS_READY,
        )


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
        allow_deterministic_fallback=True,
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


def test_analyze_candidate_keeps_generic_target_by_default(tmp_path):
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

    assert result.output["target"] == "unspecified"
    assert result.output["strategy"] == "inspect hot path"
    assert result.output["rationale"] == ""


def test_analyze_candidate_replaces_generic_target_when_deterministic_fallback_enabled(tmp_path):
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
        allow_deterministic_fallback=True,
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
        allow_deterministic_fallback=True,
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


def test_failed_patch_verification_rolls_back_and_returns_to_candidate_selection(tmp_path):
    project_path = _project_file(tmp_path)
    patch = """*** Begin Patch
*** Update File: sample_project.py
@@
 def placeholder():
-    return 1
+    return 2
*** End Patch
"""
    provider = MockProvider(
        responses=[
            json.dumps({"action": "run_baseline", "args": {}, "reason": "baseline"}),
            json.dumps(
                {
                    "action": "analyze_candidate",
                    "args": {"target": "placeholder", "strategy": "change return", "rationale": "test candidate"},
                    "reason": "choose target",
                }
            ),
            json.dumps(
                {
                    "action": "propose_change",
                    "args": {
                        "target": "placeholder",
                        "strategy": "change return",
                        "patch": patch,
                        "rationale": "test patch",
                    },
                    "reason": "propose patch",
                }
            ),
            json.dumps({"action": "apply_and_verify", "args": {}, "reason": "apply"}),
            json.dumps({"action": "apply_and_verify", "args": {}, "reason": "verify"}),
        ]
    )
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=provider,
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=8, max_tool_calls=8),
        interactive=False,
        test_command='python -B -c "import sample_project; raise SystemExit(0 if sample_project.placeholder()==1 else 1)"',
        output_dir=str(tmp_path / "results"),
    )

    for _ in range(5):
        orchestrator._step()

    assert orchestrator.state_machine.current_state == State.PROFILE_READY
    assert orchestrator.pending_patch == ""
    assert orchestrator._rejected_targets() == ["placeholder"]


def test_regressed_verified_patch_is_rolled_back_before_next_candidate(tmp_path):
    project_path = _project_file(tmp_path)
    patch = """*** Begin Patch
*** Update File: sample_project.py
@@
 def placeholder():
-    return 1
+    return 2
*** End Patch
"""
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )
    ApplyAndVerifyTool().execute(
        patch=patch,
        project_path=orchestrator.project_path,
        patch_cwd=orchestrator.workspace_root,
        current_state=State.PATCH_PROPOSED.name,
    )
    assert "return 2" in Path(orchestrator.project_path).read_text(encoding="utf-8")
    orchestrator.session_state.current_target = "placeholder"
    orchestrator.session_state.checkpoint_metadata["last_verified_patch"] = patch
    result = ToolResult(
        success=True,
        output={
            "baseline_runtime": 10.0,
            "optimized_runtime": 11.0,
            "relative_speedup": 0.9,
            "decision": "continue",
        },
        next_state=State.ANALYSIS_READY,
        metadata={},
    )

    orchestrator._handle_successful_tool_result("evaluate_result", State.REMEASURED, {}, result)
    orchestrator._update_session_state("evaluate_result", result.output)

    assert result.next_state == State.PROFILE_READY
    assert result.output["performance_rollback"]["rollback_performed"] is True
    assert result.output["performance_rollback"]["target"] == "placeholder"
    assert "return 1" in Path(orchestrator.project_path).read_text(encoding="utf-8")
    assert orchestrator._rejected_targets() == ["placeholder"]
    assert orchestrator._rejected_target_details() == [
        {"target": "placeholder", "reason": "runtime regression speedup=0.900000"}
    ]
    assert orchestrator.session_state.checkpoint_metadata.get("last_verified_patch") is None


def test_source_context_refreshes_after_workspace_changes(tmp_path):
    project_path = _project_file(tmp_path)
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )
    orchestrator.session_state.current_target = "placeholder"
    before = orchestrator._source_context_for(State.ANALYSIS_READY)

    Path(orchestrator.project_path).write_text("def placeholder():\n    return 2\n", encoding="utf-8")
    after = orchestrator._source_context_for(State.ANALYSIS_READY)

    assert "return 1" in before
    assert "return 2" in after


def test_action_guidance_is_appended_even_when_master_omits_placeholder(tmp_path):
    project_path = _project_file(tmp_path)
    provider = CapturePromptProvider(
        responses=[
            json.dumps(
                {
                    "action": "propose_change",
                    "args": {"target": "placeholder", "strategy": "none", "patch": "", "rationale": "no safe patch"},
                    "reason": "capture prompt",
                }
            )
        ]
    )
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=provider,
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )
    orchestrator.state_machine._current_state = State.ANALYSIS_READY

    orchestrator._step()

    assert "# Action Guidance" in provider.last_prompt
    assert "Avoid cosmetic micro-optimizations" in provider.last_prompt


def test_state_specific_action_prompt_is_included(tmp_path):
    project_path = _project_file(tmp_path)
    provider = CapturePromptProvider(
        responses=[
            json.dumps(
                {
                    "action": "propose_change",
                    "args": {"target": "placeholder", "strategy": "none", "patch": "", "rationale": "no safe patch"},
                    "reason": "capture prompt",
                }
            )
        ]
    )
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=provider,
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )
    orchestrator.state_machine._current_state = State.ANALYSIS_READY
    orchestrator.session_state.current_target = "placeholder"

    orchestrator._step()

    assert "# State-Specific Prompt: propose_change" in provider.last_prompt
    assert "Propose a minimal structured patch" in provider.last_prompt
    assert '"target": "placeholder"' in provider.last_prompt


def test_state_prompt_mapping_is_only_used_for_single_purpose_states(tmp_path):
    project_path = _project_file(tmp_path)
    orchestrator = Orchestrator(
        project_path=str(project_path),
        provider=MockProvider(),
        prompt_pack=_prompt_pack(),
        guardrails_config=GuardrailsConfig(max_llm_calls=1, max_tool_calls=1),
        interactive=False,
        output_dir=str(tmp_path / "results"),
    )

    assert orchestrator._state_prompt_name(State.INIT) is None
    assert orchestrator._state_prompt_name(State.BASELINE_READY) is None
    assert orchestrator._state_prompt_name(State.PROFILE_READY) == "analyze_candidate"
    assert orchestrator._state_prompt_name(State.ANALYSIS_READY) == "propose_change"
    assert orchestrator._state_prompt_name(State.REMEASURED) == "evaluate_result"
