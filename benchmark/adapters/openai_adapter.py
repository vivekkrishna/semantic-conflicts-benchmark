"""OpenAI adapter — supports GPT-3.5, GPT-4, GPT-4o, o1, o3, o4 and any future models.

Usage:
    export OPENAI_API_KEY=sk-...
    python -m benchmark.run --adapter openai --model gpt-4o
    python -m benchmark.run --adapter openai --model o3
"""

from typing import Optional

from benchmark.adapters.base import ModelAdapter, AdapterResponse, parse_verdict_response

# o-series reasoning models require max_completion_tokens (not max_tokens)
# and do not support a temperature parameter (fixed at 1).
_REASONING_MODEL_PREFIXES = ("o1", "o2", "o3", "o4")


def _is_reasoning_model(model: str) -> bool:
    base = model.split("-")[0]
    return base in _REASONING_MODEL_PREFIXES


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI chat-completion models."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.0,
                 max_tokens: int = 512, api_key: Optional[str] = None) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Run: pip install 'semantic-conflicts-benchmark[openai]'"
            )
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = OpenAI(api_key=api_key)
        self._reasoning = _is_reasoning_model(model)

    @property
    def name(self) -> str:
        return f"openai/{self._model}"

    def predict(self, prompt: str) -> AdapterResponse:
        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
        }
        if self._reasoning:
            # o-series: temperature is fixed at 1; use max_completion_tokens
            kwargs["max_completion_tokens"] = self._max_tokens * 8
        else:
            kwargs["temperature"] = self._temperature
            kwargs["max_tokens"] = self._max_tokens

        response = self._client.chat.completions.create(**kwargs)
        raw = response.choices[0].message.content or ""
        return parse_verdict_response(raw)
