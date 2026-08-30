from __future__ import annotations

import math
from typing import Any, Mapping

from ai_fund_lab_v2.strategy.reduce_intensity_authority import canonical_reduce_fraction


CONTRACT_VERSION = "phase31_f1f_pm_canonical_sell_semantic_integration_v1"
PRODUCER = "strategy.sell_semantic_state"
PM_SEVERITY_CONTRACT_VERSION = "phase31_g4_pm_severity_persistence_v1"
PM_SEVERITY_PRODUCER = "strategy.pm_severity"

AGGREGATE_PASS_SEMANTICS = "EVIDENCE_AVAILABLE_NOT_HEALTH_SIGNAL"

HEALTHY_OR_RECOVERING = "HEALTHY_OR_RECOVERING"
WEAKENING_BUT_INTACT = "WEAKENING_BUT_INTACT"
PERSISTENT_DETERIORATION = "PERSISTENT_DETERIORATION"
EXIT_GRADE = "EXIT_GRADE"
UNRESOLVED = "UNRESOLVED"

PM_SEVERITY_NORMAL = "PM_SEVERITY_NORMAL"
PM_SEVERITY_CAUTION = "PM_SEVERITY_CAUTION"
PM_SEVERITY_DEFENSIVE = "PM_SEVERITY_DEFENSIVE"
PM_SEVERITY_EXIT_CANDIDATE = "PM_SEVERITY_EXIT_CANDIDATE"
PM_SEVERITY_UNRESOLVED = "PM_SEVERITY_UNRESOLVED"

FIRST_OBSERVATION = "FIRST_OBSERVATION"
REPEATED_OBSERVATION = "REPEATED_OBSERVATION"
PERSISTENT = "PERSISTENT"
WORSENING = "WORSENING"
RECOVERED = "RECOVERED"

NO_ACTIVE_SOFT_DETERIORATION = "NO_ACTIVE_SOFT_DETERIORATION"
SOFT_DETERIORATION_ACTIVE = "SOFT_DETERIORATION_ACTIVE"
SOFT_DETERIORATION_PERSISTENT = "SOFT_DETERIORATION_PERSISTENT"
SOFT_DETERIORATION_DEESCALATED = "SOFT_DETERIORATION_DEESCALATED"
SOFT_DETERIORATION_CLOSED = "SOFT_DETERIORATION_CLOSED"
TERMINAL_DETERIORATION = "TERMINAL_DETERIORATION"

DEFENSIVE_ONLY = "DEFENSIVE_ONLY"
CONFIRMED_DETERIORATION = "CONFIRMED_DETERIORATION"
TERMINAL_BREAKDOWN = "TERMINAL_BREAKDOWN"

REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT = "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT"
REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL = "REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL"

ESCALATION_REASON_CODE = "pm_discrete_control_persistent_deterioration_exit"

DEFAULT_TRADING_UNIT = 100.0

EXIT_GRADE_REASONS = {
    "trend_and_opportunity_broken",
    "weak_hold_score",
    "profit_retention_break",
    "hard_stop_current_return",
    "trend_and_expected_edge_broken",
    "EXIT_BY_WEAK_HOLD_SCORE",
}
REDUCE_WEAKENING_REASONS = {
    "risk_increased_but_trend_not_broken",
    "peak_drawdown_warning",
    "expected_edge_risk_deterioration",
}
RECOVERY_REASONS = {
    "structured_hold_worthiness_pass",
    "trend_continuation",
    "downside_risk_contained",
    "positive_expected_edge",
    "strong_trend_continuation",
    "opportunity_rank_still_high",
}
RECOVERY_STATES = {"HEALTHY_CONTINUATION_ENTRY", "ADD_ALLOWED", "SUPPORTIVE", "ADEQUATE", "IMPROVED"}
DETERIORATION_STATES = {"WEAK", "DECELERATING", "ELEVATED_RISK", "HIGH_RISK", "MIXED"}


