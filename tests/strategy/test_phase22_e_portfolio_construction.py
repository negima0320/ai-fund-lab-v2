from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import corporate_event, market_context, portfolio_policy, position_management
from ai_fund_lab_v2.strategy.portfolio_construction import (
    PortfolioConstructionConsumerError,
    PortfolioConstructionSchemaError,
    PortfolioConstructionSourceSummary,
    _positive_increment_over_target,
    apply_lot_aware_final_reallocation,
    build_portfolio_construction_payload,
    default_runtime_artifact_path,
    load_portfolio_construction_fixture,
    portfolio_construction_hash,
    produce_portfolio_construction_artifact,
    validate_portfolio_construction_artifact,
    verify_source_hashes,
)
from ai_fund_lab_v2.strategy.portfolio_policy import PortfolioPolicyConfig, PortfolioPolicyInputSummary


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
    assert result["evidence"]["promoted"][0]["reason"] == "minimum_executable_lot_authorized_by_pc"
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

    assert by_code["11110"]["target_weight"] == 0.09
    assert by_code["11110"]["lot_aware_accepted_incremental_weight"] == 0.04
    assert by_code["22220"]["target_weight"] == 0.05
    assert result["evidence"]["skipped"][0]["symbol"] == "22220"


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

    assert by_code["11110"]["lot_aware_accepted_incremental_weight"] == 0.10
    assert by_code["22220"]["lot_aware_accepted_buy_new_weight"] == 0.0


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


def test_phase29_l19_lot_boundary_materializes_without_weakening_buy_add(tmp_path: Path) -> None:
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
                    "safety_hard_cap_weight": 0.25,
                    "maximum_strategy_feasible_lots": 2,
                    "maximum_safety_feasible_lots": 7,
                    "executable_quantity_delta": 0,
                },
            }
        ],
        target_gross_exposure=1.0,
        single_name_cap=0.18,
    )
    member = result["members"][0]
    skip = result["evidence"]["skipped"][0]

    assert member["pm_action"] == "ADD"
    assert member["target_weight"] == 0.136879
    assert member["phase29_l19_lot_resolution"]["blocked_reason"] == "minimum_lot_exceeds_concentration_cap"
    assert skip["blocked_reason"] == "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX"
    assert result["evidence"]["phase29_l19_cap_constrained_lot_floor_enabled"] is True
    assert result["evidence"]["phase29_l19_strategy_safety_cap_separated"] is True
    assert result["evidence"]["phase29_l19_candidate_exhaustion_status"] == "EXHAUSTED_TO_CASH"


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
            _l16_opportunity("11110", 1, price=5.0, rolling_value=1_000_000_000, prior_exit_business_date="2026-07-14"),
            _l16_opportunity("22220", 2, price=5.0, rolling_value=1_000_000_000, prior_exit_business_date="2026-07-09"),
            _l16_opportunity("33330", 11, price=5.0, rolling_value=1_000_000_000, prior_exit_business_date="2026-07-09"),
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
    assert by_code["11110"]["target_weight"] == 0.0
    assert by_code["22220"]["semantic_buy_type"] == "REENTRY"
    assert by_code["22220"]["reentry_cooldown_status"] == "PASS"
    assert by_code["22220"]["reentry_recovery_status"] == "PASS"
    assert by_code["22220"]["target_weight"] == 0.05
    assert by_code["33330"]["reentry_recovery_status"] == "FAIL_CLOSED"
    assert by_code["33330"]["reentry_recovery_reason"] == "reentry_rank_above_threshold"
    assert by_code["33330"]["target_weight"] == 0.0


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
        "target_weight": target,
        "target_membership": True,
        "target_weight_authority": {},
        "target_weight_resolution": {"status": "PASS", "resolved_weight": target, "adjustments": []},
        "runtime_opportunity_score": max(0.0, 1.0 - priority / 100.0),
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


def _policy_config_summary(tmp_path: Path, *, target_position_count: int, exposure: float, cap: float) -> PortfolioConstructionSourceSummary:
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
