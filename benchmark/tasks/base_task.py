"""Base task class and shared prompt-building utilities."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTask(ABC):
    """Abstract base for all benchmark tasks."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier used in results, e.g. 'verdict_classification'."""
        ...

    @abstractmethod
    def build_prompt(self, item: dict[str, Any]) -> str:
        """Construct the user-facing prompt string for a dataset item."""
        ...


def format_passages(item: dict[str, Any]) -> str:
    """Render passage(s) from a dataset item into a readable block."""
    passages = item["input"]["passages"]
    lines: list[str] = []
    for p in passages:
        label = f"[Passage {p['id']}]"
        source = p.get("source")
        if source:
            label += f"  (source: {source})"
        lines.append(label)
        lines.append(p["text"])
        lines.append("")
    return "\n".join(lines).strip()
