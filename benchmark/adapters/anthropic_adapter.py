"""Anthropic adapter — supports all Claude models.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m benchmark.run --adapter anthropic --model claude-haiku-4-5-20251001
"""

import re
from typing import Optional

from benchmark.adapters.base import ModelAdapter, AdapterResponse


class AnthropicAdapter(ModelAdapter):
    """Adapter for Anthropic Claude models."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001",
                 max_tokens: int = 512, api_key: Optional[str] = None) -> None:
        try:
            import anthropic as _anthropic
        except ImportError:
            raise ImportError(
                "Anthropic package not installed. Run: pip install 'semantic-conflicts-benchmark[anthropic]'"
            )
        self._model = model
        self._max_tokens = max_tokens
        self._client = _anthropic.Anthropic(api_key=api_key)

    @property
    def name(self) -> str:
        return f"anthropic/{self._model}"

    def predict(self, prompt: str) -> AdapterResponse:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text if message.content else ""
        return _parse_response(raw)


def _parse_response(raw: str) -> AdapterResponse:
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
