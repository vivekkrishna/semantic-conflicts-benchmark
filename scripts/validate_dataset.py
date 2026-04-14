#!/usr/bin/env python3
"""CLI wrapper for the dataset validator (R-1.2).

Usage:
    python scripts/validate_dataset.py                    # all domains
    python scripts/validate_dataset.py --domains philosophy software
    python scripts/validate_dataset.py --data-dir data/
    python scripts/validate_dataset.py --strict           # exit 1 if any errors found
"""

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark.evaluator import DOMAINS
from benchmark.validator import validate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate dataset items against the benchmark schema."
    )
    parser.add_argument(
        "--data-dir", default="data/", help="Path to data directory (default: data/)"
    )
    parser.add_argument(
        "--domains", nargs="+", default=None, metavar="DOMAIN",
        help=f"Domains to validate (default: all). Choices: {DOMAINS}",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit with code 1 if any validation errors are found.",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    domains = args.domains or DOMAINS

    invalid_domains = [d for d in domains if d not in DOMAINS]
    if invalid_domains:
        sys.exit(f"Unknown domain(s): {invalid_domains}. Valid: {DOMAINS}")

    # Load items
    items = []
    for domain in domains:
        path = data_dir / domain / "v1.json"
        if not path.exists():
            print(f"  [warn] not found: {path}", file=sys.stderr)
            continue
        items.extend(json.loads(path.read_text(encoding="utf-8")))

    if not items:
        sys.exit(f"No items found under {data_dir}")

    print(f"Validating {len(items)} items across {len(domains)} domain(s)...\n")

    errors_by_id = validate_dataset(items)

    if not errors_by_id:
        print(f"  All {len(items)} items passed validation.")
        return

    # Group by domain for readable output
    by_domain: dict[str, list] = {}
    for item_id, errors in sorted(errors_by_id.items()):
        domain = item_id.split("_")[0]
        by_domain.setdefault(domain, []).append((item_id, errors))

    total_errors = sum(len(e) for e in errors_by_id.values())
    print(f"  Found {total_errors} error(s) across {len(errors_by_id)} item(s):\n")

    for domain in sorted(by_domain):
        print(f"  [{domain}]")
        for item_id, errors in by_domain[domain]:
            for err in errors:
                print(f"    {item_id}  [{err.field}]  {err.message}")
        print()

    if args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
