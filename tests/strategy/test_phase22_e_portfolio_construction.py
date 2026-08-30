from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import corporate_event, market_context, portfolio_policy, position_management, strategy_intelligence
from ai_fund_lab_v2.strategy.portfolio_construction import (
    PortfolioConstructionConsumerError,
    PortfolioConstructionSchemaError,
    PortfolioConstructionSourceSummary,
    _positive_increment_over_target,
    _select_target_members,
    apply_lot_aware_final_reallocation,
    build_capital_competition_framework,
    build_portfolio_construction_payload,
    default_runtime_artifact_path,
    load_portfolio_construction_fixture,
    portfolio_construction_hash,
    produce_portfolio_construction_artifact,
    validate_portfolio_construction_artifact,
    verify_source_hashes,
)
from ai_fund_lab_v2.strategy.portfolio_policy import PortfolioPolicyConfig, PortfolioPolicyInputSummary
from ai_fund_lab_v2.strategy.shadow_runtime import _ai_output_summary, _pc_summary


def test_phase22_e_produces_draft_review_required_not_eligible_artifact(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["artifact_lifecycle_status"] == "DRAFT"
    assert result.payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert result.payload["position_count_decided"] is False
    assert result.payload["cash_ratio_decided"] is False
    assert result.payload["exposure_decided"] is False
    assert result.payload["position_sizing_decided"] is False
    assert result.payload["allocation_decided"] is False
    assert result.payload["quantity_decided"] is False
    assert validate_portfolio_construction_artifact(result.payload)["status"] == "PASS"


def test_phase22_e_schema_rejects_invalid_intent_missing_code_status_weight_allocation_quantity(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    mutations = (
        lambda item: item["portfolio_members"][0].update({"membership_intent": "HOLD"}),
        lambda item: item["portfolio_members"][0].update({"weight_intent": "10_PERCENT"}),
        lambda item: item["portfolio_members"][0].pop("security_code"),
        lambda item: item.update({"schema_version": "portfolio_construction.v999"}),
        lambda item: item.update({"runtime_consumer_eligibility": "ELIGIBLE"}),
        lambda item: item["portfolio_members"][0].update({"target_weight": -0.1}),
        lambda item: item.update({"allocation_jpy": 100000}),
        lambda item: item["portfolio_members"][0].update({"quantity": 100}),
    )
    for mutation in mutations:
        mutated = json.loads(json.dumps(payload))
        mutation(mutated)
        with pytest.raises(PortfolioConstructionSchemaError):
            validate_portfolio_construction_artifact(mutated)


def test_phase22_e_upstream_review_required_not_eligible_propagates_and_rejects_production(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "upstream_review_required:SOURCE_REVIEW_REQUIRED" in result.payload["reason_codes"]
    assert "upstream_review_required:SOURCE_NOT_ELIGIBLE" not in result.payload["reason_codes"]
    assert result.payload["downstream_calculation_eligibility"] == "CALCULATION_ALLOWED_WITH_REVIEW"
    assert result.payload["upstream_artifacts"]["portfolio_policy"]["shadow_read_allowed"] is True
    assert result.payload["upstream_artifacts"]["position_management"]["shadow_read_allowed"] is True
    with pytest.raises(PortfolioConstructionConsumerError):
        load_portfolio_construction_fixture(result.artifact_path, for_production=True)


def test_phase22_e_upstream_block_schema_date_hash_propagates(tmp_path: Path) -> None:
    market_bad = _write_market_context(tmp_path, schema_version="strategy_market_context.v999")
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=market_bad,
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_source_summary(tmp_path, "construction_policy_config"),
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert any(reason.startswith("upstream_block:") for reason in payload["reason_codes"])

    pm_bad = _write_position_management(tmp_path)
    mutated = json.loads(pm_bad.read_text(encoding="utf-8"))
    mutated["positions"][0]["action"] = "EXIT"
    _write_json(pm_bad, mutated)
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=pm_bad,
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_source_summary(tmp_path, "construction_policy_config"),
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert "upstream_block:INCOMPATIBLE_HASH" in payload["reason_codes"]


def test_phase22_e_reconciles_existing_pm_actions_and_new_candidates_without_duplicate_members(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert by_code["7203"]["membership_intent"] == "RETAIN"
    assert by_code["6758"]["membership_intent"] == "RETAIN"
    assert by_code["6758"]["weight_intent"] == "INCREASE"
    assert by_code["9984"]["membership_intent"] == "REDUCE_CANDIDATE"
    assert by_code["8306"]["membership_intent"] == "REMOVE_CANDIDATE"
    assert by_code["6098"]["membership_intent"] == "ADD_CANDIDATE"
    assert by_code["9999"]["membership_intent"] == "EXCLUDE"
    assert len(payload["portfolio_members"]) == len(by_code)
    assert "duplicate_existing_candidate_reconciled:6758" in payload["reason_codes"]


def test_phase22_e_priority_is_deterministic_and_preserves_input_rank_score_order(tmp_path: Path) -> None:
    first = _produce(tmp_path / "first").payload
    second = _produce(tmp_path / "second").payload

    assert [row["security_code"] for row in first["portfolio_members"]] == [row["security_code"] for row in second["portfolio_members"]]
    new_members = [row for row in first["portfolio_members"] if not row["current_position"]]
    assert [row["security_code"] for row in new_members[:2]] == ["6098", "9999"]
    assert new_members[0]["input_opportunity_rank"] == 1
    assert new_members[0]["input_score"] == 0.92


def test_phase23_am_portfolio_construction_preserves_raw_opportunity_score_without_quality_alias(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "phase23_am_raw_score_authority").payload
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}
    member = by_code["6098"]

    assert member["input_score"] == 0.92
    assert member["runtime_opportunity_score"] == 0.92
    assert member["runtime_opportunity_score_authority"]["authority"] == "OPPORTUNITY_RANKING_AUTHORITY"
    assert member["runtime_opportunity_score_authority"]["canonical_field"] == "runtime_opportunity_score"
    assert member["runtime_opportunity_score_authority"]["prediction_semantics"] == "runtime_opportunity_score"
    assert "quality_score" not in member
    assert "quality_score_authority" not in member
    assert "allocation_quality_score" not in member
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase23_am_negative_runtime_opportunity_score_is_schema_valid_raw_signal(tmp_path: Path) -> None:
    opportunity = PortfolioConstructionSourceSummary(
        "PASS",
        "2026-07-15",
        "2026-07-15",
        "opportunity",
        "sha256:opportunity",
        tuple([{"opportunity_id": "opportunity-6098", "code": "6098", "opportunity_rank": 1, "expected_edge_score": -0.25}]),
        {},
    )
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=opportunity,
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_source_summary(tmp_path, "construction_policy_config"),
    )

    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "6098")
    assert member["runtime_opportunity_score"] == -0.25
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_ak_negative_uncalibrated_full_quality_reaches_target_member_competition(tmp_path: Path) -> None:
    payload = _build_l21t_ak_payload(
        tmp_path,
        opportunity_rows=[
            _l21t_ak_opportunity("6098", 1, -0.25, no_buy_reason="non_positive_expected_edge_score"),
        ],
        buy_quality_rows=[
            _l21t_ak_quality("6098", "FULL_ALLOCATION_ELIGIBLE"),
        ],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "6098")

    assert member["membership_intent"] == "ADD_CANDIDATE"
    assert member["target_membership"] is True
    assert member["requested_buy_new_weight"] > 0
    assert member["target_member_eligibility"]["status"] == "PASS"
    assert member["no_buy_reason_classification"]["hard_blocking_reasons"] == []
    assert "non_positive_expected_edge_score" in member["no_buy_reason_classification"]["soft_relative_reasons"]
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_ak_negative_uncalibrated_reduced_quality_reaches_target_member_competition(tmp_path: Path) -> None:
    payload = _build_l21t_ak_payload(
        tmp_path,
        opportunity_rows=[
            _l21t_ak_opportunity("6098", 1, -0.25, no_buy_reason="non_positive_expected_edge_score"),
        ],
        buy_quality_rows=[
            _l21t_ak_quality("6098", "REDUCED_ALLOCATION_ONLY", adjustment=0.5),
        ],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "6098")

    assert member["membership_intent"] == "ADD_CANDIDATE"
    assert member["target_membership"] is True
    assert member["requested_buy_new_weight"] > 0
    assert member["target_weight_resolution"]["adjustments"][0]["quality_action"] == "REDUCED_ALLOCATION_ONLY"
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_ak_positive_score_existing_behavior_preserved(tmp_path: Path) -> None:
    payload = _build_l21t_ak_payload(
        tmp_path,
        opportunity_rows=[_l21t_ak_opportunity("9432", 1, 0.25)],
        buy_quality_rows=[_l21t_ak_quality("9432", "FULL_ALLOCATION_ELIGIBLE")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "9432")

    assert member["membership_intent"] == "ADD_CANDIDATE"
    assert member["target_membership"] is True
    assert member["requested_buy_new_weight"] > 0
    assert member["no_buy_reason_classification"]["status"] == "PASS"
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_ak_high_downside_hard_block_preserved_with_combined_soft_reasons(tmp_path: Path) -> None:
    payload = _build_l21t_ak_payload(
        tmp_path,
        opportunity_rows=[
            _l21t_ak_opportunity(
                "3782",
                1,
                -0.25,
                no_buy_reason="below_opportunity_top20|high_downside_risk_score|non_positive_expected_edge_score",
            ),
        ],
        buy_quality_rows=[_l21t_ak_quality("3782", "FULL_ALLOCATION_ELIGIBLE")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "3782")

    assert member["membership_intent"] == "EXCLUDE"
    assert member["target_membership"] is False
    assert member["requested_buy_new_weight"] == 0
    assert member["no_buy_reason_classification"]["hard_blocking_reasons"] == ["high_downside_risk_score"]
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_ak_top20_uncalibrated_reason_is_soft_metadata(tmp_path: Path) -> None:
    payload = _build_l21t_ak_payload(
        tmp_path,
        opportunity_rows=[
            _l21t_ak_opportunity("6098", 25, -0.25, no_buy_reason="below_opportunity_top20"),
        ],
        buy_quality_rows=[_l21t_ak_quality("6098", "FULL_ALLOCATION_ELIGIBLE")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "6098")

    assert member["membership_intent"] == "ADD_CANDIDATE"
    assert member["target_membership"] is True
    assert member["requested_buy_new_weight"] > 0
    assert member["no_buy_reason_classification"]["hard_blocking_reasons"] == []
    assert member["no_buy_reason_classification"]["soft_relative_reasons"] == ["below_opportunity_top20"]
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase30_ai_high_quality_lower_rank_candidate_reaches_pc_competition(tmp_path: Path) -> None:
    si_path = _write_phase30_ai_strategy_intelligence(
        tmp_path,
        {
            "6098": "HIGH_QUALITY_CONTINUATION",
            "9432": "CAUTION_CONTINUATION",
        },
    )
    payload = _build_l21t_ak_payload(
        tmp_path,
        opportunity_rows=[
            _l21t_ak_opportunity("9432", 1, 0.40),
            _l21t_ak_opportunity("6098", 25, -0.25, no_buy_reason="below_opportunity_top20|non_positive_expected_edge_score"),
        ],
        buy_quality_rows=[
            _l21t_ak_quality("9432", "FULL_ALLOCATION_ELIGIBLE"),
            _l21t_ak_quality("6098", "FULL_ALLOCATION_ELIGIBLE"),
        ],
        target_position_count=1,
        strategy_intelligence_artifact_path=si_path,
    )
    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}

    assert by_code["6098"]["selection_quality_tier"] == "HIGH_QUALITY_CONTINUATION"
    assert by_code["6098"]["membership_intent"] == "ADD_CANDIDATE"
    assert by_code["6098"]["target_membership"] is True
    assert by_code["6098"]["requested_buy_new_weight"] > 0
    assert by_code["6098"]["no_buy_reason_classification"]["hard_blocking_reasons"] == []
    assert by_code["6098"]["selection_quality_score_only_hard_rejection_retired"] is True
    selected = _select_target_members(list(payload["portfolio_members"]))
    assert [row["security_code"] for row in selected[:2]] == ["6098", "9432"]
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_ak_buy_quality_reject_remains_zero_allocation(tmp_path: Path) -> None:
    payload = _build_l21t_ak_payload(
        tmp_path,
        opportunity_rows=[
            _l21t_ak_opportunity("6098", 1, -0.25, no_buy_reason="non_positive_expected_edge_score"),
        ],
        buy_quality_rows=[_l21t_ak_quality("6098", "REJECT")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "6098")

    assert member["membership_intent"] == "EXCLUDE"
    assert member["target_membership"] is False
    assert member["requested_buy_new_weight"] == 0
    assert member["target_weight_resolution"]["zero_weight_reason"] == "buy_quality_rejected"
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_ak_missing_semantic_metadata_fails_closed_for_non_positive_reason(tmp_path: Path) -> None:
    payload = _build_l21t_ak_payload(
        tmp_path,
        opportunity_rows=[
            {
                "opportunity_id": "opportunity-6098",
                "code": "6098",
                "opportunity_rank": 1,
                "runtime_opportunity_score": -0.25,
                "no_buy_reason": "non_positive_expected_edge_score",
            },
        ],
        opportunity_summary_metadata={},
        buy_quality_rows=[_l21t_ak_quality("6098", "FULL_ALLOCATION_ELIGIBLE")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "6098")

    assert member["membership_intent"] == "EXCLUDE"
    assert member["target_membership"] is False
    assert member["no_buy_reason_classification"]["status"] == "REVIEW_REQUIRED"
    assert "semantic_metadata_missing" in member["target_member_eligibility"]["reason"]
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_ak_calibrated_economic_negative_score_preserves_zero_gate(tmp_path: Path) -> None:
    payload = _build_l21t_ak_payload(
        tmp_path,
        opportunity_rows=[
            _l21t_ak_opportunity(
                "6098",
                1,
                -0.25,
                no_buy_reason="non_positive_expected_edge_score",
                score_semantic_role="calibrated_economic_expected_return",
                calibration_applied=True,
                economic_units_available=True,
            ),
        ],
        opportunity_summary_metadata={
            "canonical_score_field": "runtime_opportunity_score",
            "score_semantic_role": "calibrated_economic_expected_return",
            "calibration_applied": True,
            "economic_units_available": True,
        },
        buy_quality_rows=[_l21t_ak_quality("6098", "FULL_ALLOCATION_ELIGIBLE")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "6098")

    assert member["membership_intent"] == "EXCLUDE"
    assert member["target_membership"] is False
    assert member["requested_buy_new_weight"] == 0
    assert member["no_buy_reason_classification"]["hard_blocking_reasons"] == ["non_positive_expected_edge_score"]
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_ak_capital_competition_can_still_select_zero_without_forced_buy_count(tmp_path: Path) -> None:
    payload = _build_l21t_ak_payload(
        tmp_path,
        opportunity_rows=[
            _l21t_ak_opportunity("1001", 1, -0.10, no_buy_reason="non_positive_expected_edge_score"),
            _l21t_ak_opportunity("1002", 2, -0.20, no_buy_reason="non_positive_expected_edge_score"),
            _l21t_ak_opportunity("1003", 3, -0.30, no_buy_reason="non_positive_expected_edge_score"),
        ],
        buy_quality_rows=[
            _l21t_ak_quality("1001", "FULL_ALLOCATION_ELIGIBLE"),
            _l21t_ak_quality("1002", "FULL_ALLOCATION_ELIGIBLE"),
            _l21t_ak_quality("1003", "FULL_ALLOCATION_ELIGIBLE"),
        ],
        current_rows=[
            {"position_id": "current-7203", "security_code": "7203", "current_weight": 0.5},
        ],
        pm_rows=[
            {"position_id": "pm-7203", "security_code": "7203", "action": "HOLD", "intensity": "NONE", "confidence": 0.8, "uncertainty": "LOW", "reason_codes": ["HOLD_FIXTURE"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""},
        ],
    )
    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}

    assert by_code["1001"]["requested_buy_new_weight"] > 0
    assert by_code["1002"]["requested_buy_new_weight"] > 0
    assert by_code["1003"]["requested_buy_new_weight"] > 0
    assert by_code["1003"]["accepted_buy_new_weight"] == 0
    assert by_code["1003"]["target_weight_resolution"]["zero_weight_reason"] == "incremental_budget_zero_allocation"
    assert by_code["1003"]["membership_intent"] == "ADD_CANDIDATE"
    assert by_code["1003"]["target_member_eligibility"]["status"] == "PASS"
    assert payload["incremental_budget_reconciliation"]["trimmed_incremental_weight"] > 0
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_am_actual_adapter_propagates_top_level_opportunity_semantic_metadata(tmp_path: Path) -> None:
    opportunity_summary = _l21t_am_actual_adapter_opportunity_summary(
        tmp_path,
        [
            _l21t_am_opportunity_row("23700", 1, -0.09952183, no_buy_reason="non_positive_expected_edge_score"),
        ],
    )

    assert opportunity_summary.summary["canonical_score_field"] == "runtime_opportunity_score"
    assert opportunity_summary.summary["score_semantic_role"] == "uncalibrated_relative_model_score"
    assert opportunity_summary.summary["calibration_applied"] is False
    assert opportunity_summary.summary["economic_units_available"] is False


def test_phase29_l21t_am_actual_adapter_non_positive_uncalibrated_reason_is_soft(tmp_path: Path) -> None:
    payload = _build_l21t_am_payload_via_actual_adapter(
        tmp_path,
        opportunity_rows=[
            _l21t_am_opportunity_row("23700", 1, -0.09952183, no_buy_reason="non_positive_expected_edge_score"),
        ],
        buy_quality_rows=[_l21t_ak_quality("23700", "FULL_ALLOCATION_ELIGIBLE")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "23700")

    assert member["membership_intent"] == "ADD_CANDIDATE"
    assert member["target_member_eligibility"]["status"] == "PASS"
    assert member["no_buy_reason_classification"]["status"] == "PASS"
    assert member["no_buy_reason_classification"]["hard_blocking_reasons"] == []
    assert member["no_buy_reason_classification"]["soft_relative_reasons"] == ["non_positive_expected_edge_score"]
    assert member["no_buy_reason_classification"]["score_contract"]["semantic_metadata_complete"] is True
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_am_actual_adapter_top20_and_non_positive_are_soft(tmp_path: Path) -> None:
    payload = _build_l21t_am_payload_via_actual_adapter(
        tmp_path,
        opportunity_rows=[
            _l21t_am_opportunity_row(
                "36640",
                25,
                -0.1045757,
                no_buy_reason="below_opportunity_top20|non_positive_expected_edge_score",
            ),
        ],
        buy_quality_rows=[_l21t_ak_quality("36640", "FULL_ALLOCATION_ELIGIBLE")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "36640")

    assert member["membership_intent"] == "ADD_CANDIDATE"
    assert member["no_buy_reason_classification"]["hard_blocking_reasons"] == []
    assert member["no_buy_reason_classification"]["soft_relative_reasons"] == [
        "below_opportunity_top20",
        "non_positive_expected_edge_score",
    ]
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_am_actual_adapter_high_downside_hard_reason_preserved(tmp_path: Path) -> None:
    payload = _build_l21t_am_payload_via_actual_adapter(
        tmp_path,
        opportunity_rows=[
            _l21t_am_opportunity_row(
                "66590",
                1,
                -0.07228975,
                no_buy_reason="high_downside_risk_score|non_positive_expected_edge_score",
            ),
        ],
        buy_quality_rows=[_l21t_ak_quality("66590", "FULL_ALLOCATION_ELIGIBLE")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "66590")

    assert member["membership_intent"] == "EXCLUDE"
    assert member["target_member_eligibility"]["status"] == "BLOCKED"
    assert member["no_buy_reason_classification"]["hard_blocking_reasons"] == ["high_downside_risk_score"]
    assert member["no_buy_reason_classification"]["soft_relative_reasons"] == ["non_positive_expected_edge_score"]
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_am_actual_adapter_missing_metadata_remains_fail_closed(tmp_path: Path) -> None:
    payload = _build_l21t_am_payload_via_actual_adapter(
        tmp_path,
        opportunity_rows=[
            _l21t_am_opportunity_row("93180", 1, -0.09100653, no_buy_reason="non_positive_expected_edge_score"),
        ],
        opportunity_metadata={},
        buy_quality_rows=[_l21t_ak_quality("93180", "FULL_ALLOCATION_ELIGIBLE")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "93180")

    assert member["membership_intent"] == "EXCLUDE"
    assert member["no_buy_reason_classification"]["status"] == "REVIEW_REQUIRED"
    assert member["no_buy_reason_classification"]["review_reason"] == "semantic_metadata_missing"
    assert member["no_buy_reason_classification"]["score_contract"]["semantic_metadata_complete"] is False
    assert "canonical_score_field" in member["no_buy_reason_classification"]["score_contract"]["missing_fields"]
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_am_actual_adapter_malformed_metadata_remains_fail_closed(tmp_path: Path) -> None:
    payload = _build_l21t_am_payload_via_actual_adapter(
        tmp_path,
        opportunity_rows=[
            _l21t_am_opportunity_row(
                "23700",
                1,
                -0.09952183,
                no_buy_reason="non_positive_expected_edge_score",
                score_semantic_role="unknown_score_semantic_role",
            ),
        ],
        opportunity_metadata={
            "canonical_score_field": "runtime_opportunity_score",
            "score_semantic_role": "unknown_score_semantic_role",
            "calibration_applied": False,
            "economic_units_available": False,
        },
        buy_quality_rows=[_l21t_ak_quality("23700", "FULL_ALLOCATION_ELIGIBLE")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "23700")

    assert member["membership_intent"] == "EXCLUDE"
    assert member["no_buy_reason_classification"]["status"] == "REVIEW_REQUIRED"
    assert member["no_buy_reason_classification"]["review_reason"] == "unsupported_score_semantic_contract"
    assert member["no_buy_reason_classification"]["score_contract"]["semantic_metadata_complete"] is True
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_am_actual_adapter_calibrated_economic_negative_gate_preserved(tmp_path: Path) -> None:
    payload = _build_l21t_am_payload_via_actual_adapter(
        tmp_path,
        opportunity_rows=[
            _l21t_am_opportunity_row(
                "23700",
                1,
                -0.09952183,
                no_buy_reason="non_positive_expected_edge_score",
                score_semantic_role="calibrated_economic_expected_return",
                calibration_applied=True,
                economic_units_available=True,
            ),
        ],
        opportunity_metadata={
            "canonical_score_field": "runtime_opportunity_score",
            "score_semantic_role": "calibrated_economic_expected_return",
            "calibration_applied": True,
            "economic_units_available": True,
        },
        buy_quality_rows=[_l21t_ak_quality("23700", "FULL_ALLOCATION_ELIGIBLE")],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "23700")

    assert member["membership_intent"] == "EXCLUDE"
    assert member["no_buy_reason_classification"]["status"] == "BLOCKED"
    assert member["no_buy_reason_classification"]["hard_blocking_reasons"] == ["non_positive_expected_edge_score"]
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l21t_am_actual_adapter_positive_candidate_preserved(tmp_path: Path) -> None:
    payload = _build_l21t_am_payload_via_actual_adapter(
        tmp_path,
        opportunity_rows=[
            _l21t_am_opportunity_row("94320", 1, 0.16908343),
        ],
        buy_quality_rows=[_l21t_ak_quality("94320", "REDUCED_ALLOCATION_ONLY", adjustment=0.5)],
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "94320")

    assert member["membership_intent"] == "ADD_CANDIDATE"
    assert member["target_member_eligibility"]["status"] == "PASS"
    assert member["requested_buy_new_weight"] > 0
    assert member["target_weight_resolution"]["adjustments"][0]["quality_action"] == "REDUCED_ALLOCATION_ONLY"
    assert member["no_buy_reason_classification"]["status"] == "PASS"
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase23_ao_target_weight_authority_equal_weight_and_cap(tmp_path: Path) -> None:
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, rows=[], producer_status="PASS"),
        candidate_summary=_source_summary(
            tmp_path,
            "candidate",
            rows=[
                {"candidate_id": "candidate-6098", "code": "6098", "candidate_order": 1, "candidate_score": 0.9, "universe_eligible": True},
                {"candidate_id": "candidate-6758", "code": "6758", "candidate_order": 2, "candidate_score": 0.88, "universe_eligible": True},
                {"candidate_id": "candidate-8888", "code": "8888", "candidate_order": 3, "candidate_score": 0.86, "universe_eligible": True},
            ],
        ),
        opportunity_summary=_source_summary(
            tmp_path,
            "opportunity",
            rows=[
                {"opportunity_id": "opportunity-6098", "code": "6098", "opportunity_rank": 1, "expected_edge_score": 0.92},
                {"opportunity_id": "opportunity-6758", "code": "6758", "opportunity_rank": 2, "expected_edge_score": 0.86},
                {"opportunity_id": "opportunity-8888", "code": "8888", "opportunity_rank": 3, "expected_edge_score": 0.71},
            ],
        ),
        current_portfolio_summary=_source_summary(tmp_path, "current", rows=[]),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(tmp_path, target_position_count=3, exposure=0.9, cap=0.2),
    )

    assert payload["target_weight_method"]["opportunity_score_weight_transform_used"] is False
    assert payload["resolved_target_member_count"] == 3
    assert payload["total_target_weight"] == 0.6
    assert payload["total_target_weight"] <= payload["target_gross_exposure"]
    selected = [member for member in payload["portfolio_members"] if member["target_membership"]]
    assert len(selected) == 3
    assert all(member["target_weight"] == 0.2 for member in selected)
    assert all(member["target_weight_resolution"]["cap_applied"] is True for member in selected)
    assert all(member["target_weight_authority"]["method_id"] == "production_v1_equal_weight_target_allocation" for member in selected)
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase24_if_target_weight_sum_allows_six_decimal_rounding_tolerance(tmp_path: Path) -> None:
    policy_path = _write_resolved_portfolio_policy(tmp_path)
    policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
    policy_payload.update(
        {
            "target_position_count": 10,
            "target_gross_exposure_ratio": 0.79,
            "target_gross_exposure": 0.79,
            "cash_reserve_ratio": 0.21,
            "cash_reserve": 0.21,
        }
    )
    policy_payload["artifact_hash"] = portfolio_policy.portfolio_policy_hash(policy_payload)
    _write_json(policy_path, policy_payload)
    candidate_rows = [
        {
            "candidate_id": f"candidate-{code}",
            "code": code,
            "candidate_order": index,
            "candidate_score": 1.0 - index / 100,
            "universe_eligible": True,
        }
        for index, code in enumerate(("21340", "59550", "67310", "99840", "37820", "40520"), start=1)
    ]
    opportunity_rows = [
        {
            "opportunity_id": f"opportunity-{row['code']}",
            "code": row["code"],
            "opportunity_rank": index,
            "expected_edge_score": row["candidate_score"],
        }
        for index, row in enumerate(candidate_rows, start=1)
    ]

    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=policy_path,
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_source_summary(tmp_path, "candidate", rows=candidate_rows),
        opportunity_summary=_source_summary(tmp_path, "opportunity", rows=opportunity_rows),
        current_portfolio_summary=_source_summary(tmp_path, "current", rows=[]),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_artifact_summary(policy_path),
    )

    assert payload["producer_result_status"] != "BLOCK"
    assert payload["resolved_target_member_count"] == 6
    assert payload["total_target_weight"] == 0.790002
    assert payload["target_weight_sum_tolerance"] == 0.000003
    assert "total_target_weight_above_target_gross_exposure" not in payload["reason_codes"]


def test_phase23_as_aq_portfolio_policy_artifact_consumption_resolves_target_weight(tmp_path: Path) -> None:
    policy_path = _write_resolved_portfolio_policy(tmp_path)
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=policy_path,
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_artifact_summary(policy_path),
    )

    assert "target_weight_authority_unresolved" not in payload["reason_codes"]
    assert payload["portfolio_policy_allocation_authority"]["status"] == "PASS"
    selected = [member for member in payload["portfolio_members"] if member["target_membership"]]
    assert selected
    assert all(member["target_weight"] > 0 for member in selected)
    assert all(member["target_weight_authority"]["portfolio_policy_artifact_path"] == str(policy_path) for member in selected)
    assert all("dynamic_position_count_reference" not in member["target_weight_authority"] for member in selected)


def test_phase23_as_legacy_dynamic_artifacts_absent_do_not_block_policy_binding(tmp_path: Path) -> None:
    policy_path = _write_resolved_portfolio_policy(tmp_path)
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=policy_path,
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_artifact_summary(policy_path),
    )

    assert "target_weight_authority_unresolved" not in payload["reason_codes"]
    assert "target_weight_authority_unresolved" not in payload["reason_codes"]


def test_phase23_as_legacy_dynamic_artifacts_present_are_noncanonical(tmp_path: Path) -> None:
    policy_path = _write_resolved_portfolio_policy(tmp_path)
    summary = _policy_artifact_summary(policy_path)
    legacy_summary = dict(summary.summary or {})
    legacy_summary["dynamic_position_count_reference"] = "legacy-dpc.json"
    legacy_summary["dynamic_cash_exposure_reference"] = "legacy-dce.json"
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=policy_path,
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=PortfolioConstructionSourceSummary(summary.status, summary.business_date, summary.feature_date, summary.source_ref, summary.source_hash, summary.rows, legacy_summary),
    )

    selected = [member for member in payload["portfolio_members"] if member["target_membership"]]
    assert "target_weight_authority_unresolved" not in payload["reason_codes"]
    assert selected
    assert all("dynamic_position_count_reference" not in member["target_weight_authority"] for member in selected)


def test_phase23_as_valid_zero_position_count_is_not_review_required(tmp_path: Path) -> None:
    policy_path = _write_resolved_portfolio_policy(tmp_path)
    summary = _policy_artifact_summary(policy_path)
    zero_summary = {**dict(summary.summary or {}), "target_position_count": 0, "target_gross_exposure": 0.0, "target_gross_exposure_ratio": 0.0, "cash_reserve": 1.0, "cash_reserve_ratio": 1.0}
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=policy_path,
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=PortfolioConstructionSourceSummary(summary.status, summary.business_date, summary.feature_date, summary.source_ref, summary.source_hash, summary.rows, zero_summary),
    )

    assert "target_weight_authority_unresolved" not in payload["reason_codes"]
    assert payload["resolved_target_member_count"] == 0
    assert all(member["target_weight"] == 0 for member in payload["portfolio_members"])
    assert "target_weight_authority_unresolved" not in payload["reason_codes"]


def test_phase23_as_missing_single_name_weight_cap_fails_closed(tmp_path: Path) -> None:
    policy_path = _write_resolved_portfolio_policy(tmp_path)
    summary = _policy_artifact_summary(policy_path)
    missing = dict(summary.summary or {})
    missing["single_name_weight_cap"] = None
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=policy_path,
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=PortfolioConstructionSourceSummary(summary.status, summary.business_date, summary.feature_date, summary.source_ref, summary.source_hash, summary.rows, missing),
    )

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "target_weight_authority_unresolved" in payload["reason_codes"]
    assert "portfolio_policy_allocation_authority_missing:single_name_weight_cap" in payload["reason_codes"]


def test_phase23_as_ratio_absolute_conflict_fails_closed(tmp_path: Path) -> None:
    policy_path = _write_resolved_portfolio_policy(tmp_path)
    summary = _policy_artifact_summary(policy_path)
    conflict = {**dict(summary.summary or {}), "target_gross_exposure_ratio": 0.7, "target_gross_exposure": 0.8}
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=policy_path,
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=PortfolioConstructionSourceSummary(summary.status, summary.business_date, summary.feature_date, summary.source_ref, summary.source_hash, summary.rows, conflict),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert "portfolio_policy_allocation_authority_invalid:target_gross_exposure_ratio_conflict" in payload["reason_codes"]


def test_phase23_ao_negative_new_opportunity_is_not_forced_into_target_membership(tmp_path: Path) -> None:
    opportunity = PortfolioConstructionSourceSummary(
        "PASS",
        "2026-07-15",
        "2026-07-15",
        "opportunity",
        "sha256:opportunity",
        tuple([{"opportunity_id": "opportunity-6098", "code": "6098", "opportunity_rank": 1, "expected_edge_score": -0.25}]),
        {},
    )
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, rows=_pm_rows_without_sell_intents(), producer_status="PASS"),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=opportunity,
        current_portfolio_summary=_source_summary(tmp_path, "current", rows=_current_rows_without_sell_intents()),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(tmp_path, target_position_count=1, exposure=0.8, cap=0.25),
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "6098")

    assert member["runtime_opportunity_score"] == -0.25
    assert member["target_membership"] is False
    assert member["target_weight"] == 0.0
    assert member["weight_reason"] == "negative_opportunity_not_selected"
    assert member["target_weight_resolution"]["zero_weight_reason"] == "opportunity_not_selected"


def test_phase26_a_no_buy_reason_opportunity_is_excluded_without_target_count_slot_limit(tmp_path: Path) -> None:
    candidate = _source_summary(
        tmp_path,
        "candidate",
        rows=[
            {"candidate_id": "candidate-6098", "code": "6098", "candidate_order": 1, "candidate_score": 0.9, "universe_eligible": True},
            {"candidate_id": "candidate-43780", "code": "43780", "candidate_order": 2, "candidate_score": 0.88, "universe_eligible": True},
            {"candidate_id": "candidate-8888", "code": "8888", "candidate_order": 3, "candidate_score": 0.87, "universe_eligible": True},
        ],
    )
    opportunity = _source_summary(
        tmp_path,
        "opportunity",
        rows=[
            {"opportunity_id": "opportunity-6098", "code": "6098", "opportunity_rank": 1, "expected_edge_score": 0.30, "no_buy_reason": ""},
            {"opportunity_id": "opportunity-43780", "code": "43780", "opportunity_rank": 2, "expected_edge_score": 0.20, "no_buy_reason": "high_downside_risk_score"},
            {"opportunity_id": "opportunity-8888", "code": "8888", "opportunity_rank": 3, "expected_edge_score": 0.19, "no_buy_reason": ""},
        ],
    )
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, rows=_pm_rows_without_sell_intents(), producer_status="PASS"),
        candidate_summary=candidate,
        opportunity_summary=opportunity,
        current_portfolio_summary=_source_summary(tmp_path, "current", rows=_current_rows_without_sell_intents()),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(tmp_path, target_position_count=1, exposure=0.8, cap=0.2),
    )
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert by_code["43780"]["membership_intent"] == "EXCLUDE"
    assert by_code["43780"]["target_membership"] is False
    assert by_code["43780"]["target_weight"] == 0.0
    assert "opportunity_no_buy_reason_present:high_downside_risk_score" in by_code["43780"]["reason_codes"]
    assert by_code["8888"]["target_membership"] is True
    assert by_code["8888"]["target_weight"] > 0
    assert by_code["8888"]["target_weight_authority"]["target_position_count_decision_authority"] == "DEPRECATED_METADATA_ONLY"


