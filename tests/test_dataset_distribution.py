"""Distributional invariant tests for the benchmark dataset (R-1.5 / I-25).

These tests assert that the dataset's structural balance is preserved across
any data edit. They run in CI alongside the structural validator.

Invariants:
  - 180 items total across 6 domains
  - 30 items per domain
  - Per domain: 18 conflict / 8 consistent / 4 ambiguous
  - 18 conflict items per difficulty level (L0–L5)
  - 3 conflict items per domain per level
  - All conflict items: non-null conflict_level, reasoning_chain, conflicting_spans
  - All consistent/ambiguous items: null conflict_level
"""

import json
from collections import Counter
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent.parent / "data"
DOMAINS = ["content", "law", "philosophy", "science", "software", "teams"]
LEVELS = [0, 1, 2, 3, 4, 5]

EXPECTED_TOTAL = 180
EXPECTED_PER_DOMAIN = 30
EXPECTED_CONFLICT_PER_DOMAIN = 18
EXPECTED_CONSISTENT_PER_DOMAIN = 8
EXPECTED_AMBIGUOUS_PER_DOMAIN = 4
EXPECTED_CONFLICT_PER_LEVEL = 18       # across all domains
EXPECTED_CONFLICT_PER_DOMAIN_PER_LEVEL = 3


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def all_items() -> list[dict]:
    items = []
    for domain in DOMAINS:
        path = DATA_DIR / domain / "v1.json"
        assert path.exists(), f"Missing data file: {path}"
        items.extend(json.loads(path.read_text(encoding="utf-8")))
    return items


@pytest.fixture(scope="module")
def conflict_items(all_items) -> list[dict]:
    return [i for i in all_items if i["label"]["verdict"] == "conflict"]


@pytest.fixture(scope="module")
def consistent_items(all_items) -> list[dict]:
    return [i for i in all_items if i["label"]["verdict"] == "consistent"]


@pytest.fixture(scope="module")
def ambiguous_items(all_items) -> list[dict]:
    return [i for i in all_items if i["label"]["verdict"] == "ambiguous"]


# ---------------------------------------------------------------------------
# Total count
# ---------------------------------------------------------------------------

class TestTotalCount:
    def test_total_item_count(self, all_items):
        assert len(all_items) == EXPECTED_TOTAL, (
            f"Expected {EXPECTED_TOTAL} total items, got {len(all_items)}"
        )

    def test_all_six_domains_present(self, all_items):
        domains_found = {i["domain"] for i in all_items}
        assert domains_found == set(DOMAINS), (
            f"Missing domains: {set(DOMAINS) - domains_found}"
        )


# ---------------------------------------------------------------------------
# Per-domain counts
# ---------------------------------------------------------------------------

class TestPerDomainCounts:
    @pytest.mark.parametrize("domain", DOMAINS)
    def test_domain_total(self, all_items, domain):
        count = sum(1 for i in all_items if i["domain"] == domain)
        assert count == EXPECTED_PER_DOMAIN, (
            f"Domain '{domain}': expected {EXPECTED_PER_DOMAIN} items, got {count}"
        )

    @pytest.mark.parametrize("domain", DOMAINS)
    def test_domain_conflict_count(self, all_items, domain):
        count = sum(1 for i in all_items
                    if i["domain"] == domain and i["label"]["verdict"] == "conflict")
        assert count == EXPECTED_CONFLICT_PER_DOMAIN, (
            f"Domain '{domain}': expected {EXPECTED_CONFLICT_PER_DOMAIN} conflict items, got {count}"
        )

    @pytest.mark.parametrize("domain", DOMAINS)
    def test_domain_consistent_count(self, all_items, domain):
        count = sum(1 for i in all_items
                    if i["domain"] == domain and i["label"]["verdict"] == "consistent")
        assert count == EXPECTED_CONSISTENT_PER_DOMAIN, (
            f"Domain '{domain}': expected {EXPECTED_CONSISTENT_PER_DOMAIN} consistent items, got {count}"
        )

    @pytest.mark.parametrize("domain", DOMAINS)
    def test_domain_ambiguous_count(self, all_items, domain):
        count = sum(1 for i in all_items
                    if i["domain"] == domain and i["label"]["verdict"] == "ambiguous")
        assert count == EXPECTED_AMBIGUOUS_PER_DOMAIN, (
            f"Domain '{domain}': expected {EXPECTED_AMBIGUOUS_PER_DOMAIN} ambiguous items, got {count}"
        )


