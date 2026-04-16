Analyze the latest baseline/profile result and select one optimization target.

Return JSON:
{
  "action": "analyze_candidate",
  "args": {
    "target": "file/function or subsystem",
    "strategy": "hardware-first or algorithm-first strategy",
    "rationale": "short reason"
  },
  "reason": "why this target is best now"
}
