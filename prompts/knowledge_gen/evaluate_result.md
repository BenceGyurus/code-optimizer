Phase 1: Generate criteria for "diminishing returns" in code optimization.
Phase 2: Decide whether to stop.

Return exactly one JSON object.
Schema:
{
  "generated_knowledge": "Define when an optimization loop should stop (e.g., speedup < 1%).",
  "action": "evaluate_result",
  "args": {
    "continue_optimization": false
  },
  "reason": "stop or continue rationale based on the generated criteria"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
