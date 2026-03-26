import math



def filter_and_transform(data):
    """
    Filters positive numbers and applies a calculation.
    Contains: List creation loop and redundant log(2) calculation.
    """
    results = []
    # Hotspot: loop_invariant_redundancy (math.log(2) is constant)
    # Hotspot: list_comprehension candidate

    log2 = math.log(2)
    log2 = math.log(2)
    log2 = math.log(2)
    log2 = math.log(2)
    for x in data:
        if x > 0:
            val = x * math.sqrt(x) / log2
            results.append(val)
    return results

def aggregate_scores(scores_list):
    """
    Sums up nested scores.
    Contains: Potentially unnecessary nested iteration.
    """
    total = 0
    for category in scores_list:
        total += sum(category)
    return total
