import os
from typing import Dict


def write_report(eval_dir: str, aggregate: Dict[str, object]) -> str:
    path = os.path.join(eval_dir, "report.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# Evaluation Report\n\n")
        handle.write(f"- Total runs: {aggregate.get('total_runs')}\n")
        handle.write(f"- Successful runs: {aggregate.get('successful_runs')}\n")
        handle.write(f"- Failed runs: {aggregate.get('failed_runs')}\n")
        handle.write(f"- Incomplete runs: {aggregate.get('incomplete_runs')}\n")
        handle.write(f"- Runs using deterministic fallback: {aggregate.get('fallback_runs')}\n")
        handle.write(f"- Average deterministic fallbacks per run: {_fmt_summary(aggregate.get('fallback_count'))}\n")
        handle.write(f"- Average patch apply failures per run: {_fmt_summary(aggregate.get('patch_apply_failures'))}\n")
        handle.write(f"- Average baseline runtime: {_fmt_summary(aggregate.get('baseline_runtime'))}\n")
        handle.write(f"- Average optimized runtime: {_fmt_summary(aggregate.get('optimized_runtime'))}\n")
        handle.write(f"- Average relative speedup: {_fmt_summary(aggregate.get('relative_speedup'))}\n")
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
        rows = sorted(aggregate.get("rows") or [], key=_sort_key, reverse=True)
        if rows:
            handle.write("\n## Per-Run Summary\n\n")
            handle.write("| provider | model | prompt_pack | rep | state | quality | baseline_s | optimized_s | speedup | fallback | patch_failures | cache_hit_before | cache_hit_after | llm_calls | tool_calls | iterations |\n")
            handle.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
            for row in rows:
                handle.write(
                    "| "
                    f"{row.get('provider', 'n/a')} | "
                    f"{row.get('model', 'n/a')} | "
                    f"{row.get('prompt_pack', 'n/a')} | "
                    f"{row.get('repetition', 'n/a')} | "
                    f"{row.get('final_state', 'n/a')} | "
                    f"{_run_quality(row)} | "
                    f"{_fmt_value(row.get('baseline_runtime'))} | "
                    f"{_fmt_value(row.get('optimized_runtime'))} | "
                    f"{_fmt_value(row.get('relative_speedup'))} | "
                    f"{_fmt_bool(row.get('fallback_applied'))} | "
                    f"{_fmt_value(row.get('patch_apply_failures'))} | "
                    f"{_fmt_nested_value(row.get('hardware_before'), 'cache_hit_rate')} | "
                    f"{_fmt_nested_value(row.get('hardware_after'), 'cache_hit_rate')} | "
                    f"{_fmt_value(row.get('llm_calls'))} | "
                    f"{_fmt_value(row.get('tool_calls'))} | "
                    f"{_fmt_value(row.get('iterations'))} |\n"
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


def _run_quality(row: dict) -> str:
    if row.get("final_state") == "FAILED":
        return "failed"
    if row.get("final_state") not in {"DONE", "REMEASURED"}:
        return "incomplete"
    if all(
        isinstance(row.get(key), (int, float))
        for key in ("baseline_runtime", "optimized_runtime", "relative_speedup")
    ):
        return "measured"
    return "incomplete"
