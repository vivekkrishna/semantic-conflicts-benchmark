"""Tests for benchmark/reporter.py — R-4.4 (baseline row) and R-4.5 (failure taxonomy).

TDD: tests written before the implementation changes.
"""

import csv
import io
import json
from pathlib import Path

import pytest

from benchmark.evaluator import EvaluationResults
from benchmark.reporter import (
    BASELINE_ROW,
    LEADERBOARD_HEADER,
    write_leaderboard,
    write_json,
    write_markdown,
)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

def _make_results(**overrides) -> EvaluationResults:
    """Minimal EvaluationResults for reporter tests."""
    defaults = dict(
        model_name="test-model",
        run_id="20260101T000000Z",
        total_items=6,
        overall={
            "accuracy": 0.8,
            "macro_f1": 0.75,
            "binary_conflict_f1": 0.9,
            "per_class_f1": {"conflict": 0.85, "consistent": 0.80, "ambiguous": 0.60},
            "explanation_bert_f1": 0.82,
            "lw_f1": 0.72,
            "n_items": 6,
            "n_explained": 4,
        },
        by_domain={"philosophy": {"accuracy": 0.8, "macro_f1": 0.75,
                                   "binary_conflict_f1": 0.9,
                                   "per_class_f1": {"conflict": 0.85, "consistent": 0.80, "ambiguous": 0.60},
                                   "explanation_bert_f1": 0.82, "n_items": 6, "n_explained": 4}},
        by_level={0: {"accuracy": 0.9, "macro_f1": 0.85,
                       "binary_conflict_f1": 0.95,
                       "per_class_f1": {"conflict": 0.9, "consistent": 0.85, "ambiguous": 0.7},
                       "explanation_bert_f1": 0.83, "n_items": 6, "n_explained": 4}},
        by_conflict_type={},
        by_category={},
        by_difficulty={"easy": {"accuracy": 0.9, "macro_f1": 0.85,
                                 "binary_conflict_f1": 0.95,
                                 "per_class_f1": {"conflict": 0.9, "consistent": 0.85, "ambiguous": 0.7},
                                 "explanation_bert_f1": 0.83, "n_items": 4, "n_explained": 3},
                        "hard": {"accuracy": 0.6, "macro_f1": 0.55,
                                  "binary_conflict_f1": 0.75,
                                  "per_class_f1": {"conflict": 0.65, "consistent": 0.60, "ambiguous": 0.40},
                                  "explanation_bert_f1": 0.78, "n_items": 2, "n_explained": 1}},
        per_item=[
            {"id": "p1", "domain": "philosophy", "category": "cross_document",
             "difficulty": "easy", "conflict_level": 0, "conflict_type": "surface",
             "label": "conflict", "prediction": "conflict", "correct": True,
             "explanation_bert_f1": 0.85, "model_explanation": "Good reasoning.", "raw_response": "CONFLICT\nGood."},
            {"id": "p2", "domain": "philosophy", "category": "cross_document",
             "difficulty": "easy", "conflict_level": 1, "conflict_type": "implicit_L1",
             "label": "conflict", "prediction": "ambiguous", "correct": False,
             "explanation_bert_f1": 0.78, "model_explanation": "Uncertain.", "raw_response": "AMBIGUOUS\nUncertain."},
            {"id": "p3", "domain": "philosophy", "category": "cross_document",
             "difficulty": "easy", "conflict_level": None, "conflict_type": "none",
             "label": "consistent", "prediction": "conflict", "correct": False,
             "explanation_bert_f1": None, "model_explanation": None, "raw_response": "CONFLICT"},
            {"id": "p4", "domain": "philosophy", "category": "cross_document",
             "difficulty": "easy", "conflict_level": None, "conflict_type": "none",
             "label": "consistent", "prediction": "consistent", "correct": True,
             "explanation_bert_f1": None, "model_explanation": None, "raw_response": "CONSISTENT"},
            {"id": "p5", "domain": "philosophy", "category": "cross_document",
             "difficulty": "hard", "conflict_level": None, "conflict_type": "none",
             "label": "ambiguous", "prediction": "conflict", "correct": False,
             "explanation_bert_f1": 0.80, "model_explanation": "It conflicts.", "raw_response": "CONFLICT\nIt conflicts."},
            {"id": "p6", "domain": "philosophy", "category": "cross_document",
             "difficulty": "hard", "conflict_level": 2, "conflict_type": "implicit_L2",
             "label": "conflict", "prediction": "consistent", "correct": False,
             "explanation_bert_f1": 0.75, "model_explanation": "Consistent.", "raw_response": "CONSISTENT\nConsistent."},
        ],
        dataset_hash="abc123",
        n_runs=1,
    )
    defaults.update(overrides)
    return EvaluationResults(**defaults)


