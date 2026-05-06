from typing import Dict, List

from optimizer.evaluation.metrics import summarize


class ResultAggregator:
    def aggregate(self, rows: List[Dict[str, object]]) -> Dict[str, object]:
        tool_usage_totals: Dict[str, int] = {}
        for row in rows:
            row["run_outcome"] = _run_outcome(row)
        for row in rows:
            tool_usage = row.get("tool_usage")
            if not isinstance(tool_usage, dict):
                continue
            for tool_name, count in tool_usage.items():
                if isinstance(count, int):
                    tool_usage_totals[tool_name] = tool_usage_totals.get(tool_name, 0) + count
        optimized_runs = sum(1 for row in rows if row.get("run_outcome") == "optimized")
        verified_no_improvement_runs = sum(
            1 for row in rows if row.get("run_outcome") == "verified_no_improvement"
        )
        no_effect_runs = sum(1 for row in rows if row.get("run_outcome") == "no_effect")
        failed_runs = sum(1 for row in rows if row.get("run_outcome") == "failed")
        incomplete_runs = sum(1 for row in rows if row.get("run_outcome") == "incomplete")

        return {
            "total_runs": len(rows),
            "optimized_runs": optimized_runs,
            "verified_no_improvement_runs": verified_no_improvement_runs,
            "no_effect_runs": no_effect_runs,
            "successful_runs": optimized_runs,
            "failed_runs": failed_runs,
            "incomplete_runs": incomplete_runs,
            "fallback_runs": sum(1 for row in rows if row.get("fallback_applied") is True),
            "fallback_count": summarize(_numeric_values(rows, "fallback_count")),
            "patch_apply_failures": summarize(_numeric_values(rows, "patch_apply_failures")),
            "verification_failures": summarize(_numeric_values(rows, "verification_failures")),
            "performance_rollbacks": summarize(_numeric_values(rows, "performance_rollbacks")),
            "patch_application_count": summarize(_numeric_values(rows, "patch_application_count")),
            "optimization_attempts": summarize(_numeric_values(rows, "optimization_attempts")),
            "baseline_runtime": summarize(_numeric_values(rows, "baseline_runtime")),
            "optimized_runtime": summarize(_numeric_values(rows, "optimized_runtime")),
            "final_runtime": summarize(_numeric_values(rows, "final_runtime")),
            "accepted_optimized_runtime": summarize(_numeric_values(rows, "accepted_optimized_runtime")),
            "post_rollback_runtime": summarize(_numeric_values(rows, "post_rollback_runtime")),
            "relative_speedup": summarize(_numeric_values(rows, "relative_speedup")),
            "final_relative_speedup": summarize(_numeric_values(rows, "final_relative_speedup")),
            "accepted_relative_speedup": summarize(_numeric_values(rows, "accepted_relative_speedup")),
            "attempted_relative_speedup": summarize(_numeric_values(rows, "attempted_relative_speedup")),
            "llm_calls": summarize(_numeric_values(rows, "llm_calls")),
            "llm_recoveries": summarize(_numeric_values(rows, "llm_recoveries")),
            "tool_calls": summarize(_numeric_values(rows, "tool_calls")),
            "iterations": summarize(_numeric_values(rows, "iterations")),
            "cache_hit_before": summarize(_nested_numeric_values(rows, "hardware_before", "cache_hit_rate")),
            "cache_hit_after": summarize(_nested_numeric_values(rows, "hardware_after", "cache_hit_rate")),
            "cache_miss_before": summarize(_nested_numeric_values(rows, "hardware_before", "cache_miss_rate")),
            "cache_miss_after": summarize(_nested_numeric_values(rows, "hardware_after", "cache_miss_rate")),
            "l1_hit_before": summarize(_nested_numeric_values(rows, "hardware_before", "l1_dcache_load_hit_rate")),
            "l1_hit_after": summarize(_nested_numeric_values(rows, "hardware_after", "l1_dcache_load_hit_rate")),
            "l1_miss_before": summarize(_nested_numeric_values(rows, "hardware_before", "l1_dcache_load_miss_rate")),
            "l1_miss_after": summarize(_nested_numeric_values(rows, "hardware_after", "l1_dcache_load_miss_rate")),
            "llc_hit_before": summarize(_nested_numeric_values(rows, "hardware_before", "llc_load_hit_rate")),
            "llc_hit_after": summarize(_nested_numeric_values(rows, "hardware_after", "llc_load_hit_rate")),
            "llc_miss_before": summarize(_nested_numeric_values(rows, "hardware_before", "llc_load_miss_rate")),
            "llc_miss_after": summarize(_nested_numeric_values(rows, "hardware_after", "llc_load_miss_rate")),
            "branch_miss_before": summarize(_nested_numeric_values(rows, "hardware_before", "branch_miss_rate")),
            "branch_miss_after": summarize(_nested_numeric_values(rows, "hardware_after", "branch_miss_rate")),
            "unsupported_hardware_counters": _unsupported_hardware_counters(rows),
            "tool_usage_totals": tool_usage_totals,
            "rows": rows,
        }


def _numeric_values(rows: List[Dict[str, object]], key: str) -> List[float]:
    values: List[float] = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def _nested_numeric_values(rows: List[Dict[str, object]], container_key: str, value_key: str) -> List[float]:
    values: List[float] = []
    for row in rows:
        container = row.get(container_key)
        if not isinstance(container, dict):
            continue
        value = container.get(value_key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def _unsupported_hardware_counters(rows: List[Dict[str, object]]) -> List[str]:
    counters: set[str] = set()
    for row in rows:
        values = row.get("unsupported_hardware_counters")
        if not isinstance(values, list):
            continue
        counters.update(str(value) for value in values if value)
    return sorted(counters)


def _is_successful_run(row: Dict[str, object]) -> bool:
    return _run_outcome(row) == "optimized"


def _run_outcome(row: Dict[str, object]) -> str:
    if row.get("final_state") == "FAILED":
        return "failed"
    if row.get("final_state") not in {"DONE", "REMEASURED"}:
        return "incomplete"
    measured = all(
        isinstance(row.get(key), (int, float))
        for key in ("baseline_runtime", "optimized_runtime", "relative_speedup")
    )
    if not measured:
        return "incomplete"
    if isinstance(row.get("performance_rollbacks"), (int, float)) and float(row.get("performance_rollbacks")) > 0:
        return "no_effect"
    if row.get("verified_patch_applied") is not True:
        return "no_effect"
    speedup = row.get("relative_speedup")
    if isinstance(speedup, (int, float)) and float(speedup) > 1.0:
        return "optimized"
    return "verified_no_improvement"
