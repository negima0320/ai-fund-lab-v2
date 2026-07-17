from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ai_fund_lab_v2.runtime_v2.buy_ai.producer import (
    CANDIDATE_ARTIFACT_SCHEMA_VERSION,
    OPPORTUNITY_ARTIFACT_SCHEMA_VERSION,
    load_ai_planning_signals_from_opportunity_artifact,
    produce_buy_ai_decisions,
)
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import OPPORTUNITY_REQUIRED_COLUMNS
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import generate_public_report_from_current
from tests.runtime_v2.feature_date_contract_helpers import materialize_feature_date_contract


BUSINESS_DATE = "2026-07-08"
FEATURE_DATE = "2026-07-07"


class CandidateFixtureModel:
    def predict_proba(self, matrix):
        values = np.asarray(matrix, dtype=float)[:, 0]
        scores = np.clip(values, 0.0, 1.0)
        return np.column_stack([1.0 - scores, scores])


class OpportunityFixtureModel:
    def predict(self, matrix):
        return np.asarray(matrix, dtype=float)[:, 0]


def test_phase15ag_candidate_and_opportunity_artifacts_feed_morning(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")
    candidate_model_path = _write_candidate_model(tmp_path / "candidate_model.pkl")
    opportunity_model_path = _write_opportunity_model(tmp_path / "opportunity_model.pkl")
    opportunity_metrics_path = _write_opportunity_metrics(tmp_path / "opportunity_training_metrics.json", opportunity_model_path)

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=candidate_model_path,
        opportunity_model_path=opportunity_model_path,
        opportunity_training_metrics_path=opportunity_metrics_path,
        selected_rank_limit=2,
    )
    candidate = json.loads(Path(result.candidate_artifact_path).read_text(encoding="utf-8"))
    opportunity = json.loads(Path(result.opportunity_artifact_path).read_text(encoding="utf-8"))
    signals = load_ai_planning_signals_from_opportunity_artifact(result.opportunity_artifact_path, selected_rank_limit=2)

    assert result.status == "PASS"
    assert candidate["schema_version"] == CANDIDATE_ARTIFACT_SCHEMA_VERSION
    assert opportunity["schema_version"] == OPPORTUNITY_ARTIFACT_SCHEMA_VERSION
    assert candidate["rows"][0]["symbol"] == "7203"
    assert opportunity["rankings"][0]["symbol"] == "7203"
    assert signals[0].source_ai == "opportunity_ai"
    assert signals[0].symbol == "7203"


def test_phase16aq_missing_opportunity_metrics_halts_without_phase5e_fallback(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_candidate_model(tmp_path / "candidate_model.pkl"),
        opportunity_model_path=_write_opportunity_model(tmp_path / "opportunity_model.pkl"),
    )
    opportunity = json.loads(Path(result.opportunity_artifact_path).read_text(encoding="utf-8"))

    assert result.status == "HALT"
    assert result.reason == "opportunity_metrics_artifact_not_supplied"
    assert opportunity["status"] == "HALT"
    assert opportunity["halt_reason"] == "opportunity_metrics_artifact_not_supplied"
    assert opportunity["metrics_validation"]["phase5e_fallback_used"] is False
    assert "reports/opportunity_ai/phase5e" not in json.dumps(opportunity).lower()


def test_phase16aq_phase5e_metrics_path_is_rejected(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")
    opportunity_model_path = _write_opportunity_model(tmp_path / "opportunity_model.pkl")
    phase5e_metrics = _write_opportunity_metrics(
        tmp_path / "reports" / "opportunity_ai" / "phase5e" / "opportunity_training_metrics.json",
        opportunity_model_path,
    )

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_candidate_model(tmp_path / "candidate_model.pkl"),
        opportunity_model_path=opportunity_model_path,
        opportunity_training_metrics_path=phase5e_metrics,
    )

    assert result.status == "HALT"
    assert result.reason == "opportunity_phase5e_metrics_rejected"


