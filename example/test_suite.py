import math
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from data_processor import filter_and_transform, aggregate_scores
    from image_utils import apply_brightness, find_max_pixel
    from math_ops import get_unique_elements, slow_multiplication
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def test_data_processor():
    data = [1, 4, -1, 9]
    result = filter_and_transform(data)
    # Expected: [1*1/log(2), 4*2/log(2), 9*3/log(2)]
    log2 = math.log(2)
    expected = [1/log2, 8/log2, 27/log2]
    for r, e in zip(result, expected):
        assert abs(r - e) < 0.001
    
    scores = [[1, 2], [3, 4]]
    assert aggregate_scores(scores) == 10
    print("✅ data_processor tests passed")

def test_image_utils():
    buffer = [[10, 20], [30, 40]]
    apply_brightness(buffer, 2, 2, 2.0)
    assert buffer == [[20, 40], [60, 80]]
    assert find_max_pixel(buffer) == 80
    print("✅ image_utils tests passed")

def test_math_ops():
    items = [1, 2, 2, 3, 1, 4]
    assert get_unique_elements(items) == [1, 2, 3, 4]
    assert slow_multiplication(5, 3) == 15
    print("✅ math_ops tests passed")

if __name__ == "__main__":
    try:
        test_data_processor()
        test_image_utils()
        test_math_ops()
        print("\n🚀 ALL TESTS PASSED SUCCESSFULLY")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: Assertion Error")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
