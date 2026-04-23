Select an optimization target by breaking down the profile data.

Return exactly one JSON object.
Schema:
{
  "sub_tasks": {
    "step_1": "List the main bottlenecks from the visible evidence.",
    "step_2": "Filter out changes that risk mathematical differences.",
    "step_3": "Rank the remaining hotspots by likely measured gain."
  },
  "action": "analyze_candidate",
  "args": {
    "target": "highest ranked file/function",
    "strategy": "hardware-first or algorithm-first strategy",
    "rationale": "short reason"
  },
  "reason": "why this target is best now"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
