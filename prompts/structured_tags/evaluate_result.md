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

Return only the JSON object.
