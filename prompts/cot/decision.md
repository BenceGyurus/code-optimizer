Based on the current state, what is the next best action?
Allowed: {{allowed_actions}}
Current session: {{session_summary}}

Let's think step by step. Return exactly one JSON object.
Runtime contract:
- The runtime ignores `thought_process` and consumes `action`, `args`, and `reason`.
- Copy `action` exactly from Allowed actions.
- `analyze_candidate` needs `target`, `strategy`, `rationale`.
- `propose_change` needs `target`, `strategy`, `patch`, `rationale`; the patch should start with `diff --git` when a safe change exists.
- `apply_and_verify` is two-step: apply in `PATCH_PROPOSED`, verify in `PATCH_APPLIED`. It usually works with empty args because patch and commands are injected.
- `evaluate_result` receives baseline and optimized results automatically unless you intentionally override them.

Schema:
{
  "thought_process": [
    "Step 1: Identify current state",
    "Step 2: Identify allowed actions",
    "Step 3: Map the best action to the tool's real args contract"
  ],
  "action": "tool_name",
  "args": { ... },
  "reason": "short final rationale"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
