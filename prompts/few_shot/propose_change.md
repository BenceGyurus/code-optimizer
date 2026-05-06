Propose a patch for `{{current_target}}` using the output style shown below.

Return exactly one JSON object.
Example when no concrete safe patch can be produced:
{"action":"propose_change","args":{"target":"{{current_target}}","strategy":"no safe code change from visible source","patch":"","rationale":"Visible source does not support a safe semantics-preserving patch."},"reason":"Avoid an unsafe or placeholder patch."}

Use the current target. Do not emit placeholder patch text.

Schema:
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "real structured patch beginning with *** Begin Patch, or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
