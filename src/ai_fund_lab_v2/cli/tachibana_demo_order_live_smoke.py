from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.broker.tachibana_demo_order_smoke import run_tachibana_demo_order_live_smoke_foundation
from ai_fund_lab_v2.runtime import OrderSide


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare Tachibana demo order live smoke foundation.")
    parser.add_argument("--reports-dir", default="reports/phase_reports", help="Directory for the smoke result JSON.")
    parser.add_argument(
        "--report-filename",
        default="phase10u_tachibana_demo_order_live_smoke_foundation_result.json",
        help="Smoke foundation result JSON filename.",
    )
    parser.add_argument("--source", default="phase10u_demo_order_live_smoke_foundation", help="Sanitized report source label.")
    parser.add_argument("--run-demo-order-live-smoke", action="store_true", help="Explicitly run demo order live smoke foundation.")
    parser.add_argument("--dry-run", action="store_true", help="Phase10-U only supports dry-run readiness.")
    parser.add_argument("--approval-id", default="phase10u_demo_order_dry_run", help="Approval id for dry-run scope.")
    parser.add_argument("--issue-code", default="7203", help="Issue code for dry-run request shape.")
    parser.add_argument("--side", choices=["BUY", "SELL"], default="BUY", help="Order side for dry-run request shape.")
    parser.add_argument("--quantity", default="100", help="Quantity for dry-run request shape.")
    parser.add_argument("--limit-price", default="2000", help="Limit price for dry-run request shape.")
    parser.add_argument("--max-notional", default="250000", help="Approval max notional.")
    parser.add_argument("--approval-expires-at", default="", help="UTC ISO timestamp for approval expiry.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    expires_at = datetime.fromisoformat(args.approval_expires_at).astimezone(timezone.utc) if args.approval_expires_at else None
    result = run_tachibana_demo_order_live_smoke_foundation(
        reports_dir=Path(args.reports_dir),
        run_enabled=args.run_demo_order_live_smoke,
        dry_run=args.dry_run,
        report_filename=args.report_filename,
        source=args.source,
        approval_id=args.approval_id,
        issue_code=args.issue_code,
        side=OrderSide(args.side),
        quantity=Decimal(args.quantity),
        limit_price=Decimal(args.limit_price),
        max_notional=Decimal(args.max_notional),
        approval_expires_at=expires_at,
    )
    output = sanitize_mapping(
        {
            "status": result.status,
            "executed": result.executed,
            "report_path": str(result.report_path),
            "message": result.message,
        }
    )
    print(json.dumps(output, ensure_ascii=True, sort_keys=True))
    return 0 if result.status in {"SKIPPED", "DRY_RUN_READY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
