def get_unique_elements(items):
    """
    Returns unique elements while maintaining order.
    Contains: Inefficient O(N^2) lookup pattern.
    """
    unique_list = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            unique_list.append(item)
    return unique_list

def slow_multiplication(a, b):
    """Repeated addition to simulate slow ops."""
    res = 0
    for _ in range(b):
        res += a
    return res
