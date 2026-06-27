from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping
from ai_fund_lab_v2.broker.tachibana_account_smoke import run_tachibana_account_balance_smoke
from ai_fund_lab_v2.broker.tachibana_account_smoke import run_tachibana_account_error_reveal
from ai_fund_lab_v2.broker.tachibana_account_smoke import run_tachibana_account_transport_diagnosis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tachibana demo account/balance read-only smoke.")
    parser.add_argument("--reports-dir", default="reports/phase_reports", help="Directory for the smoke result JSON.")
    parser.add_argument(
        "--report-filename",
        default="phase10e_tachibana_account_balance_smoke_result.json",
        help="Smoke result JSON filename.",
    )
    parser.add_argument("--source", default="phase10e_account_balance_readonly_smoke", help="Sanitized report source label.")
    parser.add_argument(
        "--run-demo-account-balance",
        action="store_true",
        help="Explicitly allow Tachibana demo login/account/balance/logout. Requires TACHIBANA_API_READONLY_SMOKE_ENABLED=true.",
    )
    parser.add_argument(
        "--run-demo-account-transport-diagnosis",
        action="store_true",
        help="Explicitly allow Tachibana demo account/balance POST transport compatibility diagnosis. Requires TACHIBANA_API_READONLY_SMOKE_ENABLED=true.",
    )
    parser.add_argument(
        "--run-demo-account-error-reveal",
        action="store_true",
        help="Explicitly allow Tachibana demo account/balance p_errno/p_err reveal. Requires TACHIBANA_API_READONLY_SMOKE_ENABLED=true.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.run_demo_account_error_reveal:
        result = run_tachibana_account_error_reveal(
            reports_dir=Path(args.reports_dir),
            run_enabled=True,
            report_filename=args.report_filename,
            source=args.source,
        )
    elif args.run_demo_account_transport_diagnosis:
        result = run_tachibana_account_transport_diagnosis(
            reports_dir=Path(args.reports_dir),
            run_enabled=True,
            report_filename=args.report_filename,
            source=args.source,
        )
    else:
        result = run_tachibana_account_balance_smoke(
            reports_dir=Path(args.reports_dir),
            run_enabled=args.run_demo_account_balance,
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
