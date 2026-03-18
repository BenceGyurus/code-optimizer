import os
import litellm
from typing import Dict, Optional
from hunter import CodeMatch

# Load .env variables (handled in main entry)
class Optimizer:
    def __init__(self, provider: str, rules_config: Dict):
        self.provider = provider
        self.rules_config = rules_config
        self.system_prompt = (
            "You are an expert automated code optimization agent. "
            "Your task is to apply a specific performance optimization rule to the provided "
            "AST-extracted code snippet. "
            "Return your response in the following format:\n"
            "<optimized_code>\n[YOUR CODE HERE]\n</optimized_code>\n"
            "<reasoning>[EXPLAIN WHY THIS IS BETTER]</reasoning>\n"
            "<focus>[WHAT IS OPTIMIZED: e.g., Cache Locality, Redundancy, Algorithmic Complexity]</focus>\n"
            "<speedup>[ESTIMATED SPEEDUP: e.g., 2x, 10x, 1.5x]</speedup>"
        )

    def optimize_snippet(self, match: CodeMatch) -> Optional[Dict]:
        rule = self.rules_config.get("rules", {}).get(match.rule_id, {})
        
        user_prompt = f"""
Rule: {match.rule_id}
Description: {rule.get('description')}

Example Bad Code:
{rule.get('bad_example')}

Example Good Code:
{rule.get('good_example')}

YOUR TASK:
Optimize the following snippet and provide the metadata:
{match.snippet}
"""
        try:
            model = os.getenv("OPTIMIZER_LLM_PROVIDER", "gemini/gemini-1.5-flash")
            if "gemini" in model and not model.startswith("gemini/"):
                model = f"gemini/{model}"

            response = litellm.completion(
                model=model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            
            # Simple parsing of the custom tags
            import re
            def get_tag(tag, text):
                res = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
                return res.group(1).strip() if res else ""

            return {
                "code": get_tag("optimized_code", content),
                "reasoning": get_tag("reasoning", content),
                "focus": get_tag("focus", content),
                "speedup": get_tag("speedup", content)
            }
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return None
