import csv
import json
import os
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
        runtime_repetitions: int = 5,
        hardware_repetitions: int = 10,
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
                runtime_repetitions=runtime_repetitions,
                hardware_repetitions=hardware_repetitions,
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

        return {
            "session_dir": session_dir,
            "tool_calls": summary.get("tool_calls"),
            "llm_calls": summary.get("llm_calls"),
            "llm_recoveries": summary.get("llm_recoveries"),
            "iterations": summary.get("iterations"),
            "baseline_runtime": _to_float(_read_nested(summary, "latest_result", "baseline_runtime")),
            "optimized_runtime": _to_float(_read_nested(summary, "latest_result", "optimized_runtime")),
            "relative_speedup": _to_float(_read_nested(summary, "latest_result", "relative_speedup")),
            "hardware_before": embedded_hardware_before or _read_hardware_summary(baseline_profile),
            "hardware_after": embedded_hardware_after or _read_hardware_summary(optimized_profile),
            "tool_usage": tool_usage,
            "fallback_applied": _fallback_applied(tool_outputs),
            "fallback_count": _fallback_count(tool_outputs),
            "patch_apply_failures": _patch_apply_failures(tool_outputs),
            "verification_failures": _verification_failures(tool_outputs),
            "verified_patch_applied": _verified_patch_applied(tool_outputs),
            "patch_application_count": _patch_application_count(tool_outputs),
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
    for verification in _apply_verification_events(tool_outputs):
        if (
            verification.get("patch_applied") is True
            and verification.get("noop_patch") is not True
            and verification.get("fallback_applied") is not True
        ):
            pending_model_patch = True
            continue
        if (
            pending_model_patch
            and verification.get("build_success") is True
            and verification.get("test_success") is True
            and not verification.get("short_error_summary")
        ):
            return True
    return False


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
    events: list[tuple[float, dict]] = []
    verifications: list[dict] = []
    for payload in tool_outputs.get("__all__", []):
        if not isinstance(payload, dict) or payload.get("tool_name") != "apply_and_verify":
            continue
        content = payload.get("content")
        if not isinstance(content, dict):
            continue
        verification = content.get("verification_result")
        if isinstance(verification, dict):
            timestamp = payload.get("timestamp")
            timestamp_value = float(timestamp) if isinstance(timestamp, (int, float)) else float("-inf")
            events.append((timestamp_value, verification))
    for _, verification in sorted(events, key=lambda item: item[0]):
        verifications.append(verification)
    return verifications