def test_phase28_d49_unsupported_buy_new_is_excluded_without_blocking_lower_eligible_candidate(tmp_path: Path) -> None:
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, rows=[], producer_status="PASS"),
        candidate_summary=_source_summary(
            tmp_path,
            "candidate",
            rows=[
                {"candidate_id": "candidate-93990", "code": "93990", "candidate_order": 1, "candidate_score": 0.95, "universe_eligible": True, "listed_info": _broker_fixture_listed_info("93990", "021")},
                {"candidate_id": "candidate-6098", "code": "6098", "candidate_order": 2, "candidate_score": 0.80, "universe_eligible": True, "listed_info": _broker_fixture_listed_info("6098", "011")},
            ],
        ),
        opportunity_summary=_source_summary(
            tmp_path,
            "opportunity",
            rows=[
                {"opportunity_id": "opportunity-93990", "code": "93990", "opportunity_rank": 1, "expected_edge_score": 0.95, "listed_info": _broker_fixture_listed_info("93990", "021")},
                {"opportunity_id": "opportunity-6098", "code": "6098", "opportunity_rank": 2, "expected_edge_score": 0.80, "listed_info": _broker_fixture_listed_info("6098", "011")},
            ],
        ),
        current_portfolio_summary=_source_summary(tmp_path, "current", rows=[]),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(tmp_path, target_position_count=1, exposure=0.5, cap=0.5),
    )
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert payload["broker_eligibility_gating_owner"] == "PORTFOLIO_CONSTRUCTION"
    assert by_code["93990"]["input_opportunity_rank"] == 1
    assert by_code["93990"]["runtime_opportunity_score"] == 0.95
    assert by_code["93990"]["membership_intent"] == "EXCLUDE"
    assert by_code["93990"]["target_membership"] is False
    assert by_code["93990"]["target_weight"] == 0.0
    assert by_code["93990"]["broker_eligibility"]["broker_security_type"] == "UNSUPPORTED_FOREIGN_LISTED_STOCK"
    assert "BROKER_PRODUCT_CATEGORY_UNSUPPORTED" in by_code["93990"]["reason_codes"]
    assert by_code["6098"]["membership_intent"] == "ADD_CANDIDATE"
    assert by_code["6098"]["target_membership"] is True
    assert by_code["6098"]["target_weight"] > 0
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase28_d51_candidate_flat_listed_info_metadata_reaches_broker_eligibility(tmp_path: Path) -> None:
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, rows=[], producer_status="PASS"),
        candidate_summary=_source_summary(
            tmp_path,
            "candidate",
            rows=[
                {
                    "candidate_id": "candidate-93990",
                    "code": "93990",
                    "candidate_order": 1,
                    "candidate_score": 0.95,
                    "universe_eligible": True,
                    "market_name": "スタンダード",
                    "product_category": "021",
                    "security_type": "021",
                    "is_current_listed": True,
                },
                {
                    "candidate_id": "candidate-6098",
                    "code": "6098",
                    "candidate_order": 2,
                    "candidate_score": 0.80,
                    "universe_eligible": True,
                    "market_name": "プライム",
                    "product_category": "011",
                    "security_type": "011",
                    "is_current_listed": True,
                },
            ],
        ),
        opportunity_summary=_source_summary(
            tmp_path,
            "opportunity",
            rows=[
                {"opportunity_id": "opportunity-93990", "code": "93990", "opportunity_rank": 1, "expected_edge_score": 0.95},
                {"opportunity_id": "opportunity-6098", "code": "6098", "opportunity_rank": 2, "expected_edge_score": 0.80},
            ],
        ),
        current_portfolio_summary=_source_summary(tmp_path, "current", rows=[]),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(tmp_path, target_position_count=1, exposure=0.5, cap=0.5),
    )
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert by_code["93990"]["broker_listed_info"] == {
        "code": "93990",
        "current_listed": True,
        "market": "スタンダード",
        "product_category": "021",
        "security_type": "021",
    }
    assert by_code["93990"]["broker_eligibility"]["broker_security_type"] == "UNSUPPORTED_FOREIGN_LISTED_STOCK"
    assert by_code["93990"]["membership_intent"] == "EXCLUDE"
    assert by_code["93990"]["target_membership"] is False
    assert by_code["93990"]["target_weight"] == 0.0
    assert by_code["6098"]["target_membership"] is True
    assert by_code["6098"]["target_weight"] > 0
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase28_d49_unknown_category_fails_closed_and_zero_eligible_buy_day_is_valid(tmp_path: Path) -> None:
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, rows=[], producer_status="PASS"),
        candidate_summary=_source_summary(
            tmp_path,
            "candidate",
            rows=[{"candidate_id": "candidate-99990", "code": "99990", "candidate_order": 1, "candidate_score": 0.90, "universe_eligible": True, "listed_info": _broker_fixture_listed_info("99990", "999")}],
        ),
        opportunity_summary=_source_summary(
            tmp_path,
            "opportunity",
            rows=[{"opportunity_id": "opportunity-99990", "code": "99990", "opportunity_rank": 1, "expected_edge_score": 0.90, "listed_info": _broker_fixture_listed_info("99990", "999")}],
        ),
        current_portfolio_summary=_source_summary(tmp_path, "current", rows=[]),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(tmp_path, target_position_count=1, exposure=0.5, cap=0.5),
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "99990")

    assert payload["producer_result_status"] != "BLOCK"
    assert payload["total_target_weight"] == 0.0
    assert member["membership_intent"] == "EXCLUDE"
    assert member["broker_eligibility"]["status"] == "FAIL_CLOSED"
    assert member["broker_eligibility"]["reason"] == "BROKER_PRODUCT_CATEGORY_UNKNOWN"
    assert "BROKER_PRODUCT_CATEGORY_UNKNOWN" in member["reason_codes"]
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase28_d49_existing_unsupported_position_stays_visible_but_buy_add_is_blocked(tmp_path: Path) -> None:
    def build(action: str) -> dict[str, object]:
        workdir = tmp_path / action.lower()
        workdir.mkdir(parents=True, exist_ok=True)
        opportunity_rows = [
            _eligible_add_opportunity("93990", 1, 0.80) | {"listed_info": _broker_fixture_listed_info("93990", "021")}
        ]
        return _build_d28_payload(
            workdir,
            current_rows=[{"position_id": "current-93990", "security_code": "93990", "current_weight": 0.10, "listed_info": _broker_fixture_listed_info("93990", "021")}],
            pm_rows=[_pm_row("93990", action)],
            opportunity_rows=opportunity_rows if action == "ADD" else [],
            exposure=0.5,
            cap=0.5,
        )

    hold = next(row for row in build("HOLD")["portfolio_members"] if row["security_code"] == "93990")
    reduce = next(row for row in build("REDUCE")["portfolio_members"] if row["security_code"] == "93990")
    exit_member = next(row for row in build("EXIT")["portfolio_members"] if row["security_code"] == "93990")
    add = next(row for row in build("ADD")["portfolio_members"] if row["security_code"] == "93990")

    assert hold["current_position"] is True
    assert hold["membership_intent"] == "RETAIN"
    assert "broker_eligibility_existing_position_visibility_preserved" in hold["reason_codes"]
    assert reduce["membership_intent"] == "REDUCE_CANDIDATE"
    assert exit_member["membership_intent"] == "REMOVE_CANDIDATE"
    assert add["pm_action"] == "ADD"
    assert add["weight_intent"] == "MAINTAIN"
    assert add["target_weight"] == add["current_weight"]
    assert add["add_allocation_eligibility_status"] == "FAIL_CLOSED"
    assert "broker_eligibility_buy_add_excluded_existing_position_visible" in add["target_weight_reason_codes"]


def test_phase22_e_date_pit_blocks_cross_date_and_future_snapshot(tmp_path: Path) -> None:
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path, business_date="2026-07-14"),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path, feature_date="2026-07-16"),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_source_summary(tmp_path, "construction_policy_config"),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert "candidate_date_mismatch" in payload["reason_codes"]
    assert "current_portfolio_date_mismatch" in payload["reason_codes"]
    assert "future_feature_or_snapshot_date_detected" in payload["reason_codes"]
    assert payload["temporal_safety"]["implicit_latest_fallback_used"] is False


