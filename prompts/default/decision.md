Based on the current state and available tools, what is the next best action?
Allowed actions: {{allowed_actions}}
Current session info: {{session_summary}}
Current target: {{current_target}}
Counters: {{counters}}
Action guidance: {{action_guidance}}
Return exactly one JSON object. Do not include markdown. Do not include explanations outside JSON. Do not include <think> text.
Keep every string short. The reason must be at most 12 words.
If action is propose_change, include args.target, args.strategy, args.patch, and args.rationale.
For propose_change, args.patch should be a unified diff beginning with "diff --git" unless a safe change is impossible.
The action value must be copied exactly from Allowed actions. Aliases like "analyze" are invalid.

Schema:
{
  "action": "tool_name",
  "args": { ... },
  "reason": "..."
}
