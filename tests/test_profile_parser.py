from optimizer.tools.profile_parser import parse_hardware_counters


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
