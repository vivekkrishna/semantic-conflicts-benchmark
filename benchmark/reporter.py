"""Generates all output artefacts from an EvaluationResults object.

Supported formats:
    JSON     — full results, per-item predictions, raw responses
    Markdown — human-readable report with tables and failure examples
    CSV      — one row appended to a running leaderboard file
    JSONL    — one line appended to a cumulative run log (audit trail)
    Console  — formatted table printed to stdout
"""

import csv
import json
import os
import statistics
from pathlib import Path
from typing import Any

from tabulate import tabulate

from benchmark.evaluator import EvaluationResults

LEVEL_NAMES = {0: "L0 Surface", 1: "L1 Immediate", 2: "L2 Two-hop",
               3: "L3 Three-hop", 4: "L4 Four-hop", 5: "L5 Deep"}


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def write_json(results: EvaluationResults, path: str) -> None:
    os.makedirs(Path(path).parent, exist_ok=True)

    lw_f1_std = None
    unstable  = False
    if len(results.per_run_lw_f1) > 1:
        lw_f1_std = statistics.stdev(results.per_run_lw_f1)
        unstable  = lw_f1_std > 0.01

    # Mirror lw_f1_std into the overall dict for convenience
    overall = dict(results.overall)
    overall["lw_f1_std"] = lw_f1_std

    payload = {
        "model":             results.model_name,
        "run_id":            results.run_id,
        "total_items":       results.total_items,
        "n_runs":            results.n_runs,
        "temperature":       results.temperature,
        "dataset_hash":      results.dataset_hash,
        "overall":           overall,
        "lw_f1_std":         lw_f1_std,
        "per_run_lw_f1":     results.per_run_lw_f1 if results.per_run_lw_f1 else [],
        "unstable":          unstable if results.n_runs > 1 else False,
        "by_domain":         results.by_domain,
        "by_level":          {str(k): v for k, v in results.by_level.items()},
        "by_conflict_type":  results.by_conflict_type,
        "by_category":       results.by_category,
        "by_difficulty":     results.by_difficulty,
        "failure_breakdown": _compute_failure_breakdown(results.per_item, results.total_items),
        "per_item":          results.per_item,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  JSON  → {path}")


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def write_markdown(results: EvaluationResults, path: str) -> None:
    os.makedirs(Path(path).parent, exist_ok=True)
    lines: list[str] = []

    lines.append(f"# Benchmark Results — {results.model_name}")
    hash_str = f"  |  **Dataset:** `{results.dataset_hash}`" if results.dataset_hash else ""
    runs_str = f"  |  **Runs/item:** {results.n_runs}" if results.n_runs > 1 else ""
    lines.append(f"\n**Run ID:** `{results.run_id}`  |  **Items:** {results.total_items}{hash_str}{runs_str}\n")

    # Overall scores
    o = results.overall
    lines.append("## Overall Scores\n")
    overall_rows = [
        ["**LW-F1** _(primary score)_",   f"{o.get('lw_f1', 0):.4f}"],
        ["Accuracy",                       f"{o['accuracy']:.4f}"],
        ["Macro-F1 (3-class)",             f"{o['macro_f1']:.4f}"],
        ["Binary Conflict F1",             f"{o['binary_conflict_f1']:.4f}"],
        ["Explanation BERTScore-F1",       f"{o.get('explanation_bert_f1') or 0:.4f}"],
        ["— Conflict F1",                  f"{o['per_class_f1'].get('conflict', 0):.4f}"],
        ["— Consistent F1",                f"{o['per_class_f1'].get('consistent', 0):.4f}"],
        ["— Ambiguous F1",                 f"{o['per_class_f1'].get('ambiguous', 0):.4f}"],
    ]
    lines.append(tabulate(overall_rows, headers=["Metric", "Score"], tablefmt="github"))
    lines.append("")

    # By difficulty level
    lines.append("## By Difficulty Level\n")
    level_rows = _level_table_rows(results.by_level)
    lines.append(tabulate(level_rows,
                          headers=["Level", "Accuracy", "Macro-F1", "Conflict-F1", "BERTScore-F1", "N"],
                          tablefmt="github"))
    lines.append("")

    # By domain
    lines.append("## By Domain\n")
    domain_rows = _dict_to_table_rows(results.by_domain)
    lines.append(tabulate(domain_rows,
                          headers=["Domain", "Accuracy", "Macro-F1", "Conflict-F1", "BERTScore-F1", "N"],
                          tablefmt="github"))
    lines.append("")

    # By difficulty bucket
    lines.append("## By Difficulty Bucket\n")
    diff_rows = _dict_to_table_rows(results.by_difficulty)
    lines.append(tabulate(diff_rows,
                          headers=["Difficulty", "Accuracy", "Macro-F1", "Conflict-F1", "BERTScore-F1", "N"],
                          tablefmt="github"))
    lines.append("")

    # Conflict polarity (destructive vs constructive)
    lines.extend(_polarity_markdown(results))

    # Failure breakdown (R-4.5)
    breakdown = _compute_failure_breakdown(results.per_item, results.total_items)
    nonzero = {k: v for k, v in breakdown.items() if v["count"] > 0}
    if nonzero:
        lines.append("## Failure Breakdown\n")
        breakdown_rows = [
            [ftype, entry["count"], f"{entry['pct']:.1f}%"]
            for ftype, entry in sorted(nonzero.items(), key=lambda x: -x[1]["count"])
        ]
        lines.append(tabulate(breakdown_rows,
                              headers=["Failure type", "Count", "% of items"],
                              tablefmt="github"))
        lines.append("")

    # Example failures
    failures = [r for r in results.per_item if not r["correct"]][:5]
    if failures:
        lines.append("## Example Failures\n")
        for i, f in enumerate(failures, 1):
            lvl = f["conflict_level"]
            lvl_s = f"L{lvl}" if lvl is not None else "n/a"
            lines.append(f"### Failure {i} — `{f['id']}`")
            lines.append(
                f"- **Domain:** {f['domain']}  |  **Level:** {lvl_s}  |  "
                f"**Difficulty:** {f['difficulty']}"
            )
            lines.append(f"- **Label:** `{f['label']}`  |  **Predicted:** `{f['prediction']}`")
            if f.get("model_explanation"):
                snippet = f["model_explanation"][:300]
                lines.append(f"- **Model explanation:** {snippet}…")
            lines.append("")

    content = "\n".join(lines)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"  MD    → {path}")


