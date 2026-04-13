"""OpenAI adapter — supports GPT-3.5, GPT-4, GPT-4o, o1, o3 and any future models.

Usage:
    export OPENAI_API_KEY=sk-...
    python -m benchmark.run --adapter openai --model gpt-4o
"""

import re
from typing import Optional

from benchmark.adapters.base import ModelAdapter, AdapterResponse, VALID_VERDICTS


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
        return _parse_response(raw)


def _parse_response(raw: str) -> AdapterResponse:
    """Extract verdict and explanation from the model's raw text output."""
    upper = raw.upper()
    verdict = "consistent"
    for v in ("CONFLICT", "AMBIGUOUS", "CONSISTENT"):
        if v in upper:
            verdict = v.lower()
            break

    explanation: Optional[str] = None
    if verdict in ("conflict", "ambiguous"):
        lines = raw.strip().splitlines()
        body_lines = [l for l in lines if not re.match(r"^\s*(CONFLICT|CONSISTENT|AMBIGUOUS)\s*$", l, re.I)]
        explanation = "\n".join(body_lines).strip() or raw.strip()

    return AdapterResponse(verdict=verdict, explanation=explanation, raw_response=raw)
