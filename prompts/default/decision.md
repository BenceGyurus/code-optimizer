Based on the current state and available tools, what is the next best action?
Allowed actions: {{allowed_actions}}
Current session info: {{session_summary}}
Current target: {{current_target}}
Counters: {{counters}}
Action guidance: {{action_guidance}}
Return exactly one JSON object. Do not include markdown. Do not include explanations outside JSON. Do not include <think> text.
Keep every string short. The reason must be at most 12 words.

Runtime contract:
- Prefer copying the `action` exactly from Allowed actions. The runner can normalize some aliases, but do not rely on that.
- The runtime reads only `action`, `args`, and `reason`.
- `analyze_candidate`: include `args.target`, `args.strategy`, and `args.rationale`.
- `propose_change`: include `args.target`, `args.strategy`, `args.patch`, and `args.rationale`.
- For `propose_change`, `args.patch` should be a unified diff beginning with `diff --git` unless a safe change is impossible.
- `apply_and_verify` usually needs `{}` because the runner injects the stored patch plus build and test commands. In `PATCH_PROPOSED` it applies; in `PATCH_APPLIED` it verifies.
- `evaluate_result` usually needs `{}` or a small control field such as `continue_optimization` or `target_speedup`; baseline and optimized results are auto-injected.
- `run_baseline`, `profile_execution`, and `remeasure` usually work best with empty args unless you intentionally want to override the injected commands.

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
