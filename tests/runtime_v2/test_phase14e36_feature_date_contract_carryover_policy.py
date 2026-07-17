import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.market_refresh import pipeline as market_refresh_pipeline
from ai_fund_lab_v2.runtime_v2.market_refresh.pipeline import run_runtime_v2_market_refresh_pipeline


ARTIFACTS = (
    "candidate_features.parquet",
    "opportunity_feature_input.parquet",
    "position_feature_input.parquet",
    "capital_policy_input.parquet",
)


class CandidateFixtureModel:
    def predict_proba(self, matrix):
        values = np.asarray(matrix, dtype=float)[:, 0]
        scores = np.clip(values, 0.0, 1.0)
        return np.column_stack([1.0 - scores, scores])


class OpportunityFixtureModel:
    def predict(self, matrix):
        return np.asarray(matrix, dtype=float)[:, 0]


def test_phase14e36_market_refresh_emits_explicit_carryover_contract(tmp_path, monkeypatch):
    operations_root = tmp_path / ".runtime" / "operations"
    _write_feature_inputs(operations_root / "feature_artifacts", feature_date="2026-07-07")

    def fake_operations_market_refresh(**kwargs):
        return {
            "status": "BLOCK",
            "blocked_reasons": ["api_fetch_failed:JQuantsClientError", "data_until_before_decision_for"],
            "jquants_api_fetch_executed": True,
            "canonical_normalized_updated": True,
            "feature_refresh_executed": True,
            "feature_refresh_status": "FEATURES_READY",
            "latest_available_market_date": "2026-07-07",
            "data_quality_status": "BLOCK",
            "feature_freshness_status": "MARKET_DATA_NOT_YET_AVAILABLE",
        }

    monkeypatch.setattr(market_refresh_pipeline, "_run_operations_market_refresh", fake_operations_market_refresh)

    result = run_runtime_v2_market_refresh_pipeline(
        business_date="2026-07-08",
        operations_root=operations_root,
        allow_api_fetch=True,
    )

    contract_path = operations_root / "feature_date_contract" / "2026-07-08.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    assert result.status == "PASS"
    assert result.reason == "carryover_feature_artifacts_available"
    assert result.requested_feature_date == "2026-07-08"
    assert result.selected_feature_date == "2026-07-07"
    assert result.carryover_used is True
    assert result.freshness_lag_business_days == 1
    assert set(result.generated_feature_artifacts) == set(ARTIFACTS)
    assert contract["carryover_used"] is True
    assert contract["selected_feature_date"] == "2026-07-07"


def test_phase14e36_morning_uses_selected_carryover_feature_date(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")
    feature_root = _write_feature_inputs(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        feature_date="2026-07-08",
    )
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    opportunity_model_path = _write_opportunity_model(tmp_path / "opportunity_model.pkl")
    _write_json(
        tmp_path / ".runtime" / "operations" / "feature_date_contract" / "2026-07-09.json",
        {
            "status": "PASS",
            "reason": "carryover_feature_artifacts_available",
            "requested_feature_date": "2026-07-09",
            "selected_feature_date": "2026-07-08",
            "latest_available_market_date": "2026-07-08",
            "carryover_used": True,
            "carryover_reason": "requested_feature_date_missing_latest_available_within_freshness_limit",
            "freshness_lag_business_days": 1,
            "freshness_limit_business_days": 1,
            "feature_artifact_dir": str(feature_root / "2026-07-08"),
            "generated_feature_artifacts": {name: str(feature_root / "2026-07-08" / name) for name in ARTIFACTS},
            "missing_feature_artifacts": [],
            "requested_feature_artifact_dir": str(feature_root / "2026-07-09"),
            "requested_missing_feature_artifacts": list(ARTIFACTS),
            "price_source_alignment": "selected_feature_date",
            "contract_artifact_path": str(
                tmp_path / ".runtime" / "operations" / "feature_date_contract" / "2026-07-09.json"
            ),
        },
    )

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            "2026-07-09",
            "--feature-root",
            str(feature_root),
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            "--candidate-model-path",
            str(_write_candidate_model(tmp_path / "candidate_model.pkl")),
            "--opportunity-model-path",
            str(opportunity_model_path),
            "--opportunity-training-metrics-path",
            str(_write_opportunity_metrics(tmp_path / "opportunity_training_metrics.json", opportunity_model_path)),
        ]
    )

    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        next((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-09").glob("*.json")).read_text(
            encoding="utf-8"
        )
    )
    morning_stage = next(stage for stage in manifest["stages"] if stage["name"] == "morning_ai_planning_pending_pipeline")
    readiness_stage = next(stage for stage in manifest["stages"] if stage["name"] == "runtime_data_readiness_gate")
    order_plan = json.loads((runtime_root / "runtime_state" / "morning_pipeline" / "2026-07-09" / "order_plan.json").read_text(encoding="utf-8"))
    public_report = (tmp_path / "reports" / "public" / "runtime_v2" / "latest.md").read_text(encoding="utf-8")

    assert exit_code == 0
    assert pending["state"] == "APPROVED"
    assert readiness_stage["details"]["feature_date_contract"]["requested_feature_date"] == "2026-07-09"
    assert readiness_stage["details"]["feature_date_contract"]["selected_feature_date"] == "2026-07-08"
    assert pending["feature_date_contract"]["requested_feature_date"] == "2026-07-08"
    assert pending["feature_date_contract"]["selected_feature_date"] == "2026-07-08"
    assert pending["feature_date_contract"]["carryover_used"] is False
    assert all(item["price_as_of"] == "2026-07-08" for item in pending["items"])
    assert morning_stage["status"] == "PASS"
    assert morning_stage["details"]["feature_date"] == "2026-07-08"
    assert readiness_stage["details"]["feature_date_contract"]["carryover_used"] is True
    assert readiness_stage["details"]["feature_date_contract"]["freshness_lag_business_days"] == 1
    assert "feature_input_missing" not in morning_stage["details"]["reason"]
    assert order_plan["feature_date_contract"]["selected_feature_date"] == "2026-07-08"
    assert "Market data freshness" in public_report


