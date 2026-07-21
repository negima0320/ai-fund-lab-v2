from __future__ import annotations

from ai_fund_lab_v2.ai_lifecycle.dataset_revision_materialization import (
    ROLLING_SPLIT_POLICY_APPROVED,
    build_approved_rolling_split_policy_contract,
    build_rolling_split_policy_human_review_approval,
    build_versioned_split_from_evidence,
    validate_approved_versioned_split,
    validate_rolling_split_review_binding,
)


def test_approved_policy_binds_reviewed_hash_and_deferred_model_quality_values() -> None:
    policy = _policy()
    review = _review(policy)
    binding = validate_rolling_split_review_binding(policy_contract=policy, human_review=review)

    assert policy["policy_status"] == ROLLING_SPLIT_POLICY_APPROVED
    assert policy["reviewed_hash"] == policy["policy_hash"]
    assert review["reviewed_hash"] == policy["policy_hash"]
    assert binding["status"] == "PASS"
    assert "minimum_training_rows" in policy["deferred_model_quality_decisions"]


def test_review_hash_mismatch_blocks_reuse_after_policy_change() -> None:
    policy = _policy()
    review = _review(policy)
    changed = {**policy, "policy_hash": "changed"}

    binding = validate_rolling_split_review_binding(policy_contract=changed, human_review=review)

    assert binding["status"] == "BLOCK"
    assert "reviewed_hash_mismatch" in binding["reason_codes"]


def test_draft_or_unapproved_policy_cannot_generate_split() -> None:
    policy = {**_policy(), "policy_status": "DRAFT_REVIEW_REQUIRED"}

    split = build_versioned_split_from_evidence(
        component="Candidate",
        dataset_revision=_revision(),
        split_evidence=_split_evidence(),
        policy_contract=policy,
        created_at="2026-07-19T00:00:00+09:00",
    )

    assert split["status"] == "BLOCK"
    assert split["split_id"] is None


def test_approved_policy_generates_valid_generation_input_split() -> None:
    policy = _policy()
    revision = _revision()

    split = build_versioned_split_from_evidence(
        component="Candidate",
        dataset_revision=revision,
        split_evidence=_split_evidence(),
        policy_contract=policy,
        created_at="2026-07-19T00:00:00+09:00",
    )
    validation = validate_approved_versioned_split(
        split=split,
        dataset_revision=revision,
        label_safe_authority={"dataset_max": "2026-05-15"},
        policy_contract=policy,
    )

    assert split["split_id"]
    assert split["generation_input_artifact"] is True
    assert split["runtime_consumed"] is False
    assert validation["status"] == "PASS"


def test_embargo_shorter_than_target_blocks_validation() -> None:
    policy = _policy()
    revision = _revision()
    split = build_versioned_split_from_evidence(
        component="Candidate",
        dataset_revision=revision,
        split_evidence=_split_evidence(),
        policy_contract=policy,
        created_at="2026-07-19T00:00:00+09:00",
    )
    split["embargo_business_days"] = 10

    validation = validate_approved_versioned_split(
        split=split,
        dataset_revision=revision,
        label_safe_authority={"dataset_max": "2026-05-15"},
        policy_contract=policy,
    )

    assert validation["status"] == "BLOCK"
    assert "embargo_not_equal_target_horizon" in validation["reason_codes"]


def test_split_after_label_safe_dataset_max_blocks_validation() -> None:
    policy = _policy()
    revision = _revision()
    split = build_versioned_split_from_evidence(
        component="Candidate",
        dataset_revision=revision,
        split_evidence={**_split_evidence(), "recent_holdout_end": "2026-06-01"},
        policy_contract=policy,
        created_at="2026-07-19T00:00:00+09:00",
    )

    validation = validate_approved_versioned_split(
        split=split,
        dataset_revision=revision,
        label_safe_authority={"dataset_max": "2026-05-15"},
        policy_contract=policy,
    )

    assert validation["status"] == "BLOCK"
    assert "holdout_after_label_safe_dataset_max" in validation["reason_codes"]


def _policy() -> dict:
    return build_approved_rolling_split_policy_contract(
        policy_id="phase19_ad_u2_f_rolling_split_policy",
        effective_from="2026-07-19",
        reviewer="user:negishi",
        source_draft={"policy_hash": "draft-hash"},
        trading_calendar_identity="calendar-hash",
    )


def _review(policy: dict) -> dict:
    return build_rolling_split_policy_human_review_approval(
        review_id="phase19_ad_u2_f_review",
        reviewer="user:negishi",
        reviewed_at="2026-07-19T00:00:00+09:00",
        policy_contract=policy,
        decision_reason="User approved Option C.",
        evidence_paths=[],
    )


def _revision() -> dict:
    return {
        "dataset_revision": "candidate_dataset_revision",
        "dataset_hash": "dataset-hash",
        "schema_hash": "schema-hash",
    }


def _split_evidence() -> dict:
    return {
        "train_start": "2021-06-14",
        "train_end": "2024-12-02",
        "validation_start": "2025-01-06",
        "validation_end": "2025-12-01",
        "test_start": "2026-01-05",
        "test_end": "2026-03-03",
        "recent_holdout_start": "2026-04-01",
        "recent_holdout_end": "2026-05-15",
        "train_business_days": 852,
        "validation_business_days": 222,
        "test_business_days": 39,
        "recent_holdout_business_days": 29,
    }
