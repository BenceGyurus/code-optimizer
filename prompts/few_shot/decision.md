Choose the next action from: {{allowed_actions}}.
Session summary: {{session_summary}}

Return exactly one JSON object. No markdown.
Match the examples' style and the real tool contracts:
- `analyze_candidate`: `target`, `strategy`, `rationale`
- `propose_change`: `target`, `strategy`, `patch`, `rationale`
- `apply_and_verify`: usually `{}`
- `evaluate_result`: usually `continue_optimization` and optional `target_speedup`

# Example
{"action":"evaluate_result","args":{"continue_optimization":false,"target_speedup":1.01},"reason":"Stop after acceptable measured gain."}

Schema:
{
  "action": "tool_name",
  "args": { ... },
  "reason": "short"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
