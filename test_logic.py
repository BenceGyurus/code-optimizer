# Simple logic verification for complex_sample.py
import math
try:
    from complex_sample import analyze_sensor_data, find_duplicates_slow
    
    # Test 1: Sensor analysis
    data = [100, 4, None, -5]
    result = analyze_sensor_data(data)
    # Expected: [100 * sqrt(100) / log(10), 4 * sqrt(4) / log(10)]
    expected_0 = 100 * 10 / math.log(10)
    if abs(result[0] - expected_0) > 0.001:
        print(f"FAILED: Sensor analysis value mismatch. Got {result[0]}, expected {expected_0}")
        exit(1)
        
    # Test 2: Duplicates
    items = [1, 2, 3, 2, 4, 1]
    dupes = find_duplicates_slow(items)
    if set(dupes) != {1, 2}:
        print(f"FAILED: Duplicate detection logic broken. Got {dupes}, expected [1, 2]")
        exit(1)

    print("SUCCESS: All logic tests passed.")
    exit(0)
except Exception as e:
    print(f"FAILED: Test execution error: {e}")
    exit(1)
