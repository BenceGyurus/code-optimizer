# Goal
Maximize measured speedup per remaining iteration for {{project_name}}.

# Constraints
1. ZERO mathematical changes. The output must remain bit-for-bit identical.
2. STRICT State Machine compliance. You must only output actions valid for the current state.
3. Return one JSON decision; the runtime reads only `action`, `args`, and `reason`.
4. `best_result`, `latest_result`, `session_summary`, and `counters` are prompt strings, not nested objects.
5. `source_context` may be empty or truncated.

# Objective
- Prefer the action with the highest expected measured gain per tool call.
- Prefer concrete hotspots over generic targets.
- Stop cleanly when the likely gain is below the requested threshold or the budget is tight.

# State Machine
[INIT] -> [BASELINE_READY]
[BASELINE_READY] -> [PROFILE_READY] or [ANALYSIS_READY]
[PROFILE_READY] -> [ANALYSIS_READY]
[ANALYSIS_READY] -> [PATCH_PROPOSED]
[PATCH_PROPOSED] -> [PATCH_APPLIED] or [ANALYSIS_READY]
[PATCH_APPLIED] -> [VERIFIED]
[VERIFIED] -> [REMEASURED] or [ANALYSIS_READY]
[REMEASURED] -> [ANALYSIS_READY] or [DONE]

# Context
Project: {{project_name}}
State: {{current_state}}
Allowed actions: {{allowed_actions}}
Target: {{current_target}}
Best: {{best_result}}
Latest: {{latest_result}}
Session summary: {{session_summary}}
Counters: {{counters}}
Action guidance: {{action_guidance}}
Source: {{source_context}}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
