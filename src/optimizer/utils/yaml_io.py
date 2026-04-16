import json
from typing import Any, Dict


try:
    import yaml
except ImportError:  # pragma: no cover - fallback for minimal environments
    yaml = None


def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    if yaml is not None:
        loaded = yaml.safe_load(text)
        return loaded or {}
    return _parse_simple_yaml(text)


def dump_yaml(data: Dict[str, Any]) -> str:
    if yaml is not None:
        return yaml.safe_dump(data, sort_keys=False)
    return json.dumps(data, indent=2)


def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    current_key = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- ") and current_key:
            result.setdefault(current_key, []).append(_coerce_scalar(line[2:].strip()))
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            result[key] = [] if value == "" else _coerce_scalar(value)
    return result


def _coerce_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
