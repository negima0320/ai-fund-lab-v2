from __future__ import annotations

import json
import pickle
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.buy_ai.producer import (
    DEFAULT_CANDIDATE_MODEL_PATH,
    DEFAULT_OPPORTUNITY_MODEL_PATH,
)
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness


BUSINESS_DATE = "2026-07-08"
FEATURE_DATE = "2026-07-07"


class FixtureModel:
    pass


def test_phase15as_market_calendar_open_quote_missing_is_market_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, write_market=False)
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts")
    candidate_model = _write_model(tmp_path / "candidate.pkl")
    opportunity_model = _write_model(tmp_path / "opportunity.pkl")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=candidate_model,
        opportunity_model_path=opportunity_model,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["market_calendar_status"] == "READY"
    assert result.payload["market_data_status"] == "REVIEW_REQUIRED"
    assert result.payload["market_status"] == "REVIEW_REQUIRED"
    assert "market_evidence" in result.payload["missing_evidence"]


def test_phase15as_safety_quote_missing_sets_quote_and_market_effective_review_required(tmp_path):
    runtime_root = _runtime_root(
        tmp_path,
        safety_decision="REVIEW_REQUIRED",
        safety_reason="QUOTE_MISSING_FOR_MONITOR;BROKER_SNAPSHOT_MISSING;POSITION_WITHOUT_BROKER_SNAPSHOT",
    )
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts")
    candidate_model = _write_model(tmp_path / "candidate.pkl")
    opportunity_model = _write_model(tmp_path / "opportunity.pkl")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=candidate_model,
        opportunity_model_path=opportunity_model,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["broker_direct_scope_status"] == "NOT_REQUIRED"
    assert result.payload["broker_safety_dependency_status"] == "REVIEW_REQUIRED"
    assert result.payload["broker_effective_status"] == "REVIEW_REQUIRED"
    assert result.payload["quote_status"] == "REVIEW_REQUIRED"
    assert result.payload["safety_market_input_status"] == "REVIEW_REQUIRED"
    assert result.payload["market_status"] == "REVIEW_REQUIRED"
    assert "safety_requires_quote_evidence" in result.payload["component_reasons"]["quote"]
    assert "safety_requires_broker_snapshot" in result.payload["component_reasons"]["broker"]


def test_phase15as_market_evidence_ready_and_safety_allow_can_be_ready(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts")
    candidate_model = _write_model(tmp_path / "candidate.pkl")
    opportunity_model = _write_model(tmp_path / "opportunity.pkl")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=candidate_model,
        opportunity_model_path=opportunity_model,
    )

    assert result.status == "READY"
    assert result.payload["market_status"] == "READY"
    assert result.payload["quote_status"] == "READY"
    assert result.payload["safety_status"] == "READY"


def test_phase15as_gate_uses_canonical_buy_ai_model_paths_when_cli_paths_omitted(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
    )

    assert result.payload["candidate_model_path"] == str(DEFAULT_CANDIDATE_MODEL_PATH)
    assert result.payload["opportunity_model_path"] == str(DEFAULT_OPPORTUNITY_MODEL_PATH)
    assert result.payload["candidate_model_path"]
    assert result.payload["opportunity_model_path"]


def test_phase15as_corrupt_model_artifact_halts_with_component_reason(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts")
    corrupt_model = tmp_path / "corrupt.pkl"
    corrupt_model.write_text("not pickle", encoding="utf-8")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=corrupt_model,
        opportunity_model_path=_write_model(tmp_path / "opportunity.pkl"),
    )

    assert result.status == "HALT"
    assert result.payload["candidate_model_status"] == "HALT"
    assert result.payload["component_reasons"]["candidate"]


def test_phase15as_empty_pending_slot_is_ready_and_cli_has_no_missing_warning(tmp_path):
    runtime_root = _runtime_root(tmp_path, pending_empty=True)
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts")
    candidate_model = _write_model(tmp_path / "candidate.pkl")
    opportunity_model = _write_model(tmp_path / "opportunity.pkl")
    policy = _write_policy(tmp_path / "capital_deployment.json")

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
            str(policy),
            "--candidate-model-path",
            str(candidate_model),
            "--opportunity-model-path",
            str(opportunity_model),
        ]
    )

    manifest = _latest_manifest(runtime_root)
    assert exit_code == 0
    assert manifest["pending_slot_status"] == "EMPTY"
    assert manifest["pending_active"] is False
    assert "pending_order_plan MISSING" not in manifest["warnings"]
    assert "runtime_state MISSING" not in manifest["warnings"]


