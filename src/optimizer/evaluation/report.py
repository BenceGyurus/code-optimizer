import os
from typing import Dict


def write_report(eval_dir: str, aggregate: Dict[str, object]) -> str:
    path = os.path.join(eval_dir, "report.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("# Evaluation Report\n\n")
        handle.write(f"- Total runs: {aggregate.get('total_runs')}\n")
        handle.write(f"- Successful runs: {aggregate.get('successful_runs')}\n")
        handle.write(f"- Failed runs: {aggregate.get('failed_runs')}\n")
        handle.write(f"- Average baseline runtime: {_fmt_summary(aggregate.get('baseline_runtime'))}\n")
        handle.write(f"- Average optimized runtime: {_fmt_summary(aggregate.get('optimized_runtime'))}\n")
        handle.write(f"- Average relative speedup: {_fmt_summary(aggregate.get('relative_speedup'))}\n")
    return path


def _fmt_summary(summary: object) -> str:
    if not isinstance(summary, dict):
        return "n/a"
    average = summary.get("average")
    if isinstance(average, (int, float)):
        return f"{average:.6f}"
    return "n/a"
