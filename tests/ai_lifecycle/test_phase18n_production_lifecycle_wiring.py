from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from ai_fund_lab_v2.ai_lifecycle.policy_operators import (
    PMPolicyEvidenceOperator,
    PM_REQUIRED_SCENARIOS,
    PolicyEvidenceRequest,
    SAFETY_REQUIRED_SCENARIOS,
    SafetyPolicyEvidenceOperator,
    validate_future_ai_onboarding,
)
from ai_fund_lab_v2.ai_lifecycle.rollback_revoke import (
    AtomicRevokeRequest,
    AtomicRollbackRequest,
    IsolatedRegistryRollbackRevokeOperator,
)
from ai_fund_lab_v2.ai_lifecycle.scheduler import (
    LifecycleRetryPolicy,
    LifecycleSchedulerInput,
    WeeklyLifecycleSchedulerOperator,
)
from ai_fund_lab_v2.runtime_v2.ai_lifecycle_gates import evaluate_runtime_ai_gate


def test_phase18n_runtime_gate_contract_blocks_buy_not_sell() -> None:
    result = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "PASS"},
            "freshness": {"dataset_lag_business_days": 0, "model_training_lag_business_days": 21, "model_acceptance_age_business_days": 1},
            "drift": {
                "baseline_identity": "baseline",
                "current_window_identity": "current",
                "baseline_prediction_scores": [0.1] * 30,
                "current_prediction_scores": [0.1] * 30,
                "baseline_feature_values": [1.0] * 30,
                "current_feature_values": [1.0] * 30,
                "baseline_positive_coverage": 0.0,
                "current_positive_coverage": 0.5,
                "baseline_candidate_population": 30,
                "current_candidate_population": 30,
                "baseline_calibration_error": 0.01,
                "current_calibration_error": 0.01,
            },
        }
    )
    payload = result.to_dict()
    assert payload["decision"] == "BLOCK"
    assert payload["classification"] == "MODEL_UNHEALTHY"
    assert payload["block_buy"] is True
    assert payload["block_submit"] is True
    assert payload["block_sell"] is False


def test_phase18n_runtime_gate_market_no_opportunity_and_insufficient_evidence() -> None:
    no_opp = evaluate_runtime_ai_gate(
        {
            "integrity": {"status": "PASS"},
            "freshness": {"dataset_lag_business_days": 0, "model_training_lag_business_days": 0, "model_acceptance_age_business_days": 1},
            "drift": {
                "baseline_identity": "baseline",
                "current_window_identity": "current",
                "baseline_prediction_scores": [-0.1] * 30,
                "current_prediction_scores": [-0.1] * 30,
                "baseline_feature_values": [1.0] * 30,
                "current_feature_values": [1.0] * 30,
                "baseline_positive_coverage": 0.0,
                "current_positive_coverage": 0.0,
                "baseline_candidate_population": 30,
                "current_candidate_population": 30,
                "all_negative_consecutive_business_days": 1,
                "baseline_calibration_error": 0.01,
                "current_calibration_error": 0.01,
            },
        }
    ).to_dict()
    assert no_opp["classification"] == "MARKET_NO_OPPORTUNITY"
    assert no_opp["block_buy"] is False
    insufficient = evaluate_runtime_ai_gate({"freshness": {}, "drift": {}}).to_dict()
    assert insufficient["classification"] == "INSUFFICIENT_EVIDENCE"
    assert insufficient["block_buy"] is True


