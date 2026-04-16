from optimizer.llm.context_builder import ContextBuilder
from optimizer.llm.prompt_loader import PromptPack


class PromptBuilder:
    def __init__(self, context_builder: ContextBuilder):
        self.context_builder = context_builder

    def build(self, prompt_pack: PromptPack, action: str, context: dict) -> str:
        master = prompt_pack.get_prompt("master") or ""
        action_prompt = prompt_pack.get_prompt(action) or prompt_pack.get_prompt("decision") or ""
        return "\n\n".join(
            [
                self.context_builder.render_prompt(master, context),
                self.context_builder.render_prompt(action_prompt, context),
            ]
        )
