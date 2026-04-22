Propose a minimal unified-diff patch for the current target.

Return JSON:
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "unified diff or empty string if no safe patch exists",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe"
}


## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
