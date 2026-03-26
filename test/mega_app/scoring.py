from typing import Dict, List


def score_events(events: List[Dict[str, object]], weight: float) -> List[float]:
    scores = []
    for event in events:
        score = float(event.get("score", 0.0)) * weight
        scores.append(score)
    return scores


def normalize_scores(scores: List[float]) -> List[float]:
    normalized = []
    max_score = max(scores) if scores else 1.0
    for score in scores:
        normalized.append(score / max_score)
    return normalized


def find_outliers(scores: List[float], threshold: float) -> List[float]:
    outliers = []
    for score in scores:
        if score > threshold:
            outliers.append(score)
    return outliers


def bucket_scores(scores: List[float], bucket_size: float) -> Dict[str, int]:
    buckets: Dict[str, int] = {}
    for score in scores:
        key = f"{int(score / bucket_size)}"
        if key not in buckets:
            buckets[key] = 0
        buckets[key] += 1
    return buckets
