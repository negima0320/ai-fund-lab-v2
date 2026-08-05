from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.position_management_ai.inference import (
    BLOCKED_BY_LEAKAGE_AUDIT,
    READY_FOR_PHASE6_VALIDATION,
    OUTPUT_COLUMNS,
    audit_position_feature_frame,
    build_position_feature_frame,
    build_position_management_output,
    run_position_management_inference,
)


def test_phase6a_rule_based_baseline_outputs_required_schema() -> None:
    frame = build_position_feature_frame(
        holding_frame=_holding_frame(),
        opportunity_frame=_opportunity_frame(),
        feature_frame=_feature_frame(),
    )
    audit = audit_position_feature_frame(frame, input_holding_count=4, created_at="2026-06-14T00:00:00+00:00")
    output = build_position_management_output(
        frame,
        created_at="2026-06-14T00:00:00+00:00",
        inference_run_id="fixture_run",
    )

    assert audit["leakage_audit_status"] == "OK"
    assert list(output.columns) == list(OUTPUT_COLUMNS)
    assert set(output["action"]) == {"ADD", "EXIT", "HOLD", "REDUCE"}
    assert output.loc[output["code"] == "1001", "add_candidate"].item() is True
    assert output.loc[output["code"] == "1002", "exit_candidate"].item() is True
    assert output.loc[output["code"] == "1003", "reduce_candidate"].item() is True
    assert output.loc[output["code"] == "1004", "continue_holding"].item() is True


def test_phase27_d6d_expected_edge_adequate_profit_retention_review_holds() -> None:
    frame = build_position_feature_frame(
        holding_frame=pd.DataFrame(
            [
                {
                    "target_date": "2026-06-12",
                    "code": "2001",
                    "entry_price": 100.0,
                    "current_price": 108.0,
                    "holding_days": 12,
                    "position_size": 100,
                    "peak_return": 0.22,
                }
            ]
        ),
        opportunity_frame=pd.DataFrame(
            [
                {
                    "target_date": "2026-06-12",
                    "code": "2001",
                    "expected_edge_score": 0.08,
                    "buy_rank": 12,
                    "downside_risk_score": 0.30,
                    "risk_guard_status": "ok",
                }
            ]
        ),
        feature_frame=pd.DataFrame(
            [
                _feature_row(
                    "2001",
                    close_over_ma=1.04,
                    ma_ratio=1.02,
                    return_5d=0.03,
                    return_20d=0.08,
                    volatility=0.03,
                    volume=1.10,
                )
            ]
        ),
    )
    output = build_position_management_output(
        frame,
        created_at="2026-06-14T00:00:00+00:00",
        inference_run_id="fixture_run",
    )
    row = output.loc[output["code"] == "2001"].iloc[0]

    assert row["action"] == "HOLD"
    assert row["continue_holding"] == True
    assert row["exit_candidate"] == False
    assert row["action_reason"] == "positive_expected_edge|profit_retention_break"
    assert row["exit_reason"] == ""


def test_phase27_d6d_profit_retention_review_does_not_override_hard_exit_evidence() -> None:
    frame = build_position_feature_frame(
        holding_frame=pd.DataFrame(
            [
                {
                    "target_date": "2026-06-12",
                    "code": "2002",
                    "entry_price": 100.0,
                    "current_price": 90.0,
                    "holding_days": 12,
                    "position_size": 100,
                    "peak_return": 0.04,
                }
            ]
        ),
        opportunity_frame=pd.DataFrame(
            [
                {
                    "target_date": "2026-06-12",
                    "code": "2002",
                    "expected_edge_score": 0.08,
                    "buy_rank": 12,
                    "downside_risk_score": 0.30,
                    "risk_guard_status": "ok",
                }
            ]
        ),
        feature_frame=pd.DataFrame(
            [
                _feature_row(
                    "2002",
                    close_over_ma=1.04,
                    ma_ratio=1.02,
                    return_5d=0.03,
                    return_20d=0.08,
                    volatility=0.03,
                    volume=1.10,
                )
            ]
        ),
    )
    output = build_position_management_output(
        frame,
        created_at="2026-06-14T00:00:00+00:00",
        inference_run_id="fixture_run",
    )
    row = output.loc[output["code"] == "2002"].iloc[0]

    assert row["action"] == "EXIT"
    assert row["exit_candidate"] == True
    assert "hard_stop_current_return" in row["exit_reason"]


def test_phase6a_blocks_forbidden_future_feature() -> None:
    features = _feature_frame()
    features["future_return_20d"] = 0.50
    frame = build_position_feature_frame(
        holding_frame=_holding_frame(),
        opportunity_frame=_opportunity_frame(),
        feature_frame=features,
    )

    audit = audit_position_feature_frame(frame, input_holding_count=4, created_at="2026-06-14T00:00:00+00:00")

    assert audit["readiness_status"] == BLOCKED_BY_LEAKAGE_AUDIT
    assert audit["leakage_audit_status"] == "ERROR"
    assert "feature__future_return_20d" in audit["forbidden_feature_columns"]


