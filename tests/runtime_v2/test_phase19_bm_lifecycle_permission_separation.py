from __future__ import annotations

import pytest

from ai_fund_lab_v2.runtime_v2.ai_lifecycle_gates import evaluate_runtime_ai_gate


def test_phase19_bm_lifecycle_review_does_not_block_daily_buy_when_runtime_integrity_passes() -> None:
    gate = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "PASS"},
            "freshness": _freshness_pass(),
            "drift": {
                "baseline_prediction_scores": [0.1, 0.2, 0.3, 0.4, 0.5],
                "current_prediction_scores": [10, 20, 30, 40, 50],
                "baseline_prediction_contract": _prediction_contract("standardized_score", scope="CandidateTop50_validation_window_aggregate"),
                "current_prediction_contract": _prediction_contract("runtime_opportunity_score", scope="CandidateTop50_single_business_day"),
                "baseline_feature_values": [1, 2, 3, 4, 5],
                "current_feature_values": [1, 2, 3, 4, 5],
                "baseline_feature_contract": _feature_contract("CandidateTop50_validation_window_aggregate"),
                "current_feature_contract": _feature_contract("CandidateTop50_single_business_day"),
                "baseline_candidate_population": 1940,
                "current_candidate_population": 50,
                "baseline_population_contract": {"population_scope": "CandidateTop50_validation_window_aggregate"},
                "current_population_contract": {"population_scope": "CandidateTop50_single_business_day"},
                "baseline_positive_coverage": 0.5,
                "current_positive_coverage": 0.5,
            },
        }
    ).to_dict()

    assert gate["decision"] == "REVIEW_REQUIRED"
    assert gate["classification"] == "MODEL_HEALTH_REVIEW_REQUIRED"
    assert gate["monitoring_action"] == "HUMAN_REVIEW"
    assert gate["trading_permission_effect"] == "NONE"
    assert gate["runtime_integrity_status"] == "PASS"
    assert gate["block_buy"] is False
    assert gate["block_buy_planning"] is False
    assert gate["block_buy_submit"] is False
    assert gate["block_sell"] is False
    assert gate["block_sell_planning"] is False
    assert gate["block_sell_submit"] is False


@pytest.mark.parametrize(
    "reason_code",
    [
        "artifact_hash_mismatch",
        "schema_mismatch",
        "model_load_failure",
        "required_feature_missing",
        "non_finite_feature",
        "inference_failure",
    ],
)
def test_phase19_bm_runtime_integrity_failures_block_daily_buy(reason_code: str) -> None:
    gate = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "CRITICAL_AUTHORITY_VIOLATION", "reason_codes": [reason_code]},
            "freshness": _freshness_pass(),
            "drift": _drift_pass(),
        }
    ).to_dict()

    assert gate["decision"] == "BLOCK"
    assert gate["trading_permission_effect"] == "BUY_BLOCK"
    assert gate["runtime_integrity_status"] == "BLOCK"
    assert gate["block_buy"] is True
    assert gate["block_buy_planning"] is True
    assert gate["block_buy_submit"] is True
    assert reason_code in gate["runtime_integrity_reason_codes"][0]


def test_phase19_bm_future_data_consumption_blocks_daily_buy() -> None:
    gate = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "PASS"},
            "freshness": {**_freshness_pass(), "reason_codes": ["feature_date_after_business_date"]},
            "drift": _drift_pass(),
        }
    ).to_dict()

    assert gate["decision"] == "BLOCK"
    assert gate["trading_permission_effect"] == "BUY_BLOCK"
    assert gate["runtime_integrity_status"] == "BLOCK"
    assert gate["block_buy_planning"] is True
    assert gate["block_buy_submit"] is True


def test_phase19_bm_lifecycle_pass_contract_remains_non_blocking() -> None:
    gate = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "PASS"},
            "freshness": _freshness_pass(),
            "drift": _drift_pass(),
        }
    ).to_dict()

    assert gate["decision"] == "PASS"
    assert gate["classification"] == "HEALTHY"
    assert gate["monitoring_action"] == "NONE"
    assert gate["trading_permission_effect"] == "NONE"
    assert gate["runtime_integrity_status"] == "PASS"
    assert gate["block_buy"] is False
    assert gate["block_sell"] is False


def test_phase19_bm_contract_is_common_across_runtime_profiles() -> None:
    for profile in ("historical", "demo", "production"):
        gate = evaluate_runtime_ai_gate(
            {
                "profile": profile,
                "integrity": {"status": "PASS"},
                "freshness": _freshness_pass(),
                "drift": {
                    **_drift_pass(),
                    "baseline_prediction_contract": _prediction_contract("standardized_score"),
                    "current_prediction_contract": _prediction_contract("runtime_opportunity_score"),
                },
            }
        ).to_dict()
        assert gate["decision"] == "REVIEW_REQUIRED"
        assert gate["trading_permission_effect"] == "NONE"
        assert gate["block_buy_planning"] is False
        assert gate["block_sell_planning"] is False


def _freshness_pass() -> dict:
    return {
        "dataset_lag_business_days": 0,
        "model_training_lag_business_days": 0,
        "model_acceptance_age_business_days": 0,
        "source_data_age_business_days": 0,
        "feature_data_age_business_days": 0,
        "reason_codes": [],
    }


def _prediction_contract(semantics: str, *, scope: str = "CandidateTop50_single_business_day") -> dict:
    return {
        "prediction_metric_name": "opportunity_score",
        "prediction_semantics": semantics,
        "transformation_stage": "runtime_artifact_opportunity_score",
        "calibration_applied": semantics != "runtime_opportunity_score",
        "population_scope": scope,
    }


def _feature_contract(scope: str = "CandidateTop50_single_business_day") -> dict:
    return {
        "feature_order_hash": "feature-hash",
        "feature_count": 2,
        "population_scope": scope,
        "aggregation_method": "per_feature_summary_min_max_mean_std",
    }


def _drift_pass() -> dict:
    return {
        "baseline_prediction_scores": [0.1, 0.2, 0.3, 0.4, 0.5],
        "current_prediction_scores": [0.1, 0.2, 0.3, 0.4, 0.5],
        "baseline_prediction_contract": _prediction_contract("runtime_opportunity_score"),
        "current_prediction_contract": _prediction_contract("runtime_opportunity_score"),
        "baseline_feature_values": [1, 2, 3, 4, 5],
        "current_feature_values": [1, 2, 3, 4, 5],
        "baseline_feature_contract": _feature_contract(),
        "current_feature_contract": _feature_contract(),
        "baseline_candidate_population": 50,
        "current_candidate_population": 50,
        "baseline_population_contract": {"population_scope": "CandidateTop50_single_business_day"},
        "current_population_contract": {"population_scope": "CandidateTop50_single_business_day"},
        "baseline_positive_coverage": 0.5,
        "current_positive_coverage": 0.5,
    }
