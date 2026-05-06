import os
from typing import Dict


def write_report(eval_dir: str, aggregate: Dict[str, object]) -> str:
    path = os.path.join(eval_dir, "report.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# Evaluation Report\n\n")
        handle.write(f"- Total runs: {aggregate.get('total_runs')}\n")
        handle.write(f"- Optimized runs: {aggregate.get('optimized_runs', aggregate.get('successful_runs'))}\n")
        handle.write(f"- Verified but not faster runs: {aggregate.get('verified_no_improvement_runs')}\n")
        handle.write(f"- No-effect measured runs: {aggregate.get('no_effect_runs')}\n")
        handle.write(f"- Failed runs: {aggregate.get('failed_runs')}\n")
        handle.write(f"- Incomplete runs: {aggregate.get('incomplete_runs')}\n")
        handle.write(f"- Runs using deterministic fallback: {aggregate.get('fallback_runs')}\n")
        handle.write(f"- Average deterministic fallbacks per run: {_fmt_summary(aggregate.get('fallback_count'))}\n")
        handle.write(f"- Average patch apply failures per run: {_fmt_summary(aggregate.get('patch_apply_failures'))}\n")
        handle.write(f"- Average verification failures per run: {_fmt_summary(aggregate.get('verification_failures'))}\n")
        handle.write(f"- Average performance rollbacks per run: {_fmt_summary(aggregate.get('performance_rollbacks'))}\n")
        handle.write(f"- Average model patch applications per run: {_fmt_summary(aggregate.get('patch_application_count'))}\n")
        handle.write(f"- Average optimization attempts per run: {_fmt_summary(aggregate.get('optimization_attempts'))}\n")
        handle.write(f"- Average baseline runtime: {_fmt_summary(aggregate.get('baseline_runtime'))}\n")
        handle.write(f"- Average final measured runtime: {_fmt_summary(aggregate.get('final_runtime') or aggregate.get('optimized_runtime'))}\n")
        handle.write(f"- Average accepted optimized runtime: {_fmt_summary(aggregate.get('accepted_optimized_runtime'))}\n")
        handle.write(f"- Average post-rollback runtime: {_fmt_summary(aggregate.get('post_rollback_runtime'))}\n")
        handle.write(f"- Average final measured speedup: {_fmt_summary(aggregate.get('final_relative_speedup') or aggregate.get('relative_speedup'))}\n")
        handle.write(f"- Average accepted speedup: {_fmt_summary(aggregate.get('accepted_relative_speedup'))}\n")
        handle.write(f"- Average attempted patch speedup: {_fmt_summary(aggregate.get('attempted_relative_speedup'))}\n")
        handle.write(f"- Average cache hit before: {_fmt_summary(aggregate.get('cache_hit_before'))}\n")
        handle.write(f"- Average cache hit after: {_fmt_summary(aggregate.get('cache_hit_after'))}\n")
        handle.write(f"- Average cache miss before: {_fmt_summary(aggregate.get('cache_miss_before'))}\n")
        handle.write(f"- Average cache miss after: {_fmt_summary(aggregate.get('cache_miss_after'))}\n")
        handle.write(f"- Average L1 hit before: {_fmt_summary(aggregate.get('l1_hit_before'))}\n")
        handle.write(f"- Average L1 hit after: {_fmt_summary(aggregate.get('l1_hit_after'))}\n")
        handle.write(f"- Average LLC hit before: {_fmt_summary(aggregate.get('llc_hit_before'))}\n")
        handle.write(f"- Average LLC hit after: {_fmt_summary(aggregate.get('llc_hit_after'))}\n")
        handle.write(f"- Average branch miss before: {_fmt_summary(aggregate.get('branch_miss_before'))}\n")
        handle.write(f"- Average branch miss after: {_fmt_summary(aggregate.get('branch_miss_after'))}\n")
        handle.write(f"- Average LLM calls: {_fmt_summary(aggregate.get('llm_calls'))}\n")
        handle.write(f"- Average LLM recoveries per run: {_fmt_summary(aggregate.get('llm_recoveries'))}\n")
        handle.write(f"- Average tool calls: {_fmt_summary(aggregate.get('tool_calls'))}\n")
        handle.write(f"- Average iterations: {_fmt_summary(aggregate.get('iterations'))}\n")
        unsupported = aggregate.get("unsupported_hardware_counters") or []
        if unsupported:
            handle.write(f"- Unsupported hardware counters: {', '.join(_human_counter_name(value) for value in _ordered_counters(unsupported))}\n")
        rows = sorted(aggregate.get("rows") or [], key=_sort_key, reverse=True)
        if rows:
            handle.write("\n## Per-Run Summary\n\n")
            handle.write("| provider | model | prompt_pack | rep | state | outcome | baseline_s | final_s | accepted_opt_s | final_speedup | accepted_speedup | attempted_speedup | patch_verified | fallback | patch_failures | verification_failures | performance_rollbacks | attempts | cache_hit_before | cache_hit_after | llm_calls | tool_calls |\n")
            handle.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
            for row in rows:
                handle.write(
                    "| "
                    f"{row.get('provider', 'n/a')} | "
                    f"{row.get('model', 'n/a')} | "
                    f"{row.get('prompt_pack', 'n/a')} | "
                    f"{row.get('repetition', 'n/a')} | "
                    f"{row.get('final_state', 'n/a')} | "
                    f"{_run_outcome(row)} | "
                    f"{_fmt_value(row.get('baseline_runtime'))} | "
                    f"{_fmt_value(row.get('final_runtime') if row.get('final_runtime') is not None else row.get('optimized_runtime'))} | "
                    f"{_fmt_value(row.get('accepted_optimized_runtime'))} | "
                    f"{_fmt_value(row.get('final_relative_speedup') if row.get('final_relative_speedup') is not None else row.get('relative_speedup'))} | "
                    f"{_fmt_value(row.get('accepted_relative_speedup'))} | "
                    f"{_fmt_value(row.get('attempted_relative_speedup'))} | "
                    f"{_fmt_bool(row.get('verified_patch_applied'))} | "
                    f"{_fmt_bool(row.get('fallback_applied'))} | "
                    f"{_fmt_value(row.get('patch_apply_failures'))} | "
                    f"{_fmt_value(row.get('verification_failures'))} | "
                    f"{_fmt_value(row.get('performance_rollbacks'))} | "
                    f"{_fmt_value(row.get('optimization_attempts'))} | "
                    f"{_fmt_nested_value(row.get('hardware_before'), 'cache_hit_rate')} | "
                    f"{_fmt_nested_value(row.get('hardware_after'), 'cache_hit_rate')} | "
                    f"{_fmt_value(row.get('llm_calls'))} | "
                    f"{_fmt_value(row.get('tool_calls'))} |\n"
                )
            rejected_rows = _rejected_attempt_rows(rows)
            if rejected_rows:
                handle.write("\n## Rejected Optimization Attempts\n\n")
                handle.write("| provider | model | prompt_pack | rep | target | reason | speedup |\n")
                handle.write("| --- | --- | --- | --- | --- | --- | --- |\n")
                for row, detail in rejected_rows:
                    handle.write(
                        "| "
                        f"{row.get('provider', 'n/a')} | "
                        f"{row.get('model', 'n/a')} | "
                        f"{row.get('prompt_pack', 'n/a')} | "
                        f"{row.get('repetition', 'n/a')} | "
                        f"{detail.get('target', 'n/a')} | "
                        f"{_escape_table_text(detail.get('reason') or '')} | "
                        f"{_fmt_value(detail.get('relative_speedup'))} |\n"
                    )
    return path


