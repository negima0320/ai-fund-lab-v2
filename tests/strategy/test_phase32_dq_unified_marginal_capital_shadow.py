from __future__ import annotations

import pytest

from ai_fund_lab_v2.strategy import marginal_capital_value
from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


def test_phase32_dq_shadow_preserves_action_identity_and_separates_value_from_feasibility() -> None:
    result = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[
            _buy_new("7203", rank=4),
            _reentry("8306", rank=2),
            _buy_add("9432", current_weight=0.17, accepted=0.0),
        ],
        competitors=[
            _production_competitor("NEW_BUY", "7203", accepted=0.04),
            _production_competitor("NEW_BUY", "8306", accepted=0.03),
            _production_competitor("ADD", "9432", accepted=0.0, reason_codes=["CONCENTRATION_BLOCK"]),
        ],
        cash_evidence=_cash_evidence(["VALID_POLICY_RESERVE"]),
        market_candidate_cash_interaction={"capital_competition_winner_type": "NEW_BUY", "capital_competition_winner_symbol": "7203"},
        incremental_budget_evidence={"available_incremental_budget": 0.2},
        risk_pacing_evidence={"risk_pacing_intent": "NORMAL_DEPLOYMENT", "risk_pacing_evidence_completeness": "COMPLETE"},
    )

    assert result["authoritative_consumer_count"] == 0
    assert result["shadow_only"] is True
    assert result["production_allocation_consumer"] is False
    assert result["contract_flags"]["reentry_semantic_identity_preserved"] is True
    assert result["contract_flags"]["add_campaign_identity_preserved"] is True
    assert result["contract_flags"]["value_eligibility_feasibility_separated"] is True
    assert result["contract_flags"]["cash_optionality_competitor_present"] is True
    assert result["contract_flags"]["historical_outcome_used"] is False
    assert result["contract_flags"]["future_information_used"] is False

    by_type = {row["competitor_type"]: row for row in result["competitor_rows"]}
    by_symbol = {row["symbol"]: row for row in result["competitor_rows"] if row.get("symbol")}
    assert set(by_type) == {"BUY_NEW_NEXT_LOT", "BUY_ADD_NEXT_LOT", "CASH_OPTIONALITY"}
    assert by_symbol["8306"]["competitor_type"] == "BUY_NEW_NEXT_LOT"
    assert by_symbol["8306"]["semantic_buy_type"] == "BUY_NEW"
    assert by_symbol["8306"]["reentry_evidence"]["recent_exit_guard_state"] == "EXPIRED_NOT_CURRENT_DECISION_AUTHORITY"
    assert by_type["BUY_ADD_NEXT_LOT"]["position_campaign_id"] == "pc-9432-0001"
    assert by_type["BUY_ADD_NEXT_LOT"]["source_pm_decision_id"] == "pm-2026-07-15-9432-add"
    assert by_type["BUY_ADD_NEXT_LOT"]["marginal_desirability"]["state"] in {"HIGH_VALUE", "MEDIUM_VALUE"}
    assert by_type["BUY_ADD_NEXT_LOT"]["portfolio_risk_cost"]["state"] == "ACCEPTABLE"
    assert by_type["BUY_ADD_NEXT_LOT"]["structured_headroom"]["state"] == "HEADROOM_AVAILABLE"
    assert by_type["BUY_ADD_NEXT_LOT"]["executable_capital_winner"] is False
    assert by_type["BUY_ADD_NEXT_LOT"]["campaign_graduation_shadow_state"] == "ADD_CONSIDERED"
    assert by_type["CASH_OPTIONALITY"]["execution_feasibility"]["state"] == "FEASIBLE"
    assert result["opportunity_strength_ranking"]["winner"]["competitor_type"] in {
        "BUY_NEW_NEXT_LOT",
        "BUY_ADD_NEXT_LOT",
        "CASH_OPTIONALITY",
    }
    assert result["executable_capital_ranking"]["winner"]["competitor_type"] != "BUY_ADD_NEXT_LOT"
    assert result["production_comparison"]["stage_b_divergence_class"]
    assert result["shadow_arbitration"]["action_type_fixed_preference"] == "NONE"
    assert result["shadow_arbitration"]["pnl_calibrated_scalar_introduced"] is False


