Phase 1: Generate knowledge about common algorithmic bottlenecks in this type of codebase.
Phase 2: Select the target.

Return exactly one JSON object.
Schema:
{
  "generated_knowledge": "List 2-3 short anti-patterns grounded in the visible code and latest metrics.",
  "action": "analyze_candidate",
  "args": {
    "target": "file/function or subsystem",
    "strategy": "hardware-first or algorithm-first strategy",
    "rationale": "short reason"
  },
  "reason": "why this target is best now"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
