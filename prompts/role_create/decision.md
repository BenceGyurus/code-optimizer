Based on the current evidence, apply your engineering expertise to select the next action.
Allowed actions: {{allowed_actions}}
Session summary: {{session_summary}}
Action guidance: {{action_guidance}}
Latest result: {{latest_result}}

Return exactly one JSON object.
Copy `action` exactly from Allowed actions.
Use the actual tool contracts, not imagined ones:
- `analyze_candidate`: `target`, `strategy`, `rationale`
- `propose_change`: `target`, `strategy`, `patch`, `rationale`
- `apply_and_verify`: usually empty args because the runner injects patch and commands
- `evaluate_result`: baseline and optimized measurements are auto-injected; `target_speedup` is optional

Schema:
{
  "action": "tool_name",
  "args": { ... },
  "reason": "12 words max explaining the engineering necessity"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
