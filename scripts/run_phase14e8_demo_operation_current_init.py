#!/usr/bin/env python3
"""Initialize Runtime v2 demo operation Current SoT for Phase14-E8."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.runtime_v2.asset.initializer import initialize_demo_operation_current_sot  # noqa: E402
from ai_fund_lab_v2.runtime_v2.current_state.reader import read_current_state  # noqa: E402
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import generate_public_report_from_current  # noqa: E402


def main() -> int:
    business_date = "2026-07-07"
    init_result = initialize_demo_operation_current_sot(
        runtime_root=PROJECT_ROOT / ".runtime",
        business_date=business_date,
        backup_root=PROJECT_ROOT / ".runtime" / "backups" / "phase14e8",
    )
    readback = read_current_state(
        mode="demo",
        environment="demo",
        object_type="persistent_ledger_state",
        base_dir=PROJECT_ROOT,
    )
    report_result = generate_public_report_from_current(
        runtime_root=PROJECT_ROOT / ".runtime",
        runtime_output_dir=PROJECT_ROOT / "reports" / "runtime_v2" / business_date,
        public_output_dir=PROJECT_ROOT / "reports" / "public" / "runtime_v2" / business_date,
        business_date=business_date,
    )
    payload = {
        "business_date": business_date,
        "initialization": init_result,
        "readback": {
            "classification": readback.classification,
            "exists": readback.exists,
            "valid": readback.valid,
            "review_required": readback.review_required,
        },
        "report": {
            "runtime_report_md": report_result["runtime_report_md"],
            "public_report_md": report_result["public_report_md"],
            "latest_md": report_result["latest_md"],
            "redaction_scan": report_result["redaction_scan"],
        },
        "prohibited_actions": {
            "demo_submit_executed": False,
            "broker_api_write_called": False,
            "production_order_executed": False,
            "notification_sent": False,
            "launchd_load_unload": False,
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if readback.classification == "CONFIRMED_EMPTY" else 20


if __name__ == "__main__":
    raise SystemExit(main())
