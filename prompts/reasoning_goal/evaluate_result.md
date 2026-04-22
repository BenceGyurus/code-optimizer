Compare metrics. Stop if diminishing returns are reached; otherwise, continue.

Return exactly one JSON object. No markdown, no preambles.
{
  "action": "evaluate_result",
  "args": {
    "continue_optimization": boolean
  },
  "reason": "10 words max"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
