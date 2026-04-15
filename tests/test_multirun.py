"""Tests for R-3.2: temperature logging and multi-run evaluation stats.

TDD: tests written before the implementation changes.

Covers:
  - temperature stored in EvaluationResults and results JSON
  - per_run_lw_f1 list stored in EvaluationResults and results JSON
  - lw_f1_std computed and stored when n_runs > 1
  - leaderboard CSV gets temperature and lw_f1_std columns
  - stability flag when std > 0.01
"""

import csv
import json
import statistics
from pathlib import Path

import pytest

from benchmark.evaluator import EvaluationResults
from benchmark.reporter import (
    LEADERBOARD_HEADER,
    write_json,
    write_leaderboard,
)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

def _make_results(**overrides) -> EvaluationResults:
    defaults = dict(
        model_name="test-model",
        run_id="20260101T000000Z",
        total_items=6,
        temperature=0.0,
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
        by_domain={},
        by_level={},
        by_conflict_type={},
        by_category={},
        by_difficulty={},
        per_item=[],
        dataset_hash="abc123",
        n_runs=1,
        per_run_lw_f1=[],
    )
    defaults.update(overrides)
    return EvaluationResults(**defaults)


def _make_multirun_results(**overrides) -> EvaluationResults:
    """Results with 3 runs and per-run LW-F1 values."""
    per_run = [0.72, 0.73, 0.71]
    return _make_results(
        n_runs=3,
        temperature=0.0,
        per_run_lw_f1=per_run,
        **overrides,
    )


# ---------------------------------------------------------------------------
# R-3.2a: temperature stored in EvaluationResults
# ---------------------------------------------------------------------------

class TestTemperatureField:
    def test_evaluation_results_has_temperature_field(self):
        """EvaluationResults must accept and store a temperature field."""
        r = _make_results(temperature=0.0)
        assert r.temperature == 0.0

    def test_temperature_nonzero(self):
        r = _make_results(temperature=0.7)
        assert r.temperature == 0.7

    def test_temperature_in_results_json(self, tmp_path):
        """results.json must contain a 'temperature' key."""
        r = _make_results(temperature=0.5)
        path = str(tmp_path / "results.json")
        write_json(r, path)
        data = json.loads(Path(path).read_text())
        assert "temperature" in data
        assert data["temperature"] == 0.5

    def test_temperature_default_zero_in_json(self, tmp_path):
        r = _make_results(temperature=0.0)
        path = str(tmp_path / "results.json")
        write_json(r, path)
        data = json.loads(Path(path).read_text())
        assert data["temperature"] == 0.0


# ---------------------------------------------------------------------------
# R-3.2b: per-run LW-F1 stored in EvaluationResults
# ---------------------------------------------------------------------------

class TestPerRunLwF1:
    def test_evaluation_results_has_per_run_lw_f1_field(self):
        """EvaluationResults must accept a per_run_lw_f1 list."""
        r = _make_results(per_run_lw_f1=[0.72, 0.73, 0.71])
        assert r.per_run_lw_f1 == [0.72, 0.73, 0.71]

    def test_per_run_lw_f1_empty_for_single_run(self):
        r = _make_results(n_runs=1, per_run_lw_f1=[])
        assert r.per_run_lw_f1 == []

    def test_per_run_lw_f1_in_results_json(self, tmp_path):
        """results.json must contain per_run_lw_f1 when n_runs > 1."""
        r = _make_multirun_results()
        path = str(tmp_path / "results.json")
        write_json(r, path)
        data = json.loads(Path(path).read_text())
        assert "per_run_lw_f1" in data
        assert data["per_run_lw_f1"] == [0.72, 0.73, 0.71]

    def test_per_run_lw_f1_absent_or_empty_for_single_run(self, tmp_path):
        """results.json should omit or have empty per_run_lw_f1 for single runs."""
        r = _make_results(n_runs=1, per_run_lw_f1=[])
        path = str(tmp_path / "results.json")
        write_json(r, path)
        data = json.loads(Path(path).read_text())
        # Either absent or empty list — both acceptable
        assert data.get("per_run_lw_f1", []) == []


# ---------------------------------------------------------------------------
# R-3.2c: lw_f1_std computed and exposed
# ---------------------------------------------------------------------------

