from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import (
    CANDIDATE_REQUIRED_COLUMNS,
    OPPORTUNITY_REQUIRED_COLUMNS,
)


BUSINESS_DATE = "2026-07-07"
PREVIOUS_TRADING_DATE = "2026-07-06"
RUN_ID = "runtime-test-historical-smoke-fixture"
PROFILE_ID = "historical-smoke"


class FixtureModel:
    pass


def test_phase17_af_day2_morning_accepts_previous_close_current_valuation_and_consumed_pending_safety(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path, valuation_as_of=PREVIOUS_TRADING_DATE, historical=True, safety_missing=True)
    feature_root = _write_feature_inputs(root / "operations" / "feature_artifacts")
    candidate_model = _write_model(tmp_path / "candidate.pkl")
    opportunity_model = _write_model(tmp_path / "opportunity.pkl")

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=BUSINESS_DATE,
        candidate_model_path=candidate_model,
        opportunity_model_path=opportunity_model,
        runtime_test_evidence_root=tmp_path / "reports" / "runtime_tests" / "runs" / RUN_ID,
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        broker_environment="historical_simulated",
        broker_write=False,
        external_delivery=False,
    )

    assert result.status == "READY"
    assert result.payload["current_valuation_status"] == "READY"
    assert result.payload["current_valuation_expected_date"] == PREVIOUS_TRADING_DATE
    assert result.payload["current_valuation_expected_date_policy"] == "morning_previous_close_or_same_day"
    assert result.payload["current_valuation_previous_close_carry_allowed"] is True
    assert result.payload["current_valuation_temporal_authority"] == "current_valuation_previous_trading_day_close"
    assert result.payload["current_valuation_temporal_reason"] == "previous_trading_day_close_is_latest_available_at_morning_evaluation"
    assert "current_valuation_not_ready" not in result.payload["review_reasons"]
    assert result.payload["safety_status"] == "READY"
    assert result.payload["components"]["safety"]["pending_safety_authority"]["reason"] == "historical_consumed_pending_safety_authority_carry_forward"
    assert "historical_safety_temporal_authority_missing" not in result.payload["review_reasons"]


def test_phase17_af_current_valuation_scope_accepts_previous_close_as_refresh_precondition(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path, valuation_as_of=PREVIOUS_TRADING_DATE)
    feature_root = _write_feature_inputs(root / "operations" / "feature_artifacts")

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="current_valuation",
        feature_root=feature_root,
        feature_date=BUSINESS_DATE,
        candidate_model_path=_write_model(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_model(tmp_path / "opportunity.pkl"),
    )

    assert result.status == "READY"
    assert result.payload["current_valuation_status"] == "READY"
    assert result.payload["current_valuation_expected_date"] == BUSINESS_DATE
    assert result.payload["current_valuation_expected_date_policy"] == "current_valuation_refresh_precondition"
    assert result.payload["current_valuation_previous_close_carry_allowed"] is False
    assert result.payload["valuation_refresh_precondition_status"] == "PASS"
    assert result.payload["current_valuation_temporal_authority"] == "current_valuation_previous_close_ready_for_refresh"
    assert "current_valuation_not_ready" not in result.payload["review_reasons"]


def test_phase17_af_future_current_valuation_date_fails_closed(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path, valuation_as_of="2026-07-08")
    feature_root = _write_feature_inputs(root / "operations" / "feature_artifacts")

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=BUSINESS_DATE,
        candidate_model_path=_write_model(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_model(tmp_path / "opportunity.pkl"),
    )

    assert result.status == "HALT"
    assert result.payload["current_valuation_status"] == "HALT"
    assert result.payload["current_valuation_temporal_reason"] == "current_valuation_future_date"
    assert "current_valuation_future_date" in result.payload["halt_reasons"]


def _runtime_root(
    tmp_path: Path,
    *,
    valuation_as_of: str,
    historical: bool = False,
    safety_missing: bool = False,
) -> Path:
    root = tmp_path / ".runtime"
    mode = "historical" if historical else "demo"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "temporal_schema_version": "runtime_v2_current_temporal_v1",
            "environment": mode,
            "business_date": PREVIOUS_TRADING_DATE,
            "position_state_as_of": PREVIOUS_TRADING_DATE,
            "valuation_as_of": valuation_as_of,
            "source_market_date": valuation_as_of,
            "last_execution_date": PREVIOUS_TRADING_DATE,
            "last_reconciled_at": PREVIOUS_TRADING_DATE + "T15:40:00+09:00",
            "updated_at": PREVIOUS_TRADING_DATE + "T15:40:00+09:00",
            "positions": [{"symbol": "81050", "quantity": 100, "average_price": 100}],
            "cash": 900000,
            "buying_power": 900000,
            "market_value": 10000,
            "total_equity": 910000,
            "review_required": False,
            "current_state_confirmed_empty": False,
            "current_positions_unknown": False,
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "runtime_v2_operation_state_v1",
            "role": "authoritative_runtime_operation_state",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T08:00:00+09:00",
            "updated_at": BUSINESS_DATE + "T08:00:00+09:00",
            "environment": mode,
            "runtime_mode": mode,
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
            "current_safety_state": "NORMAL",
            "source": "runtime_v2_runtime_state_producer",
            "asset_state_is_authoritative_here": False,
            "pending_state_is_authoritative_here": False,
            "asset_state_source": "persistent_ledger/state.json",
        },
    )
    _write_json(
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": BUSINESS_DATE,
            "runtime_business_date": BUSINESS_DATE,
            "market_date": BUSINESS_DATE,
            "as_of": BUSINESS_DATE,
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": 1,
            "market_summary": {"status": "READY"},
        },
    )
    _write_pending(root, historical=historical)
    if not safety_missing:
        _write_safety(root, mode=mode)
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _write_pending(root: Path, *, historical: bool) -> None:
    if not historical:
        _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "EMPTY", "status": "EMPTY", "active_pending": False})
        return
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "state": "CONSUMED",
            "status": "CONSUMED",
            "active_pending": True,
            "environment": "historical",
            "target_session_date": PREVIOUS_TRADING_DATE,
            "consume": {"consumed": True},
            "safety_context": {
                "safety_authority": "historical_initial_no_external_effect",
                "safety_decision": "ALLOW",
                "safety_policy_version": "historical_replay_neutral_safety_v1",
                "safety_source": "data_readiness_historical_temporal_authority",
                "safety_business_date": PREVIOUS_TRADING_DATE,
                "runtime_test_run_id": RUN_ID,
                "runtime_test_profile_id": PROFILE_ID,
                "runtime_test_evidence_root": str(root.parent / "reports" / "runtime_tests" / "runs" / RUN_ID),
            },
        },
    )


