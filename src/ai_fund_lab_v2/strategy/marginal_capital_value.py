from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


AUTHORITY_TYPE = "MARGINAL_CAPITAL_VALUE_AUTHORITY"
PRODUCER = "strategy.marginal_capital_value"
CONTRACT_ID = "phase31_g40_opportunity_quality_authority.v1"

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
