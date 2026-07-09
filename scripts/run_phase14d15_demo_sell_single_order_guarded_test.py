#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.broker.phase14d15_demo_sell_test import run_phase14d15_demo_sell_single_order_guarded_test  # noqa: E402
from ai_fund_lab_v2.broker.runtime_v2_demo_submit_adapter import RuntimeV2TachibanaDemoSubmitAdapter  # noqa: E402
from ai_fund_lab_v2.broker.settings import load_broker_settings  # noqa: E402


def main() -> int:
    settings = load_broker_settings()
    symbol = os.environ.get("PHASE14D15_ISSUE_CODE", "7203").strip()
    quantity = float(os.environ.get("PHASE14D15_QUANTITY", "100"))
    estimated_price = float(os.environ.get("PHASE14D15_ESTIMATED_PRICE", "2941"))
    max_order_amount = float(os.environ.get("PHASE14D15_MAX_ORDER_AMOUNT", "500000"))
    result = run_phase14d15_demo_sell_single_order_guarded_test(
        root=PROJECT_ROOT / ".runtime" / "phase14d15",
        docs_report_path=PROJECT_ROOT / "docs" / "phase_reports" / "phase14_d15_demo_sell_single_order_guarded_test.md",
        json_report_path=PROJECT_ROOT / "reports" / "phase_reports" / "phase14_d15_demo_sell_single_order_guarded_test.json",
        adapter=RuntimeV2TachibanaDemoSubmitAdapter(settings=settings, dry_run=False),
        settings=settings,
        symbol=symbol,
        quantity=quantity,
        estimated_price=estimated_price,
        max_order_amount=max_order_amount,
        run_submit=True,
    )
    print(result.final_decision)
    return 0 if result.final_decision == "PHASE14D15_DEMO_SELL_SINGLE_ORDER_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
