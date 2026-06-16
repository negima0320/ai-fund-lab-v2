#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.paper_trading.market_data_refresh import run_market_data_refresh


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_market_data_refresh(
        from_date=args.from_date,
        to_date=args.to_date,
        dry_run=args.dry_run,
        allow_api_fetch=args.allow_api_fetch,
        raw_output_root=args.raw_output_root,
        normalized_output_root=args.normalized_output_root,
        manifest_output_root=args.manifest_output_root,
        backup_existing=args.backup_existing,
        fetch_mode=args.fetch_mode,
        markdown_report_path=args.markdown_report_path,
        json_report_path=args.json_report_path,
    )
    print(json.dumps({"status": result.status, "manifest": result.manifest_path, "json": result.json_report_path}, ensure_ascii=False, sort_keys=True))
    return 0 if result.status not in {"FAILED"} else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase9-I market data refresh runner.")
    parser.add_argument("--from-date", required=True)
    parser.add_argument("--to-date", required=True)
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--allow-api-fetch", action="store_true", default=False)
    parser.add_argument("--raw-output-root", type=Path, default=Path(".runtime/data/raw"))
    parser.add_argument("--normalized-output-root", type=Path, default=Path(".runtime/data/raw_normalized"))
    parser.add_argument("--manifest-output-root", type=Path, default=Path(".runtime/phase9/market_data_refresh"))
    parser.add_argument("--backup-existing", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fetch-mode", choices=("range", "per-date"), default="range")
    parser.add_argument("--markdown-report-path", type=Path, default=Path("docs/phase_reports/phase9i_market_data_refresh_report.md"))
    parser.add_argument("--json-report-path", type=Path, default=Path("reports/phase_reports/phase9i_market_data_refresh_report.json"))
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
