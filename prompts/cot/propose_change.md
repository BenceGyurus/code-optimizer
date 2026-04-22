Propose a minimal unified-diff patch for {{current_target}}.

Let's think step by step about how to safely modify this code. Return exactly one JSON object.
Schema:
{
  "thought_process": [
    "Step 1: Analyze current implementation of target",
    "Step 2: Draft the optimization",
    "Step 3: Verify mathematical equivalence",
    "Step 4: Format as unified diff"
  ],
  "action": "propose_change",
  "args": {
    "target": "{{current_target}}",
    "strategy": "chosen strategy",
    "patch": "unified diff or empty string",
    "rationale": "short rationale"
  },
  "reason": "why this patch is safe"
}

## Budget Limits
Limits: {{guardrail_limits}}
Current usage: {{budget_status}}
Do not assume unlimited retries or iterations. If budget is tight or progress is weak, choose the action that cleanly finishes the session.
