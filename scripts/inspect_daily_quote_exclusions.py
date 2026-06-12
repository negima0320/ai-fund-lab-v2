#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_quality.daily_quote_exclusions import inspect_daily_quote_exclusions, render_exclusion_markdown, save_exclusion_report


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)
    paths.ensure_base_dirs()

    report = inspect_daily_quote_exclusions(paths, input_format=args.input_format, limit=args.limit)
    if args.output == "json":
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(render_exclusion_markdown(report))
    if args.save_report:
        json_path, markdown_path = save_exclusion_report(report, paths, "both")
        print(f"json_report={json_path}")
        print(f"markdown_report={markdown_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect daily quote records excluded from normalized raw.")
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--input-format", choices=("auto", "jsonl", "parquet"), default="auto")
    parser.add_argument("--output", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--save-report", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
