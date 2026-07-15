from __future__ import annotations

import json
import pickle
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness


BUSINESS_DATE = "2026-07-08"
FEATURE_DATE = "2026-07-07"
NON_TRADING_DAY = "2026-09-21"


class FixtureModel:
    pass


def test_phase15aq_data_readiness_job_writes_ready_artifact(tmp_path):
    runtime_root = _runtime_root(tmp_path, business_date=BUSINESS_DATE, current_as_of=BUSINESS_DATE)
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts", feature_date=FEATURE_DATE)
    policy_path = _write_policy(tmp_path / "capital_deployment.json")
    candidate_model = _write_file(tmp_path / "candidate.pkl")
    opportunity_model = _write_file(tmp_path / "opportunity.pkl")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "data_readiness",
            "--readiness-scope",
            "morning",
            "--business-date",
            BUSINESS_DATE,
            "--feature-date",
            FEATURE_DATE,
            "--feature-root",
            str(feature_root),
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            "--candidate-model-path",
            str(candidate_model),
            "--opportunity-model-path",
            str(opportunity_model),
        ]
    )

    artifact = _load_json(runtime_root / "runtime_state" / "data_readiness" / BUSINESS_DATE / "data_readiness.json")
    manifest = _latest_manifest(runtime_root, BUSINESS_DATE)
    notification = _load_json(tmp_path / "reports" / "runtime_v2" / BUSINESS_DATE / "notification_payload.json")

    assert exit_code == 0
    assert artifact["overall_status"] == "READY"
    assert artifact["candidate_status"] == "PRE_INFERENCE_READY"
    assert artifact["opportunity_status"] == "PRE_INFERENCE_READY"
    assert artifact["gate_does_not_generate_ai_decisions"] is True
    assert manifest["data_readiness_status"] == "READY"
    assert notification["data_readiness_status"] == "READY"


def test_phase15aq_schema_mismatch_blocks_before_morning_ai(tmp_path):
    runtime_root = _runtime_root(tmp_path, business_date=BUSINESS_DATE, current_as_of=BUSINESS_DATE)
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts", feature_date=FEATURE_DATE)
    bad_candidate = pd.read_parquet(feature_root / FEATURE_DATE / "candidate_features.parquet").drop(
        columns=["price_momentum_return_20d"]
    )
    bad_candidate.to_parquet(feature_root / FEATURE_DATE / "candidate_features.parquet", index=False)
    policy_path = _write_policy(tmp_path / "capital_deployment.json")
    candidate_model = _write_file(tmp_path / "candidate.pkl")
    opportunity_model = _write_file(tmp_path / "opportunity.pkl")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            BUSINESS_DATE,
            "--feature-date",
            FEATURE_DATE,
            "--feature-root",
            str(feature_root),
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            "--candidate-model-path",
            str(candidate_model),
            "--opportunity-model-path",
            str(opportunity_model),
        ]
    )

    manifest = _latest_manifest(runtime_root, BUSINESS_DATE)
    stage_names = {stage["name"] for stage in manifest["stages"]}
    artifact = _load_json(runtime_root / "runtime_state" / "data_readiness" / BUSINESS_DATE / "data_readiness.json")

    assert exit_code == 20
    assert artifact["overall_status"] == "REVIEW_REQUIRED"
    assert "price_momentum_return_20d" in artifact["missing_columns"]
    assert "runtime_data_readiness_gate" in stage_names
    assert "candidate_opportunity_ai_runtime_producer" not in stage_names
    assert "morning_ai_planning_pending_pipeline" not in stage_names


def test_phase15aq_stale_current_is_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, business_date=BUSINESS_DATE, current_as_of="2026-07-07")
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts", feature_date=FEATURE_DATE)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_file(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_file(tmp_path / "opportunity.pkl"),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "current_stale" in result.payload["review_reasons"]
    assert result.payload["current_expected_as_of"] == BUSINESS_DATE
    assert result.payload["current_actual_as_of"] == "2026-07-07"


