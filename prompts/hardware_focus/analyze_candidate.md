Pick the hottest hardware-related target from the latest digest.

Use the project context and action guidance to name a concrete hotspot.
Prefer dense numeric kernels, repeated rescans, nested joins, or locality-heavy loops over tiny helper functions when the digest supports that choice.
Do not return generic placeholders like `unspecified`, `unknown`, or `hot path`.

Return exactly one JSON object.
Schema:
{
  "action": "analyze_candidate",
  "args": {
    "target": "file/function or subsystem",
    "strategy": "cache/locality, branch, allocation, or algorithmic strategy",
    "rationale": "short reason"
  },
  "reason": "why this hardware-focused target is best now"
}


## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
