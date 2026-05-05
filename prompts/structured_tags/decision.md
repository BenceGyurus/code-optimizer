<task>
Select the next valid action from allowed_actions.
</task>

<allowed_actions>{{allowed_actions}}</allowed_actions>
<state>{{current_state}}</state>
<latest_result>{{latest_result}}</latest_result>
<action_guidance>{{action_guidance}}</action_guidance>

<tool_contract>
run_baseline: args {}
profile_execution: args {}
analyze_candidate: args target, strategy, rationale
propose_change: args target, strategy, patch, rationale
apply_and_verify: usually args {}
remeasure: args {}
evaluate_result: usually args {} or continue_optimization and target_speedup
</tool_contract>

<output_schema>
{
  "action": "tool_name",
  "args": { ... },
  "reason": "short"
}
</output_schema>

Return only the JSON object.