def test_phase16aq_wrong_metrics_hash_is_rejected(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")
    opportunity_model_path = _write_opportunity_model(tmp_path / "opportunity_model.pkl")
    metrics_path = _write_opportunity_metrics(
        tmp_path / "opportunity_training_metrics.json",
        opportunity_model_path,
        extra={"model_artifact_hash": "sha256:" + ("0" * 64)},
    )

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_candidate_model(tmp_path / "candidate_model.pkl"),
        opportunity_model_path=opportunity_model_path,
        opportunity_training_metrics_path=metrics_path,
    )

    assert result.status == "HALT"
    assert result.reason == "opportunity_metrics_model_hash_mismatch"


def test_phase17t_legacy_metrics_model_path_with_same_sha256_is_accepted(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")
    opportunity_model_path = _write_opportunity_model(tmp_path / ".runtime" / "artifacts" / "opportunity" / "model.pkl")
    legacy_model_path = tmp_path / "reports" / "opportunity_ai" / "phase5p" / "models" / "opportunity_model.pkl"
    legacy_model_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_model_path.write_bytes(opportunity_model_path.read_bytes())
    metrics_path = _write_opportunity_metrics(
        tmp_path / ".runtime" / "artifacts" / "opportunity" / "metrics.json",
        legacy_model_path,
    )

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_candidate_model(tmp_path / "candidate_model.pkl"),
        opportunity_model_path=opportunity_model_path,
        opportunity_training_metrics_path=metrics_path,
    )
    opportunity = json.loads(Path(result.opportunity_artifact_path).read_text(encoding="utf-8"))

    assert result.status == "PASS"
    assert opportunity["metrics_validation"]["metrics_model_path"] == str(legacy_model_path)
    assert opportunity["metrics_validation"]["metrics_model_path_hash"]
    assert (
        opportunity["metrics_validation"]["metrics_model_path_authority"]
        == "legacy_metrics_path_content_matches_runtime_model"
    )


def test_phase17t_legacy_metrics_model_path_with_different_sha256_still_halts(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")
    opportunity_model_path = _write_opportunity_model(tmp_path / ".runtime" / "artifacts" / "opportunity" / "model.pkl")
    legacy_model_path = _write_opportunity_model(
        tmp_path / "reports" / "opportunity_ai" / "phase5p" / "models" / "opportunity_model.pkl",
        artifact_set_id="different-set",
    )
    metrics_path = _write_opportunity_metrics(
        tmp_path / ".runtime" / "artifacts" / "opportunity" / "metrics.json",
        legacy_model_path,
    )

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_candidate_model(tmp_path / "candidate_model.pkl"),
        opportunity_model_path=opportunity_model_path,
        opportunity_training_metrics_path=metrics_path,
    )
    opportunity = json.loads(Path(result.opportunity_artifact_path).read_text(encoding="utf-8"))

    assert result.status == "HALT"
    assert result.reason == "opportunity_metrics_model_path_mismatch"
    assert opportunity["metrics_validation"]["metrics_model_path_hash"]


def test_phase16aq_wrong_artifact_set_is_rejected(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")
    opportunity_model_path = _write_opportunity_model(tmp_path / "opportunity_model.pkl", artifact_set_id="set-a")
    metrics_path = _write_opportunity_metrics(
        tmp_path / "opportunity_training_metrics.json",
        opportunity_model_path,
        artifact_set_id="set-b",
    )

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=feature_root,
        feature_date=FEATURE_DATE,
        candidate_model_path=_write_candidate_model(tmp_path / "candidate_model.pkl"),
        opportunity_model_path=opportunity_model_path,
        opportunity_training_metrics_path=metrics_path,
    )

    assert result.status == "HALT"
    assert result.reason == "opportunity_model_metrics_artifact_set_mismatch"