def test_phase18n_scheduler_lock_retry_timeout_idempotency_and_alert(tmp_path: Path) -> None:
    ticks = [datetime(2026, 7, 17, tzinfo=timezone.utc)]

    def now() -> datetime:
        return ticks[-1]

    operator = WeeklyLifecycleSchedulerOperator(state_root=tmp_path, retry_policy=LifecycleRetryPolicy(max_attempts=2, timeout_seconds=5), now=now)
    input_ = LifecycleSchedulerInput("opportunity_ai", "2026-07-17", 5, 250, "PASS")
    result = operator.run(input_, idempotency_key="window-1", action=lambda: "PROMOTION_REVIEW_REQUIRED")
    assert result.final_state == "PROMOTION_REVIEW_REQUIRED"
    assert Path(result.alert_payload_path).is_file()
    again = operator.run(input_, idempotency_key="window-1", action=lambda: "DATASET_REBUILD_REQUIRED")
    assert again.final_state == result.final_state

    lock_path = tmp_path / "locks" / "candidate_ai.json"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text('{"owner":"other","acquired_at":"2026-07-17T00:00:00+00:00","expires_at":"2026-07-18T00:00:00+00:00","component":"candidate_ai"}')
    contended = operator.run(LifecycleSchedulerInput("candidate_ai", "2026-07-17", 5, 250, "PASS"), idempotency_key="window-2")
    assert contended.lock_status == "CONTENDED"

    ticks.append(ticks[-1] + timedelta(seconds=10))
    timeout = operator.run(input_, idempotency_key="window-3", action=lambda: "TRAINING_REQUIRED")
    assert timeout.final_state in {"FAILED", "TRAINING_REQUIRED", "PROMOTION_REVIEW_REQUIRED"}


def test_phase18n_isolated_atomic_rollback_revoke_and_failures(tmp_path: Path) -> None:
    op = IsolatedRegistryRollbackRevokeOperator(registry_root=tmp_path)
    state_a = {"bundle": "A", "runtime_use_eligible": True}
    state_b = {"bundle": "B", "runtime_use_eligible": True}
    init = op.initialize(accepted_state=state_b)
    targets = {"A": state_a, "B": state_b}
    rollback = op.atomic_rollback(
        AtomicRollbackRequest("rb-1", "B", "A", "rollback", "tester", "APPROVED", init["state_hash"], "", "idem-rb"),
        targets=targets,
    )
    assert rollback["status"] == "PASS"
    duplicate = op.atomic_rollback(
        AtomicRollbackRequest("rb-1", "B", "A", "rollback", "tester", "APPROVED", init["state_hash"], "", "idem-rb"),
        targets=targets,
    )
    assert duplicate["audit_hash"] == rollback["audit_hash"]
    reject = op.atomic_rollback(
        AtomicRollbackRequest("rb-2", "B", "A", "rollback", "tester", "REJECTED", rollback["after_state_hash"], "", "idem-reject"),
        targets=targets,
    )
    assert reject["status"] == "REJECTED"
    mismatch = op.atomic_revoke(
        AtomicRevokeRequest("rv-1", "A", "revoke", "tester", "APPROVED", "B", "bad-hash", "idem-rv"),
        targets=targets,
    )
    assert mismatch["status"] == "FAILED"


def test_phase18n_policy_operators_and_future_validator(tmp_path: Path) -> None:
    pm = PMPolicyEvidenceOperator().run(
        PolicyEvidenceRequest(
            "position_management",
            "pm-policy",
            "v1",
            {"policy_freshness": "PASS", "semantic_regression": "PASS", "runtime_compatibility": "PASS", "buy_gate_independence": True, "scenarios": sorted(PM_REQUIRED_SCENARIOS)},
            "pm-rollback",
            tmp_path,
        )
    )
    assert pm.status == "PASS"
    safety = SafetyPolicyEvidenceOperator().run(
        PolicyEvidenceRequest(
            "safety_policy",
            "safety-policy",
            "v1",
            {"policy_freshness": "PASS", "threshold_evidence": "PASS", "rule_evidence": "PASS", "semantic_regression": "PASS", "scenarios": sorted(SAFETY_REQUIRED_SCENARIOS)},
            "safety-rollback",
            tmp_path,
        )
    )
    assert safety.status == "PASS"
    future = validate_future_ai_onboarding(
        {
            "component_name": "future_alpha",
            "component_classification": "TRAINABLE",
            "required_artifacts": ["model"],
            "required_lifecycle_stages": ["dataset", "training"],
            "runtime_consumer": "Runtime v2",
            "authority_scope": "approval",
            "registry_scope": "accepted artifact",
            "rollback_contract": "required",
            "self_promotion_allowed": False,
        },
        output_dir=tmp_path,
    )
    assert future["status"] == "PASS"
    invalid = validate_future_ai_onboarding({"component_name": "bad", "component_classification": "UNKNOWN"})
    assert invalid["status"] == "REVIEW_REQUIRED"
