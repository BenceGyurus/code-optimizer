import os
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import List

from optimizer.providers.base import LLMRequest, LLMResponse
from optimizer.providers.static import CommandProvider


class OllamaCliProvider(CommandProvider):
    provider_name = "ollama"
    executable = "ollama"
    default_models = ["llama3.1", "qwen2.5-coder", "deepseek-coder"]

    def is_available(self) -> bool:
        return self._http_available() or shutil.which(self.executable) is not None

    def resolve_default_model(self) -> str:
        configured = os.getenv("OLLAMA_MODEL")
        if configured:
            return configured
        models = self.list_models()
        return models[0] if models else self.default_models[0]

    def list_models(self) -> List[str]:
        http_models = self._list_models_http()
        if http_models:
            return http_models

        if shutil.which(self.executable):
            process = subprocess.run(["ollama", "list"], text=True, capture_output=True, check=False)
            if process.returncode == 0:
                lines = process.stdout.strip().splitlines()[1:]
                models = [line.split()[0] for line in lines if line.strip()]
                return models or self.default_models

        return self.default_models

    def send_prompt(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.resolve_default_model()
        prompt = self._decision_prompt(request)
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "600"))

        if self._should_use_http():
            return self._send_prompt_http(model=model, prompt=prompt, timeout=timeout)

        if not shutil.which(self.executable):
            raise RuntimeError(
                "Ollama is unavailable. Install the ollama CLI or set OLLAMA_HOST, "
                "for example: export OLLAMA_HOST=http://192.168.1.50:11434"
            )

        command = ["ollama", "run", model]
        if self._json_mode_enabled():
            command.extend(["--format", "json"])

        process = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(process.stderr.strip() or f"ollama run {model} failed.")

        return LLMResponse(
            content=process.stdout.strip(),
            model_name=model,
            provider_name=self.name,
        )

    def supports_structured_output(self) -> bool:
        return True

    def _decision_prompt(self, request: LLMRequest) -> str:
        prompt = request.prompt if not request.system_prompt else f"{request.system_prompt}\n\n{request.prompt}"
        return (
            f"{prompt}\n\n"
            "Critical output rule for Ollama: respond with exactly one JSON object and no markdown, "
            "no explanation, no <think> block. The JSON object must contain action, args, and reason. "
            "Keep all strings short. reason must be at most 12 words. Do not debate alternatives. "
            "For propose_change, include args.target, args.strategy, args.patch, and args.rationale; "
            "patch may be an empty string."
        )

    def _should_use_http(self) -> bool:
        return bool(os.getenv("OLLAMA_HOST")) or not shutil.which(self.executable)

    def _ollama_host(self) -> str:
        host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip().rstrip("/")
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"
        return host

    def _http_available(self) -> bool:
        try:
            self._get_json("/api/tags", timeout=2)
            return True
        except Exception:
            return False

    def _list_models_http(self) -> List[str]:
        try:
            payload = self._get_json("/api/tags", timeout=5)
        except Exception:
            return []
        return [model.get("name") for model in payload.get("models", []) if model.get("name")]

    def _send_prompt_http(self, model: str, prompt: str, timeout: int) -> LLMResponse:
        if os.getenv("OLLAMA_ENDPOINT", "chat").lower() == "generate":
            return self._send_prompt_generate_http(model=model, prompt=prompt, timeout=timeout)

        return self._send_prompt_chat_http(model=model, prompt=prompt, timeout=timeout)

    def _send_prompt_chat_http(self, model: str, prompt: str, timeout: int) -> LLMResponse:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": self._think_setting(),
            "options": {
                "temperature": 0,
                "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192")),
                "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "2048")),
            },
        }
        if self._json_mode_enabled():
            payload["format"] = "json"

        try:
            result = self._post_json("/api/chat", payload, timeout=timeout)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach Ollama at {self._ollama_host()}: {exc}") from exc

        if "error" in result:
            raise RuntimeError(f"Ollama error for model {model}: {result['error']}")

        message = result.get("message") or {}
        response_text = (message.get("content") or "").strip()
        thinking = (message.get("thinking") or "").strip()
        if not response_text:
            raise RuntimeError(
                "Ollama chat returned an empty message.content. "
                f"done={result.get('done')} done_reason={result.get('done_reason')} "
                f"eval_count={result.get('eval_count')} thinking_chars={len(thinking)}. "
                "For Qwen3-style thinking models keep OLLAMA_THINK=false, or try qwen2.5-coder."
            )

        return LLMResponse(
            content=response_text,
            model_name=model,
            provider_name=self.name,
            usage={
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
            },
        )

    def _send_prompt_generate_http(self, model: str, prompt: str, timeout: int) -> LLMResponse:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": self._think_setting(),
        }
        if self._json_mode_enabled():
            payload["format"] = "json"
        payload["options"] = {
            "temperature": 0,
            "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192")),
            "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "2048")),
        }

        try:
            result = self._post_json("/api/generate", payload, timeout=timeout)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach Ollama at {self._ollama_host()}: {exc}") from exc

        if "error" in result:
            raise RuntimeError(f"Ollama error for model {model}: {result['error']}")

        response_text = (result.get("response") or "").strip()
        if not response_text:
            thinking = (result.get("thinking") or "").strip()
            raise RuntimeError(
                "Ollama returned an empty response. "
                f"done={result.get('done')} done_reason={result.get('done_reason')} "
                f"eval_count={result.get('eval_count')} thinking_chars={len(thinking)}. "
                "For Qwen3-style thinking models keep OLLAMA_THINK=false, or try a coder/instruct model."
            )

        return LLMResponse(
            content=response_text,
            model_name=model,
            provider_name=self.name,
            usage={
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
            },
        )

    def _get_json(self, path: str, timeout: int) -> dict:
        request = urllib.request.Request(f"{self._ollama_host()}{path}", method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(self, path: str, payload: dict, timeout: int) -> dict:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._ollama_host()}{path}",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _json_mode_enabled(self) -> bool:
        return os.getenv("OLLAMA_FORMAT", "json").lower() not in {"0", "false", "text", "none"}

    def _think_setting(self):
        value = os.getenv("OLLAMA_THINK", "false").strip().lower()
        if value in {"0", "false", "no", "off"}:
            return False
        if value in {"1", "true", "yes", "on"}:
            return True
        return value