def test_phase15aq_non_trading_day_demo_override_allows_expected_previous_current(tmp_path):
    runtime_root = _runtime_root(tmp_path, business_date=NON_TRADING_DAY, current_as_of="2026-09-18")
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts", feature_date="2026-09-18")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=NON_TRADING_DAY,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date="2026-09-18",
        candidate_model_path=_write_file(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_file(tmp_path / "opportunity.pkl"),
        allow_non_trading_day_demo=True,
    )

    assert result.status == "READY"
    assert result.payload["non_trading_day_demo_override"] is True
    assert result.payload["current_expected_as_of"] == "2026-09-18"
    assert result.payload["acceptance_scope"] == "demo_acceptance_only"


def test_phase15aq_non_trading_day_demo_override_rejects_older_current(tmp_path):
    runtime_root = _runtime_root(tmp_path, business_date=NON_TRADING_DAY, current_as_of="2026-09-17")
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts", feature_date="2026-09-18")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=NON_TRADING_DAY,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date="2026-09-18",
        candidate_model_path=_write_file(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_file(tmp_path / "opportunity.pkl"),
        allow_non_trading_day_demo=True,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "current_stale" in result.payload["review_reasons"]


def test_phase15aq_production_override_is_halt(tmp_path):
    runtime_root = _runtime_root(tmp_path, business_date=NON_TRADING_DAY, current_as_of="2026-09-18", mode="production")
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts", feature_date="2026-09-18")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=NON_TRADING_DAY,
        mode="production",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date="2026-09-18",
        candidate_model_path=_write_file(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_file(tmp_path / "opportunity.pkl"),
        allow_non_trading_day_demo=True,
    )

    assert result.status == "HALT"
    assert "non_trading_day_demo_override_forbidden_in_production" in result.payload["halt_reasons"]


def test_phase15aq_scope_does_not_require_candidate_for_sell_planning(tmp_path):
    runtime_root = _runtime_root(
        tmp_path,
        business_date=BUSINESS_DATE,
        current_as_of=BUSINESS_DATE,
        positions=[_position("3926")],
    )
    pm_opportunity, pm_feature = _write_pm_inputs(tmp_path, symbols=("3926",), feature_date=BUSINESS_DATE)
    _write_broker_snapshot(runtime_root)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="sell_planning",
        pm_opportunity_path=pm_opportunity,
        pm_feature_path=pm_feature,
    )

    assert result.status == "READY"
    assert result.payload["candidate_status"] == "NOT_REQUIRED"
    assert result.payload["pm_status"] == "READY"
    assert "candidate_model" not in result.payload["missing_evidence"]


def test_phase17r_historical_data_readiness_uses_contract_and_historical_scope(tmp_path):
    business_date = "2026-07-06"
    runtime_root = _runtime_root(tmp_path, business_date=business_date, current_as_of="2026-07-14", mode="historical")
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts", feature_date=business_date)
    _write_feature_inputs(runtime_root / "operations" / "feature_artifacts", feature_date="2026-07-14")
    _write_feature_date_contract(runtime_root, business_date=business_date, selected_feature_date=business_date)
    _write_safety_decision(runtime_root, business_date="2026-07-10", mode="historical")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="historical",
        readiness_scope="morning",
        feature_root=feature_root,
        candidate_model_path=_write_file(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_file(tmp_path / "opportunity.pkl"),
        broker_environment="historical_simulated",
        runtime_test_evidence_root=tmp_path / "reports" / "runtime_tests" / "runs" / "phase17r",
    )

    assert result.status == "READY"
    assert result.payload["acceptance_scope"] == "historical_replay"
    assert result.payload["runtime_environment_status"] == "READY"
    assert result.payload["components"]["runtime_environment"]["reason"] == "historical_replay_environment_ready"
    assert result.payload["selected_feature_date"] == business_date
    assert result.payload["components"]["feature"]["readiness_artifact_path"].endswith(f"{business_date}.json")
    assert result.payload["current_actual_as_of"] == business_date
    assert result.payload["components"]["safety"]["reason"] == "historical_neutral_no_event_safety_ready"
    assert "runtime_acceptance_requires_demo_mode" not in result.payload["halt_reasons"]
    assert not (runtime_root / "runtime_state" / "data_readiness" / business_date / "data_readiness.json").exists()
    assert result.artifact_path.endswith("/daily/2026-07-06/data_readiness/data_readiness.json")


