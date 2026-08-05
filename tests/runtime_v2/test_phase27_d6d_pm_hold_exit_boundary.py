from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.position_management.producer import produce_position_management_decisions


BUSINESS_DATE = "2026-07-09"


def test_phase27_d6d_runtime_pm_holds_expected_edge_adequate_profit_retention_review(tmp_path: Path) -> None:
    runtime_root = _runtime_root(
        tmp_path,
        positions=[
            {
                "symbol": "2001",
                "quantity": 100,
                "average_price": 100.0,
                "current_price": 108.0,
                "market_value": 10800.0,
                "unrealized_pnl": 800.0,
                "holding_days": 12,
                "peak_return": 0.22,
                "source": "runtime_v2_runtime_owned_fill_projection",
                "as_of": BUSINESS_DATE,
            }
        ],
    )
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbol="2001")

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = json.loads(Path(result.artifact_path).read_text(encoding="utf-8"))
    decision = artifact["decisions"][0]
    trace = decision["decision_trace"]

    assert result.status == "PASS"
    assert decision["decision"] == "HOLD"
    assert decision["runtime_action"] == "NO_SELL_ORDER"
    assert decision["runtime_sell_quantity"] == 0
    assert decision["expected_edge_status"] == "ADEQUATE"
    assert "peak_drawdown_profit_retention_risk" in decision["canonical_decision_reason_codes"]
    assert trace["expected_edge_semantics"]["risk_review_status"] == "REVIEW"


def _runtime_root(tmp_path: Path, *, positions: list[dict]) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "phase27d6d-fixture",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": BUSINESS_DATE,
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
            "positions": positions,
            "cash": 500000,
            "buying_power": 500000,
            "market_value": sum(float(item.get("market_value") or 0) for item in positions),
            "total_equity": 500000 + sum(float(item.get("market_value") or 0) for item in positions),
            "review_required": False,
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "items": []})
    _write_json(root / "runtime_state" / "current_state.json", {"state": "CURRENT_STATE_LOADED"})
    for name in ("orders", "executions", "cash", "events", "positions"):
        path = root / "persistent_ledger" / f"{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    return root


def _pm_inputs(tmp_path: Path, *, symbol: str) -> tuple[Path, Path]:
    opportunity_path = tmp_path / "pm_opportunity.csv"
    pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "code": symbol,
                "expected_edge_score": 0.08,
                "buy_rank": 12,
                "downside_risk_score": 0.30,
                "risk_guard_status": "ok",
                "candidate_score": 0.5,
                "candidate_rank": 12,
                "buy_reason": "",
                "no_buy_reason": "",
                "calibration_policy_name": "phase27d6d_fixture",
            }
        ]
    ).to_csv(opportunity_path, index=False)
    feature_path = tmp_path / "pm_feature.csv"
    pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "feature_as_of_date": BUSINESS_DATE,
                "as_of_date": BUSINESS_DATE,
                "code": symbol,
                "price_momentum_return_5d": 0.03,
                "price_momentum_return_20d": 0.08,
                "trend_close_over_ma_20d": 1.04,
                "trend_ma_5_20_ratio": 1.02,
                "volume_momentum_ratio_5d": 1.10,
                "volatility_return_std_20d": 0.03,
                "feature_source_artifact": "candidate_features.parquet",
                "feature_source_hash": "fixture-candidate-feature-hash",
                "required_features": "[]",
                "optional_features": "[]",
                "missing_features": "[]",
                "defaulted_features": "[]",
                "temporal_validation_status": "PASS",
                "feature_version": "runtime_v2_pm_feature_input_v2_technical_complete",
                "data_until": BUSINESS_DATE,
                "created_at": BUSINESS_DATE + "T00:00:00Z",
            }
        ]
    ).to_csv(feature_path, index=False)
    return opportunity_path, feature_path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
