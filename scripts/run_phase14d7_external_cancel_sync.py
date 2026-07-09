#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.broker.phase14d7_external_cancel_sync import run_phase14d7_external_cancel_sync  # noqa: E402
from ai_fund_lab_v2.broker.settings import load_broker_settings  # noqa: E402


def main() -> int:
    result = run_phase14d7_external_cancel_sync(
        root=PROJECT_ROOT / ".runtime" / "phase14d7",
        docs_report_path=PROJECT_ROOT / "docs" / "phase_reports" / "phase14_d7_external_cancel_sync.md",
        json_report_path=PROJECT_ROOT / "reports" / "phase_reports" / "phase14_d7_external_cancel_sync.json",
        settings=load_broker_settings(),
        pending_plan_path=PROJECT_ROOT / ".runtime" / "phase14d" / "pending_order_plan" / "pending_order_plan.json",
        target_issue_code="9432",
        target_quantity=100.0,
        run_readonly=True,
    )
    print(result.final_decision)
    return 0 if result.final_decision == "PHASE14D7_BROKER_STATE_SYNC_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
