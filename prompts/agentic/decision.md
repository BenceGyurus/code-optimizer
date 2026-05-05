Reflect on the session history and plan your next state transition.
Allowed actions: {{allowed_actions}}
Session summary: {{session_summary}}
Current target: {{current_target}}
Action guidance: {{action_guidance}}

Runtime contract:
- Return exactly one valid JSON object. No markdown. No prose outside JSON.
- Prefer copying `action` exactly from Allowed actions. Some aliases may be normalized by the runner, but do not rely on that.
- The runtime reads only `action`, `args`, and `reason`.
- Use only the args that the chosen tool actually consumes.
- `analyze_candidate` expects `args.target`, `args.strategy`, and `args.rationale`.
- `propose_change` expects `args.target`, `args.strategy`, `args.patch`, and `args.rationale`. When a safe patch exists, `args.patch` should be a structured patch beginning with `*** Begin Patch`.
- `apply_and_verify` usually needs `{}` because the runner injects the stored patch and commands. In `PATCH_PROPOSED` it applies the patch; in `PATCH_APPLIED` it verifies build and tests.
- `evaluate_result` usually needs only high-level control fields such as `continue_optimization` or `target_speedup`; baseline and optimized results are auto-injected.
- `run_baseline`, `profile_execution`, and `remeasure` usually work best with empty args unless you intentionally want to override injected commands.

Schema:
{
  "reflection_and_plan": {
    "reflection": "What have we achieved so far in this session?",
    "plan": "What is the logical next step according to the State Machine and runtime contract?"
  },
  "action": "tool_name",
  "args": { ... },
  "reason": "short rationale"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
