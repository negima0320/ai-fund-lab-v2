from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.position_management_ai.inference import (
    BLOCKED_BY_LEAKAGE_AUDIT,
    READY_FOR_PHASE6_VALIDATION,
    audit_position_feature_frame,
    build_position_feature_frame,
    run_position_management_inference,
)
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import run_sell_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.safety_decision import RuntimeSafetyDecision


BUSINESS_DATE = "2026-07-07"
SYMBOLS = ("36670", "45640", "66590", "67400", "81050")


@pytest.mark.parametrize("mode", ["production", "demo", "historical"])
def test_phase17_ak_current_operational_fields_are_runtime_safe_across_modes(mode: str) -> None:
    frame = _pm_inference_frame()
    frame["runtime_mode"] = mode
    frame["runtime_test_run_id"] = "metadata-only"
    frame["feature__broker_issue_code"] = frame["code"]

    audit = audit_position_feature_frame(frame, input_holding_count=5, created_at="2026-07-07T00:00:00+00:00")

    assert audit["leakage_audit_status"] == "OK"
    assert audit["readiness_status"] == READY_FOR_PHASE6_VALIDATION
    assert "feature__broker_issue_code" in audit["metadata_only_columns"]
    assert "runtime_test_run_id" in audit["metadata_only_columns"]
    assert audit["forbidden_feature_columns"] == []


def test_phase17_ak_five_positions_with_no_exit_generate_five_hold_decisions(tmp_path: Path) -> None:
    holding_path = tmp_path / "holding.csv"
    opportunity_path = tmp_path / "opportunity.csv"
    feature_path = tmp_path / "position_feature_input.parquet"
    _holding_frame().to_csv(holding_path, index=False)
    _opportunity_frame(ranked_symbols=SYMBOLS[:2]).to_csv(opportunity_path, index=False)
    _runtime_pm_feature_frame().to_parquet(feature_path, index=False)

    result = run_position_management_inference(
        holding_path=holding_path,
        opportunity_path=opportunity_path,
        feature_path=feature_path,
        output_dir=tmp_path / "pm",
        created_at="2026-07-07T00:00:00+00:00",
        inference_run_id="phase17-ak",
    )

    assert result.summary["readiness_status"] == READY_FOR_PHASE6_VALIDATION
    assert result.summary["output_count"] == 5
    assert result.summary["hold_count"] == 5
    assert result.summary["exit_count"] == 0
    assert result.summary["reduce_count"] == 0
    assert result.summary["add_candidate_count"] == 0
    assert set(result.output["action"]) == {"HOLD"}


def test_phase17_ak_buy_ranking_unlisted_symbols_are_valid_pm_context(tmp_path: Path) -> None:
    holding = _holding_frame()
    opportunity = _opportunity_frame(ranked_symbols=SYMBOLS[:2])
    feature = _runtime_pm_feature_frame()

    frame = build_position_feature_frame(holding_frame=holding, opportunity_frame=opportunity, feature_frame=feature)
    output_symbols = set(frame["code"].astype(str))
    unranked = frame[frame["expected_edge_score"].isna()]["code"].astype(str).tolist()

    assert output_symbols == set(SYMBOLS)
    assert sorted(unranked) == sorted(SYMBOLS[2:])


def test_phase17_ak_sell_planning_accepts_hold_only_pm_result(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    _write_current_ledger(root)

    result = run_sell_planning_pending_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="production",
        exit_decisions=(),
        safety_decision=_production_allow_safety_decision(),
    )

    assert result.status == "NO_SIGNAL"
    assert result.selected_count == 0
    assert result.current_position_count == 1


@pytest.mark.parametrize(
    "column,value,expected_reason",
    [
        ("feature__future_return_20d", 0.40, "forbidden_future_signal"),
        ("feature__realized_future_return", 0.40, "forbidden_training_signal"),
        ("feature__backtest_return", 0.40, "forbidden_training_signal"),
        ("feature__paper_ledger_pnl", 1000.0, "forbidden_training_signal"),
        ("feature__test_verdict", "PASS", "forbidden_training_signal"),
        ("feature__audit_verdict", "PASS", "forbidden_training_signal"),
        ("feature__runtime_test_run_id", "runtime-test-id", "forbidden_training_signal"),
    ],
)
def test_phase17_ak_forbidden_model_feature_inputs_fail_closed(column: str, value: object, expected_reason: str) -> None:
    frame = _pm_inference_frame()
    frame[column] = value

    audit = audit_position_feature_frame(frame, input_holding_count=5, created_at="2026-07-07T00:00:00+00:00")

    assert audit["readiness_status"] == BLOCKED_BY_LEAKAGE_AUDIT
    assert audit["leakage_audit_status"] == "ERROR"
    assert column in audit["forbidden_feature_columns"]
    assert audit["field_classification_counts"][expected_reason] >= 1