def test_phase14e36_stale_carryover_blocks_morning(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")
    feature_root = _write_feature_inputs(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        feature_date="2026-07-06",
    )
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_json(
        tmp_path / ".runtime" / "operations" / "feature_date_contract" / "2026-07-09.json",
        {
            "status": "REVIEW_REQUIRED",
            "reason": "carryover_stale",
            "requested_feature_date": "2026-07-09",
            "selected_feature_date": "2026-07-06",
            "latest_available_market_date": "2026-07-06",
            "carryover_used": True,
            "carryover_reason": "requested_feature_date_missing_but_latest_available_is_stale",
            "freshness_lag_business_days": 2,
            "freshness_limit_business_days": 1,
            "feature_artifact_dir": str(feature_root / "2026-07-06"),
            "generated_feature_artifacts": {name: str(feature_root / "2026-07-06" / name) for name in ARTIFACTS},
            "missing_feature_artifacts": [],
            "requested_feature_artifact_dir": str(feature_root / "2026-07-09"),
            "requested_missing_feature_artifacts": list(ARTIFACTS),
            "price_source_alignment": "selected_feature_date",
        },
    )

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            "2026-07-09",
            "--feature-root",
            str(feature_root),
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            "--candidate-model-path",
            str(_write_candidate_model(tmp_path / "candidate_model.pkl")),
            "--opportunity-model-path",
            str(_write_opportunity_model(tmp_path / "opportunity_model.pkl")),
        ]
    )

    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        next((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-09").glob("*.json")).read_text(
            encoding="utf-8"
        )
    )
    readiness_stage = next(stage for stage in manifest["stages"] if stage["name"] == "runtime_data_readiness_gate")

    assert exit_code == 20
    assert pending["state"] == "PENDING_APPROVAL"
    assert readiness_stage["status"] == "REVIEW_REQUIRED"
    assert "carryover_stale" in readiness_stage["details"]["review_reasons"]
    assert readiness_stage["details"]["feature_date_contract"]["freshness_lag_business_days"] == 2


