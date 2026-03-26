from typing import Dict, List


def sample_events(count: int) -> List[Dict[str, object]]:
    events: List[Dict[str, object]] = []
    for i in range(count):
        events.append({
            "type": "purchase" if i % 2 == 0 else "visit",
            "user": f"User {i % 5}",
            "region": "eu" if i % 3 == 0 else "us",
            "amount": float(i) * 1.5,
            "score": float(i) * 0.8,
        })
    return events
