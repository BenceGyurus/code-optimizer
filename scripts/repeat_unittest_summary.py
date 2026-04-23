#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import time
from statistics import mean, pstdev


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repeat unittest discovery and print a compact summary.")
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--start-dir", default=".")
    parser.add_argument("--python", default=sys.executable)
    return parser.parse_args()


def build_command(args: argparse.Namespace) -> list[str]:
    return [args.python, "-m", "unittest", "discover", "-s", args.start_dir, "-p", args.pattern, "-q"]


def compact_preview(text: str, max_lines: int = 8, max_chars: int = 400) -> str:
    lines = text.splitlines()[:max_lines]
    preview = "\n".join(lines)
    if len(preview) > max_chars:
        preview = preview[:max_chars]
    return preview


def main() -> int:
    args = parse_args()
    command = build_command(args)
    repetitions = max(1, args.repetitions)
    durations = []
    failed_runs = []
    parsed_test_counts = []

    for index in range(1, repetitions + 1):
        start = time.perf_counter()
        process = subprocess.run(command, text=True, capture_output=True, check=False)
        duration = time.perf_counter() - start
        durations.append(duration)
        combined = "\n".join(part for part in [process.stdout.strip(), process.stderr.strip()] if part).strip()
        test_count = parse_test_count(combined)
        if test_count is not None:
            parsed_test_counts.append(test_count)
        if process.returncode != 0:
            failed_runs.append(
                {
                    "iteration": index,
                    "returncode": process.returncode,
                    "duration": duration,
                    "preview": compact_preview(combined),
                }
            )

    summary = {
        "kind": "unittest_repeat_summary",
        "command": " ".join(command),
        "repetitions": repetitions,
        "passed_runs": repetitions - len(failed_runs),
        "failed_runs": len(failed_runs),
        "average_duration": mean(durations),
        "minimum_duration": min(durations),
        "maximum_duration": max(durations),
        "stdev_duration": pstdev(durations) if len(durations) > 1 else 0.0,
        "tests_per_run": round(mean(parsed_test_counts), 3) if parsed_test_counts else None,
        "status": "ok" if not failed_runs else "failed",
    }
    if failed_runs:
        summary["failures"] = failed_runs[:2]

    print(json.dumps(summary, ensure_ascii=True))
    return 0 if not failed_runs else 1


def parse_test_count(text: str) -> int | None:
    marker = "Ran "
    if marker not in text:
        return None
    try:
        tail = text.split(marker, 1)[1]
        return int(tail.split(" test", 1)[0].strip())
    except Exception:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