def test_phase32_dq_shadow_flags_incomplete_evidence_without_creating_confident_high_value() -> None:
    result = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[
            {
                "security_code": "9432",
                "symbol": "9432",
                "current_position": True,
                "membership_intent": "RETAIN",
                "pm_action": "ADD",
                "current_weight": 0.05,
                "current_quantity": 100,
                "requested_incremental_weight": 0.03,
                "source_pm_decision_ref": "",
            }
        ],
        competitors=[_production_competitor("ADD", "9432", accepted=0.0, reason_codes=["ADD_INSUFFICIENT_EVIDENCE"])],
        cash_evidence=_cash_evidence(["NO_VALID_COMPETITOR"]),
        market_candidate_cash_interaction={"capital_competition_winner_type": "CASH_OPTIONALITY", "capital_competition_winner_symbol": ""},
    )

    add = next(row for row in result["competitor_rows"] if row["competitor_type"] == "BUY_ADD_NEXT_LOT")
    assert add["evidence_completeness"]["state"] == "INCOMPLETE"
    assert "source_pm_decision_id" in add["evidence_completeness"]["missing_inputs"]
    assert add["marginal_desirability"]["state"] == "HIGH_VALUE_EVIDENCE_INCOMPLETE"
    assert result["opportunity_strength_ranking"]["winner"]["competitor_type"] == "BUY_ADD_NEXT_LOT"
    assert result["executable_capital_ranking"]["winner"]["competitor_type"] == "CASH_OPTIONALITY"
    assert result["production_comparison"]["later_outcome_used"] is False


def test_phase32_dq_pc_integration_is_shadow_only_and_preserves_production_competition() -> None:
    members = [
        _buy_new("7203", rank=1, accepted=0.04),
        _reentry("8306", rank=2, accepted=0.03),
        _buy_add("9432", current_weight=0.04, accepted=0.02),
    ]
    result = build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.8,
        total_target_weight=0.09,
        business_date="2026-07-15",
        incremental_budget_evidence={"available_incremental_budget": 0.4},
        risk_pacing_evidence={"risk_pacing_intent": "NORMAL_DEPLOYMENT", "risk_pacing_evidence_completeness": "COMPLETE"},
    )

    competitors = {(row["competitor_type"], row["symbol"]): row for row in result["competitors"]}
    assert competitors[("NEW_BUY", "7203")]["accepted_weight"] == 0.04
    assert competitors[("NEW_BUY", "8306")]["accepted_weight"] == 0.03
    assert competitors[("ADD", "9432")]["accepted_weight"] == 0.02
    shadow = result["unified_marginal_capital_shadow"]
    assert shadow["authoritative_consumer_count"] == 0
    assert result["authority"]["unified_marginal_capital_shadow_authoritative_consumer_count"] == 0
    assert result["authority"]["unified_marginal_capital_shadow_production_consumer"] is False
    assert {row["competitor_type"] for row in shadow["competitor_rows"]} == {
        "BUY_NEW_NEXT_LOT",
        "BUY_ADD_NEXT_LOT",
        "CASH_OPTIONALITY",
    }
    assert "opportunity_strength_ranking" in shadow
    assert "executable_capital_ranking" in shadow
    assert shadow["schema_version"] == "unified_marginal_capital_shadow.v2"
    assert shadow["production_comparison"]["two_stage_divergence_class"]
    assert shadow["contract_flags"]["executable_capital_ranking_present"] is True