def test_phase17_ak_temporal_and_schema_anomalies_fail_closed() -> None:
    future_asof = _pm_inference_frame()
    future_asof["as_of_date"] = "2026-07-08"
    malformed = _pm_inference_frame()
    malformed["feature__return_5d"] = "not-a-number"
    duplicate = pd.concat([_pm_inference_frame(), _pm_inference_frame().head(1)], ignore_index=True)

    future_audit = audit_position_feature_frame(future_asof, input_holding_count=5, created_at="2026-07-07T00:00:00+00:00")
    malformed_audit = audit_position_feature_frame(malformed, input_holding_count=5, created_at="2026-07-07T00:00:00+00:00")

    assert future_audit["readiness_status"] == BLOCKED_BY_LEAKAGE_AUDIT
    assert future_audit["as_of_date_violation_count"] == 5
    assert malformed_audit["readiness_status"] == BLOCKED_BY_LEAKAGE_AUDIT
    assert malformed_audit["malformed_numeric_columns"] == ["feature__return_5d"]
    assert duplicate.duplicated(["target_date", "code"]).any()


def _pm_inference_frame() -> pd.DataFrame:
    return build_position_feature_frame(
        holding_frame=_holding_frame(),
        opportunity_frame=_opportunity_frame(ranked_symbols=SYMBOLS[:2]),
        feature_frame=_runtime_pm_feature_frame(),
    )


def _holding_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "code": symbol,
                "entry_price": 100.0,
                "current_price": 102.0,
                "holding_days": 3,
                "position_size": 100.0,
                "current_return": 0.02,
                "peak_return": 0.03,
            }
            for symbol in SYMBOLS
        ]
    )


def _opportunity_frame(*, ranked_symbols: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "code": symbol,
                "expected_edge_score": 0.04,
                "buy_rank": rank,
                "downside_risk_score": 0.20,
                "risk_guard_status": "ok",
            }
            for rank, symbol in enumerate(ranked_symbols, start=1)
        ]
    )


def _runtime_pm_feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "position_state_as_of": BUSINESS_DATE,
                "entry_date": "2026-07-06",
                "code": symbol,
                "broker_issue_code": symbol,
                "holding_days": 3,
                "average_price": 100.0,
                "current_price": 102.0,
                "unrealized_return": 0.02,
                "quantity": 100.0,
                "return_5d": 0.04,
                "return_20d": 0.08,
                "close_over_ma_20d": 1.04,
                "ma_5_20_ratio": 1.02,
                "volume_ratio_5d": 1.10,
                "volatility_20d": 0.02,
                "feature_version": "runtime_v2_pm_feature_input_v1",
                "data_until": BUSINESS_DATE,
                "created_at": BUSINESS_DATE + "T00:00:00+00:00",
                "no_position_reason": "",
            }
            for symbol in SYMBOLS
        ]
    )


def _write_current_ledger(root: Path) -> None:
    path = root / "persistent_ledger" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
{
  "schema_version": "runtime_v2_current_temporal_v1",
  "environment": "production",
  "as_of": "2026-07-07",
  "positions": [
    {"symbol": "36670", "quantity": 100, "average_price": 100.0, "market_value": 10200.0, "source": "runtime_current", "as_of": "2026-07-07"}
  ],
  "cash": 100000,
  "buying_power": 100000,
  "market_value": 10200,
  "total_equity": 110200,
  "review_required": false,
  "current_state_confirmed_empty": false,
  "current_positions_unknown": false
}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _production_allow_safety_decision() -> RuntimeSafetyDecision:
    return RuntimeSafetyDecision(
        safety_decision_id="phase17-ak-production-safety-pass",
        safety_policy_version="runtime_safety_v1",
        safety_source="phase17_ak_fixture",
        business_date=BUSINESS_DATE,
        runtime_mode="production",
        decision="ALLOW",
        reason="phase17_ak_no_signal",
        review_required=False,
        block_buy=False,
        block_sell=False,
        block_submit=False,
        halt_runtime=False,
        emergency_stop=False,
        generated_at=BUSINESS_DATE + "T08:40:00+09:00",
        expires_at=BUSINESS_DATE + "T15:00:00+09:00",
        safety_status="PASS",
        action_permissions={"sell_planning": "ALLOWED", "broker_write": "ALLOWED"},
    )
