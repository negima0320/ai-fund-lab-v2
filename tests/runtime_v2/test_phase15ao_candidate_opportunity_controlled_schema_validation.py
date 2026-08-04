from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ai_fund_lab_v2.runtime_v2.buy_ai.producer import produce_buy_ai_decisions
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main


BUSINESS_DATE = "2026-07-08"
FEATURE_DATE = "2026-07-07"


class CandidateFixtureModel:
    def predict_proba(self, matrix):
        values = np.asarray(matrix, dtype=float)[:, 0]
        return np.column_stack([1.0 - values, values])


class OpportunityFixtureModel:
    def predict(self, matrix):
        return np.asarray(matrix, dtype=float)[:, 0]


def test_phase15ao_candidate_missing_column_writes_controlled_review_artifacts(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        drop_candidate_column="price_momentum_return_60d",
    )

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_candidate_model(
            tmp_path / "candidate_model.pkl",
            ["feature__price_momentum_return_60d"],
        ),
        opportunity_model_path=_write_opportunity_model(tmp_path / "opportunity_model.pkl"),
    )
    candidate = _read_json(result.candidate_artifact_path)
    opportunity = _read_json(result.opportunity_artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "candidate_feature_schema_mismatch"
    assert candidate["status"] == "REVIEW_REQUIRED"
    assert candidate["review_required"] is True
    assert candidate["review_reason"] == "candidate_feature_schema_mismatch"
    assert candidate["candidate_count"] == 0
    assert candidate["missing_columns"] == ["price_momentum_return_60d"]
    assert opportunity["status"] == "REVIEW_REQUIRED"
    assert opportunity["reason"] == "candidate_dependency_review_required"
    assert opportunity["ranking_count"] == 0


def test_phase15ao_candidate_alias_risk_is_enumerated_without_keyerror(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        drop_candidate_column="missing_flags_insufficient_history",
        extra_candidate_columns={"missing_flags_insufficient_lookback": False},
    )

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_candidate_model(
            tmp_path / "candidate_model.pkl",
            ["feature__missing_flags_insufficient_history"],
        ),
        opportunity_model_path=_write_opportunity_model(tmp_path / "opportunity_model.pkl"),
    )
    candidate = _read_json(result.candidate_artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert candidate["alias_risks"] == {
        "missing_flags_insufficient_lookback": "missing_flags_insufficient_history"
    }
    assert "missing_flags_insufficient_history" in candidate["missing_columns"]


def test_phase15ao_opportunity_prefixed_artifact_column_stops_before_inference(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        extra_opportunity_columns={"feature__price_momentum_return_20d": 0.2},
    )

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_candidate_model(tmp_path / "candidate_model.pkl"),
        opportunity_model_path=_write_opportunity_model(
            tmp_path / "opportunity_model.pkl",
            ["feature__candidate_score", "feature__price_momentum_return_20d"],
        ),
        opportunity_training_metrics_path=_write_opportunity_metrics(
            tmp_path / "opportunity_training_metrics.json",
            tmp_path / "opportunity_model.pkl",
            feature_columns=["feature__candidate_score", "feature__price_momentum_return_20d"],
        ),
    )
    opportunity = _read_json(result.opportunity_artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert opportunity["status"] == "REVIEW_REQUIRED"
    assert opportunity["review_reason"] == "opportunity_feature_prefix_policy_violation"
    assert opportunity["double_prefix_detected"] is True
    assert opportunity["unexpected_columns"] == ["feature__price_momentum_return_20d"]


def test_phase15ao_opportunity_missing_required_feature_does_not_nan_continue(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        drop_opportunity_column="price_momentum_return_60d",
    )

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_candidate_model(tmp_path / "candidate_model.pkl"),
        opportunity_model_path=_write_opportunity_model(
            tmp_path / "opportunity_model.pkl",
            ["feature__candidate_score", "feature__price_momentum_return_60d"],
        ),
        opportunity_training_metrics_path=_write_opportunity_metrics(
            tmp_path / "opportunity_training_metrics.json",
            tmp_path / "opportunity_model.pkl",
            feature_columns=["feature__candidate_score", "feature__price_momentum_return_60d"],
        ),
    )
    opportunity = _read_json(result.opportunity_artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert opportunity["review_required"] is True
    assert opportunity["review_reason"] == "opportunity_feature_schema_mismatch"
    assert opportunity["missing_columns"] == ["feature__price_momentum_return_60d"]
    assert opportunity["rankings"] == []


def test_phase15ao_morning_stops_before_planning_on_buy_ai_schema_failure(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        drop_candidate_column="price_momentum_return_60d",
    )
    policy_path = _write_policy(tmp_path / "capital_deployment.json")

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
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            "--candidate-model-path",
            str(_write_candidate_model(tmp_path / "candidate_model.pkl", ["feature__price_momentum_return_60d"])),
            "--opportunity-model-path",
            str(_write_opportunity_model(tmp_path / "opportunity_model.pkl")),
        ]
    )
    manifest = _latest_manifest(runtime_root)
    stage_names = {stage["name"] for stage in manifest["stages"]}

    assert exit_code == 20
    assert manifest["final_state"] == "REVIEW_REQUIRED"
    assert manifest["candidate_schema_status"] == "REVIEW_REQUIRED"
    assert "price_momentum_return_60d" in manifest["candidate_missing_columns"]
    assert manifest["candidate_review_required"] is True
    assert "runtime_data_readiness_gate" in stage_names
    assert "candidate_opportunity_ai_runtime_producer" not in stage_names
    assert "morning_ai_planning_pending_pipeline" not in stage_names
    assert not (runtime_root / "runtime_state" / "morning_pipeline" / BUSINESS_DATE / "order_plan.json").exists()


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15ao",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": BUSINESS_DATE,
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "review_required": False,
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "items": []})
    _write_json(root / "runtime_state" / "current_state.json", {"state": "CURRENT_STATE_LOADED"})
    _write_safety_decision(root)
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _write_feature_inputs(
    root: Path,
    *,
    drop_candidate_column: str = "",
    drop_opportunity_column: str = "",
    extra_candidate_columns: dict | None = None,
    extra_opportunity_columns: dict | None = None,
) -> Path:
    feature_dir = root / FEATURE_DATE
    feature_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "target_date": FEATURE_DATE,
        "code": "7203",
        "price_momentum_return_20d": 0.8,
        "price_momentum_return_60d": 0.9,
        "missing_flags_insufficient_history": False,
        "volatility_return_std_20d": 0.02,
    }
    candidate = dict(row)
    opportunity = dict(row)
    if drop_candidate_column:
        candidate.pop(drop_candidate_column)
    if drop_opportunity_column:
        opportunity.pop(drop_opportunity_column)
    candidate.update(extra_candidate_columns or {})
    opportunity.update(extra_opportunity_columns or {})
    pd.DataFrame([candidate]).to_parquet(feature_dir / "candidate_features.parquet", index=False)
    pd.DataFrame([opportunity]).to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame(columns=["target_date", "code", "no_position_reason"]).to_parquet(
        feature_dir / "position_feature_input.parquet",
        index=False,
    )
    pd.DataFrame([{"target_date": FEATURE_DATE, "code": "__POLICY_INPUT__"}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )
    price_dir = root.parent / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily"
    price_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Code": "7203", "Date": FEATURE_DATE, "Close": 1000.0}]).to_parquet(
        price_dir / "data.parquet",
        index=False,
    )
    return root


