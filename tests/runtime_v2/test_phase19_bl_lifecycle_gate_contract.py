from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.ai_lifecycle_gates import evaluate_runtime_ai_gate
from ai_fund_lab_v2.runtime_v2.lifecycle_evidence import (
    _build_current_window_evidence,
    build_runtime_lifecycle_evidence,
)


def test_phase19_bl_generation_source_coverage_metadata_is_not_future_consumption(tmp_path: Path) -> None:
    manifest = _phase19_manifest(tmp_path, raw_max="2026-07-14", normalized_max="2026-07-14")
    evidence = build_runtime_lifecycle_evidence(
        runtime_root=tmp_path,
        business_date="2026-07-06",
        feature_date="2026-07-06",
        runtime_id="runtime-test",
        candidate_payload={"rows": [{"code": "1001", "candidate_score": 1.0}] * 50},
        opportunity_payload={"rankings": [{"code": "1001", "opportunity_score": 0.1}] * 50},
        accepted_bundle_path=manifest,
    )

    assert evidence.freshness_evidence["raw_data_max_date_at_generation"] == "2026-07-14"
    assert evidence.freshness_evidence["actual_consumed_source_max_date"] == "2026-07-06"
    assert "source_data_after_business_date" not in evidence.freshness_evidence["reason_codes"]


def test_phase19_bl_actual_future_feature_consumption_is_review_required(tmp_path: Path) -> None:
    manifest = _phase19_manifest(tmp_path, raw_max="2026-07-14", normalized_max="2026-07-14")
    evidence = build_runtime_lifecycle_evidence(
        runtime_root=tmp_path,
        business_date="2026-07-06",
        feature_date="2026-07-07",
        runtime_id="runtime-test",
        candidate_payload={"rows": [{"code": "1001", "candidate_score": 1.0}] * 50},
        opportunity_payload={"rankings": [{"code": "1001", "opportunity_score": 0.1}] * 50},
        accepted_bundle_path=manifest,
    )

    assert "source_data_after_business_date" in evidence.freshness_evidence["reason_codes"]
    assert "feature_date_after_business_date" in evidence.freshness_evidence["reason_codes"]
    assert evidence.freshness_evidence["status"] == "REVIEW_REQUIRED"


def test_phase19_bl_prediction_semantics_match_allows_psi() -> None:
    gate = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "PASS"},
            "freshness": _freshness_pass(),
            "drift": {
                "baseline_prediction_scores": [0.1, 0.2, 0.3, 0.4, 0.5],
                "current_prediction_scores": [0.11, 0.21, 0.29, 0.41, 0.49],
                "baseline_prediction_contract": _prediction_contract("standardized_score"),
                "current_prediction_contract": _prediction_contract("standardized_score"),
                "baseline_feature_values": [1, 2, 3, 4, 5],
                "current_feature_values": [1, 2, 3, 4, 5],
                "baseline_feature_contract": _feature_contract("scope"),
                "current_feature_contract": _feature_contract("scope"),
                "baseline_candidate_population": 50,
                "current_candidate_population": 50,
                "baseline_population_contract": {"population_scope": "scope"},
                "current_population_contract": {"population_scope": "scope"},
            },
        }
    ).to_dict()

    prediction = next(item for item in gate["evidence"] if item["name"] == "prediction_distribution_drift")
    assert prediction["metric"] == "psi"


def test_phase19_bl_prediction_semantics_mismatch_skips_psi() -> None:
    gate = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "PASS"},
            "freshness": _freshness_pass(),
            "drift": {
                "baseline_prediction_scores": [0.1, 0.2, 0.3, 0.4, 0.5],
                "current_prediction_scores": [10, 20, 30, 40, 50],
                "baseline_prediction_contract": _prediction_contract("raw_prediction"),
                "current_prediction_contract": _prediction_contract("calibrated_expected_edge"),
                "baseline_feature_values": [1, 2, 3, 4, 5],
                "current_feature_values": [1, 2, 3, 4, 5],
                "baseline_feature_contract": _feature_contract("scope"),
                "current_feature_contract": _feature_contract("scope"),
                "baseline_candidate_population": 50,
                "current_candidate_population": 50,
                "baseline_population_contract": {"population_scope": "scope"},
                "current_population_contract": {"population_scope": "scope"},
            },
        }
    ).to_dict()

    prediction = next(item for item in gate["evidence"] if item["name"] == "prediction_distribution_drift")
    assert prediction["metric"] == "BASELINE_CURRENT_SEMANTICS_MISMATCH"
    assert prediction["value"] is None


