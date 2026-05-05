Phase 1: Generate knowledge about mathematical equivalence when optimizing {{current_target}}.
Phase 2: Propose the patch.

Return exactly one JSON object.
Schema:
{
  "generated_knowledge": "State the shortest rules required to keep the output identical here.",
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "structured patch beginning with *** Begin Patch, or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe based on the generated knowledge"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
