"""Tests for the destructive/constructive conflict-polarity task.

Covers: response parsing, AdapterResponse validation, compute_polarity_metrics,
validator rules, Evaluator wiring (draft exclusion, multi-run vote), Markdown
report section, and dataset invariants for the shipped labels.
"""

import json
from collections import Counter
from pathlib import Path

import pytest

from benchmark.adapters.base import AdapterResponse, ModelAdapter, parse_verdict_response
from benchmark.evaluator import Evaluator
from benchmark.metrics import compute_polarity_metrics
from benchmark.reporter import write_markdown
from benchmark.validator import validate_item

DATA_DIR = Path(__file__).parent.parent / "data"
DOMAINS = ["content", "law", "philosophy", "science", "software", "teams"]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class TestParseConflictType:
    def test_type_line(self):
        r = parse_verdict_response("CONFLICT\nTYPE: DESTRUCTIVE\nThe cache is stale.")
        assert r.verdict == "conflict"
        assert r.conflict_type == "destructive"

    def test_type_line_markdown_and_case(self):
        r = parse_verdict_response("CONFLICT\n**Type:** constructive\nwhy")
        assert r.conflict_type == "constructive"

    def test_type_line_with_dash(self):
        r = parse_verdict_response("CONFLICT\n- TYPE — Destructive\nx")
        assert r.conflict_type == "destructive"

    def test_type_on_verdict_line(self):
        r = parse_verdict_response("CONFLICT — CONSTRUCTIVE\nbody")
        assert r.verdict == "conflict"
        assert r.conflict_type == "constructive"

    def test_type_word_in_body_is_ignored(self):
        r = parse_verdict_response("CONFLICT\nThis is destructive to user trust.")
        assert r.conflict_type is None

    def test_no_type_for_non_conflict_verdicts(self):
        assert parse_verdict_response("CONSISTENT\nTYPE: DESTRUCTIVE").conflict_type is None
        assert parse_verdict_response("AMBIGUOUS\nTYPE: DESTRUCTIVE\nx").conflict_type is None

    def test_type_line_stripped_from_explanation(self):
        r = parse_verdict_response("CONFLICT\nTYPE: DESTRUCTIVE\nThe cache is stale.")
        assert r.explanation == "The cache is stale."

    def test_constructive_does_not_trip_verdict_parsing(self):
        # "CONSTRUCTIVE" must not be read as CONSISTENT/CONFLICT by the verdict scan
        r = parse_verdict_response("AMBIGUOUS\nCould be constructive or not.")
        assert r.verdict == "ambiguous"


class TestAdapterResponseConflictType:
    def test_defaults_to_none(self):
        assert AdapterResponse(verdict="conflict").conflict_type is None

    def test_rejects_unknown_type(self):
        with pytest.raises(ValueError):
            AdapterResponse(verdict="conflict", conflict_type="neutral")


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _r(label, pred, pol_label=None, pol_pred=None):
    return {
        "label": label, "prediction": pred,
        "polarity_label": pol_label, "polarity_prediction": pol_pred,
    }


class TestComputePolarityMetrics:
    def test_no_labels_returns_none_metrics(self):
        m = compute_polarity_metrics([_r("conflict", "conflict"), _r("consistent", "consistent")])
        assert m["n_labelled"] == 0
        assert m["polarity_accuracy"] is None
        assert m["joint_accuracy"] is None

    def test_perfect(self):
        rs = [
            _r("conflict", "conflict", "destructive", "destructive"),
            _r("conflict", "conflict", "constructive", "constructive"),
        ]
        m = compute_polarity_metrics(rs)
        assert m["polarity_accuracy"] == 1.0
        assert m["polarity_macro_f1"] == 1.0
        assert m["joint_accuracy"] == 1.0
        assert m["type_coverage"] == 1.0

    def test_missed_detection_hurts_joint_not_conditional(self):
        rs = [
            _r("conflict", "conflict", "destructive", "destructive"),
            _r("conflict", "consistent", "constructive", None),
        ]
        m = compute_polarity_metrics(rs)
        assert m["n_detected"] == 1
        assert m["polarity_accuracy"] == 1.0
        assert m["joint_accuracy"] == 0.5

    def test_missing_type_counts_wrong_and_lowers_coverage(self):
        rs = [
            _r("conflict", "conflict", "destructive", "destructive"),
            _r("conflict", "conflict", "constructive", None),
        ]
        m = compute_polarity_metrics(rs)
        assert m["polarity_accuracy"] == 0.5
        assert m["type_coverage"] == 0.5
        assert m["per_class_f1"]["constructive"] == 0.0

    def test_single_class_predictor_macro_f1(self):
        rs = [
            _r("conflict", "conflict", "destructive", "destructive"),
            _r("conflict", "conflict", "constructive", "destructive"),
        ]
        m = compute_polarity_metrics(rs)
        assert m["polarity_accuracy"] == 0.5
        # destructive F1 = 2/3, constructive F1 = 0 → macro = 1/3
        assert m["polarity_macro_f1"] == pytest.approx(0.3333, abs=1e-4)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def _item(verdict="conflict", **label_extra):
    level = 0 if verdict == "conflict" else None
    label = {
        "verdict": verdict,
        "conflict_level": level,
        "reasoning_chain": ["CONFLICT — x."] if verdict == "conflict" else None,
        "explanation": "e" if verdict == "conflict" else None,
        "conflicting_spans": [{"passage_id": "A", "span": "a"}] if verdict == "conflict" else None,
        "ambiguity_reason": None,
        **label_extra,
    }
    return {
        "id": "t_001", "domain": "software", "category": "cross_document",
        "conflict_level": level, "difficulty": "easy",
        "input": {"passages": [], "question": "?"}, "label": label, "metadata": {},
    }


