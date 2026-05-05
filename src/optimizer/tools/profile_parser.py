import re
from statistics import mean, pstdev
from typing import Dict, Iterable, Optional


COUNTER_ALIASES = {
    "cache-misses": "cache_misses",
    "cache-references": "cache_references",
    "branch-misses": "branch_misses",
    "branches": "branches",
    "cycles": "cycles",
    "instructions": "instructions",
    "l1-dcache-load-misses": "l1_dcache_load_misses",
    "l1-dcache-loads": "l1_dcache_loads",
    "llc-load-misses": "llc_load_misses",
    "llc-loads": "llc_loads",
}


def parse_hardware_counters(stdout: str = "", stderr: str = "") -> Dict[str, float]:
    """Extract common perf-style hardware counters from profiler output."""
    counters: Dict[str, float] = {}
    for line in f"{stdout}\n{stderr}".splitlines():
        parsed = _parse_counter_line(line)
        if parsed is None:
            continue
        name, value = parsed
        key = COUNTER_ALIASES.get(name.lower())
        if key:
            counters[key] = value

    _add_rate(counters, "cache_miss_rate", "cache_misses", "cache_references")
    _add_rate(counters, "branch_miss_rate", "branch_misses", "branches")
    _add_rate(counters, "l1_dcache_load_miss_rate", "l1_dcache_load_misses", "l1_dcache_loads")
    _add_rate(counters, "llc_load_miss_rate", "llc_load_misses", "llc_loads")
    _add_complement_rate(counters, "cache_hit_rate", "cache_miss_rate")
    _add_complement_rate(counters, "branch_hit_rate", "branch_miss_rate")
    _add_complement_rate(counters, "l1_dcache_load_hit_rate", "l1_dcache_load_miss_rate")
    _add_complement_rate(counters, "llc_load_hit_rate", "llc_load_miss_rate")
    return counters


def parse_unsupported_counters(stdout: str = "", stderr: str = "") -> list[str]:
    """Return normalized perf counters that the current machine could not count."""
    unsupported: set[str] = set()
    for line in f"{stdout}\n{stderr}".splitlines():
        parsed = _parse_unsupported_counter_line(line)
        if parsed is not None:
            unsupported.add(parsed)
    return sorted(unsupported)


def normalize_counter_names(names: Iterable[str]) -> list[str]:
    normalized: set[str] = set()
    for name in names:
        key = _normalize_counter_name(str(name).strip())
        if key:
            normalized.add(key)
    return sorted(normalized)


def summarize_counter_runs(runs: Iterable[Dict[str, float]]) -> Dict[str, dict]:
    grouped: Dict[str, list[float]] = {}
    for run in runs:
        for key, value in run.items():
            grouped.setdefault(key, []).append(value)

    return {
        key: {
            "average": mean(values),
            "minimum": min(values),
            "maximum": max(values),
            "stdev": pstdev(values) if len(values) > 1 else 0.0,
        }
        for key, values in grouped.items()
    }


def profiler_source(command: Optional[str]) -> str:
    text = (command or "").lower()
    if "perf " in text or text.startswith("perf"):
        return "perf"
    if "xctrace" in text or "instruments" in text:
        return "xctrace"
    if not text:
        return "none"
    return "custom"


def profiler_unavailable(command: Optional[str], stderr: str, stdout: str, returncode: int) -> bool:
    if returncode == 0:
        return False
    text = f"{stdout}\n{stderr}".lower()
    source = profiler_source(command)
    if "command not found" in text or "is not recognized" in text:
        return True
    if source == "perf" and "perf_event_open" in text:
        return True
    if source == "xctrace" and ("unable to find utility" in text or "developer tools" in text):
        return True
    return False


def unsupported_profile_output(command: Optional[str], reason: str) -> Dict[str, object]:
    return {
        "supported": False,
        "source": profiler_source(command),
        "message": reason,
    }


def _parse_counter_line(line: str) -> Optional[tuple[str, float]]:
    if "<not supported>" in line or "<not counted>" in line:
        return None

    match = re.match(r"^\s*([0-9][0-9,.\s]*)\s+([A-Za-z0-9_.:-]+)\b", line)
    if not match:
        return None

    value = _parse_number(match.group(1))
    if value is None:
        return None
    return match.group(2), value


def _parse_unsupported_counter_line(line: str) -> Optional[str]:
    if "<not supported>" not in line and "<not counted>" not in line:
        return None
    match = re.match(r"^\s*<[^>]+>\s+([A-Za-z0-9_.:-]+)\b", line)
    if not match:
        return None
    return _normalize_counter_name(match.group(1))


def _normalize_counter_name(name: str) -> Optional[str]:
    if not name:
        return None
    return COUNTER_ALIASES.get(name.lower(), name.lower().replace("-", "_"))


def _parse_number(value: str) -> Optional[float]:
    compact = value.strip().replace(" ", "")
    if not compact:
        return None

    if "," in compact and "." in compact:
        compact = compact.replace(",", "")
    elif "," in compact:
        parts = compact.split(",")
        compact = "".join(parts) if all(len(part) == 3 for part in parts[1:]) else compact.replace(",", ".")

    try:
        return float(compact)
    except ValueError:
        return None


def _add_rate(counters: Dict[str, float], rate_key: str, numerator_key: str, denominator_key: str) -> None:
    numerator = counters.get(numerator_key)
    denominator = counters.get(denominator_key)
    if numerator is not None and denominator:
        counters[rate_key] = numerator / denominator


def _add_complement_rate(counters: Dict[str, float], rate_key: str, source_rate_key: str) -> None:
    source_rate = counters.get(source_rate_key)
    if source_rate is None or not 0.0 <= source_rate <= 1.0:
        return
    counters[rate_key] = 1.0 - source_rate
