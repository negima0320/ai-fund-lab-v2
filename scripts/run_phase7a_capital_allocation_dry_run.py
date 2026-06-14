#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.capital_allocation_ai.engine import DEFAULT_OUTPUT_DIR, run_capital_allocation_engine  # noqa: E402
from ai_fund_lab_v2.capital_allocation_ai.schema import Phase7AConfig, PortfolioSnapshot  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase7-A Capital Allocation Engine fixture dry-run.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    fixture_dir = output_dir / "fixture_inputs"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture_opportunity_frame().to_csv(fixture_dir / "opportunities.csv", index=False)
    fixture_holdings_frame().to_csv(fixture_dir / "holdings.csv", index=False)
    fixture_position_signal_frame().to_csv(fixture_dir / "position_signals.csv", index=False)

    result = run_capital_allocation_engine(
        portfolio=fixture_portfolio(),
        opportunity_frame=fixture_opportunity_frame(),
        holdings_frame=fixture_holdings_frame(),
        position_signal_frame=fixture_position_signal_frame(),
        output_dir=output_dir,
        config=Phase7AConfig(),
    )
    print(json.dumps(result["summary"], ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["summary"].get("status") == "OK" else 1


def fixture_portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(target_date="2026-06-15", total_assets=1_000_000.0, cash=500_000.0)


def fixture_opportunity_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-15", "code": "7001", "expected_edge_score": 0.12, "buy_rank": 1, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7002", "expected_edge_score": 0.10, "buy_rank": 2, "downside_risk_score": 0.25, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7003", "expected_edge_score": 0.09, "buy_rank": 3, "downside_risk_score": 0.30, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7004", "expected_edge_score": 0.07, "buy_rank": 4, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7005", "expected_edge_score": 0.06, "buy_rank": 5, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7006", "expected_edge_score": 0.05, "buy_rank": 6, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7101", "expected_edge_score": 0.08, "buy_rank": 8, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7102", "expected_edge_score": 0.04, "buy_rank": 12, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7103", "expected_edge_score": 0.03, "buy_rank": 18, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7104", "expected_edge_score": 0.01, "buy_rank": 25, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7105", "expected_edge_score": 0.09, "buy_rank": 22, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7106", "expected_edge_score": 0.05, "buy_rank": 30, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7107", "expected_edge_score": 0.02, "buy_rank": 28, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
        ]
    )


def fixture_holdings_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-15", "code": "7101", "current_position_value": 180_000.0, "holding_days": 2, "unrealized_return": 0.03},
            {"target_date": "2026-06-15", "code": "7102", "current_position_value": 160_000.0, "holding_days": 8, "unrealized_return": -0.16},
            {"target_date": "2026-06-15", "code": "7103", "current_position_value": 140_000.0, "holding_days": 9, "unrealized_return": -0.02},
            {"target_date": "2026-06-15", "code": "7104", "current_position_value": 120_000.0, "holding_days": 10, "unrealized_return": 0.02},
            {"target_date": "2026-06-15", "code": "7105", "current_position_value": 130_000.0, "holding_days": 10, "unrealized_return": 0.04},
            {"target_date": "2026-06-15", "code": "7106", "current_position_value": 110_000.0, "holding_days": 10, "unrealized_return": 0.01},
            {"target_date": "2026-06-15", "code": "7107", "current_position_value": 100_000.0, "holding_days": 3, "unrealized_return": 0.00},
        ]
    )


def fixture_position_signal_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-15", "code": "7101", "position_signal": "HOLD", "replacement_confirmation_days": 0},
            {"target_date": "2026-06-15", "code": "7102", "position_signal": "HOLD", "replacement_confirmation_days": 0},
            {"target_date": "2026-06-15", "code": "7103", "position_signal": "EXIT", "replacement_confirmation_days": 0},
            {"target_date": "2026-06-15", "code": "7104", "position_signal": "HOLD", "replacement_confirmation_days": 0},
            {"target_date": "2026-06-15", "code": "7105", "position_signal": "HOLD", "replacement_confirmation_days": 2},
            {"target_date": "2026-06-15", "code": "7106", "position_signal": "HOLD", "replacement_confirmation_days": 1},
            {"target_date": "2026-06-15", "code": "7107", "position_signal": "HOLD", "replacement_confirmation_days": 2},
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
