Propose a patch for {{current_target}} by solving the optimization in steps.

Return exactly one JSON object.
Schema:
{
  "sub_tasks": {
    "step_1": "Identify the exact logic causing the bottleneck.",
    "step_2": "Draft the smallest safe optimization.",
    "step_3": "Verify that edge cases still match the original behavior."
  },
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "structured patch beginning with *** Begin Patch, or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
