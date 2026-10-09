"""Orchestrates the full evaluation pipeline.

Flow:
    Evaluator.run()
      ├── Load JSON files from data/<domain>/v1.json
      ├── For each item: build prompt → adapter.predict() → score
      ├── Compute: accuracy, macro-F1, LW-F1, BERTScore, conflict polarity
      └── Return EvaluationResults
"""

import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from benchmark.adapters.base import ModelAdapter
from benchmark.metrics import (
    compute_metrics,
    compute_metrics_for_subset,
    compute_level_metrics,
    compute_polarity_metrics,
    level_weighted_f1,
)
from benchmark.tasks.explanation import (
    score_explanation,
    score_explanations_batch,
    should_score_explanation,
)
from benchmark.tasks.verdict_classification import VerdictClassificationTask


DOMAINS = ["philosophy", "software", "law", "science", "content", "teams"]
DATA_VERSION = "v1"
DATA_EXT     = ".json"


@dataclass
class EvaluationResults:
    model_name:       str
    run_id:           str
    total_items:      int
    overall:          dict[str, Any]
    by_domain:        dict[str, dict[str, Any]]
    by_level:         dict[int, dict[str, Any]]
    by_conflict_type: dict[str, dict[str, Any]]
    by_category:      dict[str, dict[str, Any]]
    by_difficulty:    dict[str, dict[str, Any]]
    per_item:         list[dict[str, Any]] = field(default_factory=list)
    dataset_hash:     str = ""
    n_runs:           int = 1
    temperature:      float = 0.0
    per_run_lw_f1:    list[float] = field(default_factory=list)


