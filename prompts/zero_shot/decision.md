Choose one next action from: {{allowed_actions}}.

Return exactly one JSON object. No markdown. No extra text.
Copy `action` exactly from Allowed actions.
Use only the real tool args contract:
- `analyze_candidate`: `target`, `strategy`, `rationale`
- `propose_change`: `target`, `strategy`, `patch`, `rationale`
- `apply_and_verify`: usually `{}`
- `evaluate_result`: usually `{}`
- `run_baseline`, `profile_execution`, `remeasure`: usually `{}`

Schema:
{
  "action": "tool_name",
  "args": {},
  "reason": "short"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
