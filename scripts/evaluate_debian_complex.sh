#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

PROJECT="${1:-examples/complex_pipeline}"
OUTPUT_DIR="${2:-results/debian-complex-pipeline}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"
RUN_REPETITIONS="${RUN_REPETITIONS:-15}"
FUNCTION_PROFILE_REPETITIONS="${FUNCTION_PROFILE_REPETITIONS:-1}"
EFFECTIVE_PROVIDER_MODELS="${PROVIDER_MODELS:-openrouter=google/gemini-3.1-pro-preview,openrouter=openai/gpt-oss-120b,openrouter=openai/gpt-5.3-codex}"
EFFECTIVE_PROMPT_PACKS="${PROMPT_PACKS:-hypothesis_driven}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "Set OPENROUTER_API_KEY before running this script." >&2
  exit 1
fi

if ! command -v perf >/dev/null 2>&1; then
  echo "perf is not installed or not in PATH." >&2
  exit 1
fi

export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/matplotlib}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/optimizer-cache}"
export OPENROUTER_RESPONSE_FORMAT="${OPENROUTER_RESPONSE_FORMAT:-off}"
export OPENROUTER_TIMEOUT="${OPENROUTER_TIMEOUT:-180}"
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

mkdir -p "${MPLCONFIGDIR}" "${XDG_CACHE_HOME}"
cd "${REPO_ROOT}"

if [[ ! -d "${PROJECT}" ]]; then
  echo "Project directory not found: ${PROJECT}" >&2
  exit 1
fi

if ! "${PYTHON_BIN}" -c "import matplotlib" >/dev/null 2>&1; then
  echo "matplotlib is missing in ${PYTHON_BIN}. Install requirements before running." >&2
  exit 1
fi

PERF_EVENT_CANDIDATES=(
  cache-references
  cache-misses
  branches
  branch-misses
  L1-dcache-loads
  L1-dcache-load-misses
  LLC-loads
  LLC-load-misses
)
SUPPORTED_PERF_EVENTS=()
UNSUPPORTED_PERF_EVENTS=()
for event in "${PERF_EVENT_CANDIDATES[@]}"; do
  if perf stat -e "${event}" -- true >/dev/null 2>&1; then
    SUPPORTED_PERF_EVENTS+=("${event}")
  else
    UNSUPPORTED_PERF_EVENTS+=("${event}")
  fi
done

if [[ ${#SUPPORTED_PERF_EVENTS[@]} -eq 0 ]]; then
  echo "perf hardware counters are not available on this Debian machine." >&2
  echo "Typical fix: lower kernel.perf_event_paranoid and rerun." >&2
  exit 1
fi

PERF_EVENTS="$(IFS=,; echo "${SUPPORTED_PERF_EVENTS[*]}")"
export OPTIMIZER_UNSUPPORTED_PERF_EVENTS="$(IFS=,; echo "${UNSUPPORTED_PERF_EVENTS[*]}")"
if [[ ${#UNSUPPORTED_PERF_EVENTS[@]} -gt 0 ]]; then
  echo "perf warning: unsupported counters skipped: ${OPTIMIZER_UNSUPPORTED_PERF_EVENTS}" >&2
fi

TEST_COMMAND="\"${PYTHON_BIN}\" \"${REPO_ROOT}/scripts/repeat_unittest_summary.py\" --start-dir . --pattern \"test_*.py\" --repetitions ${RUN_REPETITIONS}"
BENCHMARK_COMMAND="\"${PYTHON_BIN}\" -m market_sim --skip-tests --repetitions 1"
PROFILE_COMMAND="perf stat -e ${PERF_EVENTS} -- \"${PYTHON_BIN}\" -m market_sim --skip-tests --repetitions 1"
FUNCTION_PROFILE_COMMAND="\"${PYTHON_BIN}\" -m cProfile -s cumulative -m market_sim --skip-tests --repetitions 1"

"${PYTHON_BIN}" -m optimizer.cli evaluate \
  --project "${PROJECT}" \
  --provider-models "${EFFECTIVE_PROVIDER_MODELS}" \
  --prompt-packs "${EFFECTIVE_PROMPT_PACKS}" \
  --repetitions 1 \
  --runtime-repetitions "${RUN_REPETITIONS}" \
  --hardware-repetitions "${RUN_REPETITIONS}" \
  --function-profile-repetitions "${FUNCTION_PROFILE_REPETITIONS}" \
  --test-command "${TEST_COMMAND}" \
  --benchmark-command "${BENCHMARK_COMMAND}" \
  --profile-command "${PROFILE_COMMAND}" \
  --function-profile-command "${FUNCTION_PROFILE_COMMAND}" \
  --output-dir "${OUTPUT_DIR}" \
  --max-llm-calls 18 \
  --max-tool-calls 36 \
  --max-iterations 4 \
  --no-deterministic-fallback \
  --verbose
