Propose a patch for `{{current_target}}` and state the expected measurable effect.

Return exactly one JSON object.
Schema:
{
  "hypothesis": "why this exact code change should help",
  "expected_signal": "runtime, cache, branch, or allocation metric expected to improve",
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