def test_phase22_e_hash_lineage_and_artifact_hash_validation(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert verify_source_hashes(result.payload)["status"] == "PASS"
    assert result.payload["artifact_hash"] == portfolio_construction_hash(result.payload)
    changed = json.loads(json.dumps(result.payload))
    changed["source_hashes"][0]["sha256"] = "deadbeef"
    assert verify_source_hashes(changed)["status"] == "BLOCK"
    changed = json.loads(json.dumps(result.payload))
    changed["portfolio_members"][0]["membership_intent"] = "REMOVE_CANDIDATE"
    assert changed["artifact_hash"] != portfolio_construction_hash(changed)


def test_phase22_e_bootstrap_missing_inputs_does_not_emit_empty_pass_or_all_retain(tmp_path: Path) -> None:
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=None,
        corporate_event_artifact_path=None,
        portfolio_policy_artifact_path=None,
        position_management_artifact_path=None,
        candidate_summary=_source_summary(tmp_path, "candidate", status="REVIEW_REQUIRED", rows=[]),
        opportunity_summary=_source_summary(tmp_path, "opportunity", status="REVIEW_REQUIRED", rows=[]),
        current_portfolio_summary=_source_summary(tmp_path, "current", status="REVIEW_REQUIRED", rows=[]),
        pending_summary=None,
        policy_config_summary=_source_summary(tmp_path, "construction_policy_config", status="REVIEW_REQUIRED"),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert payload["portfolio_members"] == []
    assert payload["temporal_safety"]["previous_day_portfolio_construction_copied"] is False
    assert "upstream_block:SOURCE_MISSING" in payload["reason_codes"]


def test_phase22_e_behavior_and_capital_deployment_authority_preserved(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload

    assert payload["position_count_decided"] is False
    assert payload["cash_ratio_decided"] is False
    assert payload["exposure_decided"] is False
    assert payload["allocation_decided"] is False
    assert payload["quantity_decided"] is False
    assert payload["production_consumer_connected"] is False
    assert payload["runtime_switch_performed"] is False
    assert payload["legacy_authority_active"] is True
    assert payload["capital_competition"]["authority"]["owner"] == "PORTFOLIO_CONSTRUCTION"
    assert payload["capital_competition"]["competitor_types"] == ["NEW_BUY", "ADD", "CASH"]
    assert payload["capital_competition"]["authority"]["add_automatic_priority"] is False
    assert payload["capital_competition"]["authority"]["new_buy_automatic_priority"] is False
    assert payload["cash_competitor"]["competitor_type"] == "CASH"
    assert payload["cash_competitor"]["cash_is_valid_allocation"] is True
    assert payload["final_no_deployable_opportunity_authority"]["owner"] == "PORTFOLIO_CONSTRUCTION"
    assert payload["final_no_deployable_opportunity_authority"]["downstream_reclassification_allowed"] is False
    assert payload["capital_competition"]["constraint_decision_model"]["position_sizing_decides_next_competitor"] is False
    assert payload["capital_competition"]["residual_reconsideration"]["position_sizing_quantity_authority_duplicated"] is False
    assert payload["capital_competition"]["authority"]["risk_pacing_authoritative"] is True
    assert payload["capital_competition"]["authority"]["historical_outcome_used_for_competition"] is False


def test_phase31_g24_capital_competition_framework_selects_new_buy_and_keeps_cash_valid() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[_lot_rebatch_member("11110", priority=1, request=0.10, accepted=0.10)],
        lot_feasibility_rows=[{"symbol": "11110", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08}],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
    )
    competition = result["evidence"]["capital_competition"]

    assert competition["authority"]["owner"] == "PORTFOLIO_CONSTRUCTION"
    assert competition["competitor_types"] == ["NEW_BUY", "ADD", "CASH"]
    assert competition["cash_competitor"]["status"] == "COMPETITOR_SELECTED"
    assert competition["cash_competitor"]["cash_is_valid_allocation"] is True
    assert competition["authority"]["new_buy_automatic_priority"] is False
    assert competition["authority"]["add_automatic_priority"] is False
    assert [item["competitor_type"] for item in competition["competitors"]] == ["NEW_BUY"]
    assert competition["competitors"][0]["status"] == "COMPETITOR_SELECTED"
    assert competition["final_no_deployable_opportunity"] is False


def test_phase31_g24_reconsiderable_lot_failure_can_fund_next_competitor_without_duplicates() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _lot_rebatch_member("11110", priority=1, request=0.18, accepted=0.18),
            _lot_rebatch_member("22220", priority=2, request=0.08, accepted=0.0),
        ],
        lot_feasibility_rows=[
            {"symbol": "11110", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.30},
            {"symbol": "22220", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
    )
    competition = result["evidence"]["capital_competition"]
    by_symbol = {item["symbol"]: item for item in competition["competitors"]}

    assert by_symbol["11110"]["status"] == "COMPETITOR_REJECTED_RECONSIDERABLE"
    assert by_symbol["11110"]["constraint_rejection_class"] == "RECONSIDERABLE"
    assert set(by_symbol["11110"]["reason_codes"]) & {"LOT_RESIDUAL", "CONCENTRATION_BLOCK"}
    assert by_symbol["22220"]["status"] == "COMPETITOR_SELECTED"
    assert competition["residual_reconsideration"]["implemented"] is True
    assert competition["residual_reconsideration"]["finite"] is True
    assert competition["residual_reconsideration"]["duplicate_symbol_order_risk"] is False
    assert len({(item["competitor_type"], item["symbol"]) for item in competition["competitors"]}) == len(competition["competitors"])


def test_phase31_g24_safety_hard_block_is_terminal_and_no_valid_competitor_is_pc_owned() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[_lot_rebatch_member("78780", priority=1, request=0.18, accepted=0.18)],
        lot_feasibility_rows=[
            {
                "symbol": "78780",
                "lot_feasible": False,
                "broker_eligible": True,
                "minimum_executable_weight": 0.30,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX",
                    "safety_hard_cap_preserved": False,
                },
            }
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.18,
    )
    competition = result["evidence"]["capital_competition"]
    competitor = competition["competitors"][0]

    assert competitor["status"] == "COMPETITOR_REJECTED_TERMINAL"
    assert competitor["constraint_rejection_class"] == "TERMINAL"
    assert "VALID_SAFETY_RESERVE" in competitor["reason_codes"]
    assert competition["final_no_deployable_opportunity"] is True
    assert competition["final_no_deployable_opportunity_authority"]["owner"] == "PORTFOLIO_CONSTRUCTION"
    assert competition["final_no_deployable_opportunity_authority"]["decision"] == "NO_DEPLOYABLE_OPPORTUNITY"


def test_phase31_g25_pc_consumes_canonical_sizing_evidence_for_reconsideration() -> None:
    sizing_lot_infeasible = {
        "schema_version": "position_sizing.canonical_lot_residual_evidence.v1",
        "symbol": "11110",
        "intent_type": "NEW_BUY",
        "evidence_class": "LOT_INFEASIBLE",
        "terminality": "RECONSIDERABLE",
        "requested_notional": 180_000.0,
        "executable_quantity": 0,
        "executable_notional": 0.0,
        "lot_size": 100,
        "residual_capital": 180_000.0,
        "residual_capital_classification": "REALLOCATABLE_RESIDUAL",
        "constraint_reason_codes": ["LOT_INFEASIBLE"],
        "quantity_authority_owner": "POSITION_SIZING",
        "pc_reconsideration_owner": "PORTFOLIO_CONSTRUCTION",
    }
    result = apply_lot_aware_final_reallocation(
        members=[
            _lot_rebatch_member("11110", priority=1, request=0.18, accepted=0.18),
            _lot_rebatch_member("22220", priority=2, request=0.08, accepted=0.0),
        ],
        lot_feasibility_rows=[
            {
                "symbol": "11110",
                "lot_feasible": False,
                "broker_eligible": True,
                "minimum_executable_weight": 0.30,
                "canonical_sizing_evidence": sizing_lot_infeasible,
            },
            {"symbol": "22220", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
    )
    competition = result["evidence"]["capital_competition"]
    by_symbol = {item["symbol"]: item for item in competition["competitors"]}

    assert by_symbol["11110"]["status"] == "COMPETITOR_REJECTED_RECONSIDERABLE"
    assert by_symbol["11110"]["constraint_evidence"]["canonical_sizing_evidence"]["evidence_class"] == "LOT_INFEASIBLE"
    assert "LOT_RESIDUAL" in by_symbol["11110"]["reason_codes"]
    assert by_symbol["22220"]["status"] == "COMPETITOR_SELECTED"
    assert competition["residual_reconsideration"]["cash_double_use_risk"] is False
    assert competition["residual_reconsideration"]["duplicate_competitor_count"] == 0


def test_phase31_g24_add_framework_does_not_auto_win_or_change_add_semantics() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _lot_rebatch_member("11110", priority=1, request=0.10, accepted=0.0),
            _lot_rebatch_add_member("22220", priority=2, current_weight=0.05, request=0.10, accepted=0.0),
        ],
        lot_feasibility_rows=[
            {"symbol": "11110", "intent_type": "BUY_NEW", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
            {"symbol": "22220", "intent_type": "BUY_ADD", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
    )
    by_code = {row["security_code"]: row for row in result["members"]}
    competition = result["evidence"]["capital_competition"]
    by_competitor = {(item["competitor_type"], item["symbol"]): item for item in competition["competitors"]}

    assert by_code["11110"]["lot_aware_accepted_buy_new_weight"] == 0.10
    assert by_code["22220"]["lot_aware_accepted_incremental_weight"] == 0.0
    assert by_competitor[("NEW_BUY", "11110")]["status"] == "COMPETITOR_SELECTED"
    assert by_competitor[("ADD", "22220")]["status"] == "COMPETITOR_REJECTED_RECONSIDERABLE"
    assert competition["authority"]["add_automatic_priority"] is False


def test_phase31_g27_add_competitor_can_win_and_preserves_sizing_quantity_owner() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _lot_rebatch_add_member("22220", priority=1, current_weight=0.05, request=0.08, accepted=0.08),
            _lot_rebatch_member("11110", priority=2, request=0.08, accepted=0.08),
        ],
        lot_feasibility_rows=[
            {"symbol": "22220", "intent_type": "BUY_ADD", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
            {"symbol": "11110", "intent_type": "BUY_NEW", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
        ],
        target_gross_exposure=0.13,
        single_name_cap=0.20,
    )
    competition = result["evidence"]["capital_competition"]
    by_competitor = {(item["competitor_type"], item["symbol"]): item for item in competition["competitors"]}
    add = by_competitor[("ADD", "22220")]

    assert competition["authority"]["pm_add_intent_owner"] == "POSITION_MANAGEMENT"
    assert competition["authority"]["add_capital_competition_owner"] == "PORTFOLIO_CONSTRUCTION"
    assert competition["authority"]["add_discrete_quantity_owner"] == "POSITION_SIZING"
    assert add["status"] == "COMPETITOR_SELECTED"
    assert add["canonical_add_competitor"]["eligibility_state"] == "PASS"
    assert add["canonical_add_competitor"]["source_pm_intent"]["owner"] == "POSITION_MANAGEMENT"
    assert add["canonical_add_competitor"]["constraint_evidence"]["position_sizing_quantity_owner"] == "POSITION_SIZING"
    assert add["canonical_add_competitor"]["constraint_evidence"]["pc_calculates_authoritative_quantity"] is False
    assert "ADD_SELECTED" in add["reason_codes"]
    assert by_competitor[("NEW_BUY", "11110")]["status"] == "COMPETITOR_REJECTED_RECONSIDERABLE"


def test_phase31_g27_stronger_new_buy_beats_add_without_auto_add_priority() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _lot_rebatch_member("11110", priority=1, request=0.08, accepted=0.08),
            _lot_rebatch_add_member("22220", priority=2, current_weight=0.05, request=0.08, accepted=0.08),
        ],
        lot_feasibility_rows=[
            {"symbol": "11110", "intent_type": "BUY_NEW", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
            {"symbol": "22220", "intent_type": "BUY_ADD", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
        ],
        target_gross_exposure=0.13,
        single_name_cap=0.20,
    )
    by_competitor = {
        (item["competitor_type"], item["symbol"]): item
        for item in result["evidence"]["capital_competition"]["competitors"]
    }

    assert by_competitor[("NEW_BUY", "11110")]["status"] == "COMPETITOR_SELECTED"
    assert by_competitor[("ADD", "22220")]["status"] == "COMPETITOR_REJECTED_RECONSIDERABLE"
    assert "ADD_LOST_TO_NEW_BUY" in by_competitor[("ADD", "22220")]["reason_codes"]
    assert result["evidence"]["capital_competition"]["authority"]["add_automatic_priority"] is False


def test_phase31_g27_cash_can_beat_weak_add_and_weak_new_buy() -> None:
    add_member = _lot_rebatch_add_member("22220", priority=1, current_weight=0.05, request=0.08, accepted=0.08)
    add_member["add_allocation_eligibility_status"] = "FAIL_CLOSED"
    add_member["incremental_investment_value_state"] = "NEGATIVE"
    add_member["target_weight"] = 0.13
    new_member = _lot_rebatch_member("11110", priority=2, request=0.08, accepted=0.08)
    result = apply_lot_aware_final_reallocation(
        members=[add_member, new_member],
        lot_feasibility_rows=[
            {"symbol": "22220", "intent_type": "BUY_ADD", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
            {"symbol": "11110", "intent_type": "BUY_NEW", "lot_feasible": False, "broker_eligible": False, "minimum_executable_weight": 0.08},
        ],
        target_gross_exposure=0.21,
        single_name_cap=0.20,
    )
    competition = result["evidence"]["capital_competition"]
    by_competitor = {(item["competitor_type"], item["symbol"]): item for item in competition["competitors"]}

    assert by_competitor[("ADD", "22220")]["canonical_add_competitor"]["eligibility_state"] == "FAIL_CLOSED"
    assert "ADD_LOST_TO_CASH" in by_competitor[("ADD", "22220")]["reason_codes"]
    assert competition["cash_competitor"]["cash_is_valid_allocation"] is True
    assert competition["cash_competitor"]["status"] == "COMPETITOR_SELECTED"


def test_phase31_g27_add_strategy_safety_lot_and_zero_delta_reasons_are_canonical() -> None:
    strategy = apply_lot_aware_final_reallocation(
        members=[_lot_rebatch_add_member("22220", priority=1, current_weight=0.18, request=0.08, accepted=0.08)],
        lot_feasibility_rows=[{"symbol": "22220", "intent_type": "BUY_ADD", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08}],
        target_gross_exposure=0.40,
        single_name_cap=0.20,
    )
    safety = apply_lot_aware_final_reallocation(
        members=[_lot_rebatch_add_member("33330", priority=1, current_weight=0.05, request=0.08, accepted=0.08)],
        lot_feasibility_rows=[
            {
                "symbol": "33330",
                "intent_type": "BUY_ADD",
                "lot_feasible": False,
                "broker_eligible": True,
                "minimum_executable_weight": 0.30,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX",
                    "safety_hard_cap_preserved": False,
                },
            }
        ],
        target_gross_exposure=0.40,
        single_name_cap=0.20,
    )
    zero = build_capital_competition_framework(
        members=[_lot_rebatch_add_member("44440", priority=1, current_weight=0.05, request=0.0, accepted=0.0)],
        target_gross_exposure=0.40,
        total_target_weight=0.05,
        business_date="2026-07-15",
    )

    strategy_add = next(item for item in strategy["evidence"]["capital_competition"]["competitors"] if item["competitor_type"] == "ADD")
    safety_add = next(item for item in safety["evidence"]["capital_competition"]["competitors"] if item["competitor_type"] == "ADD")
    zero_add = next(item for item in zero["competitors"] if item["competitor_type"] == "ADD")

    assert "ADD_STRATEGY_CAP_BOUND" in strategy_add["canonical_add_competitor"]["reason_codes"]
    assert "ADD_SAFETY_CAP_BOUND" in safety_add["canonical_add_competitor"]["reason_codes"]
    assert "ADD_NO_POSITIVE_DELTA" in zero_add["canonical_add_competitor"]["reason_codes"]


def test_phase31_g28_framework_consumes_authoritative_risk_pacing_without_quantity_authority(tmp_path: Path) -> None:
    (tmp_path / "with").mkdir()
    (tmp_path / "without").mkdir()
    with_shadow, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path / "with"),
        corporate_event_artifact_path=_write_corporate_event(tmp_path / "with"),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path / "with"),
        position_management_artifact_path=_write_position_management(tmp_path / "with"),
        candidate_summary=_candidate_summary(tmp_path / "with"),
        opportunity_summary=_opportunity_summary(tmp_path / "with"),
        current_portfolio_summary=_current_summary(tmp_path / "with"),
        pending_summary=_source_summary(tmp_path / "with", "pending", rows=[]),
        policy_config_summary=_policy_config_summary(tmp_path / "with", target_position_count=3, exposure=0.7, cap=0.25, risk_pacing_intent="NORMAL_DEPLOYMENT"),
    )
    without_shadow, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path / "without"),
        corporate_event_artifact_path=_write_corporate_event(tmp_path / "without"),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path / "without"),
        position_management_artifact_path=_write_position_management(tmp_path / "without"),
        candidate_summary=_candidate_summary(tmp_path / "without"),
        opportunity_summary=_opportunity_summary(tmp_path / "without"),
        current_portfolio_summary=_current_summary(tmp_path / "without"),
        pending_summary=_source_summary(tmp_path / "without", "pending", rows=[]),
        policy_config_summary=_policy_config_summary(tmp_path / "without", target_position_count=3, exposure=0.7, cap=0.25),
    )

    assert [(m["security_code"], m["target_weight"]) for m in with_shadow["portfolio_members"]] == [
        (m["security_code"], m["target_weight"]) for m in without_shadow["portfolio_members"]
    ]
    assert with_shadow["capital_competition"]["authority"]["risk_pacing_authoritative"] is True
    assert with_shadow["capital_competition"]["authority"]["risk_pacing_owner"] == "PORTFOLIO_POLICY"
    assert with_shadow["capital_competition"]["authority"]["risk_pacing_authoritative_consumer"] == "PORTFOLIO_CONSTRUCTION"
    assert with_shadow["capital_competition"]["risk_pacing_evidence"]["mode"] == "AUTHORITATIVE"
    assert validate_portfolio_construction_artifact(with_shadow)["status"] == "PASS"


def test_phase31_g28_risk_pacing_competition_matrix_preserves_cash_and_strong_deployment(tmp_path: Path) -> None:
    normal = _build_l16_payload(
        tmp_path / "normal",
        opportunity_rows=[_l16_opportunity("11110", 1, price=1000.0, rolling_value=1_000_000_000)],
        buy_quality_rows=[_l16_quality("11110", "FULL_ALLOCATION_ELIGIBLE")],
        exposure=0.18,
        cap=0.18,
        portfolio_equity=1_000_000,
        risk_pacing_intent="NORMAL_DEPLOYMENT",
    )
    cautious = _build_l16_payload(
        tmp_path / "cautious",
        opportunity_rows=[_l16_opportunity("22220", 1, price=1000.0, rolling_value=1_000_000_000)],
        buy_quality_rows=[_l16_quality("22220", "FULL_ALLOCATION_ELIGIBLE")],
        exposure=0.18,
        cap=0.18,
        portfolio_equity=1_000_000,
        risk_pacing_intent="CAUTIOUS_DEPLOYMENT",
    )
    preserve = _build_l16_payload(
        tmp_path / "preserve",
        opportunity_rows=[_l16_opportunity("33330", 1, price=1000.0, rolling_value=1_000_000_000)],
        exposure=0.18,
        cap=0.18,
        portfolio_equity=1_000_000,
        risk_pacing_intent="PRESERVE_OPTIONALITY",
    )

    assert normal["portfolio_members"][0]["target_weight"] == 0.18
    assert cautious["portfolio_members"][0]["target_weight"] == 0.18
    assert cautious["portfolio_members"][0]["risk_pacing_competition_decision"]["blocks_deployment"] is False
    assert preserve["portfolio_members"][0]["target_weight"] == 0.18
    assert preserve["portfolio_members"][0]["risk_pacing_competition_decision"]["compatibility_evidence_only"] is True
    assert preserve["portfolio_members"][0]["risk_pacing_competition_decision"]["late_decision_authority_active"] is False
    assert preserve["cash_competitor"]["cash_is_valid_allocation"] is True
    assert "RISK_PACING_OPTIONALITY_WEAK_COMPETITOR_TO_CASH" in preserve["portfolio_members"][0]["risk_pacing_competition_decision"]["reason_codes"]
    assert preserve["capital_competition"]["authority"]["legacy_late_risk_pacing_decision_authority_count"] == 0


def test_phase28_c_canonical_add_bridge_increases_existing_target_weight_when_incremental_evidence_passes(tmp_path: Path) -> None:
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_source_summary(
            tmp_path,
            "candidate",
            rows=[
                {"candidate_id": "candidate-6758", "code": "6758", "candidate_order": 1, "candidate_score": 0.88, "universe_eligible": True},
                {"candidate_id": "candidate-6098", "code": "6098", "candidate_order": 2, "candidate_score": 0.70, "universe_eligible": True},
            ],
        ),
        opportunity_summary=_source_summary(
            tmp_path,
            "opportunity",
            rows=[
                {
                    "opportunity_id": "opportunity-6758",
                    "code": "6758",
                    "opportunity_rank": 1,
                    "expected_edge_score": 0.86,
                    "expected_edge_baseline_score": 0.72,
                    "expected_edge_baseline_business_date": "2026-07-14",
                    "incremental_investment_value_state": "POSITIVE",
                    "opportunity_cost_status": "PASS",
                    "campaign_continuation_status": "PASS",
                    "no_loss_averaging_status": "PASS",
                },
                {"opportunity_id": "opportunity-6098", "code": "6098", "opportunity_rank": 2, "expected_edge_score": 0.70},
            ],
        ),
        current_portfolio_summary=_source_summary(
            tmp_path,
            "current",
            rows=[
                {"position_id": "current-7203", "security_code": "7203", "current_weight": 0.10},
                {"position_id": "current-6758", "security_code": "6758", "current_weight": 0.05},
            ],
        ),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(tmp_path, target_position_count=3, exposure=0.6, cap=0.2),
    )

    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "6758")
    assert member["pm_action"] == "ADD"
    assert member["target_weight"] == 0.2
    assert member["post_add_target_weight"] == 0.2
    assert member["target_weight_change"] == 0.15
    assert member["add_allocation_eligibility_status"] == "PASS"
    assert member["expected_edge_improvement_state"] == "IMPROVING"
    assert member["incremental_investment_value_state"] == "POSITIVE"
    assert "ADD_TARGET_WEIGHT_INCREASED" in member["target_weight_reason_codes"]
    assert member["target_weight_resolution"]["add_allocation_bridge"]["status"] == "PASS"
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase28_c_canonical_add_bridge_fails_closed_when_expected_edge_evidence_missing(tmp_path: Path) -> None:
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_source_summary(
            tmp_path,
            "current",
            rows=[
                {"position_id": "current-7203", "security_code": "7203", "current_weight": 0.10},
                {"position_id": "current-6758", "security_code": "6758", "current_weight": 0.05},
                {"position_id": "current-9984", "security_code": "9984", "current_weight": 0.10},
                {"position_id": "current-8306", "security_code": "8306", "current_weight": 0.10},
            ],
        ),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(tmp_path, target_position_count=3, exposure=0.6, cap=0.2),
    )

    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "6758")
    assert member["target_weight"] == 0.05
    assert member["post_add_target_weight"] == 0.05
    assert member["target_weight_change"] == 0.0
    assert member["add_allocation_eligibility_status"] == "FAIL_CLOSED"
    assert member["expected_edge_improvement_state"] == "UNKNOWN"
    assert "ADD_EXPECTED_EDGE_UNKNOWN_FAIL_CLOSED" in member["target_weight_reason_codes"]
    assert member["target_weight_resolution"]["review_reason"]


