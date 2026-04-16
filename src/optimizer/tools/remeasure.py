from typing import List, Optional

from optimizer.execution.runners import run_command
from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult
from optimizer.tools.profile_parser import (
    parse_hardware_counters,
    profiler_unavailable,
    summarize_counter_runs,
    unsupported_profile_output,
)


class RemeasureTool(Tool):
    """Runs benchmark and optional profiler after a verified patch."""

    @property
    def name(self) -> str:
        return "remeasure"

    @property
    def allowed_states(self) -> List[State]:
        return [State.VERIFIED]

    def execute(
        self,
        benchmark_cmd: Optional[str] = None,
        bench_cmd: Optional[str] = None,
        profile_cmd: Optional[str] = None,
        profile_command: Optional[str] = None,
        project_path: str = ".",
        runtime_repetitions: int = 1,
        hardware_repetitions: int = 1,
        **_: object,
    ) -> ToolResult:
        benchmark_cmd = benchmark_cmd or bench_cmd
        profile_cmd = profile_cmd or profile_command
        output = {
            "benchmark": [],
            "profile": [],
            "hardware_summary": {},
            "profiler": {"supported": bool(profile_cmd), "source": unsupported_profile_output(profile_cmd, "")["source"]},
        }
        counter_runs = []

        for _ in range(max(1, runtime_repetitions)):
            if benchmark_cmd:
                result = run_command(benchmark_cmd, cwd=project_path)
                output["benchmark"].append({"success": result.returncode == 0, "duration": result.duration, "stdout": result.stdout, "stderr": result.stderr})
                if result.returncode != 0:
                    return ToolResult(success=False, output=output, metadata=output)

        for _ in range(max(1, hardware_repetitions)):
            if profile_cmd:
                result = run_command(profile_cmd, cwd=project_path)
                counters = parse_hardware_counters(result.stdout, result.stderr)
                if counters:
                    counter_runs.append(counters)
                output["profile"].append(
                    {
                        "success": result.returncode == 0,
                        "duration": result.duration,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "hardware_counters": counters,
                    }
                )
                if result.returncode != 0:
                    if profiler_unavailable(profile_cmd, result.stderr, result.stdout, result.returncode):
                        output["profiler"] = unsupported_profile_output(
                            profile_cmd,
                            result.stderr.strip() or "Profiler command is unavailable on this machine.",
                        )
                        return ToolResult(success=True, output=output, next_state=State.REMEASURED, metadata=output)
                    return ToolResult(success=False, output=output, metadata=output)

        output["hardware_summary"] = summarize_counter_runs(counter_runs)
        return ToolResult(success=True, output=output, next_state=State.REMEASURED, metadata=output)
