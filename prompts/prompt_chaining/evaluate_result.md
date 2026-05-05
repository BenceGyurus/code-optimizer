Close or continue the chain based on baseline vs optimized measurements.

Return exactly one JSON object.
Schema:
{
  "chain_state": {
    "previous_link": "latest remeasurement result",
    "next_link": "stop or choose another analysis link"
  },
  "action": "evaluate_result",
  "args": {
    "continue_optimization": false,
    "target_speedup": 1.01
  },
  "reason": "stop or continue rationale"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