def test_phase6a_blocks_forbidden_portfolio_feature() -> None:
    features = _feature_frame()
    features["portfolio_weight"] = 0.10
    frame = build_position_feature_frame(
        holding_frame=_holding_frame(),
        opportunity_frame=_opportunity_frame(),
        feature_frame=features,
    )

    audit = audit_position_feature_frame(frame, input_holding_count=4, created_at="2026-06-14T00:00:00+00:00")

    assert audit["readiness_status"] == BLOCKED_BY_LEAKAGE_AUDIT
    assert audit["leakage_audit_status"] == "ERROR"
    assert "feature__portfolio_weight" in audit["forbidden_feature_columns"]


def test_phase6a_small_dry_run_writes_summary_and_audit(tmp_path: Path) -> None:
    holding_path = tmp_path / "holding.parquet"
    opportunity_path = tmp_path / "opportunity.parquet"
    feature_path = tmp_path / "feature.parquet"
    _holding_frame().to_parquet(holding_path, index=False)
    _opportunity_frame().to_parquet(opportunity_path, index=False)
    _feature_frame().to_parquet(feature_path, index=False)

    result = run_position_management_inference(
        holding_path=holding_path,
        opportunity_path=opportunity_path,
        feature_path=feature_path,
        output_dir=tmp_path / "out",
        created_at="2026-06-14T00:00:00+00:00",
        inference_run_id="fixture_run",
    )

    assert result.summary["readiness_status"] == READY_FOR_PHASE6_VALIDATION
    assert result.summary["broker_api_executed"] is False
    assert result.summary["order_executed"] is False
    assert result.summary["paper_trading_executed"] is False
    assert result.summary["capital_allocation_executed"] is False
    assert result.summary["hold_count"] == 1
    assert result.summary["exit_count"] == 1
    assert result.summary["add_candidate_count"] == 1
    assert result.summary["reduce_count"] == 1
    assert Path(result.summary["output_path"]).is_file()
    assert Path(result.summary["audit_path"]).is_file()


def _holding_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-12", "code": "1001", "entry_price": 100.0, "current_price": 112.0, "holding_days": 12, "position_size": 100, "peak_return": 0.14},
            {"target_date": "2026-06-12", "code": "1002", "entry_price": 100.0, "current_price": 91.0, "holding_days": 15, "position_size": 100, "peak_return": 0.04},
            {"target_date": "2026-06-12", "code": "1003", "entry_price": 100.0, "current_price": 106.0, "holding_days": 20, "position_size": 100, "peak_return": 0.16},
            {"target_date": "2026-06-12", "code": "1004", "entry_price": 100.0, "current_price": 104.0, "holding_days": 8, "position_size": 100, "peak_return": 0.05},
        ]
    )


def _opportunity_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-12", "code": "1001", "expected_edge_score": 0.16, "buy_rank": 2, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "1002", "expected_edge_score": -0.04, "buy_rank": 35, "downside_risk_score": 0.80, "risk_guard_status": "bad"},
            {"target_date": "2026-06-12", "code": "1003", "expected_edge_score": 0.07, "buy_rank": 8, "downside_risk_score": 0.66, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "1004", "expected_edge_score": 0.05, "buy_rank": 12, "downside_risk_score": 0.30, "risk_guard_status": "ok"},
        ]
    )


def _feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _feature_row("1001", close_over_ma=1.08, ma_ratio=1.05, return_5d=0.08, return_20d=0.18, volatility=0.02, volume=1.50),
            _feature_row("1002", close_over_ma=0.94, ma_ratio=0.96, return_5d=-0.08, return_20d=-0.16, volatility=0.08, volume=0.70),
            _feature_row("1003", close_over_ma=1.03, ma_ratio=1.02, return_5d=0.02, return_20d=0.09, volatility=0.09, volume=1.20),
            _feature_row("1004", close_over_ma=1.04, ma_ratio=1.02, return_5d=0.03, return_20d=0.08, volatility=0.03, volume=1.10),
        ]
    )


def _feature_row(
    code: str,
    *,
    close_over_ma: float,
    ma_ratio: float,
    return_5d: float,
    return_20d: float,
    volatility: float,
    volume: float,
) -> dict[str, object]:
    return {
        "target_date": "2026-06-12",
        "as_of_date": "2026-06-12",
        "code": code,
        "feature_version": "fixture_feature_v1",
        "price_momentum_return_5d": return_5d,
        "price_momentum_return_20d": return_20d,
        "trend_close_over_ma_20d": close_over_ma,
        "trend_ma_5_20_ratio": ma_ratio,
        "volatility_return_std_20d": volatility,
        "volume_momentum_ratio_5d": volume,
    }
