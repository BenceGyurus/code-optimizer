import math
import time

def analyze_sensor_data(sensor_readings):
    """
    Simulates processing a large list of sensor data.
    Contains: Inefficient loop, repeated calculations.
    """
    processed = []
    # Hotspot 1: List comprehension candidate + unnecessary calculation
    import math
    log_10 = math.log(10)
    for val in sensor_readings:
        if val is not None and val > 0:
            calc = val * math.sqrt(val) / log_10
            processed.append(calc)
    return processed

def optimize_image_buffer(buffer, width, height):
    """
    Simulates image processing with 2D buffers.
    Contains: Potential cache locality issues if access pattern is wrong.
    """
    # Hotspot 2: Nested loops - can be improved for readability/performance
    import numpy as np

    buffer = np.clip(buffer, 0, 255)
    return buffer

def find_duplicates_slow(items):
    """
    Extremely inefficient duplicate check (O(N^2)).
    The AST should catch this nested loop.
    """
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                if items[i] not in duplicates:
                    duplicates.append(items[i])
        if items[i] not in duplicates:
                for j in range(i + 1, len(items)):
                        if items[i] == items[j]:
                            duplicates.append(items[i])
                            break
    data = [i for i in range(1000)]
    
    start = time.time()
    analyze_sensor_data(data)
    print(f"Sensor analysis took: {time.time() - start:.4f}s")
    
    matrix = [[i+j for i in range(100)] for j in range(100)]
    start = time.time()
    optimize_image_buffer(matrix, 100, 100)
    print(f"Buffer optimization took: {time.time() - start:.4f}s")
