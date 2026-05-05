from optimizer.evaluation.aggregator import ResultAggregator


def test_aggregate_counts_done_without_complete_measurement_as_incomplete():
    aggregate = ResultAggregator().aggregate(
        [
            {
                "final_state": "DONE",
                "baseline_runtime": 10.0,
                "optimized_runtime": 8.0,
                "relative_speedup": 1.25,
            },
            {"final_state": "DONE"},
            {"final_state": "FAILED"},
        ]
    )

    assert aggregate["successful_runs"] == 1
    assert aggregate["failed_runs"] == 1
    assert aggregate["incomplete_runs"] == 1
