Advance exactly one prompt-chain link.

Allowed actions: {{allowed_actions}}
Current state: {{current_state}}
Previous link output: {{latest_result}}
Action guidance: {{action_guidance}}

Return exactly one JSON object. No markdown. No prose outside JSON.
Copy `action` exactly from Allowed actions.

Tool args contract:
- `run_baseline`: `{}`
- `profile_execution`: `{}`
- `analyze_candidate`: `target`, `strategy`, `rationale`
- `propose_change`: `target`, `strategy`, `patch`, `rationale`
- `apply_and_verify`: usually `{}`
- `remeasure`: `{}`
- `evaluate_result`: usually `{}` or `continue_optimization` plus optional `target_speedup`

Schema:
{
  "chain_state": {
    "previous_link": "short summary of latest_result",
    "next_link": "why the chosen action is the valid next link"
  },
  "action": "tool_name",
  "args": { ... },
  "reason": "short"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
