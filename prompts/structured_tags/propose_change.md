<task>
Propose one minimal safe patch for current_target.
</task>

<current_target>{{current_target}}</current_target>

<output_schema>
{
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "structured patch beginning with *** Begin Patch, or empty string if unsafe",
    "rationale": "short safety and performance rationale"
  },
  "reason": "why this patch should be safe"
}
</output_schema>

<budget>
limits={{guardrail_limits}}
usage={{budget_status}}
Prefer one concrete, semantics-preserving patch over exploration. If unsafe, return an empty patch rather than placeholder text.
</budget>

Return only the JSON object.