def _fields(errors):
    return {e.field for e in errors}


class TestValidatePolarity:
    def test_absent_keys_are_allowed(self):
        assert validate_item(_item()) == []

    def test_valid_conflict_polarity(self):
        item = _item(conflict_polarity="destructive", polarity_rationale="why",
                     polarity_status="draft")
        assert validate_item(item) == []

    def test_bad_polarity_value(self):
        item = _item(conflict_polarity="neutral", polarity_rationale="why",
                     polarity_status="draft")
        assert "label.conflict_polarity" in _fields(validate_item(item))

    def test_missing_rationale_and_bad_status(self):
        item = _item(conflict_polarity="constructive", polarity_rationale="",
                     polarity_status="final")
        fields = _fields(validate_item(item))
        assert {"label.polarity_rationale", "label.polarity_status"} <= fields

    def test_non_conflict_must_be_null(self):
        item = _item("consistent", conflict_polarity="destructive",
                     polarity_rationale=None, polarity_status=None)
        assert "label.conflict_polarity" in _fields(validate_item(item))

    def test_non_conflict_all_null_ok(self):
        item = _item("consistent", conflict_polarity=None,
                     polarity_rationale=None, polarity_status=None)
        assert validate_item(item) == []


# ---------------------------------------------------------------------------
# Evaluator wiring
# ---------------------------------------------------------------------------

def _eval_item(item_id, verdict, text, polarity=None, status=None):
    level = 0 if verdict == "conflict" else None
    return {
        "id": item_id, "domain": "software", "category": "cross_document",
        "conflict_level": level, "difficulty": "easy" if level is not None else "n/a",
        "input": {
            "passages": [{"id": "A", "text": text}, {"id": "B", "text": "other"}],
            "question": "?",
        },
        "label": {
            "verdict": verdict, "conflict_level": level,
            "reasoning_chain": ["CONFLICT — x."] if verdict == "conflict" else None,
            "explanation": None, "conflicting_spans": None, "ambiguity_reason": None,
            "conflict_polarity": polarity,
            "polarity_rationale": "r" if polarity else None,
            "polarity_status": status,
        },
        "metadata": {},
    }


EVAL_ITEMS = [
    _eval_item("software_L0_901", "conflict", "PASSAGE-ONE", "destructive", "reviewed"),
    _eval_item("software_L0_902", "conflict", "PASSAGE-TWO", "constructive", "reviewed"),
    _eval_item("software_L0_903", "conflict", "PASSAGE-THREE", "constructive", "draft"),
    _eval_item("software_C_904", "consistent", "PASSAGE-FOUR"),
]


class ScriptedAdapter(ModelAdapter):
    """Returns a scripted (verdict, type) per passage marker; cycles per call for multi-run."""

    def __init__(self, script: dict[str, list[tuple[str, str | None]]]):
        self._script = script
        self._calls: Counter = Counter()

    @property
    def name(self) -> str:
        return "scripted-mock"

    def predict(self, prompt: str) -> AdapterResponse:
        for marker, answers in self._script.items():
            if marker in prompt:
                verdict, ctype = answers[self._calls[marker] % len(answers)]
                self._calls[marker] += 1
                return AdapterResponse(verdict=verdict, explanation="x", conflict_type=ctype)
        raise AssertionError("unscripted prompt")


@pytest.fixture
def eval_data_dir(tmp_path):
    (tmp_path / "software").mkdir()
    (tmp_path / "software" / "v1.json").write_text(json.dumps(EVAL_ITEMS), encoding="utf-8")
    return tmp_path


def _run(data_dir, script, **kw):
    return Evaluator(ScriptedAdapter(script), domains=["software"],
                     data_dir=str(data_dir), **kw).run()


