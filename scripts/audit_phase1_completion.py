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
from ai_fund_lab_v2.data_quality.phase1_audit import audit_phase1_completion, render_audit_markdown, save_phase1_audit


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)
    report = audit_phase1_completion(paths, PROJECT_ROOT)
    json_path, markdown_path = save_phase1_audit(report, paths)
    if args.output == "json":
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(render_audit_markdown(report))
    print(f"json_report={json_path}")
    print(f"markdown_report={markdown_path}")
    return 0 if report.status in ("OK", "WARNING") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit AI Fund Lab vNext Phase1 completion.")
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--output", choices=("markdown", "json"), default="markdown")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
