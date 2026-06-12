#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_quality.phase1_report import write_phase1_completion_report


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)
    docs_path, runtime_path = write_phase1_completion_report(paths, PROJECT_ROOT)
    print(f"docs_report={docs_path}")
    print(f"runtime_report={runtime_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write Phase1 completion handoff report.")
    parser.add_argument("--runtime-dir", type=Path)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
