import os
import litellm
import textwrap
import hashlib
import json
import re
import ast
from typing import Dict, Optional, List, Tuple, Any
from hunter import CodeMatch
from rich.console import Console
from rich.panel import Panel

# Suppress litellm helper messages
litellm.suppress_debug_info = True
console = Console()

class Optimizer:
    def __init__(
        self,
        provider: str,
        rules_config: Dict,
        allow_remote: bool = False,
        max_remote_file_percent: int = 20,
        remote_model: Optional[str] = None,
        decision_models: Optional[List[str]] = None,
        recursive_max_steps: int = 2,
        use_cache: bool = True,
        strict_llm: bool = True
    ):
        self.local_model = provider
        self.remote_model = remote_model
        self.decision_models = decision_models or []
        self.rules_config = rules_config
        self.allow_remote = allow_remote
        self.max_remote_file_percent = max_remote_file_percent
        self.recursive_max_steps = max(1, recursive_max_steps)
        self.use_cache = use_cache
        self.strict_llm = strict_llm
        self.cache_file = ".opticode_cache.json"
        self.fail_cache_file = ".opticode_failures.json"
        self.rule_vector_file = ".opticode_rule_vectors.json"
        self.cache = self._load_cache()
        self.fail_cache = self._load_fail_cache()
        self.rule_vectors = self._load_or_build_rule_vectors()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.local_calls = 0
        self.remote_calls = 0
        self.verify_calls = 0
        self.decision_calls = 0
        self.remote_skipped_due_to_percent = 0

        self.micro_system_prompt = (
            "You are a precise code optimizer. "
            "CRITICAL RULES:\n"
            "1. Output ONLY the optimized code block inside <optimized_code> tags.\n"
            "2. Start the optimized code at column 0.\n"
            "3. Ensure the result is syntactically valid.\n"
            "4. NEVER change the mathematical logic or result.\n"
            "5. NEVER leave a loop or if-statement without an indented body.\n"
            "6. [SAFETY] NEVER hoist expressions that depend on the loop variable outside the loop.\n"
            "7. [SAFETY] NEVER use a list comprehension for operations that depend on the updated state of the list during the loop (e.g., uniqueness checks). Use sets instead for O(N) performance.\n"
            "8. If you are unsure or cannot safely optimize, return <optimized_code>NO_CHANGE</optimized_code>."
        )

        self.repair_system_prompt = (
            "You are a precise code repair agent. "
            "CRITICAL RULES:\n"
            "1. Output ONLY the repaired full file inside <optimized_code> tags.\n"
            "2. Start the code at column 0.\n"
            "3. Ensure the result is syntactically valid.\n"
            "4. Fix only what is necessary to satisfy the failing tests."
        )

    def _load_cache(self) -> Dict:
        if not self.use_cache:
            return {}
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except: return {}
        return {}

    def _load_fail_cache(self) -> Dict:
        if os.path.exists(self.fail_cache_file):
            try:
                with open(self.fail_cache_file, "r") as f:
                    return json.load(f)
            except: return {}
        return {}

    def _load_or_build_rule_vectors(self) -> Dict[str, Dict[str, int]]:
        if os.path.exists(self.rule_vector_file):
            try:
                with open(self.rule_vector_file, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except:
                pass

        vectors = {}
        rules = self.rules_config.get("rules", {})
        for rule_id, rule in rules.items():
            text = " ".join([
                str(rule.get("description", "")),
                str(rule.get("bad_example", "")),
                str(rule.get("good_example", ""))
            ])
            vectors[rule_id] = self._tokenize_counts(text)
        try:
            with open(self.rule_vector_file, "w") as f:
                json.dump(vectors, f, indent=2)
        except:
            pass
        return vectors

    def _save_cache(self):
        if not self.use_cache:
            return
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=2)

    def _save_fail_cache(self):
        with open(self.fail_cache_file, "w") as f:
            json.dump(self.fail_cache, f, indent=2)

    def _get_hash(self, snippet: str, rule_id: str, model: str) -> str:
        return hashlib.md5(f"{rule_id}:{model}:{snippet}".encode()).hexdigest()

    def _normalize_model(self, model: str) -> str:
        if model.startswith("copilot/"):
            return "github_copilot/" + model.split("/", 1)[1]
        return model

    def mark_failed(self, snippet: str, rule_id: str, model: str) -> None:
        fail_hash = self._get_hash(snippet, rule_id, model)
        self.fail_cache[fail_hash] = True
        self._save_fail_cache()

    def _is_remote_model(self, model: Optional[str]) -> bool:
        if not model:
            return False
        return not model.startswith("ollama/")

    def _pick_decision_models(self, fallback_model: str) -> List[str]:
        models = [m for m in self.decision_models if m]
        if fallback_model and fallback_model not in models:
            models.append(fallback_model)
        return models

    def _build_micro_prompt(self, rule_id: str, description: str, snippet: str) -> str:
        rule = self.rules_config.get("rules", {}).get(rule_id, {})
        bad_example = rule.get("bad_example", "")
        good_example = rule.get("good_example", "")
        return (
            f"Task: Apply rule '{rule_id}' to optimize the code.\n"
            f"Rule description: {description}\n"
            f"Bad example:\n{bad_example}\n"
            f"Good example:\n{good_example}\n"
            "Constraints: keep semantics, no loop-variable hoisting, valid blocks.\n"
            "Return ONLY <optimized_code>. If unsafe, return NO_CHANGE.\n"
            "Code:\n"
            f"{snippet}"
        )

    def _strip_alias_lines(self, code: str) -> str:
        alias_pattern = re.compile(r"^\s*[A-Za-z_]\w*\s*=\s*([A-Za-z_]\w*|[A-Za-z_]\w*\.[A-Za-z_]\w*)\s*$")
        kept = []
        for line in code.splitlines():
            if alias_pattern.match(line):
                continue
            kept.append(line)
        return "\n".join(kept).strip()

    def is_noop_alias_change(self, original: str, optimized: str) -> bool:
        if not original or not optimized:
            return False
        if original.strip() == optimized.strip():
            return True
        stripped_original = self._strip_alias_lines(original)
        stripped_optimized = self._strip_alias_lines(optimized)
        return stripped_original == stripped_optimized

    def _contains_defs(self, node: ast.AST) -> bool:
        for sub in ast.walk(node):
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return True
        return False

    def _passes_strict_guard(self, original: str, optimized: str, rule_id: str) -> bool:
        try:
            orig_tree = ast.parse(original)
            opt_tree = ast.parse(optimized)
        except SyntaxError:
            return False
        if len(orig_tree.body) != 1 or len(opt_tree.body) != 1:
            return False
        orig_node = orig_tree.body[0]
        opt_node = opt_tree.body[0]

        if self._contains_defs(orig_node) != self._contains_defs(opt_node):
            return False

        if type(orig_node) != type(opt_node):
            if rule_id == "list_comprehension" and isinstance(orig_node, ast.For) and isinstance(opt_node, ast.Assign):
                return True
            return False

        if isinstance(orig_node, ast.For) and isinstance(opt_node, ast.For):
            if ast.dump(orig_node.target, include_attributes=False) != ast.dump(opt_node.target, include_attributes=False):
                return False
            if ast.dump(orig_node.iter, include_attributes=False) != ast.dump(opt_node.iter, include_attributes=False):
                return False
        return True

    def deterministic_optimize(self, match: CodeMatch) -> Optional[Dict]:
        clean_snippet = textwrap.dedent(match.snippet)
        if match.rule_id == "unnecessary_nested_loops":
            replacement = self._deterministic_uniqueness_rewrite(clean_snippet)
            if replacement:
                return {
                    "code": replacement,
                    "reasoning": "Deterministic uniqueness rewrite",
                    "focus": match.rule_id,
                    "speedup": "",
                    "cached": False,
                    "model": "deterministic"
                }
            replacement = self._deterministic_sum_rewrite(clean_snippet)
            if replacement:
                return {
                    "code": replacement,
                    "reasoning": "Deterministic sum rewrite",
                    "focus": match.rule_id,
                    "speedup": "",
                    "cached": False,
                    "model": "deterministic"
                }
        if match.rule_id == "list_comprehension":
            replacement = self._deterministic_list_comp_rewrite(clean_snippet)
            if replacement:
                return {
                    "code": replacement,
                    "reasoning": "Deterministic list comprehension rewrite",
                    "focus": match.rule_id,
                    "speedup": "",
                    "cached": False,
                    "model": "deterministic"
                }
        return None

    def _deterministic_sum_rewrite(self, snippet: str) -> Optional[str]:
        try:
            tree = ast.parse(snippet)
        except SyntaxError:
            return None

        for_node = None
        for node in tree.body:
            if isinstance(node, ast.For):
                for_node = node
                break
        if not for_node:
            return None

        new_body: List[ast.stmt] = []
        replaced = False
        for stmt in for_node.body:
            if isinstance(stmt, ast.For) and self._is_sum_inner_loop(stmt, for_node.body):
                assign = self._build_sum_assign(stmt, for_node.body)
                if assign:
                    new_body.append(assign)
                    replaced = True
                    continue
            new_body.append(stmt)

        if not replaced:
            return None

        new_for = ast.For(
            target=for_node.target,
            iter=for_node.iter,
            body=new_body,
            orelse=for_node.orelse,
            type_comment=for_node.type_comment
        )
        ast.copy_location(new_for, for_node)
        ast.fix_missing_locations(new_for)
        return ast.unparse(new_for)

    def _is_sum_inner_loop(self, inner: ast.For, outer_body: List[ast.stmt]) -> bool:
        if not isinstance(inner.target, ast.Name):
            return False
        if not isinstance(inner.iter, ast.Name):
            return False
        if len(inner.body) != 1:
            return False
        aug = inner.body[0]
        if not isinstance(aug, ast.AugAssign):
            return False
        if not isinstance(aug.op, (ast.Add, ast.Sub)):
            return False
        if not isinstance(aug.target, ast.Name):
            return False
        if not self._is_float_call_on_name(aug.value, inner.target.id):
            return False
        if not self._has_amounts_assign(inner.iter.id, outer_body):
            return False
        if not self._has_zero_init(aug.target.id, outer_body):
            return False
        return True

    def _build_sum_assign(self, inner: ast.For, outer_body: List[ast.stmt]) -> Optional[ast.Assign]:
        aug = inner.body[0]
        if not isinstance(aug, ast.AugAssign):
            return None
        if not isinstance(aug.target, ast.Name):
            return None
        if not isinstance(inner.iter, ast.Name):
            return None
        if not isinstance(inner.target, ast.Name):
            return None
        amounts_name = inner.iter.id
        amount_var = inner.target.id
        elt = ast.Call(func=ast.Name(id="float", ctx=ast.Load()), args=[ast.Name(id=amount_var, ctx=ast.Load())], keywords=[])
        gen = ast.GeneratorExp(
            elt=elt,
            generators=[ast.comprehension(
                target=ast.Name(id=amount_var, ctx=ast.Store()),
                iter=ast.Name(id=amounts_name, ctx=ast.Load()),
                ifs=[],
                is_async=0
            )]
        )
        sum_call = ast.Call(func=ast.Name(id="sum", ctx=ast.Load()), args=[gen], keywords=[])
        value = sum_call
        if isinstance(aug.op, ast.Sub):
            value = ast.UnaryOp(op=ast.USub(), operand=sum_call)
        assign = ast.Assign(targets=[ast.Name(id=aug.target.id, ctx=ast.Store())], value=value)
        ast.copy_location(assign, inner)
        ast.fix_missing_locations(assign)
        return assign

    def _has_amounts_assign(self, name: str, outer_body: List[ast.stmt]) -> bool:
        for stmt in outer_body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if isinstance(target, ast.Name) and target.id == name:
                    return True
        return False

    def _has_zero_init(self, name: str, outer_body: List[ast.stmt]) -> bool:
        for stmt in outer_body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(stmt.value, ast.Constant) and stmt.value.value in (0, 0.0):
                        return True
        return False

    def _is_float_call_on_name(self, node: ast.AST, name: str) -> bool:
        if not isinstance(node, ast.Call):
            return False
        if not isinstance(node.func, ast.Name) or node.func.id != "float":
            return False
        if len(node.args) != 1:
            return False
        return isinstance(node.args[0], ast.Name) and node.args[0].id == name

    def _deterministic_list_comp_rewrite(self, snippet: str) -> Optional[str]:
        try:
            tree = ast.parse(snippet)
        except SyntaxError:
            return None
        for_node = None
        for node in tree.body:
            if isinstance(node, ast.For):
                for_node = node
                break
        if not for_node or len(for_node.body) != 1:
            return None
        stmt = for_node.body[0]
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                comp = ast.ListComp(
                    elt=call.args[0] if call.args else ast.Constant(value=None),
                    generators=[ast.comprehension(target=for_node.target, iter=for_node.iter, ifs=[], is_async=0)]
                )
                assign = ast.Assign(targets=[call.func.value], value=comp)
                ast.copy_location(assign, for_node)
                ast.fix_missing_locations(assign)
                return ast.unparse(assign)
        return None

    def _deterministic_uniqueness_rewrite(self, snippet: str) -> Optional[str]:
        try:
            tree = ast.parse(snippet)
        except SyntaxError:
            return None
        for_node = None
        for node in tree.body:
            if isinstance(node, ast.For):
                for_node = node
                break
        if not for_node or len(for_node.body) != 1:
            return None
        if_node = for_node.body[0]
        if not isinstance(if_node, ast.If) or if_node.orelse:
            return None
        if len(if_node.body) != 1:
            return None
        test = if_node.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            return None
        if not isinstance(test.ops[0], ast.NotIn):
            return None
        if len(test.comparators) != 1:
            return None
        left = test.left
        right = test.comparators[0]
        if not isinstance(left, ast.Name) or not isinstance(right, ast.Name):
            return None
        inner = if_node.body[0]
        if not isinstance(inner, ast.Expr) or not isinstance(inner.value, ast.Call):
            return None
        call = inner.value
        if not (isinstance(call.func, ast.Attribute) and call.func.attr == "append"):
            return None
        if not isinstance(call.func.value, ast.Name):
            return None
        if call.func.value.id != right.id:
            return None
        seen_name = f"{right.id}_seen"
        target_code = ast.unparse(for_node.target)
        iter_code = ast.unparse(for_node.iter)
        item_code = ast.unparse(left)
        list_code = ast.unparse(right)

        lines = [
            f"{seen_name} = set()",
            f"for {target_code} in {iter_code}:",
            f"    if {item_code} not in {seen_name}:",
            f"        {list_code}.append({item_code})",
            f"        {seen_name}.add({item_code})",
        ]
        return "\n".join(lines)

    def _build_verify_prompt(self, original: str, optimized: str, rule_id: str) -> str:
        return (
            "Verify if the optimized code preserves semantics and follows safety rules.\n"
            f"Rule: {rule_id}\n"
            "Answer ONLY with YES or NO.\n"
            "Original:\n"
            f"{original}\n"
            "Optimized:\n"
            f"{optimized}"
        )

    def _tokenize_counts(self, text: str) -> Dict[str, int]:
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z_0-9]+", text.lower())
        counts: Dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        return counts

    def _vector_score(self, a: Dict[str, int], b: Dict[str, int]) -> float:
        if not a or not b:
            return 0.0
        dot = 0
        a_norm = 0
        b_norm = 0
        for key, val in a.items():
            a_norm += val * val
            if key in b:
                dot += val * b[key]
        for val in b.values():
            b_norm += val * val
        if a_norm == 0 or b_norm == 0:
            return 0.0
        return dot / ((a_norm ** 0.5) * (b_norm ** 0.5))

    def retrieve_candidates(self, snippet: str, top_k: int = 3) -> List[str]:
        snippet_vec = self._tokenize_counts(snippet)
        scored: List[Tuple[str, float]] = []
        for rule_id, vec in self.rule_vectors.items():
            score = self._vector_score(snippet_vec, vec)
            scored.append((rule_id, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return [rule_id for rule_id, score in scored[:top_k] if score > 0.0]

    def _build_repair_prompt(self, file_content: str, test_output: str) -> str:
        return (
            "Task: Fix the code to satisfy the failing tests.\n"
            "Return ONLY <optimized_code> with the full file content.\n"
            "Failing tests output:\n"
            f"{test_output}\n"
            "File:\n"
            f"{file_content}"
        )

    def _build_repair_verify_prompt(self, original: str, optimized: str, test_output: str) -> str:
        return (
            "Verify if the optimized file likely fixes the failing tests described.\n"
            "Answer ONLY with YES or NO.\n"
            "Failing tests output:\n"
            f"{test_output}\n"
            "Original file:\n"
            f"{original}\n"
            "Optimized file:\n"
            f"{optimized}"
        )

    def _extract_tag(self, tag: str, text: str) -> str:
        res = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return res.group(1).strip() if res else ""

    def _get_usage(self, response: Any) -> Dict:
        if isinstance(response, dict):
            usage = response.get("usage", {})
            return usage if isinstance(usage, dict) else {}
        usage = getattr(response, "usage", None)
        return usage if isinstance(usage, dict) else {}

    def _get_message_content(self, response: Any) -> str:
        if isinstance(response, dict):
            try:
                return response["choices"][0]["message"]["content"] or ""
            except Exception:
                return ""
        choices = getattr(response, "choices", None)
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        if not message:
            return ""
        return getattr(message, "content", "") or ""

    def _validate_snippet_syntax(self, code: str) -> bool:
        try:
            ast.parse(textwrap.dedent(code))
            return True
        except SyntaxError:
            return False

    def _optimize_with_model(self, model: str, system_prompt: str, user_prompt: str, call_type: str) -> Optional[str]:
        if call_type == "local":
            self.local_calls += 1
        elif call_type == "remote":
            self.remote_calls += 1

        normalized_model = self._normalize_model(model)
        self._prepare_env(normalized_model)
        try:
            if "gpt-5" in normalized_model:
                litellm.drop_params = True
                response = litellm.completion(
                    model=normalized_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=1
                )
            else:
                response = litellm.completion(
                    model=normalized_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1
                )
        except Exception as e:
            message = str(e)
            if "NOT_FOUND" in message and normalized_model.startswith("gemini/"):
                fallback_models = [
                    "gemini/gemini-2-flash-lite",
                    "gemini/gemini-2.0-flash-exp",
                    "gemini/gemini-1.5-flash-latest",
                ]
                response = None
                for fallback_model in fallback_models:
                    if fallback_model == normalized_model:
                        continue
                    try:
                        response = litellm.completion(
                            model=fallback_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.1
                        )
                        break
                    except Exception:
                        continue
                if response is None:
                    raise
            else:
                raise

        usage = self._get_usage(response)
        self.total_tokens += usage.get("total_tokens", 0)
        try:
            self.total_cost += litellm.completion_cost(response)
        except:
            pass

        return self._get_message_content(response).strip()

    def _verify_with_model(self, model: str, prompt: str) -> bool:
        self.verify_calls += 1
        normalized_model = self._normalize_model(model)
        self._prepare_env(normalized_model)
        try:
            if "gpt-5" in normalized_model:
                litellm.drop_params = True
                response = litellm.completion(
                    model=normalized_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1
                )
            else:
                response = litellm.completion(
                    model=normalized_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
        except Exception as e:
            message = str(e)
            if "NOT_FOUND" in message and normalized_model.startswith("gemini/"):
                fallback_models = [
                    "gemini/gemini-2-flash-lite",
                    "gemini/gemini-2.0-flash-exp",
                    "gemini/gemini-1.5-flash-latest",
                ]
                response = None
                for fallback_model in fallback_models:
                    if fallback_model == normalized_model:
                        continue
                    try:
                        response = litellm.completion(
                            model=fallback_model,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0
                        )
                        break
                    except Exception:
                        continue
                if response is None:
                    raise
            else:
                raise
        usage = self._get_usage(response)
        self.total_tokens += usage.get("total_tokens", 0)
        try:
            self.total_cost += litellm.completion_cost(response)
        except:
            pass
        content = self._get_message_content(response).strip().upper()
        return content.startswith("YES")

    def rerank_rules(self, snippet: str, candidates: List[str]) -> str:
        if len(candidates) <= 1:
            return candidates[0] if candidates else "general_optimization"

        rules_desc = ""
        for c in candidates:
            desc = self.rules_config.get("rules", {}).get(c, {}).get("description", "General fix")
            rules_desc += f"- {c}: {desc}\n"

        rerank_prompt = f"""
I have retrieved multiple potential optimization rules for this Python snippet.
Rerank them and pick the ONE that provides the highest performance gain.

SNIPPET:
{snippet}

CANDIDATES:
{rules_desc}

Respond ONLY with the RULE_ID of the best rule.
"""
        try:
            fallback_model = self.local_model or os.getenv("OPTIMIZER_LLM_PROVIDER", "gemini/gemini-1.5-flash-latest")
            for model in self._pick_decision_models(fallback_model):
                try:
                    self.decision_calls += 1
                    self._prepare_env(model)
                    response = litellm.completion(
                        model=model,
                        messages=[{"role": "user", "content": rerank_prompt}],
                        temperature=0
                    )
                    best_rule = self._get_message_content(response).strip()
                    for c in candidates:
                        if c in best_rule:
                            return c
                except Exception:
                    continue
            return candidates[0]
        except Exception:
            return candidates[0]

    def _prepare_env(self, model: str):
        """Sets up environment variables for the specific provider."""
        if "gemini" in model:
            google_key = os.getenv("GOOGLE_API_KEY")
            if not os.getenv("GEMINI_API_KEY") and google_key is not None and google_key != "":
                os.environ["GEMINI_API_KEY"] = google_key
        elif model.startswith("github/"):
            token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_API_KEY")
            if token:
                os.environ["GITHUB_API_KEY"] = token
        elif model.startswith("copilot/"):
            token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_API_KEY")
            if token:
                os.environ["GITHUB_API_KEY"] = token

    def _attempt_recursive_optimize(
        self,
        model: str,
        rule_id: str,
        description: str,
        snippet: str,
        call_type: str
    ) -> Optional[Tuple[str, str]]:
        user_prompt = self._build_micro_prompt(rule_id, description, snippet)
        decision_models = self._pick_decision_models(model)

        for _ in range(self.recursive_max_steps):
            content = self._optimize_with_model(model, self.micro_system_prompt, user_prompt, call_type)
            if not isinstance(content, str) or not content.strip():
                continue
            code = self._extract_tag("optimized_code", content) or content
            if not isinstance(code, str) or not code.strip():
                continue
            if code.strip() == "NO_CHANGE":
                return None
            if not self._validate_snippet_syntax(code):
                continue
            if self.strict_llm and not self._passes_strict_guard(snippet, code, rule_id):
                continue
            verify_prompt = self._build_verify_prompt(snippet, code, rule_id)
            verified = False
            for decision_model in decision_models:
                try:
                    self.decision_calls += 1
                    if self._verify_with_model(decision_model, verify_prompt):
                        verified = True
                        break
                except Exception:
                    continue
            if verified:
                return code, content
        return None

    def _attempt_recursive_repair(
        self,
        model: str,
        file_content: str,
        test_output: str,
        call_type: str
    ) -> Optional[Tuple[str, str]]:
        user_prompt = self._build_repair_prompt(file_content, test_output)
        decision_models = self._pick_decision_models(model)

        for _ in range(self.recursive_max_steps):
            content = self._optimize_with_model(model, self.repair_system_prompt, user_prompt, call_type)
            if not isinstance(content, str) or not content.strip():
                continue
            code = self._extract_tag("optimized_code", content) or content
            if not isinstance(code, str) or not code.strip():
                continue
            if not self._validate_snippet_syntax(code):
                continue
            verify_prompt = self._build_repair_verify_prompt(file_content, code, test_output)
            verified = False
            for decision_model in decision_models:
                try:
                    self.decision_calls += 1
                    if self._verify_with_model(decision_model, verify_prompt):
                        verified = True
                        break
                except Exception:
                    continue
            if verified:
                return code, content
        return None

    def optimize_snippet(
        self,
        match: CodeMatch,
        best_rule_id: Optional[str] = None,
        file_path: Optional[str] = None,
        total_lines: Optional[int] = None
    ) -> Optional[Dict]:
        rule_id = best_rule_id or match.rule_id
        rule = self.rules_config.get("rules", {}).get(rule_id, {})
        clean_snippet = textwrap.dedent(match.snippet)

        if rule_id != "static_analysis_issue":
            candidates = self.retrieve_candidates(clean_snippet, top_k=3)
            if rule_id not in candidates:
                return None

        local_model = self.local_model or os.getenv("OPTIMIZER_LLM_PROVIDER", "gemini/gemini-1.5-flash-latest")
        snippet_hash = self._get_hash(clean_snippet, rule_id, local_model)
        if snippet_hash in self.fail_cache:
            return None
        if self.use_cache and snippet_hash in self.cache:
            return self.cache[snippet_hash]

        try:
            local_result = self._attempt_recursive_optimize(
                local_model,
                rule_id,
                rule.get("description", ""),
                clean_snippet,
                "local"
            )
            if local_result:
                code, content = local_result
                result = {
                    "code": code,
                    "reasoning": self._extract_tag("reasoning", content),
                    "focus": self._extract_tag("focus", content) or rule_id,
                    "speedup": self._extract_tag("speedup", content),
                    "cached": False,
                    "model": local_model
                }
                if self.use_cache:
                    self.cache[snippet_hash] = result
                    self.cache[snippet_hash]["cached"] = True
                    self._save_cache()
                return result

            if not self.allow_remote:
                return None

            remote_model = self.remote_model or local_model
            remote_hash = self._get_hash(clean_snippet, rule_id, remote_model)
            if remote_hash in self.fail_cache:
                return None
            if self._is_remote_model(remote_model):
                if total_lines and total_lines > 0:
                    snippet_lines = match.end_line - match.start_line + 1
                    percent = (snippet_lines / total_lines) * 100
                    if percent > self.max_remote_file_percent:
                        self.remote_skipped_due_to_percent += 1
                        return None

            remote_result = self._attempt_recursive_optimize(
                remote_model,
                rule_id,
                rule.get("description", ""),
                clean_snippet,
                "remote"
            )
            if not remote_result:
                return None
            code, content = remote_result
            result = {
                "code": code,
                "reasoning": self._extract_tag("reasoning", content),
                "focus": self._extract_tag("focus", content) or rule_id,
                "speedup": self._extract_tag("speedup", content),
                "cached": False,
                "model": remote_model
            }
            if self.use_cache:
                self.cache[remote_hash] = result
                self.cache[remote_hash]["cached"] = True
                self._save_cache()
            return result
        except Exception as e:
            if "Authentication" in str(e) or "401" in str(e):
                console.print(Panel(f"[bold red]Authentication Error:[/bold red] {str(e)}\n"
                                    "If using Copilot token, try the 'GitHub Copilot Chat' option.",
                                    title="LLM Error", border_style="red"))
            else:
                console.print(Panel(f"[bold red]Communication Error:[/bold red] {str(e)}", title="LLM Error", border_style="red"))
            return None

    def repair_file(self, file_content: str, test_output: str) -> Optional[Dict]:
        model = self.local_model or os.getenv("OPTIMIZER_LLM_PROVIDER", "gemini/gemini-1.5-flash-latest")
        snippet_hash = self._get_hash(file_content, "repair_mode", model)
        if snippet_hash in self.fail_cache:
            return None
        if self.use_cache and snippet_hash in self.cache:
            return self.cache[snippet_hash]

        try:
            result_tuple = self._attempt_recursive_repair(model, file_content, test_output, "local")
            if not result_tuple:
                if not self.allow_remote:
                    return None
                remote_model = self.remote_model or model
                result_tuple = self._attempt_recursive_repair(remote_model, file_content, test_output, "remote")
                if not result_tuple:
                    return None
                model = remote_model

            code, content = result_tuple
            result = {
                "code": code,
                "reasoning": self._extract_tag("reasoning", content),
                "focus": "repair_mode",
                "speedup": "",
                "cached": False,
                "model": model
            }
            if self.use_cache:
                self.cache[snippet_hash] = result
                self.cache[snippet_hash]["cached"] = True
                self._save_cache()
            return result
        except Exception as e:
            console.print(Panel(f"[bold red]Communication Error:[/bold red] {str(e)}", title="LLM Error", border_style="red"))
            return None
