#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.broker.runtime_v2_demo_submit_adapter import RuntimeV2TachibanaDemoSubmitAdapter  # noqa: E402
from ai_fund_lab_v2.broker.settings import load_broker_settings  # noqa: E402
from ai_fund_lab_v2.broker.phase14d5_pure_retest import run_phase14d5_pure_runtime_v2_demo_buy_retest  # noqa: E402


def main() -> int:
    settings = load_broker_settings()
    symbol = os.environ.get("PHASE14D5_ISSUE_CODE", "7203").strip()
    quantity = float(os.environ.get("PHASE14D5_QUANTITY", "100"))
    estimated_price = float(os.environ.get("PHASE14D5_ESTIMATED_PRICE", "3000"))
    max_order_amount = float(os.environ.get("PHASE14D5_MAX_ORDER_AMOUNT", "500000"))
    result = run_phase14d5_pure_runtime_v2_demo_buy_retest(
        root=PROJECT_ROOT / ".runtime" / "phase14d5",
        docs_report_path=PROJECT_ROOT / "docs" / "phase_reports" / "phase14_d5_pure_runtime_v2_demo_buy_retest.md",
        json_report_path=PROJECT_ROOT / "reports" / "phase_reports" / "phase14_d5_pure_runtime_v2_demo_buy_retest.json",
        adapter=RuntimeV2TachibanaDemoSubmitAdapter(settings=settings, dry_run=False),
        settings=settings,
        symbol=symbol,
        quantity=quantity,
        estimated_price=estimated_price,
        max_order_amount=max_order_amount,
        run_submit=True,
    )
    print(result.final_decision)
    return 0 if result.final_decision == "PHASE14D5_PURE_RUNTIME_V2_DEMO_BUY_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
