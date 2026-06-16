#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_fund_lab_v2.paper_trading.feature_refresh import run_feature_refresh


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase9-J feature freshness audit and refresh runner.")
    parser.add_argument("--target-data-until", required=True)
    parser.add_argument("--execute", action="store_true", help="Generate Phase9 feature artifacts. Default is dry-run audit only.")
    parser.add_argument("--daily-quotes-path", default=None, help="Override canonical normalized daily_quotes path.")
    parser.add_argument("--listed-info-path", default=None, help="Override canonical listed_info path.")
    parser.add_argument("--config-path", default="config/phase9_data_sources.yaml")
    parser.add_argument("--feature-output-root", default=".runtime/phase9/features")
    parser.add_argument("--manifest-root", default=".runtime/phase9/feature_refresh")
    parser.add_argument("--markdown-report-path", default="docs/phase_reports/phase9j_feature_refresh_report.md")
    parser.add_argument("--json-report-path", default="reports/phase_reports/phase9j_feature_refresh_report.json")
    args = parser.parse_args()

    result = run_feature_refresh(
        target_data_until=args.target_data_until,
        dry_run=not args.execute,
        execute=args.execute,
        daily_quotes_path=Path(args.daily_quotes_path) if args.daily_quotes_path else None,
        listed_info_path=Path(args.listed_info_path) if args.listed_info_path else None,
        config_path=Path(args.config_path),
        feature_output_root=Path(args.feature_output_root),
        manifest_root=Path(args.manifest_root),
        markdown_report_path=Path(args.markdown_report_path),
        json_report_path=Path(args.json_report_path),
    )
    print(json.dumps({"status": result.status, "manifest_path": result.manifest_path}, ensure_ascii=False, sort_keys=True))
    return 0 if result.status in {"FEATURES_READY", "FEATURE_REFRESH_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
