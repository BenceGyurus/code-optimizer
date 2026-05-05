import os
from typing import List, Optional

from optimizer.execution.runners import run_command
from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult
from optimizer.tools.profile_parser import (
    normalize_counter_names,
    parse_hardware_counters,
    parse_unsupported_counters,
    profiler_unavailable,
    profiler_source,
    summarize_counter_runs,
    unsupported_profile_output,
)


class ProfileExecutionTool(Tool):
    """Runs a profiler command and stores hardware/runtime counters when available."""

    @property
    def name(self) -> str:
        return "profile_execution"

    @property
    def allowed_states(self) -> List[State]:
        return [State.BASELINE_READY]

    def execute(
        self,
        profile_cmd: Optional[str] = None,
        profile_command: Optional[str] = None,
        project_path: str = ".",
        hardware_repetitions: int = 1,
        **_: object,
    ) -> ToolResult:
        command = profile_cmd or profile_command
        if not command:
            return ToolResult(
                success=True,
                output={
                    "message": "No profile command configured.",
                    "runs": [],
                    "hardware_summary": {},
                    "profiler": {"supported": False, "source": "none", "message": "No profile command configured."},
                },
                next_state=State.PROFILE_READY,
                metadata={"skipped": True},
            )

        runs = []
        counter_runs = []
        unsupported_counters = set(
            normalize_counter_names((os.environ.get("OPTIMIZER_UNSUPPORTED_PERF_EVENTS") or "").split(","))
        )
        for _ in range(max(1, hardware_repetitions)):
            result = run_command(command, cwd=project_path)
            counters = parse_hardware_counters(result.stdout, result.stderr)
            unsupported_counters.update(parse_unsupported_counters(result.stdout, result.stderr))
            if counters:
                counter_runs.append(counters)
            runs.append(
                {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration": result.duration,
                    "hardware_counters": counters,
                }
            )
            if result.returncode != 0:
                if profiler_unavailable(command, result.stderr, result.stdout, result.returncode):
                    output = {
                        "message": "Profiler is unavailable on this machine; hardware counters skipped.",
                        "runs": runs,
                        "hardware_summary": {},
                        "profiler": {
                            **unsupported_profile_output(command, result.stderr.strip() or "Profiler command is unavailable."),
                            "unsupported_counters": sorted(unsupported_counters),
                        },
                    }
                    return ToolResult(success=True, output=output, next_state=State.PROFILE_READY, metadata=output)
                return ToolResult(success=False, output="Profile command failed", metadata={"runs": runs})

        output = {
            "runs": runs,
            "hardware_summary": summarize_counter_runs(counter_runs),
            "profiler": {
                "supported": True,
                "source": profiler_source(command),
                "unsupported_counters": sorted(unsupported_counters),
            },
        }
        return ToolResult(success=True, output=output, next_state=State.PROFILE_READY, metadata=output)