def test_phase15ag_morning_cli_uses_opportunity_artifact_not_feature_row_signal(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")
    materialize_feature_date_contract(runtime_root, business_date=BUSINESS_DATE, selected_feature_date=FEATURE_DATE)
    policy_path = _write_policy(tmp_path / "capital_deployment.json")
    candidate_model_path = _write_candidate_model(tmp_path / "candidate_model.pkl")
    opportunity_model_path = _write_opportunity_model(tmp_path / "opportunity_model.pkl")
    opportunity_metrics_path = _write_opportunity_metrics(tmp_path / "opportunity_training_metrics.json", opportunity_model_path)

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
            str(candidate_model_path),
            "--opportunity-model-path",
            str(opportunity_model_path),
            "--opportunity-training-metrics-path",
            str(opportunity_metrics_path),
        ]
    )
    manifest = _latest_manifest(runtime_root)
    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    order_plan = json.loads((runtime_root / "runtime_state" / "morning_pipeline" / BUSINESS_DATE / "order_plan.json").read_text(encoding="utf-8"))
    pending_symbols = [item["symbol"] for item in pending["items"]]

    assert exit_code == 0
    assert manifest["candidate_count"] == 3
    assert manifest["opportunity_count"] == 3
    assert manifest["selected_rank_count"] == 3
    assert pending_symbols == ["7203"]
    assert "runtime_v2_morning_feature_inference" not in json.dumps(order_plan)
    assert order_plan["buy_ai_context"]["opportunity_artifact_path"] == manifest["opportunity_artifact_path"]


def test_phase15ag_missing_buy_ai_models_stops_before_morning_planning(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")
    materialize_feature_date_contract(runtime_root, business_date=BUSINESS_DATE, selected_feature_date=FEATURE_DATE)
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
            str(tmp_path / "missing_candidate_model.pkl"),
            "--opportunity-model-path",
            str(tmp_path / "missing_opportunity_model.pkl"),
        ]
    )
    manifest = _latest_manifest(runtime_root)
    stage_names = {stage["name"] for stage in manifest["stages"]}

    assert exit_code == 20
    assert manifest["final_state"] == "REVIEW_REQUIRED"
    assert manifest["buy_ai_status"] == "REVIEW_REQUIRED"
    assert "runtime_data_readiness_gate" in stage_names
    assert "candidate_opportunity_ai_runtime_producer" not in stage_names
    assert "morning_ai_planning_pending_pipeline" not in stage_names


def test_phase15ag_report_and_notification_include_buy_ai_summary(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")
    materialize_feature_date_contract(runtime_root, business_date=BUSINESS_DATE, selected_feature_date=FEATURE_DATE)
    policy_path = _write_policy(tmp_path / "capital_deployment.json")
    candidate_model_path = _write_candidate_model(tmp_path / "candidate_model.pkl")
    opportunity_model_path = _write_opportunity_model(tmp_path / "opportunity_model.pkl")
    opportunity_metrics_path = _write_opportunity_metrics(tmp_path / "opportunity_training_metrics.json", opportunity_model_path)
    main(
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
            str(candidate_model_path),
            "--opportunity-model-path",
            str(opportunity_model_path),
            "--opportunity-training-metrics-path",
            str(opportunity_metrics_path),
        ]
    )

    result = generate_public_report_from_current(
        runtime_root=runtime_root,
        runtime_output_dir=tmp_path / "reports" / "runtime_v2" / BUSINESS_DATE,
        public_output_dir=tmp_path / "reports" / "public" / "runtime_v2" / BUSINESS_DATE,
        business_date=BUSINESS_DATE,
    )
    runtime_report = Path(result["runtime_report_md"]).read_text(encoding="utf-8")
    payload = json.loads(Path(result["notification_payload_json"]).read_text(encoding="utf-8"))

    assert "## Candidate AI Summary" in runtime_report
    assert "## Opportunity AI Summary" in runtime_report
    assert "## Why Selected" in runtime_report
    assert payload["buy_ai_summary"].startswith("selected_candidates")
    assert payload["selected_candidates"] == 3
    assert payload["selected_top_rank"] == 1


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15ag",
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
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "environment": "demo", "items": []})
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "1",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase15ag-test",
            "state": "CURRENT_STATE_LOADED",
            "environment": "demo",
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
        },
    )
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    _write_safety_decision(root)
    _write_market_evidence(root)
    return root