def test_phase19_bl_feature_distribution_uses_runtime_feature_space_not_constant_candidate_scores(tmp_path: Path) -> None:
    feature_path = tmp_path / "opportunity_feature_input.parquet"
    frame = pd.DataFrame(
        {
            "target_date": ["2026-07-06"] * 3,
            "code": ["1001", "1002", "1003"],
            "feature__candidate_score": [0.1, 0.5, 0.9],
            "feature__price_momentum_return_20d": [1.0, 2.0, 4.0],
        }
    )
    frame.to_parquet(feature_path)

    current = _build_current_window_evidence(
        runtime_id="runtime-test",
        feature_date="2026-07-06",
        candidate_payload={"rows": [{"code": code, "candidate_score": 1.0} for code in ("1001", "1002", "1003")]},
        opportunity_payload={
            "opportunity_feature_path": str(feature_path),
            "rankings": [{"code": code, "opportunity_score": 0.1} for code in ("1001", "1002", "1003")],
        },
        baseline_evidence={
            "feature_contract": {
                "feature_names": ["feature__candidate_score", "feature__price_momentum_return_20d"],
                "feature_order_hash": "feature-hash",
            }
        },
    )

    assert current["feature_distribution_values"]
    assert set(current["feature_distribution_values"]) != {1.0}
    assert current["feature_contract"]["source_artifact"] == str(feature_path)


def test_phase19_bl_population_scope_match_allows_ratio() -> None:
    gate = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "PASS"},
            "freshness": _freshness_pass(),
            "drift": {
                "baseline_prediction_scores": [0.1, 0.2, 0.3, 0.4, 0.5],
                "current_prediction_scores": [0.1, 0.2, 0.3, 0.4, 0.5],
                "baseline_prediction_contract": _prediction_contract("standardized_score", scope="CandidateTop50_single_business_day"),
                "current_prediction_contract": _prediction_contract("standardized_score", scope="CandidateTop50_single_business_day"),
                "baseline_feature_values": [1, 2, 3, 4, 5],
                "current_feature_values": [1, 2, 3, 4, 5],
                "baseline_feature_contract": _feature_contract("CandidateTop50_single_business_day"),
                "current_feature_contract": _feature_contract("CandidateTop50_single_business_day"),
                "baseline_candidate_population": 50,
                "current_candidate_population": 50,
                "baseline_population_contract": {"population_scope": "CandidateTop50_single_business_day"},
                "current_population_contract": {"population_scope": "CandidateTop50_single_business_day"},
            },
        }
    ).to_dict()

    population = next(item for item in gate["evidence"] if item["name"] == "candidate_population_drift")
    assert population["metric"] == "current_to_baseline_population_ratio"


def test_phase19_bl_population_scope_mismatch_skips_ratio() -> None:
    gate = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "PASS"},
            "freshness": _freshness_pass(),
            "drift": {
                "baseline_prediction_scores": [0.1, 0.2, 0.3, 0.4, 0.5],
                "current_prediction_scores": [0.1, 0.2, 0.3, 0.4, 0.5],
                "baseline_prediction_contract": _prediction_contract("standardized_score", scope="full_universe"),
                "current_prediction_contract": _prediction_contract("standardized_score", scope="CandidateTop50"),
                "baseline_feature_values": [1, 2, 3, 4, 5],
                "current_feature_values": [1, 2, 3, 4, 5],
                "baseline_feature_contract": _feature_contract("full_universe"),
                "current_feature_contract": _feature_contract("CandidateTop50"),
                "baseline_candidate_population": 1940,
                "current_candidate_population": 50,
                "baseline_population_contract": {"population_scope": "full_universe"},
                "current_population_contract": {"population_scope": "CandidateTop50"},
            },
        }
    ).to_dict()

    population = next(item for item in gate["evidence"] if item["name"] == "candidate_population_drift")
    assert population["metric"] == "BASELINE_CURRENT_POPULATION_SCOPE_MISMATCH"
    assert population["value"] is None


