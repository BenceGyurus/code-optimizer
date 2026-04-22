import json
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
            "best_result": json.dumps(best_result, indent=2) if best_result else "None",
            "latest_result": json.dumps(latest_result, indent=2) if latest_result else "None",
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
