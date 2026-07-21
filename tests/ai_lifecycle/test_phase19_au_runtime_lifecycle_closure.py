from pathlib import Path

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation
from ai_fund_lab_v2.runtime_v2.ai_lifecycle_gates import evaluate_runtime_ai_gate


def test_phase19_au_statistical_drift_review_does_not_auto_stop_buy() -> None:
    result = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "PASS"},
            "freshness": {
                "dataset_lag_business_days": 0,
                "model_training_lag_business_days": 0,
                "model_acceptance_age_business_days": 0,
                "source_data_age_business_days": 0,
                "feature_data_age_business_days": 0,
            },
            "drift": {
                "baseline_prediction_scores": [0.0, 0.1, 0.2, 0.3, 0.4],
                "current_prediction_scores": [100.0, 101.0, 102.0, 103.0, 104.0],
                "baseline_feature_values": [0.0, 0.1, 0.2, 0.3, 0.4],
                "current_feature_values": [10.0, 11.0, 12.0, 13.0, 14.0],
                "baseline_candidate_population": 1000,
                "current_candidate_population": 50,
                "baseline_positive_coverage": 0.01,
                "current_positive_coverage": 1.0,
            },
        }
    )

    payload = result.to_dict()
    assert payload["decision"] == "REVIEW_REQUIRED"
    assert payload["classification"] == "STATISTICAL_DRIFT_REVIEW_REQUIRED"
    assert payload["block_buy"] is False
    assert payload["block_buy_planning"] is False


def test_phase19_au_committed_resolver_supplies_accepted_opportunity_metrics() -> None:
    resolution = resolve_accepted_generation(Path(".runtime"))

    assert resolution.is_resolved
    metrics_path = resolution.artifact_paths()["opportunity_metrics"]
    assert metrics_path == Path("reports/phase19_aj_formal_corrective_reevaluation/opportunity_dual_gate_artifact.json")
    assert metrics_path.is_file()

