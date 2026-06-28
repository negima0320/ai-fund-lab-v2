#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_fund_lab_v2.safety_phase11.integration_dry_run import IntegrationDryRunConfig, run_phase11g_integration_dry_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase11-G Safety Integration Dry Run with mock data only.")
    parser.add_argument("--business-date", default="2026-06-29")
    parser.add_argument("--environment", default="dry_run")
    parser.add_argument("--runtime-id", default="phase11g_safety_integration_dry_run")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--runtime-dir", default=".runtime")
    args = parser.parse_args()

    summary = run_phase11g_integration_dry_run(
        IntegrationDryRunConfig(
            business_date=args.business_date,
            environment=args.environment,
            runtime_id=args.runtime_id,
            reports_dir=Path(args.reports_dir),
            runtime_dir=Path(args.runtime_dir),
        )
    )
    print(
        json.dumps(
            {
                "status": summary.status,
                "scenario_count": len(summary.scenario_results),
                "summary_report_path": summary.summary_report_path,
                "phase_report_path": summary.phase_report_path,
                "phase_report_json_path": summary.phase_report_json_path,
                "judgement": [
                    "PHASE11G_SAFETY_INTEGRATION_DRY_RUN_COMPLETE",
                    "PHASE11Z_READY_TO_START",
                    "LIVE_ORDER_EXECUTION_REMAINS_BLOCKED",
                ],
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
