import shlex
import sys

from optimizer.execution.runners import run_command


def test_run_command_terminates_timed_out_process_tree():
    code = (
        "import subprocess, sys, time; "
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
        "time.sleep(30)"
    )
    command = f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"

    result = run_command(command, timeout=1)

    assert result.returncode == -1
    assert "process tree was terminated" in result.stderr
    assert result.duration < 8
