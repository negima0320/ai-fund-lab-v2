from __future__ import annotations

from ai_fund_lab_v2.ai_lifecycle.dataset_revision_materialization import (
    APPROVE_WITH_FORMAL_LIMITATION,
    PASS_WITH_FORMAL_LIMITATION,
    RollingSplitPolicy,
    audit_prohibited_training_input_references,
    build_corporate_action_policy_contract,
    build_corporate_action_policy_human_review,
    build_policy_amended_dataset_revision,
    evaluate_corporate_action_policy_sufficiency,
    validate_corporate_action_review_binding,
    validate_rolling_split_policy_contract,
)


def test_human_review_approves_policy_with_reviewed_hash() -> None:
    contract = _policy_contract()
    review = build_corporate_action_policy_human_review(
        review_id="review-1",
        reviewer="user:negishi",
        reviewed_at="2026-07-19T00:00:00+09:00",
        policy_contract=contract,
        evidence_paths=["reports/phase19_ad_u2_c_dataset_policy_blocker_closure/"],
        decision_reason="User approved formal limitations.",
    )

    binding = validate_corporate_action_review_binding(policy_contract=contract, human_review=review)

    assert review["decision"] == APPROVE_WITH_FORMAL_LIMITATION
    assert review["reviewed_hash"] == contract["policy_hash"]
    assert binding["status"] == "PASS"


def test_policy_changed_after_review_blocks_hash_binding() -> None:
    contract = _policy_contract()
    review = build_corporate_action_policy_human_review(
        review_id="review-1",
        reviewer="user:negishi",
        reviewed_at="2026-07-19T00:00:00+09:00",
        policy_contract=contract,
        evidence_paths=[],
        decision_reason="User approved formal limitations.",
    )
    changed = {**contract, "policy_hash": "changed"}

    binding = validate_corporate_action_review_binding(policy_contract=changed, human_review=review)

    assert binding["status"] == "BLOCK"
    assert "reviewed_hash_mismatch" in binding["reason_codes"]


def test_missing_or_codex_reviewer_is_invalid() -> None:
    contract = _policy_contract()
    review = build_corporate_action_policy_human_review(
        review_id="review-1",
        reviewer="codex",
        reviewed_at="2026-07-19T00:00:00+09:00",
        policy_contract=contract,
        evidence_paths=[],
        decision_reason="Invalid reviewer.",
    )

    binding = validate_corporate_action_review_binding(policy_contract=contract, human_review=review)

    assert review["status"] == "INVALID"
    assert binding["status"] == "BLOCK"
    assert "missing_or_invalid_reviewer" in binding["reason_codes"]


def test_sufficiency_passes_with_formal_limitation_when_no_hard_block() -> None:
    contract = _policy_contract()
    review = _review(contract)

    result = evaluate_corporate_action_policy_sufficiency(
        policy_contract=contract,
        human_review=review,
        label_safe_authority={"overall_status": "PASS"},
        current_feature_label_requires_standalone_event=False,
    )

    assert result["decision"] == PASS_WITH_FORMAL_LIMITATION
    assert result["implicit_pass_used"] is False


def test_future_corporate_action_or_adjustment_leakage_blocks() -> None:
    contract = _policy_contract()
    review = _review(contract)

    corporate = evaluate_corporate_action_policy_sufficiency(
        policy_contract=contract,
        human_review=review,
        label_safe_authority={"overall_status": "PASS"},
        current_feature_label_requires_standalone_event=False,
        future_corporate_action_leakage=True,
    )
    adjustment = evaluate_corporate_action_policy_sufficiency(
        policy_contract=contract,
        human_review=review,
        label_safe_authority={"overall_status": "PASS"},
        current_feature_label_requires_standalone_event=False,
        future_adjustment_leakage=True,
    )

    assert corporate["decision"] == "BLOCK"
    assert "FUTURE_CORPORATE_ACTION_LEAKAGE" in corporate["blockers"]
    assert adjustment["decision"] == "BLOCK"
    assert "FUTURE_ADJUSTMENT_LEAKAGE" in adjustment["blockers"]


def test_unknown_unsupported_event_with_feature_impact_requires_review() -> None:
    contract = _policy_contract()
    review = _review(contract)

    result = evaluate_corporate_action_policy_sufficiency(
        policy_contract=contract,
        human_review=review,
        label_safe_authority={"overall_status": "PASS"},
        current_feature_label_requires_standalone_event=False,
        unknown_unsupported_event_feature_impact=True,
    )

    assert result["decision"] == "REVIEW_REQUIRED"


def test_prohibited_training_inputs_block_when_used_as_input_or_target() -> None:
    result = audit_prohibited_training_input_references(
        [
            {"term": "test result", "classification": "TRAINING_INPUT", "path": "features.py"},
            {"term": "audit result", "classification": "TRAINING_TARGET", "path": "labels.py"},
            {"term": "Runtime PnL", "classification": "TRAINING_INPUT", "path": "features.py"},
        ]
    )

    assert result["status"] == "BLOCK"
    assert len(result["violations"]) == 3


def test_prohibited_terms_are_allowed_as_audit_only() -> None:
    result = audit_prohibited_training_input_references(
        [
            {"term": "test result", "classification": "AUDIT_ONLY", "path": "tests/test_policy.py"},
            {"term": "Broker Snapshot", "classification": "RUNTIME_ONLY", "path": "runtime.py"},
        ]
    )

    assert result["status"] == "PASS"


def test_policy_amended_revision_is_append_only_and_keeps_bytes_hash() -> None:
    contract = _policy_contract()
    result = build_policy_amended_dataset_revision(
        previous_revision={
            "dataset_revision": "candidate_dataset_revision_old",
            "component": "Candidate",
            "dataset_hash": "dataset-hash",
            "schema_hash": "schema-hash",
            "artifact_path": "old.json",
        },
        policy_contract=contract,
        sufficiency={"decision": PASS_WITH_FORMAL_LIMITATION},
        created_at="2026-07-19T00:00:00+09:00",
    )

    assert result["previous_dataset_revision"] == "candidate_dataset_revision_old"
    assert result["dataset_hash"] == "dataset-hash"
    assert result["dataset_bytes_reused"] is True
    assert result["corporate_action_policy_hash"] == contract["policy_hash"]
    assert result["dataset_revision"] != "candidate_dataset_revision_old"


def test_rolling_split_threshold_runtime_override_stays_rejected() -> None:
    policy = RollingSplitPolicy(
        policy_version="unapproved",
        training_window_business_days=None,
        validation_window_business_days=None,
        embargo_business_days=20,
        target_horizon_business_days=20,
        minimum_training_rows=None,
        minimum_validation_rows=None,
        trading_calendar_identity="calendar",
    )

    result = validate_rolling_split_policy_contract(
        policy=policy,
        runtime_override={"training_window_business_days": 100},
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert "runtime_override_prohibited" in result["reason_codes"]


def _policy_contract() -> dict:
    return build_corporate_action_policy_contract(
        policy_id="phase19_ad_u2_d_corporate_action_dataset_handling",
        effective_from="2026-07-19",
        authority="User Human Review decision for Phase19-AD-U2-D",
        decision_reason="Approve current Corporate Action handling with formal limitations.",
        review_reference="Phase19-AD-U2-D",
        source_authorities={"jquants": "PIT market/listed/calendar data"},
    )


def _review(contract: dict) -> dict:
    return build_corporate_action_policy_human_review(
        review_id="review-1",
        reviewer="user:negishi",
        reviewed_at="2026-07-19T00:00:00+09:00",
        policy_contract=contract,
        evidence_paths=[],
        decision_reason="User approved formal limitations.",
    )