def evaluate_position_sell_semantic(position: Mapping[str, Any], *, business_date: str) -> dict[str, Any]:
    action = _state(position, "action", "decision", "pm_action")
    reasons = [str(item) for item in position.get("reason_codes") or position.get("decision_reason_codes") or []]
    si = _strategy_intelligence_evidence(position)
    recovery = _recovery_dimensions(action=action, reasons=reasons, si=si)
    deterioration = _deterioration_dimensions(action=action, reasons=reasons, si=si)
    representability = _representability(position, action=action)
    pit = _pit_proof(position, business_date=business_date)
    campaign_id = str(position.get("position_campaign_id") or position.get("strategy_intelligence_campaign_id") or "")
    campaign_valid = bool(campaign_id) and _campaign_identity_status(position) == "COMPLETE"
    prior_summary = _prior_unrepresentable_reduce_summary(position)
    prior_count = _active_prior_reduce_count(prior_summary)
    conflict = recovery["recovery_present"] and deterioration["deterioration_present"] and action == "REDUCE"
    episode = _soft_deterioration_episode(
        action=action,
        business_date=business_date,
        campaign_id=campaign_id,
        representability=representability,
        deterioration=deterioration,
        recovery=recovery,
        prior_summary=prior_summary,
        pit_pass=pit["pit_validation_state"] == "PASS",
    )
    exit_confirmation = _exit_confirmation_state(
        action=action,
        reasons=reasons,
        deterioration=deterioration,
        recovery=recovery,
        episode=episode,
        pit_pass=pit["pit_validation_state"] == "PASS",
    )
    canonical_state, state_reasons, parameter_status = _canonical_state(
        action=action,
        reasons=reasons,
        representability=representability,
        deterioration=deterioration,
        recovery=recovery,
        prior_unrepresentable_count=prior_count,
        pit_pass=pit["pit_validation_state"] == "PASS",
        campaign_valid=campaign_valid,
        conflict=conflict,
        exit_confirmation_state=exit_confirmation["exit_confirmation_state"],
    )
    escalation = _escalation_decision(
        action=action,
        canonical_state=canonical_state,
        representability=representability,
        recovery=recovery,
        pit=pit,
        campaign_valid=campaign_valid,
        conflict=conflict,
        episode=episode,
        exit_confirmation=exit_confirmation,
    )
    severity = _pm_severity_evidence(
        position,
        action=action,
        canonical_state=canonical_state,
        representability=representability,
        deterioration=deterioration,
        recovery=recovery,
        pit=pit,
        campaign_id=campaign_id,
        campaign_valid=campaign_valid,
        conflict=conflict,
        prior_unrepresentable_count=prior_count,
        si=si,
        business_date=business_date,
        episode=episode,
        exit_confirmation=exit_confirmation,
    )
    return {
        "contract_version": CONTRACT_VERSION,
        "producer": PRODUCER,
        "business_date": business_date,
        "symbol": str(position.get("security_code") or position.get("symbol") or ""),
        "campaign_id": campaign_id,
        "original_pm_action": action,
        "original_pm_reasons": reasons,
        "canonical_sell_state": canonical_state,
        "canonical_state_reasons": state_reasons,
        "aggregate_pass_semantics": AGGREGATE_PASS_SEMANTICS,
        "continuation_quality_status": si["continuation_quality_status"],
        "downside_risk_status": si["downside_risk_status"],
        "deterioration_dimensions": deterioration,
        "recovery_state": "RECOVERY_PRESENT" if recovery["recovery_present"] else "NO_RECOVERY",
        "recovery_dimensions": recovery,
        "representability_family": representability["representability_family"],
        "representability_reason": representability["representability_reason"],
        "current_quantity": representability["current_quantity"],
        "trading_unit": representability["trading_unit"],
        "raw_reduce_quantity": representability["raw_reduce_quantity"],
        "rounded_reduce_quantity": representability["rounded_reduce_quantity"],
        "final_reduce_quantity": representability["final_reduce_quantity"],
        "one_lot_flag": representability["one_lot_flag"],
        "minimum_notional_flag": representability["minimum_notional_flag"],
        "valid_intermediate_exposure_available": representability["valid_intermediate_exposure_available"],
        "prior_unrepresentable_reduce_count": prior_count,
        "prior_unrepresentable_reduce_summary": prior_summary,
        "campaign_identity_valid": campaign_valid,
        "conflicting_recovery_deterioration_evidence": conflict,
        "soft_deterioration_episode": episode,
        "soft_deterioration_episode_id": episode["soft_deterioration_episode_id"],
        "soft_deterioration_episode_state": episode["soft_deterioration_episode_state"],
        "episode_start_business_date": episode["episode_start_business_date"],
        "episode_last_deterioration_business_date": episode["episode_last_deterioration_business_date"],
        "episode_persistence_severity": episode["episode_persistence_severity"],
        "episode_increment_evidence": episode["episode_increment_evidence"],
        "episode_recovery_evidence": episode["episode_recovery_evidence"],
        "episode_deescalation_reason": episode["episode_deescalation_reason"],
        "hard_deterioration_present": exit_confirmation["hard_deterioration_present"],
        "exit_confirmation_state": exit_confirmation["exit_confirmation_state"],
        "exit_confirmation_evidence": exit_confirmation,
        "prior_soft_deterioration_cleared": episode["prior_soft_deterioration_cleared"],
        "zero_lot_reduce_persistence_scope": episode["zero_lot_reduce_persistence_scope"],
        "pit_proof": pit,
        "parameter_resolution_status": parameter_status,
        "pm_severity": severity["pm_severity"],
        "pm_severity_reasons": severity["pm_severity_reasons"],
        "pm_severity_evidence": severity,
        "persistence_state": severity["persistence_state"],
        "escalation_considered": escalation["escalation_considered"],
        "escalation_decision": escalation["escalation_decision"],
        "final_pm_action": escalation["final_pm_action"],
        "escalation_reason_code": escalation["escalation_reason_code"],
        "future_information_used": False,
        "outcome_used_for_parameter_selection": False,
        "production_shadow_consumer": False,
    }


