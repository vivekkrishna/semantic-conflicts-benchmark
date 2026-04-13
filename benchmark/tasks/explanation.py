"""Task 2: Explanation scoring.

For items where label.verdict is "conflict" or "ambiguous", compare the
model's explanation against the reference reasoning_chain using ROUGE-L.
"""

import re
from typing import Any, Optional

from rouge_score import rouge_scorer


_SCORER = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

# Markdown patterns to strip before scoring so formatting symbols don't
# penalise the LCS computation.
_MD_PATTERNS = [
    (re.compile(r"\*{1,3}(.*?)\*{1,3}"), r"\1"),   # **bold**, *italic*, ***both***
    (re.compile(r"#{1,6}\s*"),            r""),      # ## headings
    (re.compile(r"^\s*[-*+]\s+", re.M),  r""),      # bullet list markers
    (re.compile(r"`{1,3}(.*?)`{1,3}"),   r"\1"),    # `code` / ```code```
    (re.compile(r"\[(.*?)\]\(.*?\)"),    r"\1"),    # [text](url)
]


def _strip_markdown(text: str) -> str:
    """Remove common markdown formatting from a string."""
    for pattern, replacement in _MD_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()


def score_explanation(prediction: Optional[str], reference: Optional[str]) -> float:
    """Return ROUGE-L F1 between prediction and reference strings.

    Markdown is stripped from the prediction before scoring so that formatting
    symbols (**, -, ##) do not artificially reduce the LCS overlap.
    Returns 0.0 if either string is missing or empty.
    """
    if not prediction or not reference:
        return 0.0
    clean_pred = _strip_markdown(prediction)
    if not clean_pred:
        return 0.0
    scores = _SCORER.score(reference, clean_pred)
    return round(scores["rougeL"].fmeasure, 4)


def should_score_explanation(item: dict[str, Any]) -> bool:
    """Return True for items that have a reference to score the explanation against.

    Scores any conflict or ambiguous item that has a reasoning_chain or an
    explanation field — i.e. all conflict and ambiguous items in the dataset.
    Previously this only triggered when label.explanation was non-null, which
    silently skipped the 52/132 items that have reasoning_chain but no
    separate explanation field.
    """
    verdict = item.get("label", {}).get("verdict", "consistent")
    if verdict not in ("conflict", "ambiguous"):
        return False
    label = item.get("label", {})
    return bool(label.get("reasoning_chain") or label.get("explanation"))
