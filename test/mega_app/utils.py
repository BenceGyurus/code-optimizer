from typing import Dict, List, Tuple


def flatten(nested: List[List[float]]) -> List[float]:
    flat = []
    for sub in nested:
        for val in sub:
            flat.append(val)
    return flat


def index_by_key(items: List[Dict[str, object]], key_name: str) -> Dict[str, Dict[str, object]]:
    indexed: Dict[str, Dict[str, object]] = {}
    for item in items:
        key = str(item.get(key_name, ""))
        indexed[key] = item
    return indexed


def chunk(items: List[float], size: int) -> List[List[float]]:
    chunks = []
    i = 0
    while i < len(items):
        chunks.append(items[i:i + size])
        i += size
    return chunks


def slow_lookup(values: List[str], targets: List[str]) -> List[str]:
    found = []
    for target in targets:
        if target in values:
            found.append(target)
    return found


def build_pairs(left: List[str], right: List[str]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for lval in left:
        for rval in right:
            pairs.append((lval, rval))
    return pairs