def test_phase28_d55_a_add_evidence_resolver_valid_case_drives_positive_increment(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.05, "position_campaign_id": "campaign-11110"}],
        pm_rows=[{**_pm_row("11110", "ADD"), "position_campaign_id": "campaign-11110", "reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"]}],
        opportunity_rows=[
            _opportunity_row(
                "11110",
                1,
                0.82,
                position_campaign_id="campaign-11110",
                expected_edge_baseline_score=0.70,
                expected_edge_baseline_business_date="2026-07-14",
                expected_edge_baseline_campaign_id="campaign-11110",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
            )
        ],
        exposure=0.4,
        cap=0.4,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")
    evidence = member["add_investment_evidence"]

    assert evidence["schema_version"] == "add_investment_evidence.v1"
    assert evidence["producer_result_status"] == "PASS"
    assert evidence["campaign_continuation"]["status"] == "PASS"
    assert evidence["expected_edge"]["status"] == "PASS"
    assert evidence["expected_edge"]["temporal_authority"]["baseline_temporally_valid"] is True
    assert evidence["no_loss_averaging"]["status"] == "PASS"
    assert member["target_weight"] > member["current_weight"]
    assert member["add_allocation_eligibility_status"] == "PASS"


def test_phase30_ae1_canonical_si_campaign_repairs_runtime_current_add_mismatch(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.05}],
        pm_rows=[
            {
                **_pm_row("11110", "ADD"),
                "lifecycle_reference": "runtime-current-11110",
                "strategy_intelligence_campaign_id": "pc-canonical-11110-0001",
                "strategy_intelligence_add_worthiness_state": "ADD_ALLOWED",
                "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
                "entry_admission_action": "ADD_ALLOWED",
                "reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"],
            }
        ],
        opportunity_rows=[
            _opportunity_row(
                "11110",
                1,
                0.82,
                position_campaign_id="pc-canonical-11110-0001",
                expected_edge_baseline_score=0.70,
                expected_edge_baseline_business_date="2026-07-14",
                expected_edge_baseline_campaign_id="pc-canonical-11110-0001",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
            )
        ],
        exposure=0.4,
        cap=0.4,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")

    assert member["current_position_campaign_id"] == "pc-canonical-11110-0001"
    assert member["pm_position_campaign_id"] == "pc-canonical-11110-0001"
    assert member["add_investment_evidence"]["campaign_continuation"]["status"] == "PASS"
    assert member["add_investment_evidence"]["campaign_continuation"]["current_campaign_id"] == "pc-canonical-11110-0001"
    assert member["target_weight_change"] > 0
    assert member["add_allocation_eligibility_status"] == "PASS"


def test_phase31_g74_si_no_add_does_not_hard_block_positive_add_increment(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.05}],
        pm_rows=[
            {
                **_pm_row("11110", "ADD"),
                "position_campaign_id": "pc-canonical-11110-0001",
                "strategy_intelligence_campaign_id": "pc-canonical-11110-0001",
                "strategy_intelligence_add_worthiness_state": "NO_ADD",
                "entry_admission_state": "REVERSAL_RISK_ENTRY",
                "entry_admission_action": "NO_ADD",
                "reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"],
            }
        ],
        opportunity_rows=[
            _opportunity_row(
                "11110",
                1,
                0.82,
                position_campaign_id="pc-canonical-11110-0001",
                expected_edge_baseline_score=0.70,
                expected_edge_baseline_business_date="2026-07-14",
                expected_edge_baseline_campaign_id="pc-canonical-11110-0001",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
            )
        ],
        exposure=0.4,
        cap=0.4,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")
    competitor = next(
        row
        for row in payload["capital_competition"]["competitors"]
        if row["competitor_type"] == "ADD" and row["symbol"] == "11110"
    )

    assert member["add_investment_evidence"]["campaign_continuation"]["status"] == "PASS"
    assert member["add_investment_evidence"]["incremental_value"]["status"] == "PASS"
    assert member["add_investment_evidence"]["opportunity_cost"]["status"] == "PASS"
    assert member["strategy_intelligence_add_worthiness_state"] == "NO_ADD"
    assert member["entry_admission_action"] == "NO_ADD"
    assert member["target_weight_change"] > 0.0
    assert member["requested_incremental_weight"] > 0.0
    assert member["add_allocation_eligibility_status"] == "PASS"
    assert "ADD_WORTHINESS_NO_ADD" not in member["target_weight_reason_codes"]
    assert "ADD_ENTRY_ADMISSION_NO_ADD" not in member["target_weight_reason_codes"]
    assert member["target_weight_resolution"]["add_allocation_bridge"]["si_interpretation_context"]["hard_add_increment_gate"] is False
    assert competitor["canonical_add_competitor"]["proposed_incremental_target_weight"] > 0.0
    assert competitor["canonical_add_competitor"]["eligibility_state"] == "PASS"


def test_phase31_g74_99840_equivalent_si_no_add_does_not_hard_block_positive_add_increment(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-99840", "security_code": "99840", "current_weight": 0.157211, "position_campaign_id": "pc-162e0224bb69bedf-99840-0001"}],
        pm_rows=[
            {
                **_pm_row("99840", "ADD"),
                "position_campaign_id": "pc-162e0224bb69bedf-99840-0001",
                "strategy_intelligence_campaign_id": "pc-162e0224bb69bedf-99840-0001",
                "strategy_intelligence_add_worthiness_state": "NO_ADD",
                "entry_admission_state": "OVERHEATED_DECELERATING_ENTRY",
                "entry_admission_action": "NO_ADD",
                "reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"],
            }
        ],
        opportunity_rows=[
            _opportunity_row(
                "99840",
                1,
                0.21849110,
                position_campaign_id="pc-162e0224bb69bedf-99840-0001",
                expected_edge_baseline_score=0.21049026,
                expected_edge_baseline_business_date="2022-11-09",
                expected_edge_baseline_campaign_id="pc-162e0224bb69bedf-99840-0001",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
            ),
            _opportunity_row("22220", 2, 0.17880795),
        ],
        exposure=1.0,
        cap=0.18,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "99840")
    competitor = next(
        row
        for row in payload["capital_competition"]["competitors"]
        if row["competitor_type"] == "ADD" and row["symbol"] == "99840"
    )

    assert member["add_investment_evidence"]["producer_result_status"] == "PASS"
    assert member["add_investment_evidence"]["opportunity_cost"]["best_new_buy_score"] == 0.17880795
    assert member["requested_incremental_weight"] > 0.0
    assert member["target_weight_change"] > 0.0
    assert member["add_allocation_eligibility_status"] == "PASS"
    assert "ADD_WORTHINESS_NO_ADD" not in member["target_weight_reason_codes"]
    assert "ADD_ENTRY_ADMISSION_NO_ADD" not in member["target_weight_reason_codes"]
    assert competitor["canonical_add_competitor"]["proposed_incremental_target_weight"] > 0.0
    assert competitor["canonical_add_competitor"]["eligibility_state"] == "PASS"


def test_phase31_g74_40520_equivalent_expected_edge_weakening_still_blocks_add(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-40520", "security_code": "40520", "current_weight": 0.087036, "position_campaign_id": "pc-aa583a673123e666-40520-0001"}],
        pm_rows=[
            {
                **_pm_row("40520", "ADD"),
                "position_campaign_id": "pc-aa583a673123e666-40520-0001",
                "strategy_intelligence_campaign_id": "pc-aa583a673123e666-40520-0001",
                "strategy_intelligence_add_worthiness_state": "NO_ADD",
                "entry_admission_state": "OVERHEATED_DECELERATING_ENTRY",
                "entry_admission_action": "NO_ADD",
                "reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"],
            }
        ],
        opportunity_rows=[
            _opportunity_row(
                "40520",
                1,
                0.15478216,
                position_campaign_id="pc-aa583a673123e666-40520-0001",
                expected_edge_baseline_score=0.15523374,
                expected_edge_baseline_business_date="2023-06-19",
                expected_edge_baseline_campaign_id="pc-aa583a673123e666-40520-0001",
            ),
            _opportunity_row("22220", 2, 0.10296784),
        ],
        exposure=1.0,
        cap=0.18,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "40520")

    assert member["add_investment_evidence"]["expected_edge"]["state"] == "WEAKENING"
    assert member["add_investment_evidence"]["incremental_value"]["state"] == "UNKNOWN"
    assert member["add_investment_evidence"]["incremental_value"]["status"] == "FAIL_CLOSED"
    assert member["target_weight_change"] == 0.0
    assert member["requested_incremental_weight"] == 0.0
    assert member["add_allocation_eligibility_status"] == "FAIL_CLOSED"
    assert "ADD_EXPECTED_EDGE_WEAKENING" in member["target_weight_reason_codes"]
    assert "ADD_INCREMENTAL_VALUE_UNKNOWN" in member["target_weight_reason_codes"]


def test_phase28_d61_add_current_above_base_target_still_requests_increment_when_eligible(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.22, "position_campaign_id": "campaign-11110"}],
        pm_rows=[{**_pm_row("11110", "ADD"), "position_campaign_id": "campaign-11110", "reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"]}],
        opportunity_rows=[
            _opportunity_row(
                "11110",
                1,
                0.82,
                position_campaign_id="campaign-11110",
                expected_edge_baseline_score=0.70,
                expected_edge_baseline_business_date="2026-07-14",
                expected_edge_baseline_campaign_id="campaign-11110",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
            ),
            _opportunity_row("22220", 2, 0.60),
        ],
        exposure=0.4,
        cap=0.35,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")

    assert member["current_weight"] >= member["target_weight_resolution"]["base_weight"]
    assert member["add_allocation_eligibility_status"] == "PASS"
    assert member["requested_incremental_weight"] > 0
    assert member["accepted_incremental_weight"] > 0
    assert member["target_weight"] > member["current_weight"]
    assert member["target_weight"] <= 0.35
    assert "ADD_TARGET_WEIGHT_INCREASED" in member["target_weight_reason_codes"]


def test_phase28_d55_a_missing_campaign_authority_fails_closed(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.05}],
        pm_rows=[{**_pm_row("11110", "ADD"), "reason_codes": ["no_loss_averaging"]}],
        opportunity_rows=[
            _opportunity_row(
                "11110",
                1,
                0.82,
                expected_edge_baseline_score=0.70,
                expected_edge_baseline_business_date="2026-07-14",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
            )
        ],
        exposure=0.4,
        cap=0.4,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")

    assert member["target_weight"] == member["current_weight"]
    assert member["add_investment_evidence"]["campaign_continuation"]["status"] == "FAIL_CLOSED"
    assert "ADD_CAMPAIGN_CONTINUATION_FAIL" in member["target_weight_reason_codes"]


def test_phase28_d55_a_campaign_mismatch_and_future_baseline_fail_closed(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.05, "position_campaign_id": "campaign-current"}],
        pm_rows=[{**_pm_row("11110", "ADD"), "position_campaign_id": "campaign-current", "reason_codes": ["no_loss_averaging"]}],
        opportunity_rows=[
            _opportunity_row(
                "11110",
                1,
                0.82,
                position_campaign_id="campaign-other",
                expected_edge_baseline_score=0.70,
                expected_edge_baseline_business_date="2026-07-16",
                expected_edge_baseline_campaign_id="campaign-other",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
            )
        ],
        exposure=0.4,
        cap=0.4,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")
    evidence = member["add_investment_evidence"]

    assert member["target_weight"] == member["current_weight"]
    assert evidence["campaign_continuation"]["state"] == "MISMATCH"
    assert evidence["expected_edge"]["temporal_authority"]["future_evidence_used"] is True
    assert evidence["expected_edge"]["status"] == "FAIL_CLOSED"


def test_phase28_d55_a_edge_deterioration_negative_value_opportunity_cost_and_loss_averaging_fail_closed(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.05, "position_campaign_id": "campaign-11110"}],
        pm_rows=[{**_pm_row("11110", "ADD"), "position_campaign_id": "campaign-11110", "reason_codes": ["loss_averaging_violation"]}],
        opportunity_rows=[
            _opportunity_row(
                "11110",
                1,
                0.60,
                position_campaign_id="campaign-11110",
                expected_edge_baseline_score=0.70,
                expected_edge_baseline_business_date="2026-07-14",
                incremental_investment_value_state="NEGATIVE",
                opportunity_cost_status="FAIL",
            ),
            _opportunity_row("22220", 2, 0.90),
        ],
        exposure=0.4,
        cap=0.4,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")
    evidence = member["add_investment_evidence"]

    assert member["target_weight"] == member["current_weight"]
    assert evidence["expected_edge"]["state"] == "WEAKENING"
    assert evidence["incremental_value"]["state"] == "NEGATIVE"
    assert evidence["opportunity_cost"]["status"] == "FAIL_CLOSED"
    assert evidence["no_loss_averaging"]["status"] == "FAIL_CLOSED"
    assert {"ADD_EXPECTED_EDGE_WEAKENING", "ADD_INCREMENTAL_VALUE_NEGATIVE", "ADD_OPPORTUNITY_COST_FAIL", "ADD_NO_LOSS_AVERAGING_FAIL"} <= set(member["target_weight_reason_codes"])


def test_phase28_d55_b_lot_aware_reallocation_authorizes_minimum_lot_only_within_policy(tmp_path: Path) -> None:
    members = [
        {
            "security_code": "11110",
            "symbol": "11110",
            "current_position": False,
            "membership_intent": "ADD_CANDIDATE",
            "pm_action": "NEW",
            "construction_priority": 1,
            "target_weight": 0.03,
            "target_membership": True,
            "target_weight_authority": {},
            "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.03, "adjustments": []},
            "runtime_opportunity_score": 0.9,
        }
    ]
    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {
                "symbol": "11110",
                "lot_feasible": False,
                "broker_eligible": True,
                "minimum_executable_weight": 0.08,
                "reason_codes": ["below_minimum_executable_notional"],
            }
        ],
        target_gross_exposure=0.5,
        single_name_cap=0.2,
    )
    member = result["members"][0]

    assert member["target_weight"] == 0.08
    assert member["lot_aware_accepted_buy_new_weight"] == 0.08
    assert result["evidence"]["promoted"][0]["reason"] == "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED"
    assert result["evidence"]["ps_preflight_decides_economic_allocation"] is False


def test_phase28_d55_b_lot_aware_reallocation_preserves_cash_when_minimum_lot_not_justified(tmp_path: Path) -> None:
    members = [
        {
            "security_code": "11110",
            "symbol": "11110",
            "current_position": False,
            "membership_intent": "ADD_CANDIDATE",
            "pm_action": "NEW",
            "construction_priority": 1,
            "target_weight": 0.03,
            "target_membership": True,
            "target_weight_authority": {},
            "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.03, "adjustments": []},
            "runtime_opportunity_score": 0.9,
        }
    ]
    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[{"symbol": "11110", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.25}],
        target_gross_exposure=0.2,
        single_name_cap=0.2,
    )

    assert result["members"][0]["target_weight"] == 0.0
    assert result["members"][0]["target_weight_resolution"]["zero_weight_reason"] == "minimum_lot_exceeds_concentration_cap"
    assert result["evidence"]["remaining_cash_weight"] == 0.2
    assert result["evidence"]["skipped"][0]["reason"] == "minimum_lot_exceeds_concentration_cap"


def test_phase28_d55_b_lot_aware_reallocation_can_skip_high_rank_and_fund_lower_rank(tmp_path: Path) -> None:
    members = [
        {
            "security_code": "11110",
            "symbol": "11110",
            "current_position": False,
            "membership_intent": "ADD_CANDIDATE",
            "pm_action": "NEW",
            "construction_priority": 1,
            "target_weight": 0.03,
            "target_membership": True,
            "target_weight_authority": {},
            "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.03, "adjustments": []},
            "runtime_opportunity_score": 0.9,
        },
        {
            "security_code": "22220",
            "symbol": "22220",
            "current_position": False,
            "membership_intent": "ADD_CANDIDATE",
            "pm_action": "NEW",
            "construction_priority": 2,
            "target_weight": 0.06,
            "target_membership": True,
            "target_weight_authority": {},
            "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.06, "adjustments": []},
            "runtime_opportunity_score": 0.8,
        },
    ]
    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {"symbol": "11110", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.25},
            {"symbol": "22220", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.05},
        ],
        target_gross_exposure=0.2,
        single_name_cap=0.2,
    )
    by_code = {row["security_code"]: row for row in result["members"]}

    assert by_code["11110"]["target_weight"] == 0.0
    assert by_code["22220"]["target_weight"] == 0.06
    assert result["evidence"]["remaining_cash_weight"] == 0.14


def test_phase28_d55_b_lot_aware_reallocation_handles_buy_add_and_infeasible_add(tmp_path: Path) -> None:
    members = [
        {
            "security_code": "11110",
            "symbol": "11110",
            "current_position": True,
            "membership_intent": "RETAIN",
            "pm_action": "ADD",
            "construction_priority": 1,
            "current_weight": 0.05,
            "target_weight": 0.06,
            "target_membership": True,
            "target_weight_authority": {},
            "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.06, "adjustments": []},
        },
        {
            "security_code": "22220",
            "symbol": "22220",
            "current_position": True,
            "membership_intent": "RETAIN",
            "pm_action": "ADD",
            "construction_priority": 2,
            "current_weight": 0.05,
            "target_weight": 0.06,
            "target_membership": True,
            "target_weight_authority": {},
            "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.06, "adjustments": []},
        },
    ]
    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {"symbol": "11110", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.04},
            {"symbol": "22220", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.2},
        ],
        target_gross_exposure=0.2,
        single_name_cap=0.12,
    )
    by_code = {row["security_code"]: row for row in result["members"]}

    assert by_code["11110"]["target_weight"] == 0.05
    assert by_code["11110"]["lot_aware_accepted_incremental_weight"] == 0.0
    assert by_code["22220"]["target_weight"] == 0.05
    assert {row["symbol"] for row in result["evidence"]["skipped"]} == {"11110", "22220"}


def test_phase29_e_lot_first_rebatch_recycles_competition_loss_to_next_good_buy_new(tmp_path: Path) -> None:
    members = [
        _lot_rebatch_member("11110", priority=1, request=0.16, accepted=0.16),
        _lot_rebatch_member("22220", priority=2, request=0.10, accepted=0.0),
        _lot_rebatch_member("33330", priority=3, request=0.10, accepted=0.0),
    ]

    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {"symbol": "11110", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.25},
            {"symbol": "22220", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
            {"symbol": "33330", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
        ],
        target_gross_exposure=0.10,
        single_name_cap=0.20,
    )
    by_code = {row["security_code"]: row for row in result["members"]}

    assert by_code["11110"]["target_weight"] == 0.0
    assert by_code["22220"]["lot_aware_accepted_buy_new_weight"] == 0.10
    assert by_code["33330"]["lot_aware_accepted_buy_new_weight"] == 0.0
    assert result["evidence"]["rebatch_allocations"][0]["symbol"] == "22220"
    assert "lot_first_rebatch_recycled_request_positive_capital" in result["reason_codes"]
    assert result["evidence"]["capital_conservation"]["status"] == "PASS"


def test_phase29_e_lot_first_rebatch_does_not_expand_to_low_quality_non_participant(tmp_path: Path) -> None:
    members = [
        _lot_rebatch_member("11110", priority=1, request=0.16, accepted=0.16),
        _lot_rebatch_member("22220", priority=2, request=0.10, accepted=0.0),
        _lot_rebatch_member("33330", priority=3, request=0.0, accepted=0.0),
    ]

    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {"symbol": "11110", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.25},
            {"symbol": "22220", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.25},
            {"symbol": "33330", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.05},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
    )
    by_code = {row["security_code"]: row for row in result["members"]}

    assert by_code["11110"]["target_weight"] == 0.0
    assert by_code["22220"]["target_weight"] == 0.0
    assert by_code["33330"]["target_weight"] == 0.0
    assert result["evidence"]["rebatch_allocations"] == []
    assert result["evidence"]["remaining_cash_weight"] == 0.20


