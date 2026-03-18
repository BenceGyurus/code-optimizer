import math
import time

def analyze_sensor_data(sensor_readings):
    """
    Simulates processing a large list of sensor data.
    Contains: Inefficient loop, repeated calculations.
    """
    processed = []
    # Hotspot 1: List comprehension candidate + unnecessary calculation
    for val in sensor_readings:
        if val is not None and val > 0:
            # Repeatedly calculating log(10) which is constant
            calc = val * math.sqrt(val) / math.log(10)
            processed.append(calc)
    return processed

def optimize_image_buffer(buffer, width, height):
    """
    Simulates image processing with 2D buffers.
    Contains: Potential cache locality issues if access pattern is wrong.
    """
    # Hotspot 2: Nested loops - can be improved for readability/performance
    for x in range(width):
        for y in range(height):
            pixel = buffer[y][x]
            if pixel > 255:
                buffer[y][x] = 255
            elif pixel < 0:
                buffer[y][x] = 0
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

if __name__ == "__main__":
    # Generate some dummy data
    data = [i for i in range(1000)]
    
    start = time.time()
    analyze_sensor_data(data)
    print(f"Sensor analysis took: {time.time() - start:.4f}s")
    
    matrix = [[i+j for i in range(100)] for j in range(100)]
    start = time.time()
    optimize_image_buffer(matrix, 100, 100)
    print(f"Buffer optimization took: {time.time() - start:.4f}s")
