Choose the next valid action from: {{allowed_actions}}.

Return exactly one complete JSON object:
{
  "action": "tool_name",
  "args": {},
  "reason": "short reason"
}

Decision policy:
- If `current_state` is `INIT` and source context already contains the file, choose `run_baseline`, not `inspect_codebase`.
- Use `inspect_codebase` only when source context is missing, truncated, or directory layout is truly needed.
- If `current_state` is `BASELINE_READY` and `profile_execution` is allowed, prefer it once before `analyze_candidate`.
- Do not repeat `inspect_codebase` after it already succeeded in the same state.
- If budget is tight, prefer the action that advances or cleanly finishes the state machine.

Runtime contract:
- Copy `action` exactly from the allowed list.
- `analyze_candidate` should name a concrete hotspot and hardware-aware strategy.
- `propose_change` should include `target`, `strategy`, `patch`, and `rationale`; use a structured `*** Begin Patch` patch when a safe change exists.
- `apply_and_verify` usually needs empty args because the runner injects the stored patch and commands.
- `evaluate_result` can stop even without hardware counters if runtime improved or the budget is tight.
- Keep every string short.
- Return valid JSON only, with a closed final `}` and no markdown or extra text.

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
