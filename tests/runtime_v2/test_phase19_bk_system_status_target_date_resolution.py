from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2 import system_status


TARGET_DATE = "2026-07-06"
FUTURE_DATE = "2026-07-14"


def test_phase19_bk_target_exact_wins_over_future_artifacts(tmp_path: Path, monkeypatch) -> None:
    runtime_root, manifest_path, future_manifest_path = _runtime_root_with_artifacts(
        tmp_path,
        target_artifacts=True,
        future_artifacts=True,
    )
    monkeypatch.setattr(
        system_status,
        "build_ai_status_report",
        lambda **_: _ai_report(manifest_path=manifest_path, latest_feature_manifest=future_manifest_path),
    )

    report = system_status.build_system_status_report(
        runtime_root=runtime_root,
        expected_business_date=TARGET_DATE,
        runtime_mode="historical",
        profile_id="historical-smoke",
        broker_environment="historical_simulated",
        target_business_dates=[TARGET_DATE],
    )

    context = report["inspection_context"]["artifact_resolution"]
    assert context["authority"] == "target_business_date_exact_match"
    assert context["runtime_artifact_business_date"] == TARGET_DATE
    assert context["fallback_used"] is False

    assert _runtime_feature_dates(report) == {TARGET_DATE}
    models = _active_models(report)
    assert models["candidate_ai"]["latest_inference_date"] == TARGET_DATE
    assert models["candidate_ai"]["latest_inference_input_date"] == TARGET_DATE
    assert models["opportunity_ai"]["latest_inference_date"] == TARGET_DATE
    assert models["opportunity_ai"]["latest_inference_input_date"] == TARGET_DATE
    assert TARGET_DATE in _decision_artifact(report, "runtime_baseline")
    assert TARGET_DATE in _decision_artifact(report, "freshness_evaluation")
    assert report["temporal_authority_audit"]["future_state_reference_count"] == 0
    assert FUTURE_DATE not in _runtime_consumer_resolution_payload(report)


def test_phase19_bk_missing_target_does_not_fallback_to_future(tmp_path: Path, monkeypatch) -> None:
    runtime_root, manifest_path, future_manifest_path = _runtime_root_with_artifacts(
        tmp_path,
        target_artifacts=False,
        future_artifacts=True,
    )
    monkeypatch.setattr(
        system_status,
        "build_ai_status_report",
        lambda **_: _ai_report(manifest_path=manifest_path, latest_feature_manifest=future_manifest_path),
    )

    report = system_status.build_system_status_report(
        runtime_root=runtime_root,
        expected_business_date=TARGET_DATE,
        runtime_mode="historical",
        profile_id="historical-smoke",
        broker_environment="historical_simulated",
        target_business_dates=[TARGET_DATE],
    )

    context = report["inspection_context"]["artifact_resolution"]
    assert context["status"] == "TARGET_DATE_ARTIFACT_MISSING"
    assert context["runtime_artifact_business_date"] == TARGET_DATE
    assert context["fallback_used"] is False

    features = {
        item["component_id"]: item
        for item in report["data_inspection"]["runtime_features"]
    }
    assert features["candidate_runtime_feature"]["target_date_resolution_status"] == "TARGET_DATE_ARTIFACT_MISSING"
    assert features["opportunity_runtime_feature"]["target_date_resolution_status"] == "TARGET_DATE_ARTIFACT_MISSING"
    assert TARGET_DATE in features["candidate_runtime_feature"]["artifact_path"]
    assert TARGET_DATE in features["opportunity_runtime_feature"]["artifact_path"]

    models = _active_models(report)
    assert models["candidate_ai"]["latest_inference_date"] == "NOT_YET_MATERIALIZED"
    assert models["opportunity_ai"]["latest_inference_date"] == "NOT_YET_MATERIALIZED"
    assert FUTURE_DATE not in _runtime_consumer_resolution_payload(report)