def test_phase32_dy_non_authoritative_shadow_failure_does_not_replace_pc_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    members = [
        _buy_new("7203", rank=1, accepted=0.04),
        _reentry("8306", rank=2, accepted=0.03),
        _buy_add("9432", current_weight=0.04, accepted=0.02),
    ]
    normal = build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.8,
        total_target_weight=0.09,
        business_date="2026-07-15",
        incremental_budget_evidence={"available_incremental_budget": 0.4},
        risk_pacing_evidence={
            "risk_pacing_intent": "NORMAL_DEPLOYMENT",
            "risk_pacing_evidence_completeness": "COMPLETE",
        },
    )

    def raise_shadow_error(**_: object) -> dict[str, object]:
        raise NameError("name '_two_stage_divergence_class' is not defined")

    monkeypatch.setattr(
        marginal_capital_value,
        "build_unified_marginal_capital_shadow",
        raise_shadow_error,
    )
    isolated = build_capital_competition_framework(
        members=members,
        target_gross_exposure=0.8,
        total_target_weight=0.09,
        business_date="2026-07-15",
        incremental_budget_evidence={"available_incremental_budget": 0.4},
        risk_pacing_evidence={
            "risk_pacing_intent": "NORMAL_DEPLOYMENT",
            "risk_pacing_evidence_completeness": "COMPLETE",
        },
    )

    assert isolated["schema_version"] == "portfolio_construction.capital_competition.v1"
    assert isolated["competitors"] == normal["competitors"]
    assert isolated["market_candidate_cash_interaction"] == normal["market_candidate_cash_interaction"]
    assert isolated["canonical_deployment_set"] == normal["canonical_deployment_set"]
    assert isolated["capital_competition_winner_type"] == normal["capital_competition_winner_type"]
    assert isolated["capital_competition_winner_symbol"] == normal["capital_competition_winner_symbol"]
    assert isolated["authority"]["unified_marginal_capital_shadow_authoritative_consumer_count"] == 0
    assert isolated["authority"]["unified_marginal_capital_shadow_production_consumer"] is False

    diagnostic = isolated["unified_marginal_capital_shadow"]
    assert diagnostic["schema_version"] == "unified_marginal_capital_shadow_error.v1"
    assert diagnostic["status"] == "SHADOW_ERROR"
    assert diagnostic["component"] == "unified_marginal_capital_shadow"
    assert diagnostic["exception_type"] == "NameError"
    assert diagnostic["exception_message"] == "name '_two_stage_divergence_class' is not defined"
    assert diagnostic["shadow_schema"] == "unified_marginal_capital_shadow.v2"
    assert diagnostic["authoritative_consumer_count"] == 0
    assert diagnostic["production_allocation_consumer"] is False
    assert diagnostic["production_ordering_consumer"] is False
    assert diagnostic["production_sizing_consumer"] is False
    assert diagnostic["runtime_planning_consumer"] is False
    assert diagnostic["canonical_production_artifact_survives_shadow_failure"] is True


def test_phase32_dw_cap_applied_false_does_not_create_concentration_block() -> None:
    add = _buy_add("9432", current_weight=0.04, accepted=0.0)
    add["target_weight_authority"] = {"single_name_weight_cap": 0.18}
    add["target_weight_resolution"] = {"cap_applied": False, "reason": "lot_aware_final_reallocation"}
    add["phase29_l19_lot_resolution"] = {
        "one_lot_quantity": 100,
        "one_lot_notional": 90000,
        "final_quantity_delta": 0,
        "post_trade_weight": 0.13,
        "one_lot_feasibility_status": "PASS",
    }

    result = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[add, _buy_new("7203", rank=1)],
        competitors=[
            _production_competitor(
                "ADD",
                "9432",
                accepted=0.0,
                reason_codes=["ADD_NO_POSITIVE_DELTA", "CAP_METADATA_PRESENT_BUT_NOT_APPLIED"],
            ),
            _production_competitor("NEW_BUY", "7203", accepted=0.04),
        ],
        cash_evidence=_cash_evidence(["VALID_POLICY_RESERVE"]),
        market_candidate_cash_interaction={"capital_competition_winner_type": "NEW_BUY", "capital_competition_winner_symbol": "7203"},
    )

    row = next(row for row in result["competitor_rows"] if row["competitor_type"] == "BUY_ADD_NEXT_LOT")
    assert row["structured_headroom"]["strategy_cap_applied"] is False
    assert row["structured_headroom"]["state"] == "HEADROOM_AVAILABLE"
    assert row["portfolio_risk_cost"]["state"] == "ACCEPTABLE"


