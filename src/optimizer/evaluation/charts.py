import math
import os
from typing import Dict, Iterable, List, Sequence


def write_charts(charts_dir: str, aggregate: Dict[str, object]) -> None:
    os.makedirs(charts_dir, exist_ok=True)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError(
            "Chart generation requires matplotlib. Install it with "
            "`PYTHONPATH=src .venv/bin/python -m pip install matplotlib`."
        ) from exc

    rows = aggregate.get("rows") or []
    labels = [_run_label(row, index) for index, row in enumerate(rows, start=1)]

    _runtime_chart(plt, os.path.join(charts_dir, "runtime_baseline_vs_optimized.png"), labels, rows)
    _speedup_chart(plt, os.path.join(charts_dir, "relative_speedup.png"), labels, rows)
    _before_after_chart(
        plt,
        os.path.join(charts_dir, "cache_hit_before_after.png"),
        labels,
        rows,
        "cache_hit_rate",
        "cache hit rate",
        "Cache Hit Before/After",
    )
    _before_after_chart(
        plt,
        os.path.join(charts_dir, "cache_miss_before_after.png"),
        labels,
        rows,
        "cache_miss_rate",
        "cache miss rate",
        "Cache Miss Before/After",
    )
    _before_after_chart(
        plt,
        os.path.join(charts_dir, "l1_cache_hit_before_after.png"),
        labels,
        rows,
        "l1_dcache_load_hit_rate",
        "L1 data cache hit rate",
        "L1 Data Cache Hit Before/After",
    )
    _before_after_chart(
        plt,
        os.path.join(charts_dir, "l1_cache_miss_before_after.png"),
        labels,
        rows,
        "l1_dcache_load_miss_rate",
        "L1 data cache miss rate",
        "L1 Data Cache Miss Before/After",
    )
    _before_after_chart(
        plt,
        os.path.join(charts_dir, "llc_cache_hit_before_after.png"),
        labels,
        rows,
        "llc_load_hit_rate",
        "LLC hit rate",
        "LLC Hit Before/After",
    )
    _before_after_chart(
        plt,
        os.path.join(charts_dir, "llc_cache_miss_before_after.png"),
        labels,
        rows,
        "llc_load_miss_rate",
        "LLC miss rate",
        "LLC Miss Before/After",
    )
    _before_after_chart(
        plt,
        os.path.join(charts_dir, "branch_miss_before_after.png"),
        labels,
        rows,
        "branch_miss_rate",
        "branch miss rate",
        "Branch Miss Before/After",
    )
    _metric_chart(plt, os.path.join(charts_dir, "llm_calls_per_run.png"), labels, rows, "llm_calls", "LLM Calls Per Run", "calls")
    _metric_chart(plt, os.path.join(charts_dir, "tool_calls_per_run.png"), labels, rows, "tool_calls", "Tool Calls Per Run", "calls")
    _metric_chart(
        plt,
        os.path.join(charts_dir, "optimization_attempts_per_run.png"),
        labels,
        rows,
        "optimization_attempts",
        "Optimization Attempts Per Run",
        "attempts",
    )
    _tool_usage_chart(plt, os.path.join(charts_dir, "tool_usage.png"), aggregate.get("tool_usage_totals") or {})
    _success_failure_chart(
        plt,
        os.path.join(charts_dir, "success_failure.png"),
        int(aggregate.get("optimized_runs") or aggregate.get("successful_runs") or 0),
        int(aggregate.get("verified_no_improvement_runs") or 0),
        int(aggregate.get("no_effect_runs") or 0),
        int(aggregate.get("failed_runs") or 0),
        int(aggregate.get("incomplete_runs") or 0),
    )