def _write_feature_inputs(root: Path) -> Path:
    feature_dir = root / FEATURE_DATE
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        _feature_row("7203", 0.90, 500.0),
        _feature_row("6501", 0.70, 2500.0),
        _feature_row("9432", 0.50, 150.0),
    ]
    pd.DataFrame(rows).to_parquet(feature_dir / "candidate_features.parquet", index=False)
    opportunity_rows = [_opportunity_feature_row(row) for row in rows]
    pd.DataFrame(opportunity_rows).to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame(
        columns=[
            "target_date",
            "entry_date",
            "code",
            "holding_days",
            "current_price",
            "unrealized_return",
            "feature_version",
            "data_until",
            "created_at",
            "no_position_reason",
        ]
    ).to_parquet(feature_dir / "position_feature_input.parquet", index=False)
    pd.DataFrame(
        [
            {
                "target_date": FEATURE_DATE,
                "code": "__POLICY_INPUT__",
                "policy_input_type": "phase15ag_fixture_refs",
                "data_until": FEATURE_DATE,
            }
        ]
    ).to_parquet(feature_dir / "capital_policy_input.parquet", index=False)
    price_dir = root.parent / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily"
    price_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"Code": row["code"], "Date": FEATURE_DATE, "Close": row["price"], "PriceSource": "fixture_close"} for row in rows]
    ).to_parquet(price_dir / "data.parquet", index=False)
    return root


def _feature_row(code: str, momentum: float, price: float) -> dict:
    return {
        "target_date": FEATURE_DATE,
        "as_of_date": FEATURE_DATE,
        "code": code,
        "feature_version": "phase15ag_fixture_features",
        "source_snapshot_id": "snapshot-" + code,
        "universe_eligible": True,
        "excluded_reason": "",
        "price_momentum_return_20d": momentum,
        "price_momentum_return_5d": momentum / 2,
        "price_momentum_return_60d": momentum * 1.5,
        "trend_close_over_ma_20d": momentum / 3,
        "trend_ma_20_60_ratio": 1.01,
        "trend_ma_5_20_ratio": 1.02,
        "volatility_return_std_20d": 0.02,
        "volume_momentum_ratio_1d_20d": 1.2,
        "volume_momentum_ratio_5d": 1.1,
        "liquidity_avg_volume_20d": 1_000_000,
        "missing_flags_insufficient_history": False,
        "missing_flags_price": False,
        "missing_flags_volume": False,
        "price": price,
    }


def _opportunity_feature_row(candidate_row: dict) -> dict:
    row = {
        "target_date": candidate_row["target_date"],
        "as_of_date": candidate_row["as_of_date"],
        "code": candidate_row["code"],
        "created_at": BUSINESS_DATE + "T00:00:00Z",
        "data_until": FEATURE_DATE,
        "feature_version": "runtime_v2_opportunity_feature_input_v2_market_sector_fixture",
    }
    for column in OPPORTUNITY_REQUIRED_COLUMNS:
        if column in {"target_date", "code"}:
            row[column] = candidate_row[column]
        elif column in candidate_row:
            row[column] = candidate_row[column]
        elif column.endswith("_flag") or column.endswith("_context"):
            row[column] = False
        else:
            row[column] = 0.1
    return row


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


def _write_opportunity_model(path: Path, *, artifact_set_id: str = "") -> Path:
    payload = {
        "model": OpportunityFixtureModel(),
        "feature_columns": ["feature__candidate_score"],
        "preprocessing": {"medians": {"feature__candidate_score": 0.0}},
        "model_version": "opportunity_model_phase15ag_fixture",
    }
    if artifact_set_id:
        payload["artifact_set_id"] = artifact_set_id
    _write_pickle(
        path,
        payload,
    )
    return path


def _write_opportunity_metrics(
    path: Path,
    model_path: Path,
    *,
    artifact_set_id: str = "phase15ag_fixture_set",
    extra: dict | None = None,
) -> Path:
    payload = {
        "status": "PASS",
        "readiness_status": "READY",
        "model_artifact_path": str(model_path),
        "artifact_set_id": artifact_set_id,
        "feature_columns": ["feature__candidate_score"],
    }
    payload.update(extra or {})
    _write_json(path, payload)
    return path


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


def _write_safety_decision(root: Path) -> None:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase15ag-allow",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": str(path),
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase15ag fixture safety allow",
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


def _write_market_evidence(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "market_summary": {"quote_count": 3},
            "quote_count": 3,
        },
    )


def _latest_manifest(runtime_root: Path) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


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
