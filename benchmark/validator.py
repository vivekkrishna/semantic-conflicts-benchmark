"""Dataset schema validator for the semantic-conflicts-benchmark.

Implements the acceptance criteria for R-1.2 (automated dataset validator).

Usage:
    # Programmatic:
    from benchmark.validator import validate_dataset, validate_item
    errors_by_id = validate_dataset(items)

    # CLI (see scripts/validate_dataset.py):
    python scripts/validate_dataset.py
    python scripts/validate_dataset.py --domains philosophy software

Rules enforced:
  conflict items:
    - conflict_level is an integer 0–5
    - reasoning_chain length == conflict_level + 1
      (conflict_level "Step N —" entries + 1 "CONFLICT — " entry)
    - each "Step N —" entry must not contain prohibited modal/hedging words
    - final entry must start with "CONFLICT — "
    - explanation is non-null and non-empty
    - conflicting_spans is a non-empty list
  ambiguous items:
    - conflict_level is null
    - reasoning_chain is present and final entry starts with "AMBIGUOUS — "
  consistent items:
    - conflict_level is null
  all items:
    - required top-level fields are present
"""

import re
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "id", "domain", "category", "conflict_level",
    "difficulty", "input", "label", "metadata",
]

REQUIRED_LABEL_KEYS = [
    "verdict", "conflict_level", "reasoning_chain",
    "explanation", "conflicting_spans", "ambiguity_reason",
]

# Words that indicate epistemic uncertainty — prohibited in conflict-item inference steps.
# These are checked with word-boundary matching to avoid false positives
# (e.g. "Mayflower", "courageous").
PROHIBITED_MODAL_WORDS = [
    "may", "might", "could", "perhaps", "arguably", "likely",
]

_MODAL_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in PROHIBITED_MODAL_WORDS) + r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class ValidationError:
    item_id: str
    field: str
    message: str

    def __str__(self) -> str:
        return f"[{self.item_id}] {self.field}: {self.message}"


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

def validate_item(item: dict[str, Any]) -> list[ValidationError]:
    """Validate a single dataset item against the schema rules.

    Returns a list of ValidationError objects. An empty list means the item
    is valid.
    """
    errors: list[ValidationError] = []
    item_id = item.get("id", "<unknown>")

    # --- Required top-level fields ---
    for field in REQUIRED_FIELDS:
        if field not in item:
            errors.append(ValidationError(item_id, field, f"Missing required field '{field}'"))

    label = item.get("label", {})
    verdict = label.get("verdict")
    top_level_cl = item.get("conflict_level")

    # --- Required label keys ---
    for key in REQUIRED_LABEL_KEYS:
        if key not in label:
            errors.append(ValidationError(
                item_id, f"label.{key}",
                f"Missing required label key '{key}'",
            ))

    if verdict == "conflict":
        errors.extend(_validate_conflict_item(item_id, item, label, top_level_cl))
    elif verdict == "consistent":
        errors.extend(_validate_consistent_item(item_id, top_level_cl))
    elif verdict == "ambiguous":
        errors.extend(_validate_ambiguous_item(item_id, item, label, top_level_cl))

    return errors


def validate_dataset(items: list[dict[str, Any]]) -> dict[str, list[ValidationError]]:
    """Validate every item in a list.

    Returns a dict mapping item_id → list[ValidationError] for items that
    have at least one error. Items with no errors are omitted.
    """
    result: dict[str, list[ValidationError]] = {}
    for item in items:
        errors = validate_item(item)
        if errors:
            item_id = item.get("id", "<unknown>")
            result[item_id] = errors
    return result


# ---------------------------------------------------------------------------
# Verdict-specific helpers
# ---------------------------------------------------------------------------

def _validate_conflict_item(
    item_id: str,
    item: dict,
    label: dict,
    top_level_cl: Any,
) -> list[ValidationError]:
    errors: list[ValidationError] = []

    # conflict_level must be int 0–5
    if not isinstance(top_level_cl, int) or not (0 <= top_level_cl <= 5):
        errors.append(ValidationError(
            item_id, "conflict_level",
            f"conflict items must have integer conflict_level 0–5, got {top_level_cl!r}",
        ))
        # Cannot validate chain length without a valid level; return early for chain checks
        return errors

    # explanation must be non-null and non-empty
    explanation = label.get("explanation")
    if not explanation:
        errors.append(ValidationError(
            item_id, "label.explanation",
            "conflict items must have a non-null, non-empty explanation",
        ))

    # conflicting_spans must be a non-empty list
    spans = label.get("conflicting_spans")
    if not spans:
        errors.append(ValidationError(
            item_id, "label.conflicting_spans",
            "conflict items must have a non-empty conflicting_spans list",
        ))

    # reasoning_chain checks
    chain = label.get("reasoning_chain")
    if not chain:
        errors.append(ValidationError(
            item_id, "label.reasoning_chain",
            "conflict items must have a non-null reasoning_chain",
        ))
        return errors

    expected_len = top_level_cl + 1  # conflict_level Step entries + 1 CONFLICT entry
    if len(chain) != expected_len:
        errors.append(ValidationError(
            item_id, "label.reasoning_chain",
            f"expected {expected_len} chain entries (level={top_level_cl} step(s) + CONFLICT), "
            f"got {len(chain)}",
        ))

    # Final entry must start with "CONFLICT — "
    if not chain[-1].startswith("CONFLICT — "):
        errors.append(ValidationError(
            item_id, "label.reasoning_chain",
            f"final chain entry must start with 'CONFLICT — ', got: {chain[-1][:60]!r}",
        ))

    # Modal/hedging words in inference steps (all entries except the final CONFLICT line)
    for i, step in enumerate(chain[:-1]):
        match = _MODAL_PATTERN.search(step)
        if match:
            errors.append(ValidationError(
                item_id, f"label.reasoning_chain[{i}]",
                f"prohibited modal word {match.group()!r} in step {i + 1}: {step[:80]}",
            ))

    return errors


def _validate_consistent_item(item_id: str, top_level_cl: Any) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if top_level_cl is not None:
        errors.append(ValidationError(
            item_id, "conflict_level",
            f"consistent items must have conflict_level=null, got {top_level_cl!r}",
        ))
    return errors


def _validate_ambiguous_item(
    item_id: str,
    item: dict,
    label: dict,
    top_level_cl: Any,
) -> list[ValidationError]:
    errors: list[ValidationError] = []

    if top_level_cl is not None:
        errors.append(ValidationError(
            item_id, "conflict_level",
            f"ambiguous items must have conflict_level=null, got {top_level_cl!r}",
        ))

    chain = label.get("reasoning_chain")
    if not chain:
        errors.append(ValidationError(
            item_id, "label.reasoning_chain",
            "ambiguous items must have a non-null reasoning_chain",
        ))
    elif not chain[-1].startswith("AMBIGUOUS — "):
        errors.append(ValidationError(
            item_id, "label.reasoning_chain",
            f"final chain entry of ambiguous item must start with 'AMBIGUOUS — ', "
            f"got: {chain[-1][:60]!r}",
        ))

    return errors
