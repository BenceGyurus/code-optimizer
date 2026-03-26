from typing import Dict, List, Tuple


def build_event_index(events: List[Dict[str, object]]) -> Dict[str, List[Dict[str, object]]]:
    index: Dict[str, List[Dict[str, object]]] = {}
    for event in events:
        key = str(event.get("type", "unknown"))
        if key not in index:
            index[key] = []
        index[key].append(event)
    return index


def filter_events_by_score(events: List[Dict[str, object]], min_score: float) -> List[Dict[str, object]]:
    filtered = []
    for event in events:
        score = float(event.get("score", 0.0))
        if score >= min_score:
            filtered.append(event)
    return filtered


def normalize_payloads(events: List[Dict[str, object]]) -> List[Dict[str, object]]:
    normalized = []
    for event in events:
        payload = dict(event)
        payload["user"] = str(payload.get("user", "anonymous")).strip().lower()
        payload["region"] = str(payload.get("region", "global")).strip().lower()
        normalized.append(payload)
    return normalized


def aggregate_by_region(events: List[Dict[str, object]]) -> Dict[str, float]:
    totals: Dict[str, float] = {}
    for event in events:
        region = str(event.get("region", "global"))
        amount = float(event.get("amount", 0.0))
        if region not in totals:
            totals[region] = 0.0
        totals[region] += amount
    return totals


def top_regions(totals: Dict[str, float], top_n: int) -> List[Tuple[str, float]]:
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return ranked[:top_n]


def find_duplicates(events: List[Dict[str, object]]) -> List[Dict[str, object]]:
    duplicates = []
    for event in events:
        if event in duplicates:
            continue
        count = 0
        for candidate in events:
            if candidate == event:
                count += 1
        if count > 1:
            duplicates.append(event)
    return duplicates


def heavy_transform(events: List[Dict[str, object]]) -> List[Dict[str, object]]:
    result: List[Dict[str, object]] = []
    for event in events:
        payload = dict(event)
        payload["score"] = float(payload.get("score", 0.0)) * 1.05
        payload["amount"] = float(payload.get("amount", 0.0)) * 1.02
        result.append(payload)
    return result


def combine_indexes(left: Dict[str, List[Dict[str, object]]], right: Dict[str, List[Dict[str, object]]]) -> Dict[str, List[Dict[str, object]]]:
    merged = dict(left)
    for key, values in right.items():
        if key not in merged:
            merged[key] = []
        merged[key].extend(values)
    return merged