# ---------------------------------------------------------------------------
# R-4.4: Baseline row in leaderboard
# ---------------------------------------------------------------------------

class TestBaselineRow:
    def test_baseline_row_constant_exists(self):
        """BASELINE_ROW must be exported from reporter."""
        assert BASELINE_ROW is not None
        assert isinstance(BASELINE_ROW, dict)

    def test_baseline_row_has_all_header_fields(self):
        assert set(BASELINE_ROW.keys()) == set(LEADERBOARD_HEADER)

    def test_baseline_row_model_name(self):
        assert BASELINE_ROW["model"] == "baseline_always_conflict"

    def test_baseline_row_lw_f1_is_one_third(self):
        lw_f1 = float(BASELINE_ROW["lw_f1"])
        assert abs(lw_f1 - 0.333) < 0.005

    def test_baseline_row_accuracy_is_0_6(self):
        assert float(BASELINE_ROW["accuracy"]) == pytest.approx(0.6, abs=0.01)

    def test_baseline_row_macro_f1(self):
        # always-conflict: conflict_f1 = 2*(108/180)/(1+108/180) = 0.75
        # consistent_f1 = 0, ambiguous_f1 = 0 → macro = 0.75/3 = 0.25
        assert float(BASELINE_ROW["macro_f1"]) == pytest.approx(0.25, abs=0.005)

    def test_baseline_written_when_leaderboard_created(self, tmp_path):
        """Baseline row appears as the first row when a new leaderboard is created."""
        csv_path = str(tmp_path / "leaderboard.csv")
        results = _make_results()
        write_leaderboard(results, csv_path)

        rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
        assert rows[0]["model"] == "baseline_always_conflict"
        assert rows[1]["model"] == "test-model"

    def test_baseline_not_duplicated_on_second_write(self, tmp_path):
        """Appending a second run does not add a second baseline row."""
        csv_path = str(tmp_path / "leaderboard.csv")
        r1 = _make_results(model_name="model-a", run_id="20260101T000000Z")
        r2 = _make_results(model_name="model-b", run_id="20260101T010000Z")
        write_leaderboard(r1, csv_path)
        write_leaderboard(r2, csv_path)

        rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
        baseline_rows = [r for r in rows if r["model"] == "baseline_always_conflict"]
        assert len(baseline_rows) == 1

    def test_baseline_always_first_row(self, tmp_path):
        """Baseline row is always the first data row regardless of append order."""
        csv_path = str(tmp_path / "leaderboard.csv")
        write_leaderboard(_make_results(model_name="model-a"), csv_path)
        write_leaderboard(_make_results(model_name="model-b", run_id="20260101T010000Z"), csv_path)

        rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
        assert rows[0]["model"] == "baseline_always_conflict"


# ---------------------------------------------------------------------------
# R-4.5: Failure taxonomy
# ---------------------------------------------------------------------------

