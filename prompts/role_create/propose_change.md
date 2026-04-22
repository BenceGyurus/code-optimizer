Propose an elegant, minimal unified-diff patch for {{current_target}}. Ensure it is production-ready.

Return exactly one JSON object.
Schema:
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "unified diff or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is mathematically safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
