"""Tests for benchmark/validator.py — dataset schema validation.

TDD: all tests in this file were written before the validator implementation.
They define the acceptance criteria for R-1.2 (automated dataset validator).

Rule summary being tested:
  - conflict items: chain_len == conflict_level + 1 (level "Step N" entries + 1 "CONFLICT —" entry)
  - conflict items: no modal/hedging words in Step entries
  - conflict items: final entry starts with "CONFLICT — "
  - conflict items: explanation is non-null
  - conflict items: conflicting_spans is non-null list
  - ambiguous items: chain_len >= 1; final entry starts with "AMBIGUOUS — "
  - ambiguous/consistent items: conflict_level is null at top level
  - all items: required top-level fields present
"""

import json
from pathlib import Path

import pytest

from benchmark.validator import ValidationError, validate_dataset, validate_item


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
DATA_DIR = Path(__file__).parent.parent / "data"

REQUIRED_TOP_LEVEL = ["id", "domain", "category", "conflict_level", "difficulty", "input", "label", "metadata"]


def _conflict_item(level: int = 1, chain=None, explanation="Prose explanation.", spans=None) -> dict:
    """Minimal valid conflict item at the given level."""
    default_chain = [f"Step {i + 1} — certain inference." for i in range(level)] + [
        "CONFLICT — the two passages are incompatible."
    ]
    return {
        "id": f"test_L{level}_001",
        "domain": "philosophy",
        "category": "cross_document",
        "conflict_level": level,
        "difficulty": "easy",
        "input": {
            "passages": [
                {"id": "A", "text": "Passage A text.", "source": "Source A"},
                {"id": "B", "text": "Passage B text.", "source": "Source B"},
            ],
            "question": "Conflict, consistent, or ambiguous?",
        },
        "label": {
            "verdict": "conflict",
            "conflict_level": level,
            "reasoning_chain": chain if chain is not None else default_chain,
            "explanation": explanation,
            "conflicting_spans": spans if spans is not None else [
                {"passage_id": "A", "span": "Passage A text."},
                {"passage_id": "B", "span": "Passage B text."},
            ],
            "ambiguity_reason": None,
        },
        "metadata": {
            "created_by": "human",
            "version": "1.0",
            "source_type": "synthetic",
            "source_verifiability": "illustrative",
        },
    }


def _consistent_item() -> dict:
    return {
        "id": "test_C_001",
        "domain": "philosophy",
        "category": "cross_document",
        "conflict_level": None,
        "difficulty": "n/a",
        "input": {
            "passages": [
                {"id": "A", "text": "Passage A.", "source": "Source A"},
                {"id": "B", "text": "Passage B.", "source": "Source B"},
            ],
            "question": "Conflict, consistent, or ambiguous?",
        },
        "label": {
            "verdict": "consistent",
            "conflict_level": None,
            "reasoning_chain": None,
            "explanation": None,
            "conflicting_spans": None,
            "ambiguity_reason": None,
        },
        "metadata": {
            "created_by": "human",
            "version": "1.0",
            "source_type": "synthetic",
            "source_verifiability": "illustrative",
        },
    }


def _ambiguous_item() -> dict:
    return {
        "id": "test_A_001",
        "domain": "philosophy",
        "category": "cross_document",
        "conflict_level": None,
        "difficulty": "n/a",
        "input": {
            "passages": [
                {"id": "A", "text": "Passage A.", "source": "Source A"},
                {"id": "B", "text": "Passage B.", "source": "Source B"},
            ],
            "question": "Conflict, consistent, or ambiguous?",
        },
        "label": {
            "verdict": "ambiguous",
            "conflict_level": None,
            "reasoning_chain": [
                "Step 1 — the passages appear compatible on the surface.",
                "AMBIGUOUS — a conflict exists only if term X means Y, which is not specified.",
            ],
            "explanation": None,
            "conflicting_spans": None,
            "ambiguity_reason": "The meaning of term X is underdetermined.",
        },
        "metadata": {
            "created_by": "human",
            "version": "1.0",
            "source_type": "synthetic",
            "source_verifiability": "illustrative",
        },
    }


def _error_fields(errors: list[ValidationError]) -> set[str]:
    return {e.field for e in errors}


# ---------------------------------------------------------------------------
# Valid items pass with no errors
# ---------------------------------------------------------------------------

class TestValidItemsPass:
    def test_valid_conflict_L0(self):
        item = _conflict_item(level=0)
        assert validate_item(item) == []

    def test_valid_conflict_L1(self):
        item = _conflict_item(level=1)
        assert validate_item(item) == []

    def test_valid_conflict_L3(self):
        item = _conflict_item(level=3)
        assert validate_item(item) == []

    def test_valid_conflict_L5(self):
        item = _conflict_item(level=5)
        assert validate_item(item) == []

    def test_valid_consistent(self):
        assert validate_item(_consistent_item()) == []

    def test_valid_ambiguous(self):
        assert validate_item(_ambiguous_item()) == []


