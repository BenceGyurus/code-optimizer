import math

from complex_sample import analyze_sensor_data, find_duplicates_slow


def test_analyze_sensor_data():
    data = [100, 4, None, -5]
    result = analyze_sensor_data(data)
    expected_0 = 100 * 10 / math.log(10)
    assert abs(result[0] - expected_0) <= 0.001


def test_find_duplicates_slow():
    items = [1, 2, 3, 2, 4, 1]
    dupes = find_duplicates_slow(items)
    assert set(dupes) == {1, 2}
