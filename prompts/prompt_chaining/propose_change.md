Convert the selected target chain link into one safe patch.

Return exactly one JSON object.
Schema:
{
  "chain_state": {
    "previous_link": "selected target and strategy",
    "next_link": "patch to apply and verify"
  },
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "unified diff beginning with diff --git, or empty string if unsafe",
    "rationale": "short equivalence and performance rationale"
  },
  "reason": "why this patch should be the next chain link"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
