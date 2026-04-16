# Optimizer Framework

Command-line, modular, LLM-driven optimization and evaluation framework.

The framework has two modes:

- `optimizer run`: runs one controlled optimization session on a project.
- `optimizer evaluate`: runs an experiment matrix across providers, models, prompt packs and repetitions.

## Architecture

```text
CLI
  -> Optimizer Runner / Evaluator Runner
  -> Orchestrator
     -> State Machine
     -> Guardrails
     -> Tool Registry
     -> Provider Registry
     -> Prompt Pack Loader
     -> Context Builder
     -> Artifact / Session / Result Stores
```

The state machine uses these states:

```text
INIT
BASELINE_READY
PROFILE_READY
ANALYSIS_READY
PATCH_PROPOSED
PATCH_APPLIED
VERIFIED
REMEASURED
DONE
FAILED
```

## CLI

```bash
optimizer run --project . --provider mock --prompt-pack default
optimizer evaluate --project . --provider mock --prompt-pack default --repetitions 3
optimizer providers list
optimizer models list --provider mock
optimizer prompt-packs list
optimizer doctor
```

During local development without installing the package:

```bash
PYTHONPATH=src .venv/bin/python -m optimizer.cli doctor
```

## Important Flags

- `--project`
- `--provider`
- `--model`
- `--prompt-pack`
- `--build-command`
- `--test-command`
- `--benchmark-command`
- `--profile-command`
- `--allow-all-changes`
- `--interactive-approval`
- `--non-interactive`
- `--max-tool-calls`
- `--max-llm-calls`
- `--max-iterations`
- `--runtime-repetitions`
- `--hardware-repetitions`
- `--output-dir`

## Providers

The registry includes API and CLI provider entries:

- API: `openai`, `gemini`, `anthropic`, `openrouter`, `mock`
- CLI: `openai-codex-cli`, `ollama`, `gemini-cli`, `github-copilot-cli`

Live API providers are represented by MVP adapters and report availability based on environment variables. The `mock` provider is used for deterministic local smoke tests.

## Tools

Registered tools:

- `inspect_codebase`
- `run_baseline`
- `profile_execution`
- `analyze_candidate`
- `propose_change`
- `apply_and_verify`
- `remeasure`
- `evaluate_result`
- optional `rollback_to_checkpoint`

## Prompt Packs

Prompt packs live under `prompts/` and must include:

- `master.md`
- `decision.md`
- `analyze_candidate.md`
- `propose_change.md`
- `evaluate_result.md`
- `config.yaml`

Included packs:

- `default`
- `hardware_focus`
- `concise`

## Results

Optimizer runs write session artifacts under:

```text
results/session_<timestamp>/
```

Evaluator runs write:

```text
results/eval_<timestamp>/
  experiment_matrix.yaml
  aggregated_results.csv
  aggregated_results.yaml
  charts/*.svg
  per_run/
  report.md
```

## Verification

```bash
PYTHONPATH=src .venv/bin/python -m compileall -q src/optimizer
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m optimizer.cli doctor
```
# code-optimizer
# code-optimizer
# code-optimizer
# code-optimizer
