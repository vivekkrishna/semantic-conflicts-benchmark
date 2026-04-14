"""End-to-end benchmark tests — calls the real Anthropic API.

Run with:
    pytest tests/test_e2e.py -v -m e2e

Skipped automatically if ANTHROPIC_API_KEY is not set in the environment.

These tests verify that the full pipeline (data loading → real model call →
scoring → runlog) works correctly against a 6-item multi-hop fixture (L0–L5).
They also verify reproducibility: two runs at temperature=0 over the same
dataset must produce identical predictions, metrics, and dataset hash.

Fixture schema sanity tests (no API required) are in TestFixtureSchema and
run as part of the normal test suite regardless of API key availability.
"""

import json
import os
import re
from pathlib import Path

import pytest

from benchmark.evaluator import Evaluator, _hash_dataset
from benchmark.reporter import write_runlog


# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
E2E_FIXTURE  = FIXTURES_DIR / "e2e_multihop.json"
EXPECTED_LEVELS = {0, 1, 2, 3, 4, 5}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_fixture() -> list[dict]:
    if not E2E_FIXTURE.exists():
        pytest.fail(f"e2e fixture not found: {E2E_FIXTURE}")
    with E2E_FIXTURE.open(encoding="utf-8") as f:
        return json.load(f)


def _build_data_dir(tmp_path: Path, items: list[dict]) -> Path:
    by_domain: dict[str, list] = {}
    for item in items:
        by_domain.setdefault(item["domain"], []).append(item)
    for domain, domain_items in by_domain.items():
        d = tmp_path / domain
        d.mkdir(parents=True, exist_ok=True)
        with (d / "v1.json").open("w", encoding="utf-8") as fh:
            json.dump(domain_items, fh)
    return tmp_path


def _make_evaluator(adapter, data_dir: Path, n_runs: int = 1) -> Evaluator:
    domains = [p.name for p in data_dir.iterdir() if p.is_dir()]
    return Evaluator(adapter=adapter, domains=domains,
                     data_dir=str(data_dir), n_runs=n_runs)


# ---------------------------------------------------------------------------
# pytest markers and fixtures
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "e2e: end-to-end tests that call the real Anthropic API (requires ANTHROPIC_API_KEY)",
    )


@pytest.fixture(scope="module")
def fixture_items() -> list[dict]:
    return _load_fixture()