def test_phase19_bk_feature_candidate_opportunity_lifecycle_share_target_date(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime_root, manifest_path, future_manifest_path = _runtime_root_with_artifacts(
        tmp_path,
        target_artifacts=True,
        future_artifacts=True,
    )
    monkeypatch.setattr(
        system_status,
        "build_ai_status_report",
        lambda **_: _ai_report(manifest_path=manifest_path, latest_feature_manifest=future_manifest_path),
    )

    report = system_status.build_system_status_report(
        runtime_root=runtime_root,
        expected_business_date=TARGET_DATE,
        runtime_mode="historical",
        profile_id="historical-smoke",
        broker_environment="historical_simulated",
        target_business_dates=[TARGET_DATE],
    )

    assert report["runtime_input_lineage_contract"]["target_business_date"] == TARGET_DATE
    assert report["runtime_input_lineage_contract"]["actual_feature_business_date"] == TARGET_DATE
    assert report["runtime_input_lineage_contract"]["inference_business_date"] == TARGET_DATE
    assert report["runtime_stage_contract"]["target_business_date"] == TARGET_DATE
    assert _runtime_feature_dates(report) == {TARGET_DATE}
    assert _model_dates(report) == {TARGET_DATE}
    assert TARGET_DATE in _decision_artifact(report, "runtime_baseline")
    assert TARGET_DATE in _decision_artifact(report, "freshness_evaluation")


def test_phase19_bk_future_source_coverage_does_not_contaminate_runtime_consumers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime_root, manifest_path, future_manifest_path = _runtime_root_with_artifacts(
        tmp_path,
        target_artifacts=True,
        future_artifacts=True,
    )
    monkeypatch.setattr(
        system_status,
        "build_ai_status_report",
        lambda **_: _ai_report(
            manifest_path=manifest_path,
            latest_feature_manifest=future_manifest_path,
            source_latest_business_date=FUTURE_DATE,
        ),
    )

    report = system_status.build_system_status_report(
        runtime_root=runtime_root,
        expected_business_date=TARGET_DATE,
        runtime_mode="historical",
        profile_id="historical-smoke",
        broker_environment="historical_simulated",
        target_business_dates=[TARGET_DATE],
    )

    sources = {
        item["component_id"]: item
        for item in report["data_inspection"]["data_sources"]
    }
    assert sources["normalized_jquants_daily_quotes"]["latest_business_date"] == FUTURE_DATE
    assert _runtime_feature_dates(report) == {TARGET_DATE}
    assert _model_dates(report) == {TARGET_DATE}
    assert report["temporal_authority_audit"]["future_state_reference_count"] == 0
    assert FUTURE_DATE not in _runtime_consumer_resolution_payload(report)


def _runtime_root_with_artifacts(
    tmp_path: Path,
    *,
    target_artifacts: bool,
    future_artifacts: bool,
) -> tuple[Path, Path, Path]:
    runtime_root = tmp_path / ".runtime"
    manifest_path = tmp_path / "accepted_generation_manifest.json"
    _write_json(
        manifest_path,
        {
            "accepted_generation_id": "accepted-generation-fixture",
            "dataset_bundle_ref": {"dataset_revision_ids": ["dataset-fixture"]},
            "candidate_member": {
                "feature_order": ["f1"],
                "feature_schema_hash": "candidate-schema-hash",
                "model_artifact_path": str(tmp_path / "candidate-model.pkl"),
                "scaler_artifact_path": str(tmp_path / "candidate-scaler.pkl"),
                "calibration_artifact_path": str(tmp_path / "candidate-calibration.json"),
            },
            "opportunity_member": {
                "feature_order": ["candidate_score", "f1"],
                "feature_schema_hash": "opportunity-schema-hash",
                "model_artifact_path": str(tmp_path / "opportunity-model.pkl"),
                "scaler_artifact_path": str(tmp_path / "opportunity-scaler.pkl"),
                "calibration_artifact_path": str(tmp_path / "opportunity-calibration.json"),
            },
        },
    )
    for artifact_name in (
        "candidate-model.pkl",
        "candidate-scaler.pkl",
        "candidate-calibration.json",
        "opportunity-model.pkl",
        "opportunity-scaler.pkl",
        "opportunity-calibration.json",
    ):
        (tmp_path / artifact_name).write_text("fixture", encoding="utf-8")

    _write_runtime_state(runtime_root)
    future_manifest = _write_day(runtime_root, FUTURE_DATE) if future_artifacts else runtime_root / "missing_future_manifest.json"
    if target_artifacts:
        _write_day(runtime_root, TARGET_DATE)
    return runtime_root, manifest_path, future_manifest


def _write_runtime_state(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "runtime_state" / "current_state.json",
        {
            "schema_version": "current_state.v1",
            "business_date": TARGET_DATE,
            "as_of": f"{TARGET_DATE}T09:00:00Z",
            "cash": 1_000_000,
            "positions": [],
        },
    )
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "pending_order_plan.v1",
            "state": "EMPTY",
            "active": False,
            "business_date": TARGET_DATE,
            "last_transition_at": f"{TARGET_DATE}T09:01:00Z",
            "orders": [],
        },
    )
    _write_json(
        runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "schema_version": "safety_decision.v1",
            "business_date": TARGET_DATE,
            "created_at": f"{TARGET_DATE}T09:02:00Z",
            "decision": "ALLOW",
        },
    )
    (runtime_root / "runtime_state" / "ledger" / "ledger.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (runtime_root / "runtime_state" / "ledger" / "ledger.jsonl").write_text("", encoding="utf-8")


def _write_day(runtime_root: Path, business_date: str) -> Path:
    artifact_dir = runtime_root / "operations" / "feature_artifacts" / business_date
    artifact_dir.mkdir(parents=True, exist_ok=True)
    feature_specs = {
        "candidate": "candidate_features.parquet",
        "opportunity": "opportunity_feature_input.parquet",
        "position": "position_feature_input.parquet",
        "capital": "capital_policy_input.parquet",
    }
    artifacts = []
    for ai_name, filename in feature_specs.items():
        path = artifact_dir / filename
        path.write_text(f"{ai_name},{business_date}\n", encoding="utf-8")
        artifacts.append(
            {
                "ai_name": ai_name,
                "artifact_path": str(path),
                "data_until": business_date,
                "max_date": business_date,
                "row_count": 2,
                "feature_schema_hash": f"{ai_name}-schema-hash",
                "status": "FEATURES_READY",
            }
        )
    manifest_path = runtime_root / "operations" / "feature_refresh_detail" / business_date / "feature_refresh_manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "feature_refresh_manifest.v1",
            "status": "PASS",
            "created_at": f"{business_date}T09:03:00Z",
            "artifacts": artifacts,
        },
    )
    buy_ai_dir = runtime_root / "runtime_state" / "buy_ai" / business_date
    _write_json(
        buy_ai_dir / "candidate_decisions.json",
        {
            "schema_version": "candidate_decisions.v1",
            "business_date": business_date,
            "feature_date": business_date,
            "feature_path": str(artifact_dir / "candidate_features.parquet"),
            "generated_at": f"{business_date}T09:04:00Z",
            "candidate_count": 2,
            "rows": [{"code": "1301"}, {"code": "1332"}],
        },
    )
    _write_json(
        buy_ai_dir / "opportunity_rankings.json",
        {
            "schema_version": "opportunity_rankings.v1",
            "business_date": business_date,
            "feature_date": business_date,
            "generated_at": f"{business_date}T09:05:00Z",
            "rows": [{"code": "1301"}, {"code": "1332"}],
        },
    )
    _write_json(
        buy_ai_dir / "opportunity_inference_summary.json",
        {
            "schema_version": "opportunity_inference_summary.v1",
            "business_date": business_date,
            "feature_path": str(artifact_dir / "opportunity_feature_input.parquet"),
            "created_at": f"{business_date}T09:06:00Z",
            "input_candidate_count": 2,
            "output_count": 2,
            "top20_count": 2,
        },
    )
    _write_json(
        buy_ai_dir / "ai_lifecycle_gate_decision.json",
        {
            "schema_version": "ai_lifecycle_gate_decision.v1",
            "business_date": business_date,
            "created_at": f"{business_date}T09:07:00Z",
            "decision": "ALLOW",
            "baseline_status": "PASS",
            "freshness_status": "PASS",
        },
    )
    return manifest_path


