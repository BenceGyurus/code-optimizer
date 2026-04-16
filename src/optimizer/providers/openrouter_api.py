import os
from typing import List

import requests

from optimizer.providers.base import LLMRequest, LLMResponse, Provider


class OpenRouterProvider(Provider):
    provider_name = "openrouter"
    api_base = "https://openrouter.ai/api/v1"
    default_models = [
        "openrouter/free",
        "deepseek/deepseek-chat-v3.1:free",
        "qwen/qwen3-coder:free",
        "meta-llama/llama-3.2-3b-instruct:free",
    ]

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

    @property
    def name(self) -> str:
        return self.provider_name

    def is_available(self) -> bool:
        return bool(self.api_key)

    def list_models(self) -> List[str]:
        try:
            response = requests.get(f"{self.api_base}/models", timeout=15)
            response.raise_for_status()
            models = [item["id"] for item in response.json().get("data", []) if item.get("id")]
            free_models = [model for model in models if model.endswith(":free")]
            return ["openrouter/free", *free_models] if free_models else self.default_models
        except Exception:
            return self.default_models

    def resolve_default_model(self) -> str:
        return os.getenv("OPENROUTER_MODEL") or "openrouter/free"

    def send_prompt(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set.")

        model = request.model or self.resolve_default_model()
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append(
            {
                "role": "user",
                "content": (
                    f"{request.prompt}\n\n"
                    "Return exactly one JSON object. Do not include markdown, prose, or thinking text."
                ),
            }
        )

        payload = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        if self._use_response_format(model):
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "optimizer-framework"),
        }

        response = self._post_chat(payload, headers)
        if response.status_code == 400 and "JSON mode is not enabled" in response.text and "response_format" in payload:
            payload = dict(payload)
            payload.pop("response_format", None)
            response = self._post_chat(payload, headers)
        if response.status_code >= 400:
            raise RuntimeError(f"OpenRouter error {response.status_code}: {response.text[:1000]}")

        data = response.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content") or ""
        usage = data.get("usage") or {}
        return LLMResponse(
            content=content.strip(),
            model_name=data.get("model") or model,
            provider_name=self.name,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=choice.get("finish_reason", "stop"),
        )

    def supports_structured_output(self) -> bool:
        return True

    def supports_tool_use(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return False

    def _use_response_format(self, model: str) -> bool:
        setting = os.getenv("OPENROUTER_RESPONSE_FORMAT", "auto").lower()
        if setting in {"0", "false", "off", "none"}:
            return False
        if setting in {"1", "true", "on", "json"}:
            return True
        return not model.endswith(":free") and model != "openrouter/free"

    def _post_chat(self, payload: dict, headers: dict) -> requests.Response:
        return requests.post(
            f"{self.api_base}/chat/completions",
            json=payload,
            headers=headers,
            timeout=int(os.getenv("OPENROUTER_TIMEOUT", "120")),
        )
