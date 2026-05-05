Propose an elegant, minimal structured patch for {{current_target}}. Ensure it is production-ready.

Return exactly one JSON object.
If a real safe patch cannot be produced, return an empty patch instead of a placeholder.
Schema:
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "real structured patch beginning with *** Begin Patch, or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is mathematically safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