def test_phase29_e_common_rebatch_queue_allows_add_to_win_over_buy_new(tmp_path: Path) -> None:
    members = [
        _lot_rebatch_add_member("11110", priority=1, current_weight=0.05, request=0.10, accepted=0.0),
        _lot_rebatch_member("22220", priority=2, request=0.10, accepted=0.0),
    ]

    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {"symbol": "11110", "intent_type": "BUY_ADD", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
            {"symbol": "22220", "intent_type": "BUY_NEW", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
    )
    by_code = {row["security_code"]: row for row in result["members"]}

    assert by_code["11110"]["lot_aware_accepted_incremental_weight"] == 0.08
    assert by_code["22220"]["lot_aware_accepted_buy_new_weight"] == 0.0
    assert (
        by_code["11110"]["target_weight_resolution"]["lot_aware_final_reallocation"][
            "canonical_add_marginal_capital_competition_authority"
        ]["full_requested_block_authorized"]
        is False
    )


def test_phase29_e_common_rebatch_queue_allows_buy_new_to_win_over_add(tmp_path: Path) -> None:
    members = [
        _lot_rebatch_member("11110", priority=1, request=0.10, accepted=0.0),
        _lot_rebatch_add_member("22220", priority=2, current_weight=0.05, request=0.10, accepted=0.0),
    ]

    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {"symbol": "11110", "intent_type": "BUY_NEW", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
            {"symbol": "22220", "intent_type": "BUY_ADD", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.20,
    )
    by_code = {row["security_code"]: row for row in result["members"]}

    assert by_code["11110"]["lot_aware_accepted_buy_new_weight"] == 0.10
    assert by_code["22220"]["lot_aware_accepted_incremental_weight"] == 0.0


def test_phase29_e_lot_first_rebatch_preserves_concentration_cap_and_recycles_elsewhere(tmp_path: Path) -> None:
    members = [
        _lot_rebatch_add_member("11110", priority=1, current_weight=0.17, request=0.05, accepted=0.05),
        _lot_rebatch_member("22220", priority=2, request=0.08, accepted=0.0),
    ]

    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {"symbol": "11110", "intent_type": "BUY_ADD", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.04},
            {"symbol": "22220", "intent_type": "BUY_NEW", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
        ],
        target_gross_exposure=0.25,
        single_name_cap=0.18,
    )
    by_code = {row["security_code"]: row for row in result["members"]}

    assert by_code["11110"]["target_weight"] == 0.17
    assert by_code["11110"]["lot_first_rebatch_skip_reason"] == "minimum_lot_exceeds_concentration_cap"
    assert by_code["22220"]["lot_aware_accepted_buy_new_weight"] == 0.08


def test_phase29_l21d_lot_boundary_authorizes_buy_add_strategy_soft_overshoot(tmp_path: Path) -> None:
    members = [
        _lot_rebatch_add_member("94320", priority=1, current_weight=0.136879, request=0.043121, accepted=0.043121),
    ]

    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {
                "symbol": "94320",
                "intent_type": "BUY_ADD",
                "lot_feasible": False,
                "broker_eligible": True,
                "minimum_executable_weight": 0.050128,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX",
                    "strategy_cap_weight": 0.18,
                    "strategy_target_cap": 0.18,
                    "safety_hard_cap_weight": 0.25,
                    "safety_hard_cap": 0.25,
                    "maximum_strategy_feasible_lots": 2,
                    "maximum_safety_feasible_lots": 7,
                    "minimum_policy_lot_weight": 0.06052,
                    "post_trade_weight": 0.197399,
                    "safety_margin_after_trade": 0.052601,
                    "strategy_cap_overshoot_applied": True,
                    "strategy_cap_overshoot_weight": 0.017399,
                    "lot_overshoot_reason": "LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
                    "safety_hard_cap_preserved": True,
                    "executable_quantity_delta": 0,
                },
            }
        ],
        target_gross_exposure=1.0,
        single_name_cap=0.18,
    )
    member = result["members"][0]

    assert member["pm_action"] == "ADD"
    assert member["target_weight"] == 0.187007
    assert member["target_weight"] > 0.18
    assert member["target_weight"] <= 0.25
    assert member["lot_aware_accepted_incremental_weight"] == 0.050128
    assert member["phase29_l19_lot_resolution"]["strategy_cap_overshoot_applied"] is True
    assert member["phase29_l19_lot_resolution"]["lot_overshoot_reason"] == "LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP"
    assert member["phase29_l19_lot_resolution"]["preflight_executable_quantity_delta"] == 0
    assert member["phase29_l19_lot_resolution"]["final_quantity_delta"] is None
    assert result["evidence"]["skipped"] == []
    assert result["evidence"]["phase29_l19_cap_constrained_lot_floor_enabled"] is True
    assert result["evidence"]["phase29_l19_strategy_safety_cap_separated"] is True
    assert result["evidence"]["phase29_l19_candidate_exhaustion_status"] == "ALLOCATED_OR_NOT_APPLICABLE"


def test_phase29_l21d_strategy_soft_overshoot_requires_add_economic_pass(tmp_path: Path) -> None:
    member = _lot_rebatch_add_member("94320", priority=1, current_weight=0.136879, request=0.043121, accepted=0.043121)
    member["add_allocation_eligibility_status"] = "FAIL_CLOSED"

    result = apply_lot_aware_final_reallocation(
        members=[member],
        lot_feasibility_rows=[
            {
                "symbol": "94320",
                "intent_type": "BUY_ADD",
                "lot_feasible": False,
                "broker_eligible": True,
                "minimum_executable_weight": 0.050128,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX",
                    "strategy_cap_weight": 0.18,
                    "safety_hard_cap_weight": 0.25,
                    "minimum_policy_lot_weight": 0.06052,
                    "post_trade_weight": 0.197399,
                    "safety_hard_cap_preserved": True,
                },
            }
        ],
        target_gross_exposure=1.0,
        single_name_cap=0.18,
    )

    assert result["members"][0]["target_weight"] == 0.136879
    assert result["evidence"]["skipped"][0]["reason"] == "minimum_lot_exceeds_concentration_cap"


def test_phase29_l19_buy_new_safety_hard_breach_blocks_without_forced_deployment(tmp_path: Path) -> None:
    members = [_lot_rebatch_member("78780", priority=1, request=0.18, accepted=0.18)]

    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {
                "symbol": "78780",
                "intent_type": "BUY_NEW",
                "lot_feasible": False,
                "broker_eligible": True,
                "minimum_executable_weight": 0.292363,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX",
                    "strategy_cap_weight": 0.18,
                    "safety_hard_cap_weight": 0.25,
                    "maximum_strategy_feasible_lots": 0,
                    "maximum_safety_feasible_lots": 0,
                    "executable_quantity_delta": 0,
                },
            }
        ],
        target_gross_exposure=1.0,
        single_name_cap=0.18,
    )

    assert result["members"][0]["target_weight"] == 0.0
    assert result["evidence"]["skipped"][0]["blocked_reason"] == "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX"
    assert result["evidence"]["remaining_cash_weight"] == 1.0
    assert result["evidence"]["phase29_l19_candidate_exhaustion_status"] == "EXHAUSTED_TO_CASH"


def test_phase29_l19_residual_reallocation_attempts_next_lot_feasible_candidate(tmp_path: Path) -> None:
    members = [
        _lot_rebatch_member("11110", priority=1, request=0.18, accepted=0.18),
        _lot_rebatch_member("22220", priority=2, request=0.08, accepted=0.0),
    ]

    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {
                "symbol": "11110",
                "intent_type": "BUY_NEW",
                "lot_feasible": False,
                "broker_eligible": True,
                "minimum_executable_weight": 0.30,
                "phase29_l19_lot_resolution": {"boundary_classification": "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX", "safety_hard_cap_weight": 0.25},
            },
            {
                "symbol": "22220",
                "intent_type": "BUY_NEW",
                "lot_feasible": True,
                "broker_eligible": True,
                "minimum_executable_weight": 0.08,
                "phase29_l19_lot_resolution": {"boundary_classification": "CAP_CONSTRAINED_LOT_EXECUTABLE", "safety_hard_cap_weight": 0.25, "executable_quantity_delta": 100},
            },
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.18,
    )
    by_code = {row["security_code"]: row for row in result["members"]}

    assert by_code["11110"]["target_weight"] == 0.0
    assert by_code["22220"]["lot_aware_accepted_buy_new_weight"] == 0.08
    assert result["evidence"]["phase29_l19_allocation_iterations"][0]["symbol"] == "22220"
    assert result["evidence"]["phase29_l19_candidate_exhaustion_status"] == "ALLOCATED_OR_NOT_APPLICABLE"


def test_phase29_l19_candidate_exhaustion_retains_cash_without_forced_buy(tmp_path: Path) -> None:
    members = [
        _lot_rebatch_member("11110", priority=1, request=0.18, accepted=0.18),
        _lot_rebatch_member("22220", priority=2, request=0.18, accepted=0.0),
    ]

    result = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=[
            {"symbol": "11110", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.30, "phase29_l19_lot_resolution": {"boundary_classification": "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX", "safety_hard_cap_weight": 0.25}},
            {"symbol": "22220", "lot_feasible": False, "broker_eligible": True, "minimum_executable_weight": 0.30, "phase29_l19_lot_resolution": {"boundary_classification": "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX", "safety_hard_cap_weight": 0.25}},
        ],
        target_gross_exposure=0.20,
        single_name_cap=0.18,
    )

    assert all(row["target_weight"] == 0.0 for row in result["members"])
    assert result["evidence"]["remaining_cash_weight"] == 0.20
    assert result["evidence"]["residual_cash_reason"] == "CONCENTRATION_LIMIT"
    assert result["evidence"]["phase29_l19_candidate_exhaustion_status"] == "EXHAUSTED_TO_CASH"


def test_phase29_e_lot_first_rebatch_is_deterministic_for_input_order(tmp_path: Path) -> None:
    members = [
        _lot_rebatch_member("22220", priority=1, request=0.10, accepted=0.0),
        _lot_rebatch_member("11110", priority=1, request=0.10, accepted=0.0),
    ]
    feasibility = [
        {"symbol": "22220", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
        {"symbol": "11110", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08},
    ]

    first = apply_lot_aware_final_reallocation(
        members=members,
        lot_feasibility_rows=feasibility,
        target_gross_exposure=0.10,
        single_name_cap=0.20,
    )
    second = apply_lot_aware_final_reallocation(
        members=list(reversed(members)),
        lot_feasibility_rows=list(reversed(feasibility)),
        target_gross_exposure=0.10,
        single_name_cap=0.20,
    )

    assert {row["security_code"]: row["target_weight"] for row in first["members"]} == {
        row["security_code"]: row["target_weight"] for row in second["members"]
    }
    assert next(row for row in first["members"] if row["security_code"] == "11110")["target_weight"] == 0.10


def test_phase28_d28_20230404_incremental_budget_reconciliation_reproduction(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[
            {"position_id": "current-43880", "security_code": "43880", "current_weight": 0.123279},
            {"position_id": "current-83060", "security_code": "83060", "current_weight": 0.17231},
            {"position_id": "current-94320", "security_code": "94320", "current_weight": 0.126961},
        ],
        pm_rows=[
            _pm_row("43880", "HOLD"),
            _pm_row("83060", "ADD"),
            _pm_row("94320", "ADD"),
        ],
        opportunity_rows=[
            _opportunity_row("94320", 1, 0.32829857),
            _opportunity_row("83060", 2, 0.22285948),
            _opportunity_row("43880", 3, 0.19727013),
            _opportunity_row("67310", 4, 0.1747092),
            _opportunity_row("59350", 6, 0.01072994),
        ],
        exposure=0.72,
        cap=0.2,
    )

    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}
    assert payload["producer_result_status"] != "BLOCK"
    assert payload["baseline_existing_required_weight"] == 0.42255
    assert payload["available_incremental_budget"] == 0.29745
    assert payload["incremental_budget_reconciliation"]["accepted_add_increment"] == 0.0
    assert payload["incremental_budget_reconciliation"]["accepted_buy_new_weight"] == 0.288
    assert payload["total_target_weight"] == 0.71055
    assert payload["total_target_weight"] <= payload["target_gross_exposure"]
    assert by_code["43880"]["target_weight"] == 0.123279
    assert by_code["83060"]["target_weight"] == 0.17231
    assert by_code["94320"]["target_weight"] == 0.126961
    assert by_code["67310"]["target_weight"] == 0.144
    assert by_code["59350"]["target_weight"] == 0.144
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase28_d28_hold_baseline_preserves_current_weight_below_equal_weight(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.10}],
        pm_rows=[_pm_row("11110", "HOLD")],
        opportunity_rows=[_opportunity_row("11110", 1, 0.5), _opportunity_row("22220", 2, 0.4)],
        exposure=0.6,
        cap=0.5,
    )
    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}

    assert by_code["11110"]["target_weight"] == 0.10
    assert by_code["11110"]["baseline_existing_weight"] == 0.10
    assert "hold_equal_weight_increase_reconciled_to_current_weight" in payload["reason_codes"]


def test_phase28_d28_add_sufficient_budget_still_increases_existing_position(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.05}],
        pm_rows=[_pm_row("11110", "ADD")],
        opportunity_rows=[
            _opportunity_row(
                "11110",
                1,
                0.8,
                expected_edge_baseline_score=0.5,
                expected_edge_baseline_business_date="2026-07-14",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
                campaign_continuation_status="PASS",
                no_loss_averaging_status="PASS",
            )
        ],
        exposure=0.4,
        cap=0.4,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")

    assert member["target_weight"] > member["current_weight"]
    assert member["accepted_incremental_weight"] > 0
    assert member["add_allocation_eligibility_status"] == "PASS"
    assert "ADD_TARGET_WEIGHT_INCREASED" in member["target_weight_reason_codes"]


def test_phase28_d28_multiple_add_within_budget_both_increase(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[
            {"position_id": "current-11110", "security_code": "11110", "current_weight": 0.05},
            {"position_id": "current-22220", "security_code": "22220", "current_weight": 0.05},
        ],
        pm_rows=[_pm_row("11110", "ADD"), _pm_row("22220", "ADD")],
        opportunity_rows=[
            _eligible_add_opportunity("11110", 1, 0.8),
            _eligible_add_opportunity("22220", 2, 0.7),
        ],
        exposure=0.4,
        cap=0.3,
    )
    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}

    assert by_code["11110"]["accepted_incremental_weight"] > 0
    assert by_code["22220"]["accepted_incremental_weight"] > 0
    assert payload["total_target_weight"] <= payload["target_gross_exposure"]


def test_phase28_d28_multiple_add_over_budget_trims_weakest_increment(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[
            {"position_id": "current-11110", "security_code": "11110", "current_weight": 0.30},
            {"position_id": "current-22220", "security_code": "22220", "current_weight": 0.05},
            {"position_id": "current-33330", "security_code": "33330", "current_weight": 0.05},
        ],
        pm_rows=[_pm_row("11110", "HOLD"), _pm_row("22220", "ADD"), _pm_row("33330", "ADD")],
        opportunity_rows=[
            _opportunity_row("11110", 1, 0.9),
            _eligible_add_opportunity("22220", 2, 0.8),
            _eligible_add_opportunity("33330", 3, 0.7),
        ],
        exposure=0.5,
        cap=0.5,
    )
    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}

    assert payload["producer_result_status"] != "BLOCK"
    assert payload["incremental_budget_reconciliation"]["trimmed_incremental_weight"] > 0
    assert by_code["22220"]["accepted_incremental_weight"] > 0
    assert by_code["33330"]["accepted_incremental_weight"] == 0
    assert payload["total_target_weight"] <= payload["target_gross_exposure"]


def test_phase28_d28_add_and_buy_new_compete_for_same_incremental_budget(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[
            {"position_id": "current-11110", "security_code": "11110", "current_weight": 0.30},
            {"position_id": "current-22220", "security_code": "22220", "current_weight": 0.05},
        ],
        pm_rows=[_pm_row("11110", "HOLD"), _pm_row("22220", "ADD")],
        opportunity_rows=[
            _opportunity_row("11110", 1, 0.9),
            _eligible_add_opportunity("22220", 2, 0.8),
            _opportunity_row("33330", 3, 0.7),
        ],
        exposure=0.5,
        cap=0.5,
    )
    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}

    assert by_code["22220"]["accepted_incremental_weight"] > 0
    assert by_code["33330"]["accepted_buy_new_weight"] < by_code["33330"]["requested_buy_new_weight"]
    assert payload["total_target_weight"] <= payload["target_gross_exposure"]


def test_phase28_d28_reduce_releases_capacity_for_buy_new_without_exit_escalation(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[
            {"position_id": "current-11110", "security_code": "11110", "current_weight": 0.30},
            {"position_id": "current-22220", "security_code": "22220", "current_weight": 0.10},
        ],
        pm_rows=[_pm_row("11110", "REDUCE"), _pm_row("22220", "HOLD")],
        opportunity_rows=[_opportunity_row("33330", 1, 0.9), _opportunity_row("11110", 2, 0.8)],
        exposure=0.4,
        cap=0.4,
    )
    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}

    assert payload["incremental_budget_reconciliation"]["released_reduce_capacity"] > 0
    assert by_code["11110"]["membership_intent"] == "REDUCE_CANDIDATE"
    assert by_code["11110"]["target_weight"] == 0.225
    assert by_code["11110"]["reduce_fraction"] == 0.25
    assert by_code["33330"]["target_weight"] > 0
    assert payload["total_target_weight"] <= payload["target_gross_exposure"]


def test_phase28_d34_77760_light_reduce_resolves_partial_target_weight(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-77760", "security_code": "77760", "current_weight": 0.053147}],
        pm_rows=[_pm_row("77760", "REDUCE")],
        opportunity_rows=[_opportunity_row("77760", 1, 0.5)],
        exposure=0.2,
        cap=0.2,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "77760")

    assert member["target_weight"] == 0.03986
    assert member["baseline_existing_weight"] == 0.03986
    assert member["reduce_intensity"] == "LIGHT"
    assert member["reduce_fraction"] == 0.25
    assert member["released_reduce_capacity"] == 0.013287
    assert member["target_membership"] is True


def test_phase28_d34_43880_light_reduce_resolves_partial_target_weight(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-43880", "security_code": "43880", "current_weight": 0.127745}],
        pm_rows=[_pm_row("43880", "REDUCE")],
        opportunity_rows=[_opportunity_row("43880", 1, 0.5)],
        exposure=0.3,
        cap=0.3,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "43880")

    assert member["target_weight"] == 0.095809
    assert member["reduce_fraction_authority"]["authority_type"] == "CANONICAL_REDUCE_INTENSITY_AUTHORITY"
    assert member["target_weight_resolution"]["reason"] == "reduce_partial_target_resolved"


def test_phase28_d34_reduce_unknown_intensity_fails_closed_without_exit_target(tmp_path: Path) -> None:
    row = _pm_row("11110", "REDUCE")
    row["intensity"] = "UNRESOLVED"
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.2}],
        pm_rows=[row],
        opportunity_rows=[_opportunity_row("11110", 1, 0.5)],
        exposure=0.4,
        cap=0.4,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert member["pm_action"] == "REDUCE"
    assert member["target_weight_resolution"]["review_reason"] == "reduce_intensity_unknown"


def test_phase28_d28_zero_capacity_add_retains_baseline_without_sell(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.4}],
        pm_rows=[_pm_row("11110", "ADD")],
        opportunity_rows=[_eligible_add_opportunity("11110", 1, 0.8)],
        exposure=0.4,
        cap=0.5,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")

    assert payload["available_incremental_budget"] == 0.0
    assert member["target_weight"] == 0.4
    assert member["accepted_incremental_weight"] == 0.0
    assert member["membership_intent"] == "RETAIN"
    assert member["weight_intent"] == "INCREASE"


def test_phase28_d39_retained_baseline_over_target_enters_passive_convergence(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[
            {"position_id": "current-11110", "security_code": "11110", "current_weight": 0.45},
            {"position_id": "current-22220", "security_code": "22220", "current_weight": 0.30},
        ],
        pm_rows=[_pm_row("11110", "HOLD"), _pm_row("22220", "ADD")],
        opportunity_rows=[_opportunity_row("11110", 1, 0.9), _eligible_add_opportunity("22220", 2, 0.8)],
        exposure=0.7,
        cap=0.6,
    )

    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}
    assert payload["producer_result_status"] != "BLOCK"
    assert "existing_baseline_over_dynamic_target_passive_convergence" in payload["reason_codes"]
    assert "positive_increment_suppressed_while_over_target" in payload["reason_codes"]
    assert "baseline_existing_required_weight_above_target_gross_exposure" not in payload["reason_codes"]
    assert payload["baseline_existing_required_weight"] == 0.75
    assert payload["available_incremental_budget"] == 0.0
    assert payload["total_target_weight"] == 0.75
    assert payload["incremental_budget_reconciliation"]["aggregate_exposure_state"] == "OVER_TARGET_EXISTING_BASELINE"
    assert payload["incremental_budget_reconciliation"]["transition_mode"] == "PASSIVE_CONVERGENCE"
    assert payload["incremental_budget_reconciliation"]["positive_increment_allowed"] is False
    assert by_code["11110"]["target_weight"] == 0.45
    assert by_code["22220"]["target_weight"] == 0.30
    assert by_code["22220"]["accepted_incremental_weight"] == 0.0


def test_phase28_d39_20230601_exact_passive_convergence_replay(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[
            {"position_id": "current-21340", "security_code": "21340", "current_weight": 0.117487},
            {"position_id": "current-30410", "security_code": "30410", "current_weight": 0.1207},
            {"position_id": "current-59550", "security_code": "59550", "current_weight": 0.091236},
            {"position_id": "current-76470", "security_code": "76470", "current_weight": 0.183666},
            {"position_id": "current-93990", "security_code": "93990", "current_weight": 0.064251},
            {"position_id": "current-94320", "security_code": "94320", "current_weight": 0.116166},
        ],
        pm_rows=[
            _pm_row("21340", "ADD"),
            _pm_row("30410", "ADD"),
            _pm_row("59550", "ADD"),
            _pm_row("76470", "HOLD"),
            _pm_row("93990", "REDUCE"),
            _pm_row("94320", "ADD"),
        ],
        opportunity_rows=[
            _opportunity_row("94320", 1, 0.49789815),
            _opportunity_row("30410", 2, 0.45),
            _opportunity_row("21340", 3, 0.34150423),
            _opportunity_row("59550", 4, 0.3),
            _opportunity_row("76470", 5, 0.25),
            _opportunity_row("93990", 6, 0.06864322),
            _opportunity_row("11110", 7, 0.2),
            _opportunity_row("22220", 8, 0.1),
        ],
        exposure=0.54,
        cap=0.18,
    )

    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}
    assert payload["producer_result_status"] != "BLOCK"
    assert payload["baseline_existing_required_weight"] == 0.677443
    assert payload["available_incremental_budget"] == 0.0
    assert payload["total_target_weight"] == 0.677443
    assert payload["incremental_budget_reconciliation"]["aggregate_exposure_state"] == "OVER_TARGET_EXISTING_BASELINE"
    assert payload["incremental_budget_reconciliation"]["accepted_buy_new_weight"] == 0.0
    assert by_code["21340"]["target_weight"] == 0.117487
    assert by_code["30410"]["target_weight"] == 0.1207
    assert by_code["59550"]["target_weight"] == 0.091236
    assert by_code["76470"]["target_weight"] == 0.183666
    assert by_code["93990"]["target_weight"] == 0.048188
    assert by_code["93990"]["released_reduce_capacity"] == 0.016063
    assert by_code["94320"]["target_weight"] == 0.116166
    assert by_code["11110"]["accepted_buy_new_weight"] == 0.0
    assert by_code["22220"]["accepted_buy_new_weight"] == 0.0


