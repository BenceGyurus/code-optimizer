import os
import litellm
import textwrap
import hashlib
import json
import time
from typing import Dict, Optional
from hunter import CodeMatch

# Suppress litellm helper messages
litellm.suppress_debug_info = True

class Optimizer:
    def __init__(self, provider: str, rules_config: Dict):
        self.provider = provider
        self.rules_config = rules_config
        self.cache_file = ".opticode_cache.json"
        self.cache = self._load_cache()
        self.total_cost = 0.0
        self.total_tokens = 0
        
        self.system_prompt = (
            "You are an expert automated code optimization agent. "
            "Your task is to apply performance optimization rules to Python code.\n"
            "CRITICAL RULES:\n"
            "1. Output ONLY the optimized code block inside <optimized_code> tags.\n"
            "2. Start the optimized code at column 0 (no leading spaces for the base level).\n"
            "3. Ensure the result is a complete, syntactically valid Python block.\n"
            "4. NEVER change the mathematical logic or result. Only change HOW it is calculated.\n"
            "5. NEVER leave a loop or if-statement without an indented body.\n"
            "Return your response in the following format:\n"
            "<optimized_code>\n[YOUR CODE HERE]\n</optimized_code>\n"
            "<reasoning>[EXPLAIN WHY THIS IS BETTER]</reasoning>\n"
            "<focus>[WHAT IS OPTIMIZED]</focus>\n"
            "<speedup>[ESTIMATED SPEEDUP]</speedup>"
        )

    def _load_cache(self) -> Dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=2)

    def _get_hash(self, snippet: str, rule_id: str) -> str:
        content = f"{rule_id}:{snippet}"
        return hashlib.md5(content.encode()).hexdigest()

    def optimize_snippet(self, match: CodeMatch) -> Optional[Dict]:
        rule = self.rules_config.get("rules", {}).get(match.rule_id, {})
        clean_snippet = textwrap.dedent(match.snippet)
        
        # 1. Check Cache
        snippet_hash = self._get_hash(clean_snippet, match.rule_id)
        if snippet_hash in self.cache:
            return self.cache[snippet_hash]

        user_prompt = f"Rule: {match.rule_id}\nCode:\n{clean_snippet}"
        
        try:
            model = os.getenv("OPTIMIZER_LLM_PROVIDER", "gemini/gemini-1.5-flash")
            if "gemini" in model and not model.startswith("gemini/"):
                model = f"gemini/{model}"

            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = litellm.completion(
                        model=model,
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.1
                    )
                    break 
                except litellm.RateLimitError:
                    if attempt < max_retries - 1:
                        time.sleep(20 * (attempt + 1))
                    else:
                        raise
            
            if not response:
                return None

            # Track usage and cost
            usage = response.get("usage", {})
            self.total_tokens += usage.get("total_tokens", 0)
            try:
                self.total_cost += litellm.completion_cost(response)
            except:
                pass # Some models might not have cost data in litellm yet

            content = response.choices[0].message.content.strip()
            
            import re
            def get_tag(tag, text):
                res = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
                return res.group(1).strip() if res else ""

            result = {
                "code": get_tag("optimized_code", content),
                "reasoning": get_tag("reasoning", content),
                "focus": get_tag("focus", content),
                "speedup": get_tag("speedup", content),
                "cached": False
            }

            # Save to Cache if valid
            if result["code"]:
                self.cache[snippet_hash] = result
                self.cache[snippet_hash]["cached"] = True
                self._save_cache()

            return result
        except Exception:
            return None
