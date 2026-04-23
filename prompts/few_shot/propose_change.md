Propose a patch for `{{current_target}}` using the output style shown below.

Return exactly one JSON object.
Example:
{"action":"propose_change","args":{"target":"dominant_inner_loop","strategy":"reuse cached values inside the loop","patch":"diff --git ...","rationale":"Reduces repeated work while preserving output."},"reason":"Safe high-ROI patch."}

Schema:
{
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
