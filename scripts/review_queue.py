#!/usr/bin/env python3
"""CLI for querying and updating data/review_queue.json.

Usage:
    python scripts/review_queue.py                     # show all open items
    python scripts/review_queue.py --status open       # filter by status
    python scripts/review_queue.py --type minimality   # filter by flag type
    python scripts/review_queue.py --domain philosophy # filter by domain prefix
    python scripts/review_queue.py --level 5           # filter by conflict level
    python scripts/review_queue.py --summary           # counts by type and status
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
QUEUE_PATH = ROOT / "data" / "review_queue.json"


def load_queue() -> list[dict]:
    data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    return data["items"]


def extract_level(item_id: str) -> str | None:
    """Extract level number from item_id like 'philosophy_L4_002' → '4'."""
    parts = item_id.split("_")
    for part in parts:
        if part.startswith("L") and part[1:].isdigit():
            return part[1:]
    return None


def extract_domain(item_id: str) -> str:
    return item_id.split("_")[0]


def print_item(item: dict) -> None:
    status_badge = {
        "open":      "[OPEN]     ",
        "in_review": "[REVIEWING]",
        "resolved":  "[RESOLVED] ",
        "wont_fix":  "[WONT FIX] ",
    }.get(item["status"], f"[{item['status'].upper()}]")

    print(f"\n{status_badge}  {item['item_id']}  ({item['flag_type']})")
    print(f"  Flagged by: {item['flagged_by']}  |  Date: {item['flagged_date']}")
    print(f"  {item['description']}")
    if item.get("resolution_note"):
        print(f"  Resolution ({item['resolved_by']}, {item['resolved_date']}): {item['resolution_note']}")


def summary(items: list[dict]) -> None:
    from collections import Counter

    by_status = Counter(i["status"] for i in items)
    by_type   = Counter(i["flag_type"] for i in items)
    by_domain = Counter(extract_domain(i["item_id"]) for i in items)
    by_level  = Counter(extract_level(i["item_id"]) for i in items if extract_level(i["item_id"]))

    print(f"\nReview queue summary — {len(items)} total items\n")

    print("By status:")
    for status, count in sorted(by_status.items()):
        print(f"  {status:<12} {count}")

    print("\nBy flag type:")
    for ftype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {ftype:<25} {count}")

    print("\nBy domain:")
    for domain, count in sorted(by_domain.items()):
        print(f"  {domain:<15} {count}")

    print("\nBy conflict level:")
    for level in sorted(by_level.keys(), key=lambda x: int(x)):
        print(f"  L{level:<14} {by_level[level]}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the dataset review queue.")
    parser.add_argument("--status", choices=["open", "in_review", "resolved", "wont_fix"],
                        help="Filter by status")
    parser.add_argument("--type", dest="flag_type",
                        help="Filter by flag type (e.g. minimality, modal_rewrite)")
    parser.add_argument("--domain", help="Filter by domain prefix (e.g. philosophy, law)")
    parser.add_argument("--level", type=int, help="Filter by conflict level (0–5)")
    parser.add_argument("--summary", action="store_true", help="Show counts by type/status")
    args = parser.parse_args()

    items = load_queue()

    if args.status:
        items = [i for i in items if i["status"] == args.status]
    if args.flag_type:
        items = [i for i in items if i["flag_type"] == args.flag_type]
    if args.domain:
        items = [i for i in items if extract_domain(i["item_id"]) == args.domain]
    if args.level is not None:
        items = [i for i in items if extract_level(i["item_id"]) == str(args.level)]

    if args.summary:
        summary(items)
        return

    if not items:
        print("No items match the given filters.")
        return

    for item in items:
        print_item(item)

    print(f"\n{len(items)} item(s) shown.")


if __name__ == "__main__":
    main()