def _runtime_chart(plt, path: str, labels: Sequence[str], rows: Sequence[Dict[str, object]]) -> None:
    baseline = [_float_or_none(row.get("baseline_runtime")) for row in rows]
    final = [_float_or_none(row.get("final_runtime") if row.get("final_runtime") is not None else row.get("optimized_runtime")) for row in rows]
    fig, ax = plt.subplots(figsize=(10, 5))
    if not any(value is not None for value in baseline + final):
        _draw_no_data(ax, "No runtime data available.")
    else:
        positions = list(range(len(labels)))
        width = 0.38
        ax.bar([index - width / 2 for index in positions], _missing_as_nan(baseline), width=width, label="baseline", color="#64748b")
        ax.bar([index + width / 2 for index in positions], _missing_as_nan(final), width=width, label="final measured", color="#2563eb")
        ax.set_xticks(positions, labels, rotation=20, ha="right")
        ax.set_ylabel("seconds")
        ax.set_title("Baseline vs Final Runtime")
        ax.legend()
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _speedup_chart(plt, path: str, labels: Sequence[str], rows: Sequence[Dict[str, object]]) -> None:
    speedups = [_float_or_none(row.get("relative_speedup")) for row in rows]
    fig, ax = plt.subplots(figsize=(10, 5))
    if not any(value is not None for value in speedups):
        _draw_no_data(ax, "No speedup data available.")
    else:
        positions = list(range(len(labels)))
        ax.bar(positions, _missing_as_nan(speedups), color="#16a34a")
        ax.axhline(1.0, color="#111827", linestyle="--", linewidth=1)
        ax.set_xticks(positions, labels, rotation=20, ha="right")
        ax.set_ylabel("speedup")
        ax.set_title("Relative Final Speedup")
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _before_after_chart(plt, path: str, labels: Sequence[str], rows: Sequence[Dict[str, object]], key: str, ylabel: str, title: str) -> None:
    before = [_nested_float(row, "hardware_before", key) for row in rows]
    after = [_nested_float(row, "hardware_after", key) for row in rows]
    fig, ax = plt.subplots(figsize=(10, 5))
    if not any(value is not None for value in before + after):
        _draw_no_data(ax, _no_data_message(rows, key, ylabel))
    else:
        positions = list(range(len(labels)))
        width = 0.38
        ax.bar([index - width / 2 for index in positions], _missing_as_nan(before), width=width, label="before", color="#f59e0b")
        ax.bar([index + width / 2 for index in positions], _missing_as_nan(after), width=width, label="after", color="#0f766e")
        ax.set_xticks(positions, labels, rotation=20, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend()
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _tool_usage_chart(plt, path: str, tool_usage: Dict[str, object]) -> None:
    names = list(tool_usage.keys())
    counts = [_float_or_none(tool_usage.get(name)) or 0.0 for name in names]
    fig, ax = plt.subplots(figsize=(10, 5))
    if not names:
        _draw_no_data(ax, "No tool usage data available.")
    else:
        ax.barh(names, counts, color="#7c3aed")
        ax.set_xlabel("calls")
        ax.set_title("Tool Usage")
        ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _metric_chart(plt, path: str, labels: Sequence[str], rows: Sequence[Dict[str, object]], key: str, title: str, ylabel: str) -> None:
    values = [_float_or_none(row.get(key)) for row in rows]
    fig, ax = plt.subplots(figsize=(10, 5))
    if not any(value is not None for value in values):
        _draw_no_data(ax, f"No {ylabel} data available.")
    else:
        positions = list(range(len(labels)))
        ax.bar(positions, _missing_as_nan(values), color="#1d4ed8")
        ax.set_xticks(positions, labels, rotation=20, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _success_failure_chart(
    plt,
    path: str,
    optimized_runs: int,
    verified_no_improvement_runs: int,
    no_effect_runs: int,
    failed_runs: int,
    incomplete_runs: int,
) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    total = optimized_runs + verified_no_improvement_runs + no_effect_runs + failed_runs + incomplete_runs
    if total == 0:
        _draw_no_data(ax, "No run outcomes available.")
    else:
        slices = [
            ("optimized", optimized_runs, "#16a34a"),
            ("verified no improvement", verified_no_improvement_runs, "#f97316"),
            ("no effect", no_effect_runs, "#f59e0b"),
            ("failure", failed_runs, "#dc2626"),
            ("incomplete", incomplete_runs, "#64748b"),
        ]
        slices = [item for item in slices if item[1] > 0]
        labels = [item[0] for item in slices]
        values = [item[1] for item in slices]
        colors = [item[2] for item in slices]
        ax.pie(values, labels=labels, autopct="%1.0f%%", startangle=90, colors=colors)
        ax.set_title("Run Outcome Split")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _draw_no_data(ax, message: str) -> None:
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12)


def _run_label(row: Dict[str, object], index: int) -> str:
    provider = row.get("provider") or "provider"
    model = row.get("model") or "default"
    prompt_pack = row.get("prompt_pack") or "prompt"
    repetition = row.get("repetition") or index
    return f"{provider}:{model}:{prompt_pack}#{repetition}"


def _missing_as_nan(values: Iterable[float | None]) -> List[float]:
    return [math.nan if value is None else float(value) for value in values]


def _float_or_none(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _nested_float(row: Dict[str, object], container_key: str, value_key: str) -> float | None:
    container = row.get(container_key)
    if not isinstance(container, dict):
        return None
    return _float_or_none(container.get(value_key))


def _no_data_message(rows: Sequence[Dict[str, object]], key: str, ylabel: str) -> str:
    if key.startswith("llc_") and any(_has_unsupported_llc(row) for row in rows):
        return "LLC counters unsupported on this machine."
    return f"No {ylabel} data available. Supply --profile-command."


def _has_unsupported_llc(row: Dict[str, object]) -> bool:
    counters = row.get("unsupported_hardware_counters")
    if not isinstance(counters, list):
        return False
    return any(str(counter) in {"llc_loads", "llc_load_misses"} for counter in counters)