PERFECT_SCRIPT = {
    "PASSAGE-ONE":   [("conflict", "destructive")],
    "PASSAGE-TWO":   [("conflict", "constructive")],
    "PASSAGE-THREE": [("conflict", "destructive")],   # wrong vs draft gold
    "PASSAGE-FOUR":  [("consistent", None)],
}


class TestEvaluatorPolarity:
    def test_drafts_excluded_by_default(self, eval_data_dir):
        pol = _run(eval_data_dir, PERFECT_SCRIPT).overall["polarity"]
        assert pol["n_labelled"] == 2
        assert pol["n_excluded_draft"] == 1
        assert pol["polarity_accuracy"] == 1.0

    def test_drafts_included_on_request(self, eval_data_dir):
        pol = _run(eval_data_dir, PERFECT_SCRIPT, include_draft_polarity=True).overall["polarity"]
        assert pol["n_labelled"] == 3
        assert pol["n_excluded_draft"] == 0
        assert pol["polarity_accuracy"] == pytest.approx(0.6667, abs=1e-4)

    def test_per_item_fields(self, eval_data_dir):
        res = _run(eval_data_dir, PERFECT_SCRIPT)
        by_id = {r["id"]: r for r in res.per_item}
        assert by_id["software_L0_901"]["polarity_correct"] is True
        assert by_id["software_L0_903"]["polarity_label"] is None       # draft, excluded
        assert by_id["software_L0_903"]["polarity_status"] == "draft"
        assert by_id["software_C_904"]["polarity_prediction"] is None

    def test_by_domain_carries_polarity(self, eval_data_dir):
        res = _run(eval_data_dir, PERFECT_SCRIPT)
        assert res.by_domain["software"]["polarity"]["n_labelled"] == 2

    def test_verdict_metrics_unaffected_by_type(self, eval_data_dir):
        wrong_types = {k: [(v, ("constructive" if t == "destructive" else "destructive") if t else None)
                           for v, t in a] for k, a in PERFECT_SCRIPT.items()}
        a = _run(eval_data_dir, PERFECT_SCRIPT).overall
        b = _run(eval_data_dir, wrong_types).overall
        assert a["lw_f1"] == b["lw_f1"]
        assert a["accuracy"] == b["accuracy"]
        assert b["polarity"]["polarity_accuracy"] == 0.0

    def test_multi_run_majority_type(self, eval_data_dir):
        script = dict(PERFECT_SCRIPT)
        script["PASSAGE-ONE"] = [("conflict", "constructive"), ("conflict", "destructive"),
                                 ("conflict", "destructive")]
        res = _run(eval_data_dir, script, n_runs=3)
        by_id = {r["id"]: r for r in res.per_item}
        assert by_id["software_L0_901"]["polarity_prediction"] == "destructive"


class TestMarkdownPolarity:
    def test_section_when_scored(self, eval_data_dir, tmp_path):
        res = _run(eval_data_dir, PERFECT_SCRIPT)
        out = tmp_path / "r.md"
        write_markdown(res, str(out))
        md = out.read_text(encoding="utf-8")
        assert "## Conflict Type (Destructive vs Constructive)" in md
        assert "Joint accuracy" in md
        assert "1 draft labels excluded" in md

    def test_hint_when_only_drafts(self, tmp_path):
        items = [_eval_item("software_L0_905", "conflict", "ONLY-DRAFT", "destructive", "draft")]
        (tmp_path / "software").mkdir()
        (tmp_path / "software" / "v1.json").write_text(json.dumps(items), encoding="utf-8")
        res = _run(tmp_path, {"ONLY-DRAFT": [("conflict", "destructive")]})
        out = tmp_path / "r.md"
        write_markdown(res, str(out))
        assert "--include-draft-polarity" in out.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Dataset invariants for the shipped labels
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def all_items() -> list[dict]:
    items = []
    for domain in DOMAINS:
        items.extend(json.loads((DATA_DIR / domain / "v1.json").read_text(encoding="utf-8")))
    return items


class TestDatasetPolarity:
    def test_every_conflict_item_has_polarity(self, all_items):
        missing = [i["id"] for i in all_items
                   if i["label"]["verdict"] == "conflict"
                   and i["label"].get("conflict_polarity") not in ("destructive", "constructive")]
        assert missing == []

    def test_non_conflict_items_have_null_polarity(self, all_items):
        bad = [i["id"] for i in all_items
               if i["label"]["verdict"] != "conflict" and i["label"].get("conflict_polarity")]
        assert bad == []

    def test_both_classes_present(self, all_items):
        counts = Counter(i["label"]["conflict_polarity"] for i in all_items
                         if i["label"]["verdict"] == "conflict")
        assert counts["destructive"] > 0 and counts["constructive"] > 0
