#!/usr/bin/env python3
"""R-1.4 — Level minimality checker for L3–L5 conflict items.

For each L3–L5 conflict item this script runs two complementary checks:

  1. LLM skip-test (automated)
     For every numbered step in the reasoning chain, the step is temporarily
     removed and a Claude model is asked whether the remaining chain still forms
     a valid, logically-certain path from the source passages to the conflict.
     A step is flagged SKIPPABLE if the LLM answers YES — i.e., removing it
     leaves the chain intact.

  2. Human review aid (formatted output)
     The full chain is printed with per-step skip verdicts so a human reviewer
     can make the final call.

Results are written to data/minimality_audit.json.

Usage:
    # Full run (L5 → L4 → L3, most-impactful first)
    python scripts/check_minimality.py

    # Single domain
    python scripts/check_minimality.py --domains philosophy

    # Specific levels
    python scripts/check_minimality.py --levels 5 4

    # Dry-run: print formatted chains only, no API calls
    python scripts/check_minimality.py --dry-run

    # Use a specific Claude model
    python scripts/check_minimality.py --model claude-haiku-4-5-20251001
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark.evaluator import DOMAINS

# ── constants ────────────────────────────────────────────────────────────────

AUDIT_PATH   = Path("data/minimality_audit.json")
DATA_DIR     = Path("data")
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

SKIP_TEST_SYSTEM = """\
You are a strict logic auditor for a multi-hop reasoning benchmark.
Your job is to decide whether a reasoning step is NECESSARY or REDUNDANT
in a chain that connects two source passages to a stated conflict conclusion.

A step is NECESSARY if removing it creates a logical gap — i.e., the next
step no longer follows with 100% certainty from what precedes it.

A step is REDUNDANT if removing it leaves the chain logically intact —
i.e., every remaining step still follows with 100% certainty from the
previous step (and the passages), and the final CONFLICT conclusion is
still fully supported.

Respond in this exact JSON format with no other text:
{
  "verdict": "NECESSARY" | "REDUNDANT",
  "confidence": "high" | "medium" | "low",
  "reason": "<one-sentence explanation>"
}"""

SKIP_TEST_TEMPLATE = """\
=== SOURCE PASSAGES ===
Passage A ({source_a}):
{text_a}

Passage B ({source_b}):
{text_b}

=== FULL ORIGINAL CHAIN (for reference) ===
{full_chain}

=== PRUNED CHAIN (step {step_num} has been removed) ===
{pruned_chain}

=== QUESTION ===
In the PRUNED chain above, does every step still follow with 100% logical
certainty from the previous step and the source passages?  Is the final
CONFLICT conclusion still fully supported without step {step_num}?

If yes → step {step_num} is REDUNDANT (the chain is still valid without it).
If no  → step {step_num} is NECESSARY (removing it breaks the logical path).

