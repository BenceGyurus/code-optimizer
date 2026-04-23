#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

PROJECT="${1:-examples/heavy_compute.py}"
OUTPUT_DIR="${2:-results/debian-full-$(basename "${PROJECT}" .py)}"
PROJECT_FILE="$(basename "${PROJECT}")"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"
RUN_REPETITIONS="${RUN_REPETITIONS:-15}"
OLLAMA_MODEL_ID="${OLLAMA_MODEL_ID:-qwen2.5-coder:7b}"

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
export OPENROUTER_RESPONSE_FORMAT="${OPENROUTER_RESPONSE_FORMAT:-off}"
export OPENROUTER_TIMEOUT="${OPENROUTER_TIMEOUT:-180}"
export OLLAMA_HOST="${OLLAMA_HOST:-http://192.168.1.46:11434}"
export OLLAMA_FORMAT="${OLLAMA_FORMAT:-json}"
export OLLAMA_THINK="${OLLAMA_THINK:-false}"
export OLLAMA_ENDPOINT="${OLLAMA_ENDPOINT:-chat}"
export OLLAMA_TIMEOUT="${OLLAMA_TIMEOUT:-900}"
export OLLAMA_MODEL_ID
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

mkdir -p "${MPLCONFIGDIR}"
cd "${REPO_ROOT}"

if [[ ! -f "${PROJECT}" ]]; then
  echo "Project file not found: ${PROJECT}" >&2
  exit 1
fi

if ! "${PYTHON_BIN}" -c "import matplotlib" >/dev/null 2>&1; then
  echo "matplotlib is missing in ${PYTHON_BIN}. Install requirements before running." >&2
  exit 1
fi

if ! perf stat -e cache-references,cache-misses,branches,branch-misses,L1-dcache-loads,L1-dcache-load-misses,LLC-loads,LLC-load-misses -- true >/dev/null 2>&1; then
  echo "perf hardware counters are not available on this Debian machine." >&2
  echo "Typical fix: lower kernel.perf_event_paranoid and rerun." >&2
  exit 1
fi

if ! "${PYTHON_BIN}" -c "import json, os, sys, urllib.request; host=os.environ['OLLAMA_HOST'].rstrip('/'); wanted=os.environ['OLLAMA_MODEL_ID']; data=json.load(urllib.request.urlopen(host + '/api/tags', timeout=5)); names={model.get('name') for model in data.get('models', [])}; sys.exit(0 if wanted in names else 2)" >/dev/null 2>&1; then
  echo "Ollama is unreachable at ${OLLAMA_HOST} or model ${OLLAMA_MODEL_ID} is missing." >&2
  exit 1
fi

"${PYTHON_BIN}" -m optimizer.cli evaluate \
  --project "${PROJECT}" \
  --provider-models "${PROVIDER_MODELS:-openrouter=google/gemini-3.1-pro-preview,openrouter=anthropic/claude-sonnet-4.6,openrouter=openai/gpt-5.4,openrouter=openai/gpt-oss-120b,openrouter=moonshotai/kimi-k2.6,openrouter=openai/gpt-5.3-codex,openrouter=minimax/minimax-m2.7,openrouter=google/gemini-3-flash-preview,openrouter=deepseek/deepseek-v3.2,ollama=${OLLAMA_MODEL_ID}}" \
  --prompt-packs "${PROMPT_PACKS:-default,hardware_focus,role_create,zero_shot,agentic,reasoning_goal,cot,least_to_most,concise,knowledge_gen}" \
  --repetitions 1 \
  --runtime-repetitions "${RUN_REPETITIONS}" \
  --hardware-repetitions "${RUN_REPETITIONS}" \
  --test-command "bash -lc 'for i in \$(seq 1 ${RUN_REPETITIONS}); do python3 -m unittest discover -s . -p \"${PROJECT_FILE}\" -q || exit 1; done'" \
  --benchmark-command "python3 ${PROJECT_FILE} --skip-tests --repetitions 1" \
  --profile-command "perf stat -e cache-references,cache-misses,branches,branch-misses,L1-dcache-loads,L1-dcache-load-misses,LLC-loads,LLC-load-misses -- python3 ${PROJECT_FILE} --skip-tests --repetitions 1" \
  --output-dir "${OUTPUT_DIR}" \
  --max-llm-calls 16 \
  --max-tool-calls 32 \
  --max-iterations 4 \
  --verbose
