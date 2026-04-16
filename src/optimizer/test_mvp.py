import json
import logging

from optimizer.llm.prompt_loader import PromptLoader
from optimizer.orchestrator.guardrails import GuardrailsConfig
from optimizer.orchestrator.orchestrator import Orchestrator
from optimizer.providers.mock import MockProvider

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_mock_session():
    # 1. Setup mock responses
    mock_responses = [
        # Decision 1: Inspect codebase
        json.dumps({
            "action": "inspect_codebase",
            "args": {"project_path": "."},
            "reason": "Need to understand the project structure."
        }),
        # Decision 2: Run baseline
        json.dumps({
            "action": "run_baseline",
            "args": {"build_cmd": "echo 'building'", "test_cmd": "echo 'testing'", "bench_cmd": "echo 'benchmarking'"},
            "reason": "Establish baseline performance."
        })
    ]
    
    provider = MockProvider(responses=mock_responses)
    
    # 2. Get prompt pack
    loader = PromptLoader()
    pack = loader.get_pack("default")
    
    # 3. Setup Orchestrator
    config = GuardrailsConfig(max_iterations=5, max_llm_calls=2, max_tool_calls=2)
    orchestrator = Orchestrator(
        project_path=".",
        provider=provider,
        prompt_pack=pack,
        guardrails_config=config,
        interactive=False,
        output_dir="/tmp/optimizer-framework-test",
    )
    
    # 4. Run
    final_state = orchestrator.run()
    print(f"Final state: {final_state.name}")
    assert final_state.name == "DONE"

if __name__ == "__main__":
    test_mock_session()
