from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import (
    CANDIDATE_REQUIRED_COLUMNS,
    OPPORTUNITY_REQUIRED_COLUMNS,
)
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import run_sell_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.safety_decision import RuntimeSafetyDecision


BUSINESS_DATE = "2026-07-07"
PREVIOUS_TRADING_DATE = "2026-07-06"
RUN_ID = "runtime-test-historical-smoke-fixture"
PROFILE_ID = "historical-smoke"
SYMBOLS = ("36670", "45640", "66590", "67400", "81050")


def test_phase17_ag_sell_planning_resolves_pm_inputs_and_previous_close_authority(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    feature_root = _write_feature_artifacts(root)
    _write_buy_ai_opportunity(root)
    _write_empty_no_action_pending(root, tmp_path)

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="sell_planning",
        feature_root=feature_root,
        broker_environment="historical_simulated",
        runtime_test_evidence_root=_evidence_root(tmp_path),
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        broker_write=False,
        external_delivery=False,
    )

    pm_contract = result.payload["components"]["pm"]["contract"]
    pending_authority = result.payload["components"]["pending"]["historical_pending_safety_authority"]

    assert result.status == "READY"
    assert result.payload["current_valuation_status"] == "READY"
    assert result.payload["current_valuation_previous_close_carry_allowed"] is True
    assert result.payload["current_valuation_temporal_reason"] == "previous_trading_day_close_is_latest_available_at_morning_evaluation"
    assert pm_contract["pm_input_schema_status"] == "READY"
    assert pm_contract["pm_feature_row_count"] == 5
    assert pm_contract["pm_feature_source"].endswith("/position_feature_input.parquet")
    assert pm_contract["pm_opportunity_source"].endswith("/runtime_state/buy_ai/2026-07-07/opportunity_rankings.json")
    assert pm_contract["pm_opportunity_status"] == "READY"
    assert pm_contract["pm_missing_symbols"] == []
    assert pm_contract["pm_missing_fields"] == []
    assert any(field.endswith(".holding_days:pm_feature") for field in pm_contract["pm_derived_fields"])
    assert any(field.endswith(".peak_return:pm_feature") for field in pm_contract["pm_derived_fields"])
    assert pending_authority["status"] == "READY"
    assert pending_authority["reason"] == "historical_no_action_pending_safety_authority_ready"
    assert "historical_safety_temporal_authority_missing" not in result.payload["review_reasons"]
    assert "pm_feature_artifact_missing" not in result.payload["review_reasons"]


def test_phase17_ag_sell_no_signal_pending_is_empty_terminal_with_historical_authority(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)

    result = run_sell_planning_pending_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        safety_decision=_historical_allow_safety_decision(),
        environment_capability_context=_historical_context(tmp_path),
    )

    pending = _read_json(Path(result.pending_path))
    safety_context = pending["safety_context"]

    assert result.status == "NO_SIGNAL"
    assert pending["environment"] == "historical"
    assert pending["state"] == "EMPTY"
    assert pending["status"] == "EMPTY"
    assert pending["active_pending"] is False
    assert pending["items"] == []
    assert safety_context["safety_authority"] == "historical_initial_no_external_effect"
    assert safety_context["safety_business_date"] == BUSINESS_DATE
    assert safety_context["runtime_test_run_id"] == RUN_ID
    assert safety_context["runtime_test_profile_id"] == PROFILE_ID
    assert safety_context["runtime_test_evidence_root"] == str(_evidence_root(tmp_path))


def test_phase17_ag_production_no_signal_pending_is_terminal_without_test_identity(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path, mode="production", valuation_as_of=BUSINESS_DATE)

    result = run_sell_planning_pending_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="production",
        exit_decisions=(),
        safety_decision=_production_allow_safety_decision(),
    )

    pending = _read_json(Path(result.pending_path))
    assert result.status == "NO_SIGNAL"
    assert pending["environment"] == "production"
    assert pending["state"] == "EMPTY"
    assert pending["active_pending"] is False
    assert not (pending.get("safety_context") or {}).get("runtime_test_run_id")


