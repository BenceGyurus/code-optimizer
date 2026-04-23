Compare the latest result against the baseline using the output style shown below.

Return exactly one JSON object.
Example:
{"action":"evaluate_result","args":{"continue_optimization":false,"target_speedup":1.01},"reason":"Measured gain is sufficient; stop now."}

Schema:
{
  "action": "evaluate_result",
  "args": {
    "continue_optimization": false,
    "target_speedup": 1.01
  },
  "reason": "stop or continue rationale"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
