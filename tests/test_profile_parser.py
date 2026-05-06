from optimizer.tools.profile_parser import (
    filter_project_function_hotspots,
    parse_function_profile,
    parse_hardware_counters,
    parse_unsupported_counters,
    summarize_function_profile_runs,
)


def test_parse_hardware_counters_adds_hit_rates():
    counters = parse_hardware_counters(
        stderr="""
           2,500 cache-references
             500 cache-misses
           1,000 branches
             100 branch-misses
        """
    )

    assert counters["cache_miss_rate"] == 0.2
    assert counters["cache_hit_rate"] == 0.8
    assert counters["branch_miss_rate"] == 0.1
    assert counters["branch_hit_rate"] == 0.9


def test_parse_unsupported_counters_normalizes_perf_events():
    unsupported = parse_unsupported_counters(
        stderr="""
   <not supported>      LLC-loads
   <not supported>      LLC-load-misses
        """
    )

    assert unsupported == ["llc_load_misses", "llc_loads"]


def test_parse_function_profile_extracts_project_hotspots():
    profile = parse_function_profile(
        stdout="""
         642067 function calls in 3.057 seconds

   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    2.555    2.555 heavy_compute.py:171(segmented_prefix_sums_slow)
     10/1    0.100    0.010    0.216    0.216 heavy_compute.py:95(join_events_to_users_slow)
        1    0.020    0.020    0.020    0.020 {built-in method builtins.sum}
        """,
    )

    entries = profile["entries"]

    assert profile["total_seconds"] == 3.057
    assert entries[0]["function"] == "segmented_prefix_sums_slow"
    assert entries[0]["file"] == "heavy_compute.py"
    assert entries[0]["line"] == 171
    assert entries[0]["cumtime"] == 2.555
    assert round(entries[0]["percent_cumtime"], 2) == 83.58
    assert entries[1]["primitive_calls"] == 1.0
    assert entries[1]["total_calls"] == 10.0


def test_summarize_function_profile_runs_filters_project_file():
    first = parse_function_profile(
        stdout="""
         10 function calls in 2.000 seconds

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    1.500    1.500 heavy_compute.py:171(segmented_prefix_sums_slow)
        1    0.000    0.000    0.400    0.400 other.py:10(noise)
        """,
    )
    second = parse_function_profile(
        stdout="""
         10 function calls in 4.000 seconds

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    2.500    2.500 heavy_compute.py:171(segmented_prefix_sums_slow)
        1    0.000    0.000    0.800    0.800 other.py:10(noise)
        """,
    )

    summarized = summarize_function_profile_runs([first, second])
    filtered = filter_project_function_hotspots(summarized, "/tmp/heavy_compute.py")

    assert filtered == [
        {
            "function": "segmented_prefix_sums_slow",
            "file": "heavy_compute.py",
            "line": 171,
            "average_cumtime": 2.0,
            "average_tottime": 0.0,
            "average_percent_cumtime": 68.75,
            "average_primitive_calls": 1.0,
            "runs": 2,
        }
    ]


def test_filter_project_function_hotspots_skips_wrappers_and_generators():
    hotspots = [
        {"function": "<module>", "file": "heavy_compute.py", "line": 1, "average_cumtime": 10.0},
        {"function": "run_benchmark", "file": "heavy_compute.py", "line": 300, "average_cumtime": 9.0},
        {"function": "workload", "file": "heavy_compute.py", "line": 250, "average_cumtime": 8.0},
        {"function": "generate_events", "file": "heavy_compute.py", "line": 230, "average_cumtime": 2.0},
        {"function": "segmented_prefix_sums_slow", "file": "heavy_compute.py", "line": 171, "average_cumtime": 7.0},
        {"function": "join_events_to_users_slow", "file": "heavy_compute.py", "line": 43, "average_cumtime": 1.0},
    ]

    filtered = filter_project_function_hotspots(hotspots, "/tmp/heavy_compute.py")

    assert [item["function"] for item in filtered] == [
        "segmented_prefix_sums_slow",
        "join_events_to_users_slow",
    ]
