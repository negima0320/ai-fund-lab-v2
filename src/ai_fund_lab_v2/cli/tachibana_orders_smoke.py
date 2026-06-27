from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.broker.tachibana_orders_smoke import run_tachibana_orders_smoke


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tachibana demo orders read-only smoke.")
    parser.add_argument("--reports-dir", default="reports/phase_reports", help="Directory for the smoke result JSON.")
    parser.add_argument(
        "--report-filename",
        default="phase10g_tachibana_orders_smoke_result.json",
        help="Smoke result JSON filename.",
    )
    parser.add_argument("--source", default="phase10g_orders_readonly_smoke", help="Sanitized report source label.")
    parser.add_argument(
        "--run-demo-orders",
        action="store_true",
        help="Explicitly allow Tachibana demo login/orders/logout. Requires TACHIBANA_API_READONLY_SMOKE_ENABLED=true.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_tachibana_orders_smoke(
        reports_dir=Path(args.reports_dir),
        run_enabled=args.run_demo_orders,
        report_filename=args.report_filename,
        source=args.source,
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
    return 0 if result.status in {"SKIPPED", "PASS", "PASS_WITH_LOGOUT_WARNING"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
