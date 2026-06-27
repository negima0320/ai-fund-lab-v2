from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.broker.tachibana_broker_snapshot import DEFAULT_SNAPSHOT_PATH, run_tachibana_broker_snapshot
from ai_fund_lab_v2.broker.tachibana_quote_smoke import DEFAULT_QUOTE_SYMBOLS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tachibana demo read-only broker snapshot integration.")
    parser.add_argument("--reports-dir", default="reports/phase_reports", help="Directory for the integration report JSON.")
    parser.add_argument(
        "--report-filename",
        default="phase10j_tachibana_broker_snapshot_integration.json",
        help="Integration report JSON filename.",
    )
    parser.add_argument("--snapshot-path", default=str(DEFAULT_SNAPSHOT_PATH), help="Path for latest broker snapshot JSON.")
    parser.add_argument("--source", default="phase10j_broker_snapshot_integration", help="Sanitized report source label.")
    parser.add_argument("--symbols", default=",".join(DEFAULT_QUOTE_SYMBOLS), help="Comma-separated issue codes; keep small for snapshot smoke.")
    parser.add_argument("--skip-quotes", action="store_true", help="Skip PRICE quote retrieval for portfolio-only verification.")
    parser.add_argument(
        "--run-demo-snapshot",
        action="store_true",
        help="Explicitly allow Tachibana demo read-only broker snapshot. Requires TACHIBANA_API_READONLY_SMOKE_ENABLED=true.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    symbols = tuple(item.strip() for item in args.symbols.split(",") if item.strip())
    result = run_tachibana_broker_snapshot(
        reports_dir=Path(args.reports_dir),
        run_enabled=args.run_demo_snapshot,
        report_filename=args.report_filename,
        snapshot_path=Path(args.snapshot_path),
        source=args.source,
        symbols=symbols,
        include_quotes=not args.skip_quotes,
    )
    output = sanitize_mapping(
        {
            "status": result.status,
            "executed": result.executed,
            "report_path": str(result.report_path),
            "snapshot_path": str(result.snapshot_path),
            "message": result.message,
        }
    )
    print(json.dumps(output, ensure_ascii=True, sort_keys=True))
    return 0 if result.status in {"SKIPPED", "PASS", "PASS_WITH_WARNINGS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