def test_phase17_ag_production_stale_and_future_valuation_fail_closed(tmp_path: Path) -> None:
    stale = evaluate_runtime_data_readiness(
        runtime_root=_production_ready_root(tmp_path / "stale", valuation_as_of="2026-07-03"),
        business_date=BUSINESS_DATE,
        mode="production",
        readiness_scope="sell_planning",
        feature_root=_write_feature_artifacts(tmp_path / "stale" / ".runtime"),
        broker_environment="tachibana_production",
    )
    future = evaluate_runtime_data_readiness(
        runtime_root=_production_ready_root(tmp_path / "future", valuation_as_of="2026-07-08"),
        business_date=BUSINESS_DATE,
        mode="production",
        readiness_scope="sell_planning",
        feature_root=_write_feature_artifacts(tmp_path / "future" / ".runtime"),
        broker_environment="tachibana_production",
    )

    assert stale.status == "REVIEW_REQUIRED"
    assert "current_valuation_not_ready" in stale.payload["review_reasons"]
    assert future.status == "HALT"
    assert "current_valuation_future_date" in future.payload["halt_reasons"]


def test_phase17_ag_production_submit_stops_on_pending_environment_mismatch(tmp_path: Path) -> None:
    root = _production_ready_root(tmp_path, valuation_as_of=BUSINESS_DATE)
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-wrong-env",
            "state": "APPROVED",
            "active_pending": True,
            "environment": "demo",
            "target_session_date": BUSINESS_DATE,
            "items": [{"pending_item_id": "x", "symbol": "81050", "side": "BUY", "quantity": 100}],
            "approval": {"approval_status": "APPROVED", "pending_policy_hash": "hash"},
            "pending_policy_hash": "hash",
            "consume": {"consumed": False},
        },
    )

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="production",
        readiness_scope="submit",
        feature_root=_write_feature_artifacts(root),
        broker_environment="tachibana_production",
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "pending_environment_mismatch" in result.payload["review_reasons"]


def test_phase17_ag_production_sell_stops_on_pm_feature_path_mismatch(tmp_path: Path) -> None:
    root = _production_ready_root(tmp_path, valuation_as_of=PREVIOUS_TRADING_DATE)

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="production",
        readiness_scope="sell_planning",
        feature_root=_write_feature_artifacts(root),
        broker_environment="tachibana_production",
        pm_feature_path=tmp_path / "missing_position_feature.parquet",
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "pm_feature_artifact_missing" in result.payload["review_reasons"]


def _runtime_root(tmp_path: Path, *, mode: str = "historical", valuation_as_of: str = PREVIOUS_TRADING_DATE) -> Path:
    root = tmp_path / ".runtime"
    positions = [
        {
            "symbol": symbol,
            "issue_code": symbol,
            "quantity": 100,
            "average_price": 100.0,
            "market_value": 10100.0,
            "as_of": PREVIOUS_TRADING_DATE,
            "source": "persistent_ledger",
        }
        for symbol in SYMBOLS
    ]
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "temporal_schema_version": "runtime_v2_current_temporal_v1",
            "environment": mode,
            "as_of": PREVIOUS_TRADING_DATE,
            "business_date": PREVIOUS_TRADING_DATE,
            "position_state_as_of": PREVIOUS_TRADING_DATE,
            "valuation_as_of": valuation_as_of,
            "current_position_status": "READY",
            "current_valuation_status": "READY",
            "source_market_date": valuation_as_of,
            "last_execution_date": PREVIOUS_TRADING_DATE,
            "last_reconciled_at": PREVIOUS_TRADING_DATE + "T15:40:00+09:00",
            "updated_at": PREVIOUS_TRADING_DATE + "T15:40:00+09:00",
            "positions": positions,
            "cash": 191600,
            "buying_power": 191600,
            "market_value": 50500,
            "total_equity": 242100,
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
            "generated_at": BUSINESS_DATE + "T08:40:00+09:00",
            "updated_at": BUSINESS_DATE + "T08:40:00+09:00",
            "environment": mode,
            "runtime_mode": mode,
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
            "current_safety_state": "NORMAL",
            "source": "runtime_v2_runtime_state_producer",
            "asset_state_is_authoritative_here": False,
            "pending_state_is_authoritative_here": False,
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
            "quote_count": 5,
            "market_summary": {"status": "READY"},
        },
    )
    _write_json(
        root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json",
        {
            "schema_version": "runtime_v2_broker_readonly_snapshot_v1",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T08:40:00+09:00",
            "review_required": False,
            "positions": positions,
            "orders": [],
            "executions": [],
        },
    )
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "business_date": "2026-07-06",
            "runtime_mode": "historical",
            "decision": "REVIEW_REQUIRED",
            "reason": "stale_safety_decision",
            "review_required": True,
            "block_buy": True,
            "block_sell": True,
            "block_submit": True,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": PREVIOUS_TRADING_DATE + "T00:00:00Z",
            "expires_at": "",
            "safety_status": "REVIEW_REQUIRED",
        },
    )
    _write_calendar(root)
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _production_ready_root(tmp_path: Path, *, valuation_as_of: str) -> Path:
    root = _runtime_root(tmp_path, mode="production", valuation_as_of=valuation_as_of)
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "production-safety-pass",
            "safety_policy_version": "runtime_safety_v1",
            "safety_source": "production_safety_gate",
            "business_date": BUSINESS_DATE,
            "runtime_mode": "production",
            "decision": "ALLOW",
            "reason": "production_safety_pass",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": BUSINESS_DATE + "T08:00:00+09:00",
            "expires_at": BUSINESS_DATE + "T15:00:00+09:00",
            "safety_status": "PASS",
        },
    )
    _write_empty_production_pending(root)
    _write_buy_ai_opportunity(root)
    return root


