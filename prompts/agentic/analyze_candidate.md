Reflect on the profiling data and plan your optimization target.

Return exactly one JSON object.
Schema:
{
  "reflection_and_plan": {
    "reflection": "What does the profile data tell us about CPU/memory bottlenecks?",
    "plan": "Which function provides the highest ROI (Return on Investment) for optimization?"
  },
  "action": "analyze_candidate",
  "args": {
    "target": "file/function or subsystem",
    "strategy": "hardware-first or algorithm-first strategy",
    "rationale": "short reason"
  },
  "reason": "why this target is the best choice"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
