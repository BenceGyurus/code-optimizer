# 🧠 OptiCode V2: Architecture & Implementation Log

## 🚀 Project Objective
OptiCode V2 is a modular, state-machine driven, LLM-based optimization and evaluation framework. It shifts from a monolithic script to a robust orchestrator capable of both iterative code optimization and comprehensive experimental evaluation across models, prompt strategies, and hardware metrics.

---

## 🏗️ Architecture Blueprint (Target State)

### 1. Modes of Operation
*   **Optimizer Mode:** Iteratively improves a specific project's codebase.
*   **Evaluator Mode:** Runs experimental matrices (providers × models × prompts) on target codebases to compare performance, cost, and reliability.

### 2. Core Components
*   **CLI & Runners:** Primary interface (`optimizer run`, `optimizer evaluate`).
*   **Orchestrator:** The central controller. Executes the State Machine, enforces Guardrails, coordinates Tools.
*   **State Machine:** Enforces valid transitions (`INIT` -> `BASELINE_READY` -> ... -> `DONE`).
*   **Guardrails:** Budgets (tool/LLM calls), progress monitoring, repetition protection, rollback enforcement.
*   **Provider Registry:** Unified interface for API and CLI-based LLMs (OpenAI, Gemini, Ollama, Claude, Copilot).
*   **Tools:** Deterministic actions (`run_baseline`, `profile_execution`, `apply_and_verify`, etc.).
*   **Prompt Packs:** Pluggable prompt strategies (e.g., `hardware_focus`, `concise`).

---

## 📝 Implementation Progress Log

### Phase 1: MVP Scaffolding & Core Architecture
- [x] **Planning:** Define new architecture in `GEMINI.md`.
- [x] **Directory Structure:** Create `src/optimizer`, `config/`, `prompts/`, and `tests/` scaffolding.
- [x] **State Machine (`src/optimizer/orchestrator/state_machine.py`):** Define states and transitions.
- [x] **Guardrails (`src/optimizer/orchestrator/guardrails.py`):** Implement budget and repetition logic.
- [x] **Provider Base (`src/optimizer/providers/base.py`):** Define unified `Provider` interface.
- [x] **Mock Provider:** Implement a dummy provider for early orchestrator testing.

### Phase 2: Tooling & Verification
- [x] **Tool Registry (`src/optimizer/tools/registry.py`):** Dynamic tool loading and validation.
- [x] **Core Tools:** Implement `inspect_codebase`, `run_baseline`, `apply_and_verify`. (Initial tools implemented)
- [x] **Artifact Store (`src/optimizer/artifacts/store.py`):** Save logs, diffs, and metrics.

### Phase 3: Prompts & LLM Integration
- [x] **Prompt Loader (`src/optimizer/llm/prompt_loader.py`):** Read from `prompts/` directory.
- [x] **Context Builder (`src/optimizer/llm/context_builder.py`):** Assemble state into token-efficient context.
- [x] **Real Providers:** Implement `gemini_api.py`, `openai_api.py`. (Gemini implemented)

### Phase 4: CLI & Orchestrator Assembly
- [x] **Orchestrator Loop (`src/optimizer/orchestrator/orchestrator.py`):** The main `run` loop.
- [x] **CLI Implementation (`src/optimizer/cli.py`):** Typer-based interface.
- [x] **End-to-End Test:** Run a simple optimization session. (Verified with test_mvp.py)
- [x] **Example Project:** Create `examples/heavy_compute.py` for performance testing.

---

*Log is continuously updated as tasks are completed.*
