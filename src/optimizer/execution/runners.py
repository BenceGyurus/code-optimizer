import subprocess
import time
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class CommandResult:
    stdout: str
    stderr: str
    returncode: int
    duration: float

def run_command(command: str, cwd: Optional[str] = None, timeout: int = 300) -> CommandResult:
    start_time = time.time()
    command_cwd = _command_cwd(cwd)
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=command_cwd
        )
        stdout, stderr = process.communicate(timeout=timeout)
        duration = time.time() - start_time
        return CommandResult(
            stdout=stdout,
            stderr=stderr,
            returncode=process.returncode,
            duration=duration
        )

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return CommandResult(
            stdout="",
            stderr=f"Timeout after {timeout} seconds",
            returncode=-1,
            duration=duration
        )
    except Exception as e:
        duration = time.time() - start_time
        return CommandResult(
            stdout="",
            stderr=str(e),
            returncode=-2,
            duration=duration
        )


def _command_cwd(cwd: Optional[str]) -> Optional[str]:
    if cwd and os.path.isfile(cwd):
        return os.path.dirname(os.path.abspath(cwd)) or "."
    return cwd
