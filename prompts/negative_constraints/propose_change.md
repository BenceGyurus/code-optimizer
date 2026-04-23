Propose the smallest safe patch for `{{current_target}}`.

Return exactly one JSON object.
If you cannot satisfy every hard constraint, return an empty patch instead of an invalid or oversized one.
Schema:
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "specific chosen strategy",
    "patch": "unified diff beginning with diff --git, or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
