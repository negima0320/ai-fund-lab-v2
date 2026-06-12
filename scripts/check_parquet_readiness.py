#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_quality.parquet_readiness import check_parquet_readiness


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    paths = settings.runtime_paths
    if args.runtime_dir:
        paths = replace(paths, runtime_dir=args.runtime_dir)
    result = check_parquet_readiness(paths)
    rendered = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    print(rendered)
    report_dir = paths.reports / "parquet_readiness"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"parquet_readiness_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    report_path.write_text(rendered, encoding="utf-8")
    print(f"report={report_path}")
    return 0 if result.status == "READY" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check whether Parquet is ready to become the default raw format.")
    parser.add_argument("--runtime-dir", type=Path)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
