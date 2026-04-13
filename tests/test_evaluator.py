"""Smoke tests for the Evaluator using the sample fixture and a mock adapter."""

import json
import re
from pathlib import Path

import pytest

from benchmark.adapters.base import AdapterResponse, ModelAdapter
from benchmark.evaluator import Evaluator, EvaluationResults


FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_JSONL = FIXTURES_DIR / "sample.jsonl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_data_dir(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Split sample.jsonl into per-domain subdirectories under tmp_path.

    Returns (data_dir, {passage_A_prefix: verdict}) for use by PerfectAdapter.
    The lookup key is the first 40 characters of passage A's text (always unique
    across the fixture) because the prompt contains full passage text.
    """
    lookup: dict[str, str] = {}
    if not SAMPLE_JSONL.exists():
        pytest.skip("sample.jsonl fixture not found")

    items_by_domain: dict[str, list[dict]] = {}
    with SAMPLE_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            domain = item["domain"]
            items_by_domain.setdefault(domain, []).append(item)
            # Key on the first 40 chars of passage A — unique per item
            passage_a_prefix = item["input"]["passages"][0]["text"][:40]
            lookup[passage_a_prefix] = item["label"]["verdict"]

    for domain, domain_items in items_by_domain.items():
        domain_dir = tmp_path / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        with (domain_dir / "v1.jsonl").open("w", encoding="utf-8") as fh:
            for it in domain_items:
                fh.write(json.dumps(it) + "\n")

    return tmp_path, lookup


# ---------------------------------------------------------------------------
# Mock adapters
# ---------------------------------------------------------------------------

class PerfectAdapter(ModelAdapter):
    """Returns the ground-truth verdict for every item."""

    def __init__(self, lookup: dict[str, str]):
        self._lookup = lookup

    @property
    def name(self) -> str:
        return "perfect-mock"

    def predict(self, prompt: str) -> AdapterResponse:
        for passage_prefix, verdict in self._lookup.items():
            if passage_prefix in prompt:
                explanation = "Mock explanation." if verdict != "consistent" else None
                return AdapterResponse(
                    verdict=verdict,
                    explanation=explanation,
                    raw_response=f"{verdict.upper()}\nMock explanation.",
                )
        return AdapterResponse(verdict="consistent", raw_response="CONSISTENT")


class WrongAdapter(ModelAdapter):
    """Always predicts 'consistent'."""

    @property
    def name(self) -> str:
        return "always-consistent-mock"

    def predict(self, prompt: str) -> AdapterResponse:
        return AdapterResponse(verdict="consistent", raw_response="CONSISTENT")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir_and_lookup(tmp_path):
    return _build_data_dir(tmp_path)


@pytest.fixture
def perfect_evaluator(data_dir_and_lookup):
    data_dir, lookup = data_dir_and_lookup
    adapter = PerfectAdapter(lookup)
    domains = [p.name for p in data_dir.iterdir() if p.is_dir()]
    return Evaluator(
        adapter=adapter,
        domains=domains,
        data_dir=str(data_dir),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_evaluator_returns_results_object(perfect_evaluator):
    results = perfect_evaluator.run()
    assert isinstance(results, EvaluationResults)


def test_perfect_adapter_scores_one(perfect_evaluator):
    results = perfect_evaluator.run()
    # All fixture items are "conflict" → accuracy 1.0; macro-F1 is 1/3 because
    # consistent and ambiguous have zero support in this single-class fixture.
    assert results.overall["accuracy"] == pytest.approx(1.0, abs=1e-3)
    assert results.overall["per_class_f1"]["conflict"] == pytest.approx(1.0, abs=1e-3)


def test_lw_f1_present_in_overall(perfect_evaluator):
    results = perfect_evaluator.run()
    assert "lw_f1" in results.overall
    assert 0.0 <= results.overall["lw_f1"] <= 1.0


def test_by_domain_populated(perfect_evaluator):
    results = perfect_evaluator.run()
    assert len(results.by_domain) > 0
    for domain, m in results.by_domain.items():
        assert "accuracy" in m
        assert "macro_f1" in m


def test_by_level_populated(perfect_evaluator):
    results = perfect_evaluator.run()
    # The fixture has only L0 conflict items, so level 0 must appear
    assert 0 in results.by_level


def test_per_item_list_populated(perfect_evaluator):
    results = perfect_evaluator.run()
    assert len(results.per_item) == results.total_items
    for item in results.per_item:
        assert "id"         in item
        assert "label"      in item
        assert "prediction" in item
        assert "correct"    in item


def test_wrong_adapter_scores_low(data_dir_and_lookup):
    data_dir, lookup = data_dir_and_lookup
    domains = [p.name for p in data_dir.iterdir() if p.is_dir()]
    evaluator = Evaluator(
        adapter=WrongAdapter(),
        domains=domains,
        data_dir=str(data_dir),
    )
    results = evaluator.run()
    # All fixture items are 'conflict'; predicting 'consistent' gives 0% accuracy
    assert results.overall["accuracy"] == pytest.approx(0.0, abs=1e-3)


def test_run_id_is_utc_timestamp(perfect_evaluator):
    results = perfect_evaluator.run()
    assert re.match(r"\d{8}T\d{6}Z", results.run_id)