def _pm_severity_evidence(
    position: Mapping[str, Any],
    *,
    action: str,
    canonical_state: str,
    representability: Mapping[str, Any],
    deterioration: Mapping[str, Any],
    recovery: Mapping[str, Any],
    pit: Mapping[str, Any],
    campaign_id: str,
    campaign_valid: bool,
    conflict: bool,
    prior_unrepresentable_count: int,
    si: Mapping[str, Any],
    business_date: str,
    episode: Mapping[str, Any],
    exit_confirmation: Mapping[str, Any],
) -> dict[str, Any]:
    campaign_return = _float_or_none(si.get("current_campaign_relative_return"))
    campaign_return_side = _campaign_return_side(campaign_return)
    regime = _market_regime(position)
    severity = PM_SEVERITY_UNRESOLVED
    persistence_state = FIRST_OBSERVATION
    reasons: list[str] = []

    if pit["pit_validation_state"] != "PASS":
        reasons.append("pit_proof_failed")
    elif conflict:
        reasons.append("conflicting_recovery_deterioration_evidence")
    elif not campaign_valid:
        reasons.append("campaign_identity_ambiguous")
    elif canonical_state == UNRESOLVED:
        reasons.extend(["canonical_sell_state_unresolved", "missing_or_unresolved_pm_evidence"])
    elif recovery["recovery_present"] or canonical_state == HEALTHY_OR_RECOVERING:
        severity = PM_SEVERITY_NORMAL
        persistence_state = RECOVERED
        reasons.append("recovery_deescalation")
    elif canonical_state == EXIT_GRADE:
        severity = PM_SEVERITY_EXIT_CANDIDATE
        persistence_state = WORSENING
        reasons.append("existing_pm_exit_grade")
    elif canonical_state == PERSISTENT_DETERIORATION:
        severity = PM_SEVERITY_EXIT_CANDIDATE
        persistence_state = PERSISTENT
        reasons.extend(["strict_prior_persistence_present", "current_deterioration_evidence"])
        if exit_confirmation.get("exit_confirmation_state") == DEFENSIVE_ONLY:
            severity = PM_SEVERITY_DEFENSIVE if campaign_return_side == "FAILING" else PM_SEVERITY_CAUTION
            reasons.append("non_emergency_exit_confirmation_defensive_only")
    elif canonical_state == WEAKENING_BUT_INTACT:
        persistence_state = REPEATED_OBSERVATION if prior_unrepresentable_count > 0 else FIRST_OBSERVATION
        if campaign_return_side == "FAILING":
            severity = PM_SEVERITY_DEFENSIVE
            reasons.append("nonhealthy_campaign_failing")
        elif campaign_return_side in {"PROFITABLE", "FLAT"}:
            severity = PM_SEVERITY_CAUTION
            reasons.append("nonhealthy_but_not_failing")
        else:
            severity = PM_SEVERITY_CAUTION
            reasons.append("campaign_return_modifier_unavailable")
        if prior_unrepresentable_count > 0:
            reasons.append("strict_prior_persistence_present")
        if regime["regime_adverse"]:
            reasons.append("adverse_regime_modifier_observed")

    if severity == PM_SEVERITY_UNRESOLVED and not reasons:
        reasons.append("severity_contract_unresolved")

    return {
        "contract_version": PM_SEVERITY_CONTRACT_VERSION,
        "producer": PM_SEVERITY_PRODUCER,
        "business_date": business_date,
        "symbol": str(position.get("security_code") or position.get("symbol") or ""),
        "campaign_id": campaign_id,
        "canonical_sell_state": canonical_state,
        "pm_severity": severity,
        "pm_severity_reasons": sorted(set(reasons)),
        "persistence_state": persistence_state,
        "severity_action_authority": "PM_ONLY",
        "canonical_sell_state_owner_changed": False,
        "second_sell_classifier_created": False,
        "campaign_economics": {
            "current_campaign_relative_return": campaign_return,
            "campaign_return_side": campaign_return_side,
            "role": "SEVERITY_MODIFIER_NOT_PRIMARY_SELL_SIGNAL",
            "direct_exit_rule_applied": False,
        },
        "persistence_evidence": {
            "source": "strict_prior_pm_decision_evidence_or_campaign_summary",
            "prior_unrepresentable_reduce_count": prior_unrepresentable_count,
            "soft_deterioration_episode_id": episode.get("soft_deterioration_episode_id"),
            "soft_deterioration_episode_state": episode.get("soft_deterioration_episode_state"),
            "prior_soft_deterioration_cleared": episode.get("prior_soft_deterioration_cleared"),
            "zero_lot_reduce_persistence_scope": episode.get("zero_lot_reduce_persistence_scope"),
            "same_day_self_count": 0,
            "cross_campaign_history_leak": 0,
            "reduce_count_direct_exit_rule_applied": False,
            "strict_prior_persistence_required": True,
        },
        "exit_confirmation": dict(exit_confirmation),
        "recovery_deescalation_evidence": {
            "recovery_state": "RECOVERY_PRESENT" if recovery["recovery_present"] else "NO_RECOVERY",
            "reset_policy": recovery["reset_policy"],
            "deescalated": bool(recovery["recovery_present"] or canonical_state == HEALTHY_OR_RECOVERING),
        },
        "regime_modifier": {
            "regime_state": regime["regime_state"],
            "source_status": regime["source_status"],
            "role": "SEVERITY_CONFIRMATION_MODIFIER_ONLY",
            "direct_exit_rule_applied": False,
        },
        "representability_family": representability["representability_family"],
        "pit_proof": pit,
        "future_information_used": False,
        "final_campaign_outcome_used": False,
        "outcome_used_for_parameter_selection": False,
        "new_numeric_threshold_added": False,
        "missing_evidence_auto_exit": False,
    }


