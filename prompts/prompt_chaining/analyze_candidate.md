Use the previous chain link's measurement/profile output to select the next optimization target.

Return exactly one JSON object.
Schema:
{
  "chain_state": {
    "previous_link": "baseline/profile evidence used",
    "next_link": "target selection for patch proposal"
  },
  "action": "analyze_candidate",
  "args": {
    "target": "specific file/function/subsystem",
    "strategy": "strategy for the next patch link",
    "rationale": "short evidence-based reason"
  },
  "reason": "why this target is the next chain link"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
