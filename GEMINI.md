# 🧠 OptiCode: Foundational Memory & Architecture

## 🚀 Project Objective
OptiCode is a high-performance, hybrid (AST + LLM) code optimization CLI designed to reduce execution overhead, improve algorithmic complexity, and maintain strict code integrity through automated verification.

## 🏗️ Core Architecture
- **Hybrid Hunter Logic:** Uses Python's `ast` module for deterministic pattern matching (Hunter) combined with `Ruff` for static analysis.
- **Post-Retrieval Reranking:** When multiple rules apply to the same code block, the LLM reranks them to select the most impactful and safest optimization.
- **Indentation Normalization:** Implements a "Dedent -> Optimize -> Re-indent" workflow to ensure robust patching regardless of LLM output precision.
- **Iterative (Multi-pass) Optimization:** Re-scans files up to 3 times (default) to catch optimizations made possible by previous changes.

## 🛡️ Safety & Verification
- **Safety Check:** Every patch is parsed by `ast.parse` in memory before being written to disk.
- **Automated Verification:** Integration with `--test-cmd` (e.g., `pytest`) runs after every patch.
- **Intelligent Rollback:** Automatic or interactive restoration of original code if tests fail or syntax is broken.
- **Mathematical Integrity:** Strict system prompt instruction: *Never change the mathematical result, only the calculation performance.*

## 💰 Efficiency & Enterprise Features
- **Local Caching:** Snippet hashes and LLM responses are stored in `.opticode_cache.json` to eliminate redundant API calls.
- **Cost Tracking:** Real-time token usage and USD cost estimation via `litellm`.
- **Git Integration:** Automatic branch creation and per-patch commits for full traceability.
- **CI/CD Mode:** Nona-interactive `--ci` flag for pipeline integration.

## 🤖 Model Ecosystem
- **Dynamic Selection:** Real-time fetching of models from GitHub Marketplace, GitHub Copilot, and local Ollama instances.
- **Authentication:** Integrated guidance for GitHub Personal Access Tokens (PAT) with `models` scope and Gemini API keys.

## 📜 Coding Mandates (Rules for LLM)
1. **No Loop-Variable Hoisting:** Never move expressions outside a loop if they depend on the loop variable.
2. **Set-based Uniqueness:** For $O(N)$ uniqueness checks, prefer `set()` over list comprehensions with `in` checks.
3. **PEP8 Imports:** Always move nested imports to the top level using the `finalize_imports` logic.
4. **Valid Blocks:** Never leave a control structure (loop/if) without a body.

## 📁 Current Project Status
- **Core CLI:** `cli.py` (Stable)
- **Engine:** `hunter.py`, `optimizer.py`, `patcher.py`, `linter.py`, `auth.py`
- **Rules:** `rules.yaml` (Updated with safety few-shots)
- **Tests:** `test_logic.py`, `example/test_suite.py`