def test_phase28_d39_add_over_target_preserves_baseline_and_suppresses_increment(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[
            {"position_id": "current-11110", "security_code": "11110", "current_weight": 0.5},
            {"position_id": "current-22220", "security_code": "22220", "current_weight": 0.2},
        ],
        pm_rows=[_pm_row("11110", "HOLD"), _pm_row("22220", "ADD")],
        opportunity_rows=[_opportunity_row("11110", 1, 0.9), _eligible_add_opportunity("22220", 2, 0.8)],
        exposure=0.54,
        cap=0.5,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "22220")

    assert payload["producer_result_status"] != "BLOCK"
    assert member["pm_action"] == "ADD"
    assert member["target_weight"] == 0.2
    assert member["accepted_incremental_weight"] == 0.0
    assert member["requested_incremental_weight"] > 0


def test_phase28_d39_buy_new_over_target_gets_zero_allocation_without_block(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.68}],
        pm_rows=[_pm_row("11110", "HOLD")],
        opportunity_rows=[_opportunity_row("11110", 1, 0.9), _opportunity_row("22220", 2, 0.8)],
        exposure=0.54,
        cap=0.5,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "22220")

    assert payload["producer_result_status"] != "BLOCK"
    assert member["current_position"] is False
    assert member["requested_buy_new_weight"] > 0
    assert member["accepted_buy_new_weight"] == 0.0
    assert member["target_weight"] == 0.0


def test_phase28_d39_reduce_over_target_passes_even_when_aggregate_remains_over_target(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[
            {"position_id": "current-11110", "security_code": "11110", "current_weight": 0.4},
            {"position_id": "current-22220", "security_code": "22220", "current_weight": 0.4},
        ],
        pm_rows=[_pm_row("11110", "REDUCE"), _pm_row("22220", "HOLD")],
        opportunity_rows=[_opportunity_row("11110", 1, 0.9), _opportunity_row("22220", 2, 0.8)],
        exposure=0.54,
        cap=0.5,
    )
    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}

    assert payload["producer_result_status"] != "BLOCK"
    assert payload["total_target_weight"] == 0.7
    assert by_code["11110"]["target_weight"] == 0.3
    assert by_code["11110"]["reduce_fraction"] == 0.25
    assert payload["incremental_budget_reconciliation"]["aggregate_exposure_state"] == "OVER_TARGET_EXISTING_BASELINE"


def test_phase28_d39_exit_over_target_passes_and_preserves_zero_target(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[
            {"position_id": "current-11110", "security_code": "11110", "current_weight": 0.68},
            {"position_id": "current-22220", "security_code": "22220", "current_weight": 0.2},
        ],
        pm_rows=[_pm_row("11110", "HOLD"), _pm_row("22220", "EXIT")],
        opportunity_rows=[_opportunity_row("11110", 1, 0.9), _opportunity_row("22220", 2, 0.8)],
        exposure=0.54,
        cap=0.5,
    )
    by_code = {row["security_code"]: row for row in payload["portfolio_members"]}

    assert payload["producer_result_status"] != "BLOCK"
    assert by_code["22220"]["membership_intent"] == "REMOVE_CANDIDATE"
    assert by_code["22220"]["target_weight"] == 0.0
    assert payload["total_target_weight"] == 0.68


def test_phase28_d39_positive_increment_over_target_remains_fail_closed() -> None:
    assert _positive_increment_over_target(
        final_target_weight_sum=0.58,
        target_gross_exposure=0.54,
        tolerance=0.0,
        accepted_add=0.08,
        accepted_buy_new=0.0,
    )
    assert not _positive_increment_over_target(
        final_target_weight_sum=0.677443,
        target_gross_exposure=0.54,
        tolerance=0.0,
        accepted_add=0.0,
        accepted_buy_new=0.0,
    )


def test_phase29_l16_tick_risk_caps_low_price_buy_new_without_hard_exclusion(tmp_path: Path) -> None:
    payload = _build_l16_payload(
        tmp_path,
        opportunity_rows=[
            _l16_opportunity("11110", 1, price=100.0, rolling_value=1_000_000_000),
            _l16_opportunity("22220", 2, price=50.0, rolling_value=1_000_000_000),
            _l16_opportunity("33330", 3, price=20.0, rolling_value=1_000_000_000),
            _l16_opportunity("44440", 4, price=10.0, rolling_value=1_000_000_000),
        ],
        exposure=0.72,
        cap=0.18,
        portfolio_equity=1_000_000,
    )
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert by_code["11110"]["price_tick_risk_tier"] == "WATCH"
    assert by_code["11110"]["target_weight"] == 0.12
    assert by_code["22220"]["price_tick_risk_tier"] == "ELEVATED"
    assert by_code["22220"]["target_weight"] == 0.10
    assert by_code["33330"]["price_tick_risk_tier"] == "SEVERE"
    assert by_code["33330"]["target_weight"] == 0.08
    assert by_code["44440"]["price_tick_risk_tier"] == "EXTREME"
    assert by_code["44440"]["target_weight"] == 0.05
    assert all(member["target_weight"] > 0 for member in by_code.values())
    assert validate_portfolio_construction_artifact(payload)["status"] == "PASS"


def test_phase29_l16_liquidity_capacity_caps_but_does_not_blanket_reject_ordinary_buy_new(tmp_path: Path) -> None:
    payload = _build_l16_payload(
        tmp_path,
        opportunity_rows=[
            _l16_opportunity("11110", 1, price=100.0, rolling_value=10_000_000),
            _l16_opportunity("22220", 2, price=1000.0, rolling_value=1_000_000_000),
        ],
        exposure=0.36,
        cap=0.18,
        portfolio_equity=2_000_000,
    )
    low_price = next(member for member in payload["portfolio_members"] if member["security_code"] == "11110")
    normal_price = next(member for member in payload["portfolio_members"] if member["security_code"] == "22220")

    assert low_price["liquidity_capacity_status"] == "SEVERE"
    assert low_price["liquidity_capacity_cap_weight"] == 0.05
    assert low_price["target_weight"] == 0.05
    assert low_price["target_membership"] is True
    assert normal_price["price_tick_risk_tier"] == "NORMAL"
    assert normal_price["target_weight"] == 0.18


def test_phase29_l16_low_price_missing_liquidity_evidence_fails_closed_symbol_only(tmp_path: Path) -> None:
    payload = _build_l16_payload(
        tmp_path,
        opportunity_rows=[
            _l16_opportunity("11110", 1, price=50.0, rolling_value=None),
            _l16_opportunity("22220", 2, price=1000.0, rolling_value=None),
        ],
        exposure=0.36,
        cap=0.18,
        portfolio_equity=1_000_000,
    )
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert by_code["11110"]["target_weight"] == 0.0
    assert by_code["11110"]["target_membership"] is False
    assert by_code["11110"]["allocation_cap_reason"] == "low_price_liquidity_evidence_missing_fail_closed"
    assert by_code["22220"]["target_weight"] == 0.18


def test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle(tmp_path: Path) -> None:
    payload = _build_l16_payload(
        tmp_path,
        opportunity_rows=[
            _l16_opportunity("11110", 1, price=5.0, rolling_value=1_000_000_000, prior_exit_business_date="2026-07-14", prior_exit_reason="EXIT_BY_TREND_AND_EDGE_BREAK"),
            _l16_opportunity("22220", 2, price=5.0, rolling_value=1_000_000_000, prior_exit_business_date="2026-07-09", prior_exit_reason="EXIT_BY_TREND_AND_EDGE_BREAK"),
            _l16_opportunity("33330", 11, price=5.0, rolling_value=1_000_000_000, prior_exit_business_date="2026-07-09", prior_exit_reason="EXIT_BY_TREND_AND_EDGE_BREAK"),
        ],
        buy_quality_rows=[
            _l16_quality("11110", "FULL_ALLOCATION_ELIGIBLE"),
            _l16_quality("22220", "FULL_ALLOCATION_ELIGIBLE"),
            _l16_quality("33330", "FULL_ALLOCATION_ELIGIBLE"),
        ],
        exposure=0.54,
        cap=0.18,
        portfolio_equity=1_000_000,
    )
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert by_code["11110"]["semantic_buy_type"] == "REENTRY"
    assert by_code["11110"]["reentry_cooldown_status"] == "FAIL_CLOSED"
    assert by_code["11110"]["reentry_semantic_state"] == "REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION"
    assert by_code["11110"]["reentry_semantic_status"] == "FAIL_CLOSED"
    assert "REENTRY_BLOCKED_CHURN_PROTECTION" in by_code["11110"]["reentry_reason_codes"]
    assert by_code["11110"]["target_weight"] == 0.0
    assert by_code["22220"]["semantic_buy_type"] == "REENTRY"
    assert by_code["22220"]["reentry_cooldown_status"] == "PASS"
    assert by_code["22220"]["reentry_recovery_status"] == "PASS"
    assert by_code["22220"]["reentry_semantic_state"] == "REENTRY_ELIGIBLE"
    assert by_code["22220"]["reentry_semantic_status"] == "PASS"
    assert by_code["22220"]["reentry_semantic_eligibility"]["owner"] == "PORTFOLIO_CONSTRUCTION"
    assert by_code["22220"]["target_weight"] == 0.05
    assert by_code["33330"]["reentry_recovery_status"] == "FAIL_CLOSED"
    assert by_code["33330"]["reentry_recovery_reason"] == "reentry_opportunity_not_requalified"
    assert by_code["33330"]["reentry_semantic_state"] == "REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE"
    assert "REENTRY_BLOCKED_CURRENT_ELIGIBILITY" in by_code["33330"]["reentry_reason_codes"]
    assert by_code["33330"]["target_weight"] == 0.0


def test_phase31_g26_first_time_buy_new_has_non_reentry_semantic_contract(tmp_path: Path) -> None:
    payload = _build_l16_payload(
        tmp_path,
        opportunity_rows=[_l16_opportunity("11110", 1, price=1000.0, rolling_value=1_000_000_000)],
        buy_quality_rows=[_l16_quality("11110", "FULL_ALLOCATION_ELIGIBLE")],
        exposure=0.18,
        cap=0.18,
        portfolio_equity=1_000_000,
    )
    member = payload["portfolio_members"][0]

    assert member["semantic_buy_type"] == "BUY_NEW"
    assert member["reentry_semantic_state"] == "REENTRY_NOT_APPLICABLE"
    assert member["reentry_semantic_status"] == "NOT_APPLICABLE"
    assert member["target_weight"] == 0.18
    assert member["target_weight_authority"]["semantic_reentry_authority"]["semantic_result"]["constraint_scope"] == "NOT_APPLICABLE"


def test_phase29_l21r3_reentry_capacity_authority_resolves_normal_excessive_and_missing_cases(tmp_path: Path) -> None:
    payload = _build_l16_payload(
        tmp_path,
        opportunity_rows=[
            _l16_opportunity("11110", 1, price=1000.0, rolling_value=1_000_000_000, prior_exit_business_date="2026-07-09", prior_exit_reason="EXIT_BY_TREND_AND_EDGE_BREAK"),
            _l16_opportunity("22220", 2, price=1000.0, rolling_value=1_000_000, prior_exit_business_date="2026-07-09", prior_exit_reason="EXIT_BY_TREND_AND_EDGE_BREAK"),
            _l16_opportunity("33330", 3, price=1000.0, rolling_value=None, prior_exit_business_date="2026-07-09", prior_exit_reason="EXIT_BY_TREND_AND_EDGE_BREAK"),
        ],
        buy_quality_rows=[
            _l16_quality("11110", "FULL_ALLOCATION_ELIGIBLE"),
            _l16_quality("22220", "FULL_ALLOCATION_ELIGIBLE"),
            _l16_quality("33330", "FULL_ALLOCATION_ELIGIBLE"),
        ],
        exposure=0.54,
        cap=0.18,
        portfolio_equity=1_000_000,
    )
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert by_code["11110"]["semantic_buy_type"] == "REENTRY"
    assert by_code["11110"]["capacity_ratio"] == 0.00018
    assert by_code["11110"]["liquidity_capacity_status"] == "NORMAL"
    assert by_code["11110"]["reentry_capacity_status"] == "NORMAL"
    assert by_code["11110"]["target_weight"] == 0.18
    assert by_code["11110"]["capacity_source_field"] == "rolling_median_traded_value_20"

    assert by_code["22220"]["capacity_ratio"] == 0.18
    assert by_code["22220"]["liquidity_capacity_status"] == "SEVERE"
    assert by_code["22220"]["reentry_recovery_status"] == "FAIL_CLOSED"
    assert by_code["22220"]["reentry_recovery_reason"] == "reentry_capacity_unavailable"
    assert by_code["22220"]["reentry_semantic_status"] == "FAIL_CLOSED"
    assert by_code["22220"]["reentry_constraint_scope"] == "SYMBOL_LOCAL"
    assert by_code["22220"]["target_weight"] == 0.0

    assert by_code["33330"]["capacity_ratio"] is None
    assert by_code["33330"]["liquidity_capacity_status"] == "UNKNOWN"
    assert by_code["33330"]["reentry_recovery_status"] == "REVIEW_REQUIRED"
    assert by_code["33330"]["reentry_recovery_reason"] == "reentry_capacity_unavailable"
    assert by_code["33330"]["reentry_semantic_state"] == "REENTRY_INSUFFICIENT_EVIDENCE"
    assert by_code["33330"]["reentry_semantic_status"] == "REVIEW_REQUIRED"
    assert by_code["33330"]["target_weight"] == 0.0


def test_phase31_g26_reentry_rejection_is_symbol_local_and_next_competitor_survives(tmp_path: Path) -> None:
    payload = _build_l16_payload(
        tmp_path,
        opportunity_rows=[
            _l16_opportunity("11110", 1, price=1000.0, rolling_value=1_000_000, prior_exit_business_date="2026-07-09", prior_exit_reason="EXIT_BY_TREND_AND_EDGE_BREAK"),
            _l16_opportunity("22220", 2, price=1000.0, rolling_value=1_000_000_000),
        ],
        buy_quality_rows=[
            _l16_quality("11110", "FULL_ALLOCATION_ELIGIBLE"),
            _l16_quality("22220", "FULL_ALLOCATION_ELIGIBLE"),
        ],
        exposure=0.36,
        cap=0.18,
        portfolio_equity=1_000_000,
    )
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert by_code["11110"]["reentry_semantic_state"] == "REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE"
    assert by_code["11110"]["reentry_constraint_scope"] == "SYMBOL_LOCAL"
    assert by_code["11110"]["target_weight"] == 0.0
    assert by_code["22220"]["semantic_buy_type"] == "BUY_NEW"
    assert by_code["22220"]["target_weight"] == 0.18


def test_phase29_l21r3_prior_exit_persists_when_buy_quality_temporarily_excludes_candidate(tmp_path: Path) -> None:
    payload = _build_l16_payload(
        tmp_path,
        opportunity_rows=[
            _l16_opportunity("23880", 1, price=1000.0, rolling_value=1_000_000_000, prior_exit_business_date="2026-07-09"),
        ],
        buy_quality_rows=[
            _l16_quality("23880", "REJECT"),
        ],
        exposure=0.18,
        cap=0.18,
        portfolio_equity=1_000_000,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "23880")

    assert member["membership_intent"] == "EXCLUDE"
    assert member["target_weight"] == 0.0
    assert member["prior_exit_business_date"] == "2026-07-09"
    assert member["semantic_buy_type"] == "REENTRY"
    assert member["reentry_cooldown_status"] == "PASS"
    assert member["reentry_semantic_state"] == "REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE"
    assert member["reentry_semantic_status"] == "FAIL_CLOSED"


def test_phase29_l21s_one_lot_fallback_allocates_positive_buy_new_below_normal_lot_rounding() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _lot_rebatch_member("11110", priority=1, request=0.03, accepted=0.03),
        ],
        lot_feasibility_rows=[
            {
                "symbol": "11110",
                "intent_type": "BUY_NEW",
                "lot_feasible": True,
                "broker_eligible": True,
                "minimum_executable_weight": 0.08,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "CAP_CONSTRAINED_LOT_EXECUTABLE",
                    "one_lot_quantity": 100,
                    "one_lot_notional": 80_000.0,
                    "one_lot_feasibility_status": "PASS",
                    "one_lot_fallback_applied": True,
                    "normal_lot_quantity": 0,
                    "continuous_target_weight": 0.03,
                    "continuous_target_notional": 30_000.0,
                    "safety_hard_cap_preserved": True,
                },
            }
        ],
        target_gross_exposure=0.5,
        single_name_cap=0.18,
    )
    member = result["members"][0]

    assert member["target_weight"] == 0.08
    assert member["lot_aware_accepted_buy_new_weight"] == 0.08
    assert member["phase29_l19_lot_resolution"]["one_lot_fallback_applied"] is True
    assert member["phase29_l19_lot_resolution"]["final_allocated_quantity"] == 100


def test_phase29_l21s_one_lot_fallback_blocks_cash_shortfall() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[_lot_rebatch_member("11110", priority=1, request=0.03, accepted=0.03)],
        lot_feasibility_rows=[{"symbol": "11110", "lot_feasible": True, "broker_eligible": True, "minimum_executable_weight": 0.08}],
        target_gross_exposure=0.05,
        single_name_cap=0.18,
    )
    member = result["members"][0]

    assert member["target_weight"] == 0.0
    assert member["lot_first_rebatch_skip_reason"] == "minimum_lot_exceeds_remaining_budget"


def test_phase29_l21s_one_lot_fallback_blocks_safety_hard_violation() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[_lot_rebatch_member("11110", priority=1, request=0.03, accepted=0.03)],
        lot_feasibility_rows=[
            {
                "symbol": "11110",
                "lot_feasible": False,
                "broker_eligible": True,
                "minimum_executable_weight": 0.30,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX",
                    "safety_hard_cap_preserved": False,
                    "one_lot_feasibility_status": "FAIL_CLOSED",
                },
            }
        ],
        target_gross_exposure=1.0,
        single_name_cap=0.18,
    )
    member = result["members"][0]

    assert member["target_weight"] == 0.0
    assert member["lot_first_rebatch_skip_reason"] == "minimum_lot_exceeds_safety_hard_cap"


def test_phase30_ak9r19_final_pc_budget_uses_canonical_discrete_requirement_for_60310_equivalent() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[_lot_rebatch_member("60310", priority=1, request=0.041667, accepted=0.041667)],
        lot_feasibility_rows=[
            _ak9r19_discrete_requirement_row(
                "60310",
                one_lot_weight=0.034743,
                executable_quantity=100,
                continuous_target_weight=0.041667,
            )
        ],
        target_gross_exposure=0.03511875,
        single_name_cap=0.18,
    )
    member = result["members"][0]
    iteration = result["evidence"]["phase29_l19_allocation_iterations"][0]

    assert member["target_weight"] == 0.034743
    assert member["lot_aware_accepted_buy_new_weight"] == 0.034743
    assert member["lot_first_rebatch_skip_reason"] == ""
    assert iteration["budget_requirement_source"] == "CANONICAL_DISCRETE_EXECUTABLE_REQUIREMENT"
    assert iteration["canonical_discrete_executable_required_weight"] == 0.034743
    assert result["evidence"]["capital_conservation"]["status"] == "PASS"
    assert result["evidence"]["capital_conservation"]["allocated_increment_weight"] == 0.034743
    assert result["evidence"]["capital_conservation"]["residual_cash_weight"] == 0.000376


def test_phase30_ak9r19_true_remaining_budget_shortfall_still_fails_closed() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[_lot_rebatch_member("60310", priority=1, request=0.041667, accepted=0.041667)],
        lot_feasibility_rows=[
            _ak9r19_discrete_requirement_row(
                "60310",
                one_lot_weight=0.034743,
                executable_quantity=100,
                continuous_target_weight=0.041667,
            )
        ],
        target_gross_exposure=0.034,
        single_name_cap=0.18,
    )
    member = result["members"][0]
    skipped = result["evidence"]["skipped"][0]

    assert member["target_weight"] == 0.0
    assert member["lot_first_rebatch_skip_reason"] == "minimum_lot_exceeds_remaining_budget"
    assert skipped["required_weight"] == 0.034743
    assert skipped["budget_requirement_source"] == "CANONICAL_DISCRETE_EXECUTABLE_REQUIREMENT"


def test_phase30_ak9r19_canonical_discrete_requirement_requires_complete_authority() -> None:
    incomplete = _ak9r19_discrete_requirement_row(
        "60310",
        one_lot_weight=0.034743,
        executable_quantity=100,
        continuous_target_weight=0.041667,
    )
    incomplete["phase29_l19_lot_resolution"].pop("executable_quantity_delta")
    incomplete["phase29_l19_lot_resolution"].pop("normal_lot_quantity")
    result = apply_lot_aware_final_reallocation(
        members=[_lot_rebatch_member("60310", priority=1, request=0.041667, accepted=0.041667)],
        lot_feasibility_rows=[incomplete],
        target_gross_exposure=0.03511875,
        single_name_cap=0.18,
    )
    skipped = result["evidence"]["skipped"][0]

    assert result["members"][0]["target_weight"] == 0.0
    assert skipped["required_weight"] == 0.041667
    assert skipped["budget_requirement_source"] == "DRAFT_CONTINUOUS_ALLOCATION"