def _write_fixed_current(root: Path) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-e36",
            "environment": "demo",
            "source": "phase14e8_demo_operation_initial_state",
            "as_of": "2026-07-09",
            "positions": [],
            "cash": 1_000_000.0,
            "buying_power": 1_000_000.0,
            "market_value": 0,
            "total_equity": 1_000_000.0,
            "review_required": False,
            "production_equivalent": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
            "generated_from": ["fixture"],
            "created_at": "2026-07-09",
            "updated_at": "2026-07-09",
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-e36-initial",
            "state": "PENDING_APPROVAL",
            "environment": "demo",
            "created_at": "2026-07-09T00:00:00+09:00",
            "updated_at": "2026-07-09T00:00:00+09:00",
            "items": [],
        },
    )
    _write_json(root / "runtime_state" / "current_state.json", {"state": "CURRENT_STATE_LOADED"})
    for name in ("orders", "executions", "positions", "cash", "events"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    _write_safety_decision(root)
    _write_market_evidence(root, business_date="2026-07-09")
    return root


def _write_feature_inputs(root: Path, *, feature_date: str, candidate_codes=("72030", "65010", "67580")) -> Path:
    _write_current_authority(root.parent.parent, business_date=feature_date)
    feature_dir = root / feature_date
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "target_date": feature_date,
            "as_of_date": feature_date,
            "code": code,
            "universe_eligible": True,
            "price_momentum_return_20d": 0.9 - index * 0.1,
            "price_momentum_return_5d": 0.5 - index * 0.05,
            "trend_close_over_ma_20d": 0.20,
            "missing_flags_insufficient_history": False,
            "missing_flags_price": False,
            "missing_flags_volume": False,
            "price_momentum_return_60d": 0.6 - index * 0.1,
            "trend_ma_20_60_ratio": 1.01,
            "trend_ma_5_20_ratio": 1.02,
            "volatility_return_std_20d": 0.02,
            "volume_momentum_ratio_1d_20d": 1.2,
            "liquidity_avg_volume_20d": 1_000_000 - index,
            "market_breadth_20d": 0.5,
            "market_breadth_5d": 0.5,
            "market_downtrend_context": 0.0,
            "market_downtrend_flag": False,
            "market_ma_5_20_ratio": 1.0,
            "market_return_20d": 0.02,
            "market_return_5d": 0.01,
            "market_risk_flag": False,
            "market_volatility_20d": 0.02,
            "volume_momentum_ratio_5d": 1.1,
            "data_until": feature_date,
            "sector_breadth_20d": 0.5,
            "sector_momentum_flag": True,
            "sector_rank_20d": index + 1,
            "sector_return_20d": 0.03,
            "sector_return_5d": 0.01,
            "sector_weak_flag": False,
            "stock_vs_sector_return_20d": 0.01,
        }
        for index, code in enumerate(candidate_codes)
    ]
    candidate = pd.DataFrame(rows)
    candidate.to_parquet(feature_dir / "candidate_features.parquet", index=False)
    candidate.to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame(columns=["target_date", "code", "data_until", "no_position_reason"]).to_parquet(
        feature_dir / "position_feature_input.parquet",
        index=False,
    )
    pd.DataFrame([{"target_date": feature_date, "code": "__POLICY_INPUT__", "data_until": feature_date}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )
    price_dir = root.parent / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily"
    price_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"Code": str(code), "Date": feature_date, "Close": 1000.0 + index * 100, "PriceSource": "fixture_close"}
            for index, code in enumerate(candidate_codes)
        ]
    ).to_parquet(price_dir / "data.parquet", index=False)
    return root


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
            "manual_review_threshold": {
                "buy_amount": None,
                "sell_liquidation_amount": None,
            },
        },
    )
    return path


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_current_authority(runtime_root: Path, *, business_date: str) -> None:
    if (runtime_root / "persistent_ledger" / "state.json").exists():
        return
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-e36-feature",
            "environment": "demo",
            "business_date": business_date,
            "as_of": business_date,
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
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
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": 1,
            "market_summary": {"source": "phase14e36_fixture"},
        },
    )


def _write_candidate_model(path: Path) -> Path:
    _write_pickle(
        path,
        {
            "model": CandidateFixtureModel(),
            "feature_columns": ["feature__price_momentum_return_20d"],
            "model_version": "candidate_model_phase15ag_fixture",
        },
    )
    return path


def _write_opportunity_model(path: Path) -> Path:
    _write_pickle(
        path,
        {
            "model": OpportunityFixtureModel(),
            "feature_columns": ["feature__candidate_score"],
            "preprocessing": {"medians": {"feature__candidate_score": 0.0}},
            "model_version": "opportunity_model_phase15ag_fixture",
        },
    )
    return path


def _write_opportunity_metrics(path: Path, model_path: Path) -> Path:
    _write_json(
        path,
        {
            "status": "PASS",
            "readiness_status": "READY",
            "model_artifact_path": str(model_path),
            "feature_columns": ["feature__candidate_score"],
        },
    )
    return path


def _write_pickle(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(payload, handle)


def _write_safety_decision(root: Path) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase14e36-allow",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": str(path),
            "business_date": "2026-07-09",
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase14e36 fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": "2026-07-09T00:00:00+09:00",
            "expires_at": "2026-07-10T00:00:00+09:00",
        },
    )
    return path


def _write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