@pytest.fixture(scope="module")
def anthropic_adapter():
    """Returns a real AnthropicAdapter. Fails loudly if ANTHROPIC_API_KEY is not set."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.fail(
            "ANTHROPIC_API_KEY is not set. E2E tests require a real API key.\n"
            "Set it in your environment or in a .env file before running:\n"
            "  pytest tests/test_e2e.py -v -m e2e"
        )
    from benchmark.adapters.anthropic_adapter import AnthropicAdapter
    return AnthropicAdapter(model="claude-haiku-4-5-20251001", temperature=0.0)


@pytest.fixture(scope="module")
def e2e_results(anthropic_adapter, fixture_items, tmp_path_factory):
    """Runs the full pipeline once and caches the result for the module."""
    data_dir = _build_data_dir(tmp_path_factory.mktemp("e2e_data"), fixture_items)
    ev = _make_evaluator(anthropic_adapter, data_dir)
    return ev.run()


# ---------------------------------------------------------------------------
# 1. Pipeline smoke — full run completes without error
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestPipelineSmoke:
    def test_run_completes_and_returns_results(self, e2e_results):
        from benchmark.evaluator import EvaluationResults
        assert isinstance(e2e_results, EvaluationResults)

    def test_results_use_real_anthropic_model_not_a_mock(self, e2e_results):
        """Confirms the run was against a real Anthropic model, not a mock adapter."""
        assert e2e_results.model_name.startswith("anthropic/"), (
            f"Expected model name to start with 'anthropic/', got {e2e_results.model_name!r}"
        )
        assert "haiku" in e2e_results.model_name or "claude" in e2e_results.model_name, (
            f"Unexpected model name: {e2e_results.model_name!r}"
        )

    def test_total_items_matches_fixture(self, e2e_results, fixture_items):
        assert e2e_results.total_items == len(fixture_items)

    def test_per_item_has_all_required_fields(self, e2e_results):
        for item in e2e_results.per_item:
            for field in ("id", "domain", "label", "prediction", "correct",
                          "conflict_level", "model_explanation", "raw_response"):
                assert field in item, f"{item.get('id')} missing field {field!r}"

    def test_predictions_are_valid_verdicts(self, e2e_results):
        valid = {"conflict", "consistent", "ambiguous"}
        for item in e2e_results.per_item:
            assert item["prediction"] in valid, (
                f"{item['id']}: invalid prediction {item['prediction']!r}"
            )


# ---------------------------------------------------------------------------
# 2. Metric structure
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestMetricStructure:
    def test_all_conflict_levels_present_in_by_level(self, e2e_results):
        assert set(e2e_results.by_level.keys()) == EXPECTED_LEVELS

    def test_overall_contains_required_keys(self, e2e_results):
        for key in ("accuracy", "macro_f1", "lw_f1", "binary_conflict_f1",
                    "per_class_f1", "n_items"):
            assert key in e2e_results.overall, f"overall missing key {key!r}"

    def test_lw_f1_in_valid_range(self, e2e_results):
        assert 0.0 <= e2e_results.overall["lw_f1"] <= 1.0

    def test_accuracy_in_valid_range(self, e2e_results):
        assert 0.0 <= e2e_results.overall["accuracy"] <= 1.0

    def test_by_level_each_has_required_keys(self, e2e_results):
        for level, m in e2e_results.by_level.items():
            for key in ("accuracy", "macro_f1", "per_class_f1", "n_items"):
                assert key in m, f"by_level[{level}] missing key {key!r}"

    def test_dataset_hash_is_16_hex_chars(self, e2e_results):
        assert re.fullmatch(r"[0-9a-f]{16}", e2e_results.dataset_hash), (
            f"dataset_hash {e2e_results.dataset_hash!r} is not 16 hex chars"
        )


# ---------------------------------------------------------------------------
# 3. Reproducibility — three identical runs must produce identical outputs
#    Verified at overall level AND per conflict level (L0–L5)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def three_runs(anthropic_adapter, fixture_items, tmp_path_factory):
    """Runs the evaluator three times on the 8-item fixture.
    Module-scoped so all reproducibility tests share the same 3 runs
    (24 API calls total, not 24 × number-of-tests).
    """
    data_dir = _build_data_dir(tmp_path_factory.mktemp("repro"), fixture_items)
    ev = _make_evaluator(anthropic_adapter, data_dir)
    return [ev.run() for _ in range(3)]


@pytest.mark.e2e
class TestReproducibility:

    def test_three_runs_produce_identical_per_item_predictions(self, three_runs):
        """At temperature=0, every item must receive the same verdict in all 3 runs."""
        r1, r2, r3 = three_runs
        for run_a, run_b, label in ((r1, r2, "run1 vs run2"), (r1, r3, "run1 vs run3")):
            preds_a = {item["id"]: item["prediction"] for item in run_a.per_item}
            preds_b = {item["id"]: item["prediction"] for item in run_b.per_item}
            differing = {k for k in preds_a if preds_a[k] != preds_b[k]}
            assert not differing, (
                f"Non-deterministic predictions ({label}) at temperature=0: {differing}"
            )

    def test_three_runs_produce_identical_overall_metrics(self, three_runs):
        """Overall accuracy, macro_f1, and lw_f1 must be identical across all 3 runs."""
        r1, r2, r3 = three_runs
        for metric in ("accuracy", "macro_f1", "lw_f1"):
            values = [r.overall[metric] for r in (r1, r2, r3)]
            assert values[0] == values[1] == values[2], (
                f"Overall {metric} not stable across 3 runs: {values}"
            )

    def test_three_runs_produce_identical_per_level_metrics(self, three_runs):
        """For each conflict level (L0–L5), accuracy and conflict-F1 must be
        identical across all 3 runs."""
        r1, r2, r3 = three_runs
        for level in EXPECTED_LEVELS:
            for metric in ("accuracy",):
                values = [
                    r.by_level.get(level, {}).get(metric)
                    for r in (r1, r2, r3)
                ]
                assert values[0] == values[1] == values[2], (
                    f"by_level[{level}][{metric}] not stable across 3 runs: {values}"
                )
            # Check conflict-class F1 per level
            conf_f1_values = [
                r.by_level.get(level, {})
                 .get("per_class_f1", {})
                 .get("conflict")
                for r in (r1, r2, r3)
            ]
            assert conf_f1_values[0] == conf_f1_values[1] == conf_f1_values[2], (
                f"by_level[{level}][conflict_f1] not stable across 3 runs: {conf_f1_values}"
            )

    def test_three_runs_have_same_dataset_hash(self, three_runs):
        """Dataset hash must be identical across all 3 runs — same data, same hash."""
        r1, r2, r3 = three_runs
        assert r1.dataset_hash == r2.dataset_hash == r3.dataset_hash

    def test_all_six_levels_present_in_every_run(self, three_runs):
        """Each run must expose metrics for all 6 conflict levels."""
        for i, r in enumerate(three_runs, 1):
            assert set(r.by_level.keys()) == EXPECTED_LEVELS, (
                f"Run {i} missing levels: {EXPECTED_LEVELS - set(r.by_level.keys())}"
            )

    def test_per_item_stability_across_all_verdict_types(self, three_runs):
        """Every item — conflict, consistent, and ambiguous ground truth —
        must receive the same prediction in all 3 runs.

        Note: we verify stability of predictions, not correctness. A model
        that consistently predicts 'consistent' for an ambiguous item is
        stable (passes) but wrong (reflected in accuracy metrics). These are
        separate properties — this test covers reproducibility only.
        """
        r1, r2, r3 = three_runs
        preds_by_run = [
            {item["id"]: (item["prediction"], item["label"])
             for item in r.per_item}
            for r in (r1, r2, r3)
        ]
        for item_id in preds_by_run[0]:
            p1, label = preds_by_run[0][item_id]
            p2 = preds_by_run[1][item_id][0]
            p3 = preds_by_run[2][item_id][0]
            assert p1 == p2 == p3, (
                f"Item {item_id!r} (ground truth='{label}') gave unstable predictions "
                f"across 3 runs: run1={p1}, run2={p2}, run3={p3}"
            )


# ---------------------------------------------------------------------------
# 4. Run log
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestRunLog:
    """Uses the already-computed three_runs fixture — zero additional API calls."""

    def test_three_runs_append_three_entries(self, three_runs, tmp_path):
        log_path = str(tmp_path / "runlog.jsonl")
        for i, r in enumerate(three_runs, 1):
            write_runlog(r, log_path)
            lines = Path(log_path).read_text().strip().splitlines()
            assert len(lines) == i, f"Expected {i} lines after run {i}, got {len(lines)}"

    def test_runlog_entry_has_required_fields(self, three_runs, tmp_path):
        log_path = str(tmp_path / "runlog.jsonl")
        write_runlog(three_runs[0], log_path)

        entry = json.loads(Path(log_path).read_text().strip())
        for field in ("run_id", "model", "dataset_hash", "n_runs",
                      "n_items", "overall", "by_level", "by_domain"):
            assert field in entry, f"runlog entry missing field: {field!r}"

    def test_runlog_reproducible_runs_have_matching_metrics(self, three_runs, tmp_path):
        """All 3 runs logged → every entry has the same accuracy, lw_f1, and dataset_hash."""
        log_path = str(tmp_path / "runlog.jsonl")
        for r in three_runs:
            write_runlog(r, log_path)

        entries = [
            json.loads(line)
            for line in Path(log_path).read_text().strip().splitlines()
        ]
        for metric in ("accuracy", "lw_f1", "macro_f1"):
            values = [e["overall"][metric] for e in entries]
            assert values[0] == values[1] == values[2], (
                f"Runlog metric '{metric}' not stable across 3 entries: {values}"
            )
        hashes = [e["dataset_hash"] for e in entries]
        assert hashes[0] == hashes[1] == hashes[2]


# ---------------------------------------------------------------------------
# 5. Fixture schema sanity — no API required, always runs
# ---------------------------------------------------------------------------

class TestFixtureSchema:
    """Data integrity checks on e2e_multihop.json. No API key required."""

    def test_all_items_have_required_top_level_fields(self, fixture_items):
        required = {"id", "domain", "category", "conflict_level",
                    "difficulty", "input", "label", "metadata"}
        for item in fixture_items:
            missing = required - item.keys()
            assert not missing, f"{item.get('id', '?')} missing fields: {missing}"

    def test_all_items_have_two_passages(self, fixture_items):
        for item in fixture_items:
            assert len(item["input"]["passages"]) == 2, (
                f"{item['id']} does not have exactly 2 passages"
            )

    def test_all_three_verdict_classes_present(self, fixture_items):
        verdicts = {item["label"]["verdict"] for item in fixture_items}
        for v in ("conflict", "consistent", "ambiguous"):
            assert v in verdicts, f"Fixture missing verdict class '{v}'"

    def test_conflict_levels_span_0_to_5(self, fixture_items):
        conflict_items = [i for i in fixture_items if i["label"]["verdict"] == "conflict"]
        levels = {item["conflict_level"] for item in conflict_items}
        assert levels == EXPECTED_LEVELS, (
            f"Expected conflict levels 0–5, got {sorted(levels)}"
        )

    def test_each_conflict_level_appears_exactly_once(self, fixture_items):
        from collections import Counter
        conflict_items = [i for i in fixture_items if i["label"]["verdict"] == "conflict"]
        counts = Counter(item["conflict_level"] for item in conflict_items)
        for level in range(6):
            assert counts[level] == 1, (
                f"Level {level} appears {counts[level]} time(s), expected 1"
            )

    def test_consistent_and_ambiguous_have_null_conflict_level(self, fixture_items):
        for item in fixture_items:
            if item["label"]["verdict"] in ("consistent", "ambiguous"):
                assert item["conflict_level"] is None, (
                    f"{item['id']} has verdict '{item['label']['verdict']}' "
                    f"but conflict_level={item['conflict_level']!r} (expected null)"
                )

    def test_conflict_and_ambiguous_chains_end_with_correct_prefix(self, fixture_items):
        for item in fixture_items:
            verdict = item["label"]["verdict"]
            chain = item["label"].get("reasoning_chain")
            if verdict == "consistent":
                continue  # consistent items have no chain by design
            assert chain, f"{item['id']} ({verdict}) has empty reasoning_chain"
            prefix = "CONFLICT" if verdict == "conflict" else "AMBIGUOUS"
            assert chain[-1].startswith(prefix), (
                f"{item['id']} ({verdict}) last chain step should start with "
                f"'{prefix}': {chain[-1]!r}"
            )

    def test_higher_conflict_levels_have_longer_chains(self, fixture_items):
        conflict_items = {
            item["conflict_level"]: item
            for item in fixture_items
            if item["label"]["verdict"] == "conflict"
        }
        l0_len = len(conflict_items[0]["label"]["reasoning_chain"])
        l5_len = len(conflict_items[5]["label"]["reasoning_chain"])
        assert l5_len > l0_len, (
            f"L5 chain ({l5_len} steps) should be longer than L0 chain ({l0_len} steps)"
        )

    def test_conflicting_spans_are_objects_with_required_keys(self, fixture_items):
        for item in fixture_items:
            spans = item["label"].get("conflicting_spans", [])
            assert spans, f"{item['id']} has no conflicting_spans"
            for s in spans:
                assert isinstance(s, dict), (
                    f"{item['id']} span is not an object: {s!r}"
                )
                assert "passage_id" in s and "span" in s, (
                    f"{item['id']} span missing passage_id or span: {s}"
                )

    def test_dataset_hash_stable_under_item_reorder(self, fixture_items):
        import random, copy
        shuffled = fixture_items.copy()
        random.shuffle(shuffled)
        assert _hash_dataset(fixture_items) == _hash_dataset(shuffled)

    def test_dataset_hash_changes_when_text_changes(self, fixture_items):
        import copy
        modified = copy.deepcopy(fixture_items)
        modified[0]["input"]["passages"][0]["text"] += " MODIFIED"
        assert _hash_dataset(fixture_items) != _hash_dataset(modified)
