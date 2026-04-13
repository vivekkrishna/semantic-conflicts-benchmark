"""Task 2: Explanation scoring.

For items where label.verdict is "conflict" or "ambiguous", compare the
model's explanation against the reference explanation using ROUGE-L.
"""

from typing import Any, Optional

from rouge_score import rouge_scorer


_SCORER = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)


def score_explanation(prediction: Optional[str], reference: Optional[str]) -> float:
    """Return ROUGE-L F1 between prediction and reference strings.

    Returns 0.0 if either string is missing or empty.
    """
    if not prediction or not reference:
        return 0.0
    scores = _SCORER.score(reference, prediction)
    return round(scores["rougeL"].fmeasure, 4)


def should_score_explanation(item: dict[str, Any]) -> bool:
    """Return True for items that have a reference explanation to score against."""
    verdict = item.get("label", {}).get("verdict", "consistent")
    explanation = item.get("label", {}).get("explanation")
    return verdict in ("conflict", "ambiguous") and bool(explanation)
