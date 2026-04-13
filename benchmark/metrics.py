"""Metric computation for verdict classification and explanation scoring.

Primary score: Level-Weighted F1 (LW-F1)
    LW-F1 = Σ ((level + 1) × macro_F1_at_level) / Σ (level + 1)
    Weight surface (L0) = 1, deep (L5) = 6.
    A model that only detects surface conflicts scores ~0.14; perfect = 1.0.
"""

from typing import Any

from sklearn.metrics import accuracy_score, f1_score


LABELS = ["conflict", "consistent", "ambiguous"]
CONFLICT_LEVELS = list(range(6))   # 0 … 5


# ---------------------------------------------------------------------------
# Core metric computation
# ---------------------------------------------------------------------------

def compute_metrics(
    labels: list[str],
    predictions: list[str],
    rouge_scores: list[float],
) -> dict[str, Any]:
    """Compute all benchmark metrics from flat lists.

    Args:
        labels:       Ground-truth verdict strings.
        predictions:  Model-predicted verdict strings.
        rouge_scores: ROUGE-L scores per item; 0.0 for items without reference.

    Returns:
        Dict with accuracy, macro_f1, binary_conflict_f1, per_class_f1, explanation_rouge_l.
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

    scored = [s for s in rouge_scores if s > 0.0]
    rouge_avg = round(sum(scored) / len(scored), 4) if scored else 0.0

    return {
        "accuracy":            accuracy,
        "macro_f1":            macro_f1,
        "binary_conflict_f1":  binary_f1,
        "per_class_f1":        per_class_f1,
        "explanation_rouge_l": rouge_avg,
        "n_items":             len(labels),
        "n_explained":         len(scored),
    }


def compute_metrics_for_subset(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Convenience wrapper — compute metrics from a list of result-item dicts."""
    labels      = [r["label"] for r in items]
    predictions = [r["prediction"] for r in items]
    rouge       = [r.get("explanation_rouge_l", 0.0) for r in items]
    return compute_metrics(labels, predictions, rouge)


# ---------------------------------------------------------------------------
# Level-based metrics
# ---------------------------------------------------------------------------

def compute_level_metrics(results: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Compute metrics at each conflict level (0–5).

    Only items with a non-null `conflict_level` are included.
    Items that are consistent/ambiguous (conflict_level == None) are excluded
    so we isolate the model's ability to detect conflicts at each depth.
    """
    by_level: dict[int, dict[str, Any]] = {}
    for level in CONFLICT_LEVELS:
        level_items = [r for r in results if r.get("conflict_level") == level]
        if level_items:
            by_level[level] = compute_metrics_for_subset(level_items)
    return by_level


def level_weighted_f1(by_level: dict[int, dict[str, Any]]) -> float:
    """Primary benchmark score: higher difficulty levels get more weight.

    Weight for level N = N + 1 (surface L0 = 1, deep L5 = 6).
    Returns 0.0 if no level data is available.
    """
    if not by_level:
        return 0.0
    total_weight = sum(l + 1 for l in by_level)
    weighted_sum = sum((l + 1) * m["macro_f1"] for l, m in by_level.items())
    return round(weighted_sum / total_weight, 4)
