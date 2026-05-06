<task>
Select one concrete optimization target from the tagged evidence.
</task>

<output_schema>
{
  "action": "analyze_candidate",
  "args": {
    "target": "specific file/function/subsystem",
    "strategy": "algorithmic or hardware-aware strategy",
    "rationale": "short evidence-based reason"
  },
  "reason": "why this target is best now"
}
</output_schema>

<budget>
limits={{guardrail_limits}}
usage={{budget_status}}
If budget is tight, choose the strongest concrete target from current evidence instead of requesting more exploration.
</budget>

Return only the JSON object.
