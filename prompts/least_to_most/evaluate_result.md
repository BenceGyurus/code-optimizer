Compare measurements to decide the next step using a sequential breakdown.

Return exactly one JSON object.
Schema:
{
  "sub_tasks": {
    "step_1": "Extract baseline metrics.",
    "step_2": "Extract latest metrics.",
    "step_3": "Calculate the delta (improvement or regression).",
    "step_4": "Evaluate if further optimization is worth the effort."
  },
  "action": "evaluate_result",
  "args": {
    "continue_optimization": false,
    "target_speedup": 1.01
  },
  "reason": "stop or continue rationale"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
