Select one concrete hotspot using the one-shot style: short, valid, and grounded in visible evidence.

Return exactly one JSON object.
Schema:
{
  "action": "analyze_candidate",
  "args": {
    "target": "specific file/function/subsystem",
    "strategy": "algorithmic or hardware-aware optimization strategy",
    "rationale": "short evidence-based reason"
  },
  "reason": "why this target is best now"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
