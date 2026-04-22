Analyze the latest baseline/profile result and select one optimization target.

Return exactly one JSON object.
Schema:
{
  "action": "analyze_candidate",
  "args": {
    "target": "file/function or subsystem",
    "strategy": "hardware-first or algorithm-first strategy",
    "rationale": "short reason"
  },
  "reason": "why this target is best now"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
