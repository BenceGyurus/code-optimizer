import re
from typing import Any, List, Optional

from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult


class EvaluateResultTool(Tool):
    """Compares latest measurement against baseline and decides whether to stop."""

    @property
    def name(self) -> str:
        return "evaluate_result"

    @property
    def allowed_states(self) -> List[State]:
        return [State.REMEASURED]

    def execute(
        self,
        baseline_runtime: Optional[float] = None,
        optimized_runtime: Optional[float] = None,
        baseline_result: Optional[dict] = None,
        optimized_result: Optional[dict] = None,
        target_speedup: float = 1.01,
        continue_optimization: bool = False,
        **_: object,
    ) -> ToolResult:
        baseline_runtime = baseline_runtime or _extract_runtime(baseline_result)
        optimized_runtime = optimized_runtime or _extract_runtime(optimized_result)

        speedup = None
        if baseline_runtime and optimized_runtime and optimized_runtime > 0:
            speedup = baseline_runtime / optimized_runtime
            continue_optimization = speedup < target_speedup

        output = {
            "baseline_runtime": baseline_runtime,
            "optimized_runtime": optimized_runtime,
            "relative_speedup": speedup,
            "decision": "continue" if continue_optimization else "stop",
        }
        return ToolResult(
            success=True,
            output=output,
            next_state=State.ANALYSIS_READY if continue_optimization else State.DONE,
            metadata=output,
        )


def _extract_runtime(result: Any) -> Optional[float]:
    if isinstance(result, list):
        values = [_runtime_from_run(run) for run in result]
        values = [value for value in values if value is not None]
        return _average(values)

    if not isinstance(result, dict):
        return None

    benchmark = result.get("benchmark")
    if isinstance(benchmark, dict):
        from_runs = _extract_runtime(benchmark.get("runs"))
        if from_runs is not None:
            return from_runs
        explicit = _first_number(benchmark, ["average_duration", "duration", "min_duration"])
        if explicit is not None:
            return explicit

    if isinstance(benchmark, list):
        return _extract_runtime(benchmark)

    if "runs" in result:
        return _extract_runtime({"benchmark": result["runs"]})

    return _runtime_from_run(result)


def _runtime_from_run(run: Any) -> Optional[float]:
    if not isinstance(run, dict):
        return None
    parsed = _parse_best_seconds(run.get("stdout") or run.get("output") or "")
    if parsed is not None:
        return parsed
    return _first_number(run, ["duration"])


def _parse_best_seconds(stdout: str) -> Optional[float]:
    matches = re.findall(r"best_seconds=([0-9]+(?:\.[0-9]+)?)", stdout or "")
    if not matches:
        return None
    return _average(float(value) for value in matches)


def _first_number(mapping: dict, keys: list[str]) -> Optional[float]:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _average(values) -> Optional[float]:
    numbers = list(values)
    if not numbers:
        return None
    return sum(numbers) / len(numbers)