def _ai_report(
    *,
    manifest_path: Path,
    latest_feature_manifest: Path,
    source_latest_business_date: str = FUTURE_DATE,
) -> dict[str, Any]:
    return {
        "accepted_generation_status": {
            "status": "PASS",
            "accepted_generation_id": "accepted-generation-fixture",
            "manifest_path": str(manifest_path),
        },
        "runtime_authority_status": {
            "status": "PASS",
            "authority_status": "PASS",
            "runtime_business_date": FUTURE_DATE,
            "runtime_loaded_generation": "accepted-generation-fixture",
        },
        "jquants_and_feature_freshness": {
            "status": "PASS",
            "latest_jquants": {
                "latest_successful_daily_quotes_date": source_latest_business_date,
                "latest_normalized_daily_quotes_date": source_latest_business_date,
                "manifest_path": "",
            },
            "latest_buy_feature": {
                "feature_date": FUTURE_DATE,
                "manifest_path": str(latest_feature_manifest),
            },
            "generation_bound": {
                "raw_data_max_date_at_generation": source_latest_business_date,
                "normalized_data_max_date_at_generation": source_latest_business_date,
            },
        },
        "dataset_lineage": {"status": "PASS"},
        "split_audit": {"status": "PASS"},
        "freshness_taxonomy": {"status": "PASS"},
        "candidate_ai_status": {
            "status": "PASS",
            "calibration_hash": "candidate-calibration-hash",
            "runtime_top50_count": 2,
        },
        "opportunity_ai_status": {
            "status": "PASS",
            "calibration_hash": "opportunity-calibration-hash",
            "runtime_top20_count": 2,
            "dual_gate_status": "DUAL_GATE_PASS",
        },
        "runtime_readiness": {
            "status": "PASS",
            "lifecycle_classification": {"status": "PASS"},
        },
    }


