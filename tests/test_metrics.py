"""Tests for benchmark/metrics.py — accuracy, macro-F1, LW-F1, ROUGE-L."""

import pytest

from benchmark.metrics import (
    compute_level_metrics,
    compute_metrics,
    compute_metrics_for_subset,
    level_weighted_f1,
)


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------

class TestComputeMetrics:
    def test_perfect_predictions(self):
        labels = ["conflict", "consistent", "ambiguous"]
        preds  = ["conflict", "consistent", "ambiguous"]
        rouge  = [0.8, 0.0, 0.6]
        m = compute_metrics(labels, preds, rouge)
        assert m["accuracy"]  == 1.0
        assert m["macro_f1"]  == 1.0
        assert m["n_items"]   == 3

    def test_all_wrong(self):
        labels = ["conflict", "conflict", "conflict"]
        preds  = ["consistent", "consistent", "consistent"]
        rouge  = [0.0, 0.0, 0.0]
        m = compute_metrics(labels, preds, rouge)
        assert m["accuracy"] == 0.0
        assert m["macro_f1"] == pytest.approx(0.0, abs=1e-3)

    def test_rouge_avg_excludes_zeros(self):
        labels = ["conflict", "conflict", "consistent"]
        preds  = ["conflict", "conflict", "consistent"]
        rouge  = [0.5, 0.9, 0.0]   # 0.0 = not scored (consistent)
        m = compute_metrics(labels, preds, rouge)
        # Average of [0.5, 0.9] = 0.7
        assert m["explanation_rouge_l"] == pytest.approx(0.7, abs=1e-3)
        assert m["n_explained"] == 2

    def test_rouge_all_zeros(self):
        labels = ["consistent"] * 3
        preds  = ["consistent"] * 3
        rouge  = [0.0, 0.0, 0.0]
        m = compute_metrics(labels, preds, rouge)
        assert m["explanation_rouge_l"] == 0.0

    def test_binary_conflict_f1(self):
        labels = ["conflict", "consistent", "ambiguous"]
        preds  = ["conflict", "consistent", "consistent"]
        rouge  = [0.0, 0.0, 0.0]
        m = compute_metrics(labels, preds, rouge)
        # non-consistent (conflict+ambiguous) vs consistent
        # label: non-c, c, non-c; pred: non-c, c, c
        # TP=1 (conflict), FP=0, FN=1 (ambiguous missed)
        assert m["binary_conflict_f1"] == pytest.approx(2/3, abs=1e-3)

    def test_per_class_f1_present(self):
        labels = ["conflict", "consistent", "ambiguous"]
        preds  = ["conflict", "consistent", "ambiguous"]
        rouge  = [0.0, 0.0, 0.0]
        m = compute_metrics(labels, preds, rouge)
        assert set(m["per_class_f1"].keys()) == {"conflict", "consistent", "ambiguous"}
        for v in m["per_class_f1"].values():
            assert v == pytest.approx(1.0, abs=1e-3)


# ---------------------------------------------------------------------------
# compute_level_metrics
# ---------------------------------------------------------------------------

class TestComputeLevelMetrics:
    def _make_result(self, label, pred, level, rouge=0.0):
        return {
            "label":               label,
            "prediction":          pred,
            "conflict_level":      level,
            "explanation_rouge_l": rouge,
        }

    def test_groups_by_level(self):
        # 2 conflict items (levels 0 and 1) + 1 non-conflict (None level)
        # Each level subset = level-L conflict items + all non-conflict items
        # L0 subset: 2 conflict-L0 items + 1 consistent = 3 items
        # L1 subset: 1 conflict-L1 item + 1 consistent = 2 items
        results = [
            self._make_result("conflict",   "conflict",   0),
            self._make_result("conflict",   "consistent", 0),
            self._make_result("conflict",   "conflict",   1),
            self._make_result("consistent", "consistent", None),
        ]
        by_level = compute_level_metrics(results)
        assert set(by_level.keys()) == {0, 1}
        assert by_level[0]["n_items"] == 3   # 2 L0 conflict + 1 consistent
        assert by_level[1]["n_items"] == 2   # 1 L1 conflict + 1 consistent

    def test_excludes_none_level(self):
        # No conflict items with a level → no levels computed
        results = [
            self._make_result("consistent", "consistent", None),
            self._make_result("ambiguous",  "ambiguous",  None),
        ]
        by_level = compute_level_metrics(results)
        assert by_level == {}

    def test_level_conflict_f1_penalises_false_positives(self):
        # 2 conflict items at level 2, 1 consistent item (None level)
        # Model predicts all as "conflict" → FP on consistent item
        results = [
            self._make_result("conflict",   "conflict", 2),
            self._make_result("conflict",   "conflict", 2),
            self._make_result("consistent", "conflict", None),  # false positive
        ]
        by_level = compute_level_metrics(results)
        m = by_level[2]
        # conflict: TP=2, FP=1, FN=0 → precision=2/3, recall=1.0, F1=0.8
        assert m["per_class_f1"]["conflict"] == pytest.approx(0.8, abs=1e-3)

    def test_non_conflict_items_appear_in_every_level(self):
        # 1 conflict each at L0 and L1, plus 1 consistent
        # Both level subsets should contain the consistent item
        results = [
            self._make_result("conflict",   "conflict",   0),
            self._make_result("conflict",   "conflict",   1),
            self._make_result("consistent", "consistent", None),
        ]
        by_level = compute_level_metrics(results)
        assert by_level[0]["n_items"] == 2  # 1 L0 + 1 consistent
        assert by_level[1]["n_items"] == 2  # 1 L1 + 1 consistent


