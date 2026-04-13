"""OpenAI adapter — supports GPT-3.5, GPT-4, GPT-4o, o1, o3 and any future models.

Usage:
    export OPENAI_API_KEY=sk-...
    python -m benchmark.run --adapter openai --model gpt-4o
"""

from typing import Optional

from benchmark.adapters.base import ModelAdapter, AdapterResponse, VALID_VERDICTS, parse_verdict_response


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

    @property
    def name(self) -> str:
        return f"openai/{self._model}"

    def predict(self, prompt: str) -> AdapterResponse:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content or ""
        return parse_verdict_response(raw)
