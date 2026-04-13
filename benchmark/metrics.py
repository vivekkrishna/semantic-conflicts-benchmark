"""Metric computation for verdict classification and explanation scoring.

Primary score: Level-Weighted F1 (LW-F1)
    LW-F1 = Σ ((level + 1) × conflict_F1_at_level) / Σ (level + 1)
    Weight surface (L0) = 1, deep (L5) = 6.
    A model that only detects surface conflicts scores ~0.05; perfect = 1.0.
"""

from typing import Any, Optional

from sklearn.metrics import accuracy_score, f1_score


LABELS = ["conflict", "consistent", "ambiguous"]
CONFLICT_LEVELS = list(range(6))   # 0 … 5


# ---------------------------------------------------------------------------
# Core metric computation
# ---------------------------------------------------------------------------

def compute_metrics(
    labels: list[str],
    predictions: list[str],
    bert_scores: list[Optional[float]],
) -> dict[str, Any]:
    """Compute all benchmark metrics from flat lists.

    Args:
        labels:      Ground-truth verdict strings.
        predictions: Model-predicted verdict strings.
        bert_scores: BERTScore F1 per item; None for items without a reference
                     (consistent items) or where the model gave no explanation.

    Returns:
        Dict with accuracy, macro_f1, binary_conflict_f1, per_class_f1,
        explanation_bert_f1, n_items, n_explained.
    """
    accuracy = round(accuracy_score(labels, predictions), 4)

    macro_f1 = round(
        f1_score(labels, predictions, labels=LABELS, average="macro", zero_division=0), 4
    )

    per_class_f1 = {
        cls: round(
            f1_score(labels, predictions, labels=[cls], average="micro", zero_division=0), 4
        )
        for cls in LABELS
    }

    binary_labels = [("non-consistent" if l != "consistent" else "consistent") for l in labels]
    binary_preds  = [("non-consistent" if p != "consistent" else "consistent") for p in predictions]
    binary_f1 = round(
        f1_score(binary_labels, binary_preds,
                 pos_label="non-consistent", average="binary", zero_division=0), 4
    )

    scored = [s for s in bert_scores if s is not None and s > 0.0]
    bert_avg = round(sum(scored) / len(scored), 4) if scored else None

    return {
        "accuracy":            accuracy,
        "macro_f1":            macro_f1,
        "binary_conflict_f1":  binary_f1,
        "per_class_f1":        per_class_f1,
        "explanation_bert_f1": bert_avg,
        "n_items":             len(labels),
        "n_explained":         len(scored),
    }


def compute_metrics_for_subset(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Convenience wrapper — compute metrics from a list of result-item dicts."""
    labels      = [r["label"] for r in items]
    predictions = [r["prediction"] for r in items]
    bert        = [r.get("explanation_bert_f1") for r in items]
    return compute_metrics(labels, predictions, bert)


# ---------------------------------------------------------------------------
# Level-based metrics
# ---------------------------------------------------------------------------

def compute_level_metrics(results: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Compute metrics at each conflict level (0–5).

    Each level's evaluation set = level-L conflict items + ALL consistent/ambiguous items.
    Including non-conflict items in every level is essential so that precision is measured:
    a model that blindly predicts "conflict" is penalised for false positives on the
    consistent/ambiguous items, and conflict-class F1 correctly ranges 0→1.

    A purely correct model (no false positives, no false negatives) scores conflict F1 = 1.0
    at every level and therefore LW-F1 = 1.0.  A model that always predicts "conflict" scores
    conflict F1 = 18/(18+72) precision × 1.0 recall ≈ 0.333 at each level → LW-F1 = 0.333.
    """
    non_conflict = [r for r in results if r.get("conflict_level") is None]
    by_level: dict[int, dict[str, Any]] = {}
    for level in CONFLICT_LEVELS:
        level_conflict = [r for r in results if r.get("conflict_level") == level]
        if level_conflict:
            by_level[level] = compute_metrics_for_subset(level_conflict + non_conflict)
    return by_level


def level_weighted_f1(by_level: dict[int, dict[str, Any]]) -> float:
    """Primary benchmark score: higher difficulty levels get more weight.

    Weight for level N = N + 1 (surface L0 = 1, deep L5 = 6).
    Uses per-level conflict-class F1 (not macro-F1) so that the score ranges 0→1:
    a perfect model scores 1.0; a blind always-conflict predictor scores ~0.333.
    Returns 0.0 if no level data is available.
    """
    if not by_level:
        return 0.0
    total_weight = sum(l + 1 for l in by_level)
    weighted_sum = sum(
        (l + 1) * m.get("per_class_f1", {}).get("conflict", 0.0)
        for l, m in by_level.items()
    )
    return round(weighted_sum / total_weight, 4)
