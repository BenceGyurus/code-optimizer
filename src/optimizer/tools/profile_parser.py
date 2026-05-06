import os
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

NON_ACTIONABLE_FUNCTION_NAMES = {
    "<module>",
    "__main__",
    "__init__",
    "main",
    "run",
    "runner",
    "benchmark",
    "run_benchmark",
    "workload",
    "parse_args",
    "checksum",
}

NON_ACTIONABLE_NAME_PARTS = (
    "summary",
    "summarize",
    "validate",
    "validation",
    "report",
    "argparse",
)


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


def parse_function_profile(stdout: str = "", stderr: str = "") -> Dict[str, object]:
    """Extract top cProfile rows from text output."""
    text = f"{stdout}\n{stderr}"
    total_seconds = _parse_profile_total_seconds(text)
    entries: list[dict[str, object]] = []
    for line in text.splitlines():
        parsed = _parse_function_profile_line(line)
        if parsed is None:
            continue
        if total_seconds and parsed["cumtime"]:
            parsed["percent_cumtime"] = float(parsed["cumtime"]) / total_seconds * 100.0
        entries.append(parsed)
    entries.sort(key=lambda item: float(item.get("cumtime") or 0.0), reverse=True)
    return {"total_seconds": total_seconds, "entries": entries}


def summarize_function_profile_runs(runs: Iterable[Dict[str, object]], top_n: int = 12) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int, str], list[dict[str, object]]] = {}
    for run in runs:
        entries = run.get("entries") if isinstance(run, dict) else None
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            file_name = str(entry.get("file") or "")
            function = str(entry.get("function") or "")
            line = int(entry.get("line") or 0)
            if not file_name or not function:
                continue
            grouped.setdefault((file_name, line, function), []).append(entry)

    summarized: list[dict[str, object]] = []
    for (file_name, line, function), values in grouped.items():
        cumtimes = _entry_values(values, "cumtime")
        tottimes = _entry_values(values, "tottime")
        percentages = _entry_values(values, "percent_cumtime")
        calls = _entry_values(values, "primitive_calls")
        if not cumtimes:
            continue
        summarized.append(
            {
                "function": function,
                "file": file_name,
                "line": line,
                "average_cumtime": mean(cumtimes),
                "average_tottime": mean(tottimes) if tottimes else None,
                "average_percent_cumtime": mean(percentages) if percentages else None,
                "average_primitive_calls": mean(calls) if calls else None,
                "runs": len(values),
            }
        )
    summarized.sort(key=lambda item: float(item.get("average_cumtime") or 0.0), reverse=True)
    return summarized[:top_n]


def filter_project_function_hotspots(hotspots: Iterable[dict[str, object]], project_path: str) -> list[dict[str, object]]:
    """Prefer hotspots that belong to the optimized project file when possible."""
    project_name = os.path.basename(project_path)
    if not project_name:
        project_hotspots = list(hotspots)
        actionable = _actionable_function_hotspots(project_hotspots)
        return actionable or project_hotspots

    filtered = []
    for hotspot in hotspots:
        file_name = str(hotspot.get("file") or "")
        if os.path.basename(file_name) == project_name:
            filtered.append(hotspot)
    project_hotspots = filtered or list(hotspots)
    actionable = _actionable_function_hotspots(project_hotspots)
    return actionable or project_hotspots


def profiler_source(command: Optional[str]) -> str:
    text = (command or "").lower()
    if "perf " in text or text.startswith("perf"):
        return "perf"
    if "xctrace" in text or "instruments" in text:
        return "xctrace"
    if not text:
        return "none"
    return "custom"


def function_profiler_source(command: Optional[str]) -> str:
    text = (command or "").lower()
    if "cprofile" in text:
        return "cprofile"
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


def _parse_function_profile_line(line: str) -> Optional[dict[str, object]]:
    match = re.match(
        r"^\s*(?P<ncalls>\S+)\s+"
        r"(?P<tottime>[0-9.]+)\s+"
        r"(?P<percall1>[0-9.]+)\s+"
        r"(?P<cumtime>[0-9.]+)\s+"
        r"(?P<percall2>[0-9.]+)\s+"
        r"(?P<location>.+)$",
        line,
    )
    if not match:
        return None

    location = match.group("location").strip()
    location_match = re.match(r"^(?P<file>.+):(?P<line>\d+)\((?P<function>.+)\)$", location)
    if not location_match:
        return None

    primitive_calls, total_calls = _parse_ncalls(match.group("ncalls"))
    return {
        "ncalls": match.group("ncalls"),
        "primitive_calls": primitive_calls,
        "total_calls": total_calls,
        "tottime": float(match.group("tottime")),
        "cumtime": float(match.group("cumtime")),
        "file": location_match.group("file"),
        "line": int(location_match.group("line")),
        "function": location_match.group("function"),
    }


def _parse_unsupported_counter_line(line: str) -> Optional[str]:
    if "<not supported>" not in line and "<not counted>" not in line:
        return None
    match = re.match(r"^\s*<[^>]+>\s+([A-Za-z0-9_.:-]+)\b", line)
    if not match:
        return None
    return _normalize_counter_name(match.group(1))


def _parse_profile_total_seconds(text: str) -> Optional[float]:
    match = re.search(r"\bfunction calls(?: \([^)]*\))? in ([0-9.]+) seconds", text)
    if not match:
        return None
    return float(match.group(1))


def _parse_ncalls(value: str) -> tuple[float, float]:
    if "/" in value:
        total, primitive = value.split("/", 1)
        return float(primitive), float(total)
    parsed = float(value)
    return parsed, parsed


def _entry_values(entries: list[dict[str, object]], key: str) -> list[float]:
    return [float(entry[key]) for entry in entries if isinstance(entry.get(key), (int, float))]


def _actionable_function_hotspots(hotspots: list[dict[str, object]]) -> list[dict[str, object]]:
    return [hotspot for hotspot in hotspots if not _is_non_actionable_function_name(str(hotspot.get("function") or ""))]


def _is_non_actionable_function_name(name: str) -> bool:
    normalized = name.strip().lower()
    short = normalized.rsplit(".", 1)[-1]
    if not short:
        return True
    if short in NON_ACTIONABLE_FUNCTION_NAMES:
        return True
    if short.startswith("<") and short.endswith(">"):
        return True
    if short.startswith("test_") or short.startswith("generate_"):
        return True
    return any(part in short for part in NON_ACTIONABLE_NAME_PARTS)


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
