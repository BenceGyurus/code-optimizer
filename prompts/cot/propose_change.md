Propose a minimal unified-diff patch for {{current_target}}.

Use a short visible chain of thought about how to safely modify this code. Return exactly one JSON object.
Schema:
{
  "thought_process": [
    "Step 1: Analyze current implementation of target",
    "Step 2: Draft the optimization",
    "Step 3: Verify mathematical equivalence and diff format"
  ],
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "real unified diff beginning with diff --git, or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