def _campaign_return_side(value: float | None) -> str:
    if value is None:
        return "UNKNOWN"
    if value > 0:
        return "PROFITABLE"
    if value < 0:
        return "FAILING"
    return "FLAT"


def _market_regime(position: Mapping[str, Any]) -> dict[str, Any]:
    raw = (
        position.get("market_context_regime")
        or position.get("regime_state")
        or position.get("market_regime")
        or _nested(position, "market_context", "regime_state")
        or _nested(position, "market_context", "regime")
    )
    regime_state = str(raw or "NOT_AVAILABLE").upper()
    adverse = regime_state in {"BEAR", "BEARISH", "RISK_OFF", "CORRECTION", "DOWNTREND", "ADVERSE"}
    return {
        "regime_state": regime_state,
        "source_status": "AVAILABLE" if raw not in (None, "") else "NOT_AVAILABLE",
        "regime_adverse": adverse,
    }


def _canonical_state(
    *,
    action: str,
    reasons: list[str],
    representability: Mapping[str, Any],
    deterioration: Mapping[str, Any],
    recovery: Mapping[str, Any],
    prior_unrepresentable_count: int,
    pit_pass: bool,
    campaign_valid: bool,
    conflict: bool,
    exit_confirmation_state: str,
) -> tuple[str, list[str], str]:
    lower_reasons = {reason.lower() for reason in reasons}
    if not pit_pass:
        return UNRESOLVED, ["pit_proof_failed"], "PIT_PROOF_FAILED"
    if conflict:
        return UNRESOLVED, ["conflicting_recovery_deterioration_evidence"], "RECOVERY_DETERIORATION_CONFLICT"
    if action == "EXIT" or lower_reasons & {reason.lower() for reason in EXIT_GRADE_REASONS}:
        return EXIT_GRADE, ["same_day_pm_exit_grade_reason_family"], "CANONICAL_EXISTING"
    if action in {"HOLD", "ADD"}:
        return HEALTHY_OR_RECOVERING, ["pm_hold_add_recovery_or_preserve"], recovery["reset_policy"]
    if action != "REDUCE":
        return UNRESOLVED, ["unsupported_pm_action"], "UNSUPPORTED_ACTION"
    if representability["minimum_notional_flag"]:
        return UNRESOLVED, ["minimum_notional_policy_unresolved"], "MINIMUM_NOTIONAL_POLICY_UNRESOLVED"
    if recovery["recovery_present"]:
        return HEALTHY_OR_RECOVERING, ["recovery_guard_present"], recovery["reset_policy"]
    if not campaign_valid:
        return UNRESOLVED, ["campaign_identity_ambiguous"], "CAMPAIGN_IDENTITY_UNRESOLVED"
    if (
        representability["representability_family"] == "DISCRETE_LOT"
        and prior_unrepresentable_count > 0
        and deterioration["deterioration_present"]
    ):
        if exit_confirmation_state == DEFENSIVE_ONLY:
            return (
                PERSISTENT_DETERIORATION,
                ["active_soft_deterioration_episode", "non_emergency_exit_confirmation_defensive_only"],
                "PHASE32_X_ACTIVE_EPISODE_EXIT_CONFIRMATION_REQUIRED",
            )
        return (
            PERSISTENT_DETERIORATION,
            ["active_soft_deterioration_episode", "current_deterioration_evidence", "non_emergency_exit_confirmed"],
            "F1F_DISCRETE_CONTROL_EXIT_ELIGIBLE",
        )
    if deterioration["deterioration_present"] or lower_reasons & {reason.lower() for reason in REDUCE_WEAKENING_REASONS}:
        return WEAKENING_BUT_INTACT, ["current_reduce_weakening_but_intact"], "CANONICAL_EXISTING"
    return UNRESOLVED, ["deterioration_semantics_unresolved"], "DETERIORATION_EVIDENCE_MISSING"


