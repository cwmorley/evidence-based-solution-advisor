"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import recommend
from .diagnostics import render_diagnostics, score_diagnostics
from .io import AdvisorDataError, dump_json, load_json
from .report import render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solution-advisor",
        description=(
            "Turn structured discovery data into explainable product, configuration, "
            "and service recommendations."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    recommend_parser = subparsers.add_parser("recommend", help="Evaluate an intake")
    recommend_parser.add_argument("intake", type=Path, help="Path to an intake JSON file")
    recommend_parser.add_argument(
        "--knowledge",
        type=Path,
        default=Path("knowledge/workstations"),
        help="Knowledge-store directory (default: knowledge/workstations)",
    )
    recommend_parser.add_argument("--json-out", type=Path, help="Write full JSON output")
    recommend_parser.add_argument("--markdown-out", type=Path, help="Write Markdown report")
    recommend_parser.add_argument(
        "--format", choices=("markdown", "json"), default="markdown", help="Console format"
    )
    diagnostics = subparsers.add_parser("score-diagnostics", help="Inspect score variation across viable candidates")
    diagnostics.add_argument("intakes", nargs="+", type=Path)
    diagnostics.add_argument("--knowledge", type=Path, default=Path("knowledge/workstations"))
    diagnostics.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "score-diagnostics":
            result = score_diagnostics([load_json(path) for path in args.intakes], args.knowledge)
            print(json.dumps(result, indent=2) if args.format == "json" else render_diagnostics(result))
            return 0
        if args.command == "recommend":
            result = recommend(load_json(args.intake), args.knowledge)
            markdown = render_markdown(result)
            if args.json_out:
                dump_json(result, args.json_out)
            if args.markdown_out:
                args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
                args.markdown_out.write_text(markdown, encoding="utf-8")
            if args.format == "json":
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(markdown)
            return 0 if result["recommendation"] else 2
    except (AdvisorDataError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1
