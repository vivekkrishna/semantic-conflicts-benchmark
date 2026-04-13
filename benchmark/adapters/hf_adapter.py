"""HuggingFace adapter — any text-generation pipeline model.

Usage:
    pip install 'semantic-conflicts-benchmark[hf]'
    python -m benchmark.run --adapter hf --model mistralai/Mistral-7B-Instruct-v0.2
"""

import re
from typing import Optional

from benchmark.adapters.base import ModelAdapter, AdapterResponse


class HuggingFaceAdapter(ModelAdapter):
    """Adapter for HuggingFace text-generation pipeline models."""

    def __init__(self, model: str = "mistralai/Mistral-7B-Instruct-v0.2",
                 max_new_tokens: int = 512, device: Optional[str] = None) -> None:
        try:
            from transformers import pipeline
        except ImportError:
            raise ImportError(
                "Transformers not installed. Run: pip install 'semantic-conflicts-benchmark[hf]'"
            )
        self._model_name = model
        kwargs: dict = {"max_new_tokens": max_new_tokens, "do_sample": False}
        if device:
            kwargs["device"] = device
        self._pipe = pipeline("text-generation", model=model, **kwargs)

    @property
    def name(self) -> str:
        return f"hf/{self._model_name}"

    def predict(self, prompt: str) -> AdapterResponse:
        full_prompt = f"{self.system_prompt}\n\n{prompt}"
        outputs = self._pipe(full_prompt)
        raw: str = outputs[0]["generated_text"]
        # Strip the input prompt from the output (some pipelines echo it back)
        if raw.startswith(full_prompt):
            raw = raw[len(full_prompt):].strip()
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