# ---------------------------------------------------------------------------
# CSV leaderboard
# ---------------------------------------------------------------------------

LEADERBOARD_HEADER = [
    "model", "run_id", "n_items", "n_runs", "temperature",
    "lw_f1", "lw_f1_std", "accuracy", "macro_f1", "binary_conflict_f1", "expl_bert_f1",
    "level_0_f1", "level_1_f1", "level_2_f1", "level_3_f1", "level_4_f1", "level_5_f1",
    "philosophy_f1", "software_f1", "law_f1", "science_f1", "content_f1", "teams_f1",
]

# R-4.4: Static baseline row — always-predict-conflict trivial baseline.
# Pre-computed for the standard 180-item dataset (18 conflict + 72 non-conflict per level).
#   conflict precision = 18/90 = 0.2, recall = 1.0 → F1 = 1/3
#   accuracy = 108/180 = 0.6 (18 conflict items per level × 6 correct, all non-conflict wrong)
#   macro_f1 = (1/3 + 0 + 0) / 3 ≈ 0.111 (consistent-F1 = 0, ambiguous-F1 = 0)
#   binary_conflict_f1: positive = conflict+ambiguous (108 items), always predicted conflict
#     precision = 108/180 = 0.6, recall = 1.0 → F1 = 2*0.6/(0.6+1.0) = 0.75
BASELINE_ROW = {
    "model":               "baseline_always_conflict",
    "run_id":              "static",
    "n_items":             180,
    "n_runs":              1,
    "temperature":         "",
    "lw_f1":               0.333,
    "lw_f1_std":           "",
    "accuracy":            0.600,
    "macro_f1":            0.250,
    "binary_conflict_f1":  0.750,
    "expl_bert_f1":        "",
    **{f"level_{l}_f1": 0.333 for l in range(6)},
    **{d: "" for d in ["philosophy_f1", "software_f1", "law_f1",
                        "science_f1", "content_f1", "teams_f1"]},
}