def test_phase32_dw_real_strategy_and_safety_cap_blocks_are_structured() -> None:
    strategy_block = _buy_add("9432", current_weight=0.18, accepted=0.0)
    strategy_block["target_weight_authority"] = {"single_name_weight_cap": 0.18}
    strategy_block["target_weight_resolution"] = {"cap_applied": True}

    safety_block = _buy_add("9984", current_weight=0.24, accepted=0.0)
    safety_block["target_weight_authority"] = {"single_name_weight_cap": 0.3}
    safety_block["phase29_l19_lot_resolution"] = {
        "one_lot_quantity": 100,
        "one_lot_notional": 90000,
        "final_quantity_delta": 0,
        "post_trade_weight": 0.26,
        "one_lot_feasibility_status": "FAIL_CLOSED",
        "safety_hard_cap": 0.25,
        "blocked_reason": "minimum_lot_exceeds_safety_hard_cap",
    }

    result = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[strategy_block, safety_block],
        competitors=[
            _production_competitor("ADD", "9432", accepted=0.0, reason_codes=["CONCENTRATION_BLOCK"]),
            _production_competitor("ADD", "9984", accepted=0.0, reason_codes=["ADD_SAFETY_CAP_BOUND"]),
        ],
        cash_evidence=_cash_evidence(["VALID_POLICY_RESERVE"]),
        market_candidate_cash_interaction={"capital_competition_winner_type": "CASH_OPTIONALITY", "capital_competition_winner_symbol": ""},
    )

    by_symbol = {row["symbol"]: row for row in result["competitor_rows"]}
    assert by_symbol["9432"]["structured_headroom"]["state"] == "STRATEGY_CAP_BLOCKED"
    assert by_symbol["9432"]["portfolio_risk_cost"]["state"] == "STRATEGY_CAP_BLOCKED"
    assert by_symbol["9984"]["structured_headroom"]["state"] == "SAFETY_HARD_CAP_BLOCKED"
    assert by_symbol["9984"]["portfolio_risk_cost"]["state"] == "BLOCKED_BY_SAFETY"


def test_phase32_dw_complete_executable_add_can_win_stage_b_without_production_effect() -> None:
    add = _buy_add("9432", current_weight=0.04, accepted=0.02)
    add["strategy_intelligence_add_worthiness_state"] = "ADD_ALLOWED"
    add["entry_admission_action"] = "ADD_ALLOWED"
    result = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[
            add,
            _buy_new("7203", rank=4, accepted=0.04),
        ],
        competitors=[
            _production_competitor("ADD", "9432", accepted=0.02, reason_codes=["ADD_SELECTED"]),
            _production_competitor("NEW_BUY", "7203", accepted=0.04),
        ],
        cash_evidence=_cash_evidence(["VALID_POLICY_RESERVE"]),
        market_candidate_cash_interaction={"capital_competition_winner_type": "NEW_BUY", "capital_competition_winner_symbol": "7203"},
    )

    winner = result["executable_capital_ranking"]["winner"]
    assert winner["competitor_type"] == "BUY_ADD_NEXT_LOT"
    assert winner["portfolio_risk_cost"] == "ACCEPTABLE"
    assert result["authoritative_consumer_count"] == 0
    assert result["production_allocation_consumer"] is False


def test_phase32_ec_add_strength_shadow_can_create_positive_increment_target_without_production_consumer() -> None:
    add = _buy_add("9432", current_weight=0.04, accepted=0.0)
    add["target_weight"] = 0.04
    add["requested_incremental_weight"] = 0.0
    add["accepted_incremental_weight"] = 0.0
    add["lot_aware_accepted_incremental_weight"] = 0.0
    add["entry_admission_action"] = "ADD_ALLOWED"
    add["phase29_l19_lot_resolution"]["post_trade_weight"] = 0.055
    add["phase29_l19_lot_resolution"]["one_lot_notional"] = 15000
    add["phase29_l19_lot_resolution"]["final_quantity_delta"] = 100
    add["add_investment_evidence"] = _add_investment_evidence("9432")

    result = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[add, _buy_new("7203", rank=4, accepted=0.04)],
        competitors=[
            _production_competitor("ADD", "9432", accepted=0.0, reason_codes=["ADD_TARGET_WEIGHT_UNCHANGED"]),
            _production_competitor("NEW_BUY", "7203", accepted=0.04),
        ],
        cash_evidence=_cash_evidence(["VALID_POLICY_RESERVE"]),
        market_candidate_cash_interaction={"capital_competition_winner_type": "NEW_BUY", "capital_competition_winner_symbol": "7203"},
    )

    row = next(row for row in result["competitor_rows"] if row["competitor_type"] == "BUY_ADD_NEXT_LOT")
    authority = row["add_strength_to_increment_target_authority"]
    assert authority["authority_type"] == "ADD_STRENGTH_TO_INCREMENT_TARGET_AUTHORITY"
    assert authority["owner"] == "PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY"
    assert authority["increment_demand_status"] == "POSITIVE_INCREMENT_DEMAND"
    assert authority["proposed_incremental_target_weight"] == 0.015
    assert authority["proposed_refreshed_target_weight"] == 0.055
    assert authority["fixed_add_bonus"] is False
    assert authority["pm_add_alone_creates_positive_demand"] is False
    assert authority["historical_pnl_used_for_increment_magnitude"] is False
    assert authority["authoritative_consumer_count"] == 0
    ec_eligible = result["ec_strength_increment_executable_capital_ranking"]["eligible_rows"]
    assert any(row["competitor_type"] == "BUY_ADD_NEXT_LOT" and row["symbol"] == "9432" for row in ec_eligible)
    assert result["authoritative_consumer_count"] == 0
    assert result["production_allocation_consumer"] is False
    assert result["production_sizing_consumer"] is False