def _fmt_summary(summary: object) -> str:
    if not isinstance(summary, dict):
        return "n/a"
    average = summary.get("average")
    if isinstance(average, (int, float)):
        return f"{average:.6f}"
    return "n/a"


def _fmt_value(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.6f}"
    return "n/a"


def _fmt_bool(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return "n/a"


def _fmt_nested_value(container: object, key: str) -> str:
    if isinstance(container, dict):
        value = container.get(key)
        if isinstance(value, (int, float)):
            return f"{float(value):.6f}"
    return "n/a"


def _sort_key(row: dict) -> tuple[float, float]:
    speedup = row.get("relative_speedup")
    optimized = row.get("optimized_runtime")
    speedup_value = float(speedup) if isinstance(speedup, (int, float)) else float("-inf")
    optimized_value = -float(optimized) if isinstance(optimized, (int, float)) else float("-inf")
    return speedup_value, optimized_value


def _rejected_attempt_rows(rows: list[dict]) -> list[tuple[dict, dict]]:
    rejected: list[tuple[dict, dict]] = []
    for row in rows:
        details = row.get("rejected_target_details")
        if not isinstance(details, list):
            continue
        for detail in details:
            if isinstance(detail, dict) and detail.get("target"):
                rejected.append((row, detail))
    return rejected


def _human_counter_name(value: object) -> str:
    text = str(value)
    names = {
        "llc_loads": "LLC-loads",
        "llc_load_misses": "LLC-load-misses",
        "l1_dcache_loads": "L1-dcache-loads",
        "l1_dcache_load_misses": "L1-dcache-load-misses",
        "cache_references": "cache-references",
        "cache_misses": "cache-misses",
        "branch_misses": "branch-misses",
    }
    return names.get(text, text)


def _ordered_counters(values: object) -> list[object]:
    if not isinstance(values, list):
        return []
    order = {
        "cache_references": 0,
        "cache_misses": 1,
        "l1_dcache_loads": 2,
        "l1_dcache_load_misses": 3,
        "llc_loads": 4,
        "llc_load_misses": 5,
        "branches": 6,
        "branch_misses": 7,
    }
    return sorted(values, key=lambda value: (order.get(str(value), 100), str(value)))


def _escape_table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _run_outcome(row: dict) -> str:
    outcome = row.get("run_outcome")
    if isinstance(outcome, str):
        return outcome
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
