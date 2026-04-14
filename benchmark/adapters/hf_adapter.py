"""HuggingFace adapter — any text-generation pipeline model.

Usage:
    pip install 'semantic-conflicts-benchmark[hf]'
    python -m benchmark.run --adapter hf --model mistralai/Mistral-7B-Instruct-v0.2
"""

from typing import Optional

from benchmark.adapters.base import ModelAdapter, AdapterResponse, parse_verdict_response


class HuggingFaceAdapter(ModelAdapter):
    """Adapter for HuggingFace text-generation pipeline models."""

    def __init__(self, model: str = "mistralai/Mistral-7B-Instruct-v0.2",
                 max_new_tokens: int = 512, temperature: float = 0.0,
                 device: Optional[str] = None) -> None:
        try:
            from transformers import pipeline
        except ImportError:
            raise ImportError(
                "Transformers not installed. Run: pip install 'semantic-conflicts-benchmark[hf]'"
            )
        self._model_name = model
        # temperature=0.0 → greedy decoding (do_sample=False); >0 → sampling
        do_sample = temperature > 0.0
        kwargs: dict = {"max_new_tokens": max_new_tokens, "do_sample": do_sample}
        if do_sample:
            kwargs["temperature"] = temperature
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
        return parse_verdict_response(raw)
