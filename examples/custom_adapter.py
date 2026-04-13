"""Example: plug in any model by implementing ModelAdapter.

This file shows how to wrap a local Ollama server.
Copy, rename, and adapt for any other inference backend.

Usage:
    scbench --adapter-class examples.custom_adapter.OllamaAdapter \
            --model llama3 --domains philosophy software
"""

import json
import re
import urllib.request
from typing import Optional

from benchmark.adapters.base import AdapterResponse, ModelAdapter


class OllamaAdapter(ModelAdapter):
    """Adapter for a locally running Ollama server (http://localhost:11434)."""

    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return f"ollama/{self._model}"

    def predict(self, prompt: str) -> AdapterResponse:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user",   "content": prompt},
            ],
            "stream": False,
        }
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())

        raw = body["message"]["content"]
        return self._parse(raw)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse(self, raw: str) -> AdapterResponse:
        """Extract verdict from first keyword found on any line."""
        verdict = _extract_verdict(raw)
        explanation = raw.strip() if verdict != "consistent" else None
        return AdapterResponse(
            verdict=verdict,
            explanation=explanation,
            raw_response=raw,
        )


def _extract_verdict(text: str) -> str:
    upper = text.upper()
    for line in upper.splitlines():
        line = line.strip()
        if re.search(r"\bCONFLICT\b", line):
            return "conflict"
        if re.search(r"\bAMBIGUOUS\b", line):
            return "ambiguous"
        if re.search(r"\bCONSISTENT\b", line):
            return "consistent"
    # Fallback: scan full text
    if "CONFLICT" in upper:
        return "conflict"
    if "AMBIGUOUS" in upper:
        return "ambiguous"
    return "consistent"
