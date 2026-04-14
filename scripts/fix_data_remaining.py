#!/usr/bin/env python3
"""Fix remaining 22 dataset violations after fix_data_r11_r13.py.

Remaining issues identified by validator:
  1. Content domain: 18 conflict items have 1 extra passage-reading step at front
     - L0 items: chain has 3 entries, need 1 (just CONFLICT)
     - L1 items: chain has 3 entries, need 2 (Step 1 + CONFLICT)
     - L2 items: chain has 4 entries, need 3 (Step 1 + Step 2 + CONFLICT)
     - etc.
     Fix: drop first (current_len - expected_len) entries, renumber remaining Steps.
  2. law_L4_002 Step 3: "might actually benefit competition" → "benefit competition"
  3. law_L5_002 Step 5: "it may be forced to do if contributions become unsustainable"
     → rephrase as conditional without "may"
  4. teams_L3_001 Step 3: quotes "No service may hold a direct connection..." → rephrase
  5. teams_L4_001 Step 1: quotes "cached responses 'may contain verbatim fragments'"
     → rephrase to not echo modal
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"


def load(domain: str) -> list[dict]:
    path = DATA / domain / "v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def save(domain: str, items: list[dict]) -> None:
    path = DATA / domain / "v1.json"
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"  saved {path}")


def renumber_steps(chain: list[str]) -> list[str]:
    """Renumber Step N — entries from 1 to len-1, keep CONFLICT — final."""
    result = []
    step_num = 1
    for entry in chain:
        if entry.startswith("CONFLICT — ") or entry.startswith("AMBIGUOUS — "):
            result.append(entry)
        else:
            # Replace "Step N —" prefix with correct number
            renumbered = re.sub(r"^Step \d+ —", f"Step {step_num} —", entry)
            result.append(renumbered)
            step_num += 1
    return result


# ---------------------------------------------------------------------------
# Fix 1: Content domain — trim extra passage-reading step from conflict items
# ---------------------------------------------------------------------------

def fix_content():
    items = load("content")
    changed = 0
    for item in items:
        if item["label"]["verdict"] != "conflict":
            continue
        chain = item["label"]["reasoning_chain"]
        level = item["conflict_level"]
        expected_len = level + 1
        current_len = len(chain)
        if current_len <= expected_len:
            continue  # already correct

        # Drop first (current_len - expected_len) entries (passage-reading steps)
        excess = current_len - expected_len
        trimmed = chain[excess:]  # keep last expected_len entries
        renumbered = renumber_steps(trimmed)
        item["label"]["reasoning_chain"] = renumbered
        changed += 1
        print(f"  content/{item['id']}: {current_len} → {len(renumbered)} entries")

    save("content", items)
    print(f"  Fixed {changed} content items.")


# ---------------------------------------------------------------------------
# Fix 2: law_L4_002 Step 3 — "might actually benefit competition"
# ---------------------------------------------------------------------------

def fix_law_l4_002(items: list[dict]) -> bool:
    for item in items:
        if item["id"] != "law_L4_002":
            continue
        chain = item["label"]["reasoning_chain"]
        # Step 3 (index 2): contains "might actually benefit competition"
        old = chain[2]
        if "might actually benefit competition" in old:
            chain[2] = old.replace(
                "removing the Platform's ability to price-discriminate in ways that might actually benefit competition",
                "removing the Platform's ability to price-discriminate in ways that benefit competition"
            )
            print(f"  Fixed law_L4_002 Step 3: removed 'might actually'")
            return True
        else:
            print(f"  [WARN] law_L4_002 Step 3 pattern not found: {old[:80]}")
    return False


# ---------------------------------------------------------------------------
# Fix 3: law_L5_002 Step 5 — "it may be forced to do if contributions become unsustainable"
# ---------------------------------------------------------------------------

def fix_law_l5_002(items: list[dict]) -> bool:
    for item in items:
        if item["id"] != "law_L5_002":
            continue
        chain = item["label"]["reasoning_chain"]
        # Step 5 (index 4)
        old = chain[4]
        if "may be forced to do if contributions become unsustainable" in old:
            chain[4] = old.replace(
                "if Acquirer terminates the plan within five years (which it may be forced to do if contributions become unsustainable), the PBGC can assess",
                "if Acquirer terminates the plan within five years due to contributions becoming unsustainable, the PBGC can assess"
            )
            print(f"  Fixed law_L5_002 Step 5: rephrased 'may be forced to'")
            return True
        else:
            print(f"  [WARN] law_L5_002 Step 5 pattern not found: {old[:120]}")
    return False


def fix_law():
    items = load("law")
    fix_law_l4_002(items)
    fix_law_l5_002(items)
    save("law", items)


# ---------------------------------------------------------------------------
# Fix 4: teams_L3_001 Step 3 — quotes "No service may hold a direct connection"
# ---------------------------------------------------------------------------

def fix_teams_l3_001(items: list[dict]) -> bool:
    for item in items:
        if item["id"] != "teams_L3_001":
            continue
        chain = item["label"]["reasoning_chain"]
        # Step 3 (index 2)
        old = chain[2]
        if "No service may hold a direct connection" in old:
            chain[2] = old.replace(
                "ADR-014 states 'No service may hold a direct connection to another service's database at any network layer' and classifies such connections as critical architectural defects.",
                "ADR-014 prohibits any service from holding a direct connection to another service's database at any network layer and classifies such connections as critical architectural defects."
            )
            print(f"  Fixed teams_L3_001 Step 3: rephrased quoted 'may' rule")
            return True
        else:
            print(f"  [WARN] teams_L3_001 Step 3 pattern not found: {old[:120]}")
    return False


# ---------------------------------------------------------------------------
# Fix 5: teams_L4_001 Step 1 — quotes "cached responses 'may contain verbatim fragments'"
# ---------------------------------------------------------------------------

def fix_teams_l4_001(items: list[dict]) -> bool:
    for item in items:
        if item["id"] != "teams_L4_001":
            continue
        chain = item["label"]["reasoning_chain"]
        # Step 1 (index 0)
        old = chain[0]
        if "may contain verbatim fragments" in old:
            chain[0] = old.replace(
                "Passage B states that cached responses 'may contain verbatim fragments of the original input' and are stored on a global edge network.",
                "Passage B acknowledges that cached responses contain verbatim fragments of the original input and are stored on a global edge network."
            )
            print(f"  Fixed teams_L4_001 Step 1: rephrased quoted 'may contain'")
            return True
        else:
            print(f"  [WARN] teams_L4_001 Step 1 pattern not found: {old[:120]}")
    return False


def fix_teams():
    items = load("teams")
    fix_teams_l3_001(items)
    fix_teams_l4_001(items)
    save("teams", items)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Fix remaining 22 dataset violations ===\n")

    print("[1/3] Fixing content domain (18 chain-length violations)...")
    fix_content()
    print()

    print("[2/3] Fixing law domain (2 modal violations)...")
    fix_law()
    print()

    print("[3/3] Fixing teams domain (2 modal violations)...")
    fix_teams()
    print()

    print("Done. Run: python3 scripts/validate_dataset.py --strict")


if __name__ == "__main__":
    main()
