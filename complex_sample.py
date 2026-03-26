import math
import time

try:
    import numpy as np
except Exception:
    np = None



def analyze_sensor_data(sensor_readings):
    """
    Simulates processing a large list of sensor data.
    Contains: Inefficient loop, repeated calculations.
    """
    processed = []
    # Hotspot 1: List comprehension candidate + unnecessary calculation
    log_10 = math.log(10)
    inv_log_10 = 1 / log_10
    for val in sensor_readings:
        if val is not None and val > 0:
            calc = val * math.sqrt(val) * inv_log_10
            processed.append(calc)
    return processed

def optimize_image_buffer(buffer, width, height):
    """
    Simulates image processing with 2D buffers.
    Contains: Potential cache locality issues if access pattern is wrong.
    """
    # Hotspot 2: Nested loops - can be improved for readability/performance

    if np is None:
        return buffer
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
    return duplicates