def write_leaderboard(results: EvaluationResults, path: str) -> None:
    os.makedirs(Path(path).parent, exist_ok=True)
    file_exists = Path(path).exists()

    o  = results.overall
    bl = results.by_level
    bd = results.by_domain

    lw_f1_std = (
        statistics.stdev(results.per_run_lw_f1)
        if len(results.per_run_lw_f1) > 1 else ""
    )

    row = {
        "model":               results.model_name,
        "run_id":              results.run_id,
        "n_items":             results.total_items,
        "n_runs":              results.n_runs,
        "temperature":         results.temperature,
        "lw_f1":               o.get("lw_f1", ""),
        "lw_f1_std":           lw_f1_std,
        "accuracy":            o["accuracy"],
        "macro_f1":            o["macro_f1"],
        "binary_conflict_f1":  o["binary_conflict_f1"],
        "expl_bert_f1":        o.get("explanation_bert_f1", ""),
        **{f"level_{l}_f1": bl.get(l, {}).get("per_class_f1", {}).get("conflict", "") for l in range(6)},
        **{f"{d}_f1": bd.get(d, {}).get("macro_f1", "")
           for d in ["philosophy", "software", "law", "science", "content", "teams"]},
    }

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEADERBOARD_HEADER)
        if not file_exists:
            writer.writeheader()
            writer.writerow(BASELINE_ROW)   # R-4.4: baseline always first
        writer.writerow(row)
    print(f"  CSV   → {path}")


# ---------------------------------------------------------------------------
# JSONL run log
# ---------------------------------------------------------------------------

def write_runlog(results: EvaluationResults, path: str, results_path: str = "") -> None:
    """Append one summary record to a cumulative JSONL run log.

    Captures all aggregate metrics but omits per_item (kept in results_path).
    Two entries with the same dataset_hash + model + n_runs should produce
    identical metric values — mismatches signal non-determinism or data drift.
    """
    os.makedirs(Path(path).parent, exist_ok=True)

    def _slim(metrics: dict) -> dict:
        """Keep only the scalar metrics; drop per_class_f1 nesting for compactness."""
        return {k: v for k, v in metrics.items() if not isinstance(v, dict)}

    entry = {
        "run_id":       results.run_id,
        "model":        results.model_name,
        "dataset_hash": results.dataset_hash,
        "n_runs":       results.n_runs,
        "n_items":      results.total_items,
        "overall":      results.overall,
        "by_level":     {str(k): _slim(v) for k, v in results.by_level.items()},
        "by_domain":    {k: _slim(v) for k, v in results.by_domain.items()},
        "results_path": results_path,
    }

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"  LOG   → {path}")


# ---------------------------------------------------------------------------
# Console
# ---------------------------------------------------------------------------

def print_console(results: EvaluationResults) -> None:
    o = results.overall
    print(f"\n{'='*64}")
    print(f"  Model : {results.model_name}")
    print(f"  Run   : {results.run_id}  |  Items: {results.total_items}")
    if results.dataset_hash:
        runs_s = f"  |  Runs/item: {results.n_runs}" if results.n_runs > 1 else ""
        print(f"  Hash  : {results.dataset_hash}{runs_s}")
    print(f"{'='*64}")

    overall_rows = [
        ["LW-F1 (primary)",    f"{o.get('lw_f1', 0):.4f}"],
        ["Accuracy",           f"{o['accuracy']:.4f}"],
        ["Macro-F1",           f"{o['macro_f1']:.4f}"],
        ["Binary Conflict F1", f"{o['binary_conflict_f1']:.4f}"],
        ["Explanation BERTScore-F1", f"{o.get('explanation_bert_f1') or 0:.4f}"],
    ]
    print(tabulate(overall_rows, headers=["Metric", "Score"], tablefmt="simple"))

    pol = o.get("polarity") or {}
    if pol.get("n_labelled"):
        print("\nConflict type (destructive vs constructive):")
        print(tabulate(_polarity_rows(pol), headers=["Metric", "Score"], tablefmt="simple"))
    elif pol.get("n_excluded_draft"):
        print(f"\nConflict type: not scored — {pol['n_excluded_draft']} draft labels "
              f"excluded (use --include-draft-polarity).")

    if results.by_level:
        print("\nBy difficulty level:")
        level_rows = _level_table_rows(results.by_level)
        print(tabulate(level_rows,
                       headers=["Level", "Accuracy", "Macro-F1", "Conflict-F1", "BERTScore-F1", "N"],
                       tablefmt="simple"))

    print("\nBy domain:")
    domain_rows = _dict_to_table_rows(results.by_domain)
    print(tabulate(domain_rows,
                   headers=["Domain", "Accuracy", "Macro-F1", "Conflict-F1", "BERTScore-F1", "N"],
                   tablefmt="simple"))
    print()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fmt(v: Any) -> str:
    return "—" if v is None else f"{v:.4f}"


