<task>
Compare latest optimized measurement against baseline and decide whether to stop.
</task>

<output_schema>
{
  "action": "evaluate_result",
  "args": {
    "continue_optimization": false,
    "target_speedup": 1.01
  },
  "reason": "stop or continue rationale"
}
</output_schema>

<budget>
limits={{guardrail_limits}}
usage={{budget_status}}
Stop when the measured result is good enough or budget is tight; continue only if another high-confidence target remains.
</budget>

Return only the JSON object.
