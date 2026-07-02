#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.operations.operations import (
    DEFAULT_OPERATION_ROOT,
    run_approval_prepare,
    run_audit,
    run_daily_plan,
    run_daily_report,
    run_demo_special_fill_simulation,
    run_demo_submit,
    run_fill_monitor,
    run_market_refresh,
    run_preflight,
    run_reconcile,
    run_safety_monitor,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full automatic Demo daily operation.")
    parser.add_argument("--trade-date", required=True)
    parser.add_argument("--root", default=str(DEFAULT_OPERATION_ROOT))
    parser.add_argument("--allow-api-fetch", action="store_true")
    parser.add_argument("--refresh-broker-readonly", action="store_true")
    parser.add_argument("--execute-demo-order", action="store_true")
    parser.add_argument("--second-password-present", action="store_true")
    parser.add_argument("--enable-special-fill-simulation", action="store_true")
    parser.add_argument("--auto-approval-max-notional", default=None)
    args = parser.parse_args()
    root = Path(args.root)
    results = []
    results.append(run_market_refresh(trade_date=args.trade_date, root=root, allow_api_fetch=args.allow_api_fetch))
    results.append(run_daily_plan(trade_date=args.trade_date, root=root))
    results.append(
        run_approval_prepare(
            trade_date=args.trade_date,
            root=root,
            auto_demo_approval=True,
            approver_label="demo_auto_approval",
            max_notional=Decimal(args.auto_approval_max_notional) if args.auto_approval_max_notional is not None else None,
        )
    )
    results.append(run_preflight(trade_date=args.trade_date, root=root, refresh_broker_readonly=args.refresh_broker_readonly))
    results.append(
        run_demo_submit(
            trade_date=args.trade_date,
            root=root,
            execute_demo_order=args.execute_demo_order,
            second_password_present=args.second_password_present,
        )
    )
    results.append(run_fill_monitor(trade_date=args.trade_date, root=root))
    if args.enable_special_fill_simulation:
        results.append(
            run_demo_special_fill_simulation(
                trade_date=args.trade_date,
                root=root,
                demo_special_fill_simulation_enabled=True,
            )
        )
        results.append(run_fill_monitor(trade_date=args.trade_date, root=root))
    results.append(run_safety_monitor(trade_date=args.trade_date, root=root))
    results.append(run_reconcile(trade_date=args.trade_date, root=root))
    results.append(run_daily_report(trade_date=args.trade_date, root=root))
    results.append(run_audit(root=root))
    statuses = [str(item.get("status") or "UNKNOWN") for item in results]
    print(" -> ".join(statuses))
    return 0 if all(status in {"PASS", "APPROVED"} for status in statuses) else 2


if __name__ == "__main__":
    raise SystemExit(main())
