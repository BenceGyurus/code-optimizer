Compare the observed metrics against the expected hypothesis and decide whether to continue.

Return exactly one JSON object.
Schema:
{
  "hypothesis": "what was expected to improve",
  "expected_signal": "what metric was supposed to move",
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
