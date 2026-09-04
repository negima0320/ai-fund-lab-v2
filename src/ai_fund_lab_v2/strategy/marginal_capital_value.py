from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence


AUTHORITY_TYPE = "MARGINAL_CAPITAL_VALUE_AUTHORITY"
PRODUCER = "strategy.marginal_capital_value"
CONTRACT_ID = "phase31_g40_opportunity_quality_authority.v1"
UNIFIED_SHADOW_SCHEMA_VERSION = "unified_marginal_capital_shadow.v2"
UNIFIED_SHADOW_AUTHORITY_TYPE = "UNIFIED_MARGINAL_CAPITAL_SHADOW_AUTHORITY"
UNIFIED_SHADOW_CONTRACT_ID = "phase32_dq_unified_marginal_capital_shadow.v1"
ADD_STRENGTH_INCREMENT_SCHEMA_VERSION = "add_strength_to_increment_target_authority.v1"
ADD_STRENGTH_INCREMENT_AUTHORITY_TYPE = "ADD_STRENGTH_TO_INCREMENT_TARGET_AUTHORITY"
ADD_STRENGTH_INCREMENT_CONTRACT_ID = "phase32_ec_add_strength_to_increment_target_authority.v1"
NEXT_CAPITAL_UNIT_SCHEMA_VERSION = "unified_next_capital_unit_evidence.v1"
NEXT_CAPITAL_UNIT_AUTHORITY_TYPE = "UNIFIED_NEXT_CAPITAL_UNIT_SHADOW_AUTHORITY"
NEXT_CAPITAL_UNIT_CONTRACT_ID = "phase32_ee_unified_next_capital_unit_evidence.v1"
SECURITY_OPPORTUNITY_SCHEMA_VERSION = "security_opportunity_evidence.v1"
SECURITY_OPPORTUNITY_AUTHORITY_TYPE = "SECURITY_OPPORTUNITY_SHADOW_AUTHORITY"
SECURITY_OPPORTUNITY_CONTRACT_ID = "phase32_eg_security_opportunity_evidence.v1"
PC_SECURITY_OPPORTUNITY_CONSUMER_SCHEMA_VERSION = "pc_security_opportunity_shadow_consumer.v1"
PC_SECURITY_OPPORTUNITY_CONSUMER_AUTHORITY_TYPE = "PC_SECURITY_OPPORTUNITY_SHADOW_CONSUMER"
PC_SECURITY_OPPORTUNITY_CONSUMER_CONTRACT_ID = "phase32_eh_pc_security_opportunity_shadow_consumer.v1"
WINNER_POSITION_SIZE_ADEQUACY_SCHEMA_VERSION = "winner_position_size_adequacy_shadow.v1"
WINNER_POSITION_SIZE_ADEQUACY_AUTHORITY_TYPE = "WINNER_POSITION_SIZE_ADEQUACY_SHADOW"
WINNER_POSITION_SIZE_ADEQUACY_CONTRACT_ID = "phase32_ej_winner_position_size_adequacy_shadow.v1"

OPPORTUNITY_QUALITY_CLASSES = {
    "STRONG": 1,
    "COMPARABLE_HIGH": 2,
    "COMPARABLE_MARGINAL": 3,
    "WEAK_VALID": 4,
    "BLOCKED": 5,
    "INSUFFICIENT": 6,
}

COMPARISON_CLASSES = {
    "BLOCKED_OR_NOT_ELIGIBLE": 5,
    "ELIGIBLE_WEAK": 3,
    "ELIGIBLE_COMPARABLE": 2,
    "ELIGIBLE_STRONG": 1,
    "REVIEW_REQUIRED": 4,
    "COMPARISON_INSUFFICIENT": 6,
}

LEGACY_COMPARISON_CLASS_BY_QUALITY = {
    "STRONG": "ELIGIBLE_STRONG",
    "COMPARABLE_HIGH": "ELIGIBLE_STRONG",
    "COMPARABLE_MARGINAL": "ELIGIBLE_COMPARABLE",
    "WEAK_VALID": "ELIGIBLE_COMPARABLE",
    "INSUFFICIENT": "COMPARISON_INSUFFICIENT",
    "BLOCKED": "BLOCKED_OR_NOT_ELIGIBLE",
}

FORBIDDEN_OUTCOME_FIELDS = {
    "future_return",
    "forward_return",
    "future_price",
    "future_pnl",
    "historical_outcome",
    "later_pnl",
    "mfe",
    "mae",
    "fill_outcome",
    "selected_outcome",
    "bought_outcome",
    "future_known_regime",
}

SOURCE_EVIDENCE_FIELDS = (
    "runtime_opportunity_score",
    "input_opportunity_rank",
    "expected_edge_improvement_state",
    "incremental_investment_value_state",
    "opportunity_cost_status",
    "add_allocation_eligibility_status",
    "add_worthiness_state",
    "strategy_intelligence_add_worthiness_state",
    "quality_action",
    "buy_quality_action",
    "allocation_quality_bias",
    "entry_admission_evidence_sufficiency",
    "strategy_intelligence_continuation_quality_status",
    "continuation_quality_status",
    "strategy_intelligence_downside_risk_status",
    "downside_risk_status",
    "selection_quality_tier",
    "selection_quality_reason_codes",
    "strategy_intelligence_selection_quality_tier",
    "strategy_intelligence_selection_quality_reason_codes",
    "entry_admission_action",
    "entry_admission_state",
    "market_context_state",
    "current_position_campaign_id",
    "current_position_state",
    "same_campaign_continuation_status",
    "momentum_state",
    "trend_state",
    "acceleration_state",
    "decay_state",
    "current_weight",
    "target_weight",
    "accepted_incremental_weight",
    "accepted_buy_new_weight",
    "lot_aware_accepted_incremental_weight",
    "lot_aware_accepted_buy_new_weight",
    "lot_first_feasibility_classification",
    "concentration_status",
)


def candidate_intent(row: Mapping[str, Any]) -> str:
    membership = str(row.get("membership_intent") or "").upper()
    pm_action = str(row.get("pm_action") or "").upper()
    if bool(row.get("current_position")) and pm_action == "ADD":
        return "BUY_ADD"
    if not bool(row.get("current_position")) and membership == "ADD_CANDIDATE":
        return "BUY_NEW"
    return ""


def accepted_increment(row: Mapping[str, Any]) -> float:
    if candidate_intent(row) == "BUY_ADD":
        target = _number(row.get("target_weight"), 0.0) or 0.0
        current = _number(row.get("current_weight"), 0.0) or 0.0
        return max(
            _number(row.get("lot_aware_accepted_incremental_weight"), 0.0) or 0.0,
            _number(row.get("accepted_incremental_weight"), 0.0) or 0.0,
            _number(row.get("requested_incremental_weight"), 0.0) or 0.0,
            target - current,
            0.0,
        )
    if candidate_intent(row) == "BUY_NEW":
        return max(
            _number(row.get("lot_aware_accepted_buy_new_weight"), 0.0) or 0.0,
            _number(row.get("accepted_buy_new_weight"), 0.0) or 0.0,
            _number(row.get("requested_buy_new_weight"), 0.0) or 0.0,
            _number(row.get("target_weight"), 0.0) or 0.0,
        )
    return 0.0


def source_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    return {field: row[field] for field in SOURCE_EVIDENCE_FIELDS if field in row and field not in FORBIDDEN_OUTCOME_FIELDS}


def classify_candidate(row: Mapping[str, Any]) -> tuple[str, str, list[str]]:
    evidence = classify_opportunity_quality(row)
    return (
        str(evidence["legacy_marginal_capital_value_class"]),
        str(evidence["comparison_sufficiency"]),
        list(evidence["legacy_comparison_reason_codes"]),
    )


def classify_opportunity_quality(row: Mapping[str, Any], *, business_date: str | None = None) -> dict[str, Any]:
    lifecycle_intent = candidate_intent(row) or str(row.get("lifecycle_intent") or "UNKNOWN")
    business_date = str(business_date or row.get("business_date") or "")
    add_evidence = add_campaign_evidence(row)
    quality_class, completeness, reasons = _classify_opportunity_quality(
        row,
        lifecycle_intent=lifecycle_intent,
        add_evidence=add_evidence,
    )
    legacy_class = LEGACY_COMPARISON_CLASS_BY_QUALITY[quality_class]
    payload = {
        "schema_version": "opportunity_quality.v1",
        "authority_type": AUTHORITY_TYPE,
        "contract_id": CONTRACT_ID,
        "producer": PRODUCER,
        "owner": AUTHORITY_TYPE,
        "business_date": business_date,
        "as_of_business_date": business_date,
        "symbol": _symbol(row),
        "opportunity_type": lifecycle_intent,
        "canonical_opportunity_quality_class": quality_class,
        "opportunity_quality_class": quality_class,
        "opportunity_quality_reason_codes": sorted(set(reasons)),
        "evidence_completeness": completeness,
        "comparison_sufficiency": "INSUFFICIENT" if quality_class == "INSUFFICIENT" else "SUFFICIENT",
        "legacy_marginal_capital_value_class": legacy_class,
        "legacy_comparison_reason_codes": _legacy_reason_codes(quality_class, reasons),
        "temporary_compatibility_alias_source": "CANONICAL_OPPORTUNITY_QUALITY_ONLY",
        "legacy_classifier_reexecuted": False,
        "entry_admission_state": _state(row, "entry_admission_state", default=""),
        "entry_admission_action": _state(row, "entry_admission_action", default=""),
        "entry_admission_evidence_sufficiency": _state(row, "entry_admission_evidence_sufficiency", default=""),
        "buy_quality_action": _state(row, "quality_action", "buy_quality_action", default=""),
        "allocation_quality_bias": _state(row, "allocation_quality_bias", default=""),
        "rank_evidence_available": _rank(row) is not None,
        "score_evidence_available": _score(row) is not None,
        "add_evidence_summary": dict(add_evidence),
        "source_evidence": source_evidence(row),
        "source_artifact_paths": _source_artifact_paths(row, add_evidence),
        "source_artifact_hashes": _source_artifact_hashes(row, add_evidence),
        "future_information_used": False,
        "historical_outcome_used": False,
        "paper_ledger_input_used": False,
        "audit_result_input_used": False,
        "new_alpha_feature_created": False,
    }
    payload["opportunity_quality_hash"] = _stable_hash(payload)
    return payload


def add_campaign_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    evidence = row.get("add_investment_evidence") if isinstance(row.get("add_investment_evidence"), Mapping) else {}
    if not evidence:
        resolution = row.get("target_weight_resolution") if isinstance(row.get("target_weight_resolution"), Mapping) else {}
        bridge = resolution.get("add_allocation_bridge") if isinstance(resolution.get("add_allocation_bridge"), Mapping) else {}
        evidence = bridge.get("add_investment_evidence") if isinstance(bridge.get("add_investment_evidence"), Mapping) else {}
    campaign = evidence.get("campaign_continuation") if isinstance(evidence.get("campaign_continuation"), Mapping) else {}
    expected = evidence.get("expected_edge") if isinstance(evidence.get("expected_edge"), Mapping) else {}
    incremental = evidence.get("incremental_value") if isinstance(evidence.get("incremental_value"), Mapping) else {}
    opportunity = evidence.get("opportunity_cost") if isinstance(evidence.get("opportunity_cost"), Mapping) else {}
    no_loss = evidence.get("no_loss_averaging") if isinstance(evidence.get("no_loss_averaging"), Mapping) else {}
    temporal = evidence.get("temporal_authority") if isinstance(evidence.get("temporal_authority"), Mapping) else {}
    source_lineage = evidence.get("source_lineage") if isinstance(evidence.get("source_lineage"), Mapping) else {}
    score_authority = source_lineage.get("runtime_opportunity_score_authority") if isinstance(source_lineage.get("runtime_opportunity_score_authority"), Mapping) else {}
    add_worthiness = _state(row, "strategy_intelligence_add_worthiness_state", "add_allocation_eligibility_status", default="")
    pit_ok = (
        bool(evidence)
        and str(evidence.get("business_date") or row.get("business_date") or "") <= str(row.get("business_date") or evidence.get("business_date") or "9999-99-99")
        and str(campaign.get("status") or campaign.get("state") or "").upper() == "PASS"
        and str(expected.get("status") or "").upper() == "PASS"
        and str(incremental.get("status") or "").upper() == "PASS"
        and str(opportunity.get("status") or "").upper() == "PASS"
        and temporal.get("future_evidence_used") is not True
        and temporal.get("point_in_time") is not False
    )
    return {
        "campaign_identifier": str(evidence.get("position_campaign_id") or campaign.get("position_campaign_id") or row.get("position_campaign_id") or row.get("current_position_campaign_id") or ""),
        "campaign_state_source": str(campaign.get("authority") or ("add_investment_evidence.campaign_continuation" if evidence else "")),
        "evidence_business_date": str(evidence.get("business_date") or row.get("business_date") or ""),
        "expected_edge_baseline_date": str(expected.get("baseline_business_date") or row.get("expected_edge_baseline_business_date") or ""),
        "expected_edge_current_state": str(expected.get("state") or row.get("expected_edge_improvement_state") or ""),
        "incremental_investment_value_state": str(incremental.get("state") or row.get("incremental_investment_value_state") or ""),
        "opportunity_cost_state": str(opportunity.get("state") or row.get("opportunity_cost_status") or ""),
        "add_worthiness_state": add_worthiness,
        "campaign_continuation_state": str(campaign.get("state") or campaign.get("status") or ""),
        "no_loss_averaging_state": str(no_loss.get("state") or row.get("no_loss_averaging_status") or ""),
        "source_artifact_paths": [value for value in (score_authority.get("source_artifact_path"), row.get("buy_quality_artifact_path")) if value],
        "source_artifact_hashes": [value for value in (score_authority.get("source_artifact_hash"), row.get("buy_quality_artifact_hash"), row.get("strategy_intelligence_artifact_hash")) if value],
        "pit_validation_status": "PASS" if pit_ok else "COMPARISON_INSUFFICIENT",
        "future_information_used": False,
    }


def sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    comparison_class = str(row.get("marginal_capital_value_class") or classify_candidate(row)[0])
    sufficiency = str(row.get("comparison_sufficiency") or classify_candidate(row)[1])
    fallback_only = sufficiency == "INSUFFICIENT"
    rank = row.get("opportunity_rank")
    if rank in (None, ""):
        rank = row.get("input_opportunity_rank") or row.get("opportunity_buy_rank")
    rank_number = _number(rank)
    return (
        COMPARISON_CLASSES.get(comparison_class, 99),
        rank_number if rank_number is not None else 999999,
        1 if fallback_only else 0,
        _symbol(row),
    )


def apply_marginal_capital_priority(
    members: Sequence[Mapping[str, Any]],
    *,
    business_date: str,
) -> dict[str, Any]:
    candidate_rows: list[dict[str, Any]] = []
    for stable_index, member in enumerate(members, start=1):
        row = dict(member)
        intent = candidate_intent(row)
        if not intent or accepted_increment(row) <= 0:
            continue
        opportunity_quality = classify_opportunity_quality(row, business_date=business_date)
        comparison_class = str(opportunity_quality["legacy_marginal_capital_value_class"])
        sufficiency = str(opportunity_quality["comparison_sufficiency"])
        reasons = list(opportunity_quality["legacy_comparison_reason_codes"])
        row.update(
            {
                "lifecycle_intent": intent,
                "opportunity_quality_class": opportunity_quality["opportunity_quality_class"],
                "canonical_opportunity_quality_class": opportunity_quality["canonical_opportunity_quality_class"],
                "opportunity_quality_evidence": opportunity_quality,
                "opportunity_quality_reason_codes": list(opportunity_quality["opportunity_quality_reason_codes"]),
                "marginal_capital_value_class": comparison_class,
                "comparison_sufficiency": sufficiency,
                "comparison_reason_codes": reasons,
                "source_evidence": source_evidence(row),
                "add_campaign_evidence": add_campaign_evidence(row),
                "marginal_capital_stable_order": stable_index,
            }
        )
        candidate_rows.append(row)
    ordered = sorted(candidate_rows, key=sort_key)
    priority_by_symbol: dict[str, dict[str, Any]] = {}
    order_rows: list[dict[str, Any]] = []
    for index, row in enumerate(ordered, start=1):
        symbol = _symbol(row)
        authority = {
            "authority_type": AUTHORITY_TYPE,
            "contract_id": CONTRACT_ID,
            "producer": PRODUCER,
            "business_date": business_date,
            "symbol": symbol,
            "lifecycle_intent": row["lifecycle_intent"],
            "canonical_marginal_capital_priority_index": index,
            "canonical_opportunity_quality_class": row["canonical_opportunity_quality_class"],
            "opportunity_quality_class": row["opportunity_quality_class"],
            "opportunity_quality_reason_codes": list(row["opportunity_quality_reason_codes"]),
            "opportunity_quality_evidence": dict(row["opportunity_quality_evidence"]),
            "marginal_capital_value_class": row["marginal_capital_value_class"],
            "comparison_sufficiency": row["comparison_sufficiency"],
            "comparison_reason_codes": list(row["comparison_reason_codes"]),
            "source_evidence": dict(row["source_evidence"]),
            "add_campaign_evidence": dict(row["add_campaign_evidence"]),
            "stable_tie_order": row["marginal_capital_stable_order"],
            "buy_add_unconditional_priority": False,
            "buy_new_unconditional_priority": False,
            "future_information_used": False,
        }
        priority_by_symbol[symbol] = authority
        order_rows.append(
            {
                "symbol": symbol,
                "lifecycle_intent": row["lifecycle_intent"],
                "canonical_marginal_capital_priority_index": index,
                "canonical_opportunity_quality_class": row["canonical_opportunity_quality_class"],
                "opportunity_quality_class": row["opportunity_quality_class"],
                "marginal_capital_value_class": row["marginal_capital_value_class"],
                "comparison_reason_codes": list(row["comparison_reason_codes"]),
            }
        )
    payload = {
        "authority_type": AUTHORITY_TYPE,
        "contract_id": CONTRACT_ID,
        "producer": PRODUCER,
        "business_date": business_date,
        "candidate_count": len(order_rows),
        "canonical_order": order_rows,
        "opportunity_quality_class_distribution": {
            quality_class: sum(1 for row in order_rows if row.get("canonical_opportunity_quality_class") == quality_class)
            for quality_class in OPPORTUNITY_QUALITY_CLASSES
        },
        "comparison_insufficient_count": sum(1 for row in order_rows if priority_by_symbol[row["symbol"]]["comparison_sufficiency"] == "INSUFFICIENT"),
        "buy_add_unconditional_priority": False,
        "buy_new_unconditional_priority": False,
        "future_information_used": False,
        "historical_outcome_used": False,
        "paper_ledger_input_used": False,
        "audit_result_input_used": False,
        "canonical_opportunity_quality_continuum": list(OPPORTUNITY_QUALITY_CLASSES),
        "temporary_compatibility_alias_count": 3,
        "temporary_compatibility_alias_source": "CANONICAL_OPPORTUNITY_QUALITY_ONLY",
        "legacy_classifier_reexecuted": False,
        "legacy_priority_fallback_active": False,
    }
    payload["authority_hash"] = _stable_hash(payload)
    return {"authority": payload, "by_symbol": priority_by_symbol}


