Generate a mathematically safe, highly optimized unified diff for {{current_target}}.

Return exactly one JSON object. No markdown, no preambles.
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "applied_strategy",
    "patch": "unified diff string",
    "rationale": "10 words max"
  },
  "reason": "10 words max"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
