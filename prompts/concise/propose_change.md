Return exactly one JSON object. No markdown. No extra text.
Use `{{current_target}}` as the target.

Schema:
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "unified diff beginning with diff --git, or empty string if unsafe",
    "rationale": "short rationale"
  },
  "reason": "short"
}


## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
