from typing import List, Optional

from optimizer.execution.runners import run_command
from optimizer.orchestrator.state_machine import State
from optimizer.tools.base import Tool, ToolResult

class RunBaselineTool(Tool):
    """Runs baseline build, tests and benchmark."""
    @property
    def name(self) -> str:
        return "run_baseline"

    @property
    def allowed_states(self) -> List[State]:
        return [State.INIT]

    def execute(
        self,
        build_cmd: Optional[str] = None,
        test_cmd: Optional[str] = None,
        bench_cmd: Optional[str] = None,
        benchmark_cmd: Optional[str] = None,
        project_path: str = ".",
        runtime_repetitions: int = 1,
        **_: object,
    ) -> ToolResult:
        results = {}
        bench_cmd = bench_cmd or benchmark_cmd
        
        if build_cmd:
            res = run_command(build_cmd, cwd=project_path)
            results["build"] = {"success": res.returncode == 0, "output": res.stdout, "error": res.stderr}
            if res.returncode != 0:
                return ToolResult(success=False, output="Build failed", metadata=results)

        if test_cmd:
            res = run_command(test_cmd, cwd=project_path)
            results["test"] = {"success": res.returncode == 0, "output": res.stdout, "error": res.stderr}
            if res.returncode != 0:
                return ToolResult(success=False, output="Tests failed", metadata=results)

        benchmark_runs = []
        for _ in range(max(1, runtime_repetitions)):
            if bench_cmd:
                res = run_command(bench_cmd, cwd=project_path)
                benchmark_runs.append({"success": res.returncode == 0, "output": res.stdout, "error": res.stderr, "duration": res.duration})
                if res.returncode != 0:
                    results["benchmark"] = benchmark_runs
                    return ToolResult(success=False, output="Benchmark failed", metadata=results)

        if benchmark_runs:
            durations = [run["duration"] for run in benchmark_runs]
            results["benchmark"] = {
                "runs": benchmark_runs,
                "duration": min(durations),
                "average_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
            }
        
        output = {"message": "Baseline established", **results}
        return ToolResult(
            success=True,
            output=output,
            next_state=State.BASELINE_READY,
            metadata=results
        )
