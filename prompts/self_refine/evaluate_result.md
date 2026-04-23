Evaluate the latest result and self-check that the stop/continue decision matches the measured evidence.

Return exactly one JSON object.
Schema:
{
  "self_check": {
    "metric_reading_valid": "yes",
    "decision_consistent": "yes",
    "json_valid": "yes"
  },
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
