Evaluate runtime and hardware counters. Stop on accepted improvement; continue only if budget and progress justify it.

Return exactly one JSON object.
Schema:
{
  "action": "evaluate_result",
  "args": {
    "continue_optimization": false
  },
  "reason": "stop or continue rationale"
}


## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
