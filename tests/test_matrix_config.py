from optimizer.cli import _parse_provider_models_csv
from optimizer.evaluation.experiment_manager import ExperimentManager


def test_parse_provider_models_csv():
    parsed = _parse_provider_models_csv(
        "openrouter=google/gemini-3-flash-preview,ollama=qwen2.5-coder:7b"
    )
    assert parsed == [
        ("openrouter", "google/gemini-3-flash-preview"),
        ("ollama", "qwen2.5-coder:7b"),
    ]


def test_experiment_manager_uses_explicit_provider_model_pairs():
    configs = ExperimentManager().matrix(
        providers=["openrouter", "ollama"],
        models=["google/gemini-3-flash-preview", "qwen2.5-coder:7b"],
        prompt_packs=["default", "hardware_focus"],
        repetitions=1,
        provider_models=[
            ("openrouter", "google/gemini-3-flash-preview"),
            ("ollama", "qwen2.5-coder:7b"),
        ],
    )

    assert [(config.provider, config.model) for config in configs] == [
        ("openrouter", "google/gemini-3-flash-preview"),
        ("openrouter", "google/gemini-3-flash-preview"),
        ("ollama", "qwen2.5-coder:7b"),
        ("ollama", "qwen2.5-coder:7b"),
    ]
