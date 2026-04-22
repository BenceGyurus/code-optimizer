Based on the current state and available tools, what is the next best action?
Allowed actions: {{allowed_actions}}
Current session info: {{session_summary}}
Current target: {{current_target}}
Counters: {{counters}}
Action guidance: {{action_guidance}}

Return exactly one JSON object. Do not include markdown. Do not include explanations outside JSON.
Keep every string short. The reason must be at most 12 words.
Copy `action` exactly from Allowed actions.
Use the tool's real args contract:
- `analyze_candidate`: `target`, `strategy`, `rationale`
- `propose_change`: `target`, `strategy`, `patch`, `rationale`
- `apply_and_verify`: usually empty args because the runner injects patch and commands
- `evaluate_result`: usually empty args because measurements are auto-injected

Schema:
{
  "action": "tool_name",
  "args": { ... },
  "reason": "..."
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
