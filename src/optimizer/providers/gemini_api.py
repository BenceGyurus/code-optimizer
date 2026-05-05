import os
import warnings
from typing import List, Optional

from optimizer.providers.base import LLMRequest, LLMResponse, Provider

google_genai = None
genai_types = None
new_sdk_checked = False
legacy_genai = None


class GeminiProvider(Provider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
        self._genai_types = None
        self._client = None
        if self.api_key:
            google_module, types_module = self._new_sdk_modules()
            self._genai_types = types_module
            self._client = google_module.Client(api_key=self.api_key) if google_module else None
        self._legacy_model = None
        if self.api_key and self._client is None:
            self._legacy_model = self._load_legacy_model()

    def is_available(self) -> bool:
        return bool(self.api_key) and (self._client is not None or self._legacy_model is not None)

    def list_models(self) -> List[str]:
        return [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]

    def resolve_default_model(self) -> str:
        return self.model_name

    def send_prompt(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")

        model = request.model or self.model_name
        prompt = request.prompt if not request.system_prompt else f"{request.system_prompt}\n\n{request.prompt}"
        prompt = (
            f"{prompt}\n\n"
            "Return exactly one JSON object. Do not include markdown, prose, or thinking text."
        )

        if self._client is not None:
            return self._send_with_new_sdk(model, prompt, request)
        if self._legacy_model is not None:
            return self._send_with_legacy_sdk(model, prompt, request)
        raise RuntimeError("Gemini provider is unavailable. Install google-genai or google-generativeai.")

    def _send_with_new_sdk(self, model: str, prompt: str, request: LLMRequest) -> LLMResponse:
        _, types_module = self._new_sdk_modules()
        if types_module is None:
            raise RuntimeError("Gemini provider is unavailable. Install google-genai.")
        config = types_module.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            response_mime_type="application/json",
        )
        response = self._client.models.generate_content(model=model, contents=prompt, config=config)
        usage = getattr(response, "usage_metadata", None)
        return LLMResponse(
            content=(getattr(response, "text", "") or "").strip(),
            model_name=model,
            provider_name=self.name,
            usage={
                "prompt_tokens": getattr(usage, "prompt_token_count", 0) if usage else 0,
                "completion_tokens": getattr(usage, "candidates_token_count", 0) if usage else 0,
                "total_tokens": getattr(usage, "total_token_count", 0) if usage else 0,
            },
        )

    def _send_with_legacy_sdk(self, model: str, prompt: str, request: LLMRequest) -> LLMResponse:
        legacy_genai = self._legacy_module()
        generation_config = legacy_genai.types.GenerationConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            stop_sequences=request.stop_sequences,
            response_mime_type="application/json",
        )
        legacy_model = legacy_genai.GenerativeModel(model)
        response = legacy_model.generate_content(prompt, generation_config=generation_config)
        usage = getattr(response, "usage_metadata", None)
        return LLMResponse(
            content=(getattr(response, "text", "") or "").strip(),
            model_name=model,
            provider_name=self.name,
            usage={
                "prompt_tokens": getattr(usage, "prompt_token_count", 0) if usage else 0,
                "completion_tokens": getattr(usage, "candidates_token_count", 0) if usage else 0,
                "total_tokens": getattr(usage, "total_token_count", 0) if usage else 0,
            },
        )

    def _load_legacy_model(self):
        if not self.api_key:
            return None
        legacy = self._legacy_module()
        if legacy is None:
            return None
        legacy.configure(api_key=self.api_key)
        return legacy.GenerativeModel(self.model_name)

    def _new_sdk_modules(self):
        global google_genai, genai_types, new_sdk_checked
        if new_sdk_checked:
            return google_genai, genai_types
        new_sdk_checked = True
        try:
            from google import genai as imported_google_genai
            from google.genai import types as imported_genai_types

            google_genai = imported_google_genai
            genai_types = imported_genai_types
        except ImportError:  # pragma: no cover - optional provider dependency
            google_genai = None
            genai_types = None
        return google_genai, genai_types

    def _legacy_module(self):
        global legacy_genai
        if legacy_genai is not None:
            return legacy_genai
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                import google.generativeai as imported_legacy_genai
            legacy_genai = imported_legacy_genai
        except ImportError:
            legacy_genai = None
        return legacy_genai

    @property
    def name(self) -> str:
        return "gemini"

    def supports_structured_output(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True
