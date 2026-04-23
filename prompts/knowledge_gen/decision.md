Phase 1: Generate knowledge about what each tool does.
Phase 2: Decide the next action.
Allowed: {{allowed_actions}}
Session summary: {{session_summary}}
Action guidance: {{action_guidance}}
Latest result: {{latest_result}}

Return exactly one JSON object.
The runtime reads only `action`, `args`, and `reason`.
Copy `action` exactly from Allowed actions.
Match your generated knowledge to the real args contract:
- `analyze_candidate`: `target`, `strategy`, `rationale`
- `propose_change`: `target`, `strategy`, `patch`, `rationale`
- `apply_and_verify`: usually `{}` because patch and commands are injected
- `evaluate_result`: baseline and optimized results are auto-injected

Schema:
{
  "generated_knowledge": "At most 3 short evidence-grounded tool facts for the current state.",
  "action": "tool_name",
  "args": { ... },
  "reason": "short final rationale"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
