Pick one hotspot and state a measurement-backed hypothesis for it.

Return exactly one JSON object.
Schema:
{
  "hypothesis": "why this hotspot should dominate the current metrics",
  "expected_signal": "which metric should move if the hypothesis is right",
  "action": "analyze_candidate",
  "args": {
    "target": "concrete file/function/subsystem",
    "strategy": "hardware-first or algorithm-first strategy",
    "rationale": "short reason"
  },
  "reason": "why this target is best now"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