def test_phase19_bl_buy_lifecycle_review_preserves_sell_continuity() -> None:
    gate = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "PASS"},
            "freshness": _freshness_pass(),
            "drift": {
                "baseline_prediction_scores": [0.1, 0.2, 0.3, 0.4, 0.5],
                "current_prediction_scores": [10, 20, 30, 40, 50],
                "baseline_prediction_contract": _prediction_contract("raw_prediction"),
                "current_prediction_contract": _prediction_contract("calibrated_expected_edge"),
                "baseline_feature_values": [1, 2, 3, 4, 5],
                "current_feature_values": [1, 2, 3, 4, 5],
                "baseline_feature_contract": _feature_contract("scope"),
                "current_feature_contract": _feature_contract("scope"),
                "current_candidate_population": 50,
            },
        }
    ).to_dict()

    assert gate["decision"] == "REVIEW_REQUIRED"
    assert gate["monitoring_action"] == "HUMAN_REVIEW"
    assert gate["trading_permission_effect"] == "NONE"
    assert gate["runtime_integrity_status"] == "PASS"
    assert gate["block_buy"] is False
    assert gate["block_buy_planning"] is False
    assert gate["block_buy_submit"] is False
    assert gate["block_sell"] is False
    assert gate["block_sell_planning"] is False
    assert gate["block_sell_submit"] is False
    assert gate["allow_sell_planning"] is True
    assert gate["allow_sell_submit_authorization"] is True


def _freshness_pass() -> dict:
    return {
        "dataset_lag_business_days": 0,
        "model_training_lag_business_days": 0,
        "model_acceptance_age_business_days": 0,
        "source_data_age_business_days": 0,
        "feature_data_age_business_days": 0,
        "reason_codes": [],
    }


def _prediction_contract(semantics: str, *, scope: str = "scope") -> dict:
    return {
        "prediction_metric_name": "opportunity_score",
        "prediction_semantics": semantics,
        "transformation_stage": "stage",
        "calibration_applied": semantics != "raw_prediction",
        "population_scope": scope,
    }


def _feature_contract(scope: str) -> dict:
    return {
        "feature_order_hash": "feature-hash",
        "feature_count": 2,
        "population_scope": scope,
        "aggregation_method": "per_feature_summary_min_max_mean_std",
    }


def _phase19_manifest(tmp_path: Path, *, raw_max: str, normalized_max: str) -> Path:
    model = tmp_path / "model.pkl"
    model.write_bytes(b"model")
    baseline = {
        "prediction_distribution_values": [0.1, 0.2, 0.3, 0.4, 0.5],
        "feature_distribution_values": [1, 2, 3, 4, 5],
        "candidate_population": 50,
        "positive_coverage": 1.0,
    }
    baseline_path = tmp_path / "baseline.json"
    _write_json(baseline_path, baseline)
    manifest = tmp_path / "accepted_generation_manifest.json"
    _write_json(
        manifest,
        {
            "accepted_generation_id": "phase19-fixture",
            "aggregate_hash": "aggregate-hash",
            "runtime_baseline_hash": "",
            "runtime_baseline_ref": {"path": str(baseline_path)},
            "dual_gate_ref": {"artifact_id": "dual-gate"},
            "candidate_member": {"model_file": str(model), "model_hash": ""},
            "opportunity_member": {"model_file": str(model), "model_hash": ""},
            "accepted_at": "2026-07-20T00:00:00+09:00",
            "freshness_metadata": {
                "generation_bound": {
                    "label_safe_cutoff": "2026-06-04",
                    "dataset_target_max_date": "2026-05-15",
                    "candidate_training_cutoff": "2024-12-02",
                    "opportunity_training_cutoff": "2024-12-02",
                    "raw_data_max_date_at_generation": raw_max,
                    "normalized_data_max_date_at_generation": normalized_max,
                    "freshness_policy_version": "phase19_ap_freshness_policy.v1",
                }
            },
        },
    )
    return manifest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
