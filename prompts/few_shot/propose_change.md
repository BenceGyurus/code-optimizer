Propose a patch for `{{current_target}}` using the output style shown below.

Return exactly one JSON object.
Example when no concrete safe diff can be produced:
{"action":"propose_change","args":{"target":"selected_hotspot","strategy":"small semantics-preserving optimization","patch":"","rationale":"Empty patch avoids an invalid placeholder diff."},"reason":"No safe concrete diff available."}

Do not copy the example target. Do not emit placeholder patch text.

Schema:
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "real unified diff beginning with diff --git, or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
