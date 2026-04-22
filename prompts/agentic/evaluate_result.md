Reflect on the latest metrics against the baseline and plan whether to continue.

Return exactly one JSON object.
Schema:
{
  "reflection_and_plan": {
    "reflection": "Did the last patch successfully improve the metrics? (Baseline vs Latest)",
    "plan": "Is there enough potential speedup left to justify another iteration, or should we stop?"
  },
  "action": "evaluate_result",
  "args": {
    "continue_optimization": false
  },
  "reason": "final decision rationale"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
