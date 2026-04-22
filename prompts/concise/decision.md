Pick one allowed action from: {{allowed_actions}}.

Runtime contract:
- Return exactly one JSON object. No markdown. No extra text.
- Always include `action`, `args`, and `reason`.
- Copy `action` exactly from Allowed actions.
- `analyze_candidate` needs `target`, `strategy`, `rationale`.
- `propose_change` needs `target`, `strategy`, `patch`, `rationale`.
- `apply_and_verify`, `run_baseline`, `profile_execution`, and `remeasure` usually work with `{}` because commands and stored patch are injected by the runner.
- `evaluate_result` usually needs `{}` or a small control field such as `continue_optimization`.

Schema:
{"action":"tool_name","args":{},"reason":"short"}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