def test_phase32_ec_unknown_incremental_value_does_not_become_positive_add_demand() -> None:
    add = _buy_add("9432", current_weight=0.04, accepted=0.0)
    add["target_weight"] = 0.04
    add["requested_incremental_weight"] = 0.0
    add["accepted_incremental_weight"] = 0.0
    add["lot_aware_accepted_incremental_weight"] = 0.0
    add["phase29_l19_lot_resolution"]["post_trade_weight"] = 0.055
    add["add_investment_evidence"] = _add_investment_evidence("9432", incremental_state="UNKNOWN")

    result = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[add, _buy_new("7203", rank=4, accepted=0.04)],
        competitors=[
            _production_competitor("ADD", "9432", accepted=0.0, reason_codes=["ADD_TARGET_WEIGHT_UNCHANGED"]),
            _production_competitor("NEW_BUY", "7203", accepted=0.04),
        ],
        cash_evidence=_cash_evidence(["VALID_POLICY_RESERVE"]),
        market_candidate_cash_interaction={"capital_competition_winner_type": "NEW_BUY", "capital_competition_winner_symbol": "7203"},
    )

    row = next(row for row in result["competitor_rows"] if row["competitor_type"] == "BUY_ADD_NEXT_LOT")
    authority = row["add_strength_to_increment_target_authority"]
    assert authority["evidence_tier"] == "INSUFFICIENT"
    assert authority["increment_demand_status"] == "NO_POSITIVE_DEMAND"
    assert authority["proposed_incremental_target_weight"] == 0.0
    assert "incremental_value_not_positive:UNKNOWN" in authority["reason_codes"]
    assert result["contract_flags"]["add_strength_to_increment_target_authoritative_consumer_count"] == 0


def test_phase32_ee_unified_next_capital_unit_record_is_shadow_only_and_separates_raw_from_normalized() -> None:
    add = _buy_add("9432", current_weight=0.04, accepted=0.02)
    add["add_investment_evidence"] = _add_investment_evidence("9432")
    result = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[add, _buy_new("7203", rank=1, accepted=0.04), _reentry("8306", rank=2, accepted=0.03)],
        competitors=[
            _production_competitor("ADD", "9432", accepted=0.02, reason_codes=["ADD_SELECTED"]),
            _production_competitor("NEW_BUY", "7203", accepted=0.04),
            _production_competitor("NEW_BUY", "8306", accepted=0.03),
        ],
        cash_evidence=_cash_evidence(["VALID_POLICY_RESERVE"]),
        market_candidate_cash_interaction={"capital_competition_winner_type": "NEW_BUY", "capital_competition_winner_symbol": "7203"},
    )

    ee = result["unified_next_capital_unit_evidence"]
    assert ee["authority_type"] == "UNIFIED_NEXT_CAPITAL_UNIT_SHADOW_AUTHORITY"
    assert ee["owner"] == "PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY"
    assert ee["shadow_only"] is True
    assert ee["authoritative_consumer_count"] == 0
    assert ee["production_allocation_consumer"] is False
    assert ee["fixed_action_bonus"] == {
        "BUY_ADD_NEXT_LOT": False,
        "BUY_NEW_NEXT_LOT": False,
        "REENTRY_NEXT_LOT": False,
        "CASH_OPTIONALITY": False,
    }
    assert ee["raw_evidence_and_normalized_value_separated"] is True
    assert result["contract_flags"]["unified_next_capital_unit_authoritative_consumer_count"] == 0
    assert result["contract_flags"]["action_type_fixed_preference"] == "NONE"

    by_type = {row["competitor_type"]: row["unified_next_capital_unit_record"] for row in result["competitor_rows"]}
    add_record = by_type["BUY_ADD_NEXT_LOT"]
    assert add_record["action_specific_semantics"]["semantic"] == "increase_existing_exposure"
    assert add_record["action_specific_semantics"]["fake_buy_new_semantics_used"] is False
    assert add_record["raw_pit_evidence"]["current_weight"] == 0.04
    assert add_record["raw_pit_evidence"]["next_lot_notional"] == 90000
    assert add_record["normalized_comparison"]["evidence_completeness_class"] == "COMPLETE"
    assert add_record["normalized_comparison"]["marginal_investment_value_state"] == "POSITIVE"
    by_symbol = {row["symbol"]: row["unified_next_capital_unit_record"] for row in result["competitor_rows"] if row.get("symbol")}
    assert by_symbol["8306"]["action_specific_semantics"]["semantic"] == "open_new_exposure"
    assert by_symbol["8306"]["action_specific_semantics"]["artificial_new_penalty_used"] is False
    assert by_type["CASH_OPTIONALITY"]["action_specific_semantics"]["cash_optionality_preserved"] is True