def _escalation_decision(
    *,
    action: str,
    canonical_state: str,
    representability: Mapping[str, Any],
    recovery: Mapping[str, Any],
    pit: Mapping[str, Any],
    campaign_valid: bool,
    conflict: bool,
    episode: Mapping[str, Any],
    exit_confirmation: Mapping[str, Any],
) -> dict[str, Any]:
    considered = bool(action == "REDUCE" and representability["reduce_unrepresentable"])
    confirmation_state = str(exit_confirmation.get("exit_confirmation_state") or "")
    allowed = bool(
        action == "REDUCE"
        and representability["representability_family"] == "DISCRETE_LOT"
        and representability["final_reduce_quantity"] == 0
        and not representability["valid_intermediate_exposure_available"]
        and canonical_state == PERSISTENT_DETERIORATION
        and not recovery["recovery_present"]
        and episode.get("soft_deterioration_episode_state") == SOFT_DETERIORATION_PERSISTENT
        and confirmation_state in {CONFIRMED_DETERIORATION, TERMINAL_BREAKDOWN}
        and pit["pit_validation_state"] == "PASS"
        and campaign_valid
        and not representability["minimum_notional_flag"]
        and not conflict
    )
    return {
        "escalation_considered": considered,
        "escalation_decision": "PM_EXIT" if allowed else "PRESERVE_BASELINE",
        "final_pm_action": "EXIT" if allowed else action,
        "escalation_reason_code": ESCALATION_REASON_CODE if allowed else "",
    }


def _representability(position: Mapping[str, Any], *, action: str) -> dict[str, Any]:
    quantity = _float_or_none(
        position.get("current_quantity")
        or position.get("runtime_position_quantity")
        or _nested(position, "adapter_source_contract", "quantity")
    )
    unit = _float_or_none(position.get("trading_unit") or position.get("tradable_unit") or DEFAULT_TRADING_UNIT)
    ratio = canonical_reduce_fraction(position.get("intensity") or position.get("reduce_intensity"))
    raw = quantity * ratio if quantity is not None and ratio is not None else None
    rounded = math.floor(raw / unit) * unit if raw is not None and unit and unit > 0 else None
    semantic_hint = _state(position, "reduce_execution_semantic", default="")
    reason_text = " ".join(str(item) for item in position.get("reason_codes") or [])
    minimum = bool(semantic_hint == REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL or "MINIMUM_NOTIONAL" in reason_text.upper())
    discrete = bool(action == "REDUCE" and not minimum and rounded == 0)
    final = 0.0 if discrete or minimum else rounded
    one_lot = bool(quantity is not None and unit is not None and quantity <= unit)
    valid_intermediate = bool(final and quantity and unit and 0 < final < quantity and (quantity - final) >= unit)
    return {
        "representability_family": "MINIMUM_NOTIONAL" if minimum else "DISCRETE_LOT" if discrete else "REPRESENTABLE" if action == "REDUCE" and final and final > 0 else "NOT_APPLICABLE",
        "representability_reason": REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL if minimum else REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT if discrete else "",
        "reduce_unrepresentable": bool(discrete or minimum),
        "current_quantity": quantity,
        "trading_unit": unit,
        "raw_reduce_quantity": raw,
        "rounded_reduce_quantity": rounded,
        "final_reduce_quantity": final,
        "one_lot_flag": one_lot,
        "minimum_notional_flag": minimum,
        "valid_intermediate_exposure_available": valid_intermediate,
    }


