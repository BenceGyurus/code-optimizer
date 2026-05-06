import csv
import json
import os
import re
from dataclasses import asdict
from typing import Any

from optimizer.evaluation.aggregator import ResultAggregator
from optimizer.evaluation.charts import write_charts
from optimizer.evaluation.experiment_manager import ExperimentManager
from optimizer.evaluation.report import write_report
from optimizer.llm.prompt_loader import PromptLoader
from optimizer.orchestrator.guardrails import GuardrailsConfig
from optimizer.orchestrator.orchestrator import Orchestrator
from optimizer.providers.registry import registry as provider_registry
from optimizer.tools.profile_parser import parse_unsupported_counters
from optimizer.utils.yaml_io import load_yaml
from optimizer.utils.yaml_io import dump_yaml


class Evaluator:
    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir

    def run(
        self,
        project: str,
        providers: list[str],
        models: list[str | None],
        prompt_packs: list[str],
        repetitions: int,
        provider_models: list[tuple[str, str | None]] | None = None,
        build_command: str | None = None,
        test_command: str | None = None,
        benchmark_command: str | None = None,
        profile_command: str | None = None,
        function_profile_command: str | None = None,
        runtime_repetitions: int = 5,
        hardware_repetitions: int = 10,
        function_profile_repetitions: int = 1,
        max_tool_calls: int = 50,
        max_llm_calls: int = 20,
        max_iterations: int = 5,
        allow_deterministic_fallback: bool = False,
        verbose: bool = False,
    ) -> str:
        manager = ExperimentManager(self.output_dir)
        eval_dir = manager.create_run_dir()
        matrix = manager.matrix(providers, models, prompt_packs, repetitions, provider_models=provider_models)
        loader = PromptLoader()
        rows = []

        with open(os.path.join(eval_dir, "experiment_matrix.yaml"), "w", encoding="utf-8") as handle:
            handle.write(dump_yaml({"matrix": [asdict(item) for item in matrix]}))

        for config in matrix:
            provider = provider_registry.get_provider(config.provider)
            pack = loader.get_pack(config.prompt_pack)
            if provider is None or pack is None:
                rows.append({**asdict(config), "final_state": "FAILED", "error": "missing provider or prompt pack"})
                continue
            orchestrator = Orchestrator(
                project_path=project,
                provider=provider,
                prompt_pack=pack,
                guardrails_config=GuardrailsConfig(
                    max_tool_calls=max_tool_calls,
                    max_llm_calls=max_llm_calls,
                    max_iterations=max_iterations,
                ),
                interactive=False,
                build_command=build_command,
                test_command=test_command,
                benchmark_command=benchmark_command,
                profile_command=profile_command,
                function_profile_command=function_profile_command,
                runtime_repetitions=runtime_repetitions,
                hardware_repetitions=hardware_repetitions,
                function_profile_repetitions=function_profile_repetitions,
                allow_deterministic_fallback=allow_deterministic_fallback,
                output_dir=os.path.join(eval_dir, "per_run"),
                model=config.model,
                verbose=verbose,
            )
            final_state = orchestrator.run()
            rows.append({**asdict(config), **self._collect_run_details(orchestrator.artifact_store.session_dir), "final_state": final_state.name})

        aggregate = ResultAggregator().aggregate(rows)
        self._write_results(eval_dir, rows, aggregate)
        write_charts(os.path.join(eval_dir, "charts"), aggregate)
        write_report(eval_dir, aggregate)
        return eval_dir

    def _write_results(self, eval_dir: str, rows: list[dict], aggregate: dict) -> None:
        csv_path = os.path.join(eval_dir, "aggregated_results.csv")
        fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["final_state"]
        with open(csv_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        with open(os.path.join(eval_dir, "aggregated_results.yaml"), "w", encoding="utf-8") as handle:
            handle.write(dump_yaml(aggregate))

    def _collect_run_details(self, session_dir: str) -> dict:
        summary_path = os.path.join(session_dir, "final_summary.yaml")
        summary = load_yaml(summary_path) if os.path.exists(summary_path) else {}
        tool_outputs, tool_usage = self._load_tool_outputs(session_dir)

        baseline_profile = _first_available_output(tool_outputs, "profile_execution", "run_baseline")
        optimized_profile = _first_available_output(tool_outputs, "remeasure", "terminal_remeasure")
        embedded_hardware_before = _read_embedded_hardware_summary(summary, "hardware_before")
        embedded_hardware_after = _read_embedded_hardware_summary(summary, "hardware_after")
        latest_result = _read_nested(summary, "latest_result")
        if not isinstance(latest_result, dict):
            latest_result = {}
        baseline_runtime = _to_float(latest_result.get("baseline_runtime"))
        measured_runtime = _to_float(latest_result.get("optimized_runtime"))
        relative_speedup = _to_float(latest_result.get("relative_speedup"))
        performance_rollbacks = _performance_rollback_count(tool_outputs)
        verified_patch_applied = _verified_patch_applied(tool_outputs)
        patch_application_count = _patch_application_count(tool_outputs)
        accepted_runtime = measured_runtime if verified_patch_applied and performance_rollbacks == 0 else None
        post_rollback_runtime = measured_runtime if performance_rollbacks > 0 and not verified_patch_applied else None
        rejected_target_details = _read_rejected_target_details(summary, tool_outputs)
        final_relative_speedup = relative_speedup
        accepted_relative_speedup = (
            baseline_runtime / accepted_runtime
            if isinstance(baseline_runtime, (int, float))
            and isinstance(accepted_runtime, (int, float))
            and accepted_runtime > 0
            else None
        )
        attempted_relative_speedup = _attempted_relative_speedup(
            rejected_target_details,
            patch_application_count,
            relative_speedup,
        )

        return {
            "session_dir": session_dir,
            "tool_calls": summary.get("tool_calls"),
            "llm_calls": summary.get("llm_calls"),
            "llm_recoveries": summary.get("llm_recoveries"),
            "iterations": summary.get("iterations"),
            "optimization_attempts": patch_application_count,
            "baseline_runtime": baseline_runtime,
            "optimized_runtime": measured_runtime,
            "final_runtime": measured_runtime,
            "accepted_optimized_runtime": accepted_runtime,
            "post_rollback_runtime": post_rollback_runtime,
            "relative_speedup": relative_speedup,
            "final_relative_speedup": final_relative_speedup,
            "accepted_relative_speedup": accepted_relative_speedup,
            "attempted_relative_speedup": attempted_relative_speedup,
            "hardware_before": embedded_hardware_before or _read_hardware_summary(baseline_profile),
            "hardware_after": embedded_hardware_after or _read_hardware_summary(optimized_profile),
            "function_hotspots": _read_function_hotspots(baseline_profile),
            "unsupported_hardware_counters": _unsupported_hardware_counters(tool_outputs),
            "rejected_targets": _read_rejected_targets(summary),
            "rejected_target_details": rejected_target_details,
            "tool_usage": tool_usage,
            "fallback_applied": _fallback_applied(tool_outputs),
            "fallback_count": _fallback_count(tool_outputs),
            "patch_apply_failures": _patch_apply_failures(tool_outputs),
            "verification_failures": _verification_failures(tool_outputs),
            "performance_rollbacks": performance_rollbacks,
            "verified_patch_applied": verified_patch_applied,
            "patch_application_count": patch_application_count,
        }

    def _load_tool_outputs(self, session_dir: str) -> tuple[dict, dict]:
        latest_outputs: dict[str, tuple[float, Any]] = {}
        usage: dict[str, int] = {}
        all_outputs: list[dict[str, Any]] = []
        for name in os.listdir(session_dir):
            if not (name.startswith("tool_output_") and name.endswith(".json")):
                continue
            path = os.path.join(session_dir, name)
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            all_outputs.append(payload)
            tool_name = payload.get("tool_name") or name
            timestamp = payload.get("timestamp")
            timestamp_value = float(timestamp) if isinstance(timestamp, (int, float)) else float("-inf")
            current = latest_outputs.get(tool_name)
            if current is None or timestamp_value >= current[0]:
                latest_outputs[tool_name] = (timestamp_value, payload.get("content") or {})
            usage[tool_name] = usage.get(tool_name, 0) + 1
        outputs = {tool_name: content for tool_name, (_, content) in latest_outputs.items()}
        outputs["__all__"] = all_outputs
        return outputs, usage


def _read_nested(payload: dict, *keys: str) -> object:
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _first_available_output(tool_outputs: dict[str, Any], *tool_names: str) -> Any:
    for tool_name in tool_names:
        if tool_name in tool_outputs:
            return tool_outputs[tool_name]
    return {}


def _read_hardware_summary(tool_output: dict) -> dict:
    if not isinstance(tool_output, dict):
        return {}
    summary = tool_output.get("hardware_summary")
    if not isinstance(summary, dict):
        return {}
    reduced = {}
    for key, value in summary.items():
        if isinstance(value, dict):
            average = value.get("average")
            if isinstance(average, (int, float)):
                reduced[key] = float(average)
        elif isinstance(value, (int, float)):
            reduced[key] = float(value)
    return reduced


def _read_function_hotspots(tool_output: dict) -> list[dict[str, Any]]:
    if not isinstance(tool_output, dict):
        return []
    hotspots = tool_output.get("function_hotspots")
    if not isinstance(hotspots, list):
        return []
    return [hotspot for hotspot in hotspots if isinstance(hotspot, dict)]


def _read_embedded_hardware_summary(summary: dict, key: str) -> dict:
    latest = _read_nested(summary, "latest_result", key)
    if isinstance(latest, dict):
        return _coerce_numeric_summary(latest)
    best = _read_nested(summary, "best_result", key)
    if isinstance(best, dict):
        return _coerce_numeric_summary(best)
    return {}


def _coerce_numeric_summary(summary: dict) -> dict:
    reduced = {}
    for key, value in summary.items():
        if isinstance(value, (int, float)):
            reduced[key] = float(value)
    return reduced


def _fallback_applied(tool_outputs: dict[str, Any]) -> bool:
    return _fallback_count(tool_outputs) > 0


def _fallback_count(tool_outputs: dict[str, Any]) -> int:
    return sum(1 for verification in _apply_verifications(tool_outputs) if verification.get("fallback_applied") is True)


def _patch_apply_failures(tool_outputs: dict[str, Any]) -> int:
    return sum(
        1
        for verification in _apply_verifications(tool_outputs)
        if verification.get("short_error_summary") and verification.get("patch_applied") is not True
        and verification.get("verification_failed") is not True
    )


def _verification_failures(tool_outputs: dict[str, Any]) -> int:
    return sum(
        1
        for verification in _apply_verifications(tool_outputs)
        if verification.get("verification_failed") is True
    )


def _verified_patch_applied(tool_outputs: dict[str, Any]) -> bool:
    pending_model_patch = False
    verified = False
    for event_name, payload in _patch_lifecycle_events(tool_outputs):
        if event_name == "performance_rollback" and payload.get("rollback_performed") is True:
            pending_model_patch = False
            verified = False
            continue
        verification = payload
        if verification.get("patch_applied") is True and verification.get("noop_patch") is not True and verification.get("fallback_applied") is not True:
            pending_model_patch = True
            continue
        if pending_model_patch and verification.get("build_success") is True and verification.get("test_success") is True and not verification.get("short_error_summary"):
            verified = True
            pending_model_patch = False
    return verified


def _patch_application_count(tool_outputs: dict[str, Any]) -> int:
    return sum(
        1
        for verification in _apply_verifications(tool_outputs)
        if verification.get("patch_applied") is True
        and verification.get("noop_patch") is not True
        and verification.get("fallback_applied") is not True
    )


def _apply_verifications(tool_outputs: dict[str, Any]) -> list[dict]:
    return list(_apply_verification_events(tool_outputs))


def _apply_verification_events(tool_outputs: dict[str, Any]) -> list[dict]:
    return [payload for event_name, payload in _patch_lifecycle_events(tool_outputs) if event_name == "apply_and_verify"]


def _patch_lifecycle_events(tool_outputs: dict[str, Any]) -> list[tuple[str, dict]]:
    events: list[tuple[float, dict]] = []
    lifecycle_events: list[tuple[str, dict]] = []
    for payload in tool_outputs.get("__all__", []):
        if not isinstance(payload, dict):
            continue
        content = payload.get("content")
        if not isinstance(content, dict):
            continue
        tool_name = payload.get("tool_name")
        event_payload = None
        if tool_name == "apply_and_verify":
            event_payload = content.get("verification_result")
        elif tool_name == "performance_rollback":
            event_payload = content
        if isinstance(event_payload, dict):
            timestamp = payload.get("timestamp")
            timestamp_value = float(timestamp) if isinstance(timestamp, (int, float)) else float("-inf")
            events.append((timestamp_value, {"tool_name": tool_name, "payload": event_payload}))
    for _, event in sorted(events, key=lambda item: item[0]):
        lifecycle_events.append((str(event.get("tool_name")), event["payload"]))
    return lifecycle_events


def _performance_rollback_count(tool_outputs: dict[str, Any]) -> int:
    return sum(
        1
        for event_name, payload in _patch_lifecycle_events(tool_outputs)
        if event_name == "performance_rollback" and payload.get("rollback_performed") is True
    )


def _unsupported_hardware_counters(tool_outputs: dict[str, Any]) -> list[str]:
    unsupported: set[str] = set()
    for payload in tool_outputs.get("__all__", []):
        if not isinstance(payload, dict):
            continue
        content = payload.get("content")
        if not isinstance(content, dict):
            continue
        profiler = content.get("profiler")
        if isinstance(profiler, dict):
            counters = profiler.get("unsupported_counters")
            if isinstance(counters, list):
                unsupported.update(str(counter) for counter in counters if counter)
        for run_container in ("runs", "profile"):
            runs = content.get(run_container)
            if not isinstance(runs, list):
                continue
            for run in runs:
                if not isinstance(run, dict):
                    continue
                unsupported.update(
                    parse_unsupported_counters(
                        str(run.get("stdout") or ""),
                        str(run.get("stderr") or ""),
                    )
                )
    return sorted(unsupported)


def _read_rejected_targets(summary: dict) -> list[str]:
    targets = summary.get("rejected_targets")
    if isinstance(targets, list):
        return sorted(str(target) for target in targets if target)
    details = summary.get("rejected_target_details")
    if isinstance(details, list):
        return sorted(str(item.get("target")) for item in details if isinstance(item, dict) and item.get("target"))
    return []


def _read_rejected_target_details(summary: dict, tool_outputs: dict[str, Any]) -> list[dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    summary_details = summary.get("rejected_target_details")
    if isinstance(summary_details, list):
        for item in summary_details:
            if not isinstance(item, dict) or not item.get("target"):
                continue
            target = str(item.get("target"))
            reason = str(item.get("reason") or "")
            details[target] = {
                "target": target,
                "reason": reason,
                "relative_speedup": _speedup_from_reason(reason),
            }

    for event_name, payload in _patch_lifecycle_events(tool_outputs):
        if event_name != "performance_rollback" or payload.get("rollback_performed") is not True:
            continue
        target = payload.get("target")
        if not target:
            continue
        target_text = str(target)
        details[target_text] = {
            "target": target_text,
            "reason": str(payload.get("reason") or "runtime regression"),
            "relative_speedup": _to_float(payload.get("relative_speedup")),
        }

    for target in _read_rejected_targets(summary):
        details.setdefault(target, {"target": target, "reason": "", "relative_speedup": None})
    return [details[target] for target in sorted(details.keys())]


def _attempted_relative_speedup(
    rejected_target_details: list[dict[str, Any]],
    patch_application_count: int,
    relative_speedup: float | None,
) -> float | None:
    rejected_speedups = [
        _to_float(detail.get("relative_speedup"))
        for detail in rejected_target_details
        if isinstance(detail, dict)
    ]
    rejected_speedups = [value for value in rejected_speedups if value is not None]
    if rejected_speedups:
        return rejected_speedups[-1]
    if patch_application_count > 0:
        return relative_speedup
    return None


def _speedup_from_reason(reason: str) -> float | None:
    match = re.search(r"speedup=([0-9.]+)", reason)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None
