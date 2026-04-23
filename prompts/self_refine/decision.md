Choose the next action from: {{allowed_actions}}.

Return exactly one JSON object. No markdown.
Run a self-check before the final action.
Use the real tool contracts:
- `analyze_candidate`: `target`, `strategy`, `rationale`
- `propose_change`: `target`, `strategy`, `patch`, `rationale`
- `apply_and_verify`: usually `{}`
- `evaluate_result`: usually `continue_optimization` and optional `target_speedup`

Schema:
{
  "self_check": {
    "state_valid": "yes",
    "args_valid": "yes",
    "json_valid": "yes"
  },
  "action": "tool_name",
  "args": { ... },
  "reason": "short"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
