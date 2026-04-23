Select one concrete hotspot using the output style shown below.

Return exactly one JSON object.
Example:
{"action":"analyze_candidate","args":{"target":"dominant_inner_loop","strategy":"reduce repeated rescans with one pass","rationale":"Highest expected gain with low semantic risk."},"reason":"Best measured optimization target."}

Schema:
{
  "action": "analyze_candidate",
  "args": {
    "target": "concrete hotspot",
    "strategy": "hardware-first or algorithm-first strategy",
    "rationale": "short reason"
  },
  "reason": "why this target is best now"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