def test_phase15as_pending_slot_missing_is_not_empty(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    (runtime_root / "pending_order_plan" / "pending_order_plan.json").unlink()
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_model(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_model(tmp_path / "opportunity.pkl"),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["pending_slot_status"] == "MISSING"
    assert result.payload["pending_active"] is False
    assert "pending_slot" in result.payload["missing_evidence"]


def test_phase15as_demo_production_equivalence_fields_are_split(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_model(tmp_path / "candidate.pkl"),
        opportunity_model_path=_write_model(tmp_path / "opportunity.pkl"),
    )

    assert result.payload["runtime_core_production_baseline"] is True
    assert result.payload["broker_environment"] == "demo"
    assert result.payload["broker_environment_production"] is False
    assert result.payload["evidence_production_equivalent"] is False
    assert result.payload["acceptance_production_equivalent"] is False
    assert result.payload["acceptance_scope"] == "demo_acceptance_only"
    assert result.payload["runtime_execution_path"] == "regular_runtime"


def test_phase15as_component_reasons_are_structured(tmp_path):
    runtime_root = _runtime_root(tmp_path, write_market=False)
    feature_root = _write_feature_inputs(runtime_root / "operations" / "feature_artifacts")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning",
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=tmp_path / "missing_candidate.pkl",
        opportunity_model_path=tmp_path / "missing_opportunity.pkl",
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "market_evidence_missing" in result.payload["component_reasons"]["market"]
    assert "candidate_pre_inference_not_ready" in result.payload["component_reasons"]["candidate"]
    assert "opportunity_pre_inference_not_ready" in result.payload["component_reasons"]["opportunity"]
    assert result.payload["effective_component_statuses"]["market"] == "REVIEW_REQUIRED"


def _runtime_root(
    tmp_path: Path,
    *,
    write_market: bool = True,
    safety_decision: str = "ALLOW",
    safety_reason: str = "phase15as fixture allow",
    pending_empty: bool = False,
) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15as",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": BUSINESS_DATE,
            "business_date": BUSINESS_DATE,
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "review_required": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    if pending_empty:
        _write_json(
            root / "pending_order_plan" / "pending_order_plan.json",
            {
                "schema_version": "runtime_v2_pending_slot_v1",
                "status": "EMPTY",
                "state": "EMPTY",
                "active_pending": False,
            },
        )
    else:
        _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "environment": "demo", "items": []})
    _write_safety(root, decision=safety_decision, reason=safety_reason)
    if write_market:
        _write_market(root)
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _write_feature_inputs(feature_root: Path) -> Path:
    feature_dir = feature_root / FEATURE_DATE
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "target_date": FEATURE_DATE,
            "code": "7203",
            "liquidity_avg_volume_20d": 1_000_000,
            "missing_flags_insufficient_history": False,
            "missing_flags_price": False,
            "missing_flags_volume": False,
            "price_momentum_return_20d": 0.1,
            "price_momentum_return_5d": 0.05,
            "price_momentum_return_60d": 0.2,
            "trend_close_over_ma_20d": 1.0,
            "trend_ma_20_60_ratio": 1.0,
            "trend_ma_5_20_ratio": 1.0,
            "volatility_return_std_20d": 0.02,
            "volume_momentum_ratio_1d_20d": 1.2,
            "volume_momentum_ratio_5d": 1.1,
        }
    ]
    pd.DataFrame(rows).to_parquet(feature_dir / "candidate_features.parquet", index=False)
    pd.DataFrame(rows).to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame(columns=["target_date", "code", "no_position_reason"]).to_parquet(
        feature_dir / "position_feature_input.parquet",
        index=False,
    )
    return feature_root


def _write_model(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(
            {
                "model": FixtureModel(),
                "feature_columns": ["feature__price_momentum_return_20d"],
                "model_version": "phase15as_fixture_model",
            },
            handle,
        )
    return path


def _write_market(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": BUSINESS_DATE,
            "as_of": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "quote_count": 1,
            "market_summary": {"status": "READY"},
        },
    )


def _write_safety(root: Path, *, decision: str, reason: str) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase15as",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": "fixture",
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": decision,
            "reason": reason,
            "review_required": decision != "ALLOW",
            "block_buy": decision != "ALLOW",
            "block_sell": decision != "ALLOW",
            "block_submit": decision != "ALLOW",
            "halt_runtime": decision == "HALT",
            "emergency_stop": False,
            "generated_at": BUSINESS_DATE + "T00:00:00+09:00",
            "expires_at": BUSINESS_DATE + "T23:59:59+09:00",
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


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_manifest(runtime_root: Path) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    return _load_json(manifests[-1])