class TestFailureTaxonomy:
    def test_failure_breakdown_in_results_json(self, tmp_path):
        """results.json must contain a failure_breakdown key."""
        json_path = str(tmp_path / "results.json")
        write_json(_make_results(), json_path)
        data = json.loads(Path(json_path).read_text())
        assert "failure_breakdown" in data

    def test_failure_breakdown_has_all_six_types(self, tmp_path):
        expected_types = {
            "conflict_as_ambiguous",
            "conflict_as_consistent",
            "consistent_as_conflict",
            "consistent_as_ambiguous",
            "ambiguous_as_conflict",
            "ambiguous_as_consistent",
        }
        json_path = str(tmp_path / "results.json")
        write_json(_make_results(), json_path)
        data = json.loads(Path(json_path).read_text())
        breakdown = data["failure_breakdown"]
        assert set(breakdown.keys()) == expected_types

    def test_failure_counts_match_per_item(self, tmp_path):
        """Counts in failure_breakdown must match what's in per_item."""
        # per_item fixture has:
        #   p2: conflict → ambiguous  (conflict_as_ambiguous)
        #   p3: consistent → conflict (consistent_as_conflict)
        #   p5: ambiguous → conflict  (ambiguous_as_conflict)
        #   p6: conflict → consistent (conflict_as_consistent)
        json_path = str(tmp_path / "results.json")
        write_json(_make_results(), json_path)
        data = json.loads(Path(json_path).read_text())
        bd = data["failure_breakdown"]
        assert bd["conflict_as_ambiguous"]["count"] == 1
        assert bd["conflict_as_consistent"]["count"] == 1
        assert bd["consistent_as_conflict"]["count"] == 1
        assert bd["ambiguous_as_conflict"]["count"] == 1
        assert bd["consistent_as_ambiguous"]["count"] == 0
        assert bd["ambiguous_as_consistent"]["count"] == 0

    def test_failure_breakdown_includes_percentage(self, tmp_path):
        """Each breakdown type has a 'pct' field (percentage of total items)."""
        json_path = str(tmp_path / "results.json")
        write_json(_make_results(), json_path)
        data = json.loads(Path(json_path).read_text())
        for ftype, entry in data["failure_breakdown"].items():
            assert "pct" in entry, f"Missing 'pct' in breakdown type '{ftype}'"
            assert 0.0 <= entry["pct"] <= 100.0

    def test_failure_breakdown_in_markdown(self, tmp_path):
        """Markdown report must contain a Failure Breakdown section."""
        md_path = str(tmp_path / "report.md")
        write_markdown(_make_results(), md_path)
        content = Path(md_path).read_text()
        assert "Failure Breakdown" in content

    def test_markdown_lists_nonzero_failure_types(self, tmp_path):
        """Markdown failure section must name each failure type that has count > 0."""
        md_path = str(tmp_path / "report.md")
        write_markdown(_make_results(), md_path)
        content = Path(md_path).read_text()
        # Our fixture has these four non-zero types
        for ftype in ["conflict_as_ambiguous", "conflict_as_consistent",
                       "consistent_as_conflict", "ambiguous_as_conflict"]:
            assert ftype in content, f"Expected '{ftype}' in markdown failure section"

    def test_zero_count_types_not_in_markdown_body(self, tmp_path):
        """Failure types with count=0 are omitted from the markdown body (not the table)."""
        md_path = str(tmp_path / "report.md")
        write_markdown(_make_results(), md_path)
        content = Path(md_path).read_text()
        # consistent_as_ambiguous and ambiguous_as_consistent both have count=0
        # They should not appear as bullet points/rows with count data
        for zero_type in ["consistent_as_ambiguous", "ambiguous_as_consistent"]:
            # The type name might appear in a table header but not with a count line
            # We check it doesn't appear with "count: 0" or ": 0 (" patterns
            assert f"{zero_type}: 0" not in content and f"{zero_type} — 0" not in content

    def test_perfect_model_has_all_zeros(self, tmp_path):
        """A model with all correct predictions has a failure_breakdown with all zeros."""
        perfect_items = [
            {"id": f"p{i}", "domain": "philosophy", "category": "cross_document",
             "difficulty": "easy", "conflict_level": 0, "conflict_type": "surface",
             "label": "conflict", "prediction": "conflict", "correct": True,
             "explanation_bert_f1": 0.85, "model_explanation": "Good.", "raw_response": "CONFLICT\nGood."}
            for i in range(3)
        ]
        results = _make_results(per_item=perfect_items, total_items=3)
        json_path = str(tmp_path / "results.json")
        write_json(results, json_path)
        data = json.loads(Path(json_path).read_text())
        for ftype, entry in data["failure_breakdown"].items():
            assert entry["count"] == 0, f"Expected 0 for '{ftype}', got {entry['count']}"