# ---------------------------------------------------------------------------
# Chain length
# ---------------------------------------------------------------------------

class TestChainLength:
    def test_chain_too_long_flagged(self):
        # L1 should have 2 entries (1 Step + CONFLICT); 3 entries is wrong
        chain = ["Step 1 — inference.", "Step 2 — extra step.", "CONFLICT — conflict."]
        errors = validate_item(_conflict_item(level=1, chain=chain))
        assert any("chain" in e.field for e in errors)

    def test_chain_too_short_flagged(self):
        # L2 should have 3 entries; only CONFLICT line is wrong
        chain = ["CONFLICT — conflict."]
        errors = validate_item(_conflict_item(level=2, chain=chain))
        assert any("chain" in e.field for e in errors)

    def test_L0_with_one_conflict_entry_passes(self):
        chain = ["CONFLICT — explicit surface conflict."]
        assert validate_item(_conflict_item(level=0, chain=chain)) == []

    def test_L0_with_extra_step_flagged(self):
        chain = ["Step 1 — an inference.", "CONFLICT — conflict."]
        errors = validate_item(_conflict_item(level=0, chain=chain))
        assert any("chain" in e.field for e in errors)

    def test_error_message_includes_expected_and_actual(self):
        chain = ["Step 1 — a.", "Step 2 — b.", "CONFLICT — c."]  # 3 entries for L1
        errors = validate_item(_conflict_item(level=1, chain=chain))
        chain_errors = [e for e in errors if "chain" in e.field]
        assert chain_errors
        msg = chain_errors[0].message
        assert "2" in msg   # expected length
        assert "3" in msg   # actual length


# ---------------------------------------------------------------------------
# Final step format
# ---------------------------------------------------------------------------

class TestFinalStepFormat:
    def test_missing_conflict_prefix_flagged(self):
        chain = ["Step 1 — inference.", "The conflict is obvious."]
        errors = validate_item(_conflict_item(level=1, chain=chain))
        assert any("chain" in e.field for e in errors)

    def test_lowercase_conflict_flagged(self):
        chain = ["Step 1 — inference.", "conflict — the passages disagree."]
        errors = validate_item(_conflict_item(level=1, chain=chain))
        assert any("chain" in e.field for e in errors)

    def test_correct_prefix_passes(self):
        chain = ["Step 1 — inference.", "CONFLICT — the passages contradict."]
        assert validate_item(_conflict_item(level=1, chain=chain)) == []

    def test_ambiguous_chain_missing_ambiguous_prefix_flagged(self):
        item = _ambiguous_item()
        item["label"]["reasoning_chain"][-1] = "The relationship is unclear."
        errors = validate_item(item)
        assert any("chain" in e.field for e in errors)


# ---------------------------------------------------------------------------
# Modal language in inference steps
# ---------------------------------------------------------------------------

class TestModalLanguage:
    @pytest.mark.parametrize("word,step_text", [
        ("may",      "Step 1 — the agent may find the resource locked."),
        ("might",    "Step 1 — this might create a deadlock."),
        ("could",    "Step 1 — the model could in principle reject this."),
        ("perhaps",  "Step 1 — perhaps the value is non-null."),
        ("arguably", "Step 1 — this arguably violates the rule."),
        ("likely",   "Step 1 — this is likely to cause an error."),
    ])
    def test_prohibited_modal_in_step_flagged(self, word, step_text):
        chain = [step_text, "CONFLICT — conflict."]
        errors = validate_item(_conflict_item(level=1, chain=chain))
        modal_errors = [e for e in errors if "modal" in e.message.lower() or word in e.message.lower()]
        assert modal_errors, f"Expected modal word '{word}' to be flagged"

    def test_modal_in_conflict_conclusion_not_flagged(self):
        # Modal words in the CONFLICT line itself are not inference steps — not checked
        chain = ["Step 1 — certain inference.", "CONFLICT — this may be the core issue."]
        assert validate_item(_conflict_item(level=1, chain=chain)) == []

    def test_modal_free_step_passes(self):
        chain = ["Step 1 — the policy forbids this action.", "CONFLICT — conflict."]
        assert validate_item(_conflict_item(level=1, chain=chain)) == []

    def test_word_boundary_respected(self):
        # "mayflower", "courageous" should not be flagged
        chain = ["Step 1 — the Mayflower policy courageous forbids it.", "CONFLICT — c."]
        errors = validate_item(_conflict_item(level=1, chain=chain))
        assert not any("modal" in e.message.lower() for e in errors)


# ---------------------------------------------------------------------------
# Conflict item — required label fields
# ---------------------------------------------------------------------------

