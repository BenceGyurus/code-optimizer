import json
from typing import List

from .base import Provider, LLMRequest, LLMResponse


MOVING_AVERAGE_PATCH = """diff --git a/examples/heavy_compute.py b/examples/heavy_compute.py
--- a/examples/heavy_compute.py
+++ b/examples/heavy_compute.py
@@ -32,18 +32,18 @@
 def moving_average_slow(values, window):
     \"\"\"Recomputes every window sum from scratch.
 
     Optimization difficulty: easy. This can be replaced by a sliding-window
     running sum without changing results.
     \"\"\"
     if window <= 0:
         raise ValueError(\"window must be positive\")
     if window > len(values):
         return []
 
-    averages = []
-    for index in range(len(values) - window + 1):
-        total = 0.0
-        for offset in range(window):
-            total += values[index + offset]
-        averages.append(total / window)
+    window_sum = sum(values[:window])
+    averages = [window_sum / window]
+    for index in range(window, len(values)):
+        window_sum += values[index]
+        window_sum -= values[index - window]
+        averages.append(window_sum / window)
     return averages
"""


class MockProvider(Provider):
    def __init__(self, responses: List[str] = None):
        self.responses = responses or [
            json.dumps({"action": "run_baseline", "args": {}, "reason": "Establish a baseline first."}),
            json.dumps({"action": "profile_execution", "args": {}, "reason": "Collect optional profile data before analysis."}),
            json.dumps({
                "action": "analyze_candidate",
                "args": {
                    "target": "moving_average_slow",
                    "strategy": "replace repeated window summation with a sliding sum",
                    "rationale": "The function recomputes overlapping sums and is a deterministic low-risk target.",
                },
                "reason": "Analyze the measured baseline.",
            }),
            json.dumps({
                "action": "propose_change",
                "args": {
                    "target": "moving_average_slow",
                    "strategy": "sliding_window",
                    "rationale": "Reduce O(n * window) work to O(n).",
                    "patch": MOVING_AVERAGE_PATCH,
                },
                "reason": "Propose a concrete optimization patch.",
            }),
            json.dumps({"action": "apply_and_verify", "args": {}, "reason": "Apply the proposed patch."}),
            json.dumps({"action": "apply_and_verify", "args": {}, "reason": "Verify build and tests after applying the patch."}),
            json.dumps({"action": "remeasure", "args": {}, "reason": "Remeasure after verification."}),
            json.dumps({"action": "evaluate_result", "args": {"continue_optimization": False}, "reason": "Stop the mock session after one complete cycle."}),
        ]
        self.call_count = 0

    def is_available(self) -> bool:
        return True

    def list_models(self) -> List[str]:
        return ["mock-model-1", "mock-model-2"]

    def resolve_default_model(self) -> str:
        return "mock-model-1"

    def send_prompt(self, request: LLMRequest) -> LLMResponse:
        content = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return LLMResponse(
            content=content,
            model_name="mock-model-1",
            provider_name=self.name,
            usage={"prompt_tokens": 10, "completion_tokens": 10}
        )

    @property
    def name(self) -> str:
        return "mock"

    def supports_structured_output(self) -> bool:
        return True
