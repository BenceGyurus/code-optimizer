from statistics import mean, pstdev
from typing import Iterable


def summarize(values: Iterable[float]) -> dict:
    numbers = list(values)
    if not numbers:
        return {"average": None, "minimum": None, "maximum": None, "stdev": None}
    return {
        "average": mean(numbers),
        "minimum": min(numbers),
        "maximum": max(numbers),
        "stdev": pstdev(numbers) if len(numbers) > 1 else 0.0,
    }