class TestConflictRequiredFields:
    def test_null_explanation_flagged(self):
        item = _conflict_item(explanation=None)
        errors = validate_item(item)
        assert any("explanation" in e.field for e in errors)

    def test_empty_explanation_flagged(self):
        item = _conflict_item(explanation="")
        errors = validate_item(item)
        assert any("explanation" in e.field for e in errors)

    def test_null_conflicting_spans_flagged(self):
        item = _conflict_item(spans=None)
        # Override — set to None explicitly
        item["label"]["conflicting_spans"] = None
        errors = validate_item(item)
        assert any("span" in e.field for e in errors)

    def test_empty_conflicting_spans_list_flagged(self):
        item = _conflict_item(spans=[])
        errors = validate_item(item)
        assert any("span" in e.field for e in errors)

    def test_null_reasoning_chain_flagged(self):
        item = _conflict_item()
        item["label"]["reasoning_chain"] = None
        errors = validate_item(item)
        assert any("chain" in e.field for e in errors)


# ---------------------------------------------------------------------------
# conflict_level field rules
# ---------------------------------------------------------------------------

class TestConflictLevelField:
    def test_consistent_item_with_nonnull_level_flagged(self):
        item = _consistent_item()
        item["conflict_level"] = 2
        errors = validate_item(item)
        assert any("conflict_level" in e.field for e in errors)

    def test_ambiguous_item_with_nonnull_level_flagged(self):
        item = _ambiguous_item()
        item["conflict_level"] = 1
        errors = validate_item(item)
        assert any("conflict_level" in e.field for e in errors)

    def test_conflict_item_with_null_level_flagged(self):
        item = _conflict_item(level=2)
        item["conflict_level"] = None
        errors = validate_item(item)
        assert any("conflict_level" in e.field for e in errors)


# ---------------------------------------------------------------------------
# Required top-level fields
# ---------------------------------------------------------------------------

class TestRequiredFields:
    @pytest.mark.parametrize("field", REQUIRED_TOP_LEVEL)
    def test_missing_required_field_flagged(self, field):
        item = _conflict_item(level=1)
        del item[field]
        errors = validate_item(item)
        assert errors, f"Expected error for missing field '{field}'"


# ---------------------------------------------------------------------------
# validate_dataset — multiple items
# ---------------------------------------------------------------------------

class TestValidateDataset:
    def test_empty_list_returns_empty(self):
        assert validate_dataset([]) == {}

    def test_all_valid_returns_empty(self):
        items = [_conflict_item(1), _consistent_item(), _ambiguous_item()]
        assert validate_dataset(items) == {}

    def test_invalid_items_appear_in_result(self):
        bad = _conflict_item(level=1)
        bad["label"]["explanation"] = None   # introduce an error
        good = _conflict_item(level=2)
        good["id"] = "test_L2_001"
        errors_by_id = validate_dataset([bad, good])
        assert "test_L1_001" in errors_by_id
        assert "test_L2_001" not in errors_by_id

    def test_multiple_errors_per_item_reported(self):
        item = _conflict_item(level=1)
        item["label"]["explanation"] = None
        item["label"]["conflicting_spans"] = None
        errors_by_id = validate_dataset([item])
        assert len(errors_by_id["test_L1_001"]) >= 2


# ---------------------------------------------------------------------------
# Integration: real dataset
# ---------------------------------------------------------------------------

class TestRealDataset:
    """Run the validator against the actual data files.

    These tests verify the dataset is clean after R-1.1 and R-1.3 data fixes.
    """

    @pytest.fixture
    def all_items(self):
        items = []
        for domain_dir in sorted(DATA_DIR.iterdir()):
            if not domain_dir.is_dir():
                continue
            v1 = domain_dir / "v1.json"
            if v1.exists():
                items.extend(json.loads(v1.read_text(encoding="utf-8")))
        return items

    def test_no_chain_length_violations(self, all_items):
        """All domains have correct chain lengths after data fixes."""
        errors_by_id = validate_dataset(all_items)
        chain_length_violations = [
            item_id
            for item_id, errors in errors_by_id.items()
            if any("chain" in e.field and ("expected" in e.message or "length" in e.message) for e in errors)
        ]
        assert chain_length_violations == [], (
            f"Chain-length violations found: {sorted(chain_length_violations)}"
        )

    def test_no_modal_language_violations(self, all_items):
        """All domains are free of prohibited modal words after data fixes."""
        errors_by_id = validate_dataset(all_items)
        modal_violations = [
            item_id
            for item_id, errors in errors_by_id.items()
            if any("modal" in e.message.lower() for e in errors)
        ]
        assert modal_violations == [], (
            f"Modal language violations found: {sorted(modal_violations)}"
        )

    def test_full_dataset_is_clean(self, all_items):
        """The entire dataset passes validation (R-1.1 + R-1.3 complete)."""
        errors_by_id = validate_dataset(all_items)
        if errors_by_id:
            report = []
            for item_id, errors in sorted(errors_by_id.items()):
                for e in errors:
                    report.append(f"  {item_id}: [{e.field}] {e.message}")
            pytest.fail("Dataset has validation errors:\n" + "\n".join(report))
