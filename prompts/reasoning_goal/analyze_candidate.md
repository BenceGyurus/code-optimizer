Select the bottleneck with the highest expected measured gain.

Return exactly one JSON object. No markdown. No preambles.
{
  "action": "analyze_candidate",
  "args": {
    "target": "concrete target_name",
    "strategy": "selected_strategy",
    "rationale": "expected gain and safety in 10 words max"
  },
  "reason": "10 words max"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