def _write_feature_artifacts(root: Path) -> Path:
    operations_root = root / "operations"
    feature_dir = operations_root / "feature_artifacts" / BUSINESS_DATE
    feature_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "position_state_as_of": PREVIOUS_TRADING_DATE,
                "entry_date": PREVIOUS_TRADING_DATE,
                "code": symbol,
                "broker_issue_code": symbol,
                "holding_days": index + 1,
                "average_price": 100.0,
                "current_price": 101.0,
                "unrealized_return": 0.01,
                "quantity": 100.0,
                "feature_as_of_date": BUSINESS_DATE,
                "price_momentum_return_5d": 0.0,
                "price_momentum_return_20d": 0.0,
                "trend_close_over_ma_20d": 0.0,
                "trend_ma_5_20_ratio": 0.0,
                "volume_momentum_ratio_5d": 0.0,
                "volatility_return_std_20d": 0.0,
                "feature_source_artifact": "phase17_ag_fixture",
                "feature_source_hash": "phase17-ag-fixture-hash",
                "required_features": [],
                "optional_features": [],
                "missing_features": [],
                "defaulted_features": [],
                "temporal_validation_status": "PASS",
                "feature_version": "runtime_v2_pm_feature_input_v1",
                "data_until": BUSINESS_DATE,
                "created_at": BUSINESS_DATE + "T08:00:00+09:00",
            }
            for index, symbol in enumerate(SYMBOLS)
        ]
    ).to_parquet(feature_dir / "position_feature_input.parquet", index=False)
    pd.DataFrame([_feature_row(symbol, CANDIDATE_REQUIRED_COLUMNS) for symbol in SYMBOLS]).to_parquet(
        feature_dir / "candidate_features.parquet",
        index=False,
    )
    pd.DataFrame([_feature_row(symbol, OPPORTUNITY_REQUIRED_COLUMNS) for symbol in SYMBOLS]).to_parquet(
        feature_dir / "opportunity_feature_input.parquet",
        index=False,
    )
    pd.DataFrame([{"target_date": BUSINESS_DATE, "code": "__POLICY_INPUT__"}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )
    _write_json(
        operations_root / "feature_date_contract" / f"{BUSINESS_DATE}.json",
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
            "opportunity_schema_status": "READY",
            "pm_schema_status": "READY",
            "consumer_readiness_artifact_path": str(operations_root / "feature_consumer_readiness" / f"{BUSINESS_DATE}.json"),
            "contract_artifact_path": str(operations_root / "feature_date_contract" / f"{BUSINESS_DATE}.json"),
        },
    )
    return operations_root / "feature_artifacts"


def _write_buy_ai_opportunity(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "buy_ai" / BUSINESS_DATE / "opportunity_rankings.json",
        {
            "schema_version": "runtime_v2_opportunity_rankings_v1",
            "status": "PASS",
            "model_version": "fixture",
            "generated_at": BUSINESS_DATE + "T08:30:00+09:00",
            "feature_date": BUSINESS_DATE,
            "rankings": [
                {
                    "target_date": BUSINESS_DATE,
                    "code": symbol,
                    "expected_edge_score": 0.01,
                    "buy_rank": index + 1,
                    "downside_risk_score": 0.4,
                }
                for index, symbol in enumerate(SYMBOLS)
            ],
        },
    )


