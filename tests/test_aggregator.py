from optimizer.evaluation.aggregator import ResultAggregator


def test_aggregate_counts_run_outcomes():
    aggregate = ResultAggregator().aggregate(
        [
            {
                "final_state": "DONE",
                "baseline_runtime": 10.0,
                "optimized_runtime": 8.0,
                "relative_speedup": 1.25,
                "verified_patch_applied": True,
                "verification_failures": 0,
            },
            {
                "final_state": "DONE",
                "baseline_runtime": 10.0,
                "optimized_runtime": 11.0,
                "relative_speedup": 0.91,
                "verified_patch_applied": True,
                "verification_failures": 1,
            },
            {
                "final_state": "DONE",
                "baseline_runtime": 10.0,
                "optimized_runtime": 9.5,
                "relative_speedup": 1.05,
                "verified_patch_applied": False,
                "performance_rollbacks": 1,
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
    assert [row["run_outcome"] for row in aggregate["rows"]] == [
        "optimized",
        "verified_no_improvement",
        "no_effect",
        "incomplete",
        "failed",
    ]