def _strategy_intelligence_evidence(position: Mapping[str, Any]) -> dict[str, Any]:
    profit = position.get("strategy_intelligence_profit_protection_evidence") if isinstance(position.get("strategy_intelligence_profit_protection_evidence"), Mapping) else {}
    hold = position.get("strategy_intelligence_hold_worthiness_evidence") if isinstance(position.get("strategy_intelligence_hold_worthiness_evidence"), Mapping) else {}
    add = position.get("strategy_intelligence_add_worthiness_evidence") if isinstance(position.get("strategy_intelligence_add_worthiness_evidence"), Mapping) else {}
    return {
        "continuation_quality_status": str(position.get("strategy_intelligence_continuation_quality_status") or "").upper(),
        "downside_risk_status": str(position.get("strategy_intelligence_downside_risk_status") or "").upper(),
        "profit_protection_status": str(position.get("strategy_intelligence_profit_protection_status") or profit.get("status") or "").upper(),
        "continuation_deterioration_connection": [str(item).upper() for item in profit.get("continuation_deterioration_connection") or []],
        "downside_risk_rise_connection": [str(item).upper() for item in profit.get("downside_risk_rise_connection") or []],
        "hold_status": str(hold.get("status") or "").upper(),
        "add_status": str(add.get("status") or "").upper(),
        "hold_reason_codes": [str(item) for item in hold.get("reason_codes") or []],
        "add_reason_codes": [str(item) for item in add.get("reason_codes") or []],
        "prior_unrepresentable_reduce_summary": hold.get("prior_unrepresentable_reduce_summary") or add.get("prior_unrepresentable_reduce_summary") or {},
        "pm_decision_history_summary": hold.get("pm_decision_history_summary") or add.get("pm_decision_history_summary") or {},
        "reduce_history_summary": hold.get("reduce_history_summary") or add.get("reduce_history_summary") or {},
        "campaign_identity_authority_status": str(hold.get("campaign_identity_authority_status") or add.get("campaign_identity_authority_status") or "").upper(),
        "current_campaign_relative_return": position.get("strategy_intelligence_current_campaign_relative_return"),
        "observed_campaign_mfe": position.get("strategy_intelligence_observed_campaign_mfe"),
        "observed_giveback": position.get("strategy_intelligence_observed_giveback"),
    }


def _deterioration_dimensions(*, action: str, reasons: list[str], si: Mapping[str, Any]) -> dict[str, Any]:
    lower_reasons = {reason.lower() for reason in reasons}
    pm = sorted(lower_reasons & ({reason.lower() for reason in REDUCE_WEAKENING_REASONS} | {reason.lower() for reason in EXIT_GRADE_REASONS}))
    nested = [
        *(si.get("continuation_deterioration_connection") or []),
        *(si.get("downside_risk_rise_connection") or []),
    ]
    states = sorted({str(value).upper() for value in nested if str(value).upper() in DETERIORATION_STATES})
    return {
        "deterioration_present": bool(pm or states or action == "EXIT"),
        "pm_deterioration_reasons": pm,
        "nested_deterioration_states": states,
        "profit_protection_status": si.get("profit_protection_status"),
        "current_campaign_relative_return": si.get("current_campaign_relative_return"),
        "observed_campaign_mfe": si.get("observed_campaign_mfe"),
        "observed_giveback": si.get("observed_giveback"),
    }


def _recovery_dimensions(*, action: str, reasons: list[str], si: Mapping[str, Any]) -> dict[str, Any]:
    lower_reasons = {reason.lower() for reason in reasons}
    reason_recovery = sorted(lower_reasons & {reason.lower() for reason in RECOVERY_REASONS})
    evidence_status = {str(si.get("hold_status") or ""), str(si.get("add_status") or "")}
    recovery_present = bool(action in {"HOLD", "ADD"} and (reason_recovery or "PASS" in evidence_status))
    reset_policy = "RESET" if recovery_present and reason_recovery else "DECAY" if recovery_present else "PRESERVE"
    return {
        "recovery_present": recovery_present,
        "pm_recovery_reasons": reason_recovery,
        "nested_recovery_states": sorted(RECOVERY_STATES & evidence_status),
        "reset_policy": reset_policy,
    }


def _pit_proof(position: Mapping[str, Any], *, business_date: str) -> dict[str, Any]:
    dates = [
        str(_nested(position, "adapter_source_contract", "business_date") or ""),
        str(_nested(position, "adapter_source_contract", "position_state_as_of") or ""),
        str(_nested(position, "adapter_source_contract", "valuation_date") or ""),
    ]
    future_dates = sorted({value for value in dates if value and value > business_date})
    return {
        "pit_validation_state": "FAIL_FUTURE_DATED_EVIDENCE" if future_dates else "PASS",
        "feature_dates": sorted({value for value in dates if value}),
        "future_dates": future_dates,
        "future_information_used": False,
    }


def _prior_reduce_count(position: Mapping[str, Any]) -> int:
    return _active_prior_reduce_count(_prior_unrepresentable_reduce_summary(position))


