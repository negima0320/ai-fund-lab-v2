#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_fund_lab_v2.safety_phase11.integrated_backtest_audit import (
    AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER,
    AUDIT_PROFILE_NORMAL_MARKET,
    AUDIT_PROFILE_STRESS_INJECTION,
    full_5y_config,
    run_integrated_backtest_audit,
    smoke_1y_config,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase11-Z integrated safety backtest audit without external connections.")
    parser.add_argument("--period", choices=("smoke", "full", "all"), default="smoke")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--docs-dir", default=None)
    parser.add_argument("--max-days", type=int, default=None)
    parser.add_argument(
        "--profile",
        choices=(AUDIT_PROFILE_NORMAL_MARKET, AUDIT_PROFILE_STRESS_INJECTION, AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER),
        default=AUDIT_PROFILE_NORMAL_MARKET,
    )
    parser.add_argument("--output-subdir", default=None)
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    docs_dir = Path(args.docs_dir) if args.docs_dir else None
    results = []
    if args.period in {"smoke", "all"}:
        smoke_config = smoke_1y_config(reports_dir=reports_dir)
        if docs_dir is not None or args.max_days is not None or args.profile != AUDIT_PROFILE_NORMAL_MARKET or args.output_subdir:
            smoke_config = _replace_config(
                smoke_config,
                docs_dir=docs_dir,
                max_days=args.max_days,
                audit_profile=args.profile,
                output_subdir=args.output_subdir,
            )
        smoke = run_integrated_backtest_audit(smoke_config)
        results.append(_summary(smoke))
        if args.period == "all" and smoke.status != "PASS":
            print(json.dumps({"status": "STOPPED_AFTER_SMOKE", "results": results}, ensure_ascii=True, indent=2, sort_keys=True))
            return 1
    if args.period in {"full", "all"}:
        full_config = full_5y_config(reports_dir=reports_dir)
        if docs_dir is not None or args.max_days is not None or args.profile != AUDIT_PROFILE_NORMAL_MARKET or args.output_subdir:
            full_config = _replace_config(
                full_config,
                docs_dir=docs_dir,
                max_days=args.max_days,
                audit_profile=args.profile,
                output_subdir=args.output_subdir,
            )
        full = run_integrated_backtest_audit(full_config)
        results.append(_summary(full))

    status = "PASS" if all(result["status"] == "PASS" for result in results) else "FAIL"
    print(json.dumps({"status": status, "results": results}, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


def _summary(result) -> dict:
    return {
        "period_id": result.period_id,
        "status": result.status,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "business_day_count": result.business_day_count,
        "audit_profile": result.safety_behavior.get("audit_profile"),
        "summary_path": result.summary_path,
        "phase_report_path": result.phase_report_path,
        "phase_report_json_path": result.phase_report_json_path,
        "judgement": result.performance and ("PHASE11Z_FULL_5Y_READY_TO_START" if result.period_id == "smoke_1y" else "PHASE11_COMPLETE_CANDIDATE"),
    }


def _replace_config(config, *, docs_dir, max_days, audit_profile, output_subdir):
    from dataclasses import replace

    updates = {}
    if docs_dir is not None:
        updates["docs_dir"] = docs_dir
    if max_days is not None:
        updates["max_days"] = max_days
    if audit_profile is not None:
        updates["audit_profile"] = audit_profile
    if output_subdir is not None:
        updates["output_subdir"] = output_subdir
    return replace(config, **updates)


if __name__ == "__main__":
    raise SystemExit(main())
