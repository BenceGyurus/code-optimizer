#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

PROJECT="${1:-}"
if [[ -z "${PROJECT}" ]]; then
  echo "Usage: $0 <project.py> [output_dir]" >&2
  exit 1
fi
OUTPUT_DIR="${2:-results/debian-smoke-$(basename "${PROJECT}" .py)}"
PROJECT_FILE="$(basename "${PROJECT}")"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"
RUN_REPETITIONS="${RUN_REPETITIONS:-15}"
FUNCTION_PROFILE_REPETITIONS="${FUNCTION_PROFILE_REPETITIONS:-1}"
OLLAMA_MODEL_ID="${OLLAMA_MODEL_ID:-qwen2.5-coder:7b}"
EFFECTIVE_PROVIDER_MODELS="${PROVIDER_MODELS:-openrouter=openai/gpt-oss-120b:free}"
EFFECTIVE_PROMPT_PACKS="${PROMPT_PACKS:-knowledge_gen}"

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
export OLLAMA_HOST="${OLLAMA_HOST:-http://192.168.1.46:11434}"
export OLLAMA_FORMAT="${OLLAMA_FORMAT:-json}"
export OLLAMA_THINK="${OLLAMA_THINK:-false}"
export OLLAMA_ENDPOINT="${OLLAMA_ENDPOINT:-chat}"
export OLLAMA_TIMEOUT="${OLLAMA_TIMEOUT:-900}"
export OLLAMA_MODEL_ID
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

mkdir -p "${MPLCONFIGDIR}" "${XDG_CACHE_HOME}"
cd "${REPO_ROOT}"

TEST_COMMAND="\"${PYTHON_BIN}\" \"${REPO_ROOT}/scripts/repeat_unittest_summary.py\" --pattern \"${PROJECT_FILE}\" --repetitions ${RUN_REPETITIONS}"

if [[ ! -f "${PROJECT}" ]]; then
  echo "Project file not found: ${PROJECT}" >&2
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

if [[ "${EFFECTIVE_PROVIDER_MODELS}" == *"ollama="* ]]; then
  if ! "${PYTHON_BIN}" -c "import json, os, sys, urllib.request; host=os.environ['OLLAMA_HOST'].rstrip('/'); wanted=os.environ['OLLAMA_MODEL_ID']; data=json.load(urllib.request.urlopen(host + '/api/tags', timeout=5)); names={model.get('name') for model in data.get('models', [])}; sys.exit(0 if wanted in names else 2)" >/dev/null 2>&1; then
    echo "Ollama is unreachable at ${OLLAMA_HOST} or model ${OLLAMA_MODEL_ID} is missing." >&2
    exit 1
  fi
fi

"${PYTHON_BIN}" -m optimizer.cli evaluate \
  --project "${PROJECT}" \
  --provider-models "${EFFECTIVE_PROVIDER_MODELS}" \
  --prompt-packs "${EFFECTIVE_PROMPT_PACKS}" \
  --repetitions 1 \
  --runtime-repetitions "${RUN_REPETITIONS}" \
  --hardware-repetitions "${RUN_REPETITIONS}" \
  --test-command "${TEST_COMMAND}" \
  --benchmark-command "\"${PYTHON_BIN}\" ${PROJECT_FILE} --skip-tests --repetitions 1" \
  --profile-command "perf stat -e ${PERF_EVENTS} -- \"${PYTHON_BIN}\" ${PROJECT_FILE} --skip-tests --repetitions 1" \
  --function-profile-command "\"${PYTHON_BIN}\" -m cProfile -s cumulative ${PROJECT_FILE} --skip-tests --repetitions 1" \
  --function-profile-repetitions "${FUNCTION_PROFILE_REPETITIONS}" \
  --output-dir "${OUTPUT_DIR}" \
  --max-llm-calls 14 \
  --max-tool-calls 28 \
  --max-iterations 3 \
  --no-deterministic-fallback \
  --verbose
