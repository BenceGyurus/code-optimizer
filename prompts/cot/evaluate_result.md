Compare the latest measurement against the baseline and decide whether to stop.

Let's think step by step. Return exactly one JSON object.
Schema:
{
  "thought_process": [
    "Step 1: Extract baseline runtime/memory",
    "Step 2: Extract new runtime/memory",
    "Step 3: Calculate percentage change",
    "Step 4: Decide if diminishing returns are reached"
  ],
  "action": "evaluate_result",
  "args": {
    "continue_optimization": false,
    "target_speedup": 1.01
  },
  "reason": "stop or continue rationale"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
