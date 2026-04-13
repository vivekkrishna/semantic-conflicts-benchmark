"""Task 1: Verdict Classification.

Ask the model to classify each item as CONFLICT, CONSISTENT, or AMBIGUOUS.
Scoring: accuracy, macro-F1, per-class F1, binary conflict F1.
"""

from typing import Any

from benchmark.tasks.base_task import BaseTask, format_passages


TASK_INSTRUCTION = (
    "Analyse the following passage(s) for semantic conflicts.\n\n"
    "Remember to:\n"
    "  1. Derive all implications that follow with 100% logical certainty from each passage.\n"
    "  2. Check for conflicts among those derived implications, not just the surface text.\n\n"
    "Respond with exactly one verdict on the first line:\n"
    "  CONFLICT   — the passages or their logical implications are incompatible.\n"
    "  CONSISTENT — the passages and all their implications are fully compatible.\n"
    "  AMBIGUOUS  — a conflict may or may not exist depending on unstated context.\n\n"
    "If your verdict is CONFLICT or AMBIGUOUS, explain which specific statements "
    "or derived implications conflict and why.\n\n"
)


class VerdictClassificationTask(BaseTask):
    """Binary 3-class verdict task."""

    @property
    def name(self) -> str:
        return "verdict_classification"

    def build_prompt(self, item: dict[str, Any]) -> str:
        passages_block = format_passages(item)
        question = item["input"].get("question", "")
        return f"{TASK_INSTRUCTION}{passages_block}\n\n{question}"
