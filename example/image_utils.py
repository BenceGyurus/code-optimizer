def apply_brightness(buffer, width, height, factor):
    """
    Simulates pixel brightness adjustment.
    Contains: Classic nested loops for 2D array access.
    """
    # Hotspot: unnecessary_nested_loops (Candidate for vectorization)
    factor_int = int(factor)
    for y in range(height):
        row = buffer[y]
        row[:] = [255 if pixel * factor_int > 255 else pixel * factor_int for pixel in row]
    return buffer

def find_max_pixel(buffer):
    """Simple loop to find max."""
    max_val = 0
    for row in buffer:
        max_val = max(max_val, max(row))
    return max_val
