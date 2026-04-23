Choose the next action from: {{allowed_actions}}.

Return exactly one JSON object. No markdown.
Use the real tool contracts:
- `analyze_candidate`: `target`, `strategy`, `rationale`
- `propose_change`: `target`, `strategy`, `patch`, `rationale`
- `apply_and_verify`: usually `{}`
- `evaluate_result`: usually `continue_optimization` and optional `target_speedup`

Schema:
{
  "hypothesis": "short statement of the expected gain",
  "expected_signal": "runtime or hardware metric expected to improve",
  "action": "tool_name",
  "args": { ... },
  "reason": "short"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
