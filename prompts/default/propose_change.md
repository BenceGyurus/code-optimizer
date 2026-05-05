Propose a minimal unified-diff patch for the current target.

Return exactly one JSON object. No markdown. No prose outside JSON.
If a real safe diff cannot be produced from visible source, return an empty patch instead of a placeholder.
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "real unified diff beginning with diff --git, or empty string if no safe patch exists",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe"
}


## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
