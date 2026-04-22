Select the highest-impact bottleneck based on the profiling data.

Return exactly one JSON object. No markdown, no preambles.
{
  "action": "analyze_candidate",
  "args": {
    "target": "target_name",
    "strategy": "selected_strategy",
    "rationale": "10 words max"
  },
  "reason": "10 words max"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
