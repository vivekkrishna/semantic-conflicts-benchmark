"""Task 2: Explanation scoring.

For items where label.verdict is "conflict" or "ambiguous", compare the
model's explanation against the reference reasoning_chain using BERTScore F1.

BERTScore uses contextual token embeddings to measure semantic similarity,
capturing paraphrasing and synonymy that surface-overlap metrics miss.

Install: pip install bert-score  (included in the default dependencies)
"""

import re
from typing import Any, Optional

from bert_score import score as _bert_score_fn


# DistilBERT is ~260 MB, runs well on CPU, and captures semantic similarity
# sufficiently for reasoning-chain comparison.
_BERT_MODEL = "distilbert-base-uncased"

_MD_PATTERNS = [
    (re.compile(r"\*{1,3}(.*?)\*{1,3}"), r"\1"),   # **bold**, *italic*, ***both***
    (re.compile(r"#{1,6}\s*"),            r""),      # ## headings
    (re.compile(r"^\s*[-*+]\s+", re.M),  r""),      # bullet list markers
    (re.compile(r"`{1,3}(.*?)`{1,3}"),   r"\1"),    # `code` / ```code```
    (re.compile(r"\[(.*?)\]\(.*?\)"),    r"\1"),    # [text](url)
]


def _strip_markdown(text: str) -> str:
    """Remove common markdown formatting so it doesn't penalise BERTScore."""
    for pattern, replacement in _MD_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()


def score_explanation(prediction: Optional[str], reference: Optional[str]) -> Optional[float]:
    """BERTScore F1 between the model's explanation and the ground-truth reasoning chain.

    Uses distilbert-base-uncased. Markdown is stripped from the prediction
    before scoring. Returns None if either string is missing or empty
    (so callers can distinguish "not scored" from a genuine 0.0 score).
    """
    if not prediction or not reference:
        return None
    clean = _strip_markdown(prediction)
    if not clean:
        return None
    _, _, F1 = _bert_score_fn(
        [clean], [reference],
        model_type=_BERT_MODEL,
        verbose=False,
        device=None,   # auto: GPU if available, else CPU
    )
    return round(F1[0].item(), 4)


def should_score_explanation(item: dict[str, Any]) -> bool:
    """Return True for conflict/ambiguous items that have a reference to score against.

    Triggers on any item with a reasoning_chain or explanation field —
    i.e. all conflict and ambiguous items in the dataset.
    """
    verdict = item.get("label", {}).get("verdict", "consistent")
    if verdict not in ("conflict", "ambiguous"):
        return False
    label = item.get("label", {})
    return bool(label.get("reasoning_chain") or label.get("explanation"))
