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

Return only the JSON object.
