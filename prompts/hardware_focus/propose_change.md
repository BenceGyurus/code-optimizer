Propose a small structured patch that improves memory access, branch predictability, allocation behavior, or locality.

Return exactly one JSON object.
Schema:
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "hardware-focused strategy",
    "patch": "structured patch beginning with *** Begin Patch, or empty string if unsafe",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe and hardware-relevant"
}


## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