def test_phase17r_historical_missing_feature_contract_is_review_required(tmp_path):
    business_date = "2026-07-06"
    runtime_root = _runtime_root(tmp_path, business_date=business_date, current_as_of=business_date, mode="historical")
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts", feature_date=business_date)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="historical",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=business_date,
        candidate_model_path=_write_file(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_file(tmp_path / "opportunity.pkl"),
        broker_environment="historical_simulated",
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "historical_feature_date_contract_missing" in result.payload["review_reasons"]


def test_phase15aq_stale_approved_pending_is_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, business_date=BUSINESS_DATE, current_as_of=BUSINESS_DATE)
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-stale",
            "state": "APPROVED",
            "environment": "demo",
            "target_session_date": "2026-07-07",
            "items": [],
            "pending_policy_hash": "hash",
            "safety_decision_id": "safety",
        },
    )
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts", feature_date=FEATURE_DATE)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_file(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_file(tmp_path / "opportunity.pkl"),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "stale_approved_pending_exists" in result.payload["review_reasons"]


def _runtime_root(
    tmp_path: Path,
    *,
    business_date: str,
    current_as_of: str,
    mode: str = "demo",
    positions: list[dict] | None = None,
) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15aq",
            "environment": mode,
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": current_as_of,
            "business_date": business_date,
            "updated_at": current_as_of + "T00:00:00Z",
            "positions": positions or [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": sum(float(item.get("market_value") or 0) for item in positions or []),
            "total_equity": 1_000_000 + sum(float(item.get("market_value") or 0) for item in positions or []),
            "review_required": False,
            "current_state_confirmed_empty": not bool(positions),
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "environment": mode, "items": []})
    _write_runtime_state(root, business_date=business_date, mode=mode)
    _write_safety_decision(root, business_date=business_date, mode=mode)
    _write_market_evidence(root, business_date=business_date)
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _write_runtime_state(root: Path, *, business_date: str, mode: str) -> None:
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "runtime_v2_operation_state_v1",
            "role": "authoritative_runtime_operation_state",
            "business_date": business_date,
            "generated_at": business_date + "T00:00:00Z",
            "updated_at": business_date + "T00:00:00Z",
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


def _position(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "quantity": 100,
        "average_price": 1000,
        "current_price": 1100,
        "market_value": 110000,
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": BUSINESS_DATE,
        "holding_days": 10,
        "peak_return": 0.15,
        "unrealized_pnl": 10000,
    }


def _write_feature_inputs(feature_root: Path, *, feature_date: str) -> Path:
    feature_dir = feature_root / feature_date
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = [_candidate_row("7203", feature_date), _candidate_row("6501", feature_date)]
    pd.DataFrame(rows).to_parquet(feature_dir / "candidate_features.parquet", index=False)
    pd.DataFrame(rows).to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame(columns=["target_date", "code", "no_position_reason"]).to_parquet(
        feature_dir / "position_feature_input.parquet",
        index=False,
    )
    return feature_root


def _candidate_row(symbol: str, feature_date: str) -> dict:
    return {
        "target_date": feature_date,
        "code": symbol,
        "liquidity_avg_volume_20d": 1_000_000,
        "market_breadth_20d": 0.5,
        "market_breadth_5d": 0.5,
        "market_downtrend_context": 0.0,
        "market_downtrend_flag": False,
        "market_ma_5_20_ratio": 1.0,
        "market_return_20d": 0.02,
        "market_return_5d": 0.01,
        "market_risk_flag": False,
        "market_volatility_20d": 0.02,
        "missing_flags_insufficient_history": False,
        "missing_flags_price": False,
        "missing_flags_volume": False,
        "price_momentum_return_20d": 0.1,
        "price_momentum_return_5d": 0.05,
        "price_momentum_return_60d": 0.2,
        "sector_breadth_20d": 0.5,
        "sector_momentum_flag": True,
        "sector_rank_20d": 1,
        "sector_return_20d": 0.03,
        "sector_return_5d": 0.01,
        "sector_weak_flag": False,
        "stock_vs_sector_return_20d": 0.01,
        "trend_close_over_ma_20d": 1.0,
        "trend_ma_20_60_ratio": 1.0,
        "trend_ma_5_20_ratio": 1.0,
        "volatility_return_std_20d": 0.02,
        "volume_momentum_ratio_1d_20d": 1.2,
        "volume_momentum_ratio_5d": 1.1,
    }


