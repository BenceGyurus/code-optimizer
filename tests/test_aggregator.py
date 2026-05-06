import pytest

from optimizer.evaluation.aggregator import ResultAggregator


def test_aggregate_counts_run_outcomes():
    aggregate = ResultAggregator().aggregate(
        [
            {
                "final_state": "DONE",
                "baseline_runtime": 10.0,
                "optimized_runtime": 8.0,
                "final_runtime": 8.0,
                "accepted_optimized_runtime": 8.0,
                "relative_speedup": 1.25,
                "final_relative_speedup": 1.25,
                "accepted_relative_speedup": 1.25,
                "attempted_relative_speedup": 1.25,
                "verified_patch_applied": True,
                "verification_failures": 0,
                "optimization_attempts": 1,
                "unsupported_hardware_counters": ["llc_loads"],
            },
            {
                "final_state": "DONE",
                "baseline_runtime": 10.0,
                "optimized_runtime": 11.0,
                "final_runtime": 11.0,
                "relative_speedup": 0.91,
                "final_relative_speedup": 0.91,
                "accepted_relative_speedup": 0.91,
                "attempted_relative_speedup": 0.91,
                "verified_patch_applied": True,
                "verification_failures": 1,
                "optimization_attempts": 1,
            },
            {
                "final_state": "DONE",
                "baseline_runtime": 10.0,
                "optimized_runtime": 9.5,
                "final_runtime": 9.5,
                "post_rollback_runtime": 9.5,
                "relative_speedup": 1.05,
                "final_relative_speedup": 1.05,
                "attempted_relative_speedup": 0.95,
                "verified_patch_applied": False,
                "performance_rollbacks": 1,
                "optimization_attempts": 2,
                "unsupported_hardware_counters": ["llc_load_misses"],
            },
            {"final_state": "DONE", "verified_patch_applied": True},
            {"final_state": "FAILED"},
        ]
    )

    assert aggregate["successful_runs"] == 1
    assert aggregate["optimized_runs"] == 1
    assert aggregate["verified_no_improvement_runs"] == 1
    assert aggregate["no_effect_runs"] == 1
    assert aggregate["failed_runs"] == 1
    assert aggregate["incomplete_runs"] == 1
    assert aggregate["verification_failures"]["average"] == 0.5
    assert aggregate["performance_rollbacks"]["average"] == 1.0
    assert aggregate["optimization_attempts"]["average"] == 4 / 3
    assert aggregate["final_runtime"]["average"] == 9.5
    assert aggregate["accepted_optimized_runtime"]["average"] == 8.0
    assert aggregate["post_rollback_runtime"]["average"] == 9.5
    assert aggregate["final_relative_speedup"]["average"] == 1.07
    assert aggregate["accepted_relative_speedup"]["average"] == 1.08
    assert aggregate["attempted_relative_speedup"]["average"] == pytest.approx(1.0366666667)
    assert aggregate["unsupported_hardware_counters"] == ["llc_load_misses", "llc_loads"]
    assert [row["run_outcome"] for row in aggregate["rows"]] == [
        "optimized",
        "verified_no_improvement",
        "no_effect",
        "incomplete",
        "failed",
    ]
