Pick one concrete hotspot and self-check that it is specific enough.

Return exactly one JSON object.
Schema:
{
  "self_check": {
    "target_specific": "yes",
    "strategy_specific": "yes",
    "json_valid": "yes"
  },
  "action": "analyze_candidate",
  "args": {
    "target": "concrete file/function/subsystem",
    "strategy": "hardware-first or algorithm-first strategy",
    "rationale": "short reason"
  },
  "reason": "why this target is best now"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