Respond only with the JSON object described in the system prompt."""


# ── LLM call ─────────────────────────────────────────────────────────────────

def _call_claude(client, model: str, user_msg: str) -> dict[str, Any]:
    """Call Claude and parse the JSON response for a skip-test verdict."""
    try:
        message = client.messages.create(
            model=model,
            max_tokens=256,
            temperature=0.0,
            system=SKIP_TEST_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = message.content[0].text.strip() if message.content else "{}"
        # Strip markdown fences if the model wraps in ```json
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as exc:
        return {"verdict": "ERROR", "confidence": "low", "reason": str(exc)}


# ── core logic ────────────────────────────────────────────────────────────────

def _format_chain(steps: list[str]) -> str:
    return "\n".join(f"  {s}" for s in steps)


def _pruned_chain(steps: list[str], remove_idx: int) -> list[str]:
    """Return chain with the step at remove_idx omitted (CONFLICT line excluded)."""
    return [s for i, s in enumerate(steps) if i != remove_idx]


def check_item(item: dict, client, model: str, dry_run: bool) -> dict[str, Any]:
    """Run skip-tests for every numbered step in this item's chain.

    Returns a result dict ready for minimality_audit.json.
    """
    chain   = item["label"]["reasoning_chain"]
    passages = item["input"]["passages"]
    pa      = next(p for p in passages if p["id"] == "A")
    pb      = next(p for p in passages if p["id"] == "B")

    # Numbered steps are everything except the final CONFLICT / AMBIGUOUS line
    numbered = [s for s in chain if not s.startswith("CONFLICT")]
    conflict_line = chain[-1]

    step_results = []
    any_redundant = False

    for idx, step in enumerate(numbered):
        step_num = idx + 1  # 1-indexed for display
        pruned   = _pruned_chain(numbered, idx) + [conflict_line]

        if dry_run:
            result = {"verdict": "DRY_RUN", "confidence": "—", "reason": "dry-run mode"}
        else:
            prompt = SKIP_TEST_TEMPLATE.format(
                source_a   = pa.get("source", "A"),
                text_a     = pa["text"],
                source_b   = pb.get("source", "B"),
                text_b     = pb["text"],
                full_chain = _format_chain(chain),
                step_num   = step_num,
                pruned_chain = _format_chain(pruned),
            )
            result = _call_claude(client, model, prompt)
            time.sleep(0.3)  # gentle rate-limit

        is_redundant = result.get("verdict") == "REDUNDANT"
        if is_redundant:
            any_redundant = True

        step_results.append({
            "step_num"    : step_num,
            "step_text"   : step,
            "verdict"     : result.get("verdict", "ERROR"),
            "confidence"  : result.get("confidence", "—"),
            "reason"      : result.get("reason", ""),
            "skippable"   : is_redundant,
        })

    return {
        "id"             : item["id"],
        "domain"         : item["domain"],
        "conflict_level" : item["conflict_level"],
        "any_redundant"  : any_redundant,
        "disposition"    : "PENDING_HUMAN_REVIEW",  # human sets MINIMAL / LEVEL_DEMOTED
        "steps"          : step_results,
    }


# ── formatting ────────────────────────────────────────────────────────────────

RESET  = "\033[0m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
BOLD   = "\033[1m"
DIM    = "\033[2m"


def _color(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{code}{text}{RESET}"


def print_item_report(result: dict) -> None:
    flag   = _color("⚠  SKIPPABLE STEP FOUND", RED + BOLD) if result["any_redundant"] \
             else _color("✓  all steps necessary", GREEN)
    level  = result["conflict_level"]
    print(f"\n{'─'*72}")
    print(f"{_color(result['id'], BOLD)}  (L{level})  {flag}")
    print()

    for sr in result["steps"]:
        v = sr["verdict"]
        if v == "REDUNDANT":
            marker = _color(f"  [REDUNDANT  {sr['confidence']:6s}]", RED)
        elif v == "NECESSARY":
            marker = _color(f"  [necessary  {sr['confidence']:6s}]", GREEN)
        elif v == "DRY_RUN":
            marker = _color(f"  [dry-run            ]", YELLOW)
        else:
            marker = _color(f"  [ERROR              ]", YELLOW)

        step_label = _color(f"Step {sr['step_num']}", BOLD)
        print(f"{marker}  {step_label}  {sr['step_text'][:90]}")
        if sr["reason"] and v != "DRY_RUN":
            print(f"             {_color(sr['reason'], DIM)}")


def print_summary(results: list[dict]) -> None:
    flagged = [r for r in results if r["any_redundant"]]
    print(f"\n{'═'*72}")
    print(f"{_color('MINIMALITY CHECK SUMMARY', BOLD)}")
    print(f"{'═'*72}")
    print(f"  Items checked : {len(results)}")
    print(f"  Clean         : {len(results) - len(flagged)}")
    print(f"  Flagged       : {_color(str(len(flagged)), RED + BOLD if flagged else GREEN)}")
    if flagged:
        print()
        print(f"  {_color('Items requiring human review (sorted by level):', BOLD)}")
        for r in sorted(flagged, key=lambda x: -x["conflict_level"]):
            redundant_steps = [s["step_num"] for s in r["steps"] if s["skippable"]]
            print(f"    {r['id']:35s}  L{r['conflict_level']}  steps: {redundant_steps}")
    print()


# ── I/O helpers ───────────────────────────────────────────────────────────────

def _load_existing_audit() -> dict[str, dict]:
    """Load existing audit file so we can skip already-reviewed items."""
    if AUDIT_PATH.exists():
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        return {entry["id"]: entry for entry in data}
    return {}


def _save_audit(results: list[dict]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Merge with any existing entries (preserve human dispositions)
    existing = _load_existing_audit()
    for r in results:
        existing[r["id"]] = r
    ordered = sorted(existing.values(), key=lambda x: (x["conflict_level"], x["id"]))
    AUDIT_PATH.write_text(
        json.dumps(ordered, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Audit written → {AUDIT_PATH}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="R-1.4: Check reasoning chain minimality for L3–L5 conflict items."
    )
    parser.add_argument("--domains", nargs="+", default=None, metavar="DOMAIN",
                        help="Domains to check (default: all)")
    parser.add_argument("--levels", nargs="+", type=int, default=[5, 4, 3],
                        metavar="N", help="Conflict levels to check (default: 5 4 3)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Claude model for skip-tests (default: {DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print formatted chains only — no API calls")
    parser.add_argument("--force", action="store_true",
                        help="Re-check items that already have an audit entry")
    args = parser.parse_args()

    domains = args.domains or DOMAINS
    levels  = set(args.levels)

    # Load items
    items = []
    for domain in domains:
        path = DATA_DIR / domain / "v1.json"
        if not path.exists():
            print(f"  [warn] not found: {path}", file=sys.stderr)
            continue
        for item in json.loads(path.read_text(encoding="utf-8")):
            if (item["label"]["verdict"] == "conflict"
                    and item.get("conflict_level") in levels):
                items.append(item)

    # Sort L5 → L4 → L3 (highest LW-F1 weight first)
    items.sort(key=lambda x: (-x["conflict_level"], x["id"]))

    existing = _load_existing_audit()
    if not args.force:
        skip_ids = {iid for iid, entry in existing.items()
                    if entry.get("disposition") != "PENDING_HUMAN_REVIEW"}
        before = len(items)
        items = [i for i in items if i["id"] not in skip_ids]
        if before != len(items):
            print(f"  Skipping {before - len(items)} already-reviewed item(s). "
                  f"Use --force to re-check.\n")

    if not items:
        print("Nothing to check.")
        return

    # Set up Anthropic client (unless dry-run)
    client = None
    if not args.dry_run:
        try:
            import anthropic
        except ImportError:
            sys.exit("anthropic package not installed. Run: pip install anthropic")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            sys.exit("ANTHROPIC_API_KEY environment variable not set.")
        client = anthropic.Anthropic(api_key=api_key)

    mode = "DRY RUN" if args.dry_run else f"model={args.model}"
    print(f"\nR-1.4 Minimality Check  [{mode}]")
    print(f"Checking {len(items)} item(s) across levels {sorted(levels, reverse=True)}\n")

    results = []
    for item in items:
        print(f"  checking {item['id']} …", end="", flush=True)
        result = check_item(item, client, args.model, args.dry_run)
        results.append(result)
        status = _color("FLAGGED", RED) if result["any_redundant"] else _color("ok", GREEN)
        print(f"\r  {item['id']:40s} {status}")

    # Print detailed report
    for r in results:
        print_item_report(r)

    print_summary(results)
    _save_audit(results)


if __name__ == "__main__":
    main()
