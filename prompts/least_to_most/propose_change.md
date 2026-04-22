Propose a patch for {{current_target}} by solving the optimization in steps.

Return exactly one JSON object.
Schema:
{
  "sub_tasks": {
    "step_1": "Identify the exact lines causing the bottleneck.",
    "step_2": "Draft the optimized logic (e.g., using a better data structure).",
    "step_3": "Verify that edge cases in the new logic match the old logic."
  },
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "unified diff or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
