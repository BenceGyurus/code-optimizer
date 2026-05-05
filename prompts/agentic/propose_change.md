Reflect on the current logic of {{current_target}} and plan the patch.

Return exactly one JSON object.
Schema:
{
  "reflection_and_plan": {
    "reflection": "Why is the current logic slow?",
    "plan": "How will the new logic improve speed while maintaining exact mathematical equivalence?"
  },
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "structured patch beginning with *** Begin Patch, or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