class Evaluator:
    """Runs the benchmark for a given ModelAdapter."""

    def __init__(
        self,
        adapter: ModelAdapter,
        domains: Optional[list[str]] = None,
        data_dir: str = "data/",
        n_runs: int = 1,
        temperature: float = 0.0,
        verbose: bool = False,
        include_draft_polarity: bool = False,
    ) -> None:
        self.adapter     = adapter
        self.domains     = domains or DOMAINS
        self.data_dir    = Path(data_dir)
        self.n_runs      = max(1, n_runs)
        self.temperature = temperature
        self.verbose     = verbose
        # Draft polarity labels are unreviewed; score them only when asked.
        self.include_draft_polarity = include_draft_polarity
        self._task       = VerdictClassificationTask()

    def run(self) -> EvaluationResults:
        run_id      = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        items       = self._load_items()
        dataset_hash = _hash_dataset(items)

        if not items:
            raise RuntimeError(f"No dataset items found under {self.data_dir}")

        results = []
        for item in items:
            result = self._evaluate_item(item)
            results.append(result)
            if self.verbose:
                tick  = "✓" if result["correct"] else "✗"
                level = result["conflict_level"]
                lvl_s = f"L{level}" if level is not None else "  "
                runs_info = ""
                if self.n_runs > 1:
                    agree = result.get("run_agreement", 1.0)
                    runs_info = f" agree={agree:.0%}"
                type_info = ""
                if result["polarity_label"]:
                    type_info = (
                        f" type={result['polarity_prediction'] or '-'}"
                        f"/{result['polarity_label']}"
                    )
                print(
                    f"  [{tick}] {item['id']:<30} {lvl_s:<4} "
                    f"label={result['label']:<12} pred={result['prediction']:<12} "
                    f"bert={result['explanation_bert_f1'] or 0:.3f}{runs_info}{type_info}"
                )

        # Batch BERTScore — loads DistilBERT once for all scoreable items
        _preds = [
            r["model_explanation"] if "_bert_reference" in r else None
            for r in results
        ]
        _refs = [r.pop("_bert_reference", None) for r in results]
        for r, score in zip(results, score_explanations_batch(_preds, _refs)):
            if score is not None:
                r["explanation_bert_f1"] = score

        # Compute per-level metrics and LW-F1
        by_level = compute_level_metrics(results)
        lw_f1    = level_weighted_f1(by_level)

        overall = compute_metrics(
            [r["label"] for r in results],
            [r["prediction"] for r in results],
            [r.get("explanation_bert_f1") for r in results],
        )
        overall["lw_f1"] = lw_f1

        polarity = compute_polarity_metrics(results)
        polarity["n_excluded_draft"] = sum(
            1 for r in results
            if r["polarity_status"] == "draft" and not r["polarity_label"]
        )
        overall["polarity"] = polarity

        # Agreement rate across runs (1.0 when n_runs == 1)
        per_run_lw_f1: list[float] = []
        if self.n_runs > 1:
            overall["mean_run_agreement"] = round(
                sum(r.get("run_agreement", 1.0) for r in results) / len(results), 4
            )
            # Compute LW-F1 independently per run using that run's verdict
            for run_idx in range(self.n_runs):
                run_results = []
                for r in results:
                    verdicts = r.get("run_verdicts", [r["prediction"]])
                    verdict_i = verdicts[run_idx] if run_idx < len(verdicts) else r["prediction"]
                    run_results.append({**r, "prediction": verdict_i})
                run_by_level = compute_level_metrics(run_results)
                per_run_lw_f1.append(round(level_weighted_f1(run_by_level), 6))

        return EvaluationResults(
            model_name=self.adapter.name,
            run_id=run_id,
            total_items=len(results),
            overall=overall,
            by_domain=self._group_metrics(results, "domain"),
            by_level=by_level,
            by_conflict_type=self._group_metrics(results, "conflict_type"),
            by_category=self._group_metrics(results, "category"),
            by_difficulty=self._group_metrics(results, "difficulty"),
            per_item=results,
            dataset_hash=dataset_hash,
            n_runs=self.n_runs,
            temperature=self.temperature,
            per_run_lw_f1=per_run_lw_f1,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for domain in self.domains:
            path = self.data_dir / domain / f"{DATA_VERSION}{DATA_EXT}"
            if not path.exists():
                print(f"  [warn] dataset not found: {path}", file=sys.stderr)
                continue
            with path.open(encoding="utf-8") as f:
                domain_items = json.load(f)
            items.extend(domain_items)
        return items

    def _evaluate_item(self, item: dict[str, Any]) -> dict[str, Any]:
        prompt = self._task.build_prompt(item)
        label  = item["label"]["verdict"]
        conflict_level = item.get("conflict_level")  # int or None

        if self.n_runs == 1:
            response   = self.adapter.predict(prompt)
            prediction = response.verdict
            run_verdicts  = [prediction]
            run_agreement = 1.0
            polarity_prediction = response.conflict_type if prediction == "conflict" else None
        else:
            responses: list = []
            for _ in range(self.n_runs):
                responses.append(self.adapter.predict(prompt))
            run_verdicts = [r.verdict for r in responses]
            counts       = Counter(run_verdicts)
            prediction   = counts.most_common(1)[0][0]
            run_agreement = round(counts[prediction] / self.n_runs, 4)
            # Majority type among runs that agreed on "conflict"
            run_types = [
                r.conflict_type for r in responses
                if r.verdict == "conflict" and r.conflict_type
            ]
            polarity_prediction = (
                Counter(run_types).most_common(1)[0][0]
                if prediction == "conflict" and run_types else None
            )
            # Use the last response's explanation/raw for storage
            response = responses[-1]

        correct = label == prediction

        polarity_status = item["label"].get("polarity_status")
        polarity_label  = None
        if label == "conflict" and (
            polarity_status == "reviewed"
            or (polarity_status == "draft" and self.include_draft_polarity)
        ):
            polarity_label = item["label"].get("conflict_polarity")

        result: dict[str, Any] = {
            "id":                  item["id"],
            "domain":              item.get("domain", "unknown"),
            "category":            item.get("category", "unknown"),
            "difficulty":          item.get("difficulty", "unknown"),
            "conflict_level":      conflict_level,
            "conflict_type":       _conflict_type(conflict_level),
            "label":               label,
            "prediction":          prediction,
            "correct":             correct,
            "explanation_bert_f1": None,
            "polarity_label":      polarity_label,
            "polarity_status":     polarity_status,
            "polarity_prediction": polarity_prediction,
            "polarity_correct":    (
                polarity_prediction == polarity_label if polarity_label else None
            ),
            "model_explanation":   response.explanation,
            "raw_response":        response.raw_response,
        }
        if should_score_explanation(item):
            result["_bert_reference"] = _build_reference_text(item)
        if self.n_runs > 1:
            result["run_verdicts"]  = run_verdicts
            result["run_agreement"] = run_agreement
        return result

    @staticmethod
    def _group_metrics(
        results: list[dict[str, Any]], key: str
    ) -> dict[str, dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = {}
        for r in results:
            g = r.get(key, "unknown")
            groups.setdefault(str(g), []).append(r)
        out: dict[str, dict[str, Any]] = {}
        for g, items in groups.items():
            out[g] = compute_metrics_for_subset(items)
            out[g]["polarity"] = compute_polarity_metrics(items)
        return out


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _conflict_type(level: Optional[int]) -> str:
    if level is None:
        return "none"
    if level == 0:
        return "surface"
    return f"implicit_L{level}"


def _hash_dataset(items: list[dict]) -> str:
    """SHA-256 of the sorted, canonically serialised dataset (first 16 hex chars)."""
    serialized = json.dumps(
        sorted(items, key=lambda x: x["id"]),
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def _build_reference_text(item: dict[str, Any]) -> str:
    """Combine reasoning_chain steps + explanation as the reference for ROUGE scoring."""
    label = item.get("label", {})
    parts: list[str] = []
    chain = label.get("reasoning_chain")
    if chain:
        parts.extend(chain)
    explanation = label.get("explanation")
    if explanation:
        parts.append(explanation)
    return " ".join(parts)
