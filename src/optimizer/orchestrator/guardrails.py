from dataclasses import dataclass
from typing import Dict, List

@dataclass
class GuardrailsConfig:
    max_tool_calls: int = 50
    max_llm_calls: int = 20
    max_iterations: int = 5
    max_patch_attempts_per_target: int = 3
    require_test_success: bool = True
    max_repeated_signatures: int = 2

class Guardrails:
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self.tool_calls_count = 0
        self.llm_calls_count = 0
        self.iterations_count = 0
        self.patch_attempts: Dict[str, int] = {} # target_id -> count
        self.signatures: Dict[str, int] = {}
        self.performance_history: List[float] = []

    def can_call_tool(self) -> bool:
        return self.tool_calls_count < self.config.max_tool_calls

    def can_call_llm(self) -> bool:
        return self.llm_calls_count < self.config.max_llm_calls

    def can_iterate(self) -> bool:
        return self.iterations_count < self.config.max_iterations

    def can_attempt_patch(self, target_id: str) -> bool:
        attempts = self.patch_attempts.get(target_id, 0)
        return attempts < self.config.max_patch_attempts_per_target

    def record_tool_call(self):
        self.tool_calls_count += 1

    def record_llm_call(self):
        self.llm_calls_count += 1

    def record_iteration(self):
        self.iterations_count += 1

    def record_patch_attempt(self, target_id: str):
        self.patch_attempts[target_id] = self.patch_attempts.get(target_id, 0) + 1

    def record_repetition(self, signature: str) -> bool:
        self.signatures[signature] = self.signatures.get(signature, 0) + 1
        return self.signatures[signature] <= self.config.max_repeated_signatures

    def check_progress(self, current_metric: float) -> bool:
        """
        Returns True if progress is being made (or it's the first measurement).
        False if no progress detected over several steps.
        """
        self.performance_history.append(current_metric)
        if len(self.performance_history) < 3:
            return True
        
        # Simple check: is current better than the average of previous ones?
        # Lower is usually better for performance metrics (e.g. time, miss rate)
        # We might need more sophisticated logic here later.
        return current_metric <= min(self.performance_history[:-1])

    def is_budget_exhausted(self) -> bool:
        return not (self.can_call_tool() and self.can_call_llm() and self.can_iterate())

    def __repr__(self):
        return (f"Guardrails(tools={self.tool_calls_count}/{self.config.max_tool_calls}, "
                f"llm={self.llm_calls_count}/{self.config.max_llm_calls}, "
                f"iters={self.iterations_count}/{self.config.max_iterations})")
