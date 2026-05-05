import os
import signal
import subprocess
import time
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
            cwd=command_cwd,
            start_new_session=os.name != "nt",
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
        _terminate_process_tree(process)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            _kill_process_tree(process)
            stdout, stderr = process.communicate()
        duration = time.time() - start_time
        return CommandResult(
            stdout=stdout or "",
            stderr=_combine_timeout_stderr(stderr, timeout),
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


def _terminate_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGTERM)
            return
        except ProcessLookupError:
            return
        except Exception:
            pass
    process.terminate()


def _kill_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
        except Exception:
            pass
    process.kill()


def _combine_timeout_stderr(stderr: str | None, timeout: int) -> str:
    timeout_message = f"Timeout after {timeout} seconds; process tree was terminated."
    stderr = (stderr or "").strip()
    return f"{timeout_message}\n{stderr}" if stderr else timeout_message
