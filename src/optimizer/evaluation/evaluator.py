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
        build_command: str | None = None,
        test_command: str | None = None,
        benchmark_command: str | None = None,
        profile_command: str | None = None,
        runtime_repetitions: int = 5,
        hardware_repetitions: int = 10,
        max_tool_calls: int = 50,
        max_llm_calls: int = 20,
        max_iterations: int = 5,
        verbose: bool = False,
    ) -> str:
        manager = ExperimentManager(self.output_dir)
        eval_dir = manager.create_run_dir()
        matrix = manager.matrix(providers, models, prompt_packs, repetitions)
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

        return {
            "session_dir": session_dir,
            "tool_calls": summary.get("tool_calls"),
            "llm_calls": summary.get("llm_calls"),
            "iterations": summary.get("iterations"),
            "baseline_runtime": _to_float(_read_nested(summary, "latest_result", "baseline_runtime")),
            "optimized_runtime": _to_float(_read_nested(summary, "latest_result", "optimized_runtime")),
            "relative_speedup": _to_float(_read_nested(summary, "latest_result", "relative_speedup")),
            "hardware_before": _read_hardware_summary(baseline_profile),
            "hardware_after": _read_hardware_summary(optimized_profile),
            "tool_usage": tool_usage,
        }

    def _load_tool_outputs(self, session_dir: str) -> tuple[dict, dict]:
        latest_outputs: dict[str, tuple[float, Any]] = {}
        usage: dict[str, int] = {}
        for name in os.listdir(session_dir):
            if not (name.startswith("tool_output_") and name.endswith(".json")):
                continue
            path = os.path.join(session_dir, name)
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            tool_name = payload.get("tool_name") or name
            timestamp = payload.get("timestamp")
            timestamp_value = float(timestamp) if isinstance(timestamp, (int, float)) else float("-inf")
            current = latest_outputs.get(tool_name)
            if current is None or timestamp_value >= current[0]:
                latest_outputs[tool_name] = (timestamp_value, payload.get("content") or {})
            usage[tool_name] = usage.get(tool_name, 0) + 1
        outputs = {tool_name: content for tool_name, (_, content) in latest_outputs.items()}
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