def _write_feature_inputs(feature_root: Path) -> Path:
    feature_dir = feature_root / BUSINESS_DATE
    feature_dir.mkdir(parents=True, exist_ok=True)
    candidate = {column: _value_for_column(column) for column in CANDIDATE_REQUIRED_COLUMNS}
    opportunity = {column: _value_for_column(column) for column in OPPORTUNITY_REQUIRED_COLUMNS}
    pd.DataFrame([candidate]).to_parquet(feature_dir / "candidate_features.parquet", index=False)
    pd.DataFrame([opportunity]).to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "position_state_as_of": PREVIOUS_TRADING_DATE,
                "entry_date": PREVIOUS_TRADING_DATE,
                "code": "81050",
                "broker_issue_code": "81050",
                "holding_days": 1,
                "average_price": 100.0,
                "current_price": 101.0,
                "unrealized_return": 0.01,
                "quantity": 100.0,
                "feature_version": "runtime_v2_pm_feature_input_v1",
                "data_until": BUSINESS_DATE,
                "created_at": BUSINESS_DATE + "T08:00:00+09:00",
                "no_position_reason": "",
            }
        ]
    ).to_parquet(feature_dir / "position_feature_input.parquet", index=False)
    pd.DataFrame([{"target_date": BUSINESS_DATE, "code": "__POLICY_INPUT__"}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )
    _write_json(
        feature_root.parent / "feature_date_contract" / f"{BUSINESS_DATE}.json",
        {
            "schema_version": "runtime_v2_feature_contract_v2",
            "status": "PASS",
            "reason": "requested_feature_artifacts_available",
            "requested_feature_date": BUSINESS_DATE,
            "selected_feature_date": BUSINESS_DATE,
            "latest_available_market_date": BUSINESS_DATE,
            "carryover_used": False,
            "carryover_reason": "",
            "freshness_lag_business_days": 0,
            "freshness_limit_business_days": 1,
            "feature_artifact_dir": str(feature_dir),
            "generated_feature_artifacts": {
                "candidate_features.parquet": str(feature_dir / "candidate_features.parquet"),
                "opportunity_feature_input.parquet": str(feature_dir / "opportunity_feature_input.parquet"),
                "position_feature_input.parquet": str(feature_dir / "position_feature_input.parquet"),
                "capital_policy_input.parquet": str(feature_dir / "capital_policy_input.parquet"),
            },
            "missing_feature_artifacts": [],
            "requested_feature_artifact_dir": str(feature_dir),
            "requested_missing_feature_artifacts": [],
            "price_source_alignment": "selected_feature_date",
            "consumer_ready": True,
            "candidate_schema_status": "READY",
            "candidate_missing_columns": [],
            "opportunity_schema_status": "READY",
            "pm_schema_status": "READY",
            "consumer_readiness_artifact_path": str(feature_root.parent / "feature_consumer_readiness" / f"{BUSINESS_DATE}.json"),
            "contract_artifact_path": str(feature_root.parent / "feature_date_contract" / f"{BUSINESS_DATE}.json"),
        },
    )
    return feature_root


def _value_for_column(column: str) -> Any:
    if column == "target_date":
        return BUSINESS_DATE
    if column == "code":
        return "81050"
    if column.startswith("missing_flags_"):
        return False
    if column.endswith("_flag") or column.endswith("_context"):
        return False
    return 1.0


def _write_model(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump({"model": FixtureModel(), "feature_columns": ["feature__price_momentum_return_20d"]}, handle)
    return path


def _write_safety(root: Path, *, mode: str) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-fixture",
            "safety_policy_version": "safety_operation_guard_v1",
            "business_date": BUSINESS_DATE,
            "runtime_mode": mode,
            "decision": "ALLOW",
            "reason": "fixture allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": BUSINESS_DATE + "T08:00:00+09:00",
            "expires_at": BUSINESS_DATE + "T23:59:00+09:00",
        },
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows), encoding="utf-8")
