import json

from optimizer.llm.schemas import Decision


def parse_decision(content: str) -> Decision:
    if "```json" in content:
        content = content.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "{" in content and "}" in content:
        content = "{" + content.split("{", 1)[1].rsplit("}", 1)[0] + "}"
    data = json.loads(content)
    return Decision(action=data["action"], args=data.get("args", {}), reason=data.get("reason", ""))