# ---------------------------------------------------------------------------
# level_weighted_f1
# ---------------------------------------------------------------------------

def _level_entry(conflict_f1: float) -> dict:
    """Build a by_level entry dict with a per_class_f1.conflict value."""
    return {"per_class_f1": {"conflict": conflict_f1, "consistent": 0.0, "ambiguous": 0.0}}


class TestLevelWeightedF1:
    def test_empty_returns_zero(self):
        assert level_weighted_f1({}) == 0.0

    def test_single_level_equals_that_f1(self):
        by_level = {3: _level_entry(0.8)}
        # weight = 3+1 = 4; LW-F1 = (4 * 0.8) / 4 = 0.8
        assert level_weighted_f1(by_level) == pytest.approx(0.8, abs=1e-4)

    def test_weights_harder_levels_more(self):
        by_level = {
            0: _level_entry(1.0),  # weight 1
            5: _level_entry(0.0),  # weight 6
        }
        # numerator = 1*1.0 + 6*0.0 = 1.0; denominator = 1+6 = 7
        expected = round(1.0 / 7, 4)
        assert level_weighted_f1(by_level) == pytest.approx(expected, abs=1e-4)

    def test_all_perfect_is_one(self):
        by_level = {l: _level_entry(1.0) for l in range(6)}
        assert level_weighted_f1(by_level) == pytest.approx(1.0, abs=1e-4)

    def test_surface_only_correct(self):
        """A model that only handles L0 correctly scores 1/21 ≈ 0.0476."""
        by_level = {l: _level_entry(1.0 if l == 0 else 0.0) for l in range(6)}
        # weight 0→1,1→2,...,5→6; total=21; numerator=1*1.0=1.0
        expected = round(1.0 / 21, 4)
        assert level_weighted_f1(by_level) == pytest.approx(expected, abs=1e-4)

    def test_naive_always_conflict_baseline(self):
        """Always-predict-conflict model scores exactly 0.3333 when the level subsets
        contain 18 conflict + 72 non-conflict items (18/(18+72) precision × 1.0 recall)."""
        # conflict F1 for that distribution = 2*(18/90)*1.0 / ((18/90)+1.0) = 1/3
        naive_f1 = round(2 * (18/90) / (1 + 18/90), 4)
        by_level = {l: _level_entry(naive_f1) for l in range(6)}
        assert level_weighted_f1(by_level) == pytest.approx(naive_f1, abs=1e-4)


# ---------------------------------------------------------------------------
# compute_metrics_for_subset
# ---------------------------------------------------------------------------

class TestComputeMetricsForSubset:
    def test_wrapper_matches_direct_call(self):
        items = [
            {"label": "conflict",   "prediction": "conflict",   "explanation_rouge_l": 0.7},
            {"label": "consistent", "prediction": "consistent", "explanation_rouge_l": 0.0},
        ]
        result = compute_metrics_for_subset(items)
        direct = compute_metrics(
            ["conflict", "consistent"],
            ["conflict", "consistent"],
            [0.7, 0.0],
        )
        assert result["accuracy"]  == direct["accuracy"]
        assert result["macro_f1"]  == direct["macro_f1"]
