Propose one minimal patch for `{{current_target}}` using the one-shot style.

Return exactly one JSON object.
Schema:
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "structured patch beginning with *** Begin Patch, or empty string if unsafe",
    "rationale": "short safety and performance rationale"
  },
  "reason": "why this patch should be safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
