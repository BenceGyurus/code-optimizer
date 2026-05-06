from pathlib import Path

from optimizer.evaluation.report import write_report


def test_report_distinguishes_final_and_accepted_runtime(tmp_path: Path) -> None:
    aggregate = {
        "total_runs": 1,
        "optimized_runs": 0,
        "verified_no_improvement_runs": 0,
        "no_effect_runs": 1,
        "failed_runs": 0,
        "incomplete_runs": 0,
        "fallback_runs": 0,
        "baseline_runtime": {"average": 10.0},
        "final_runtime": {"average": 10.5},
        "accepted_optimized_runtime": {"average": None},
        "post_rollback_runtime": {"average": 10.5},
        "relative_speedup": {"average": 0.95},
        "final_relative_speedup": {"average": 0.95},
        "accepted_relative_speedup": {"average": None},
        "attempted_relative_speedup": {"average": 0.95},
        "optimization_attempts": {"average": 2.0},
        "unsupported_hardware_counters": ["llc_loads", "llc_load_misses"],
        "rows": [
            {
                "provider": "mock",
                "model": "mock-model",
                "prompt_pack": "knowledge_gen",
                "repetition": 1,
                "final_state": "DONE",
                "run_outcome": "no_effect",
                "baseline_runtime": 10.0,
                "final_runtime": 10.5,
                "relative_speedup": 0.95,
                "final_relative_speedup": 0.95,
                "attempted_relative_speedup": 0.95,
                "verified_patch_applied": False,
                "fallback_applied": False,
                "performance_rollbacks": 2,
                "optimization_attempts": 2,
                "rejected_target_details": [
                    {"target": "hot_loop", "reason": "runtime regression", "relative_speedup": 0.95}
                ],
            }
        ],
    }

    report_path = Path(write_report(str(tmp_path), aggregate))
    text = report_path.read_text(encoding="utf-8")

    assert "Average final measured runtime" in text
    assert "Average accepted optimized runtime" in text
    assert "Average attempted patch speedup" in text
    assert "Unsupported hardware counters: LLC-loads, LLC-load-misses" in text
    assert "Rejected Optimization Attempts" in text
    assert "hot_loop" in text
