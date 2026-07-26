from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.runtime_v2.data_readiness import (
    _resolve_data_readiness_operation_date,
    evaluate_runtime_data_readiness,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import (
    CANDIDATE_REQUIRED_COLUMNS,
    OPPORTUNITY_REQUIRED_COLUMNS,
)


class FixtureModel:
    pass


def test_phase20_bw_historical_20220812_uses_run_scoped_calendar_for_current_valuation(tmp_path: Path) -> None:
    business_date = "2022-08-12"
    previous_trading_date = "2022-08-10"
    run_id = "runtime-test-historical-extended-smoke-fixture"
    root = _runtime_root(
        tmp_path,
        business_date=business_date,
        previous_trading_date=previous_trading_date,
        valuation_as_of=previous_trading_date,
    )
    evidence_root = tmp_path / "reports" / "runtime_tests" / "runs" / run_id
    calendar_path = _write_run_scoped_calendar(evidence_root, business_date, _calendar_rows())
    _write_logical_input_manifest(evidence_root, business_date, calendar_path)
    feature_root = _write_feature_inputs(root / "operations" / "feature_artifacts", business_date, previous_trading_date)

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=business_date,
        mode="historical",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=business_date,
        candidate_model_path=_write_model(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_model(tmp_path / "opportunity.pkl"),
        runtime_test_evidence_root=evidence_root,
        runtime_test_run_id=run_id,
        runtime_test_profile_id="historical-extended-smoke",
        broker_environment="historical_simulated",
        broker_write=False,
        external_delivery=False,
    )

    assert "current_valuation_not_ready" not in result.payload["review_reasons"]
    assert result.payload["calendar_source"] == "historical_logical_input_manifest_trading_calendar"
    assert result.payload["market_calendar_authority_status"] == "PASS"
    assert result.payload["current_valuation_previous_trading_date"] == previous_trading_date
    assert result.payload["current_valuation_expected_date"] == previous_trading_date
    assert result.payload["current_valuation_status"] == "READY"
    assert result.payload["current_valuation_temporal_authority"] == "current_valuation_previous_trading_day_close"


def test_phase20_bw_historical_calendar_authority_boundaries(tmp_path: Path) -> None:
    run_id = "runtime-test-historical-calendar-fixture"
    evidence_root = tmp_path / "reports" / "runtime_tests" / "runs" / run_id
    for business_date in ("2022-08-10", "2022-08-15", "2022-05-06"):
        calendar_path = _write_run_scoped_calendar(evidence_root, business_date, _calendar_rows())
        _write_logical_input_manifest(evidence_root, business_date, calendar_path)

    assert _resolve_calendar(tmp_path, evidence_root, "2022-08-10")["previous_business_day"] == "2022-08-09"
    assert _resolve_calendar(tmp_path, evidence_root, "2022-08-15")["previous_business_day"] == "2022-08-12"
    assert _resolve_calendar(tmp_path, evidence_root, "2022-05-06")["previous_business_day"] == "2022-05-02"


def test_phase20_bw_missing_historical_calendar_authority_fails_closed(tmp_path: Path) -> None:
    evidence_root = tmp_path / "reports" / "runtime_tests" / "runs" / "missing-calendar"
    manifest_path = (
        evidence_root
        / "daily"
        / "2022-08-12"
        / "market_refresh"
        / "inputs"
        / "historical_asof"
        / "2022-08-12"
        / "logical_input_manifest.json"
    )
    _write_json(manifest_path, {"status": "PASS", "business_date": "2022-08-12", "logical_paths": {}})

    calendar = _resolve_calendar(tmp_path, evidence_root, "2022-08-12")

    assert calendar["calendar_authority_status"] == "REVIEW_REQUIRED"
    assert calendar["previous_business_day"] == ""
    assert calendar["calendar_authority_reason"] == "historical_logical_trading_calendar_missing"


def test_phase20_bw_invalid_historical_manifest_does_not_fallback(tmp_path: Path) -> None:
    evidence_root = tmp_path / "reports" / "runtime_tests" / "runs" / "invalid-manifest"
    calendar_path = tmp_path / ".runtime" / "operations" / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet"
    calendar_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(_calendar_rows()).to_parquet(calendar_path, index=False)
    manifest_path = (
        evidence_root
        / "daily"
        / "2022-08-12"
        / "market_refresh"
        / "inputs"
        / "historical_asof"
        / "2022-08-12"
        / "logical_input_manifest.json"
    )
    _write_json(
        manifest_path,
        {"status": "REVIEW_REQUIRED", "business_date": "2022-08-12", "logical_paths": {"trading_calendar": str(calendar_path)}},
    )

    calendar = _resolve_calendar(tmp_path, evidence_root, "2022-08-12")

    assert calendar["calendar_authority_status"] == "REVIEW_REQUIRED"
    assert calendar["previous_business_day"] == ""
    assert calendar["calendar_authority_reason"] == "historical_logical_input_manifest_not_pass"


def test_phase20_bw_production_demo_calendar_behavior_unchanged(tmp_path: Path) -> None:
    calendar = _resolve_data_readiness_operation_date(
        business_date="2022-08-12",
        mode="demo",
        broker_environment="demo",
        base_dir=tmp_path,
        operations_root=tmp_path / ".runtime" / "operations",
        runtime_test_evidence_root=None,
    )

    assert calendar["calendar_source"] == "fallback"
    assert calendar["previous_business_day"] == "2022-08-11"
    assert calendar["calendar_authority_type"] == "operations_calendar_or_fallback"


def _resolve_calendar(tmp_path: Path, evidence_root: Path, business_date: str) -> dict[str, Any]:
    return _resolve_data_readiness_operation_date(
        business_date=business_date,
        mode="historical",
        broker_environment="historical_simulated",
        base_dir=tmp_path,
        operations_root=tmp_path / ".runtime" / "operations",
        runtime_test_evidence_root=evidence_root,
    )


def _runtime_root(
    tmp_path: Path,
    *,
    business_date: str,
    previous_trading_date: str,
    valuation_as_of: str,
) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "temporal_schema_version": "runtime_v2_current_temporal_v1",
            "environment": "historical",
            "business_date": previous_trading_date,
            "position_state_as_of": previous_trading_date,
            "valuation_as_of": valuation_as_of,
            "source_market_date": valuation_as_of,
            "last_execution_date": previous_trading_date,
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
            "business_date": business_date,
            "environment": "historical",
            "runtime_mode": "historical",
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
            "current_safety_state": "NORMAL",
        },
    )
    _write_json(
        root / "runtime_state" / "market" / business_date / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": business_date,
            "runtime_business_date": business_date,
            "market_date": business_date,
            "as_of": business_date,
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": 1,
            "market_summary": {"status": "READY"},
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "state": "CONSUMED",
            "status": "CONSUMED",
            "active_pending": True,
            "environment": "historical",
            "target_session_date": previous_trading_date,
            "consume": {"consumed": True},
            "safety_context": {
                "safety_authority": "historical_initial_no_external_effect",
                "safety_decision": "ALLOW",
                "safety_policy_version": "historical_replay_neutral_safety_v1",
                "safety_source": "data_readiness_historical_temporal_authority",
                "safety_business_date": previous_trading_date,
            },
        },
    )
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _write_feature_inputs(feature_root: Path, business_date: str, previous_trading_date: str) -> Path:
    feature_dir = feature_root / business_date
    feature_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{column: _value_for_column(column, business_date) for column in CANDIDATE_REQUIRED_COLUMNS}]).to_parquet(
        feature_dir / "candidate_features.parquet",
        index=False,
    )
    pd.DataFrame([{column: _value_for_column(column, business_date) for column in OPPORTUNITY_REQUIRED_COLUMNS}]).to_parquet(
        feature_dir / "opportunity_feature_input.parquet",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "target_date": business_date,
                "feature_as_of_date": business_date,
                "position_state_as_of": previous_trading_date,
                "entry_date": previous_trading_date,
                "code": "81050",
                "broker_issue_code": "81050",
                "holding_days": 1,
                "average_price": 100.0,
                "current_price": 101.0,
                "unrealized_return": 0.01,
                "quantity": 100.0,
                "price_momentum_return_5d": 0.01,
                "price_momentum_return_20d": 0.02,
                "trend_close_over_ma_20d": 1.01,
                "trend_ma_5_20_ratio": 1.01,
                "volume_momentum_ratio_5d": 1.0,
                "volatility_return_std_20d": 0.02,
                "feature_source_artifact": "fixture",
                "feature_source_hash": "fixture",
                "required_features": [],
                "optional_features": [],
                "missing_features": [],
                "defaulted_features": [],
                "temporal_validation_status": "PASS",
                "feature_version": "runtime_v2_pm_feature_input_v1",
                "data_until": business_date,
                "created_at": business_date + "T08:00:00+09:00",
                "no_position_reason": "",
            }
        ]
    ).to_parquet(feature_dir / "position_feature_input.parquet", index=False)
    pd.DataFrame([{"target_date": business_date, "code": "__POLICY_INPUT__"}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )
    _write_json(
        feature_root.parent / "feature_date_contract" / f"{business_date}.json",
        {
            "status": "PASS",
            "requested_feature_date": business_date,
            "selected_feature_date": business_date,
            "feature_artifact_dir": str(feature_dir),
            "generated_feature_artifacts": {
                "candidate_features.parquet": str(feature_dir / "candidate_features.parquet"),
                "opportunity_feature_input.parquet": str(feature_dir / "opportunity_feature_input.parquet"),
                "position_feature_input.parquet": str(feature_dir / "position_feature_input.parquet"),
                "capital_policy_input.parquet": str(feature_dir / "capital_policy_input.parquet"),
            },
            "missing_feature_artifacts": [],
            "requested_missing_feature_artifacts": [],
            "consumer_ready": True,
            "candidate_schema_status": "READY",
            "opportunity_schema_status": "READY",
            "pm_schema_status": "READY",
        },
    )
    return feature_root


def _value_for_column(column: str, business_date: str) -> Any:
    if column == "target_date":
        return business_date
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


def _calendar_rows() -> list[dict[str, str]]:
    return [
        {"Date": "2022-05-02", "HolDiv": "1"},
        {"Date": "2022-05-03", "HolDiv": "0"},
        {"Date": "2022-05-04", "HolDiv": "0"},
        {"Date": "2022-05-05", "HolDiv": "0"},
        {"Date": "2022-05-06", "HolDiv": "1"},
        {"Date": "2022-08-09", "HolDiv": "1"},
        {"Date": "2022-08-10", "HolDiv": "1"},
        {"Date": "2022-08-11", "HolDiv": "0"},
        {"Date": "2022-08-12", "HolDiv": "1"},
        {"Date": "2022-08-15", "HolDiv": "1"},
    ]


def _write_run_scoped_calendar(evidence_root: Path, business_date: str, rows: list[dict[str, str]]) -> Path:
    path = (
        evidence_root
        / "daily"
        / business_date
        / "market_refresh"
        / "inputs"
        / "historical_asof"
        / business_date
        / "raw"
        / "jquants"
        / "trading_calendar"
        / "data.parquet"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _write_logical_input_manifest(evidence_root: Path, business_date: str, calendar_path: Path) -> None:
    _write_json(
        evidence_root
        / "daily"
        / business_date
        / "market_refresh"
        / "inputs"
        / "historical_asof"
        / business_date
        / "logical_input_manifest.json",
        {
            "status": "PASS",
            "business_date": business_date,
            "logical_cutoff": business_date,
            "logical_paths": {"trading_calendar": str(calendar_path)},
        },
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows), encoding="utf-8")