class TestLwF1Std:
    def test_lw_f1_std_in_results_json_for_multirun(self, tmp_path):
        """results.json must contain lw_f1_std when n_runs > 1."""
        r = _make_multirun_results()
        path = str(tmp_path / "results.json")
        write_json(r, path)
        data = json.loads(Path(path).read_text())
        assert "lw_f1_std" in data
        expected_std = statistics.stdev([0.72, 0.73, 0.71])
        assert abs(data["lw_f1_std"] - expected_std) < 1e-6

    def test_lw_f1_std_absent_or_none_for_single_run(self, tmp_path):
        """results.json should not include lw_f1_std for single-run evaluations."""
        r = _make_results(n_runs=1, per_run_lw_f1=[])
        path = str(tmp_path / "results.json")
        write_json(r, path)
        data = json.loads(Path(path).read_text())
        # Either absent or None/null
        assert data.get("lw_f1_std") is None

    def test_lw_f1_std_in_overall_for_multirun(self, tmp_path):
        """overall dict in results.json should also carry lw_f1_std."""
        r = _make_multirun_results()
        path = str(tmp_path / "results.json")
        write_json(r, path)
        data = json.loads(Path(path).read_text())
        assert "lw_f1_std" in data["overall"]


# ---------------------------------------------------------------------------
# R-3.2d: leaderboard CSV gets temperature and lw_f1_std columns
# ---------------------------------------------------------------------------

class TestLeaderboardColumns:
    def test_leaderboard_header_has_temperature(self):
        assert "temperature" in LEADERBOARD_HEADER

    def test_leaderboard_header_has_lw_f1_std(self):
        assert "lw_f1_std" in LEADERBOARD_HEADER

    def test_leaderboard_row_writes_temperature(self, tmp_path):
        r = _make_results(temperature=0.0)
        path = str(tmp_path / "lb.csv")
        write_leaderboard(r, path)
        rows = list(csv.DictReader(open(path)))
        model_row = next(row for row in rows if row["model"] == "test-model")
        assert float(model_row["temperature"]) == 0.0

    def test_leaderboard_row_writes_lw_f1_std_empty_for_single_run(self, tmp_path):
        r = _make_results(n_runs=1, per_run_lw_f1=[])
        path = str(tmp_path / "lb.csv")
        write_leaderboard(r, path)
        rows = list(csv.DictReader(open(path)))
        model_row = next(row for row in rows if row["model"] == "test-model")
        assert model_row["lw_f1_std"] == ""

    def test_leaderboard_row_writes_lw_f1_std_for_multirun(self, tmp_path):
        r = _make_multirun_results()
        path = str(tmp_path / "lb.csv")
        write_leaderboard(r, path)
        rows = list(csv.DictReader(open(path)))
        model_row = next(row for row in rows if row["model"] == "test-model")
        expected = statistics.stdev([0.72, 0.73, 0.71])
        assert abs(float(model_row["lw_f1_std"]) - expected) < 1e-6


# ---------------------------------------------------------------------------
# R-3.2e: stability flag when std > 0.01
# ---------------------------------------------------------------------------

class TestStabilityFlag:
    def test_unstable_flag_in_results_json_when_std_exceeds_threshold(self, tmp_path):
        """When lw_f1_std > 0.01, results.json should include unstable=True."""
        # std([0.70, 0.80, 0.75]) ≈ 0.05 — clearly above threshold
        r = _make_results(
            n_runs=3,
            per_run_lw_f1=[0.70, 0.80, 0.75],
            overall={
                "accuracy": 0.8, "macro_f1": 0.75, "binary_conflict_f1": 0.9,
                "per_class_f1": {"conflict": 0.85, "consistent": 0.80, "ambiguous": 0.60},
                "explanation_bert_f1": 0.82, "lw_f1": 0.75, "n_items": 6, "n_explained": 4,
            },
        )
        path = str(tmp_path / "results.json")
        write_json(r, path)
        data = json.loads(Path(path).read_text())
        assert data.get("unstable") is True

    def test_no_unstable_flag_when_std_within_threshold(self, tmp_path):
        """When lw_f1_std <= 0.01, unstable should be False or absent."""
        # std([0.72, 0.72, 0.73]) ≈ 0.006 — within threshold
        r = _make_results(
            n_runs=3,
            per_run_lw_f1=[0.72, 0.72, 0.73],
        )
        path = str(tmp_path / "results.json")
        write_json(r, path)
        data = json.loads(Path(path).read_text())
        assert not data.get("unstable", False)

    def test_no_unstable_flag_for_single_run(self, tmp_path):
        r = _make_results(n_runs=1, per_run_lw_f1=[])
        path = str(tmp_path / "results.json")
        write_json(r, path)
        data = json.loads(Path(path).read_text())
        assert not data.get("unstable", False)
