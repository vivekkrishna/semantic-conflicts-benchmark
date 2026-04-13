"""CLI entry point for the semantic-conflicts-benchmark.

Installed as `scbench` via pyproject.toml.  Also runnable as:
    python -m benchmark.run

Usage examples:
    # Built-in adapter:
    scbench --adapter anthropic --model claude-haiku-4-5-20251001

    # Specific domains only:
    scbench --adapter openai --model gpt-4o --domains philosophy software

    # Custom adapter class (see examples/custom_adapter.py):
    scbench --adapter-class examples.custom_adapter.OllamaAdapter

    # Full options:
    scbench --adapter anthropic --model claude-haiku-4-5-20251001 \\
            --domains all --data-dir data/ \\
            --output results/my_run.json \\
            --leaderboard results/leaderboard.csv \\
            --verbose
"""

import argparse
import importlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark.evaluator import DOMAINS, Evaluator
from benchmark.reporter import print_console, write_json, write_leaderboard, write_markdown


BUILTIN_ADAPTERS = {
    "openai":     ("benchmark.adapters.openai_adapter",    "OpenAIAdapter"),
    "anthropic":  ("benchmark.adapters.anthropic_adapter", "AnthropicAdapter"),
    "hf":         ("benchmark.adapters.hf_adapter",        "HuggingFaceAdapter"),
}


def _load_adapter(args: argparse.Namespace):
    if args.adapter_class:
        module_path, _, class_name = args.adapter_class.rpartition(".")
        module = importlib.import_module(module_path)
        cls    = getattr(module, class_name)
        return cls()

    if args.adapter not in BUILTIN_ADAPTERS:
        sys.exit(
            f"Unknown adapter '{args.adapter}'. "
            f"Choose from {list(BUILTIN_ADAPTERS)} or use --adapter-class."
        )

    module_path, class_name = BUILTIN_ADAPTERS[args.adapter]
    module = importlib.import_module(module_path)
    cls    = getattr(module, class_name)

    kwargs = {}
    if args.model:
        kwargs["model"] = args.model
    return cls(**kwargs)


def _default_output_path(model_name: str) -> str:
    ts   = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = model_name.replace("/", "_").replace(":", "-")
    return f"results/{safe}_{ts}.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the semantic-conflicts-benchmark against a language model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    adapter_group = parser.add_mutually_exclusive_group(required=True)
    adapter_group.add_argument(
        "--adapter", choices=list(BUILTIN_ADAPTERS),
        help="Built-in adapter name.",
    )
    adapter_group.add_argument(
        "--adapter-class",
        metavar="MODULE.ClassName",
        help="Dotted import path to a custom ModelAdapter subclass.",
    )

    parser.add_argument("--model",      default=None,      help="Model name passed to the adapter constructor.")
    parser.add_argument("--domains",    nargs="+",         default=None,
                        metavar="DOMAIN",
                        help=f"Domains to evaluate. Choices: {DOMAINS} (default: all).")
    parser.add_argument("--data-dir",   default="data/",   help="Path to data directory (default: data/).")
    parser.add_argument("--output",     default=None,      help="Path for JSON results file.")
    parser.add_argument("--leaderboard",default="results/leaderboard.csv",
                        help="Path for leaderboard CSV (appended to).")
    parser.add_argument("--no-markdown",action="store_true",
                        help="Skip writing the Markdown report.")
    parser.add_argument("--verbose",    action="store_true",
                        help="Print each item as it is evaluated.")

    args = parser.parse_args()

    # Validate domains
    requested_domains = args.domains or DOMAINS
    invalid = [d for d in requested_domains if d not in DOMAINS]
    if invalid:
        sys.exit(f"Unknown domain(s): {invalid}. Valid: {DOMAINS}")

    adapter = _load_adapter(args)
    print(f"\nRunning benchmark with model: {adapter.name}")
    print(f"Domains: {requested_domains}")
    print(f"Data dir: {args.data_dir}\n")

    evaluator = Evaluator(
        adapter=adapter,
        domains=requested_domains,
        data_dir=args.data_dir,
        verbose=args.verbose,
    )
    results = evaluator.run()

    # Determine output paths
    json_path = args.output or _default_output_path(adapter.name)
    md_path   = json_path.replace(".json", ".md")

    # Write all outputs
    print_console(results)
    write_json(results, json_path)
    if not args.no_markdown:
        write_markdown(results, md_path)
    write_leaderboard(results, args.leaderboard)


if __name__ == "__main__":
    main()
