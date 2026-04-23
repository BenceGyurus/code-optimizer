Propose a patch for `{{current_target}}` and self-check the patch format and safety.

Return exactly one JSON object.
Schema:
{
  "self_check": {
    "target_specific": "yes",
    "patch_valid": "yes",
    "safety_valid": "yes",
    "json_valid": "yes"
  },
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "unified diff beginning with diff --git, or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