def test_phase32_ee_add_unknown_and_weakening_do_not_become_positive_by_representation() -> None:
    add = _buy_add("9432", current_weight=0.04, accepted=0.0)
    add["target_weight"] = 0.04
    add["requested_incremental_weight"] = 0.0
    add["accepted_incremental_weight"] = 0.0
    add["lot_aware_accepted_incremental_weight"] = 0.0
    add["expected_edge_improvement_state"] = "WEAKENING"
    add["add_investment_evidence"] = _add_investment_evidence("9432", incremental_state="UNKNOWN")
    add["add_investment_evidence"]["expected_edge"]["state"] = "WEAKENING"

    result = marginal_capital_value.build_unified_marginal_capital_shadow(
        business_date="2026-07-15",
        members=[add, _buy_new("7203", rank=1, accepted=0.04)],
        competitors=[
            _production_competitor("ADD", "9432", accepted=0.0, reason_codes=["ADD_TARGET_WEIGHT_UNCHANGED"]),
            _production_competitor("NEW_BUY", "7203", accepted=0.04),
        ],
        cash_evidence=_cash_evidence(["VALID_POLICY_RESERVE"]),
        market_candidate_cash_interaction={"capital_competition_winner_type": "NEW_BUY", "capital_competition_winner_symbol": "7203"},
    )

    add_row = next(row for row in result["competitor_rows"] if row["competitor_type"] == "BUY_ADD_NEXT_LOT")
    record = add_row["unified_next_capital_unit_record"]
    assert add_row["add_strength_to_increment_target_authority"]["increment_demand_status"] == "NO_POSITIVE_DEMAND"
    assert record["normalized_comparison"]["marginal_investment_value_state"] != "POSITIVE"
    assert record["normalized_comparison"]["evidence_completeness_class"] in {"BLOCKED", "INSUFFICIENT", "PARTIAL"}
    assert result["unified_next_capital_unit_evidence"]["authoritative_consumer_count"] == 0
    assert result["production_allocation_consumer"] is False


def _buy_new(code: str, *, rank: int, accepted: float = 0.04) -> dict[str, object]:
    return {
        "security_code": code,
        "symbol": code,
        "business_date": "2026-07-15",
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "semantic_buy_type": "BUY_NEW",
        "source_candidate_id": f"candidate-{code}",
        "source_opportunity_id": f"opportunity-{code}",
        "input_opportunity_rank": rank,
        "runtime_opportunity_score": 0.8,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_score": 0.72,
        "entry_admission_action": "BUY_NEW_ALLOWED",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "requested_buy_new_weight": accepted,
        "accepted_buy_new_weight": accepted,
        "lot_aware_accepted_buy_new_weight": accepted,
        "target_weight": accepted,
        "phase29_l19_lot_resolution": {
            "one_lot_quantity": 100,
            "one_lot_notional": 100000,
            "final_quantity_delta": 100,
            "one_lot_feasibility_status": "PASS",
        },
    }


def _reentry(code: str, *, rank: int, accepted: float = 0.03) -> dict[str, object]:
    row = _buy_new(code, rank=rank, accepted=accepted)
    row.update(
        {
            "semantic_buy_type": "BUY_NEW",
            "ownership_lineage": "PRIOR_EXIT_LINEAGE_PRESENT",
            "recent_exit_guard_state": "EXPIRED_NOT_CURRENT_DECISION_AUTHORITY",
            "recent_exit_guard_status": "PASS",
            "reentry_semantic_state": "REENTRY_NOT_APPLICABLE",
            "reentry_semantic_status": "NOT_APPLICABLE",
            "reentry_recovery_status": "NOT_APPLICABLE",
            "prior_exit_business_date": "2026-07-10",
            "business_days_since_exit": 3,
            "reentry_reason_codes": ["REENTRY_CURRENT_DECISION_SEMANTIC_REMOVED"],
        }
    )
    return row


