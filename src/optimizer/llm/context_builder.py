import json
from statistics import mean, pstdev
from typing import Dict, Any, List, Optional

from optimizer.orchestrator.state_machine import State

class ContextBuilder:
    def __init__(self, project_name: str):
        self.project_name = project_name

    def build_context(self, 
                      current_state: State, 
                      allowed_actions: List[str], 
                      best_result: Optional[Dict[str, Any]] = None,
                      latest_result: Optional[Dict[str, Any]] = None,
                      artifacts_summary: Optional[str] = None,
                      current_target: Optional[str] = None,
                      counters: Optional[Dict[str, int]] = None,
                      source_context: str = "",
                      action_guidance: str = "",
                      guardrail_limits: str = "",
                      budget_status: str = "") -> Dict[str, Any]:
        """
        Assembles the variables for prompt template interpolation.
        """
        return {
            "project_name": self.project_name,
            "current_state": current_state.name,
            "allowed_actions": ", ".join(allowed_actions),
            "allowed_actions_json": json.dumps(allowed_actions),
            "current_target": current_target or "None",
            "counters": json.dumps(counters or {}, indent=2),
            "source_context": source_context or "No source context provided.",
            "action_guidance": action_guidance or "",
            "guardrail_limits": guardrail_limits or "",
            "budget_status": budget_status or "",
            "best_result": json.dumps(_summarize_for_prompt(best_result), indent=2) if best_result else "None",
            "latest_result": json.dumps(_summarize_for_prompt(latest_result), indent=2) if latest_result else "None",
            "session_summary": f"Current state is {current_state.name}. {artifacts_summary or ''}"
        }

    def render_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """
        Simple template rendering by replacing {{key}} with value.
        """
        rendered = template
        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            rendered = rendered.replace(placeholder, str(value))
        return rendered


def _summarize_for_prompt(value: Any) -> Any:
    if isinstance(value, dict):
        summarized: Dict[str, Any] = {}
        for key, item in value.items():
            if key == "patch" and isinstance(item, str):
                summarized["patch_summary"] = _summarize_patch(item)
                continue
            if key in {"runs", "function_profile_runs"} and isinstance(item, list):
                summarized[key] = _summarize_runs(item)
                continue
            if key in {"stdout", "stderr", "output", "error"} and isinstance(item, str):
                summarized[key] = _summarize_text(item)
                continue
            summarized[key] = _summarize_for_prompt(item)
        return summarized

    if isinstance(value, list):
        if len(value) <= 6:
            return [_summarize_for_prompt(item) for item in value]
        return {
            "count": len(value),
            "items_preview": [_summarize_for_prompt(item) for item in value[:3]],
            "omitted_count": len(value) - 3,
        }

    if isinstance(value, str):
        if len(value) <= 240 and value.count("\n") <= 6:
            return value
        return _summarize_text(value)

    return value


def _summarize_patch(patch: str) -> Dict[str, Any]:
    lines = patch.splitlines()
    preview = "\n".join(lines[:14])
    return {
        "present": bool(patch.strip()),
        "chars": len(patch),
        "lines": len(lines),
        "preview": preview,
        "truncated": len(lines) > 14 or len(patch) > len(preview),
    }


def _summarize_runs(runs: List[Any]) -> Dict[str, Any]:
    durations = [
        float(run["duration"])
        for run in runs
        if isinstance(run, dict) and isinstance(run.get("duration"), (int, float))
    ]
    success_count = sum(1 for run in runs if isinstance(run, dict) and run.get("success") is True)
    failure_count = sum(1 for run in runs if isinstance(run, dict) and run.get("success") is False)
    samples = []
    for run in runs[:2]:
        if not isinstance(run, dict):
            samples.append(_summarize_for_prompt(run))
            continue
        sample = {
            key: _summarize_for_prompt(item)
            for key, item in run.items()
            if key not in {"stdout", "stderr", "output", "error"}
        }
        samples.append(sample)
    summary: Dict[str, Any] = {
        "count": len(runs),
        "success_count": success_count,
        "failure_count": failure_count,
        "samples": samples,
    }
    if durations:
        summary["duration_summary"] = {
            "average": mean(durations),
            "minimum": min(durations),
            "maximum": max(durations),
            "stdev": pstdev(durations) if len(durations) > 1 else 0.0,
        }
    return summary


def _summarize_text(text: str, max_lines: int = 8, max_chars: int = 320) -> Dict[str, Any]:
    lines = text.splitlines()
    preview_lines = lines[:max_lines]
    preview = "\n".join(preview_lines)
    if len(preview) > max_chars:
        preview = preview[:max_chars]
    return {
        "chars": len(text),
        "lines": len(lines),
        "preview": preview,
        "truncated": len(lines) > max_lines or len(text) > len(preview),
    }
