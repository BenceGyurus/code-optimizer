import os
from typing import List, Optional

from optimizer.execution.runners import run_command
from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult
from optimizer.tools.profile_parser import (
    filter_project_function_hotspots,
    function_profiler_source,
    normalize_counter_names,
    parse_function_profile,
    parse_hardware_counters,
    parse_unsupported_counters,
    profiler_unavailable,
    profiler_source,
    summarize_counter_runs,
    summarize_function_profile_runs,
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
        function_profile_cmd: Optional[str] = None,
        function_profile_command: Optional[str] = None,
        project_path: str = ".",
        hardware_repetitions: int = 1,
        function_profile_repetitions: int = 1,
        **_: object,
    ) -> ToolResult:
        command = profile_cmd or profile_command
        function_command = function_profile_cmd or function_profile_command
        if not command and not function_command:
            return ToolResult(
                success=True,
                output={
                    "message": "No profile command configured.",
                    "runs": [],
                    "hardware_summary": {},
                    "function_profile_runs": [],
                    "function_hotspots": [],
                    "profiler": {"supported": False, "source": "none", "message": "No profile command configured."},
                    "function_profiler": {"supported": False, "source": "none", "message": "No function profile command configured."},
                },
                next_state=State.PROFILE_READY,
                metadata={"skipped": True},
            )

        runs = []
        counter_runs = []
        unsupported_counters = set(
            normalize_counter_names((os.environ.get("OPTIMIZER_UNSUPPORTED_PERF_EVENTS") or "").split(","))
        )
        profiler = {
            "supported": bool(command),
            "source": profiler_source(command),
            "unsupported_counters": sorted(unsupported_counters),
        }
        if command:
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
                        profiler = {
                            **unsupported_profile_output(command, result.stderr.strip() or "Profiler command is unavailable."),
                            "unsupported_counters": sorted(unsupported_counters),
                        }
                        break
                    return ToolResult(success=False, output="Profile command failed", metadata={"runs": runs})
            profiler = {
                **profiler,
                "unsupported_counters": sorted(unsupported_counters),
            }
        else:
            profiler = {"supported": False, "source": "none", "message": "No hardware profile command configured.", "unsupported_counters": sorted(unsupported_counters)}

        function_profile_runs = []
        function_profile_parsed = []
        function_profiler = {
            "supported": bool(function_command),
            "source": function_profiler_source(function_command),
        }
        if function_command:
            for _ in range(max(1, function_profile_repetitions)):
                result = run_command(function_command, cwd=project_path)
                parsed = parse_function_profile(result.stdout, result.stderr)
                function_profile_parsed.append(parsed)
                function_profile_runs.append(
                    {
                        "success": result.returncode == 0,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "duration": result.duration,
                        "profile": parsed,
                    }
                )
                if result.returncode != 0:
                    return ToolResult(success=False, output="Function profile command failed", metadata={"function_profile_runs": function_profile_runs})
        else:
            function_profiler = {"supported": False, "source": "none", "message": "No function profile command configured."}

        function_hotspots = filter_project_function_hotspots(
            summarize_function_profile_runs(function_profile_parsed, top_n=40),
            project_path,
        )[:8]

        output = {
            "runs": runs,
            "hardware_summary": summarize_counter_runs(counter_runs),
            "function_profile_runs": function_profile_runs,
            "function_hotspots": function_hotspots,
            "profiler": profiler,
            "function_profiler": function_profiler,
        }
        return ToolResult(success=True, output=output, next_state=State.PROFILE_READY, metadata=output)