def _prior_unrepresentable_reduce_summary(position: Mapping[str, Any]) -> dict[str, Any]:
    si = _strategy_intelligence_evidence(position)
    summary = si.get("prior_unrepresentable_reduce_summary") if isinstance(si.get("prior_unrepresentable_reduce_summary"), Mapping) else {}
    if not summary:
        summary = si.get("reduce_history_summary") if isinstance(si.get("reduce_history_summary"), Mapping) else {}
    return dict(summary or {})


def _active_prior_reduce_count(summary: Mapping[str, Any]) -> int:
    dates = [str(item) for item in summary.get("prior_unrepresentable_reduce_dates") or [] if str(item)]
    reset_date = str(summary.get("last_recovery_reset_date") or "")
    if dates:
        return len([date for date in dates if not reset_date or date > reset_date])
    if reset_date:
        return 0
    try:
        return int(summary.get("event_count") or 0)
    except (TypeError, ValueError):
        return 0


def _active_prior_reduce_dates(summary: Mapping[str, Any]) -> list[str]:
    reset_date = str(summary.get("last_recovery_reset_date") or "")
    return [str(item) for item in summary.get("prior_unrepresentable_reduce_dates") or [] if str(item) and (not reset_date or str(item) > reset_date)]


def _soft_deterioration_episode(
    *,
    action: str,
    business_date: str,
    campaign_id: str,
    representability: Mapping[str, Any],
    deterioration: Mapping[str, Any],
    recovery: Mapping[str, Any],
    prior_summary: Mapping[str, Any],
    pit_pass: bool,
) -> dict[str, Any]:
    active_dates = _active_prior_reduce_dates(prior_summary)
    active_count = _active_prior_reduce_count(prior_summary)
    hard = _hard_deterioration_present(action=action, reasons=deterioration.get("pm_deterioration_reasons") or [], deterioration=deterioration)
    soft = _soft_deterioration_present(action=action, deterioration=deterioration)
    zero_lot = bool(
        action == "REDUCE"
        and representability.get("representability_family") == "DISCRETE_LOT"
        and (representability.get("final_reduce_quantity") or 0) == 0
    )
    prior_cleared = bool(prior_summary.get("last_recovery_reset_date")) and active_count == 0
    if hard:
        state = TERMINAL_DETERIORATION
    elif recovery.get("recovery_present") and pit_pass:
        state = SOFT_DETERIORATION_CLOSED if active_count > 0 or soft else NO_ACTIVE_SOFT_DETERIORATION
    elif action == "REDUCE" and soft and active_count > 0:
        state = SOFT_DETERIORATION_PERSISTENT
    elif action == "REDUCE" and soft:
        state = SOFT_DETERIORATION_ACTIVE
    else:
        state = NO_ACTIVE_SOFT_DETERIORATION

    start = active_dates[0] if active_dates else business_date if state in {SOFT_DETERIORATION_ACTIVE, SOFT_DETERIORATION_PERSISTENT} else ""
    episode_id = f"{campaign_id}:soft-deterioration:{start}" if campaign_id and start else ""
    severity = (
        "TERMINAL"
        if state == TERMINAL_DETERIORATION
        else "PERSISTENT"
        if state == SOFT_DETERIORATION_PERSISTENT
        else "ACTIVE"
        if state == SOFT_DETERIORATION_ACTIVE
        else "CLOSED"
        if state == SOFT_DETERIORATION_CLOSED
        else "NONE"
    )
    increment_reasons = list(deterioration.get("pm_deterioration_reasons") or [])
    return {
        "schema_version": "phase32_x_soft_deterioration_episode.v1",
        "owner": "POSITION_MANAGEMENT_PM",
        "soft_deterioration_episode_id": episode_id,
        "soft_deterioration_episode_state": state,
        "episode_start_business_date": start,
        "episode_last_deterioration_business_date": business_date if action == "REDUCE" and soft else active_dates[-1] if active_dates else "",
        "episode_persistence_severity": severity,
        "episode_increment_evidence": {
            "business_date": business_date,
            "pm_deterioration_reasons": increment_reasons,
            "deterioration_state": "SOFT" if soft and not hard else "TERMINAL" if hard else "NONE",
            "zero_lot_reduce": zero_lot,
            "representability_family": representability.get("representability_family"),
            "final_reduce_quantity": representability.get("final_reduce_quantity"),
        },
        "episode_recovery_evidence": {
            "recovery_state": "RECOVERY_PRESENT" if recovery.get("recovery_present") else "NO_RECOVERY",
            "recovery_dimensions": dict(recovery),
        },
        "episode_deescalation_reason": "RENEWED_STRENGTH_CONFIRMED" if state == SOFT_DETERIORATION_CLOSED else "",
        "prior_soft_deterioration_cleared": prior_cleared or state == SOFT_DETERIORATION_CLOSED,
        "active_prior_unrepresentable_reduce_count": active_count,
        "active_prior_unrepresentable_reduce_dates": active_dates,
        "last_recovery_reset_date": prior_summary.get("last_recovery_reset_date"),
        "zero_lot_reduce_persistence_scope": "ACTIVE_SOFT_EPISODE_ONLY" if zero_lot else "NOT_APPLICABLE",
        "future_information_used": False,
        "outcome_used_for_parameter_selection": False,
    }


