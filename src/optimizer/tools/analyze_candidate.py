from typing import List

from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult
from optimizer.tools.deterministic_heavy_compute import build_change_for_target, preferred_targets_for_project


class AnalyzeCandidateTool(Tool):
    """Records the selected target and strategy after LLM analysis."""

    @property
    def name(self) -> str:
        return "analyze_candidate"

    @property
    def allowed_states(self) -> List[State]:
        return [State.BASELINE_READY, State.PROFILE_READY]

    def execute(
        self,
        target: str = "unspecified",
        strategy: str = "inspect hot path",
        rationale: str = "",
        project_path: str = ".",
        rejected_targets: object = None,
        allow_deterministic_fallback: bool = False,
        **_: object,
    ) -> ToolResult:
        rejected = _normalize_rejected_targets(rejected_targets)
        if allow_deterministic_fallback:
            fallback_target = _fallback_target(project_path, target, rejected)
            if fallback_target is not None:
                target = fallback_target

            deterministic_change = build_change_for_target(project_path, target)
            if deterministic_change is not None:
                if _is_generic_strategy(strategy):
                    strategy = deterministic_change.strategy
                if not rationale.strip():
                    rationale = deterministic_change.rationale

        output = {
            "target": target,
            "strategy": strategy,
            "rationale": rationale,
        }
        return ToolResult(success=True, output=output, next_state=State.ANALYSIS_READY, metadata=output)


def _fallback_target(project_path: str, target: str, rejected_targets: set[str]) -> str | None:
    if not _is_generic_target(target) and target not in rejected_targets:
        return None
    unchanged_candidate = None
    for candidate in preferred_targets_for_project(project_path):
        if candidate in rejected_targets:
            continue
        change = build_change_for_target(project_path, candidate)
        if change is None:
            continue
        if change.changed:
            return candidate
        if unchanged_candidate is None:
            unchanged_candidate = candidate
    return unchanged_candidate


def _normalize_rejected_targets(value: object) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip() for item in value if str(item).strip()}
    return set()


def _is_generic_target(target: str) -> bool:
    normalized = (target or "").strip().lower()
    return normalized in {"", "unspecified", "unknown", "hot path", "inspect hot path", "candidate", "main loop"}


def _is_generic_strategy(strategy: str) -> bool:
    normalized = (strategy or "").strip().lower()
    return normalized in {"", "inspect hot path", "inspect hotspot", "inspect cache behavior", "inspect performance"}