def _active_models(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["component_id"]: item
        for item in report["active_component_inventory"]["active_ai_models"]
    }


def _runtime_feature_dates(report: dict[str, Any]) -> set[str]:
    return {
        item["feature_date"]
        for item in report["data_inspection"]["runtime_features"]
        if item.get("feature_date") not in {"", "NOT_YET_MATERIALIZED"}
    }


def _model_dates(report: dict[str, Any]) -> set[str]:
    dates: set[str] = set()
    for item in report["active_component_inventory"]["active_ai_models"]:
        for key in ("latest_inference_date", "latest_inference_input_date"):
            value = item.get(key)
            if value not in {"", "NOT_YET_MATERIALIZED"}:
                dates.add(str(value))
    return dates


def _decision_artifact(report: dict[str, Any], component_id: str) -> str:
    subsystem = next(
        item
        for item in report["decision_subsystems"]["subsystems"]
        if item["component_id"] == component_id
    )
    return str(subsystem["input_artifact"])


def _runtime_consumer_resolution_payload(report: dict[str, Any]) -> str:
    payload = {
        "context": report["inspection_context"],
        "runtime_features": report["data_inspection"]["runtime_features"],
        "active_models": report["active_component_inventory"]["active_ai_models"],
        "decision_subsystems": report["decision_subsystems"],
        "runtime_input_lineage": report["runtime_input_lineage_contract"],
        "runtime_stage_contract": report["runtime_stage_contract"],
        "temporal_authority_audit": report["temporal_authority_audit"],
    }
    return json.dumps(payload, sort_keys=True)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