def _exit_confirmation_state(
    *,
    action: str,
    reasons: list[str],
    deterioration: Mapping[str, Any],
    recovery: Mapping[str, Any],
    episode: Mapping[str, Any],
    pit_pass: bool,
) -> dict[str, Any]:
    hard = _hard_deterioration_present(action=action, reasons=reasons, deterioration=deterioration)
    active_episode = episode.get("soft_deterioration_episode_state") == SOFT_DETERIORATION_PERSISTENT
    independent = _independent_deterioration_dimensions(deterioration)
    if not pit_pass:
        state = DEFENSIVE_ONLY
        reason = "pit_proof_failed"
    elif hard:
        state = TERMINAL_BREAKDOWN
        reason = "hard_or_terminal_deterioration_present"
    elif active_episode and not recovery.get("recovery_present") and independent:
        state = CONFIRMED_DETERIORATION
        reason = "active_unrecovered_episode_with_independent_deterioration"
    else:
        state = DEFENSIVE_ONLY
        reason = "soft_deterioration_not_terminal"
    return {
        "schema_version": "phase32_x_non_emergency_exit_confirmation.v1",
        "owner": "POSITION_MANAGEMENT_PM",
        "exit_confirmation_state": state,
        "exit_confirmation_reason": reason,
        "hard_deterioration_present": hard,
        "active_soft_deterioration_episode": active_episode,
        "independent_deterioration_dimensions": independent,
        "recovery_present": bool(recovery.get("recovery_present")),
        "future_information_used": False,
        "outcome_used_for_parameter_selection": False,
    }


def _hard_deterioration_present(*, action: str, reasons: list[str], deterioration: Mapping[str, Any]) -> bool:
    lowered = {str(item).lower() for item in reasons}
    terminal = {
        "hard_stop_current_return",
        "trend_and_opportunity_broken",
        "trend_and_expected_edge_broken",
        "safety_full_close",
        "safety_hard_constraint",
        "broker_block",
        "corporate_action_block",
        "severe_liquidity_failure",
        "high_downside_risk",
    }
    return bool(lowered & terminal or deterioration.get("expected_edge_state") in {"INSUFFICIENT", "RISK_OVERRIDE"})


def _soft_deterioration_present(*, action: str, deterioration: Mapping[str, Any]) -> bool:
    if action != "REDUCE":
        return False
    lowered = {str(item).lower() for item in deterioration.get("pm_deterioration_reasons") or []}
    return bool(
        lowered & {"risk_increased_but_trend_not_broken", "peak_drawdown_warning", "expected_edge_risk_deterioration"}
        or deterioration.get("nested_deterioration_states")
    )


def _independent_deterioration_dimensions(deterioration: Mapping[str, Any]) -> list[str]:
    dimensions: list[str] = []
    states = {str(item).upper() for item in deterioration.get("nested_deterioration_states") or []}
    reasons = {str(item).lower() for item in deterioration.get("pm_deterioration_reasons") or []}
    if reasons & {"peak_drawdown_warning", "expected_edge_risk_deterioration", "profit_retention_break"}:
        dimensions.append("pm_independent_risk_review")
    if states & {"DECELERATING", "HIGH_RISK"}:
        dimensions.append("nested_deterioration_confirmed")
    if deterioration.get("expected_edge_state") in {"DETERIORATING", "INSUFFICIENT", "RISK_OVERRIDE"}:
        dimensions.append("expected_edge_deterioration")
    campaign_return = _float_or_none(deterioration.get("current_campaign_relative_return"))
    if campaign_return is not None and campaign_return < 0:
        dimensions.append("campaign_return_failing")
    return sorted(set(dimensions))


def _campaign_identity_status(position: Mapping[str, Any]) -> str:
    status = _strategy_intelligence_evidence(position).get("campaign_identity_authority_status")
    return str(status or "").upper()


def _state(row: Mapping[str, Any], *keys: str, default: str = "UNKNOWN") -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip().upper()
    return default


def _nested(row: Mapping[str, Any], *keys: str) -> Any:
    value: Any = row
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
