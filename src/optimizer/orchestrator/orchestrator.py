import logging
import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, Optional

from rich.console import Console
from rich.text import Text

from optimizer.artifacts.store import ArtifactStore
from optimizer.llm.context_builder import ContextBuilder
from optimizer.llm.prompt_loader import PromptPack
from optimizer.orchestrator.guardrails import Guardrails, GuardrailsConfig
from optimizer.orchestrator.state_machine import State, StateMachine
from optimizer.providers.base import LLMRequest, Provider
from optimizer.state.models import SessionState
from optimizer.state.store import SessionStateStore
from optimizer.tools.registry import tool_registry

logger = logging.getLogger(__name__)
console = Console()

class Orchestrator:
    def __init__(self, 
                 project_path: str,
                 provider: Provider,
                 prompt_pack: PromptPack,
                 guardrails_config: Optional[GuardrailsConfig] = None,
                 interactive: bool = True,
                 build_command: Optional[str] = None,
                 test_command: Optional[str] = None,
                 benchmark_command: Optional[str] = None,
                 profile_command: Optional[str] = None,
                 runtime_repetitions: int = 1,
                 hardware_repetitions: int = 1,
                 output_dir: str = "results",
                 model: Optional[str] = None,
                 verbose: bool = True):
        self.original_project_path = project_path
        self.provider = provider
        self.prompt_pack = prompt_pack
        self.guardrails = Guardrails(guardrails_config or GuardrailsConfig())
        self.state_machine = StateMachine()
        self.artifact_store = ArtifactStore(output_dir=output_dir)
        self.workspace_root = os.path.join(self.artifact_store.session_dir, "workspace")
        self.project_path = self._prepare_project_workspace(project_path)
        self.state_store = SessionStateStore(self.artifact_store.session_dir)
        self.context_builder = ContextBuilder(os.path.basename(self.project_path))
        self.interactive = interactive
        self.verbose = verbose
        self.model = model or provider.resolve_default_model()
        self.command_args = {
            "project_path": self.project_path,
            "build_cmd": build_command,
            "test_cmd": test_command,
            "benchmark_cmd": benchmark_command,
            "bench_cmd": benchmark_command,
            "profile_cmd": profile_command,
            "patch_cwd": self.workspace_root if self.project_path != self.original_project_path else None,
            "runtime_repetitions": runtime_repetitions,
            "hardware_repetitions": hardware_repetitions,
        }
        self.session_state = SessionState(
            current_state=self.state_machine.current_state,
            approval_policy={"interactive": interactive},
            counters={"noop_patches": 0},
        )
        self.pending_patch = ""
        self._last_state_header = None
        self.source_context = self._load_source_context(display_path=self.original_project_path)

    def run(self):
        logger.info(f"Starting optimization session for {self.project_path}")
        workspace_suffix = f" workspace={self.project_path}" if self.project_path != self.original_project_path else ""
        self._emit(
            "SESSION",
            f"project={self.original_project_path}{workspace_suffix} provider={self.provider.name} model={self.model}",
            style="bold cyan",
        )
        
        while self.state_machine.current_state not in [State.DONE, State.FAILED]:
            if self.guardrails.is_budget_exhausted():
                logger.warning("Budget exhausted. Stopping session.")
                self._emit("GUARD", "budget exhausted, stopping", style="yellow")
                self.state_machine.force_terminal(State.DONE)
                break
                
            self._step()
            
        logger.info(f"Session finished with state: {self.state_machine.current_state.name}")
        self._emit("END", f"state={self.state_machine.current_state.name}", style="bold cyan")
        self._save_summary()
        return self.state_machine.current_state

    def _step(self):
        current_state = self.state_machine.current_state
        allowed_tools = tool_registry.list_tools(current_state)
        self._emit_state(current_state, allowed_tools)
        if not allowed_tools:
            logger.warning("No allowed tools for state %s", current_state.name)
            self._emit("FAIL", f"no allowed tools for state={current_state.name}", style="red")
            self.state_machine.transition_to(State.FAILED)
            return
        
        context_vars = self.context_builder.build_context(
            current_state=current_state,
            allowed_actions=allowed_tools,
            best_result=self.session_state.best_result,
            latest_result=self.session_state.latest_result,
            current_target=self.session_state.current_target,
            counters=self.session_state.counters,
            source_context=self.source_context,
            action_guidance=self._action_guidance(current_state),
        )
        
        master_prompt = self.prompt_pack.get_prompt("master")
        decision_prompt = self.prompt_pack.get_prompt("decision")
        if not master_prompt or not decision_prompt:
            raise ValueError(f"Prompt pack {self.prompt_pack.name} is missing master or decision prompt.")
        
        full_prompt = f"{self.context_builder.render_prompt(master_prompt, context_vars)}\n\n{self.context_builder.render_prompt(decision_prompt, context_vars)}"
        
        response = None
        try:
            self.guardrails.record_llm_call()
            self._emit("LLM", f"#{self.guardrails.llm_calls_count} {self.provider.name}/{self.model}", style="magenta")
            response = self.provider.send_prompt(LLMRequest(prompt=full_prompt, model=self.model))
            content = self._extract_json_object(response.content)
            decision = json.loads(content)
            action_name = decision.get("action")
            args = decision.get("args", {})
            reason = decision.get("reason", "No reason provided.")
            
            logger.info(f"LLM Decision: {action_name} - Reason: {reason}")
            self._emit("DECIDE", f"{action_name}  reason={self._short(reason, 120)}", style="green")
            normalized_action = self._normalize_action(action_name, allowed_tools, current_state)
            
            if normalized_action is None:
                logger.error(f"LLM proposed invalid action {action_name} for state {current_state.name}")
                self._emit("INVALID", f"action={action_name} state={current_state.name}", style="red")
                if not self.guardrails.record_repetition(f"invalid:{current_state.name}:{action_name}"):
                    self.state_machine.transition_to(State.FAILED)
                return
            if normalized_action != action_name:
                logger.warning(
                    "Normalized LLM action %s to %s for state %s",
                    action_name,
                    normalized_action,
                    current_state.name,
                )
                self._emit("NORMALIZE", f"{action_name} -> {normalized_action}", style="yellow")
                action_name = normalized_action

            tool = tool_registry.get_tool(action_name)
            if tool is None:
                logger.error("Tool %s not registered", action_name)
                self._emit("FAIL", f"tool not registered action={action_name}", style="red")
                self.state_machine.transition_to(State.FAILED)
                return

            args = self._inject_args(action_name, args, current_state)
            visible_args = {key: value for key, value in args.items() if key not in {"patch"}}

            if action_name == "apply_and_verify" and current_state == State.PATCH_PROPOSED and self.interactive and args.get("patch"):
                if not self._approve_change():
                    self.state_machine.transition_to(State.ANALYSIS_READY)
                    self.session_state.latest_result = {"approval": "rejected", "rollback_performed": False}
                    return

            self.guardrails.record_tool_call()
            self._emit("TOOL", f"start #{self.guardrails.tool_calls_count} {action_name} {self._format_args(visible_args)}", style="blue")
            
            result = tool.execute(**args)
            result_style = "green" if result.success else "red"
            self._emit("TOOL", f"end   {action_name} success={result.success} next={result.next_state.name if result.next_state else 'none'}", style=result_style)
            
            self.artifact_store.save_artifact(
                name=f"tool_output_{action_name}",
                tool_name=action_name,
                content=result.output,
                metadata=result.metadata
            )
            
            if result.success:
                self._emit_output_summary(action_name, result.output)
                if self._should_stop_after_noop(action_name, result.output):
                    self.state_machine.force_terminal(State.DONE)
                    self._emit("GUARD", "repeated no-op patches, stopping", style="yellow")
                    return
                if result.next_state:
                    if current_state == State.REMEASURED and result.next_state == State.ANALYSIS_READY:
                        self.guardrails.record_iteration()
                    if not self.state_machine.transition_to(result.next_state):
                        logger.error("Illegal state transition %s -> %s", current_state.name, result.next_state.name)
                        self._emit("FAIL", f"illegal transition {current_state.name} -> {result.next_state.name}", style="red")
                        self.state_machine.transition_to(State.FAILED)
                        return
                    self._emit("STATE", f"{current_state.name} -> {result.next_state.name}", style="cyan")
                self._update_session_state(action_name, result.output)
            else:
                logger.warning(f"Tool {action_name} failed: {result.output}")
                self._emit("FAIL", f"{action_name}: {self._short(str(result.output), 300)}", style="red")
                self.session_state.latest_result = result.output
                if action_name == "apply_and_verify":
                    self.state_machine.transition_to(State.FAILED)
                
        except Exception as e:
            preview = ((response.content if response else "") or "")[:1000]
            logger.error(f"Failed to process LLM decision: {e}. Response preview: {preview!r}")
            self._emit("ERROR", f"llm parse/error: {e}", style="red")
            self.artifact_store.save_artifact(
                name="llm_parse_error",
                tool_name="llm",
                content={"error": str(e), "response_preview": preview},
                metadata={"state": current_state.name, "provider": self.provider.name, "model": self.model},
            )
            if not self.guardrails.record_repetition(f"parse-error:{current_state.name}"):
                self.state_machine.transition_to(State.FAILED)

        self.session_state.current_state = self.state_machine.current_state
        self.session_state.counters = {
            "tool_calls": self.guardrails.tool_calls_count,
            "llm_calls": self.guardrails.llm_calls_count,
            "iterations": self.guardrails.iterations_count,
            "noop_patches": self.session_state.counters.get("noop_patches", 0),
        }
        self.state_store.save(self.session_state)

    def _emit_output_summary(self, action_name: str, output: Any) -> None:
        if not isinstance(output, dict):
            return
        if action_name == "propose_change":
            has_patch = bool(output.get("has_patch"))
            self._emit("CHANGE", f"proposal target={output.get('target')} has_patch={has_patch}", style="green" if has_patch else "yellow")
            if has_patch:
                patch = output.get("patch") or ""
                self._emit("PATCH", self._short(patch, 500), style="cyan")
        if action_name == "apply_and_verify":
            verification = output.get("verification_result") or {}
            if verification.get("noop_patch"):
                detail = "; ".join(verification.get("short_error_summary") or ["empty patch"])
                self._emit("CHANGE", f"no file changes: {self._short(detail, 220)}", style="yellow")
            elif verification.get("patch_applied"):
                self._emit("CHANGE", "file changes applied", style="green")
            elif verification.get("short_error_summary"):
                self._emit("CHANGE", f"patch not applied: {self._short('; '.join(verification['short_error_summary']), 220)}", style="yellow")
        if action_name in {"profile_execution", "remeasure"}:
            summary = output.get("hardware_summary") or {}
            profiler = output.get("profiler") or {}
            if profiler and profiler.get("supported") is False:
                self._emit("HW", self._short(str(profiler.get("message") or "Hardware counters unavailable on this machine."), 500), style="yellow")
            elif summary:
                self._emit("HW", self._short(json.dumps(summary, ensure_ascii=False), 500), style="cyan")

    def _should_stop_after_noop(self, action_name: str, output: Any) -> bool:
        if action_name != "apply_and_verify" or not isinstance(output, dict):
            return False
        verification = output.get("verification_result") or {}
        if not verification.get("noop_patch"):
            return False
        self.session_state.counters["noop_patches"] = self.session_state.counters.get("noop_patches", 0) + 1
        return self.session_state.counters["noop_patches"] >= 2

    def _inject_args(self, action_name: str, args: Dict[str, Any], current_state: State) -> Dict[str, Any]:
        merged = dict(args)
        for key, value in self.command_args.items():
            if key not in merged and value is not None:
                merged[key] = value
        merged["current_state"] = current_state.name
        if action_name == "apply_and_verify" and not merged.get("patch"):
            if self.pending_patch:
                merged["patch"] = self.pending_patch
                return merged
            latest = self.session_state.latest_result
            if isinstance(latest, dict) and latest.get("patch"):
                merged["patch"] = latest["patch"]
        if action_name == "evaluate_result":
            metadata = self.session_state.checkpoint_metadata
            merged.setdefault("baseline_result", metadata.get("baseline_result"))
            merged.setdefault("optimized_result", metadata.get("optimized_result") or self.session_state.latest_result)
        return merged

    def _update_session_state(self, action_name: str, output: Any) -> None:
        self.session_state.latest_result = output
        if isinstance(output, dict):
            if output.get("target"):
                self.session_state.current_target = output["target"]
            if output.get("patch"):
                self.pending_patch = output["patch"]
            if action_name == "apply_and_verify":
                verification = output.get("verification_result") or {}
                if verification.get("build_success") and verification.get("test_success"):
                    self.pending_patch = ""
            if action_name == "run_baseline":
                self.session_state.checkpoint_metadata["baseline_result"] = output
                self.session_state.best_result = output
            elif action_name == "remeasure":
                self.session_state.checkpoint_metadata["optimized_result"] = output
                self.session_state.best_result = output
            elif action_name == "evaluate_result":
                self.session_state.best_result = output

    def _save_summary(self) -> None:
        summary = {
            "final_state": self.state_machine.current_state.name,
            "provider": self.provider.name,
            "model": self.model,
            "original_project_path": self.original_project_path,
            "workspace_project_path": self.project_path,
            "workspace_root": self.workspace_root,
            "tool_calls": self.guardrails.tool_calls_count,
            "llm_calls": self.guardrails.llm_calls_count,
            "iterations": self.guardrails.iterations_count,
            "latest_result": self.session_state.latest_result,
            "best_result": self.session_state.best_result,
        }
        self.artifact_store.save_named_yaml("final_summary.yaml", summary)

    def _prepare_project_workspace(self, project_path: str) -> str:
        if not os.path.isfile(project_path):
            return project_path

        source = os.path.abspath(project_path)
        relative_path = self._stable_relative_path(source)
        destination = os.path.join(self.workspace_root, relative_path)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(source, destination)
        subprocess.run(["git", "init", "-q"], cwd=self.workspace_root, check=False)
        self.artifact_store.save_named_yaml(
            "workspace.yaml",
            {
                "original_project_path": project_path,
                "workspace_root": self.workspace_root,
                "workspace_project_path": destination,
                "mode": "copy_on_write",
            },
        )
        return destination

    def _stable_relative_path(self, source: str) -> str:
        try:
            relative_path = os.path.relpath(source, os.getcwd())
        except ValueError:
            relative_path = os.path.basename(source)
        if relative_path.startswith("..") or os.path.isabs(relative_path):
            return os.path.basename(source)
        return relative_path

    def _load_source_context(self, limit: int = 14000, display_path: Optional[str] = None) -> str:
        if not os.path.isfile(self.project_path):
            return ""
        try:
            with open(self.project_path, "r", encoding="utf-8") as handle:
                content = handle.read()
        except UnicodeDecodeError:
            return ""
        if len(content) > limit:
            content = content[:limit] + "\n# ... truncated ..."
        return f"File: {display_path or self.project_path}\n```python\n{content}\n```"

    def _action_guidance(self, current_state: State) -> str:
        if current_state == State.ANALYSIS_READY:
            return (
                "You must propose a concrete unified diff patch when action is propose_change. "
                "Use the source context. Prefer optimizing moving_average_slow, join_events_to_users_slow, "
                "category_totals_slow, or matrix_multiply. The patch must start with diff --git."
            )
        if current_state == State.PATCH_PROPOSED:
            return "If a patch exists, choose apply_and_verify. If no patch exists, choose rollback_to_checkpoint."
        return ""

    def _approve_change(self) -> bool:
        answer = input("Apply proposed change? [y]es / [a]ll / [n]o: ").strip().lower()
        if answer == "a":
            self.interactive = False
            return True
        return answer in {"y", "yes"}

    def _extract_json_object(self, content: str) -> str:
        text = (content or "").strip()
        if not text:
            raise ValueError("LLM returned an empty response.")

        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
        if "```json" in text:
            return text.split("```json", 1)[1].split("```", 1)[0].strip()
        if "```" in text:
            fenced = text.split("```", 1)[1].split("```", 1)[0].strip()
            if fenced.startswith("{"):
                return fenced

        start = text.find("{")
        if start < 0:
            raise ValueError("LLM response did not contain a JSON object.")

        depth = 0
        in_string = False
        escape = False
        for index, char in enumerate(text[start:], start=start):
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]

        raise ValueError("LLM response contained an incomplete JSON object.")

    def _normalize_action(self, action_name: Any, allowed_tools: list[str], current_state: State) -> Optional[str]:
        if not isinstance(action_name, str):
            return None

        normalized = action_name.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "inspect": "inspect_codebase",
            "inspect_code": "inspect_codebase",
            "baseline": "run_baseline",
            "run_benchmark": "run_baseline",
            "profile": "profile_execution",
            "analyze": "analyze_candidate",
            "analysis": "analyze_candidate",
            "propose": "propose_change",
            "patch": "propose_change",
            "apply": "apply_and_verify",
            "verify": "apply_and_verify",
            "apply_patch": "apply_and_verify",
            "rollback": "rollback_to_checkpoint",
            "measure": "remeasure",
            "evaluate": "evaluate_result",
            "finish": "evaluate_result",
            "done": "evaluate_result",
        }
        candidate = aliases.get(normalized, normalized)
        if candidate in allowed_tools:
            return candidate

        deterministic_fallbacks = {
            State.INIT: "run_baseline",
            State.BASELINE_READY: "analyze_candidate",
            State.PROFILE_READY: "analyze_candidate",
            State.ANALYSIS_READY: "propose_change",
            State.PATCH_PROPOSED: "apply_and_verify",
            State.PATCH_APPLIED: "apply_and_verify",
            State.VERIFIED: "remeasure",
            State.REMEASURED: "evaluate_result",
        }
        fallback = deterministic_fallbacks.get(current_state)
        if fallback in allowed_tools:
            return fallback
        return None

    def _emit_state(self, current_state: State, allowed_tools: list[str]) -> None:
        if not self.verbose:
            return
        if self._last_state_header != current_state:
            console.rule(f"[bold cyan]{current_state.name}[/bold cyan]")
            self._last_state_header = current_state
        self._emit("ALLOW", ", ".join(allowed_tools), style="dim")

    def _emit(self, label: str, message: str, style: str = "white") -> None:
        if not self.verbose:
            return
        label_text = Text(f"{label:<9}", style=style)
        console.print(label_text, Text(str(message)))

    def _format_args(self, args: Dict[str, Any]) -> str:
        compact = {}
        for key, value in args.items():
            if value is None:
                continue
            if key in {"runtime_repetitions", "hardware_repetitions"} and value == 1:
                continue
            compact[key] = self._short(str(value), 80)
        return json.dumps(compact, ensure_ascii=False)

    def _short(self, value: str, limit: int) -> str:
        text = str(value).replace("\n", "\\n")
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."