def _polarity_rows(pol: dict[str, Any]) -> list[list]:
    pc = pol.get("per_class_f1") or {}
    return [
        ["Type accuracy (on detected conflicts)", _fmt(pol.get("polarity_accuracy"))],
        ["Type macro-F1 (on detected conflicts)", _fmt(pol.get("polarity_macro_f1"))],
        ["— Destructive F1",                       _fmt(pc.get("destructive"))],
        ["— Constructive F1",                      _fmt(pc.get("constructive"))],
        ["Joint accuracy (verdict + type)",        _fmt(pol.get("joint_accuracy"))],
        ["Type coverage",                          _fmt(pol.get("type_coverage"))],
        ["N labelled / detected / typed",
         f"{pol.get('n_labelled', 0)} / {pol.get('n_detected', 0)} / {pol.get('n_typed', 0)}"],
    ]


def _polarity_markdown(results: EvaluationResults) -> list[str]:
    pol = results.overall.get("polarity") or {}
    lines = ["## Conflict Type (Destructive vs Constructive)\n"]
    if not pol.get("n_labelled"):
        n_draft = pol.get("n_excluded_draft", 0)
        lines.append(
            f"_Not scored: no reviewed polarity labels. {n_draft} draft labels were "
            f"excluded — rerun with `--include-draft-polarity` to score them._\n"
            if n_draft else "_Not scored: no items carry a polarity label._\n"
        )
        return lines
    if pol.get("n_excluded_draft"):
        lines.append(f"_{pol['n_excluded_draft']} draft labels excluded._\n")
    lines.append(tabulate(_polarity_rows(pol), headers=["Metric", "Score"], tablefmt="github"))
    lines.append("")

    rows = []
    for domain, m in sorted(results.by_domain.items()):
        dp = m.get("polarity") or {}
        if dp.get("n_labelled"):
            rows.append([domain, _fmt(dp.get("polarity_accuracy")),
                         _fmt(dp.get("joint_accuracy")), dp["n_labelled"]])
    if rows:
        lines.append("### By domain\n")
        lines.append(tabulate(rows, headers=["Domain", "Type acc.", "Joint acc.", "N"],
                              tablefmt="github"))
        lines.append("")
    return lines


def _level_table_rows(by_level: dict[int, dict[str, Any]]) -> list[list]:
    rows = []
    for level in range(6):
        m = by_level.get(level)
        if m is None:
            continue
        name = LEVEL_NAMES.get(level, f"L{level}")
        rows.append([
            name,
            f"{m.get('accuracy', 0):.4f}",
            f"{m.get('macro_f1', 0):.4f}",
            f"{m.get('per_class_f1', {}).get('conflict', 0):.4f}",
            f"{m.get('explanation_bert_f1') or 0:.4f}",
            m.get("n_items", 0),
        ])
    return rows


def _compute_failure_breakdown(
    per_item: list[dict[str, Any]], total_items: int
) -> dict[str, dict[str, Any]]:
    """R-4.5: Count each failure type across all items.

    Failure types:
        conflict_as_ambiguous   — conflict item predicted ambiguous
        conflict_as_consistent  — conflict item predicted consistent
        consistent_as_conflict  — consistent item predicted conflict
        consistent_as_ambiguous — consistent item predicted ambiguous
        ambiguous_as_conflict   — ambiguous item predicted conflict
        ambiguous_as_consistent — ambiguous item predicted consistent
    """
    counts: dict[str, int] = {
        "conflict_as_ambiguous":   0,
        "conflict_as_consistent":  0,
        "consistent_as_conflict":  0,
        "consistent_as_ambiguous": 0,
        "ambiguous_as_conflict":   0,
        "ambiguous_as_consistent": 0,
    }
    for item in per_item:
        if item.get("correct"):
            continue
        label = item.get("label")
        pred  = item.get("prediction")
        key   = f"{label}_as_{pred}"
        if key in counts:
            counts[key] += 1

    n = total_items or 1
    return {
        ftype: {"count": count, "pct": round(count / n * 100, 1)}
        for ftype, count in counts.items()
    }


def _dict_to_table_rows(by_group: dict[str, dict[str, Any]]) -> list[list]:
    rows = []
    for group, m in sorted(by_group.items()):
        rows.append([
            group,
            f"{m.get('accuracy', 0):.4f}",
            f"{m.get('macro_f1', 0):.4f}",
            f"{m.get('per_class_f1', {}).get('conflict', 0):.4f}",
            f"{m.get('explanation_bert_f1') or 0:.4f}",
            m.get("n_items", 0),
        ])
    return rows
