"""Orchestrates the full evaluation pipeline.

Flow:
    Evaluator.run()
      ├── Load JSONL files from data/<domain>/v1.jsonl
      ├── For each item: build prompt → adapter.predict() → score
      ├── Compute: accuracy, macro-F1, LW-F1, ROUGE-L
      └── Return EvaluationResults
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from benchmark.adapters.base import ModelAdapter
from benchmark.metrics import (
    compute_metrics,
    compute_metrics_for_subset,
    compute_level_metrics,
    level_weighted_f1,
)
from benchmark.tasks.explanation import score_explanation, should_score_explanation
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


class Evaluator:
    """Runs the benchmark for a given ModelAdapter."""

    def __init__(
        self,
        adapter: ModelAdapter,
        domains: Optional[list[str]] = None,
        data_dir: str = "data/",
        verbose: bool = False,
    ) -> None:
        self.adapter  = adapter
        self.domains  = domains or DOMAINS
        self.data_dir = Path(data_dir)
        self.verbose  = verbose
        self._task    = VerdictClassificationTask()

    def run(self) -> EvaluationResults:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        items  = self._load_items()

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
                print(
                    f"  [{tick}] {item['id']:<30} {lvl_s:<4} "
                    f"label={result['label']:<12} pred={result['prediction']:<12} "
                    f"rouge={result['explanation_rouge_l']:.3f}"
                )

        # Compute per-level metrics and LW-F1
        by_level = compute_level_metrics(results)
        lw_f1    = level_weighted_f1(by_level)

        overall = compute_metrics(
            [r["label"] for r in results],
            [r["prediction"] for r in results],
            [r["explanation_rouge_l"] for r in results],
        )
        overall["lw_f1"] = lw_f1

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
        prompt   = self._task.build_prompt(item)
        response = self.adapter.predict(prompt)

        label         = item["label"]["verdict"]
        prediction    = response.verdict
        correct       = label == prediction
        conflict_level = item.get("conflict_level")  # int or None

        rouge = 0.0
        if should_score_explanation(item):
            # Score against the full reasoning_chain joined as reference text
            reference = _build_reference_text(item)
            rouge = score_explanation(response.explanation, reference)

        return {
            "id":                  item["id"],
            "domain":              item.get("domain", "unknown"),
            "category":            item.get("category", "unknown"),
            "difficulty":          item.get("difficulty", "unknown"),
            "conflict_level":      conflict_level,
            "conflict_type":       _conflict_type(conflict_level),
            "label":               label,
            "prediction":          prediction,
            "correct":             correct,
            "explanation_rouge_l": rouge,
            "model_explanation":   response.explanation,
            "raw_response":        response.raw_response,
        }

    @staticmethod
    def _group_metrics(
        results: list[dict[str, Any]], key: str
    ) -> dict[str, dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = {}
        for r in results:
            g = r.get(key, "unknown")
            groups.setdefault(str(g), []).append(r)
        return {g: compute_metrics_for_subset(items) for g, items in groups.items()}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _conflict_type(level: Optional[int]) -> str:
    if level is None:
        return "none"
    if level == 0:
        return "surface"
    return f"implicit_L{level}"


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
