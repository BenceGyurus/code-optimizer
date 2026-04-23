Based on the current state, determine the next action by breaking the decision into steps.
Allowed actions: {{allowed_actions}}
Current session info: {{session_summary}}
Action guidance: {{action_guidance}}
Latest result: {{latest_result}}

Return exactly one JSON object.
The runtime consumes `action`, `args`, and `reason`.
Copy `action` exactly from Allowed actions.
Make the final step respect the real tool contracts:
- `analyze_candidate`: `target`, `strategy`, `rationale`
- `propose_change`: `target`, `strategy`, `patch`, `rationale`
- `apply_and_verify`: usually `{}` because the runner injects the stored patch and commands
- `evaluate_result`: usually `{}` or a small control field

Schema:
{
  "sub_tasks": {
    "step_1": "What is the exact current state?",
    "step_2": "What are the allowed transitions from this state?",
    "step_3": "Which allowed action progresses the optimization loop?",
    "step_4": "Which args does that tool really need in this runtime?"
  },
  "action": "tool_name",
  "args": { ... },
  "reason": "short final rationale"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
