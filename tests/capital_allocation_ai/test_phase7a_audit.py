from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.audit import run_phase7a_capital_allocation_audit
from ai_fund_lab_v2.capital_allocation_ai.engine import AUDIT_FILENAME, DECISION_CSV_FILENAME, SUMMARY_FILENAME, run_capital_allocation_engine
from ai_fund_lab_v2.capital_allocation_ai.schema import Phase7AConfig, PortfolioSnapshot


def test_phase7a_dry_run_writes_outputs_and_audit_confirms_boundaries(tmp_path: Path) -> None:
    result = run_capital_allocation_engine(
        portfolio=PortfolioSnapshot(target_date="2026-06-15", total_assets=1_000_000.0, cash=500_000.0),
        opportunity_frame=_opportunities(),
        holdings_frame=_holdings(),
        position_signal_frame=_signals(),
        output_dir=tmp_path,
        config=Phase7AConfig(),
        created_at="2026-06-15T00:00:00+00:00",
    )

    assert result["summary"]["status"] == "OK"
    assert (tmp_path / DECISION_CSV_FILENAME).is_file()
    assert (tmp_path / SUMMARY_FILENAME).is_file()
    assert (tmp_path / AUDIT_FILENAME).is_file()

    audit = run_phase7a_capital_allocation_audit(
        summary_path=tmp_path / SUMMARY_FILENAME,
        audit_path=tmp_path / AUDIT_FILENAME,
        output_path=tmp_path / DECISION_CSV_FILENAME,
        created_at="2026-06-15T00:00:00+00:00",
    )

    assert audit["completion_status"] == "PHASE7A_CAPITAL_ALLOCATION_ENGINE_READY"
    assert audit["checks"]["broker_api_not_executed"] is True
    assert audit["checks"]["paper_trading_not_executed"] is True
    assert audit["checks"]["order_not_executed"] is True
    assert audit["checks"]["live_order_not_executed"] is True
    assert audit["checks"]["tachibana_api_not_called"] is True
    assert audit["checks"]["fixed_take_profit_disabled"] is True
    assert audit["checks"]["phase6_single_exit_auto_sell_disabled"] is True
    assert audit["checks"]["emergency_exit_enabled"] is True
    assert audit["checks"]["replacement_requires_minimum_holding_days"] is True
    assert audit["checks"]["replacement_requires_edge_margin"] is True
    assert audit["checks"]["replacement_requires_confirmation_days"] is True
    assert audit["checks"]["cash_buffer_applied"] is True
    assert audit["checks"]["max_position_weight_applied"] is True

    persisted = json.loads((tmp_path / "phase7a_completion_audit.json").read_text(encoding="utf-8"))
    assert persisted["completion_status"] == audit["completion_status"]


def _opportunities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-15", "code": "7001", "expected_edge_score": 0.12, "buy_rank": 1, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7002", "expected_edge_score": 0.10, "buy_rank": 2, "downside_risk_score": 0.25, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7003", "expected_edge_score": 0.09, "buy_rank": 3, "downside_risk_score": 0.30, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7101", "expected_edge_score": 0.08, "buy_rank": 8, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7102", "expected_edge_score": 0.04, "buy_rank": 12, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7103", "expected_edge_score": 0.03, "buy_rank": 18, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-15", "code": "7105", "expected_edge_score": 0.09, "buy_rank": 22, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
        ]
    )


def _holdings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-15", "code": "7101", "current_position_value": 180_000.0, "holding_days": 2, "unrealized_return": 0.03},
            {"target_date": "2026-06-15", "code": "7102", "current_position_value": 160_000.0, "holding_days": 8, "unrealized_return": -0.16},
            {"target_date": "2026-06-15", "code": "7103", "current_position_value": 140_000.0, "holding_days": 9, "unrealized_return": -0.02},
            {"target_date": "2026-06-15", "code": "7105", "current_position_value": 130_000.0, "holding_days": 10, "unrealized_return": 0.04},
        ]
    )


def _signals() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-15", "code": "7101", "position_signal": "HOLD", "replacement_confirmation_days": 0},
            {"target_date": "2026-06-15", "code": "7102", "position_signal": "HOLD", "replacement_confirmation_days": 0},
            {"target_date": "2026-06-15", "code": "7103", "position_signal": "EXIT", "replacement_confirmation_days": 0},
            {"target_date": "2026-06-15", "code": "7105", "position_signal": "HOLD", "replacement_confirmation_days": 2},
        ]
    )