def test_phase30_ak9r19_tampered_post_trade_weight_fails_closed_to_draft_requirement() -> None:
    tampered = _ak9r19_discrete_requirement_row(
        "60310",
        one_lot_weight=0.034743,
        executable_quantity=100,
        continuous_target_weight=0.041667,
    )
    tampered["phase29_l19_lot_resolution"]["post_trade_weight"] = 0.05
    result = apply_lot_aware_final_reallocation(
        members=[_lot_rebatch_member("60310", priority=1, request=0.041667, accepted=0.041667)],
        lot_feasibility_rows=[tampered],
        target_gross_exposure=0.03511875,
        single_name_cap=0.18,
    )
    skipped = result["evidence"]["skipped"][0]

    assert result["members"][0]["target_weight"] == 0.0
    assert skipped["required_weight"] == 0.041667
    assert skipped["budget_requirement_source"] == "DRAFT_CONTINUOUS_ALLOCATION"


def test_phase30_ak9r19_higher_priority_discrete_requirement_consumes_budget_first() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            _lot_rebatch_member("11110", priority=1, request=0.04, accepted=0.04),
            _lot_rebatch_member("22220", priority=2, request=0.04, accepted=0.04),
        ],
        lot_feasibility_rows=[
            _ak9r19_discrete_requirement_row("11110", one_lot_weight=0.03, executable_quantity=100, continuous_target_weight=0.04),
            _ak9r19_discrete_requirement_row("22220", one_lot_weight=0.03, executable_quantity=100, continuous_target_weight=0.04),
        ],
        target_gross_exposure=0.055,
        single_name_cap=0.18,
    )
    by_code = {row["security_code"]: row for row in result["members"]}

    assert by_code["11110"]["target_weight"] == 0.03
    assert by_code["22220"]["target_weight"] == 0.0
    assert result["evidence"]["phase29_l19_allocation_iterations"][0]["symbol"] == "11110"
    assert result["evidence"]["skipped"][0]["symbol"] == "22220"
    assert result["evidence"]["skipped"][0]["required_weight"] == 0.03


def test_phase29_l21s_capacity_severe_and_buy_quality_reject_remain_zero(tmp_path: Path) -> None:
    payload = _build_l16_payload(
        tmp_path,
        opportunity_rows=[
            _l16_opportunity("11110", 1, price=1000.0, rolling_value=1_000_000, prior_exit_business_date="2026-07-09"),
            _l16_opportunity("22220", 2, price=1000.0, rolling_value=1_000_000_000),
        ],
        buy_quality_rows=[
            _l16_quality("11110", "FULL_ALLOCATION_ELIGIBLE"),
            _l16_quality("22220", "REJECT"),
        ],
        exposure=0.36,
        cap=0.18,
        portfolio_equity=1_000_000,
    )
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert by_code["11110"]["semantic_buy_type"] == "REENTRY"
    assert by_code["11110"]["reentry_recovery_reason"] == "reentry_capacity_unavailable"
    assert by_code["11110"]["target_weight"] == 0.0
    assert by_code["22220"]["membership_intent"] == "EXCLUDE"
    assert by_code["22220"]["target_weight"] == 0.0


def test_phase29_l21s_reentry_pass_keeps_semantic_when_one_lot_fallback_applies() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            {
                **_lot_rebatch_member("23880", priority=1, request=0.03, accepted=0.03),
                "semantic_buy_type": "REENTRY",
                "prior_exit_business_date": "2026-07-09",
                "reentry_recovery_status": "PASS",
            }
        ],
        lot_feasibility_rows=[
            {
                "symbol": "23880",
                "intent_type": "BUY_NEW",
                "lot_feasible": True,
                "broker_eligible": True,
                "minimum_executable_weight": 0.08,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "CAP_CONSTRAINED_LOT_EXECUTABLE",
                    "semantic_type": "REENTRY",
                    "one_lot_quantity": 100,
                    "one_lot_fallback_applied": True,
                    "safety_hard_cap_preserved": True,
                },
            }
        ],
        target_gross_exposure=0.5,
        single_name_cap=0.18,
    )
    member = result["members"][0]

    assert member["semantic_buy_type"] == "REENTRY"
    assert member["prior_exit_business_date"] == "2026-07-09"
    assert member["target_weight"] == 0.08
    assert member["lot_aware_accepted_buy_new_weight"] == 0.08


def test_phase29_l21s_buy_add_one_lot_fallback_preserves_add_semantics() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            {**_lot_rebatch_add_member("94320", priority=1, current_weight=0.10, request=0.03, accepted=0.03), "semantic_buy_type": "BUY_ADD"},
        ],
        lot_feasibility_rows=[
            {
                "symbol": "94320",
                "intent_type": "BUY_ADD",
                "lot_feasible": True,
                "broker_eligible": True,
                "minimum_executable_weight": 0.08,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "CAP_CONSTRAINED_LOT_EXECUTABLE",
                    "semantic_type": "BUY_ADD",
                    "one_lot_quantity": 100,
                    "one_lot_fallback_applied": True,
                    "safety_hard_cap_preserved": True,
                },
            }
        ],
        target_gross_exposure=0.5,
        single_name_cap=0.18,
    )
    member = result["members"][0]

    assert member["pm_action"] == "ADD"
    assert member["semantic_buy_type"] == "BUY_ADD"
    assert member["target_weight"] == 0.10
    assert member["lot_aware_accepted_incremental_weight"] == 0.0
    assert member["phase29_l19_lot_resolution"]["second_lot_plus_promotion"]["promotion_candidate"] is False


def test_phase32_f_buy_wait_existing_add_preserves_baseline_and_blocks_increment() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            {
                **_lot_rebatch_add_member("94320", priority=1, current_weight=0.10, request=0.03, accepted=0.03),
                "semantic_buy_type": "BUY_ADD",
                "quality_action": "BUY_WAIT",
                "quality_allocation_adjustment": 0.0,
            },
        ],
        lot_feasibility_rows=[
            {
                "symbol": "94320",
                "intent_type": "BUY_ADD",
                "lot_feasible": True,
                "broker_eligible": True,
                "minimum_executable_weight": 0.02,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "CAP_CONSTRAINED_LOT_EXECUTABLE",
                    "semantic_type": "BUY_ADD",
                    "one_lot_quantity": 100,
                    "safety_hard_cap_preserved": True,
                },
            }
        ],
        target_gross_exposure=0.5,
        single_name_cap=0.18,
    )
    member = result["members"][0]

    assert member["pm_action"] == "ADD"
    assert member["target_weight"] == 0.10
    assert member["target_membership"] is True
    assert member["lot_aware_accepted_incremental_weight"] == 0.0
    assert member["phase29_l19_lot_resolution"]["requested_incremental_weight"] == 0.0
    assert "BUY_QUALITY_BLOCKS_INCREMENTAL_ADD" in result["reason_codes"]


def test_phase32_f_reduced_existing_add_remains_positive_when_quality_authorizes_increment() -> None:
    result = apply_lot_aware_final_reallocation(
        members=[
            {
                **_lot_rebatch_add_member("94320", priority=1, current_weight=0.10, request=0.03, accepted=0.03),
                "semantic_buy_type": "BUY_ADD",
                "quality_action": "REDUCED_ALLOCATION_ONLY",
                "quality_allocation_adjustment": 0.5,
            },
        ],
        lot_feasibility_rows=[
            {
                "symbol": "94320",
                "intent_type": "BUY_ADD",
                "lot_feasible": True,
                "broker_eligible": True,
                "minimum_executable_weight": 0.02,
                "phase29_l19_lot_resolution": {
                    "boundary_classification": "CAP_CONSTRAINED_LOT_EXECUTABLE",
                    "semantic_type": "BUY_ADD",
                    "one_lot_quantity": 100,
                    "safety_hard_cap_preserved": True,
                },
            }
        ],
        target_gross_exposure=0.5,
        single_name_cap=0.18,
    )
    member = result["members"][0]

    assert member["pm_action"] == "ADD"
    assert member["target_weight"] > member["current_weight"]
    assert member["lot_aware_accepted_incremental_weight"] > 0.0
    assert member["phase29_l19_lot_resolution"]["semantic_type"] == "BUY_ADD"


def test_phase29_l16_canonical_add_is_not_reentry_and_remains_positive_when_low_price_capped(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.02, "position_campaign_id": "campaign-11110", "reference_price": 10.0, "rolling_median_traded_value_20": 1_000_000_000}],
        pm_rows=[{**_pm_row("11110", "ADD"), "position_campaign_id": "campaign-11110", "reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"]}],
        opportunity_rows=[
            _opportunity_row(
                "11110",
                1,
                0.82,
                position_campaign_id="campaign-11110",
                expected_edge_baseline_score=0.70,
                expected_edge_baseline_business_date="2026-07-14",
                expected_edge_baseline_campaign_id="campaign-11110",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
                reference_price=10.0,
                rolling_median_traded_value_20=1_000_000_000,
            )
        ],
        exposure=0.4,
        cap=0.4,
    )
    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")

    assert member["semantic_buy_type"] == "BUY_ADD"
    assert member["add_allocation_eligibility_status"] == "PASS"
    assert member["target_weight"] == 0.05
    assert member["target_weight"] > member["current_weight"]
    assert member["accepted_incremental_weight"] > 0
    assert member["reentry_cooldown_status"] == "NOT_APPLICABLE"
    assert member["reentry_semantic_state"] == "REENTRY_NOT_APPLICABLE"
    assert member["target_weight_authority"]["semantic_reentry_authority"]["semantic_result"]["semantic_buy_type"] == "BUY_ADD"


def test_phase29_l16_sell_reduce_exit_low_price_paths_remain_independent(tmp_path: Path) -> None:
    payload = _build_l16_payload(
        tmp_path,
        current_rows=[
            {"position_id": "current-11110", "security_code": "11110", "current_weight": 0.20, "reference_price": 5.0},
            {"position_id": "current-22220", "security_code": "22220", "current_weight": 0.10, "reference_price": 5.0},
        ],
        pm_rows=[
            {**_pm_row("11110", "REDUCE"), "intensity": "LIGHT"},
            _pm_row("22220", "EXIT"),
        ],
        opportunity_rows=[],
        exposure=0.6,
        cap=0.2,
        portfolio_equity=1_000_000,
    )
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert by_code["11110"]["pm_action"] == "REDUCE"
    assert 0.0 < by_code["11110"]["target_weight"] < by_code["11110"]["current_weight"]
    assert by_code["11110"]["semantic_buy_type"] == "NOT_APPLICABLE"
    assert by_code["11110"]["reentry_semantic_state"] == "REENTRY_NOT_APPLICABLE"
    assert by_code["22220"]["pm_action"] == "EXIT"
    assert by_code["22220"]["target_weight"] == 0.0


def test_phase29_l16_liquidity_cap_uses_current_equity_not_fixed_one_million(tmp_path: Path) -> None:
    low_equity = _build_l16_payload(
        tmp_path / "low_equity",
        opportunity_rows=[_l16_opportunity("11110", 1, price=100.0, rolling_value=10_000_000)],
        exposure=0.18,
        cap=0.18,
        portfolio_equity=1_000_000,
    )
    high_equity = _build_l16_payload(
        tmp_path / "high_equity",
        opportunity_rows=[_l16_opportunity("11110", 1, price=100.0, rolling_value=10_000_000)],
        exposure=0.18,
        cap=0.18,
        portfolio_equity=2_000_000,
    )

    low = low_equity["portfolio_members"][0]
    high = high_equity["portfolio_members"][0]
    assert low["liquidity_capacity_cap_weight"] == 0.10
    assert high["liquidity_capacity_cap_weight"] == 0.05
    assert low["target_weight"] == 0.10
    assert high["target_weight"] == 0.05


