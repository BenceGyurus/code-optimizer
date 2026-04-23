Generate a mathematically safe unified diff for `{{current_target}}` with strong expected ROI.

Return exactly one JSON object. No markdown. No preambles.
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "applied_strategy",
    "patch": "unified diff beginning with diff --git, or empty string",
    "rationale": "expected measured benefit in 10 words max"
  },
  "reason": "10 words max"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
