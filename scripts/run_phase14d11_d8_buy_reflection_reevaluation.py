#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.broker.phase14d11_buy_reflection_reevaluation import run_phase14d11_d8_buy_reflection_reevaluation  # noqa: E402
from ai_fund_lab_v2.broker.settings import load_broker_settings  # noqa: E402


def main() -> int:
    settings = load_broker_settings()
    symbol = os.environ.get("PHASE14D11_ISSUE_CODE", "7203").strip()
    quantity = float(os.environ.get("PHASE14D11_QUANTITY", "100"))
    run_readonly = os.environ.get("PHASE14D11_RUN_READONLY", "true").strip().lower() in {"1", "true", "yes", "y", "on"}
    result = run_phase14d11_d8_buy_reflection_reevaluation(
        root=PROJECT_ROOT / ".runtime" / "phase14d11",
        docs_report_path=PROJECT_ROOT / "docs" / "phase_reports" / "phase14_d11_d8_buy_reflection_reevaluation.md",
        json_report_path=PROJECT_ROOT / "reports" / "phase_reports" / "phase14_d11_d8_buy_reflection_reevaluation.json",
        settings=settings,
        target_issue_code=symbol,
        target_quantity=quantity,
        run_readonly=run_readonly,
    )
    print(result.final_decision)
    return 0 if result.final_decision == "PHASE14D11_D8_BUY_REFLECTION_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