def _buy_add(code: str, *, current_weight: float, accepted: float) -> dict[str, object]:
    return {
        "security_code": code,
        "symbol": code,
        "business_date": "2026-07-15",
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "semantic_buy_type": "BUY_ADD",
        "position_campaign_id": f"pc-{code}-0001",
        "current_position_campaign_id": f"pc-{code}-0001",
        "source_pm_decision_ref": f"pm-2026-07-15-{code}-add",
        "source_pm_reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"],
        "current_quantity": 100,
        "current_weight": current_weight,
        "target_weight": current_weight + accepted,
        "requested_incremental_weight": 0.03,
        "accepted_incremental_weight": accepted,
        "lot_aware_accepted_incremental_weight": accepted,
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_score": 0.7,
        "entry_admission_action": "ADD_REDUCED_ONLY",
        "entry_admission_state": "CONTINUATION_WITH_CAUTION",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "expected_edge_improvement_state": "IMPROVING",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "strategy_intelligence_add_worthiness_state": "ADD_REDUCED_ONLY",
        "same_campaign_continuation_status": "PASS",
        "strategy_intelligence_continuation_quality_status": "PASS",
        "strategy_intelligence_downside_risk_status": "PASS",
        "strategy_intelligence_campaign_age_business_days": 12,
        "input_opportunity_rank": 3,
        "runtime_opportunity_score": 0.75,
        "phase29_l19_lot_resolution": {
            "one_lot_quantity": 100,
            "one_lot_notional": 90000,
            "final_quantity_delta": 100 if accepted > 0 else 0,
            "one_lot_feasibility_status": "PASS" if accepted > 0 else "BLOCKED",
            "blocked_reason": "" if accepted > 0 else "CONCENTRATION_BLOCK",
            "post_trade_weight": current_weight + max(accepted, 0.0),
            "safety_hard_cap": 0.25,
        },
        "target_weight_authority": {
            "single_name_weight_cap": 0.18,
        },
        "target_weight_resolution": {
            "cap_applied": False,
        },
    }


def _production_competitor(
    competitor_type: str,
    code: str,
    *,
    accepted: float,
    reason_codes: list[str] | None = None,
) -> dict[str, object]:
    return {
        "competitor_type": competitor_type,
        "symbol": code,
        "status": "COMPETITOR_SELECTED" if accepted > 0 else "COMPETITOR_REJECTED_RECONSIDERABLE",
        "accepted_weight": accepted,
        "reason_codes": reason_codes or ["COMPETITOR_SELECTED"],
    }


def _add_investment_evidence(code: str, *, incremental_state: str = "POSITIVE") -> dict[str, object]:
    return {
        "business_date": "2026-07-15",
        "position_campaign_id": f"pc-{code}-0001",
        "campaign_continuation": {
            "status": "PASS",
            "state": "PASS",
            "position_campaign_id": f"pc-{code}-0001",
            "authority": "same_campaign_identity_match",
        },
        "expected_edge": {
            "status": "PASS",
            "state": "IMPROVING",
            "baseline_business_date": "2026-07-14",
        },
        "incremental_value": {
            "status": "PASS" if incremental_state == "POSITIVE" else "FAIL_CLOSED",
            "state": incremental_state,
        },
        "opportunity_cost": {
            "status": "PASS",
            "state": "PASS",
        },
        "no_loss_averaging": {
            "status": "PASS",
            "state": "PASS",
        },
        "temporal_authority": {
            "future_evidence_used": False,
            "point_in_time": True,
        },
    }


def _cash_evidence(reason_codes: list[str]) -> dict[str, object]:
    return {
        "schema_version": "cash_competitor_evidence.v1",
        "business_date": "2026-07-15",
        "cash_competitor_evidence_hash": "cash-hash",
        "evidence_completeness": "COMPLETE",
        "cash_preference_semantic": "VALID_OPTIONALITY",
        "current_cash_weight": 0.5,
        "remaining_cash_weight": 0.1,
        "reason_codes": reason_codes,
    }