# ---------------------------------------------------------------------------
# Per-level distribution
# ---------------------------------------------------------------------------

class TestPerLevelDistribution:
    def test_all_six_levels_present(self, conflict_items):
        levels_found = {i["label"]["conflict_level"] for i in conflict_items}
        assert levels_found == set(LEVELS), (
            f"Missing conflict levels: {set(LEVELS) - levels_found}"
        )

    @pytest.mark.parametrize("level", LEVELS)
    def test_conflict_count_per_level(self, conflict_items, level):
        count = sum(1 for i in conflict_items if i["label"]["conflict_level"] == level)
        assert count == EXPECTED_CONFLICT_PER_LEVEL, (
            f"Level {level}: expected {EXPECTED_CONFLICT_PER_LEVEL} conflict items, got {count}"
        )

    @pytest.mark.parametrize("domain", DOMAINS)
    @pytest.mark.parametrize("level", LEVELS)
    def test_conflict_count_per_domain_per_level(self, conflict_items, domain, level):
        count = sum(1 for i in conflict_items
                    if i["domain"] == domain and i["label"]["conflict_level"] == level)
        assert count == EXPECTED_CONFLICT_PER_DOMAIN_PER_LEVEL, (
            f"Domain '{domain}' level {level}: expected "
            f"{EXPECTED_CONFLICT_PER_DOMAIN_PER_LEVEL} conflict items, got {count}"
        )


# ---------------------------------------------------------------------------
# Field integrity by verdict
# ---------------------------------------------------------------------------

class TestFieldIntegrityByVerdict:
    def test_conflict_items_have_non_null_conflict_level(self, conflict_items):
        bad = [i["id"] for i in conflict_items if i["label"]["conflict_level"] is None]
        assert bad == [], f"Conflict items missing conflict_level: {bad}"

    def test_conflict_items_have_reasoning_chain(self, conflict_items):
        bad = [i["id"] for i in conflict_items
               if not i["label"].get("reasoning_chain")]
        assert bad == [], f"Conflict items missing reasoning_chain: {bad}"

    def test_conflict_items_have_conflicting_spans(self, conflict_items):
        bad = [i["id"] for i in conflict_items
               if not i["label"].get("conflicting_spans")]
        assert bad == [], f"Conflict items missing conflicting_spans: {bad}"

    def test_consistent_items_have_null_conflict_level(self, consistent_items):
        bad = [i["id"] for i in consistent_items
               if i["label"]["conflict_level"] is not None]
        assert bad == [], f"Consistent items with non-null conflict_level: {bad}"

    def test_ambiguous_items_have_null_conflict_level(self, ambiguous_items):
        bad = [i["id"] for i in ambiguous_items
               if i["label"]["conflict_level"] is not None]
        assert bad == [], f"Ambiguous items with non-null conflict_level: {bad}"

    def test_ambiguous_items_have_ambiguity_reason(self, ambiguous_items):
        bad = [i["id"] for i in ambiguous_items
               if not i["label"].get("ambiguity_reason")]
        assert bad == [], f"Ambiguous items missing ambiguity_reason: {bad}"

    def test_conflict_items_have_non_null_explanation(self, conflict_items):
        bad = [i["id"] for i in conflict_items
               if not i["label"].get("explanation")]
        assert bad == [], f"Conflict items missing explanation: {bad}"


# ---------------------------------------------------------------------------
# ID uniqueness
# ---------------------------------------------------------------------------

class TestIDUniqueness:
    def test_all_item_ids_are_unique(self, all_items):
        ids = [i["id"] for i in all_items]
        duplicates = [id_ for id_, count in Counter(ids).items() if count > 1]
        assert duplicates == [], f"Duplicate item IDs found: {duplicates}"

    def test_item_id_matches_domain(self, all_items):
        bad = [i["id"] for i in all_items
               if not i["id"].startswith(i["domain"])]
        assert bad == [], f"Item IDs don't match their domain field: {bad}"