def test_phase22_e_fixture_shadow_reads_draft_and_rejects_production(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    payload = load_portfolio_construction_fixture(result.artifact_path)

    assert payload["schema_version"] == "portfolio_construction.v1"
    with pytest.raises(PortfolioConstructionConsumerError):
        load_portfolio_construction_fixture(result.artifact_path, for_production=True)


def _produce(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return produce_portfolio_construction_artifact(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_source_summary(tmp_path, "construction_policy_config"),
        output_path=default_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _lot_rebatch_member(code: str, *, priority: int, request: float, accepted: float) -> dict[str, object]:
    return {
        "security_code": code,
        "symbol": code,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "construction_priority": priority,
        "requested_buy_new_weight": request,
        "accepted_buy_new_weight": accepted,
        "target_weight": accepted,
        "target_membership": accepted > 0,
        "target_weight_authority": {},
        "target_weight_resolution": {"status": "PASS", "resolved_weight": accepted, "adjustments": []},
        "runtime_opportunity_score": max(0.0, 1.0 - priority / 100.0),
    }


def _lot_rebatch_add_member(code: str, *, priority: int, current_weight: float, request: float, accepted: float) -> dict[str, object]:
    target = round(current_weight + accepted, 6)
    return {
        "security_code": code,
        "symbol": code,
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "construction_priority": priority,
        "current_weight": current_weight,
        "current_quantity": 100,
        "requested_incremental_weight": request,
        "accepted_incremental_weight": accepted,
        "add_allocation_eligibility_status": "PASS",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "target_weight": target,
        "target_membership": True,
        "target_weight_authority": {},
        "target_weight_resolution": {"status": "PASS", "resolved_weight": target, "adjustments": []},
        "runtime_opportunity_score": max(0.0, 1.0 - priority / 100.0),
    }


def _ak9r19_discrete_requirement_row(
    code: str,
    *,
    one_lot_weight: float,
    executable_quantity: int,
    continuous_target_weight: float,
) -> dict[str, object]:
    return {
        "symbol": code,
        "intent_type": "BUY_NEW",
        "lot_feasible": True,
        "broker_eligible": True,
        "minimum_executable_weight": one_lot_weight,
        "phase29_l19_lot_resolution": {
            "boundary_classification": "CAP_CONSTRAINED_LOT_EXECUTABLE",
            "one_lot_quantity": 100,
            "one_lot_weight": one_lot_weight,
            "one_lot_notional": round(one_lot_weight * 1_000_000, 2),
            "one_lot_feasibility_status": "PASS",
            "one_lot_fallback_applied": False,
            "normal_lot_quantity": executable_quantity,
            "executable_quantity_delta": executable_quantity,
            "continuous_target_weight": continuous_target_weight,
            "continuous_target_notional": round(continuous_target_weight * 1_000_000, 2),
            "post_trade_weight": round(one_lot_weight * (executable_quantity / 100), 6),
            "strategy_cap_weight": 0.18,
            "safety_hard_cap_weight": 0.25,
            "safety_hard_cap_preserved": True,
        },
    }


def _build_l16_payload(
    tmp_path: Path,
    *,
    opportunity_rows: list[dict[str, object]],
    exposure: float,
    cap: float,
    portfolio_equity: float,
    current_rows: list[dict[str, object]] | None = None,
    pm_rows: list[dict[str, object]] | None = None,
    buy_quality_rows: list[dict[str, object]] | None = None,
    risk_pacing_intent: str | None = "NORMAL_DEPLOYMENT",
) -> dict[str, object]:
    codes = [str(row["code"]) for row in opportunity_rows]
    candidate_rows = [
        {
            "candidate_id": f"candidate-{code}",
            "code": code,
            "candidate_order": index,
            "candidate_score": 1.0 - index / 100.0,
            "universe_eligible": True,
        }
        for index, code in enumerate(codes, start=1)
    ]
    current_summary = _source_summary(tmp_path, "current", rows=current_rows or [])
    current_summary = PortfolioConstructionSourceSummary(
        status=current_summary.status,
        business_date=current_summary.business_date,
        feature_date=current_summary.feature_date,
        source_ref=current_summary.source_ref,
        source_hash=current_summary.source_hash,
        rows=current_summary.rows,
        summary={
            "kind": "current",
            "row_count": len(current_rows or []),
            "portfolio_total_equity": portfolio_equity,
            "portfolio_value": portfolio_equity,
        },
    )
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, rows=pm_rows or [], producer_status="PASS"),
        candidate_summary=_source_summary(tmp_path, "candidate", rows=candidate_rows),
        opportunity_summary=_source_summary(tmp_path, "opportunity", rows=opportunity_rows),
        current_portfolio_summary=current_summary,
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(
            tmp_path,
            target_position_count=max(len(opportunity_rows), len(current_rows or []), 1),
            exposure=exposure,
            cap=cap,
            risk_pacing_intent=risk_pacing_intent,
        ),
        buy_quality_summary=_source_summary(tmp_path, "buy_quality", rows=buy_quality_rows or []),
    )
    return payload


def _l16_opportunity(code: str, rank: int, *, price: float, rolling_value: float | None, **extra: object) -> dict[str, object]:
    row = _opportunity_row(
        code,
        rank,
        0.20,
        reference_price=price,
        minimum_tick=1.0,
        trend_close_over_ma_20d=1.01,
        price_momentum_return_20d=0.01,
        corporate_action_status="PASS",
        **extra,
    )
    if rolling_value is not None:
        row["rolling_median_traded_value_20"] = rolling_value
    return row


def _l16_quality(code: str, action: str) -> dict[str, object]:
    return {
        "quality_decision_id": f"quality-{code}",
        "symbol": code,
        "quality_score": 0.85,
        "quality_band": "HIGH",
        "quality_action": action,
        "quality_status": "PASS",
        "quality_reason_codes": ["phase29_l16_fixture"],
        "quality_allocation_adjustment": 1.0,
        "policy_version": "phase29_l16_test",
        "PIT_status": "PASS",
    }


def _candidate_rows() -> list[dict[str, object]]:
    return [
        {"candidate_id": "candidate-6758", "code": "6758", "candidate_order": 1, "candidate_score": 0.88, "universe_eligible": True},
        {"candidate_id": "candidate-6098", "code": "6098", "candidate_order": 2, "candidate_score": 0.9, "universe_eligible": True},
        {"candidate_id": "candidate-9999", "code": "9999", "candidate_order": 3, "candidate_score": 0.7, "universe_eligible": False},
    ]


def _opportunity_rows() -> list[dict[str, object]]:
    return [
        {"opportunity_id": "opportunity-6098", "code": "6098", "opportunity_rank": 1, "expected_edge_score": 0.92},
        {"opportunity_id": "opportunity-6758", "code": "6758", "opportunity_rank": 2, "expected_edge_score": 0.86},
        {"opportunity_id": "opportunity-9999", "code": "9999", "opportunity_rank": 3, "expected_edge_score": 0.71},
    ]


def _current_rows() -> list[dict[str, object]]:
    return [
        {"position_id": "current-7203", "security_code": "7203"},
        {"position_id": "current-6758", "security_code": "6758"},
        {"position_id": "current-9984", "security_code": "9984"},
        {"position_id": "current-8306", "security_code": "8306"},
    ]


def _pm_rows() -> list[dict[str, object]]:
    return [
        {"position_id": "pm-7203", "security_code": "7203", "action": "HOLD", "intensity": "NONE", "confidence": 0.8, "uncertainty": "UPSTREAM_REVIEW_REQUIRED", "reason_codes": ["HOLD_BY_STRONG_CONTINUATION"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""},
        {"position_id": "pm-6758", "security_code": "6758", "action": "ADD", "intensity": "UNRESOLVED", "confidence": 0.7, "uncertainty": "UPSTREAM_REVIEW_REQUIRED", "reason_codes": ["ADD_BY_STRONG_TREND_AND_RANK"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""},
        {"position_id": "pm-9984", "security_code": "9984", "action": "REDUCE", "intensity": "MEDIUM", "confidence": 0.6, "uncertainty": "UPSTREAM_REVIEW_REQUIRED", "reason_codes": ["REDUCE_BY_PEAK_DRAWDOWN_WARNING"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""},
        {"position_id": "pm-8306", "security_code": "8306", "action": "EXIT", "intensity": "NONE", "confidence": 0.9, "uncertainty": "UPSTREAM_REVIEW_REQUIRED", "reason_codes": ["EXIT_BY_HARD_STOP"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""},
    ]


def _current_rows_without_sell_intents() -> list[dict[str, object]]:
    return [
        {"position_id": "current-7203", "security_code": "7203", "current_weight": 0.05},
        {"position_id": "current-6758", "security_code": "6758", "current_weight": 0.05},
    ]


def _pm_rows_without_sell_intents() -> list[dict[str, object]]:
    return [
        {"position_id": "pm-7203", "security_code": "7203", "action": "HOLD", "intensity": "NONE", "confidence": 0.8, "uncertainty": "LOW", "reason_codes": ["HOLD_FIXTURE"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""},
        {"position_id": "pm-6758", "security_code": "6758", "action": "HOLD", "intensity": "NONE", "confidence": 0.8, "uncertainty": "LOW", "reason_codes": ["HOLD_FIXTURE"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""},
    ]


def _candidate_summary(tmp_path: Path, *, business_date: str = "2026-07-15", feature_date: str = "2026-07-15") -> PortfolioConstructionSourceSummary:
    return _source_summary(tmp_path, "candidate", rows=_candidate_rows(), business_date=business_date, feature_date=feature_date)


def _opportunity_summary(tmp_path: Path, *, business_date: str = "2026-07-15", feature_date: str = "2026-07-15") -> PortfolioConstructionSourceSummary:
    return _source_summary(tmp_path, "opportunity", rows=_opportunity_rows(), business_date=business_date, feature_date=feature_date)


def _l21t_ak_opportunity(code: str, rank: int, score: float, **extra: object) -> dict[str, object]:
    return {
        "opportunity_id": f"opportunity-{code}",
        "code": code,
        "opportunity_rank": rank,
        "runtime_opportunity_score": score,
        "expected_edge_score": score,
        "canonical_score_field": "runtime_opportunity_score",
        "score_semantic_role": "uncalibrated_relative_model_score",
        "calibration_applied": False,
        "economic_units_available": False,
        "no_buy_reason": "",
        **extra,
    }


def _l21t_ak_quality(code: str, action: str, *, adjustment: float = 1.0) -> dict[str, object]:
    return {
        "quality_decision_id": f"quality-{code}",
        "symbol": code,
        "quality_score": 0.84,
        "quality_band": "HIGH",
        "quality_action": action,
        "quality_status": "PASS",
        "quality_reason_codes": ["phase29_l21t_ak_fixture"],
        "quality_allocation_adjustment": adjustment,
        "relative_opportunity_quality": 0.75,
        "policy_version": "phase29_l21t_ak_test",
        "PIT_status": "PASS",
    }


def _l21t_am_opportunity_row(code: str, rank: int, score: float, **extra: object) -> dict[str, object]:
    return {
        "opportunity_id": f"opportunity-{code}",
        "code": code,
        "symbol": code,
        "buy_rank": rank,
        "runtime_opportunity_score": score,
        "expected_edge_score": score,
        "score_semantic_role": "uncalibrated_relative_model_score",
        "calibration_applied": False,
        "economic_units_available": False,
        "no_buy_reason": "",
        **extra,
    }


def _l21t_am_actual_adapter_opportunity_summary(
    tmp_path: Path,
    rows: list[dict[str, object]],
    *,
    metadata: dict[str, object] | None = None,
) -> PortfolioConstructionSourceSummary:
    semantic_metadata = {
        "canonical_score_field": "runtime_opportunity_score",
        "score_semantic_role": "uncalibrated_relative_model_score",
        "calibration_applied": False,
        "economic_units_available": False,
    }
    if metadata is not None:
        semantic_metadata = metadata
    opportunity_path = tmp_path / "opportunity_rankings.json"
    _write_json(
        opportunity_path,
        {
            "schema_version": "runtime_v2_opportunity_ranking_v1",
            "business_date": "2026-07-15",
            "feature_date": "2026-07-15",
            **semantic_metadata,
            "rankings": rows,
        },
    )
    return _pc_summary(_ai_output_summary(opportunity_path, business_date="2026-07-15"), "2026-07-15")


def _build_l21t_am_payload_via_actual_adapter(
    tmp_path: Path,
    *,
    opportunity_rows: list[dict[str, object]],
    buy_quality_rows: list[dict[str, object]],
    opportunity_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    opportunity_summary = _l21t_am_actual_adapter_opportunity_summary(
        tmp_path,
        opportunity_rows,
        metadata=opportunity_metadata,
    )
    candidate_rows = [
        {
            "candidate_id": f"candidate-{row['code']}",
            "code": row["code"],
            "candidate_order": index,
            "candidate_score": 1.0 - index / 100.0,
            "universe_eligible": True,
        }
        for index, row in enumerate(opportunity_rows, start=1)
    ]
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, rows=[], producer_status="PASS"),
        candidate_summary=_source_summary(tmp_path, "candidate", rows=candidate_rows),
        opportunity_summary=opportunity_summary,
        current_portfolio_summary=_source_summary(tmp_path, "current", rows=[]),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(
            tmp_path,
            target_position_count=len(opportunity_rows),
            exposure=0.9,
            cap=0.2,
        ),
        buy_quality_summary=_source_summary(tmp_path, "buy_quality", rows=buy_quality_rows),
    )
    return payload


def _build_l21t_ak_payload(
    tmp_path: Path,
    *,
    opportunity_rows: list[dict[str, object]],
    buy_quality_rows: list[dict[str, object]],
    opportunity_summary_metadata: dict[str, object] | None = None,
    target_position_count: int | None = None,
    current_rows: list[dict[str, object]] | None = None,
    pm_rows: list[dict[str, object]] | None = None,
    strategy_intelligence_artifact_path: Path | None = None,
) -> dict[str, object]:
    metadata = {
        "canonical_score_field": "runtime_opportunity_score",
        "score_semantic_role": "uncalibrated_relative_model_score",
        "calibration_applied": False,
        "economic_units_available": False,
    }
    if opportunity_summary_metadata is not None:
        metadata = opportunity_summary_metadata
    candidate_rows = [
        {
            "candidate_id": f"candidate-{row['code']}",
            "code": row["code"],
            "candidate_order": index,
            "candidate_score": 1.0 - index / 100.0,
            "universe_eligible": True,
        }
        for index, row in enumerate(opportunity_rows, start=1)
    ]
    base_opportunity = _source_summary(tmp_path, "opportunity", rows=opportunity_rows)
    opportunity_summary = PortfolioConstructionSourceSummary(
        status=base_opportunity.status,
        business_date=base_opportunity.business_date,
        feature_date=base_opportunity.feature_date,
        source_ref=base_opportunity.source_ref,
        source_hash=base_opportunity.source_hash,
        rows=base_opportunity.rows,
        summary={**metadata, "kind": "opportunity", "row_count": len(opportunity_rows)},
    )
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, rows=pm_rows or [], producer_status="PASS"),
        candidate_summary=_source_summary(tmp_path, "candidate", rows=candidate_rows),
        opportunity_summary=opportunity_summary,
        current_portfolio_summary=_source_summary(tmp_path, "current", rows=current_rows or []),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(
            tmp_path,
            target_position_count=target_position_count or len(opportunity_rows),
            exposure=0.9,
            cap=0.2,
        ),
        buy_quality_summary=_source_summary(tmp_path, "buy_quality", rows=buy_quality_rows),
        strategy_intelligence_artifact_path=strategy_intelligence_artifact_path,
    )
    return payload


def _write_phase30_ai_strategy_intelligence(tmp_path: Path, tiers_by_symbol: dict[str, str]) -> Path:
    rows = {}
    for symbol, tier in tiers_by_symbol.items():
        entry_action = "BUY_NEW_REDUCED_ONLY" if tier == "CAUTION_CONTINUATION" else "BUY_NEW_ALLOWED"
        rows[symbol] = {
            "symbol": symbol,
            "eligibility": {"status": "PASS", "disqualifying_facts": []},
            "continuation_quality": {"status": "PASS"},
            "downside_risk": {"status": "PASS"},
            "expected_edge": {"calibration_status": "UNCALIBRATED", "economic_units_available": False},
            "entry_admission": {
                "entry_state": "CONTINUATION_WITH_CAUTION" if tier == "CAUTION_CONTINUATION" else "HEALTHY_CONTINUATION_ENTRY",
                "admission_action": entry_action,
                "evidence_sufficiency": "SUFFICIENT",
            },
            "selection_quality_comparator": {
                "schema_version": "selection_quality_comparator.v1",
                "tier": tier,
                "reason_codes": [f"test_{tier.lower()}"],
                "evidence_sufficiency": "SUFFICIENT",
                "rank_score_role": "SUPPORTING_NOT_HARD_REJECTION_AUTHORITY",
                "expected_edge_role": "UNCALIBRATED_SUPPORTING",
                "score_only_hard_rejection_retired": True,
                "below_top20_only_hard_rejection_retired": True,
                "not_action_authority": True,
                "future_information_used": False,
            },
            "lifecycle_context": {"current_position_state": "NO_POSITION"},
            "profit_protection_evidence": {},
            "provenance": {"future_information_used": False},
        }
    payload = {
        "schema_version": strategy_intelligence.SCHEMA_VERSION,
        "semantic_version": strategy_intelligence.SEMANTIC_VERSION,
        "business_date": "2026-07-15",
        "as_of_business_date": "2026-07-15",
        "generated_at": "2026-07-15T00:00:00+00:00",
        "pit_boundary": {"market_data_as_of": "2026-07-15", "future_information_used": False},
        "producer_result_status": "PASS",
        "runtime_consumer_eligibility": "ELIGIBLE",
        "production_consumer_connected": True,
        "shadow_only": False,
        "production_authority": False,
        "reason_codes": [],
        "future_information_used": False,
        "historical_outcome_used_as_runtime_input": False,
        "test_result_used_as_strategy_input": False,
        "historical_outcome_used_for_production_parameter_selection": False,
        "symbol_intelligence": rows,
        "shadow_decision_comparison": {},
    }
    payload["artifact_hash"] = strategy_intelligence.strategy_intelligence_hash(payload)
    path = tmp_path / "phase30_ai_strategy_intelligence.json"
    _write_json(path, payload)
    return path


def _current_summary(tmp_path: Path, *, business_date: str = "2026-07-15", feature_date: str = "2026-07-15") -> PortfolioConstructionSourceSummary:
    return _source_summary(tmp_path, "current", rows=_current_rows(), business_date=business_date, feature_date=feature_date)


def _source_summary(
    tmp_path: Path,
    kind: str,
    *,
    status: str = "PASS",
    rows: list[dict[str, object]] | None = None,
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
) -> PortfolioConstructionSourceSummary:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / f"{kind}_source.json"
    payload = {"kind": kind, "business_date": business_date, "feature_date": feature_date, "status": status, "rows": rows or []}
    _write_json(path, payload)
    return PortfolioConstructionSourceSummary(
        status=status,
        business_date=business_date,
        feature_date=feature_date,
        source_ref=str(path),
        source_hash=_sha256_file(path),
        rows=tuple(rows or []),
        summary={"kind": kind, "row_count": len(rows or [])},
    )


def _policy_config_summary(
    tmp_path: Path,
    *,
    target_position_count: int,
    exposure: float,
    cap: float,
    risk_pacing_intent: str | None = "NORMAL_DEPLOYMENT",
) -> PortfolioConstructionSourceSummary:
    base = _source_summary(tmp_path, "construction_policy_config")
    return PortfolioConstructionSourceSummary(
        status=base.status,
        business_date=base.business_date,
        feature_date=base.feature_date,
        source_ref=base.source_ref,
        source_hash=base.source_hash,
        rows=base.rows,
        summary={
            "kind": "construction_policy_config",
            "target_position_count": target_position_count,
            "target_gross_exposure_ratio": exposure,
            "target_gross_exposure": exposure,
            "cash_reserve_ratio": round(1.0 - exposure, 6),
            "cash_reserve": round(1.0 - exposure, 6),
            "single_name_weight_cap": cap,
            "deployment_posture": "DEPLOY" if exposure > 0 else "PAUSE",
            **(
                {
                    "risk_pacing_intent": risk_pacing_intent,
                    "risk_pacing_mode": "AUTHORITATIVE",
                    "risk_pacing_as_of": "2026-07-15",
                    "risk_pacing_reason_codes": [f"TEST_{risk_pacing_intent}"],
                    "risk_pacing_evidence_completeness": "COMPLETE" if risk_pacing_intent != "PRESERVE_OPTIONALITY" else "INSUFFICIENT",
                    "risk_pacing_authority": {
                        "owner": "PORTFOLIO_POLICY",
                        "mode": "AUTHORITATIVE",
                        "authoritative_consumer": "PORTFOLIO_CONSTRUCTION",
                        "authoritative_consumer_count": 1,
                        "shadow_path_removed": True,
                    },
                    "risk_pacing_component_evidence": {
                        "schema_version": "risk_pacing_component_evidence.v1",
                        "future_information_used": False,
                        "historical_outcome_used": False,
                        "evidence_feedback_used": False,
                    },
                }
                if risk_pacing_intent
                else {}
            ),
        },
    )


def _write_position_management(tmp_path: Path, rows: list[dict[str, object]] | None = None, producer_status: str = "REVIEW_REQUIRED") -> Path:
    rows = _pm_rows() if rows is None else rows
    source = tmp_path / "pm_source.json"
    _write_json(source, {"rows": rows})
    payload = {
        "schema_version": position_management.SCHEMA_VERSION,
        "producer_version": "phase22_d_position_management_producer.v1",
        "business_date": "2026-07-15",
        "as_of": "2026-07-15T00:00:00+00:00",
        "feature_date": "2026-07-15",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": producer_status,
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "positions": rows,
        "position_count": len(rows),
        "action_taxonomy": ["ADD", "EXIT", "HOLD", "REDUCE"],
        "intensity_taxonomy": ["LIGHT", "MEDIUM", "NONE", "STRONG", "UNRESOLVED"],
        "quantity_decided": False,
        "minimum_holding_decided": False,
        "cooldown_decided": False,
        "reason_codes": [] if producer_status == "PASS" else ["upstream_review_required:SOURCE_NOT_ELIGIBLE"],
        "upstream_artifacts": {},
        "accepted_generation_reference": {},
        "model_reference": {},
        "scaler_reference": {},
        "source_artifacts": [{"role": "pm_source", "path": str(source), "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "pm_source", "path": str(source), "sha256": _sha256_file(source)}],
        "temporal_safety": {"point_in_time": True, "future_leakage_used": False, "feature_date_lte_business_date": True, "implicit_latest_fallback_used": False, "previous_day_pm_artifact_copied": False},
        "production_consumer_connected": False,
        "existing_pm_authority_active": True,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    payload["artifact_hash"] = position_management.position_management_hash(payload)
    path = tmp_path / "position_management.json"
    _write_json(path, payload)
    return path


def _build_d28_payload(
    tmp_path: Path,
    *,
    current_rows: list[dict[str, object]],
    pm_rows: list[dict[str, object]],
    opportunity_rows: list[dict[str, object]],
    exposure: float,
    cap: float,
) -> dict[str, object]:
    codes = [str(row["code"]) for row in opportunity_rows]
    candidate_rows = [
        {
            "candidate_id": f"candidate-{code}",
            "code": code,
            "candidate_order": index,
            "candidate_score": 1.0 - index / 100.0,
            "universe_eligible": True,
        }
        for index, code in enumerate(codes, start=1)
    ]
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, rows=pm_rows),
        candidate_summary=_source_summary(tmp_path, "candidate", rows=candidate_rows),
        opportunity_summary=_source_summary(tmp_path, "opportunity", rows=opportunity_rows),
        current_portfolio_summary=_source_summary(tmp_path, "current", rows=current_rows),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_policy_config_summary(
            tmp_path,
            target_position_count=len(opportunity_rows),
            exposure=exposure,
            cap=cap,
        ),
    )
    return payload


def _pm_row(code: str, action: str) -> dict[str, object]:
    return {
        "position_id": f"pm-{code}",
        "security_code": code,
        "action": action,
        "intensity": "UNRESOLVED" if action == "ADD" else ("LIGHT" if action == "REDUCE" else "NONE"),
        "confidence": 0.8,
        "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
        "reason_codes": [f"{action}_FIXTURE"],
        "lifecycle_reference": "",
        "opportunity_reference": code,
        "market_context_reference": "",
        "corporate_event_reference": "",
        "portfolio_policy_reference": "",
    }


def _opportunity_row(code: str, rank: int, score: float, **extra: object) -> dict[str, object]:
    return {
        "opportunity_id": f"opportunity-{code}",
        "code": code,
        "opportunity_rank": rank,
        "expected_edge_score": score,
        **extra,
    }


def _eligible_add_opportunity(code: str, rank: int, score: float) -> dict[str, object]:
    return _opportunity_row(
        code,
        rank,
        score,
        expected_edge_baseline_score=score - 0.1,
        expected_edge_baseline_business_date="2026-07-14",
        incremental_investment_value_state="POSITIVE",
        opportunity_cost_status="PASS",
        campaign_continuation_status="PASS",
        no_loss_averaging_status="PASS",
    )


def _broker_fixture_listed_info(code: str, product_category: str) -> dict[str, object]:
    return {
        "code": code,
        "market": "TSE",
        "product_category": product_category,
        "security_type": product_category,
        "current_listed": True,
    }


def _write_portfolio_policy(tmp_path: Path) -> Path:
    config_path = tmp_path / "portfolio_policy_config.json"
    config_payload = {
        "intent_policy": {
            "risk_posture": "BALANCED",
            "entry_posture": "MAINTAIN",
            "position_count_posture": "MAINTAIN",
            "cash_posture": "MAINTAIN",
            "exposure_posture": "MAINTAIN",
            "position_management_bias": "NEUTRAL",
        },
        "single_name_weight_cap": 0.18,
    }
    _write_json(config_path, config_payload)
    result = portfolio_policy.produce_portfolio_policy_artifact(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        candidate_summary=_pp_summary(tmp_path, "candidate"),
        opportunity_summary=_pp_summary(tmp_path, "opportunity"),
        current_portfolio_summary={},
        current_cash_summary={},
        current_exposure_summary={},
        policy_config=PortfolioPolicyConfig(
            config_version="phase22_e_fixture_policy_config.v1",
            config_source=str(config_path),
            intent_policy=config_payload["intent_policy"],
            single_name_weight_cap=0.18,
            single_name_weight_cap_source=f"{config_path}#single_name_weight_cap",
        ),
        output_path=tmp_path / "portfolio_policy.json",
    )
    return Path(result.artifact_path)


def _write_resolved_portfolio_policy(tmp_path: Path) -> Path:
    path = _write_portfolio_policy(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(
        {
            "producer_result_status": "PASS",
            "target_position_count_resolution": "PASS",
            "target_position_count": 3,
            "target_gross_exposure_ratio_resolution": "PASS",
            "target_gross_exposure_ratio": 0.54,
            "target_gross_exposure": 0.54,
            "cash_reserve_ratio_resolution": "PASS",
            "cash_reserve_ratio": 0.46,
            "cash_reserve": 0.46,
            "single_name_weight_cap": 0.18,
            "deployment_posture": "BALANCED_DEPLOYMENT",
            "reason_codes": [],
        }
    )
    payload["artifact_hash"] = portfolio_policy.portfolio_policy_hash(payload)
    _write_json(path, payload)
    return path


def _policy_artifact_summary(path: Path) -> PortfolioConstructionSourceSummary:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return PortfolioConstructionSourceSummary(
        "PASS",
        str(payload["business_date"]),
        str(payload["feature_date"]),
        str(path),
        _sha256_file(path),
        (),
        payload,
    )


def _pp_summary(tmp_path: Path, kind: str) -> PortfolioPolicyInputSummary:
    path = tmp_path / f"pp_{kind}_summary.json"
    payload = {"kind": kind, "business_date": "2026-07-15", "feature_date": "2026-07-15"}
    _write_json(path, payload)
    return PortfolioPolicyInputSummary("PASS", "2026-07-15", "2026-07-15", payload, str(path), _sha256_file(path))


def _write_market_context(
    tmp_path: Path,
    *,
    schema_version: str = market_context.SCHEMA_VERSION,
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
) -> Path:
    source = tmp_path / "market_source.parquet"
    source.write_text("market-source", encoding="utf-8")
    payload = {
        "schema_version": schema_version,
        "producer_version": "phase22_a_market_context_producer.v1",
        "business_date": business_date,
        "as_of": f"{business_date}T00:00:00+00:00",
        "feature_date": feature_date,
        "trend_regime": "RANGE",
        "trend_strength": 0.0,
        "market_breadth": "NEUTRAL",
        "volatility_regime": "NORMAL",
        "sector_dispersion": "MODERATE",
        "market_quality_state": "HEALTHY_EXPANSION",
        "market_quality_reason_codes": ["MARKET_QUALITY_HEALTHY"],
        "market_quality_evidence_completeness": "COMPLETE",
        "market_quality_component_evidence": {
            "schema_version": "market_quality_component_evidence.v1",
            "future_information_used": False,
            "historical_outcome_used": False,
        },
        "market_quality_as_of": feature_date,
        "confidence": 0.0,
        "uncertainty": "THRESHOLD_OR_SOURCE_REVIEW_REQUIRED",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "reason_codes": ["market_context_threshold_config_required"],
        "source_artifacts": [{"role": "jquants_daily_quotes", "path": str(source), "required": True, "exists": True}],
        "source_hashes": [{"role": "jquants_daily_quotes", "path": str(source), "sha256": market_context.sha256_file(source)}],
        "temporal_safety": {"point_in_time": feature_date <= business_date, "future_leakage_used": feature_date > business_date, "feature_date_lte_business_date": feature_date <= business_date},
        "metrics": {},
        "threshold_policy": {"status": "CONFIG_REQUIRED", "source": "", "values": None},
    }
    payload["artifact_hash"] = market_context.market_context_hash(payload)
    path = tmp_path / f"market_context_{business_date}_{feature_date}_{schema_version}.json"
    _write_json(path, payload)
    return path


def _write_corporate_event(tmp_path: Path, *, business_date: str = "2026-07-15", feature_date: str = "2026-07-15") -> Path:
    source = tmp_path / "corporate_source.parquet"
    source.write_text("corporate-source", encoding="utf-8")
    payload = {
        "schema_version": corporate_event.SCHEMA_VERSION,
        "producer_version": "phase22_aa_corporate_event_producer.v1",
        "business_date": business_date,
        "as_of": f"{business_date}T00:00:00+00:00",
        "feature_date": feature_date,
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "coverage_status": "PARTIAL",
        "events": [],
        "event_count": 0,
        "event_taxonomy": sorted(corporate_event.EVENT_TYPES),
        "event_identity": {
            "algorithm": "sha256",
            "fields": ["security_code", "event_type", "announcement_date", "effective_date", "availability_date", "source_reference", "revision_id"],
            "row_order_dependent": False,
        },
        "reason_codes": ["corporate_event_source_coverage_incomplete"],
        "source_artifacts": [{"role": "jquants_listed_issues", "path": str(source), "required": True, "exists": True}],
        "source_hashes": [{"role": "jquants_listed_issues", "path": str(source), "sha256": corporate_event.sha256_file(source)}],
        "temporal_safety": {"point_in_time": feature_date <= business_date, "future_leakage_used": feature_date > business_date, "feature_date_lte_business_date": feature_date <= business_date},
        "no_event_semantics": {
            "empty_events_meaning": "NO_EVENTS_ONLY_WHEN_SOURCE_COVERAGE_AVAILABLE_AND_PRODUCER_PASS",
            "unknown_event_state_when_source_missing": False,
        },
    }
    payload["artifact_hash"] = corporate_event.corporate_event_hash(payload)
    path = tmp_path / f"corporate_event_{business_date}_{feature_date}.json"
    _write_json(path, payload)
    return path


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