def _write_candidate_model(path: Path, feature_columns: list[str] | None = None) -> Path:
    _write_pickle(
        path,
        {
            "model": CandidateFixtureModel(),
            "feature_columns": feature_columns or ["feature__price_momentum_return_20d"],
            "model_version": "candidate_model_phase15ao_fixture",
        },
    )
    return path


def _write_opportunity_model(path: Path, feature_columns: list[str] | None = None) -> Path:
    _write_pickle(
        path,
        {
            "model": OpportunityFixtureModel(),
            "feature_columns": feature_columns or ["feature__candidate_score"],
            "preprocessing": {"medians": {"feature__candidate_score": 0.0}},
            "model_version": "opportunity_model_phase15ao_fixture",
        },
    )
    return path


def _write_opportunity_metrics(path: Path, model_path: Path, *, feature_columns: list[str] | None = None) -> Path:
    _write_json(
        path,
        {
            "status": "PASS",
            "readiness_status": "READY",
            "model_artifact_path": str(model_path),
            "feature_columns": feature_columns or ["feature__candidate_score"],
        },
    )
    return path


def _write_policy(path: Path) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
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


def _write_safety_decision(root: Path) -> None:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase15ao-allow",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": str(path),
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase15ao fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": BUSINESS_DATE + "T00:00:00+09:00",
            "expires_at": "2026-07-09T00:00:00+09:00",
        },
    )


def _latest_manifest(runtime_root: Path) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    return _read_json(manifests[-1])


def _read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def _write_pickle(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(value, handle)