def _write_pm_inputs(tmp_path: Path, *, symbols: tuple[str, ...], feature_date: str) -> tuple[Path, Path]:
    opportunity = tmp_path / "pm_opportunity.csv"
    feature = tmp_path / "pm_feature.csv"
    pd.DataFrame(
        [
            {
                "target_date": feature_date,
                "code": symbol,
                "expected_edge_score": 0.1,
                "buy_rank": 1,
                "downside_risk_score": 0.2,
            }
            for symbol in symbols
        ]
    ).to_csv(opportunity, index=False)
    pd.DataFrame([{"target_date": feature_date, "code": symbol} for symbol in symbols]).to_csv(feature, index=False)
    return opportunity, feature


def _write_broker_snapshot(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json",
        {
            "schema_version": "runtime_v2_broker_readonly_snapshot_v1",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "broker_mode": "demo",
            "production_equivalent": False,
            "review_required": False,
            "positions": [],
            "orders": [],
            "executions": [],
        },
    )


def _write_market_evidence(root: Path, *, business_date: str) -> None:
    _write_json(
        root / "runtime_state" / "market" / business_date / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": business_date,
            "as_of": business_date,
            "generated_at": business_date + "T00:00:00Z",
            "quote_count": 2,
            "market_summary": {"source": "fixture"},
        },
    )


def _write_policy(path: Path) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "target_investment_ratio": 0.85,
            "cash_buffer": 0.05,
            "max_exposure": 850_000,
            "max_position_weight": 0.2,
            "max_positions": 5,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {"buy_amount": None, "sell_liquidation_amount": None},
        },
    )
    return path


def _write_safety_decision(root: Path, *, business_date: str, mode: str) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase15aq",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": "fixture",
            "business_date": business_date,
            "runtime_mode": mode,
            "decision": "ALLOW",
            "reason": "phase15aq fixture allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": business_date + "T00:00:00+09:00",
            "expires_at": business_date + "T23:59:59+09:00",
        },
    )


def _write_feature_date_contract(root: Path, *, business_date: str, selected_feature_date: str) -> None:
    path = root / "operations" / "feature_date_contract" / f"{business_date}.json"
    _write_json(
        path,
        {
            "status": "PASS",
            "reason": "requested_feature_artifacts_available",
            "requested_feature_date": business_date,
            "selected_feature_date": selected_feature_date,
            "latest_available_market_date": selected_feature_date,
            "carryover_used": selected_feature_date != business_date,
            "carryover_reason": "",
            "freshness_lag_business_days": 0,
            "freshness_limit_business_days": 1,
            "feature_artifact_dir": str(root / "operations" / "feature_artifacts" / selected_feature_date),
            "generated_feature_artifacts": {},
            "missing_feature_artifacts": [],
            "requested_feature_artifact_dir": str(root / "operations" / "feature_artifacts" / business_date),
            "requested_missing_feature_artifacts": [],
            "price_source_alignment": "selected_feature_date",
            "consumer_ready": True,
            "candidate_schema_status": "READY",
            "candidate_missing_columns": [],
            "opportunity_schema_status": "READY",
            "pm_schema_status": "READY",
            "consumer_readiness_artifact_path": str(root / "operations" / "feature_consumer_readiness" / f"{selected_feature_date}.json"),
            "contract_artifact_path": str(path),
        },
    )


def _write_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(
            {
                "model": FixtureModel(),
                "feature_columns": ["feature__price_momentum_return_20d"],
                "model_version": "fixture_model_v1",
            },
            handle,
        )
    return path


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_manifest(runtime_root: Path, business_date: str) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / business_date).glob("*.json"))
    return _load_json(manifests[-1])
