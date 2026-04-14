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
    payload = {
        "model":             results.model_name,
        "run_id":            results.run_id,
        "total_items":       results.total_items,
        "n_runs":            results.n_runs,
        "dataset_hash":      results.dataset_hash,
        "overall":           results.overall,
        "by_domain":         results.by_domain,
        "by_level":          {str(k): v for k, v in results.by_level.items()},
        "by_conflict_type":  results.by_conflict_type,
        "by_category":       results.by_category,
        "by_difficulty":     results.by_difficulty,
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
    "model", "run_id", "n_items",
    "lw_f1", "accuracy", "macro_f1", "binary_conflict_f1", "expl_bert_f1",
    "level_0_f1", "level_1_f1", "level_2_f1", "level_3_f1", "level_4_f1", "level_5_f1",
    "philosophy_f1", "software_f1", "law_f1", "science_f1", "content_f1", "teams_f1",
]


def write_leaderboard(results: EvaluationResults, path: str) -> None:
    os.makedirs(Path(path).parent, exist_ok=True)
    write_header = not Path(path).exists()

    o  = results.overall
    bl = results.by_level
    bd = results.by_domain

    row = {
        "model":               results.model_name,
        "run_id":              results.run_id,
        "n_items":             results.total_items,
        "lw_f1":               o.get("lw_f1", ""),
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
        if write_header:
            writer.writeheader()
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
