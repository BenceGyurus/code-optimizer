Review the latest measurement against the baseline. Apply your Senior Engineer judgment to decide if we stop or continue.

Return exactly one JSON object.
Schema:
{
  "action": "evaluate_result",
  "args": {
    "continue_optimization": false,
    "target_speedup": 1.01
  },
  "reason": "engineering rationale for stopping/continuing"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