def _feature_row(symbol: str, required_columns: tuple[str, ...]) -> dict:
    row = {"target_date": BUSINESS_DATE, "code": symbol}
    for column in required_columns:
        row.setdefault(column, 0.0)
    return row


def _write_calendar(root: Path) -> None:
    rows = [
        {"Date": PREVIOUS_TRADING_DATE, "HolidayDivision": "1"},
        {"Date": BUSINESS_DATE, "HolidayDivision": "1"},
    ]
    _write_jsonl(root / "operations" / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.jsonl", rows)


def _write_empty_no_action_pending(root: Path, tmp_path: Path) -> None:
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-order-plan-morning-no-signal-2026-07-07",
            "state": "EMPTY",
            "status": "EMPTY",
            "active_pending": False,
            "environment": "historical",
            "target_session_date": BUSINESS_DATE,
            "items": [],
            "consume": {"consumed": False},
            "safety_context": _historical_safety_context(tmp_path),
        },
    )


def _write_empty_production_pending(root: Path) -> None:
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-order-plan-production-no-signal-2026-07-07",
            "state": "EMPTY",
            "status": "EMPTY",
            "active_pending": False,
            "environment": "production",
            "target_session_date": BUSINESS_DATE,
            "items": [],
            "consume": {"consumed": False},
            "no_action_reason": "NO_SIGNAL:production_fixture",
        },
    )


def _historical_allow_safety_decision() -> RuntimeSafetyDecision:
    return RuntimeSafetyDecision(
        safety_decision_id="",
        safety_policy_version="historical_replay_neutral_safety_v1",
        safety_source="data_readiness_historical_temporal_authority",
        business_date=BUSINESS_DATE,
        runtime_mode="historical",
        decision="ALLOW",
        reason="historical_neutral_no_event_safety_ready",
        review_required=False,
        block_buy=False,
        block_sell=False,
        block_submit=False,
        halt_runtime=False,
        emergency_stop=False,
        generated_at=BUSINESS_DATE + "T08:30:00+09:00",
        expires_at="",
        safety_status="PASS",
        action_permissions={"sell_planning": "ALLOWED_FOR_REPLAY", "broker_write": "BLOCKED"},
    )


def _production_allow_safety_decision() -> RuntimeSafetyDecision:
    return RuntimeSafetyDecision(
        safety_decision_id="production-safety-pass",
        safety_policy_version="runtime_safety_v1",
        safety_source="production_safety_gate",
        business_date=BUSINESS_DATE,
        runtime_mode="production",
        decision="ALLOW",
        reason="production_safety_pass",
        review_required=False,
        block_buy=False,
        block_sell=False,
        block_submit=False,
        halt_runtime=False,
        emergency_stop=False,
        generated_at=BUSINESS_DATE + "T08:30:00+09:00",
        expires_at=BUSINESS_DATE + "T15:00:00+09:00",
        safety_status="PASS",
        action_permissions={"sell_planning": "ALLOWED", "broker_write": "ALLOWED"},
    )


def _historical_safety_context(tmp_path: Path) -> dict:
    return {
        "safety_authority": "historical_initial_no_external_effect",
        "safety_decision": "ALLOW",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "safety_source": "data_readiness_historical_temporal_authority",
        "safety_business_date": BUSINESS_DATE,
        "runtime_test_run_id": RUN_ID,
        "runtime_test_profile_id": PROFILE_ID,
        "runtime_test_evidence_root": str(_evidence_root(tmp_path)),
    }


def _historical_context(tmp_path: Path) -> dict:
    return {
        "runtime_mode": "historical",
        "broker_environment": "historical_simulated",
        "historical_replay": True,
        "simulation": True,
        "broker_write": False,
        "external_delivery": False,
        "tachibana_demo_write": False,
        "tachibana_production_write": False,
        "submit_enabled": False,
        "runtime_test_run_id": RUN_ID,
        "runtime_test_profile_id": PROFILE_ID,
        "runtime_test_evidence_root": str(_evidence_root(tmp_path)),
    }


def _evidence_root(tmp_path: Path) -> Path:
    return tmp_path / "reports" / "runtime_tests" / "runs" / RUN_ID


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