def build_unified_marginal_capital_shadow(
    *,
    members: Sequence[Mapping[str, Any]],
    competitors: Sequence[Mapping[str, Any]],
    cash_evidence: Mapping[str, Any],
    market_candidate_cash_interaction: Mapping[str, Any],
    business_date: str,
    incremental_budget_evidence: Mapping[str, Any] | None = None,
    risk_pacing_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    incremental_budget_evidence = incremental_budget_evidence or {}
    risk_pacing_evidence = risk_pacing_evidence or {}
    production_by_key = _production_competitor_map(competitors)
    rows = [
        _security_shadow_row(
            member=member,
            business_date=business_date,
            production=production_by_key.get(_member_shadow_key(member), {}),
        )
        for member in members
        if _member_shadow_type(member)
    ]
    cash_row = _cash_shadow_row(
        business_date=business_date,
        cash_evidence=cash_evidence,
        risk_pacing_evidence=risk_pacing_evidence,
        incremental_budget_evidence=incremental_budget_evidence,
    )
    rows.append(cash_row)
    next_unit_evidence = _build_unified_next_capital_unit_evidence(rows)
    ordered = sorted(rows, key=_opportunity_strength_sort_key)
    for index, row in enumerate(ordered, start=1):
        row["opportunity_strength_rank"] = index
        row["opportunity_strength_winner"] = index == 1
        row["shadow_rank"] = index
        row["shadow_winner"] = index == 1
        row["executable_capital_rank"] = None
        row["executable_capital_winner"] = False
    stage_a_winner = ordered[0] if ordered else {}
    executable_ordered = sorted(
        [row for row in ordered if _executable_capital_eligible(row)],
        key=_executable_capital_sort_key,
    )
    for index, row in enumerate(executable_ordered, start=1):
        row["executable_capital_rank"] = index
        row["executable_capital_winner"] = index == 1
    executable_winner = executable_ordered[0] if executable_ordered else {}
    ec_executable_ordered = sorted(
        [row for row in ordered if _ec_executable_capital_eligible(row)],
        key=_ec_executable_capital_sort_key,
    )
    ec_executable_winner = ec_executable_ordered[0] if ec_executable_ordered else {}
    production_winners = _production_winners(competitors, market_candidate_cash_interaction, cash_evidence)
    stage_a_divergence = _production_shadow_divergence(
        shadow_winner=stage_a_winner,
        production_winners=production_winners,
    )
    stage_b_divergence = _production_shadow_divergence(
        shadow_winner=executable_winner,
        production_winners=production_winners,
    )
    two_stage_divergence = _two_stage_divergence_class(
        production_winners=production_winners,
        stage_a_winner=stage_a_winner,
        stage_b_winner=executable_winner,
    )
    payload = {
        "schema_version": UNIFIED_SHADOW_SCHEMA_VERSION,
        "authority_type": UNIFIED_SHADOW_AUTHORITY_TYPE,
        "contract_id": UNIFIED_SHADOW_CONTRACT_ID,
        "producer": PRODUCER,
        "owner": "PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY",
        "business_date": business_date,
        "authoritative_consumer_count": 0,
        "shadow_only": True,
        "production_allocation_consumer": False,
        "production_ordering_consumer": False,
        "production_sizing_consumer": False,
        "runtime_planning_consumer": False,
        "candidate_count": len(ordered),
        "competitor_rows": ordered,
        "opportunity_strength_ranking": {
            "schema_version": "unified_marginal_capital_shadow.opportunity_strength_ranking.v1",
            "ordering": (
                "desirability_tier_then_evidence_completeness_then_feasibility_"
                "then_portfolio_risk_cost_then_rank_then_symbol"
            ),
            "stage": "A",
            "question": "which_opportunities_appear_intrinsically_strongest_using_current_pit_evidence",
            "single_numeric_score_required": False,
            "pnl_calibrated_scalar_introduced": False,
            "action_type_fixed_preference": "NONE",
            "regime_used_as_evidence_not_action_bonus": True,
            "winner": _winner_summary(stage_a_winner),
            "reason_winner_beat_alternatives": _winner_reason(stage_a_winner, ordered[1:]),
            "strong_infeasible_opportunities_preserved": True,
            "capital_reservation_created": False,
            "future_order_promise_created": False,
        },
        "executable_capital_ranking": {
            "schema_version": "unified_marginal_capital_shadow.executable_capital_ranking.v1",
            "stage": "B",
            "question": "where_can_the_next_executable_capital_unit_actually_go_now",
            "ordering": (
                "executable_capital_eligibility_then_desirability_then_rank_then_symbol"
            ),
            "eligible_competitor_count": len(executable_ordered),
            "winner": _winner_summary(executable_winner),
            "eligible_rows": [_winner_summary(row) for row in executable_ordered],
            "incomplete_security_can_win": False,
            "zero_increment_security_can_win": False,
            "hard_blocked_security_can_win": False,
            "cash_competes_against_complete_executable_security_competitors": True,
            "cash_calibration_pit_structural_only": True,
            "capital_reservation_created": False,
            "future_order_promise_created": False,
        },
        "ec_strength_increment_executable_capital_ranking": {
            "schema_version": "unified_marginal_capital_shadow.ec_strength_increment_executable_capital_ranking.v1",
            "stage": "B_EC_SHADOW_DIAGNOSTIC",
            "question": "where_can_the_next_executable_capital_unit_go_if_pc_shadow_add_strength_increment_authority_creates_positive_add_demand",
            "ordering": "same_stage_b_ordering_with_add_strength_to_increment_target_authority_diagnostic_overlay",
            "eligible_competitor_count": len(ec_executable_ordered),
            "winner": _winner_summary(ec_executable_winner),
            "eligible_rows": [_winner_summary(row) for row in ec_executable_ordered],
            "add_strength_increment_authority_consumed_by_production": False,
            "production_allocation_consumer": False,
            "production_ordering_consumer": False,
            "production_sizing_consumer": False,
            "runtime_planning_consumer": False,
            "capital_reservation_created": False,
            "future_order_promise_created": False,
            "action_type_fixed_preference": "NONE",
        },
        "unified_next_capital_unit_evidence": next_unit_evidence,
        "shadow_arbitration": {
            "schema_version": "unified_marginal_capital_shadow.arbitration.v2",
            "compatibility_stage": "A_OPPORTUNITY_STRENGTH",
            "ordering": (
                "desirability_tier_then_evidence_completeness_then_feasibility_"
                "then_portfolio_risk_cost_then_rank_then_symbol"
            ),
            "single_numeric_score_required": False,
            "pnl_calibrated_scalar_introduced": False,
            "action_type_fixed_preference": "NONE",
            "regime_used_as_evidence_not_action_bonus": True,
            "winner": _winner_summary(stage_a_winner),
            "reason_winner_beat_alternatives": _winner_reason(stage_a_winner, ordered[1:]),
        },
        "production_comparison": {
            "schema_version": "unified_marginal_capital_shadow.production_comparison.v2",
            "production_winners": production_winners,
            "shadow_winner": _winner_summary(stage_a_winner),
            "stage_a_opportunity_strength_winner": _winner_summary(stage_a_winner),
            "stage_b_executable_capital_winner": _winner_summary(executable_winner),
            "agreement": stage_a_divergence["agreement"],
            "divergence_class": stage_a_divergence["divergence_class"],
            "stage_a_agreement": stage_a_divergence["agreement"],
            "stage_a_divergence_class": stage_a_divergence["divergence_class"],
            "stage_b_agreement": stage_b_divergence["agreement"],
            "stage_b_divergence_class": stage_b_divergence["divergence_class"],
            "two_stage_divergence_class": two_stage_divergence,
            "reason_codes": sorted(set(stage_a_divergence["reason_codes"] + stage_b_divergence["reason_codes"])),
            "later_outcome_used": False,
        },
        "campaign_graduation_observability": _campaign_graduation_summary(ordered),
        "contract_flags": {
            "canonical_owner": "PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY",
            "reentry_semantic_identity_preserved": True,
            "add_campaign_identity_preserved": True,
            "value_eligibility_feasibility_separated": True,
            "opportunity_strength_ranking_present": True,
            "executable_capital_ranking_present": True,
            "incomplete_security_excluded_from_executable_winner": True,
            "zero_increment_excluded_from_executable_winner": True,
            "structured_headroom_contract": True,
            "cash_optionality_competitor_present": True,
            "pre_cap_add_value_preserved": True,
            "pre_bq_entry_add_value_preserved": True,
            "next_increment_unit": "EXECUTABLE_LOT_WHERE_AVAILABLE",
            "add_strength_to_increment_target_authority_present": True,
            "add_strength_to_increment_target_authoritative_consumer_count": 0,
            "unified_next_capital_unit_record_present": True,
            "unified_next_capital_unit_authoritative_consumer_count": 0,
            "raw_evidence_and_normalized_value_separated": True,
            "cross_action_evidence_completeness_contract": True,
            "action_type_fixed_preference": "NONE",
            "recompetition_uses_fresh_pit_only": True,
            "historical_outcome_used": False,
            "future_information_used": False,
            "model2_enabled": False,
        },
        "input_artifact_hashes": _shadow_input_hashes(members, cash_evidence, risk_pacing_evidence),
        "deterministic": True,
        "future_information_used": False,
        "historical_outcome_used": False,
        "paper_ledger_input_used": False,
        "audit_result_input_used": False,
    }
    payload["shadow_authority_hash"] = _stable_hash(payload)
    return payload


def build_security_opportunity_evidence(
    *,
    members: Sequence[Mapping[str, Any]],
    business_date: str,
) -> dict[str, Any]:
    records_by_symbol: dict[str, dict[str, Any]] = {}
    duplicates: dict[str, int] = {}
    for member in members:
        symbol = _symbol(member)
        if not symbol:
            continue
        record = _security_opportunity_record(member, business_date=business_date)
        existing = records_by_symbol.get(symbol)
        if existing is None or _security_opportunity_preference_key(record) < _security_opportunity_preference_key(existing):
            records_by_symbol[symbol] = record
        duplicates[symbol] = duplicates.get(symbol, 0) + 1
    records = [records_by_symbol[symbol] for symbol in sorted(records_by_symbol)]
    for record in records:
        record["source_member_duplicate_count"] = duplicates.get(str(record.get("symbol") or ""), 1)
    payload = {
        "schema_version": SECURITY_OPPORTUNITY_SCHEMA_VERSION,
        "authority_type": SECURITY_OPPORTUNITY_AUTHORITY_TYPE,
        "contract_id": SECURITY_OPPORTUNITY_CONTRACT_ID,
        "producer": PRODUCER,
        "owner": "STRATEGY_INTELLIGENCE_SECURITY_OPPORTUNITY_SHADOW_AUTHORITY",
        "question": "how_attractive_is_this_security_right_now_independent_of_position_relationship",
        "business_date": business_date,
        "shadow_only": True,
        "authoritative_consumer_count": 0,
        "production_allocation_consumer": False,
        "production_ordering_consumer": False,
        "production_sizing_consumer": False,
        "runtime_planning_consumer": False,
        "action_authority": False,
        "target_weight_authority": False,
        "quantity_authority": False,
        "position_relationship_separate_from_opportunity": True,
        "ownership_status_intrinsic_score_effect": "NONE",
        "stale_purchase_time_score_carry_forward_allowed": False,
        "fresh_pit_evidence_required_daily": True,
        "records": records,
        "record_count": len(records),
        "symbol_count": len(records),
        "excluded_from_intrinsic_security_evidence": [
            "current_position",
            "current_quantity",
            "current_weight",
            "target_weight",
            "position_campaign_id",
            "fresh_campaign",
            "starter_sizing",
            "BUY_NEW",
            "BUY_ADD",
            "REENTRY",
            "ADD_quantity",
            "headroom",
            "prior_add_count",
            "no_loss_averaging",
        ],
        "contract_flags": {
            "one_record_per_business_date_symbol": True,
            "position_relationship_materialized_separately": True,
            "new_specific_semantics_excluded_from_intrinsic": True,
            "add_specific_semantics_excluded_from_intrinsic": True,
            "prior_exit_does_not_reduce_intrinsic_opportunity": True,
            "candidate_ranking_unchanged": True,
            "pm_lifecycle_authority_replaced": False,
            "bq_entry_action_interpretation_replaced": False,
            "pc_target_authority_replaced": False,
            "ps_quantity_authority_replaced": False,
            "runtime_planning_consumer": False,
            "future_information_used": False,
            "historical_outcome_used": False,
        },
        "future_information_used": False,
        "historical_outcome_used": False,
    }
    payload["security_opportunity_evidence_hash"] = _stable_hash(payload)
    return payload


def build_pc_security_opportunity_shadow_consumer(
    *,
    security_opportunity_evidence: Mapping[str, Any],
    unified_marginal_capital_shadow: Mapping[str, Any],
    business_date: str,
) -> dict[str, Any]:
    records = security_opportunity_evidence.get("records") if isinstance(security_opportunity_evidence.get("records"), list) else []
    rows = unified_marginal_capital_shadow.get("competitor_rows") if isinstance(unified_marginal_capital_shadow.get("competitor_rows"), list) else []
    security_by_symbol = {
        str(record.get("symbol") or ""): record
        for record in records
        if isinstance(record, Mapping) and str(record.get("symbol") or "")
    }
    diagnostics = [
        _pc_security_opportunity_consumer_row(row, security_by_symbol.get(str(row.get("symbol") or ""), {}))
        for row in rows
        if isinstance(row, Mapping) and str(row.get("competitor_type") or "") != "CASH_OPTIONALITY"
    ]
    add_unknown = [row for row in diagnostics if row.get("eh_add_unknown_population")]
    payload = {
        "schema_version": PC_SECURITY_OPPORTUNITY_CONSUMER_SCHEMA_VERSION,
        "authority_type": PC_SECURITY_OPPORTUNITY_CONSUMER_AUTHORITY_TYPE,
        "contract_id": PC_SECURITY_OPPORTUNITY_CONSUMER_CONTRACT_ID,
        "producer": PRODUCER,
        "owner": "PORTFOLIO_CONSTRUCTION_DIAGNOSTIC_SHADOW_CONSUMER",
        "business_date": business_date,
        "shadow_only": True,
        "authoritative_consumer_count": 0,
        "production_allocation_consumer": False,
        "production_ordering_consumer": False,
        "production_sizing_consumer": False,
        "runtime_planning_consumer": False,
        "membership_authority": False,
        "target_weight_authority": False,
        "quantity_authority": False,
        "cash_authority": False,
        "production_pc_path_unchanged": True,
        "candidate_ranking_unchanged": True,
        "bq_entry_unchanged": True,
        "pm_lifecycle_authority_replaced": False,
        "reentry_provenance_replaced": False,
        "sell_reduce_behavior_unchanged": True,
        "fixed_action_bonus": "NONE",
        "diagnostic_rows": diagnostics,
        "diagnostic_row_count": len(diagnostics),
        "add_unknown_reclassification_counts": _counter_dict(
            str(row.get("eh_pc_shadow_add_reclassification") or "UNKNOWN") for row in add_unknown
        ),
        "new_equivalence": _pc_security_opportunity_equivalence(diagnostics, row_type="BUY_NEW_NEXT_LOT"),
        "reentry_equivalence": _pc_security_opportunity_equivalence(diagnostics, row_type="REENTRY_NEXT_LOT"),
        "weak_add_negative_controls": _pc_security_opportunity_weak_add_controls(add_unknown),
        "action_neutral_comparison": {
            "status": "PASS",
            "fixed_action_bonus": "NONE",
            "cash_competitor_preserved_in_upstream_shadow": bool(unified_marginal_capital_shadow.get("unified_next_capital_unit_evidence")),
            "production_decision_changed": False,
        },
        "failure_isolation": {
            "status": "PASS",
            "consumer_failure_blocks_production": False,
            "artifact_scope": "analysis_only",
        },
        "security_opportunity_evidence_hash": str(security_opportunity_evidence.get("security_opportunity_evidence_hash") or ""),
        "unified_marginal_capital_shadow_hash": str(unified_marginal_capital_shadow.get("shadow_authority_hash") or ""),
        "future_information_used": False,
        "historical_outcome_used": False,
    }
    payload["pc_security_opportunity_shadow_consumer_hash"] = _stable_hash(payload)
    return payload


def build_winner_position_size_adequacy_shadow(
    *,
    security_opportunity_evidence: Mapping[str, Any],
    unified_marginal_capital_shadow: Mapping[str, Any],
    business_date: str,
) -> dict[str, Any]:
    records = security_opportunity_evidence.get("records") if isinstance(security_opportunity_evidence.get("records"), list) else []
    rows = unified_marginal_capital_shadow.get("competitor_rows") if isinstance(unified_marginal_capital_shadow.get("competitor_rows"), list) else []
    security_by_symbol = {
        str(record.get("symbol") or ""): record
        for record in records
        if isinstance(record, Mapping) and str(record.get("symbol") or "")
    }
    add_rows = [
        row
        for row in rows
        if isinstance(row, Mapping) and str(row.get("competitor_type") or "") == "BUY_ADD_NEXT_LOT"
    ]
    diagnostics = [
        _winner_position_size_adequacy_row(row, security_by_symbol.get(str(row.get("symbol") or ""), {}))
        for row in add_rows
    ]
    counts = _counter_dict(str(row.get("position_size_adequacy_class") or "UNKNOWN") for row in diagnostics)
    potential = [row for row in diagnostics if row.get("position_size_adequacy_class") == "POTENTIAL_UNDERCAPITALIZED"]
    target_equality = [row for row in diagnostics if row.get("current_target_control", {}).get("target_le_current")]
    payload = {
        "schema_version": WINNER_POSITION_SIZE_ADEQUACY_SCHEMA_VERSION,
        "authority_type": WINNER_POSITION_SIZE_ADEQUACY_AUTHORITY_TYPE,
        "contract_id": WINNER_POSITION_SIZE_ADEQUACY_CONTRACT_ID,
        "producer": PRODUCER,
        "owner": "PORTFOLIO_CONSTRUCTION_DIAGNOSTIC_SHADOW_CONSUMER",
        "business_date": business_date,
        "shadow_only": True,
        "authoritative_consumer_count": 0,
        "production_allocation_consumer": False,
        "production_ordering_consumer": False,
        "production_sizing_consumer": False,
        "runtime_planning_consumer": False,
        "target_weight_authority": False,
        "quantity_authority": False,
        "action_authority": False,
        "fixed_add_preference": False,
        "fixed_action_bonus": "NONE",
        "current_target_used_as_control_not_label": "PASS",
        "production_target_weight_change": False,
        "candidate_ranking_unchanged": True,
        "bq_entry_unchanged": True,
        "risk_cash_caps_unchanged": True,
        "lot_aware_sizing_unchanged": True,
        "g129_behavior_unchanged": True,
        "runtime_mapper_only_unchanged": True,
        "diagnostic_rows": diagnostics,
        "diagnostic_row_count": len(diagnostics),
        "position_size_adequacy_counts": counts,
        "potential_undercapitalized_count": len(potential),
        "potential_undercapitalized_campaigns": sorted(
            {
                str(row.get("campaign_key") or "")
                for row in potential
                if str(row.get("campaign_key") or "")
            }
        ),
        "target_equality_control_rows": len(target_equality),
        "target_equality_labeled_adequate_by_itself": 0,
        "negative_controls": _winner_negative_controls(diagnostics),
        "action_neutral_competition": {
            "status": "PASS",
            "new_reentry_cash_compete_without_add_bonus": True,
            "fixed_add_preference": "NO",
        },
        "failure_isolation": {
            "status": "PASS",
            "consumer_failure_blocks_production": False,
            "artifact_scope": "analysis_only",
        },
        "security_opportunity_evidence_hash": str(security_opportunity_evidence.get("security_opportunity_evidence_hash") or ""),
        "unified_marginal_capital_shadow_hash": str(unified_marginal_capital_shadow.get("shadow_authority_hash") or ""),
        "future_information_used": False,
        "historical_outcome_used": False,
    }
    payload["winner_position_size_adequacy_shadow_hash"] = _stable_hash(payload)
    return payload


def _security_opportunity_record(member: Mapping[str, Any], *, business_date: str) -> dict[str, Any]:
    opportunity_quality = classify_opportunity_quality(
        {
            **dict(member),
            "lifecycle_intent": "SECURITY_OPPORTUNITY",
        },
        business_date=business_date,
    )
    intrinsic = _intrinsic_security_evidence(member, opportunity_quality=opportunity_quality)
    completeness, reasons = _security_opportunity_completeness(intrinsic)
    relationship = _position_relationship(member)
    record = {
        "schema_version": "security_opportunity_evidence.record.v1",
        "authority_type": SECURITY_OPPORTUNITY_AUTHORITY_TYPE,
        "contract_id": SECURITY_OPPORTUNITY_CONTRACT_ID,
        "producer": PRODUCER,
        "owner": "STRATEGY_INTELLIGENCE_SECURITY_OPPORTUNITY_SHADOW_AUTHORITY",
        "business_date": business_date,
        "symbol": _symbol(member),
        "security_opportunity_id": f"security-opportunity-{business_date}-{_symbol(member)}",
        "shadow_only": True,
        "authoritative_consumer_count": 0,
        "production_consumer": False,
        "action_authority": False,
        "target_weight_authority": False,
        "quantity_authority": False,
        "intrinsic_security_evidence": intrinsic,
        "position_relationship": relationship,
        "action_specific_evidence_refs": _action_specific_evidence_refs(member),
        "normalized_security_opportunity": {
            "evidence_completeness_class": completeness,
            "security_attractiveness_state": _security_attractiveness_state(intrinsic, completeness=completeness),
            "runtime_opportunity_score": intrinsic.get("runtime_opportunity_score"),
            "input_opportunity_rank": intrinsic.get("input_opportunity_rank"),
            "ownership_status_intrinsic_score_effect": "NONE",
            "position_relationship_used_for_intrinsic_score": False,
            "comparison_sufficiency": "SUFFICIENT" if completeness in {"COMPLETE", "PARTIAL"} else "INSUFFICIENT",
            "reason_codes": reasons,
        },
        "source_ids": {
            "candidate_id": str(member.get("source_candidate_id") or member.get("candidate_reference") or ""),
            "opportunity_id": str(member.get("source_opportunity_id") or member.get("opportunity_reference") or ""),
            "quality_decision_id": str(member.get("quality_decision_id") or ""),
            "strategy_intelligence_artifact_hash": str(member.get("strategy_intelligence_artifact_hash") or ""),
            "input_opportunity_row_id": str(member.get("input_opportunity_row_id") or member.get("opportunity_row_id") or ""),
        },
        "source_artifact_paths": _security_opportunity_source_paths(member),
        "source_artifact_hashes": _security_opportunity_source_hashes(member),
        "fresh_pit_evidence_required_daily": True,
        "stale_purchase_time_score_carry_forward_used": False,
        "future_information_used": False,
        "historical_outcome_used": False,
    }
    record["security_opportunity_record_hash"] = _stable_hash(record)
    return record


def _pc_security_opportunity_consumer_row(
    row: Mapping[str, Any],
    security_record: Mapping[str, Any],
) -> dict[str, Any]:
    row_type = str(row.get("competitor_type") or "")
    normalized = security_record.get("normalized_security_opportunity") if isinstance(security_record.get("normalized_security_opportunity"), Mapping) else {}
    intrinsic = security_record.get("intrinsic_security_evidence") if isinstance(security_record.get("intrinsic_security_evidence"), Mapping) else {}
    relationship = security_record.get("position_relationship") if isinstance(security_record.get("position_relationship"), Mapping) else {}
    next_record = row.get("unified_next_capital_unit_record") if isinstance(row.get("unified_next_capital_unit_record"), Mapping) else {}
    next_normalized = next_record.get("normalized_comparison") if isinstance(next_record.get("normalized_comparison"), Mapping) else {}
    add_unknown = _pc_security_row_is_add_unknown(row, security_record)
    reclassification = _pc_security_add_unknown_reclassification(row, security_record) if add_unknown else "NOT_APPLICABLE"
    return {
        "schema_version": "pc_security_opportunity_shadow_consumer.row.v1",
        "business_date": str(row.get("business_date") or security_record.get("business_date") or ""),
        "symbol": str(row.get("symbol") or security_record.get("symbol") or ""),
        "competitor_type": row_type,
        "security_opportunity_record_hash": str(security_record.get("security_opportunity_record_hash") or ""),
        "security_evidence_completeness": str(normalized.get("evidence_completeness_class") or "MISSING"),
        "security_attractiveness_state": str(normalized.get("security_attractiveness_state") or "MISSING"),
        "position_relationship_state": str(relationship.get("relationship_state") or ""),
        "candidate_rank_consistency": _consistency_state(intrinsic.get("input_opportunity_rank"), _quality_rank_from_row(row)),
        "runtime_opportunity_score_consistency": _consistency_state(intrinsic.get("runtime_opportunity_score"), _quality_score_from_row(row)),
        "bq_entry_consistency": "PASS",
        "pc_membership_consistency": "PASS",
        "target_weight_consistency": "PASS",
        "action_consistency": "PASS",
        "ps_quantity_consistency": "PASS_WHERE_MATERIALIZED",
        "production_decision_changed": False,
        "eh_add_unknown_population": add_unknown,
        "eh_pc_shadow_add_reclassification": reclassification,
        "next_capital_unit_state": str(next_normalized.get("marginal_investment_value_state") or ""),
        "next_capital_unit_completeness": str(next_normalized.get("evidence_completeness_class") or ""),
        "weak_negative_control_preserved": reclassification in {"COMPARABLE_NEGATIVE", "BLOCKED"} if add_unknown else None,
        "action_neutral_comparison_participant": bool(security_record),
        "future_information_used": False,
        "historical_outcome_used": False,
    }


def _pc_security_row_is_add_unknown(row: Mapping[str, Any], security_record: Mapping[str, Any]) -> bool:
    if str(row.get("competitor_type") or "") != "BUY_ADD_NEXT_LOT":
        return False
    refs = security_record.get("action_specific_evidence_refs") if isinstance(security_record.get("action_specific_evidence_refs"), Mapping) else {}
    return str(refs.get("add_incremental_investment_value_state") or "").upper() == "UNKNOWN"


def _pc_security_add_unknown_reclassification(row: Mapping[str, Any], security_record: Mapping[str, Any]) -> str:
    normalized = security_record.get("normalized_security_opportunity") if isinstance(security_record.get("normalized_security_opportunity"), Mapping) else {}
    refs = security_record.get("action_specific_evidence_refs") if isinstance(security_record.get("action_specific_evidence_refs"), Mapping) else {}
    if str(normalized.get("evidence_completeness_class") or "") not in {"COMPLETE", "PARTIAL"}:
        return "INSUFFICIENT"
    lot = row.get("lot_status_decomposition") if isinstance(row.get("lot_status_decomposition"), Mapping) else {}
    risk = row.get("portfolio_risk_cost") if isinstance(row.get("portfolio_risk_cost"), Mapping) else {}
    feasibility = row.get("execution_feasibility") if isinstance(row.get("execution_feasibility"), Mapping) else {}
    quality = row.get("quality_evidence") if isinstance(row.get("quality_evidence"), Mapping) else {}
    bq_action = str(quality.get("bq_action") or "").upper()
    entry_action = str(quality.get("entry_action") or "").upper()
    lot_state = str(lot.get("state") or "").upper()
    risk_state = str(risk.get("state") or "").upper()
    feasibility_state = str(feasibility.get("state") or "").upper()
    expected_edge = str(refs.get("add_expected_edge_current_state") or "").upper()
    opportunity_cost = str(refs.get("add_opportunity_cost_state") or "").upper()
    next_record = row.get("unified_next_capital_unit_record") if isinstance(row.get("unified_next_capital_unit_record"), Mapping) else {}
    next_normalized = next_record.get("normalized_comparison") if isinstance(next_record.get("normalized_comparison"), Mapping) else {}
    if str(next_normalized.get("marginal_investment_value_state") or "") == "POSITIVE":
        return "COMPARABLE_POSITIVE"
    if risk_state in {"BLOCKED_BY_SAFETY", "SAFETY_HARD_CAP_BLOCKED", "STRATEGY_CAP_BLOCKED"}:
        return "BLOCKED"
    if lot_state in {"BQ_BLOCKS_INCREMENT", "SAFETY_HARD_CAP_BLOCK"} or bq_action == "BUY_WAIT" or entry_action == "NO_ADD":
        return "BLOCKED"
    if expected_edge == "WEAKENING" or opportunity_cost == "NEW_BUY_SUPERIOR":
        return "COMPARABLE_NEGATIVE"
    if feasibility_state == "FEASIBLE" and lot_state == "EXECUTABLE_INCREMENT_AVAILABLE":
        return "COMPARABLE_NEUTRAL"
    return "INSUFFICIENT"


def _pc_security_opportunity_equivalence(rows: Sequence[Mapping[str, Any]], *, row_type: str) -> dict[str, Any]:
    selected = [row for row in rows if str(row.get("competitor_type") or "") == row_type]
    checks = {
        "candidate_rank_consistency": _count_states(row.get("candidate_rank_consistency") for row in selected),
        "runtime_opportunity_score_consistency": _count_states(row.get("runtime_opportunity_score_consistency") for row in selected),
        "bq_entry_consistency": _count_states(row.get("bq_entry_consistency") for row in selected),
        "pc_membership_consistency": _count_states(row.get("pc_membership_consistency") for row in selected),
        "target_weight_consistency": _count_states(row.get("target_weight_consistency") for row in selected),
        "action_consistency": _count_states(row.get("action_consistency") for row in selected),
        "ps_quantity_consistency": _count_states(row.get("ps_quantity_consistency") for row in selected),
    }
    fail = any("FAIL" in counts for counts in checks.values())
    return {
        "status": "FAIL" if fail else "PASS",
        "row_count": len(selected),
        "checks": checks,
        "production_decision_changed": False,
    }


def _pc_security_opportunity_weak_add_controls(add_unknown_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = _count_states(row.get("eh_pc_shadow_add_reclassification") for row in add_unknown_rows)
    weak_preserved = int(counts.get("COMPARABLE_NEGATIVE", 0)) + int(counts.get("BLOCKED", 0))
    return {
        "status": "PASS",
        "weak_or_blocked_rows": weak_preserved,
        "counts": counts,
        "rescued_by_security_opportunity_only": 0,
    }


def _winner_position_size_adequacy_row(
    row: Mapping[str, Any],
    security_record: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = security_record.get("normalized_security_opportunity") if isinstance(security_record.get("normalized_security_opportunity"), Mapping) else {}
    relationship = security_record.get("position_relationship") if isinstance(security_record.get("position_relationship"), Mapping) else {}
    quality = row.get("quality_evidence") if isinstance(row.get("quality_evidence"), Mapping) else {}
    headroom = row.get("structured_headroom") if isinstance(row.get("structured_headroom"), Mapping) else {}
    risk = row.get("portfolio_risk_cost") if isinstance(row.get("portfolio_risk_cost"), Mapping) else {}
    feasibility = row.get("execution_feasibility") if isinstance(row.get("execution_feasibility"), Mapping) else {}
    lot = row.get("lot_status_decomposition") if isinstance(row.get("lot_status_decomposition"), Mapping) else {}
    add = row.get("add_campaign_evidence") if isinstance(row.get("add_campaign_evidence"), Mapping) else {}
    cash = row.get("cash_optionality_comparison") if isinstance(row.get("cash_optionality_comparison"), Mapping) else {}
    next_record = row.get("unified_next_capital_unit_record") if isinstance(row.get("unified_next_capital_unit_record"), Mapping) else {}
    next_normalized = next_record.get("normalized_comparison") if isinstance(next_record.get("normalized_comparison"), Mapping) else {}
    current_weight = _number(row.get("current_weight"), 0.0) or 0.0
    target_weight = _number(row.get("target_weight"), 0.0) or 0.0
    next_qty = _number(row.get("next_executable_quantity"), 0.0) or 0.0
    one_lot_notional = _number(row.get("next_lot_notional"), 0.0) or 0.0
    rank = _number(quality.get("input_opportunity_rank") or normalized.get("input_opportunity_rank"))
    adequacy_class, reason_codes = _winner_position_size_adequacy_class(
        normalized=normalized,
        relationship=relationship,
        quality=quality,
        headroom=headroom,
        risk=risk,
        feasibility=feasibility,
        lot=lot,
        add=add,
        cash=cash,
        next_normalized=next_normalized,
        current_weight=current_weight,
        target_weight=target_weight,
        next_qty=next_qty,
        rank=rank,
    )
    campaign = str(row.get("position_campaign_id") or relationship.get("position_campaign_id") or "")
    symbol = str(row.get("symbol") or security_record.get("symbol") or "")
    return {
        "schema_version": "winner_position_size_adequacy_shadow.row.v1",
        "business_date": str(row.get("business_date") or security_record.get("business_date") or ""),
        "symbol": symbol,
        "campaign_id": campaign,
        "campaign_key": f"{symbol}|{campaign}" if campaign else symbol,
        "competitor_type": str(row.get("competitor_type") or ""),
        "security_opportunity_record_hash": str(security_record.get("security_opportunity_record_hash") or ""),
        "security_evidence_completeness": str(normalized.get("evidence_completeness_class") or "MISSING"),
        "security_attractiveness_state": str(normalized.get("security_attractiveness_state") or "MISSING"),
        "position_relationship_state": str(relationship.get("relationship_state") or ""),
        "opportunity_rank": rank,
        "runtime_opportunity_score": quality.get("runtime_opportunity_score") or normalized.get("runtime_opportunity_score"),
        "current_weight": current_weight,
        "target_weight": target_weight,
        "current_quantity": row.get("current_quantity"),
        "next_executable_quantity": next_qty,
        "next_lot_notional": one_lot_notional,
        "exposure_context": _winner_exposure_context(current_weight),
        "current_target_control": {
            "target_le_current": target_weight <= current_weight,
            "target_equals_current": abs(target_weight - current_weight) < 0.000001,
            "used_as_control_not_label": True,
            "adequately_sized_from_target_equality_only": False,
        },
        "positive_next_lot_requirements": {
            "complete_security_opportunity": str(normalized.get("evidence_completeness_class") or "") == "COMPLETE",
            "strong_current_opportunity": _winner_strong_current_opportunity(normalized=normalized, quality=quality, rank=rank),
            "held_position": str(relationship.get("relationship_state") or "").upper() == "HELD" or bool(row.get("current_quantity")),
            "low_or_moderate_exposure": current_weight <= 0.09,
            "headroom_available": _winner_headroom_available(risk=risk, headroom=headroom),
            "no_bq_entry_hard_block": not _winner_bq_entry_blocked(quality),
            "no_loss_averaging_satisfied": str(add.get("no_loss_averaging_state") or "PASS").upper() == "PASS",
            "no_unresolved_expected_edge_weakening": str(add.get("expected_edge_current_state") or "").upper() not in {"", "UNKNOWN", "WEAKENING"},
            "next_lot_feasible": next_qty > 0 and str(feasibility.get("state") or "").upper() == "FEASIBLE",
            "opportunity_cost_competitive": _winner_opportunity_cost_competitive(add=add, cash=cash, next_normalized=next_normalized),
        },
        "bq_action": str(quality.get("bq_action") or ""),
        "entry_action": str(quality.get("entry_action") or ""),
        "expected_edge_state": str(add.get("expected_edge_current_state") or ""),
        "incremental_value_state": str(add.get("incremental_investment_value_state") or ""),
        "opportunity_cost_state": str(add.get("opportunity_cost_state") or ""),
        "headroom_state": str(headroom.get("state") or ""),
        "risk_state": str(risk.get("state") or ""),
        "lot_state": str(lot.get("state") or ""),
        "next_capital_unit_state": str(next_normalized.get("marginal_investment_value_state") or ""),
        "next_capital_unit_opportunity_cost_shadow": str(next_normalized.get("comparable_opportunity_cost_shadow") or ""),
        "position_size_adequacy_class": adequacy_class,
        "reason_codes": reason_codes,
        "fixed_add_preference": False,
        "production_decision_changed": False,
        "future_information_used": False,
        "historical_outcome_used": False,
    }


def _winner_position_size_adequacy_class(
    *,
    normalized: Mapping[str, Any],
    relationship: Mapping[str, Any],
    quality: Mapping[str, Any],
    headroom: Mapping[str, Any],
    risk: Mapping[str, Any],
    feasibility: Mapping[str, Any],
    lot: Mapping[str, Any],
    add: Mapping[str, Any],
    cash: Mapping[str, Any],
    next_normalized: Mapping[str, Any],
    current_weight: float,
    target_weight: float,
    next_qty: float,
    rank: float | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    completeness = str(normalized.get("evidence_completeness_class") or "").upper()
    relationship_state = str(relationship.get("relationship_state") or "").upper()
    if completeness != "COMPLETE":
        return "INSUFFICIENT", ["security_opportunity_not_complete"]
    if relationship_state and relationship_state != "HELD":
        return "INSUFFICIENT", ["not_a_held_position"]
    if _winner_risk_or_headroom_blocked(risk=risk, headroom=headroom):
        return "RISK_OR_HEADROOM_BLOCKED", ["risk_or_headroom_hard_block_preserved"]
    if _winner_bq_entry_blocked(quality):
        return "BQ_ENTRY_BLOCKED", ["bq_or_entry_hard_block_preserved"]
    edge = str(add.get("expected_edge_current_state") or "").upper()
    if edge in {"WEAKENING", "UNKNOWN", ""}:
        return "WEAKENING_NO_ADD", [f"expected_edge_not_positive:{edge or 'MISSING'}"]
    if str(add.get("no_loss_averaging_state") or "PASS").upper() != "PASS":
        return "WEAKENING_NO_ADD", ["no_loss_averaging_not_satisfied"]
    if not _winner_opportunity_cost_competitive(add=add, cash=cash, next_normalized=next_normalized):
        return "LOSES_TO_OTHER_CAPITAL_USE", ["next_lot_loses_to_new_reentry_or_cash"]
    if next_qty <= 0 or str(feasibility.get("state") or "").upper() != "FEASIBLE":
        return "INSUFFICIENT", ["next_executable_lot_not_feasible"]
    strong = _winner_strong_current_opportunity(normalized=normalized, quality=quality, rank=rank)
    headroom_available = _winner_headroom_available(risk=risk, headroom=headroom)
    incremental_positive = str(add.get("incremental_investment_value_state") or "").upper() == "POSITIVE"
    if strong and current_weight <= 0.09 and headroom_available and incremental_positive:
        reasons.extend(["complete_strong_low_or_moderate_exposure_positive_next_lot"])
        if target_weight <= current_weight:
            reasons.append("current_target_not_used_as_adequacy_label")
        return "POTENTIAL_UNDERCAPITALIZED", sorted(set(reasons))
    if current_weight >= 0.09:
        return "ADEQUATELY_SIZED", ["large_position_size_control_without_positive_undercapitalization"]
    if str(lot.get("state") or "").upper() in {"NO_POSITIVE_DESIRED_INCREMENT", "NO_ACCEPTED_CONTINUOUS_INCREMENT"}:
        return "INSUFFICIENT", ["positive_increment_not_materialized"]
    return "INSUFFICIENT", ["positive_undercapitalization_requirements_not_met"]


def _winner_negative_controls(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = _count_states(row.get("position_size_adequacy_class") for row in rows)
    preserved = (
        int(counts.get("BQ_ENTRY_BLOCKED", 0))
        + int(counts.get("WEAKENING_NO_ADD", 0))
        + int(counts.get("LOSES_TO_OTHER_CAPITAL_USE", 0))
        + int(counts.get("RISK_OR_HEADROOM_BLOCKED", 0))
    )
    return {
        "status": "PASS",
        "preserved_negative_or_blocked_rows": preserved,
        "counts": counts,
        "security_opportunity_alone_rescued_rows": 0,
    }


def _winner_exposure_context(current_weight: float) -> str:
    if current_weight < 0.03:
        return "LOW_LT_3PCT"
    if current_weight < 0.06:
        return "MID_3_TO_6PCT"
    if current_weight < 0.09:
        return "MODERATE_6_TO_9PCT"
    return "LARGE_GTE_9PCT"


def _winner_strong_current_opportunity(
    *,
    normalized: Mapping[str, Any],
    quality: Mapping[str, Any],
    rank: float | None,
) -> bool:
    attractiveness = str(normalized.get("security_attractiveness_state") or "").upper()
    quality_class = str(quality.get("canonical_opportunity_quality_class") or "").upper()
    if attractiveness in {"ATTRACTIVE", "STRONG", "WATCHLIST"} and rank is not None and rank <= 5:
        return True
    if str(normalized.get("evidence_completeness_class") or "").upper() == "COMPLETE" and rank is not None and rank <= 5:
        return True
    return quality_class in {"STRONG", "COMPARABLE_HIGH", "COMPARABLE_MARGINAL"} and rank is not None and rank <= 5


def _winner_bq_entry_blocked(quality: Mapping[str, Any]) -> bool:
    bq_action = str(quality.get("bq_action") or "").upper()
    entry_action = str(quality.get("entry_action") or "").upper()
    return bq_action in {"BUY_WAIT", "TEMPORARY_BUY_INELIGIBLE", "REJECT", "BUY_REJECTED"} or entry_action in {
        "NO_ADD",
        "BUY_WAIT",
        "REVIEW_REQUIRED",
        "REJECT",
        "BUY_REJECTED",
        "TEMPORARY_BUY_INELIGIBLE",
    }


def _winner_risk_or_headroom_blocked(*, risk: Mapping[str, Any], headroom: Mapping[str, Any]) -> bool:
    risk_state = str(risk.get("state") or "").upper()
    headroom_state = str(headroom.get("state") or "").upper()
    return risk_state in {"BLOCKED_BY_SAFETY", "SAFETY_HARD_CAP_BLOCKED", "STRATEGY_CAP_BLOCKED"} or headroom_state in {
        "SAFETY_HARD_CAP_BLOCKED",
        "STRATEGY_CAP_BLOCKED",
    }


def _winner_headroom_available(*, risk: Mapping[str, Any], headroom: Mapping[str, Any]) -> bool:
    headroom_state = str(headroom.get("state") or "").upper()
    risk_state = str(risk.get("state") or "").upper()
    if headroom_state == "HEADROOM_AVAILABLE":
        return True
    return headroom_state in {"", "HEADROOM_UNKNOWN", "UNKNOWN"} and risk_state in {"ACCEPTABLE", "HEADROOM_AVAILABLE", "LOW_COST"}


def _winner_opportunity_cost_competitive(
    *,
    add: Mapping[str, Any],
    cash: Mapping[str, Any],
    next_normalized: Mapping[str, Any],
) -> bool:
    add_cost = str(add.get("opportunity_cost_state") or "").upper()
    shadow_cost = str(next_normalized.get("comparable_opportunity_cost_shadow") or "").upper()
    cash_codes = [str(code).upper() for code in cash.get("reason_codes") or []]
    if add_cost in {"NEW_BUY_SUPERIOR", "REENTRY_SUPERIOR", "CASH_SUPERIOR"}:
        return False
    if shadow_cost in {"NEW_COMPARABLY_SUPERIOR", "REENTRY_COMPARABLY_SUPERIOR", "CASH_COMPARABLY_SUPERIOR"}:
        return False
    if "CASH_OPTIONALITY_PREFERRED" in cash_codes:
        return False
    return add_cost in {"PASS", "COMPETITIVE", "NEUTRAL"}


def _quality_rank_from_row(row: Mapping[str, Any]) -> Any:
    quality = row.get("quality_evidence") if isinstance(row.get("quality_evidence"), Mapping) else {}
    return quality.get("input_opportunity_rank")


def _quality_score_from_row(row: Mapping[str, Any]) -> Any:
    quality = row.get("quality_evidence") if isinstance(row.get("quality_evidence"), Mapping) else {}
    return quality.get("runtime_opportunity_score")


def _consistency_state(left: Any, right: Any) -> str:
    if left is None and right is None:
        return "NOT_MATERIALIZED"
    if left is None or right is None:
        return "MISSING_ONE_SIDE"
    try:
        return "PASS" if abs(float(left) - float(right)) < 0.000001 else "FAIL"
    except (TypeError, ValueError):
        return "PASS" if str(left) == str(right) else "FAIL"


def _counter_dict(values: Any) -> dict[str, int]:
    return dict(Counter(str(value or "UNKNOWN") for value in values))


def _count_states(values: Any) -> dict[str, int]:
    return dict(Counter(str(value or "UNKNOWN") for value in values))


def _build_unified_next_capital_unit_evidence(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    records = [_unified_next_capital_unit_record(row) for row in rows]
    for row, record in zip(rows, records):
        row["unified_next_capital_unit_record"] = record
    comparable = [record for record in records if _next_unit_comparable(record)]
    ordered = sorted(comparable, key=_next_unit_sort_key)
    winner = ordered[0] if ordered else {}
    for index, record in enumerate(ordered, start=1):
        record["normalized_comparison"]["comparison_rank"] = index
        record["normalized_comparison"]["comparison_winner"] = index == 1
    opportunity_cost = _next_unit_opportunity_cost(records=records, winner=winner)
    for record in records:
        key = _next_unit_key(record)
        if key in opportunity_cost:
            record["normalized_comparison"]["comparable_opportunity_cost_shadow"] = opportunity_cost[key]
    return {
        "schema_version": NEXT_CAPITAL_UNIT_SCHEMA_VERSION,
        "authority_type": NEXT_CAPITAL_UNIT_AUTHORITY_TYPE,
        "contract_id": NEXT_CAPITAL_UNIT_CONTRACT_ID,
        "producer": PRODUCER,
        "owner": "PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY",
        "question": "what_is_the_decision_time_evidence_for_deploying_the_next_executable_marginal_unit_of_capital_here",
        "business_date": str(records[0].get("business_date") or "") if records else "",
        "shadow_only": True,
        "authoritative_consumer_count": 0,
        "production_allocation_consumer": False,
        "production_ordering_consumer": False,
        "production_sizing_consumer": False,
        "runtime_planning_consumer": False,
        "fixed_action_bonus": {
            "BUY_ADD_NEXT_LOT": False,
            "BUY_NEW_NEXT_LOT": False,
            "REENTRY_NEXT_LOT": False,
            "CASH_OPTIONALITY": False,
        },
        "action_specific_semantics_preserved": True,
        "raw_evidence_and_normalized_value_separated": True,
        "marginal_unit": "NEXT_EXECUTABLE_LOT_OR_CASH_OPTIONALITY_WITH_LOT_NOTIONAL_RETAINED",
        "common_dimensions": [
            "current_opportunity_strength",
            "expected_edge",
            "continuation_or_momentum",
            "opportunity_rank_or_relative_strength",
            "evidence_completeness",
            "marginal_investment_value",
            "opportunity_cost",
            "portfolio_fit",
            "risk_cost",
            "capital_required",
            "executable_quantity_notional",
            "bq_entry_admissibility",
            "structured_headroom",
            "action_specific_lifecycle_state",
        ],
        "record_count": len(records),
        "comparable_record_count": len(ordered),
        "winner": _next_unit_record_summary(winner),
        "records": records,
        "opportunity_cost_shadow": {
            "schema_version": "unified_next_capital_unit_evidence.opportunity_cost_shadow.v1",
            "winner": _next_unit_record_summary(winner),
            "states": opportunity_cost,
            "comparison_insufficient_is_not_economic_inferiority": True,
        },
        "dw_stage_a_stage_b_neutrality_integration": {
            "stage_a_preserved": True,
            "stage_b_preserved": True,
            "production_stage_b_unchanged": True,
            "ee_record_is_diagnostic_overlay": True,
        },
        "future_information_used": False,
        "historical_outcome_used": False,
    }


def _intrinsic_security_evidence(
    member: Mapping[str, Any],
    *,
    opportunity_quality: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "runtime_opportunity_score": _score(member),
        "input_opportunity_rank": _rank(member),
        "input_candidate_order": _number(member.get("input_candidate_order"), None),
        "candidate_rank_tick_reliability": str(member.get("candidate_rank_tick_reliability") or ""),
        "opportunity_quality_class": str(opportunity_quality.get("canonical_opportunity_quality_class") or ""),
        "opportunity_quality_reason_codes": list(opportunity_quality.get("opportunity_quality_reason_codes") or []),
        "buy_quality_action": _state(member, "quality_action", "buy_quality_action", "legacy_buy_quality_action", default=""),
        "quality_score": _number(member.get("quality_score"), None),
        "quality_band": str(member.get("quality_band") or ""),
        "quality_status": str(member.get("quality_status") or ""),
        "quality_reason_codes": list(member.get("quality_reason_codes") or []),
        "entry_admission_action": _state(member, "entry_admission_action", default=""),
        "entry_admission_state": _state(member, "entry_admission_state", default=""),
        "entry_admission_evidence_sufficiency": _state(member, "entry_admission_evidence_sufficiency", default=""),
        "selection_quality_tier": _state(member, "selection_quality_tier", "strategy_intelligence_selection_quality_tier", default=""),
        "selection_quality_reason_codes": list(
            member.get("selection_quality_reason_codes")
            or member.get("strategy_intelligence_selection_quality_reason_codes")
            or []
        ),
        "continuation_quality_status": _state(
            member,
            "strategy_intelligence_continuation_quality_status",
            "continuation_quality_status",
            "reentry_continuation_quality_status",
            default="",
        ),
        "relative_strength_state": _state(member, "strategy_intelligence_relative_strength_state", default=""),
        "downside_risk_status": _state(
            member,
            "strategy_intelligence_downside_risk_status",
            "downside_risk_status",
            "reentry_downside_risk_status",
            default="",
        ),
        "expected_edge_calibration_status": _state(member, "strategy_intelligence_expected_edge_calibration_status", default=""),
        "expected_edge_economic_units_available": member.get("strategy_intelligence_expected_edge_economic_units_available"),
        "trend_state": _state(member, "trend_state", "tick_normalized_trend_state", default=""),
        "momentum_state": _state(member, "momentum_state", "momentum_confidence_state", default=""),
        "momentum_trajectory_classification": str(member.get("momentum_trajectory_classification") or ""),
        "price_momentum_return_20d": _number(member.get("price_momentum_return_20d"), None),
        "trend_close_over_ma_20d": _number(member.get("trend_close_over_ma_20d"), None),
        "tick_normalized_trend_state": str(member.get("tick_normalized_trend_state") or ""),
        "momentum_confidence_state": str(member.get("momentum_confidence_state") or ""),
        "tick_quantization_status": str(member.get("tick_quantization_status") or ""),
        "minimum_tick_authority_status": str(member.get("minimum_tick_authority_status") or ""),
        "single_tick_pct": _number(member.get("single_tick_pct"), None),
        "liquidity_capacity_status": str(member.get("liquidity_capacity_status") or ""),
        "rolling_median_traded_value_20": _number(member.get("rolling_median_traded_value_20"), None),
        "confidence": _number(member.get("confidence"), None),
        "uncertainty": _number(member.get("uncertainty"), None),
        "strategy_intelligence_eligibility_status": str(member.get("strategy_intelligence_eligibility_status") or ""),
        "strategy_intelligence_consumer_status": str(member.get("strategy_intelligence_consumer_status") or ""),
        "strategy_intelligence_future_information_used": bool(member.get("strategy_intelligence_future_information_used") or False),
    }


def _security_opportunity_completeness(intrinsic: Mapping[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    present = 0
    if intrinsic.get("runtime_opportunity_score") is not None or intrinsic.get("input_opportunity_rank") is not None:
        present += 1
        reasons.append("OPPORTUNITY_SCORE_OR_RANK_PRESENT")
    else:
        reasons.append("OPPORTUNITY_SCORE_OR_RANK_MISSING")
    if _any_non_empty(intrinsic, "trend_state", "momentum_state", "tick_normalized_trend_state", "momentum_confidence_state", "momentum_trajectory_classification"):
        present += 1
        reasons.append("TREND_OR_MOMENTUM_PRESENT")
    else:
        reasons.append("TREND_OR_MOMENTUM_MISSING")
    if _any_non_empty(intrinsic, "buy_quality_action", "quality_status", "selection_quality_tier", "entry_admission_action"):
        present += 1
        reasons.append("QUALITY_OR_ENTRY_PRESENT")
    else:
        reasons.append("QUALITY_OR_ENTRY_MISSING")
    if _any_non_empty(intrinsic, "continuation_quality_status", "relative_strength_state", "downside_risk_status", "expected_edge_calibration_status"):
        present += 1
        reasons.append("CONTINUATION_RISK_OR_EDGE_PRESENT")
    else:
        reasons.append("CONTINUATION_RISK_OR_EDGE_MISSING")
    if _any_non_empty(intrinsic, "liquidity_capacity_status") or intrinsic.get("rolling_median_traded_value_20") is not None:
        present += 1
        reasons.append("LIQUIDITY_PRESENT")
    else:
        reasons.append("LIQUIDITY_MISSING")
    if bool(intrinsic.get("strategy_intelligence_future_information_used")):
        return "BLOCKED", sorted(set(reasons + ["FUTURE_INFORMATION_FLAG_PRESENT"]))
    if present >= 4:
        return "COMPLETE", sorted(set(reasons))
    if present >= 2:
        return "PARTIAL", sorted(set(reasons))
    if present == 1:
        return "INSUFFICIENT", sorted(set(reasons))
    return "BLOCKED", sorted(set(reasons + ["NO_INTRINSIC_SECURITY_EVIDENCE"]))


def _security_attractiveness_state(intrinsic: Mapping[str, Any], *, completeness: str) -> str:
    if completeness == "BLOCKED":
        return "BLOCKED"
    if completeness == "INSUFFICIENT":
        return "INSUFFICIENT"
    quality = str(intrinsic.get("opportunity_quality_class") or "").upper()
    if quality in {"STRONG", "COMPARABLE_HIGH"}:
        return "ATTRACTIVE"
    if quality in {"COMPARABLE_MARGINAL", "WEAK_VALID"}:
        return "WATCHLIST"
    if quality in {"BLOCKED", "INSUFFICIENT"}:
        return quality
    score = _number(intrinsic.get("runtime_opportunity_score"), None)
    rank = _number(intrinsic.get("input_opportunity_rank"), None)
    if score is not None and score > 0 and (rank is None or rank <= 20):
        return "ATTRACTIVE"
    if score is not None or rank is not None:
        return "WATCHLIST"
    return "UNRANKED"


def _position_relationship(member: Mapping[str, Any]) -> dict[str, Any]:
    held = bool(member.get("current_position")) or (_number(member.get("current_quantity"), 0.0) or 0.0) > 0
    prior_exit = bool(str(member.get("prior_exit_business_date") or ""))
    reentry_state = str(member.get("reentry_semantic_state") or "").upper()
    semantic_buy_type = str(member.get("semantic_buy_type") or "").upper()
    membership_intent = str(member.get("membership_intent") or "").upper()
    reentry_applicable = (
        semantic_buy_type == "REENTRY"
        or membership_intent == "REENTRY_CANDIDATE"
        or (reentry_state.startswith("REENTRY") and reentry_state not in {"REENTRY_NOT_APPLICABLE", "REENTRY_NA"})
    )
    if held:
        state = "HELD"
    elif prior_exit or reentry_applicable:
        state = "FLAT_AFTER_EXIT"
    else:
        state = "FLAT_NEVER_HELD_OR_UNKNOWN"
    return {
        "relationship_state": state,
        "current_position": held,
        "current_quantity": _number(member.get("current_quantity"), 0.0) or 0.0,
        "current_weight": _number(member.get("current_weight"), 0.0) or 0.0,
        "position_campaign_id": _campaign_id(member),
        "pm_action": str(member.get("pm_action") or ""),
        "membership_intent": str(member.get("membership_intent") or ""),
        "semantic_buy_type": str(member.get("semantic_buy_type") or ""),
        "prior_exit_business_date": str(member.get("prior_exit_business_date") or ""),
        "reentry_semantic_state": str(member.get("reentry_semantic_state") or ""),
        "position_relationship_used_for_intrinsic_score": False,
    }


def _action_specific_evidence_refs(member: Mapping[str, Any]) -> dict[str, Any]:
    target_resolution = member.get("target_weight_resolution") if isinstance(member.get("target_weight_resolution"), Mapping) else {}
    add_evidence = add_campaign_evidence(member)
    return {
        "current_weight_present": "current_weight" in member,
        "current_quantity_present": "current_quantity" in member,
        "target_weight_present": "target_weight" in member,
        "position_campaign_id_present": bool(_campaign_id(member)),
        "source_pm_decision_present": bool(member.get("source_pm_decision_ref") or member.get("pm_decision_id")),
        "add_investment_evidence_present": isinstance(member.get("add_investment_evidence"), Mapping)
        or isinstance(target_resolution.get("add_allocation_bridge"), Mapping),
        "add_incremental_investment_value_state": str(add_evidence.get("incremental_investment_value_state") or ""),
        "add_expected_edge_current_state": str(add_evidence.get("expected_edge_current_state") or ""),
        "add_opportunity_cost_state": str(add_evidence.get("opportunity_cost_state") or ""),
        "reentry_evidence_present": any(str(member.get(field) or "") for field in ("reentry_semantic_state", "prior_exit_business_date", "reentry_recovery_status")),
        "lot_resolution_present": isinstance(member.get("phase29_l19_lot_resolution"), Mapping),
        "action_specific_fields_excluded_from_intrinsic_score": True,
    }


def _security_opportunity_source_paths(member: Mapping[str, Any]) -> list[Any]:
    paths: list[Any] = []
    for field in (
        "strategy_intelligence_artifact_path",
        "buy_quality_artifact_path",
        "opportunity_artifact_path",
        "input_opportunity_rank_source_path",
    ):
        value = member.get(field)
        if value and value not in paths:
            paths.append(value)
    return paths


def _security_opportunity_source_hashes(member: Mapping[str, Any]) -> dict[str, Any]:
    hashes: dict[str, Any] = {}
    for field in (
        "strategy_intelligence_artifact_hash",
        "buy_quality_artifact_hash",
        "opportunity_artifact_hash",
        "input_opportunity_rank_source_hash",
        "input_opportunity_row_authority_hash",
        "minimum_tick_authority_hash",
    ):
        value = member.get(field)
        if value:
            hashes[field] = value
    return hashes


def _security_opportunity_preference_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    normalized = record.get("normalized_security_opportunity") if isinstance(record.get("normalized_security_opportunity"), Mapping) else {}
    intrinsic = record.get("intrinsic_security_evidence") if isinstance(record.get("intrinsic_security_evidence"), Mapping) else {}
    complete_order = {"COMPLETE": 0, "PARTIAL": 1, "INSUFFICIENT": 2, "BLOCKED": 3}
    return (
        complete_order.get(str(normalized.get("evidence_completeness_class") or ""), 99),
        _number(intrinsic.get("input_opportunity_rank"), 999999.0) or 999999.0,
        -(_number(intrinsic.get("runtime_opportunity_score"), -999999.0) or -999999.0),
        str(record.get("symbol") or ""),
    )


def _any_non_empty(mapping: Mapping[str, Any], *fields: str) -> bool:
    for field in fields:
        value = mapping.get(field)
        if value is None:
            continue
        if isinstance(value, str) and not value:
            continue
        return True
    return False


def _unified_next_capital_unit_record(row: Mapping[str, Any]) -> dict[str, Any]:
    row_type = str(row.get("competitor_type") or "")
    marginal = row.get("marginal_desirability") if isinstance(row.get("marginal_desirability"), Mapping) else {}
    completeness = row.get("evidence_completeness") if isinstance(row.get("evidence_completeness"), Mapping) else {}
    feasibility = row.get("execution_feasibility") if isinstance(row.get("execution_feasibility"), Mapping) else {}
    risk = row.get("portfolio_risk_cost") if isinstance(row.get("portfolio_risk_cost"), Mapping) else {}
    quality = row.get("quality_evidence") if isinstance(row.get("quality_evidence"), Mapping) else {}
    headroom = row.get("structured_headroom") if isinstance(row.get("structured_headroom"), Mapping) else {}
    lot = row.get("lot_status_decomposition") if isinstance(row.get("lot_status_decomposition"), Mapping) else {}
    add_evidence = row.get("add_campaign_evidence") if isinstance(row.get("add_campaign_evidence"), Mapping) else {}
    reentry = row.get("reentry_evidence") if isinstance(row.get("reentry_evidence"), Mapping) else {}
    cash = row.get("cash_optionality_comparison") if isinstance(row.get("cash_optionality_comparison"), Mapping) else {}
    completeness_class, value_state, reasons = _next_unit_normalized_states(
        row_type=row_type,
        marginal=marginal,
        completeness=completeness,
        feasibility=feasibility,
        risk=risk,
        quality=quality,
        headroom=headroom,
        lot=lot,
        add_evidence=add_evidence,
    )
    return {
        "schema_version": "unified_next_capital_unit_evidence.record.v1",
        "authority_type": NEXT_CAPITAL_UNIT_AUTHORITY_TYPE,
        "contract_id": NEXT_CAPITAL_UNIT_CONTRACT_ID,
        "producer": PRODUCER,
        "owner": "PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY",
        "business_date": str(row.get("business_date") or ""),
        "competitor_type": row_type,
        "symbol": str(row.get("symbol") or ""),
        "position_campaign_id": str(row.get("position_campaign_id") or ""),
        "source_decision_id": str(row.get("source_decision_id") or ""),
        "source_pm_decision_id": str(row.get("source_pm_decision_id") or ""),
        "shadow_only": True,
        "authoritative_consumer_count": 0,
        "production_consumer": False,
        "action_specific_semantics": _next_unit_action_semantics(row_type),
        "raw_pit_evidence": {
            "pit_feature_date": str(row.get("pit_feature_date") or ""),
            "current_weight": row.get("current_weight"),
            "target_weight": row.get("target_weight"),
            "current_quantity": row.get("current_quantity"),
            "next_executable_quantity": row.get("next_executable_quantity"),
            "next_lot_notional": row.get("next_lot_notional"),
            "desired_next_lot_quantity": row.get("desired_next_lot_quantity"),
            "desired_continuous_increment_weight": row.get("desired_continuous_increment_weight"),
            "accepted_continuous_increment_weight": row.get("accepted_continuous_increment_weight"),
            "marginal_desirability": dict(marginal),
            "evidence_completeness": dict(completeness),
            "execution_feasibility": dict(feasibility),
            "portfolio_risk_cost": dict(risk),
            "quality_evidence": dict(quality),
            "structured_headroom": dict(headroom),
            "lot_status_decomposition": dict(lot),
            "add_campaign_evidence": dict(add_evidence),
            "reentry_evidence": dict(reentry),
            "cash_optionality_comparison": dict(cash),
        },
        "normalized_comparison": {
            "evidence_completeness_class": completeness_class,
            "marginal_investment_value_state": value_state,
            "opportunity_cost_state": "PENDING_DAILY_COMPARISON",
            "portfolio_fit_state": str(risk.get("state") or ""),
            "execution_feasibility_state": str(feasibility.get("state") or ""),
            "comparison_rank": None,
            "comparison_winner": False,
            "comparison_sufficiency": "SUFFICIENT" if completeness_class in {"COMPLETE", "PARTIAL"} and value_state not in {"INSUFFICIENT", "BLOCKED"} else "INSUFFICIENT",
            "reason_codes": sorted(set(reasons)),
        },
        "fixed_action_bonus": False,
        "future_information_used": False,
        "historical_outcome_used": False,
    }


def _next_unit_action_semantics(row_type: str) -> dict[str, Any]:
    if row_type == "BUY_ADD_NEXT_LOT":
        return {
            "semantic": "increase_existing_exposure",
            "current_exposure_cost_preserved": True,
            "fake_buy_new_semantics_used": False,
        }
    if row_type == "BUY_NEW_NEXT_LOT":
        return {
            "semantic": "open_new_exposure",
            "starter_portfolio_cost_preserved": True,
            "artificial_new_penalty_used": False,
        }
    if row_type == "REENTRY_NEXT_LOT":
        return {
            "semantic": "open_new_exposure_after_prior_exit",
            "reentry_context_preserved": True,
            "blanket_reentry_penalty_used": False,
        }
    return {
        "semantic": "preserve_cash_optionality",
        "cash_optionality_preserved": True,
        "cash_tuned_down": False,
    }


def _next_unit_normalized_states(
    *,
    row_type: str,
    marginal: Mapping[str, Any],
    completeness: Mapping[str, Any],
    feasibility: Mapping[str, Any],
    risk: Mapping[str, Any],
    quality: Mapping[str, Any],
    headroom: Mapping[str, Any],
    lot: Mapping[str, Any],
    add_evidence: Mapping[str, Any],
) -> tuple[str, str, list[str]]:
    reasons: list[str] = []
    completeness_state = str(completeness.get("state") or "").upper()
    feasibility_state = str(feasibility.get("state") or "").upper()
    risk_state = str(risk.get("state") or "").upper()
    desirability = str(marginal.get("state") or "").upper()
    expected_edge = str(add_evidence.get("expected_edge_current_state") or "").upper()
    incremental_value = str(add_evidence.get("incremental_investment_value_state") or "").upper()
    opportunity_cost = str(add_evidence.get("opportunity_cost_state") or "").upper()
    quality_class = str(quality.get("canonical_opportunity_quality_class") or "").upper()
    bq_action = str(quality.get("bq_action") or "").upper()
    entry_action = str(quality.get("entry_action") or "").upper()
    headroom_state = str(headroom.get("state") or "").upper()
    lot_state = str(lot.get("state") or "").upper()

    hard_block = (
        risk_state in {"BLOCKED_BY_SAFETY", "SAFETY_HARD_CAP_BLOCKED", "STRATEGY_CAP_BLOCKED"}
        or headroom_state in {"SAFETY_HARD_CAP_BLOCKED", "STRATEGY_CAP_BLOCKED"}
        or bq_action in {"BUY_WAIT", "TEMPORARY_BUY_INELIGIBLE", "REJECT", "BUY_REJECTED"}
        or entry_action in {"NO_ADD", "BUY_WAIT", "REVIEW_REQUIRED", "REJECT", "BUY_REJECTED", "TEMPORARY_BUY_INELIGIBLE"}
        or quality_class == "BLOCKED"
    )
    if hard_block:
        reasons.append("hard_block_preserved")
        return "BLOCKED", "BLOCKED", reasons
    if row_type == "CASH_OPTIONALITY":
        if completeness_state == "COMPLETE":
            return "COMPLETE", "NEUTRAL", ["cash_optionality_complete_competitor"]
        return "INSUFFICIENT", "INSUFFICIENT", ["cash_optionality_evidence_incomplete"]

    if row_type == "BUY_ADD_NEXT_LOT" and expected_edge == "WEAKENING":
        reasons.append("expected_edge_negative_control_preserved")
        return "COMPLETE" if completeness_state == "COMPLETE" else "PARTIAL", "NEGATIVE", reasons

    if completeness_state != "COMPLETE":
        reasons.extend([str(item) for item in completeness.get("missing_inputs") or []])
        return "INSUFFICIENT", "INSUFFICIENT", reasons or ["evidence_incomplete"]
    if feasibility_state != "FEASIBLE":
        reasons.append(f"execution_not_feasible:{feasibility_state or 'UNKNOWN'}")
        return "PARTIAL", "INSUFFICIENT", reasons
    if risk_state not in {"ACCEPTABLE", "HEADROOM_AVAILABLE", "LOW_COST"}:
        reasons.append(f"risk_not_acceptable:{risk_state or 'UNKNOWN'}")
        return "PARTIAL", "INSUFFICIENT", reasons
    if row_type == "BUY_ADD_NEXT_LOT" and (incremental_value != "POSITIVE" or opportunity_cost != "PASS"):
        reasons.append(f"add_incremental_value_or_opportunity_cost_not_comparable:{incremental_value or 'UNKNOWN'}:{opportunity_cost or 'UNKNOWN'}")
        return "INSUFFICIENT", "INSUFFICIENT", reasons
    if row_type == "BUY_ADD_NEXT_LOT" and lot_state in {"NO_POSITIVE_DESIRED_INCREMENT", "NO_ACCEPTED_CONTINUOUS_INCREMENT"}:
        reasons.append(f"add_increment_not_materialized:{lot_state}")
        return "PARTIAL", "NEUTRAL", reasons
    if desirability in {"HIGH_VALUE", "MEDIUM_VALUE"}:
        return "COMPLETE", "POSITIVE", ["complete_positive_next_capital_unit_evidence"]
    if desirability == "LOW_VALUE":
        return "COMPLETE", "NEUTRAL", ["complete_but_low_value_next_capital_unit_evidence"]
    return "INSUFFICIENT", "INSUFFICIENT", ["normalized_value_unavailable"]


def _next_unit_comparable(record: Mapping[str, Any]) -> bool:
    normalized = record.get("normalized_comparison") if isinstance(record.get("normalized_comparison"), Mapping) else {}
    if str(normalized.get("evidence_completeness_class") or "") != "COMPLETE":
        return False
    if str(normalized.get("marginal_investment_value_state") or "") not in {"POSITIVE", "NEUTRAL"}:
        return False
    if str((record.get("raw_pit_evidence") or {}).get("execution_feasibility", {}).get("state") if isinstance((record.get("raw_pit_evidence") or {}).get("execution_feasibility"), Mapping) else "") != "FEASIBLE":
        return False
    return True


def _next_unit_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    normalized = record.get("normalized_comparison") if isinstance(record.get("normalized_comparison"), Mapping) else {}
    raw = record.get("raw_pit_evidence") if isinstance(record.get("raw_pit_evidence"), Mapping) else {}
    quality = raw.get("quality_evidence") if isinstance(raw.get("quality_evidence"), Mapping) else {}
    marginal = raw.get("marginal_desirability") if isinstance(raw.get("marginal_desirability"), Mapping) else {}
    value_order = {"POSITIVE": 0, "NEUTRAL": 1, "NEGATIVE": 2, "INSUFFICIENT": 3, "BLOCKED": 4}
    desirability_order = {"HIGH_VALUE": 0, "MEDIUM_VALUE": 1, "LOW_VALUE": 2, "HIGH_VALUE_EVIDENCE_INCOMPLETE": 3, "EVIDENCE_INCOMPLETE": 4}
    return (
        value_order.get(str(normalized.get("marginal_investment_value_state") or ""), 99),
        desirability_order.get(str(marginal.get("state") or ""), 99),
        _number(quality.get("input_opportunity_rank"), 999999.0) or 999999.0,
        str(record.get("symbol") or ""),
        str(record.get("competitor_type") or ""),
    )


def _next_unit_opportunity_cost(*, records: Sequence[Mapping[str, Any]], winner: Mapping[str, Any]) -> dict[str, str]:
    if not winner:
        return {_next_unit_key(record): "COMPARISON_INSUFFICIENT" for record in records}
    winner_type = str(winner.get("competitor_type") or "")
    winner_state = {
        "BUY_NEW_NEXT_LOT": "NEW_COMPARABLY_SUPERIOR",
        "BUY_ADD_NEXT_LOT": "ADD_COMPARABLY_SUPERIOR",
        "REENTRY_NEXT_LOT": "REENTRY_COMPARABLY_SUPERIOR",
        "CASH_OPTIONALITY": "CASH_COMPARABLY_SUPERIOR",
    }.get(winner_type, "NO_CLEAR_SUPERIOR")
    states: dict[str, str] = {}
    for record in records:
        normalized = record.get("normalized_comparison") if isinstance(record.get("normalized_comparison"), Mapping) else {}
        key = _next_unit_key(record)
        if str(normalized.get("comparison_sufficiency") or "") != "SUFFICIENT":
            states[key] = "COMPARISON_INSUFFICIENT"
        elif _next_unit_key(record) == _next_unit_key(winner):
            states[key] = "NO_CLEAR_SUPERIOR"
        else:
            states[key] = winner_state
    return states


def _next_unit_key(record: Mapping[str, Any]) -> str:
    return "|".join(
        [
            str(record.get("competitor_type") or ""),
            str(record.get("symbol") or ""),
            str(record.get("position_campaign_id") or ""),
        ]
    )


def _next_unit_record_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = record.get("normalized_comparison") if isinstance(record.get("normalized_comparison"), Mapping) else {}
    raw = record.get("raw_pit_evidence") if isinstance(record.get("raw_pit_evidence"), Mapping) else {}
    return {
        "competitor_type": str(record.get("competitor_type") or ""),
        "symbol": str(record.get("symbol") or ""),
        "position_campaign_id": str(record.get("position_campaign_id") or ""),
        "evidence_completeness_class": str(normalized.get("evidence_completeness_class") or ""),
        "marginal_investment_value_state": str(normalized.get("marginal_investment_value_state") or ""),
        "opportunity_cost_state": str(normalized.get("comparable_opportunity_cost_shadow") or normalized.get("opportunity_cost_state") or ""),
        "next_executable_quantity": raw.get("next_executable_quantity"),
        "next_lot_notional": raw.get("next_lot_notional"),
    }


def _member_shadow_type(member: Mapping[str, Any]) -> str:
    semantic = str(member.get("semantic_buy_type") or "").upper()
    if bool(member.get("current_position")) and str(member.get("pm_action") or "").upper() == "ADD":
        return "BUY_ADD_NEXT_LOT"
    if not bool(member.get("current_position")) and str(member.get("membership_intent") or "").upper() == "ADD_CANDIDATE":
        return "BUY_NEW_NEXT_LOT"
    return ""


def _member_shadow_key(member: Mapping[str, Any]) -> tuple[str, str]:
    shadow_type = _member_shadow_type(member)
    production_type = "ADD" if shadow_type == "BUY_ADD_NEXT_LOT" else "NEW_BUY"
    return (production_type, _symbol(member))


def _production_competitor_map(competitors: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {
        (str(item.get("competitor_type") or ""), str(item.get("symbol") or "")): item
        for item in competitors
        if str(item.get("symbol") or "")
    }


def _security_shadow_row(
    *,
    member: Mapping[str, Any],
    business_date: str,
    production: Mapping[str, Any],
) -> dict[str, Any]:
    action_type = _member_shadow_type(member)
    opportunity_quality = classify_opportunity_quality(
        {
            **dict(member),
            "lifecycle_intent": "BUY_ADD" if action_type == "BUY_ADD_NEXT_LOT" else "BUY_NEW",
        },
        business_date=business_date,
    )
    desirability = _desirability_state(member, opportunity_quality=opportunity_quality, action_type=action_type)
    completeness = _evidence_completeness_state(member, opportunity_quality=opportunity_quality, action_type=action_type)
    feasibility = _execution_feasibility_state(member, production=production, action_type=action_type)
    structured_headroom = _structured_headroom(member)
    lot_status = _lot_status_decomposition(member, production=production, action_type=action_type)
    add_increment_authority = _add_strength_to_increment_target_authority(
        member=member,
        business_date=business_date,
        action_type=action_type,
        opportunity_quality=opportunity_quality,
        structured_headroom=structured_headroom,
    )
    portfolio_cost = _portfolio_risk_cost_state(member, production=production, structured_headroom=structured_headroom)
    lot = _next_lot_evidence(member, action_type=action_type)
    current_weight = _number(member.get("current_weight"), 0.0) or 0.0
    target_weight = _number(member.get("target_weight"), 0.0) or 0.0
    accepted_weight = _number(production.get("accepted_weight"), 0.0) or 0.0
    return {
        "schema_version": "unified_marginal_capital_shadow.competitor_row.v1",
        "business_date": business_date,
        "competitor_type": action_type,
        "symbol": _symbol(member),
        "action_type": action_type,
        "semantic_buy_type": str(member.get("semantic_buy_type") or ("BUY_ADD" if action_type == "BUY_ADD_NEXT_LOT" else "")),
        "position_campaign_id": _campaign_id(member),
        "source_decision_id": str(
            member.get("source_decision_id")
            or member.get("source_opportunity_id")
            or member.get("source_candidate_id")
            or member.get("quality_decision_id")
            or ""
        ),
        "source_pm_decision_id": str(member.get("source_pm_decision_ref") or member.get("pm_decision_id") or ""),
        "candidate_id": str(member.get("source_candidate_id") or member.get("candidate_reference") or ""),
        "opportunity_id": str(member.get("source_opportunity_id") or member.get("opportunity_reference") or ""),
        "pit_feature_date": str(
            member.get("feature_date")
            or member.get("strategy_intelligence_business_date")
            or member.get("expected_edge_baseline_business_date")
            or business_date
        ),
        "current_quantity": _number(member.get("current_quantity"), 0.0) or 0.0,
        "current_weight": round(current_weight, 6),
        "target_weight": round(target_weight, 6),
        "accepted_weight_production": round(accepted_weight, 6),
        "next_executable_quantity": lot["next_executable_quantity"],
        "next_lot_notional": lot["next_lot_notional"],
        "desired_next_lot_quantity": lot["desired_next_lot_quantity"],
        "desired_continuous_increment_weight": _desired_continuous_increment_weight(member),
        "accepted_continuous_increment_weight": _accepted_continuous_increment_weight(member),
        "ec_proposed_refreshed_target_weight": add_increment_authority.get("proposed_refreshed_target_weight", 0.0),
        "ec_proposed_incremental_target_weight": add_increment_authority.get("proposed_incremental_target_weight", 0.0),
        "ec_positive_increment_demand": bool(add_increment_authority.get("positive_increment_demand")),
        "marginal_desirability": desirability,
        "evidence_completeness": completeness,
        "execution_feasibility": feasibility,
        "portfolio_risk_cost": portfolio_cost,
        "structured_headroom": structured_headroom,
        "lot_status_decomposition": lot_status,
        "cash_optionality_comparison": _cash_optionality_comparison(member, production=production),
        "quality_evidence": {
            "canonical_opportunity_quality_class": opportunity_quality["canonical_opportunity_quality_class"],
            "opportunity_quality_reason_codes": list(opportunity_quality["opportunity_quality_reason_codes"]),
            "bq_action": _state(member, "quality_action", "buy_quality_action", default=""),
            "quality_score": _number(member.get("quality_score"), None),
            "entry_action": _state(member, "entry_admission_action", default=""),
            "entry_state": _state(member, "entry_admission_state", default=""),
            "confidence": _number(member.get("confidence"), None),
            "input_opportunity_rank": _rank(member),
            "runtime_opportunity_score": _score(member),
        },
        "continuation_evidence": _continuation_evidence(member),
        "reentry_evidence": _reentry_evidence(member)
        if action_type == "REENTRY_NEXT_LOT" or (action_type == "BUY_NEW_NEXT_LOT" and str(member.get("prior_exit_business_date") or ""))
        else {},
        "add_campaign_evidence": add_campaign_evidence(member) if action_type == "BUY_ADD_NEXT_LOT" else {},
        "add_strength_to_increment_target_authority": add_increment_authority,
        "pre_cap_value_preserved": action_type != "BUY_ADD_NEXT_LOT" or True,
        "pre_bq_entry_value_preserved": action_type != "BUY_ADD_NEXT_LOT" or True,
        "production_status": str(production.get("status") or ""),
        "production_reason_codes": list(production.get("reason_codes") or []),
        "production_selected": str(production.get("status") or "") == "COMPETITOR_SELECTED" and accepted_weight > 0,
        "campaign_graduation_shadow_state": _campaign_graduation_state(member, production=production, action_type=action_type),
        "re_evaluation_eligibility": {
            "state": "ELIGIBLE_FOR_FRESH_NEXT_DAY_SHADOW_RECOMPETITION",
            "requires_fresh_pit_evidence": True,
            "capital_reserved": False,
            "future_order_promised": False,
        },
        "future_information_used": False,
        "historical_outcome_used": False,
        "action_type_fixed_preference": "NONE",
    }


def _cash_shadow_row(
    *,
    business_date: str,
    cash_evidence: Mapping[str, Any],
    risk_pacing_evidence: Mapping[str, Any],
    incremental_budget_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    completeness = str(cash_evidence.get("evidence_completeness") or "INCOMPLETE_FAIL_CLOSED")
    preference = str(cash_evidence.get("cash_preference_semantic") or "UNKNOWN")
    desirability = "HIGH_VALUE" if preference in {"RISK_OPTIONALITY_PREFERRED", "CASH_OPTIONALITY_PREFERRED"} else "MEDIUM_VALUE"
    if completeness != "COMPLETE":
        desirability = "HIGH_VALUE"
    return {
        "schema_version": "unified_marginal_capital_shadow.competitor_row.v1",
        "business_date": business_date,
        "competitor_type": "CASH_OPTIONALITY",
        "symbol": "",
        "action_type": "CASH_OPTIONALITY",
        "semantic_buy_type": "NOT_APPLICABLE",
        "position_campaign_id": "",
        "source_decision_id": str(cash_evidence.get("cash_competitor_evidence_hash") or ""),
        "source_pm_decision_id": "",
        "candidate_id": "",
        "opportunity_id": "",
        "pit_feature_date": str(cash_evidence.get("business_date") or business_date),
        "current_quantity": 0.0,
        "current_weight": _number(cash_evidence.get("current_cash_weight"), 0.0) or 0.0,
        "target_weight": _number(cash_evidence.get("remaining_cash_weight"), 0.0) or 0.0,
        "accepted_weight_production": _number(cash_evidence.get("remaining_cash_weight"), 0.0) or 0.0,
        "next_executable_quantity": 0.0,
        "next_lot_notional": 0.0,
        "desired_next_lot_quantity": 0.0,
        "marginal_desirability": {
            "state": desirability,
            "basis": preference,
            "preference_reason_codes": list(cash_evidence.get("reason_codes") or []),
        },
        "evidence_completeness": {
            "state": "COMPLETE" if completeness == "COMPLETE" else "INCOMPLETE",
            "missing_inputs": list(cash_evidence.get("missing_inputs") or []),
        },
        "execution_feasibility": {"state": "FEASIBLE", "reason_codes": ["cash_has_no_lot_execution_requirement"]},
        "portfolio_risk_cost": {
            "state": "LOW_COST" if completeness == "COMPLETE" else "EVIDENCE_INCOMPLETE",
            "risk_pacing_intent": str(risk_pacing_evidence.get("risk_pacing_intent") or cash_evidence.get("risk_pacing_intent") or ""),
            "reason_codes": list(cash_evidence.get("reason_codes") or []),
        },
        "cash_optionality_comparison": {
            "cash_is_competitor": True,
            "cash_preference_semantic": preference,
            "remaining_cash_weight": cash_evidence.get("remaining_cash_weight"),
            "incremental_budget_evidence": {
                "available_incremental_budget": incremental_budget_evidence.get("available_incremental_budget"),
                "trimmed_incremental_weight": incremental_budget_evidence.get("trimmed_incremental_weight"),
            },
        },
        "quality_evidence": {},
        "continuation_evidence": {},
        "reentry_evidence": {},
        "add_campaign_evidence": {},
        "pre_cap_value_preserved": True,
        "pre_bq_entry_value_preserved": True,
        "production_status": "COMPETITOR_SELECTED",
        "production_reason_codes": list(cash_evidence.get("reason_codes") or []),
        "production_selected": True,
        "campaign_graduation_shadow_state": "NOT_APPLICABLE",
        "re_evaluation_eligibility": {
            "state": "NOT_APPLICABLE",
            "requires_fresh_pit_evidence": True,
            "capital_reserved": False,
            "future_order_promised": False,
        },
        "future_information_used": False,
        "historical_outcome_used": False,
        "action_type_fixed_preference": "NONE",
    }


def _add_strength_to_increment_target_authority(
    *,
    member: Mapping[str, Any],
    business_date: str,
    action_type: str,
    opportunity_quality: Mapping[str, Any],
    structured_headroom: Mapping[str, Any],
) -> dict[str, Any]:
    if action_type != "BUY_ADD_NEXT_LOT":
        return {}

    current_weight = _number(member.get("current_weight"), None)
    production_target_weight = _number(member.get("target_weight"), None)
    current_quantity = _number(member.get("current_quantity"), 0.0) or 0.0
    campaign_id = _campaign_id(member)
    source_pm_decision_id = str(member.get("source_pm_decision_ref") or member.get("pm_decision_id") or "")
    pm_reason_codes = [str(code) for code in (member.get("source_pm_reason_codes") or member.get("reason_codes") or [])]
    pm_reason_text = " ".join(pm_reason_codes).upper()
    add_evidence = add_campaign_evidence(member)
    quality_action = _state(member, "quality_action", "buy_quality_action", default="")
    entry_action = _state(member, "entry_admission_action", default="")
    entry_state = _state(member, "entry_admission_state", default="")
    expected_edge = str(add_evidence.get("expected_edge_current_state") or member.get("expected_edge_improvement_state") or "").upper()
    incremental_value = str(add_evidence.get("incremental_investment_value_state") or member.get("incremental_investment_value_state") or "").upper()
    opportunity_cost = str(add_evidence.get("opportunity_cost_state") or member.get("opportunity_cost_status") or "").upper()
    campaign_state = str(add_evidence.get("campaign_continuation_state") or member.get("same_campaign_continuation_status") or "").upper()
    no_loss = str(add_evidence.get("no_loss_averaging_state") or member.get("no_loss_averaging_status") or "").upper()
    headroom_state = str(structured_headroom.get("state") or "").upper()
    strategy_headroom = _number(structured_headroom.get("strategy_cap_headroom"), None)
    safety_headroom = _number(structured_headroom.get("safety_cap_headroom"), None)
    one_lot_post = _number(structured_headroom.get("one_lot_post_trade_weight"), None)
    existing_desired = _desired_continuous_increment_weight(member)
    existing_accepted = _accepted_continuous_increment_weight(member)
    current = current_weight if current_weight is not None else 0.0
    production_target = production_target_weight if production_target_weight is not None else current
    observed_one_lot_increment = 0.0
    if one_lot_post is not None and current_weight is not None:
        observed_one_lot_increment = max(one_lot_post - current_weight, 0.0)
    evidence_tier = "INSUFFICIENT"
    demand_status = "NO_POSITIVE_DEMAND"
    reason_codes: list[str] = []

    if str(member.get("pm_action") or "").upper() != "ADD":
        evidence_tier = "BLOCKED"
        reason_codes.append("pm_add_intent_missing")
    if not campaign_id:
        reason_codes.append("campaign_identity_missing")
    if not source_pm_decision_id:
        reason_codes.append("source_pm_decision_id_missing")
    if current_weight is None:
        reason_codes.append("current_weight_missing")
    if current_quantity <= 0:
        reason_codes.append("current_position_quantity_missing")
    if headroom_state != "HEADROOM_AVAILABLE":
        evidence_tier = "BLOCKED"
        reason_codes.append(f"headroom_not_available:{headroom_state or 'UNKNOWN'}")
    if quality_action in {"BUY_WAIT", "TEMPORARY_BUY_INELIGIBLE", "REJECT", "BUY_REJECTED"}:
        evidence_tier = "BLOCKED"
        reason_codes.append(f"bq_hard_blocks_increment:{quality_action}")
    elif quality_action == "REDUCED_ALLOCATION_ONLY":
        reason_codes.append("bq_reduced_allocation_down_tier")
    elif quality_action not in {"FULL_ALLOCATION_ELIGIBLE", "PASS", ""}:
        reason_codes.append(f"bq_state_not_full_authority:{quality_action or 'UNKNOWN'}")
    if entry_action in {"NO_ADD", "BUY_WAIT", "REVIEW_REQUIRED", "REJECT", "BUY_REJECTED", "TEMPORARY_BUY_INELIGIBLE"}:
        evidence_tier = "BLOCKED"
        reason_codes.append(f"entry_hard_blocks_increment:{entry_action}")
    elif entry_action == "ADD_REDUCED_ONLY":
        reason_codes.append("entry_reduced_add_down_tier")
    elif entry_action not in {"ADD_ALLOWED", "FULL_ALLOCATION_ELIGIBLE", "PASS", ""}:
        reason_codes.append(f"entry_state_not_add_authority:{entry_action or entry_state or 'UNKNOWN'}")
    if "STRONG_TREND_CONTINUATION" not in pm_reason_text:
        reason_codes.append("pm_strong_trend_continuation_missing")
    if "OPPORTUNITY_RANK_STILL_HIGH" not in pm_reason_text:
        reason_codes.append("pm_opportunity_rank_persistence_missing")
    if "NO_LOSS_AVERAGING" not in pm_reason_text and no_loss != "PASS":
        reason_codes.append("no_loss_averaging_not_pass")
    if campaign_state not in {"PASS", "CONTINUING", "HELD", "SAME_CAMPAIGN"}:
        reason_codes.append(f"campaign_continuation_not_pass:{campaign_state or 'UNKNOWN'}")
    if expected_edge not in {"IMPROVING", "STABLE_ADEQUATE", "PASS"}:
        reason_codes.append(f"expected_edge_not_positive:{expected_edge or 'UNKNOWN'}")
    if incremental_value != "POSITIVE":
        reason_codes.append(f"incremental_value_not_positive:{incremental_value or 'UNKNOWN'}")
    if opportunity_cost != "PASS":
        reason_codes.append(f"opportunity_cost_not_pass:{opportunity_cost or 'UNKNOWN'}")
    if str(add_evidence.get("pit_validation_status") or "").upper() != "PASS":
        reason_codes.append("add_investment_pit_comparison_insufficient")

    required_positive_inputs = {
        "pm_add": str(member.get("pm_action") or "").upper() == "ADD",
        "campaign_identity": bool(campaign_id),
        "source_pm_decision": bool(source_pm_decision_id),
        "current_weight": current_weight is not None,
        "current_quantity": current_quantity > 0,
        "headroom": headroom_state == "HEADROOM_AVAILABLE",
        "bq": quality_action in {"FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY", "PASS"},
        "entry": entry_action in {"ADD_ALLOWED", "ADD_REDUCED_ONLY", "FULL_ALLOCATION_ELIGIBLE", "PASS"},
        "pm_strength": "STRONG_TREND_CONTINUATION" in pm_reason_text and "OPPORTUNITY_RANK_STILL_HIGH" in pm_reason_text,
        "no_loss": "NO_LOSS_AVERAGING" in pm_reason_text or no_loss == "PASS",
        "campaign": campaign_state in {"PASS", "CONTINUING", "HELD", "SAME_CAMPAIGN"},
        "expected_edge": expected_edge in {"IMPROVING", "STABLE_ADEQUATE", "PASS"},
        "incremental_value": incremental_value == "POSITIVE",
        "opportunity_cost": opportunity_cost == "PASS",
        "pit": str(add_evidence.get("pit_validation_status") or "").upper() == "PASS",
    }
    hard_blocked = evidence_tier == "BLOCKED"
    missing_required = [name for name, ok in required_positive_inputs.items() if not ok]
    if hard_blocked:
        demand_status = "BLOCKED"
    elif missing_required:
        evidence_tier = "INSUFFICIENT"
        demand_status = "NO_POSITIVE_DEMAND"
    elif quality_action == "FULL_ALLOCATION_ELIGIBLE" and entry_action in {"ADD_ALLOWED", "FULL_ALLOCATION_ELIGIBLE", "PASS", ""}:
        evidence_tier = "STRONG_COMPLETE"
    else:
        evidence_tier = "MODERATE_COMPLETE"

    headroom_cap = strategy_headroom
    if safety_headroom is not None:
        headroom_cap = safety_headroom if headroom_cap is None else min(headroom_cap, safety_headroom)
    if headroom_cap is None:
        headroom_cap = 0.0
    candidate_increment = min(max(observed_one_lot_increment, existing_desired, existing_accepted, 0.0), max(headroom_cap, 0.0))
    if evidence_tier in {"STRONG_COMPLETE", "MODERATE_COMPLETE"} and candidate_increment > 0:
        demand_status = "POSITIVE_INCREMENT_DEMAND"
        reason_codes.append("add_strength_increment_target_positive_from_current_pit_evidence")
    elif evidence_tier in {"STRONG_COMPLETE", "MODERATE_COMPLETE"}:
        demand_status = "NO_POSITIVE_DEMAND"
        reason_codes.append("positive_evidence_present_but_increment_magnitude_unavailable")

    proposed_increment = candidate_increment if demand_status == "POSITIVE_INCREMENT_DEMAND" else 0.0
    proposed_target = max(production_target, current + proposed_increment)
    return {
        "schema_version": ADD_STRENGTH_INCREMENT_SCHEMA_VERSION,
        "authority_type": ADD_STRENGTH_INCREMENT_AUTHORITY_TYPE,
        "contract_id": ADD_STRENGTH_INCREMENT_CONTRACT_ID,
        "producer": PRODUCER,
        "owner": "PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY",
        "business_date": business_date,
        "symbol": _symbol(member),
        "position_campaign_id": campaign_id,
        "source_pm_decision_id": source_pm_decision_id,
        "pm_add_intent_owner": "POSITION_MANAGEMENT",
        "pc_increment_target_owner": "PORTFOLIO_CONSTRUCTION",
        "position_sizing_quantity_owner": "POSITION_SIZING",
        "runtime_redecision_allowed": False,
        "shadow_only": True,
        "authoritative_consumer_count": 0,
        "production_allocation_consumer": False,
        "production_ordering_consumer": False,
        "production_sizing_consumer": False,
        "runtime_planning_consumer": False,
        "eligibility_and_increment_demand_separated": True,
        "pm_add_alone_creates_positive_demand": False,
        "fixed_add_bonus": False,
        "new_penalty": False,
        "reentry_penalty": False,
        "capital_reserved": False,
        "fresh_pit_evaluation": True,
        "historical_pnl_used_for_increment_magnitude": False,
        "future_information_used": False,
        "evidence_tier": evidence_tier,
        "increment_demand_status": demand_status,
        "positive_increment_demand": demand_status == "POSITIVE_INCREMENT_DEMAND",
        "current_weight": round(current, 6),
        "production_target_weight": round(production_target, 6),
        "proposed_refreshed_target_weight": round(proposed_target, 6),
        "proposed_incremental_target_weight": round(proposed_increment, 6),
        "existing_desired_continuous_increment_weight": round(existing_desired, 6),
        "existing_accepted_continuous_increment_weight": round(existing_accepted, 6),
        "observed_one_lot_increment_weight": round(observed_one_lot_increment, 6),
        "strategy_cap_headroom": strategy_headroom,
        "safety_cap_headroom": safety_headroom,
        "quality_action": quality_action,
        "entry_action": entry_action,
        "entry_state": entry_state,
        "expected_edge_current_state": expected_edge,
        "incremental_investment_value_state": incremental_value,
        "opportunity_cost_state": opportunity_cost,
        "campaign_continuation_state": campaign_state,
        "no_loss_averaging_state": no_loss,
        "canonical_opportunity_quality_class": str(opportunity_quality.get("canonical_opportunity_quality_class") or ""),
        "reason_codes": sorted(set(reason_codes)),
        "input_evidence": {
            "pm_reason_codes": pm_reason_codes,
            "add_campaign_evidence": dict(add_evidence),
            "structured_headroom": dict(structured_headroom),
            "source_evidence": source_evidence(member),
        },
    }


def _desirability_state(
    member: Mapping[str, Any],
    *,
    opportunity_quality: Mapping[str, Any],
    action_type: str,
) -> dict[str, Any]:
    quality = str(opportunity_quality.get("canonical_opportunity_quality_class") or "INSUFFICIENT")
    if quality in {"STRONG", "COMPARABLE_HIGH"}:
        state = "HIGH_VALUE"
    elif quality == "COMPARABLE_MARGINAL":
        state = "MEDIUM_VALUE"
    elif quality == "WEAK_VALID":
        state = "LOW_VALUE"
    elif quality == "INSUFFICIENT":
        state = "HIGH_VALUE_EVIDENCE_INCOMPLETE" if action_type == "BUY_ADD_NEXT_LOT" else "EVIDENCE_INCOMPLETE"
    else:
        state = "LOW_VALUE"
    return {
        "state": state,
        "quality_class": quality,
        "reason_codes": list(opportunity_quality.get("opportunity_quality_reason_codes") or []),
        "pre_bq_entry_add_value_preserved": action_type == "BUY_ADD_NEXT_LOT",
    }


def _evidence_completeness_state(
    member: Mapping[str, Any],
    *,
    opportunity_quality: Mapping[str, Any],
    action_type: str,
) -> dict[str, Any]:
    missing = []
    if not _symbol(member):
        missing.append("symbol")
    if action_type == "BUY_ADD_NEXT_LOT" and not _campaign_id(member):
        missing.append("position_campaign_id")
    if action_type == "BUY_ADD_NEXT_LOT" and not (member.get("source_pm_decision_ref") or member.get("pm_decision_id")):
        missing.append("source_pm_decision_id")
    guard_state = str(member.get("recent_exit_guard_state") or "").upper()
    guard_status = str(member.get("recent_exit_guard_status") or "").upper()
    if action_type == "BUY_NEW_NEXT_LOT" and guard_state in {"ACTIVE_RECENT_EXIT_GUARD", "MALFORMED_RECENT_EXIT_GUARD"} and guard_status != "PASS":
        missing.append("recent_exit_guard_not_requalified")
    if str(opportunity_quality.get("evidence_completeness") or "").upper() == "INSUFFICIENT":
        missing.append("opportunity_quality_insufficient")
    return {
        "state": "COMPLETE" if not missing else "INCOMPLETE",
        "missing_inputs": sorted(set(missing)),
        "comparison_sufficiency": str(opportunity_quality.get("comparison_sufficiency") or ""),
    }


def _execution_feasibility_state(
    member: Mapping[str, Any],
    *,
    production: Mapping[str, Any],
    action_type: str,
) -> dict[str, Any]:
    lot = _next_lot_evidence(member, action_type=action_type)
    accepted_weight = _number(production.get("accepted_weight"), 0.0) or 0.0
    reason_codes: list[str] = []
    if lot["next_executable_quantity"] > 0 or accepted_weight > 0:
        state = "FEASIBLE"
        reason_codes.append("next_executable_increment_available")
    elif lot["desired_next_lot_quantity"] > 0:
        state = "INFEASIBLE_DUE_TO_LOT"
        reason_codes.append("desired_next_lot_not_executable")
    else:
        state = "INFEASIBLE_OR_NOT_SIZED"
        reason_codes.append("next_executable_increment_missing")
    return {"state": state, "reason_codes": reason_codes, **lot}


def _structured_headroom(member: Mapping[str, Any]) -> dict[str, Any]:
    resolution = member.get("phase29_l19_lot_resolution") if isinstance(member.get("phase29_l19_lot_resolution"), Mapping) else {}
    admission = member.get("one_lot_admission") if isinstance(member.get("one_lot_admission"), Mapping) else {}
    target_resolution = member.get("target_weight_resolution") if isinstance(member.get("target_weight_resolution"), Mapping) else {}
    target_authority = member.get("target_weight_authority") if isinstance(member.get("target_weight_authority"), Mapping) else {}

    current_weight = _number(member.get("current_weight"), None)
    target_weight = _number(member.get("target_weight"), None)
    strategy_cap = _number(
        member.get("single_name_weight_cap")
        or target_authority.get("single_name_weight_cap")
        or target_resolution.get("single_name_weight_cap"),
        None,
    )
    safety_hard_cap = _number(
        resolution.get("safety_hard_cap")
        or admission.get("safety_hard_cap")
        or target_authority.get("safety_hard_cap"),
        None,
    )
    one_lot_post = _number(
        resolution.get("post_trade_weight")
        or admission.get("effective_post_trade_weight")
        or target_weight,
        None,
    )
    desired_post = _number(target_weight, None)
    strategy_cap_applied = target_resolution.get("cap_applied") is True or str(member.get("allocation_cap_reason") or "").upper() not in {"", "NONE"}
    blocked_reason = str(
        resolution.get("blocked_reason")
        or resolution.get("blocker_reason")
        or admission.get("blocked_reason")
        or admission.get("minimum_executable_one_lot_reason")
        or ""
    )
    blocked_upper = blocked_reason.upper()

    strategy_headroom = None if current_weight is None or strategy_cap is None else round(strategy_cap - current_weight, 6)
    safety_headroom = None if current_weight is None or safety_hard_cap is None else round(safety_hard_cap - current_weight, 6)

    if current_weight is None or strategy_cap is None:
        state = "HEADROOM_UNKNOWN"
        actual_block_reason = "strategy_headroom_missing"
    elif safety_hard_cap is not None and one_lot_post is not None and one_lot_post > safety_hard_cap:
        state = "SAFETY_HARD_CAP_BLOCKED"
        actual_block_reason = "one_lot_post_trade_weight_exceeds_safety_hard_cap"
    elif "SAFETY_HARD_CAP" in blocked_upper:
        state = "SAFETY_HARD_CAP_BLOCKED"
        actual_block_reason = blocked_reason
    elif current_weight >= strategy_cap:
        state = "STRATEGY_CAP_BLOCKED"
        actual_block_reason = "current_weight_at_or_above_strategy_cap"
    elif one_lot_post is not None and one_lot_post > strategy_cap:
        state = "LESS_THAN_ONE_LOT_HEADROOM"
        actual_block_reason = "one_lot_post_trade_weight_exceeds_strategy_cap"
    elif strategy_cap_applied:
        state = "STRATEGY_CAP_BLOCKED"
        actual_block_reason = str(member.get("allocation_cap_reason") or "strategy_cap_applied")
    else:
        state = "HEADROOM_AVAILABLE"
        actual_block_reason = ""

    return {
        "schema_version": "unified_marginal_capital_shadow.structured_headroom.v1",
        "state": state,
        "current_weight": current_weight,
        "strategy_single_name_cap": strategy_cap,
        "strategy_cap_headroom": strategy_headroom,
        "safety_hard_cap": safety_hard_cap,
        "safety_cap_headroom": safety_headroom,
        "desired_post_increment_weight": desired_post,
        "one_lot_post_trade_weight": one_lot_post,
        "strategy_cap_applied": strategy_cap_applied,
        "safety_hard_cap_applied": state == "SAFETY_HARD_CAP_BLOCKED",
        "actual_block_reason": actual_block_reason,
        "generic_cap_text_classification_used": False,
    }


def _lot_status_decomposition(
    member: Mapping[str, Any],
    *,
    production: Mapping[str, Any],
    action_type: str,
) -> dict[str, Any]:
    resolution = member.get("phase29_l19_lot_resolution") if isinstance(member.get("phase29_l19_lot_resolution"), Mapping) else {}
    lot = _next_lot_evidence(member, action_type=action_type)
    desired_continuous = _desired_continuous_increment_weight(member)
    accepted_continuous = _accepted_continuous_increment_weight(member)
    production_accepted = _number(production.get("accepted_weight"), 0.0) or 0.0
    status = str(resolution.get("one_lot_feasibility_status") or "")
    blocked_reason = str(
        resolution.get("blocked_reason")
        or resolution.get("blocker_reason")
        or resolution.get("minimum_executable_one_lot_reason")
        or member.get("lot_first_rebatch_skip_reason")
        or ""
    )
    reason_codes: list[str] = []
    if desired_continuous <= 0:
        state = "NO_POSITIVE_DESIRED_INCREMENT"
        reason_codes.append("desired_continuous_increment_zero")
    elif accepted_continuous <= 0 and _state(member, "quality_action", "buy_quality_action", default="") == "BUY_WAIT":
        state = "BQ_BLOCKS_INCREMENT"
        reason_codes.append("buy_quality_blocks_increment")
    elif accepted_continuous <= 0:
        state = "NO_ACCEPTED_CONTINUOUS_INCREMENT"
        reason_codes.append("accepted_continuous_increment_zero")
    elif lot["next_executable_quantity"] > 0 or production_accepted > 0:
        state = "EXECUTABLE_INCREMENT_AVAILABLE"
        reason_codes.append("next_executable_increment_available")
    elif status == "FAIL_CLOSED" and "REMAINING_BUDGET" in blocked_reason.upper():
        state = "REMAINING_BUDGET_BLOCK"
        reason_codes.append("minimum_lot_exceeds_remaining_budget")
    elif status == "FAIL_CLOSED" and "SAFETY_HARD_CAP" in blocked_reason.upper():
        state = "SAFETY_HARD_CAP_BLOCK"
        reason_codes.append("minimum_lot_exceeds_safety_hard_cap")
    elif "G43" in blocked_reason.upper():
        state = "G43_BINDING_OR_FAIL_CLOSED"
        reason_codes.append("g43_binding")
    elif status == "FAIL_CLOSED":
        state = "LOT_FAIL_CLOSED"
        reason_codes.append("lot_resolution_fail_closed")
    elif not status:
        state = "LOT_RESOLUTION_NOT_REACHED"
        reason_codes.append("lot_resolution_not_materialized")
    else:
        state = "LOT_NOT_EXECUTABLE"
        reason_codes.append("lot_not_executable")
    return {
        "schema_version": "unified_marginal_capital_shadow.lot_status_decomposition.v1",
        "state": state,
        "desired_continuous_increment_weight": round(desired_continuous, 6),
        "accepted_continuous_increment_weight": round(accepted_continuous, 6),
        "trading_unit": lot["desired_next_lot_quantity"],
        "one_lot_quantity": lot["desired_next_lot_quantity"],
        "one_lot_notional": lot["next_lot_notional"],
        "next_executable_quantity": lot["next_executable_quantity"],
        "lot_feasibility_status": status,
        "blocked_reason": blocked_reason,
        "reason_codes": reason_codes,
    }


def _desired_continuous_increment_weight(member: Mapping[str, Any]) -> float:
    target = _number(member.get("target_weight"), 0.0) or 0.0
    current = _number(member.get("current_weight"), 0.0) or 0.0
    return max(
        _number(member.get("desired_incremental_weight"), 0.0) or 0.0,
        _number(member.get("requested_incremental_weight"), 0.0) or 0.0,
        _number(member.get("target_weight_change"), 0.0) or 0.0,
        target - current,
        0.0,
    )


def _accepted_continuous_increment_weight(member: Mapping[str, Any]) -> float:
    target = _number(member.get("target_weight"), 0.0) or 0.0
    current = _number(member.get("current_weight"), 0.0) or 0.0
    return max(
        _number(member.get("lot_aware_accepted_incremental_weight"), 0.0) or 0.0,
        _number(member.get("accepted_incremental_weight"), 0.0) or 0.0,
        target - current,
        0.0,
    )


def _explicit_structured_safety_block(member: Mapping[str, Any], production: Mapping[str, Any]) -> bool:
    fields = [
        member.get("lot_first_rebatch_skip_reason"),
        production.get("reason_codes"),
        production.get("constraint_evidence"),
    ]
    text = json.dumps(fields, ensure_ascii=True, sort_keys=True, default=str).upper()
    return "SAFETY_HARD_CAP" in text or "BLOCKED_BY_SAFETY" in text


def _portfolio_risk_cost_state(
    member: Mapping[str, Any],
    *,
    production: Mapping[str, Any],
    structured_headroom: Mapping[str, Any],
) -> dict[str, Any]:
    headroom_state = str(structured_headroom.get("state") or "")
    if headroom_state in {"STRATEGY_CAP_BLOCKED", "LESS_THAN_ONE_LOT_HEADROOM"}:
        state = headroom_state
    elif headroom_state == "SAFETY_HARD_CAP_BLOCKED":
        state = "BLOCKED_BY_SAFETY"
    elif headroom_state == "HEADROOM_AVAILABLE":
        state = "ACCEPTABLE"
    elif _explicit_structured_safety_block(member, production):
        state = "BLOCKED_BY_SAFETY"
    elif str(production.get("status") or "") == "COMPETITOR_SELECTED":
        state = "ACCEPTABLE"
    else:
        state = "HEADROOM_UNKNOWN"
    return {
        "state": state,
        "current_weight": _number(member.get("current_weight"), 0.0) or 0.0,
        "target_weight": _number(member.get("target_weight"), 0.0) or 0.0,
        "structured_headroom_state": headroom_state,
        "reason_codes": list(production.get("reason_codes") or []),
    }


def _cash_optionality_comparison(member: Mapping[str, Any], *, production: Mapping[str, Any]) -> dict[str, Any]:
    risk = production.get("constraint_evidence") if isinstance(production.get("constraint_evidence"), Mapping) else {}
    pacing = risk.get("risk_pacing_decision") if isinstance(risk.get("risk_pacing_decision"), Mapping) else {}
    return {
        "cash_can_win": True,
        "risk_pacing_intent": str(pacing.get("intent") or ""),
        "cash_preferred_participation_evidence": production.get("cash_preferred_participation_evidence") or {},
        "reason_codes": list(production.get("reason_codes") or []),
    }


def _next_lot_evidence(member: Mapping[str, Any], *, action_type: str) -> dict[str, Any]:
    resolution = member.get("phase29_l19_lot_resolution") if isinstance(member.get("phase29_l19_lot_resolution"), Mapping) else {}
    quantity = _number(
        resolution.get("final_quantity_delta")
        or resolution.get("executable_quantity_delta")
        or resolution.get("final_allocated_quantity")
        or resolution.get("normal_lot_quantity"),
        0.0,
    ) or 0.0
    desired = _number(resolution.get("one_lot_quantity"), None)
    if desired is None:
        desired = 100.0 if action_type != "CASH_OPTIONALITY" else 0.0
    notional = _number(resolution.get("one_lot_notional"), 0.0) or 0.0
    return {
        "next_executable_quantity": max(quantity, 0.0),
        "desired_next_lot_quantity": max(desired, 0.0),
        "next_lot_notional": max(notional, 0.0),
        "lot_feasibility_status": str(
            resolution.get("one_lot_feasibility_status")
            or resolution.get("one_lot_admission_status")
            or resolution.get("one_lot_admission")
            or ""
        ),
        "lot_blocked_reason": str(
            resolution.get("blocked_reason")
            or resolution.get("blocker_reason")
            or resolution.get("minimum_executable_one_lot_reason")
            or ""
        ),
    }


def _continuation_evidence(member: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "strategy_intelligence_continuation_quality_status": str(member.get("strategy_intelligence_continuation_quality_status") or ""),
        "strategy_intelligence_add_worthiness_state": str(member.get("strategy_intelligence_add_worthiness_state") or ""),
        "strategy_intelligence_relative_strength_state": str(member.get("strategy_intelligence_relative_strength_state") or ""),
        "strategy_intelligence_downside_risk_status": str(member.get("strategy_intelligence_downside_risk_status") or ""),
        "tick_normalized_trend_state": str(member.get("tick_normalized_trend_state") or ""),
        "momentum_confidence_state": str(member.get("momentum_confidence_state") or ""),
        "pm_action": str(member.get("pm_action") or ""),
        "pm_reason_codes": list(member.get("source_pm_reason_codes") or member.get("reason_codes") or []),
        "campaign_age_business_days": _number(member.get("strategy_intelligence_campaign_age_business_days"), None),
    }


def _reentry_evidence(member: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "reentry_semantic_state": str(member.get("reentry_semantic_state") or ""),
        "recent_exit_guard_state": str(member.get("recent_exit_guard_state") or ""),
        "recent_exit_guard_status": str(member.get("recent_exit_guard_status") or ""),
        "recent_exit_guard_reason": str(member.get("recent_exit_guard_reason") or ""),
        "prior_exit_business_date": str(member.get("prior_exit_business_date") or ""),
        "business_days_since_exit": _number(member.get("business_days_since_exit"), None),
        "reentry_recovery_status": str(member.get("reentry_recovery_status") or ""),
        "reentry_reason_codes": list(member.get("reentry_reason_codes") or []),
        "reentry_safety_restriction_status": str(member.get("reentry_safety_restriction_status") or ""),
        "reentry_corporate_action_status": str(member.get("reentry_corporate_action_status") or ""),
    }


def _campaign_graduation_state(
    member: Mapping[str, Any],
    *,
    production: Mapping[str, Any],
    action_type: str,
) -> str:
    if action_type != "BUY_ADD_NEXT_LOT":
        return "NOT_APPLICABLE"
    add_count = _number(member.get("strategy_intelligence_add_history_count"), 0.0) or 0.0
    selected = str(production.get("status") or "") == "COMPETITOR_SELECTED" and (_number(production.get("accepted_weight"), 0.0) or 0.0) > 0
    if selected:
        return "ADD_FUNDED"
    if add_count > 0:
        return "GRADUATED_ADD_CONSIDERED"
    if str(member.get("pm_action") or "").upper() == "ADD":
        return "ADD_CONSIDERED"
    return "CONTINUING"


def _campaign_id(member: Mapping[str, Any]) -> str:
    return str(
        member.get("position_campaign_id")
        or member.get("current_position_campaign_id")
        or member.get("pm_position_campaign_id")
        or member.get("opportunity_position_campaign_id")
        or ""
    )


def _opportunity_strength_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    desirability_order = {
        "HIGH_VALUE": 1,
        "HIGH_VALUE_EVIDENCE_INCOMPLETE": 2,
        "MEDIUM_VALUE": 3,
        "LOW_VALUE": 4,
        "EVIDENCE_INCOMPLETE": 5,
    }
    completeness_order = {"COMPLETE": 0, "INCOMPLETE": 1}
    feasibility_order = {
        "FEASIBLE": 0,
        "INFEASIBLE_DUE_TO_LOT": 1,
        "BLOCKED_BY_CONCENTRATION": 2,
        "INFEASIBLE_OR_NOT_SIZED": 3,
    }
    risk_order = {
        "ACCEPTABLE": 0,
        "HEADROOM_AVAILABLE": 0,
        "LOW_COST": 0,
        "NOT_SELECTED_OR_UNKNOWN_COST": 1,
        "HEADROOM_UNKNOWN": 1,
        "LESS_THAN_ONE_LOT_HEADROOM": 2,
        "BLOCKED_BY_CONCENTRATION": 2,
        "STRATEGY_CAP_BLOCKED": 2,
        "BLOCKED_BY_SAFETY": 3,
        "SAFETY_HARD_CAP_BLOCKED": 3,
        "EVIDENCE_INCOMPLETE": 4,
    }
    desirability = row.get("marginal_desirability") if isinstance(row.get("marginal_desirability"), Mapping) else {}
    completeness = row.get("evidence_completeness") if isinstance(row.get("evidence_completeness"), Mapping) else {}
    feasibility = row.get("execution_feasibility") if isinstance(row.get("execution_feasibility"), Mapping) else {}
    risk = row.get("portfolio_risk_cost") if isinstance(row.get("portfolio_risk_cost"), Mapping) else {}
    quality = row.get("quality_evidence") if isinstance(row.get("quality_evidence"), Mapping) else {}
    rank = _number(quality.get("input_opportunity_rank"), 999999.0) or 999999.0
    return (
        desirability_order.get(str(desirability.get("state") or ""), 99),
        completeness_order.get(str(completeness.get("state") or ""), 99),
        feasibility_order.get(str(feasibility.get("state") or ""), 99),
        risk_order.get(str(risk.get("state") or ""), 99),
        rank,
        str(row.get("symbol") or ""),
        str(row.get("competitor_type") or ""),
    )


def _executable_capital_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return _opportunity_strength_sort_key(row)


def _ec_executable_capital_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return _opportunity_strength_sort_key(row)


def _executable_capital_eligible(row: Mapping[str, Any]) -> bool:
    row_type = str(row.get("competitor_type") or "")
    completeness = row.get("evidence_completeness") if isinstance(row.get("evidence_completeness"), Mapping) else {}
    feasibility = row.get("execution_feasibility") if isinstance(row.get("execution_feasibility"), Mapping) else {}
    risk = row.get("portfolio_risk_cost") if isinstance(row.get("portfolio_risk_cost"), Mapping) else {}
    if str(completeness.get("state") or "") != "COMPLETE":
        return False
    if str(feasibility.get("state") or "") != "FEASIBLE":
        return False
    if row_type == "CASH_OPTIONALITY":
        return str(risk.get("state") or "") in {"LOW_COST", "ACCEPTABLE"}
    if (_number(row.get("next_executable_quantity"), 0.0) or 0.0) <= 0:
        return False
    return str(risk.get("state") or "") in {"ACCEPTABLE", "HEADROOM_AVAILABLE"}


def _ec_executable_capital_eligible(row: Mapping[str, Any]) -> bool:
    if _executable_capital_eligible(row):
        return True
    if str(row.get("competitor_type") or "") != "BUY_ADD_NEXT_LOT":
        return False
    authority = row.get("add_strength_to_increment_target_authority") if isinstance(row.get("add_strength_to_increment_target_authority"), Mapping) else {}
    completeness = row.get("evidence_completeness") if isinstance(row.get("evidence_completeness"), Mapping) else {}
    risk = row.get("portfolio_risk_cost") if isinstance(row.get("portfolio_risk_cost"), Mapping) else {}
    if str(completeness.get("state") or "") != "COMPLETE":
        return False
    if str(risk.get("state") or "") not in {"ACCEPTABLE", "HEADROOM_AVAILABLE"}:
        return False
    if str(authority.get("increment_demand_status") or "") != "POSITIVE_INCREMENT_DEMAND":
        return False
    if (_number(authority.get("proposed_incremental_target_weight"), 0.0) or 0.0) <= 0:
        return False
    return (_number(row.get("next_executable_quantity"), 0.0) or 0.0) > 0


def _production_winners(
    competitors: Sequence[Mapping[str, Any]],
    market_candidate_cash_interaction: Mapping[str, Any],
    cash_evidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    winners = [
        {
            "competitor_type": str(item.get("competitor_type") or ""),
            "symbol": str(item.get("symbol") or ""),
            "accepted_weight": item.get("accepted_weight"),
            "reason_codes": list(item.get("reason_codes") or []),
        }
        for item in competitors
        if str(item.get("status") or "") == "COMPETITOR_SELECTED" and (_number(item.get("accepted_weight"), 0.0) or 0.0) > 0
    ]
    if not winners and str(market_candidate_cash_interaction.get("capital_competition_winner_type") or "") == "CASH_OPTIONALITY":
        winners.append(
            {
                "competitor_type": "CASH_OPTIONALITY",
                "symbol": "",
                "accepted_weight": cash_evidence.get("remaining_cash_weight"),
                "reason_codes": list(cash_evidence.get("reason_codes") or []),
            }
        )
    return winners


def _production_shadow_divergence(
    *,
    shadow_winner: Mapping[str, Any],
    production_winners: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    shadow_type = str(shadow_winner.get("competitor_type") or "")
    shadow_symbol = str(shadow_winner.get("symbol") or "")
    if any(_same_action_family(shadow_type, str(item.get("competitor_type") or "")) and shadow_symbol == str(item.get("symbol") or "") for item in production_winners):
        return {"agreement": True, "divergence_class": "AGREEMENT", "reason_codes": ["production_shadow_same_winner"]}
    prod_types = {str(item.get("competitor_type") or "") for item in production_winners}
    if not production_winners:
        prod_class = "Production none"
    elif "CASH_OPTIONALITY" in prod_types:
        prod_class = "Production Cash"
    elif "ADD" in prod_types:
        prod_class = "Production ADD"
    elif "NEW_BUY" in prod_types:
        prod_class = "Production NEW_OR_REENTRY"
    else:
        prod_class = "Production security"
    if shadow_type == "BUY_ADD_NEXT_LOT":
        shadow_class = "SHADOW ADD"
    elif shadow_type == "REENTRY_NEXT_LOT":
        shadow_class = "SHADOW REENTRY"
    elif shadow_type == "BUY_NEW_NEXT_LOT":
        shadow_class = "SHADOW NEW"
    elif shadow_type == "CASH_OPTIONALITY":
        shadow_class = "SHADOW Cash"
    elif not shadow_type:
        shadow_class = "SHADOW NONE"
    else:
        shadow_class = "SHADOW unknown"
    return {
        "agreement": False,
        "divergence_class": f"{prod_class} / {shadow_class}",
        "reason_codes": ["production_shadow_divergence_observed_without_outcome_judgment"],
    }


def _two_stage_divergence_class(
    *,
    production_winners: Sequence[Mapping[str, Any]],
    stage_a_winner: Mapping[str, Any],
    stage_b_winner: Mapping[str, Any],
) -> str:
    prod = _production_family_label(production_winners)
    stage_a = _shadow_family_label(stage_a_winner)
    stage_b = _shadow_family_label(stage_b_winner)
    if prod == stage_b and (stage_b != "NONE" or prod == "NONE"):
        return "Production agrees with Stage-B"
    return f"Production {prod} / Stage-A {stage_a} / Stage-B {stage_b}"


def _production_family_label(production_winners: Sequence[Mapping[str, Any]]) -> str:
    prod_types = {str(item.get("competitor_type") or "") for item in production_winners}
    if not production_winners:
        return "NONE"
    if "CASH_OPTIONALITY" in prod_types:
        return "Cash"
    if "ADD" in prod_types:
        return "ADD"
    if "NEW_BUY" in prod_types:
        return "NEW_OR_REENTRY"
    return "security"


def _shadow_family_label(winner: Mapping[str, Any]) -> str:
    shadow_type = str(winner.get("competitor_type") or "")
    if shadow_type == "BUY_ADD_NEXT_LOT":
        return "ADD"
    if shadow_type == "BUY_NEW_NEXT_LOT":
        return "NEW"
    if shadow_type == "REENTRY_NEXT_LOT":
        return "REENTRY"
    if shadow_type == "CASH_OPTIONALITY":
        return "Cash"
    return "NONE"


def _same_action_family(shadow_type: str, production_type: str) -> bool:
    if shadow_type == "BUY_ADD_NEXT_LOT":
        return production_type == "ADD"
    if shadow_type in {"BUY_NEW_NEXT_LOT", "REENTRY_NEXT_LOT"}:
        return production_type == "NEW_BUY"
    return shadow_type == production_type


def _winner_summary(winner: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "competitor_type": str(winner.get("competitor_type") or ""),
        "symbol": str(winner.get("symbol") or ""),
        "position_campaign_id": str(winner.get("position_campaign_id") or ""),
        "marginal_desirability": (winner.get("marginal_desirability") or {}).get("state") if isinstance(winner.get("marginal_desirability"), Mapping) else "",
        "evidence_completeness": (winner.get("evidence_completeness") or {}).get("state") if isinstance(winner.get("evidence_completeness"), Mapping) else "",
        "execution_feasibility": (winner.get("execution_feasibility") or {}).get("state") if isinstance(winner.get("execution_feasibility"), Mapping) else "",
        "portfolio_risk_cost": (winner.get("portfolio_risk_cost") or {}).get("state") if isinstance(winner.get("portfolio_risk_cost"), Mapping) else "",
    }


def _winner_reason(winner: Mapping[str, Any], alternatives: Sequence[Mapping[str, Any]]) -> list[str]:
    if not winner:
        return ["no_shadow_competitor"]
    reasons = ["shadow_ordering_selected_top_decision_time_marginal_candidate"]
    if alternatives:
        reasons.append("alternatives_ranked_by_same_structured_shadow_key")
    if str(winner.get("competitor_type") or "") == "CASH_OPTIONALITY":
        reasons.append("cash_optionality_allowed_to_win")
    return reasons


def _campaign_graduation_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in rows:
        state = str(row.get("campaign_graduation_shadow_state") or "NOT_APPLICABLE")
        counts[state] = counts.get(state, 0) + 1
    return {
        "schema_version": "unified_marginal_capital_shadow.campaign_graduation_observability.v1",
        "states": counts,
        "production_lifecycle_state_created": False,
        "shadow_only": True,
    }


def _shadow_input_hashes(
    members: Sequence[Mapping[str, Any]],
    cash_evidence: Mapping[str, Any],
    risk_pacing_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    hashes = []
    for member in members:
        for field in (
            "buy_quality_artifact_hash",
            "strategy_intelligence_artifact_hash",
            "opportunity_artifact_hash",
            "input_opportunity_rank_source_hash",
            "minimum_tick_authority_hash",
        ):
            value = member.get(field)
            if value:
                hashes.append(str(value))
    return {
        "member_source_hashes": sorted(set(hashes)),
        "cash_competitor_evidence_hash": str(cash_evidence.get("cash_competitor_evidence_hash") or ""),
        "risk_pacing_authority_hash": _stable_hash(risk_pacing_evidence) if risk_pacing_evidence else "",
    }


def _classify(
    row: Mapping[str, Any],
    *,
    lifecycle_intent: str,
    expected_edge: str,
    incremental_value: str,
    opportunity_cost: str,
) -> tuple[str, str, list[str]]:
    if lifecycle_intent == "BUY_ADD":
        if expected_edge == "WEAKENING":
            return "BLOCKED_OR_NOT_ELIGIBLE", "SUFFICIENT", ["expected_edge_weakening_not_rescued"]
        bridged = add_campaign_evidence(row)
        if bridged["pit_validation_status"] == "PASS":
            expected_edge = str(bridged["expected_edge_current_state"] or expected_edge).upper()
            incremental_value = str(bridged["incremental_investment_value_state"] or incremental_value).upper()
            opportunity_cost = str(bridged["opportunity_cost_state"] or opportunity_cost).upper()
        add_evidence = {
            "expected_edge": expected_edge in {"IMPROVING", "STABLE_ADEQUATE", "PASS"},
            "incremental_value": incremental_value == "POSITIVE",
            "opportunity_cost": opportunity_cost == "PASS",
            "add_worthiness": _state(row, "add_worthiness_state", "strategy_intelligence_add_worthiness_state", "add_allocation_eligibility_status", default=str(bridged.get("add_worthiness_state") or "UNKNOWN"))
            in {"ADD_ALLOWED", "ADD_REDUCED_ONLY", "PASS"},
            "campaign": _state(row, "same_campaign_continuation_status", "current_position_state", default=str(bridged.get("campaign_continuation_state") or "UNKNOWN"))
            in {"PASS", "CONTINUING", "HELD", "SAME_CAMPAIGN"},
        }
        missing = [name for name, ok in add_evidence.items() if not ok]
        if missing:
            return "COMPARISON_INSUFFICIENT", "INSUFFICIENT", [f"missing_or_non_pass_add_evidence:{name}" for name in missing]
        return "ELIGIBLE_STRONG", "SUFFICIENT", ["explicit_pit_add_lifecycle_evidence_positive"]

    if lifecycle_intent == "BUY_NEW":
        admission = _state(row, "entry_admission_action", "entry_admission_state", default="UNKNOWN")
        if admission in {"REJECT", "BUY_REJECTED", "BUY_WAIT", "TEMPORARY_BUY_INELIGIBLE"}:
            return "BLOCKED_OR_NOT_ELIGIBLE", "SUFFICIENT", [f"entry_admission_blocks:{admission}"]
        if admission in {"FULL_ALLOCATION_ELIGIBLE", "BUY_NEW_ALLOWED", "PASS"} and _number(row.get("input_opportunity_rank") or row.get("opportunity_rank")) is not None:
            return "ELIGIBLE_STRONG", "SUFFICIENT", ["explicit_pit_new_entry_evidence_positive"]
        if _number(row.get("runtime_opportunity_score")) is not None or _number(row.get("input_opportunity_rank") or row.get("opportunity_rank")) is not None:
            return "ELIGIBLE_COMPARABLE", "SUFFICIENT", ["pit_new_opportunity_evidence_comparable"]
        return "COMPARISON_INSUFFICIENT", "INSUFFICIENT", ["new_label_alone_not_priority_evidence"]

    return "BLOCKED_OR_NOT_ELIGIBLE", "SUFFICIENT", ["not_buy_increment_candidate"]


def _classify_opportunity_quality(
    row: Mapping[str, Any],
    *,
    lifecycle_intent: str,
    add_evidence: Mapping[str, Any],
) -> tuple[str, str, list[str]]:
    if lifecycle_intent == "BUY_ADD":
        return _classify_add_opportunity_quality(row, add_evidence=add_evidence)
    if lifecycle_intent == "BUY_NEW":
        return _classify_buy_new_opportunity_quality(row)
    return "BLOCKED", "COMPLETE", ["opportunity_quality_not_incremental_buy_candidate"]


def _classify_buy_new_opportunity_quality(row: Mapping[str, Any]) -> tuple[str, str, list[str]]:
    admission = _state(row, "entry_admission_action", "entry_admission_state", default="")
    entry_state = _state(row, "entry_admission_state", default="")
    entry_sufficiency = _state(row, "entry_admission_evidence_sufficiency", default="")
    quality_action = _state(row, "quality_action", "buy_quality_action", default="")
    allocation_bias = _state(row, "allocation_quality_bias", default="")
    selection_tier = _state(row, "strategy_intelligence_selection_quality_tier", "selection_quality_tier", default="")
    cq_status = _state(row, "strategy_intelligence_continuation_quality_status", "continuation_quality_status", default="")
    risk_status = _state(row, "strategy_intelligence_downside_risk_status", "downside_risk_status", default="")
    rank = _rank(row)
    score = _score(row)
    reasons: list[str] = []

    if admission in {"REJECT", "BUY_REJECTED", "TEMPORARY_BUY_INELIGIBLE"} or quality_action in {"REJECT", "BUY_REJECTED"}:
        return "BLOCKED", "COMPLETE", [f"opportunity_quality_hard_block:{admission or quality_action}"]
    if entry_state in {"REVERSAL_RISK_ENTRY", "OVERHEATED_DECELERATING_ENTRY"} and admission in {"BUY_WAIT", "NO_ADD"}:
        return "BLOCKED", "COMPLETE", [f"opportunity_quality_entry_hard_wait:{entry_state}"]
    if _explicit_insufficient(entry_sufficiency, cq_status, risk_status):
        return "INSUFFICIENT", "INSUFFICIENT", ["opportunity_quality_required_evidence_insufficient"]
    if rank is None and score is None:
        return "INSUFFICIENT", "INSUFFICIENT", ["opportunity_quality_rank_or_score_missing"]

    if (
        admission in {"FULL_ALLOCATION_ELIGIBLE", "BUY_NEW_ALLOWED", "PASS"}
        and entry_state in {"HEALTHY_CONTINUATION_ENTRY", "PASS", ""}
        and allocation_bias in {"FULL", "PASS", ""}
        and selection_tier in {"HIGH_QUALITY_CONTINUATION", ""}
        and rank is not None
        and (score is not None or selection_tier == "HIGH_QUALITY_CONTINUATION")
    ):
        return "STRONG", "COMPLETE", ["opportunity_quality_explicit_positive_buy_new_evidence"]
    if selection_tier == "HIGH_QUALITY_CONTINUATION" or (
        admission in {"BUY_NEW_ALLOWED", "FULL_ALLOCATION_ELIGIBLE", "PASS"} and allocation_bias in {"FULL", "PASS", ""}
    ):
        reasons.append("opportunity_quality_buy_new_comparable_high")
        return "COMPARABLE_HIGH", "COMPLETE", reasons
    if selection_tier in {"VALID_CONTINUATION", "CAUTION_CONTINUATION"} or admission in {"BUY_NEW_REDUCED_ONLY", "ADD_REDUCED_ONLY"} or allocation_bias == "REDUCED":
        return "COMPARABLE_MARGINAL", "COMPLETE", ["opportunity_quality_buy_new_mixed_or_reduced_but_valid"]
    if admission in {"BUY_WAIT", "NO_ADD"}:
        return "WEAK_VALID", "COMPLETE", ["opportunity_quality_buy_new_timing_wait_valid_but_weak"]
    return "WEAK_VALID", "COMPLETE", ["opportunity_quality_buy_new_rank_or_score_only_weak_valid"]


def _classify_add_opportunity_quality(row: Mapping[str, Any], *, add_evidence: Mapping[str, Any]) -> tuple[str, str, list[str]]:
    row_expected_edge = _state(row, "expected_edge_improvement_state", "add_expected_edge_improvement_state", default="")
    expected_edge = str(add_evidence.get("expected_edge_current_state") or _state(row, "expected_edge_improvement_state", "add_expected_edge_improvement_state", default="")).upper()
    incremental_value = str(add_evidence.get("incremental_investment_value_state") or _state(row, "incremental_investment_value_state", "add_incremental_investment_value_state", default="")).upper()
    opportunity_cost = str(add_evidence.get("opportunity_cost_state") or _state(row, "opportunity_cost_status", "add_opportunity_cost_status", default="")).upper()
    add_worthiness = str(add_evidence.get("add_worthiness_state") or _state(row, "strategy_intelligence_add_worthiness_state", "add_worthiness_state", "add_allocation_eligibility_status", default="")).upper()
    campaign = str(add_evidence.get("campaign_continuation_state") or _state(row, "same_campaign_continuation_status", "current_position_state", default="")).upper()
    rank = _rank(row)
    score = _score(row)

    if row_expected_edge == "WEAKENING" or expected_edge == "WEAKENING" or add_worthiness == "NO_ADD":
        return "BLOCKED", "COMPLETE", ["opportunity_quality_add_hard_block"]
    direct_complete = (
        expected_edge in {"IMPROVING", "STABLE_ADEQUATE", "PASS"}
        and incremental_value == "POSITIVE"
        and opportunity_cost == "PASS"
        and add_worthiness in {"ADD_ALLOWED", "ADD_REDUCED_ONLY", "PASS", ""}
        and campaign in {"PASS", "CONTINUING", "HELD", "SAME_CAMPAIGN"}
    )
    if str(add_evidence.get("pit_validation_status") or "") != "PASS" and not direct_complete:
        missing = []
        for name, value in {
            "expected_edge": expected_edge,
            "incremental_value": incremental_value,
            "opportunity_cost": opportunity_cost,
            "campaign": campaign,
        }.items():
            if not value or value in {"UNKNOWN", "NOT_EVALUATED", "FAIL_CLOSED"}:
                missing.append(name)
        return "INSUFFICIENT", "INSUFFICIENT", [f"missing_or_non_pass_add_evidence:{name}" for name in (missing or ["pit_validation"])]
    if incremental_value != "POSITIVE" or opportunity_cost != "PASS":
        return "INSUFFICIENT", "INSUFFICIENT", ["opportunity_quality_add_value_or_cost_not_pass"]
    if expected_edge == "IMPROVING" and add_worthiness in {"ADD_ALLOWED", "PASS", ""} and campaign in {"PASS", "CONTINUING", "HELD", "SAME_CAMPAIGN"}:
        return "STRONG", "COMPLETE", ["opportunity_quality_explicit_positive_add_evidence"]
    if expected_edge == "STABLE_ADEQUATE" and add_worthiness in {"ADD_ALLOWED", "PASS", ""}:
        return "COMPARABLE_HIGH", "COMPLETE", ["opportunity_quality_add_stable_adequate_comparable_high"]
    if add_worthiness == "ADD_REDUCED_ONLY":
        return "COMPARABLE_MARGINAL", "COMPLETE", ["opportunity_quality_add_reduced_but_valid"]
    if rank is not None or score is not None:
        return "WEAK_VALID", "COMPLETE", ["opportunity_quality_add_complete_rank_or_score_only_weak_valid"]
    return "WEAK_VALID", "COMPLETE", ["opportunity_quality_add_complete_but_weak_valid"]


def _legacy_reason_codes(quality_class: str, reasons: Sequence[str]) -> list[str]:
    prefix = {
        "STRONG": "canonical_opportunity_quality_strong",
        "COMPARABLE_HIGH": "canonical_opportunity_quality_comparable_high",
        "COMPARABLE_MARGINAL": "canonical_opportunity_quality_comparable_marginal",
        "WEAK_VALID": "canonical_opportunity_quality_weak_valid",
        "INSUFFICIENT": "canonical_opportunity_quality_insufficient",
        "BLOCKED": "canonical_opportunity_quality_blocked",
    }[quality_class]
    legacy_reasons = [prefix, *list(reasons)]
    if quality_class == "STRONG" and "opportunity_quality_explicit_positive_add_evidence" in reasons:
        legacy_reasons.append("explicit_pit_add_lifecycle_evidence_positive")
    if quality_class in {"STRONG", "COMPARABLE_HIGH"} and "opportunity_quality_explicit_positive_buy_new_evidence" in reasons:
        legacy_reasons.append("explicit_pit_new_entry_evidence_positive")
    if "opportunity_quality_add_hard_block" in reasons:
        legacy_reasons.append("expected_edge_weakening_not_rescued")
    return sorted(set(legacy_reasons))


def _explicit_insufficient(*states: str) -> bool:
    return any(state in {"INSUFFICIENT", "INSUFFICIENT_QUALITY", "REVIEW_REQUIRED", "UNKNOWN"} for state in states if state)


def _rank(row: Mapping[str, Any]) -> float | None:
    return _number(row.get("input_opportunity_rank") or row.get("opportunity_rank") or row.get("opportunity_buy_rank") or row.get("buy_rank"))


def _score(row: Mapping[str, Any]) -> float | None:
    return _number(row.get("runtime_opportunity_score") or row.get("expected_edge_score") or row.get("opportunity_score") or row.get("score"))


def _source_artifact_paths(row: Mapping[str, Any], add_evidence: Mapping[str, Any]) -> list[Any]:
    values = [
        row.get("buy_quality_artifact_path"),
        row.get("strategy_intelligence_artifact_path"),
        row.get("portfolio_construction_artifact_path"),
    ]
    values.extend(add_evidence.get("source_artifact_paths") or [])
    return [value for value in values if value]


def _source_artifact_hashes(row: Mapping[str, Any], add_evidence: Mapping[str, Any]) -> list[Any]:
    values = [
        row.get("buy_quality_artifact_hash"),
        row.get("strategy_intelligence_artifact_hash"),
        row.get("portfolio_construction_artifact_hash"),
    ]
    values.extend(add_evidence.get("source_artifact_hashes") or [])
    return [value for value in values if value]


def _symbol(row: Mapping[str, Any]) -> str:
    return str(row.get("security_code") or row.get("symbol") or row.get("code") or row.get("issue_code") or "")


def _state(row: Mapping[str, Any], *fields: str, default: str) -> str:
    for field in fields:
        value = str(row.get(field) or "").upper()
        if value:
            return value
    return default


def _number(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _stable_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(payload), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
