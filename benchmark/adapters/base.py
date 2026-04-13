"""Base interface for all model adapters.

To plug your model into the benchmark, implement ModelAdapter:

    from benchmark.adapters.base import ModelAdapter, AdapterResponse

    class MyAdapter(ModelAdapter):
        @property
        def name(self) -> str:
            return "my-model-v1"

        def predict(self, prompt: str) -> AdapterResponse:
            raw = call_my_model(prompt)
            verdict = parse_verdict(raw)
            return AdapterResponse(verdict=verdict, explanation=raw, raw_response=raw)

Then run:
    python -m benchmark.run --adapter-class my_module.MyAdapter
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


VALID_VERDICTS = {"conflict", "consistent", "ambiguous"}


@dataclass
class AdapterResponse:
    """Structured response returned by every model adapter.

    Attributes:
        verdict:      One of "conflict", "consistent", or "ambiguous".
        explanation:  Required when verdict is "conflict" or "ambiguous".
                      Should explain which statements or derived implications conflict.
        raw_response: Full, unprocessed text from the model — stored for debugging.
    """

    verdict: str
    explanation: Optional[str] = None
    raw_response: str = ""

    def __post_init__(self) -> None:
        if self.verdict not in VALID_VERDICTS:
            raise ValueError(
                f"verdict must be one of {VALID_VERDICTS!r}, got {self.verdict!r}"
            )


class ModelAdapter(ABC):
    """Abstract base class for all model adapters.

    Subclass this and implement `name` and `predict` to run your model
    against the benchmark.  Optionally override `system_prompt`.

    See examples/custom_adapter.py for a complete working example.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique model identifier used in results and the leaderboard.

        Examples: "gpt-4o-2024-11-20", "claude-opus-4-6", "ollama/llama3"
        """
        ...

    @abstractmethod
    def predict(self, prompt: str) -> AdapterResponse:
        """Call the model and return a structured verdict + explanation.

        Args:
            prompt: A fully-formatted prompt string containing the task
                    instructions and the passage(s) to evaluate.

        Returns:
            AdapterResponse with verdict and optional explanation.
        """
        ...

    @property
    def system_prompt(self) -> str:
        """System-level instructions prepended before the user prompt.

        This prompt instructs the model to reason over *derived* implications,
        not just the surface text — capturing implicit multi-hop conflicts.

        Override this to customise framing or output format for your model.
        """
        return (
            "You are an expert at detecting semantic conflicts in text.\n\n"
            "For each task, follow this reasoning process:\n\n"
            "Step 1 — Derive implications: For each passage, enumerate every "
            "statement that follows with 100% logical certainty from that passage — "
            "not just what is explicitly stated, but every fact or position that "
            "MUST be true if the passage is true.\n\n"
            "Step 2 — Check for conflicts: Look for contradictions both between "
            "the literal statements AND between their derived implications. "
            "A conflict exists even if the original passages seem compatible at "
            "surface level, as long as their logical consequences cannot "
            "simultaneously be true.\n\n"
            "Step 3 — Classify as exactly one of:\n"
            "  CONFLICT   — the passages or their derived implications assert "
            "incompatible facts/positions that cannot both be true.\n"
            "  CONSISTENT — the passages and all logical implications are fully "
            "compatible with each other.\n"
            "  AMBIGUOUS  — a conflict may or may not exist depending on unstated "
            "context, scope, or definitions that are not resolvable from the text alone.\n\n"
            "Begin your response with the verdict word on its own line. "
            "If the verdict is CONFLICT or AMBIGUOUS, explain which specific "
            "statements or derived implications conflict and why."
        )
