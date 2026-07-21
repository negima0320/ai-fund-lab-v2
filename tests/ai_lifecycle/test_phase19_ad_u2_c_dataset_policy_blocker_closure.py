from __future__ import annotations

from ai_fund_lab_v2.ai_lifecycle.dataset_revision_materialization import (
    HUMAN_REVIEW_REQUIRED,
    NO_RETRAIN_INSUFFICIENT_NEW_DATA,
    RollingSplitPolicy,
    build_corporate_action_acceptance_policy,
    build_dataset_split_policy_human_review,
    evaluate_bootstrap_vs_retraining_sufficiency,
    evaluate_formal_label_safe_cutoff_authority,
    generate_rolling_split_from_revision,
    validate_rolling_split_policy_contract,
)


def test_label_safe_metadata_mismatch_is_recorded_but_safe_rows_can_pass() -> None:
    result = evaluate_formal_label_safe_cutoff_authority(
        dataset_revision=_revision(target_date_max="2026-01-05"),
        latest_source_market_date="2026-01-09",
        legacy_metadata_label_safe_cutoff="2026-01-08",
        trading_calendar_dates=["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-09"],
        target_horizon_business_days=3,
        unavailable_label_rows=0,
    )

    assert result["status"] == "PASS"
    assert result["computed_label_safe_cutoff"] == "2026-01-05"
    assert result["metadata_cutoff_mismatch"] is True
    assert "legacy_metadata_cutoff_mismatch_recorded" in result["reason_codes"]


def test_label_safe_blocks_when_dataset_max_exceeds_formal_cutoff() -> None:
    result = evaluate_formal_label_safe_cutoff_authority(
        dataset_revision=_revision(target_date_max="2026-01-06"),
        latest_source_market_date="2026-01-09",
        legacy_metadata_label_safe_cutoff="2026-01-05",
        trading_calendar_dates=["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-09"],
        target_horizon_business_days=3,
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert "dataset_max_not_after_computed_cutoff" in result["reason_codes"]


def test_corporate_action_unknowns_require_formal_human_review() -> None:
    policy = build_corporate_action_acceptance_policy(
        source_inventory={"source": "jquants", "cutoff": "2026-06-26"},
        feature_impact_matrix=[
            {"event_type": "split_adjustment", "evidence_status": "PARTIAL", "future_leakage_guard": True},
            {"event_type": "code_change", "evidence_status": "UNKNOWN", "future_leakage_guard": True},
        ],
    )

    assert policy["status"] == HUMAN_REVIEW_REQUIRED
    assert policy["implicit_pass_used"] is False
    assert "code_change:unknown" in policy["review_reasons"]


def test_corporate_action_future_leakage_blocks() -> None:
    policy = build_corporate_action_acceptance_policy(
        source_inventory={"source": "jquants"},
        feature_impact_matrix=[
            {"event_type": "merger", "evidence_status": "PASS", "future_leakage_guard": False},
        ],
    )

    assert policy["status"] == "BLOCK"
    assert "merger:future_leakage_guard_missing" in policy["blockers"]


def test_split_policy_requires_human_review_hash_before_split_generation() -> None:
    policy = RollingSplitPolicy(
        policy_version="phase19_ad_u2_c_candidate_option",
        training_window_business_days=None,
        validation_window_business_days=40,
        embargo_business_days=20,
        target_horizon_business_days=20,
        minimum_training_rows=None,
        minimum_validation_rows=None,
        trading_calendar_identity="calendar",
    )
    review = build_dataset_split_policy_human_review(policy_options=[policy.to_dict()])

    split = generate_rolling_split_from_revision(
        revision=_revision(),
        policy=policy,
        trading_calendar_dates=["2026-01-05", "2026-01-06", "2026-01-07"],
        created_at="2026-07-19T00:00:00+09:00",
    )

    assert review["status"] == HUMAN_REVIEW_REQUIRED
    assert split["status"] == "REVIEW_REQUIRED"
    assert "split_id" not in split


def test_rolling_split_policy_rejects_runtime_override_and_hash_mismatch() -> None:
    policy = RollingSplitPolicy(
        policy_version="phase19_ad_u2_c_option",
        training_window_business_days=793,
        validation_window_business_days=40,
        embargo_business_days=20,
        target_horizon_business_days=20,
        minimum_training_rows=250,
        minimum_validation_rows=250,
        trading_calendar_identity="calendar",
    )

    result = validate_rolling_split_policy_contract(
        policy=policy,
        expected_policy_hash="wrong",
        runtime_override={"validation_window_business_days": 5},
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert "runtime_override_prohibited" in result["reason_codes"]
    assert "policy_hash_mismatch" in result["reason_codes"]


def test_human_review_hash_mismatch_is_not_approved() -> None:
    policy = RollingSplitPolicy(
        policy_version="phase19_ad_u2_c_option",
        training_window_business_days=793,
        validation_window_business_days=40,
        embargo_business_days=20,
        target_horizon_business_days=20,
        minimum_training_rows=250,
        minimum_validation_rows=250,
        trading_calendar_identity="calendar",
    )
    review = build_dataset_split_policy_human_review(
        policy_options=[policy.to_dict()],
        selected_policy_hash=policy.to_dict()["policy_hash"],
        reviewer_decision={
            "decision": "APPROVE",
            "approved_policy_hash": "changed-after-review",
            "reviewer": "human",
            "reviewed_at": "2026-07-19T00:00:00+09:00",
        },
    )

    assert review["status"] == HUMAN_REVIEW_REQUIRED
    assert "split_policy_hash_not_approved" in review["reason_codes"]


def test_bootstrap_sufficiency_is_separate_from_retraining_trigger() -> None:
    result = evaluate_bootstrap_vs_retraining_sufficiency(
        dataset_revision=_revision(row_count=1000),
        label_safe_availability={"status": "PASS"},
        split_policy_review={"status": HUMAN_REVIEW_REQUIRED},
        corporate_action_policy={"status": HUMAN_REVIEW_REQUIRED},
        previous_generation_ref=None,
        incremental_business_days=0,
        incremental_rows=0,
        min_incremental_business_days=5,
        min_incremental_rows=250,
    )

    assert result["bootstrap_generation_input_sufficiency"] == HUMAN_REVIEW_REQUIRED
    assert result["retrain_trigger_sufficiency"] == "INSUFFICIENT"
    assert result["retrain_decision_code"] == NO_RETRAIN_INSUFFICIENT_NEW_DATA


def _revision(*, target_date_max: str = "2026-05-15", row_count: int = 100) -> dict:
    return {
        "dataset_revision": "candidate_dataset_revision",
        "component": "Candidate",
        "schema_hash": "schema",
        "target_date_min": "2021-06-14",
        "target_date_max": target_date_max,
        "label_safe_cutoff": "2026-06-04",
        "row_count": row_count,
    }
