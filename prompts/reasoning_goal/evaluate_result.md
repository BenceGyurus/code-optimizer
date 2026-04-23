Compare metrics against the expected goal. Stop if diminishing returns are reached.

Return exactly one JSON object. No markdown. No preambles.
{
  "action": "evaluate_result",
  "args": {
    "continue_optimization": false,
    "target_speedup": 1.02
  },
  "reason": "10 words max"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
