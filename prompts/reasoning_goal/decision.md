Evaluate the state and advance the workflow.
Allowed actions: {{allowed_actions}}
Session summary: {{session_summary}}

Return exactly one JSON object. No markdown, no preambles.
Copy `action` exactly from Allowed actions.
Use the tool's real args contract:
- `analyze_candidate`: `target`, `strategy`, `rationale`
- `propose_change`: `target`, `strategy`, `patch`, `rationale`
- `apply_and_verify`: usually `{}`
- `evaluate_result`: usually `{}`
{
  "action": "tool_name",
  "args": { ... },
  "reason": "10 words max"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
