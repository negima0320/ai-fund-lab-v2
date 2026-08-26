from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "phase31_f1d_canonical_sell_semantic_shadow.v1"
PRODUCER = "strategy.canonical_sell_semantic_shadow"
AUTHORITY_TYPE = "CANONICAL_SELL_SEMANTIC_AUTHORITY_SHADOW"
MODE = "NON_MUTATING_SHADOW"

AGGREGATE_PASS_SEMANTICS = "EVIDENCE_AVAILABLE_NOT_HEALTH_SIGNAL"

HEALTHY_OR_RECOVERING = "HEALTHY_OR_RECOVERING"
WEAKENING_BUT_INTACT = "WEAKENING_BUT_INTACT"
PERSISTENT_DETERIORATION = "PERSISTENT_DETERIORATION"
EXIT_GRADE = "EXIT_GRADE"
UNRESOLVED = "UNRESOLVED"

REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT = "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT"
REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL = "REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL"

EXIT_GRADE_REASONS = {
    "trend_and_opportunity_broken",
    "weak_hold_score",
    "profit_retention_break",
    "hard_stop_current_return",
    "trend_and_expected_edge_broken",
    "EXIT_BY_WEAK_HOLD_SCORE",
    "hard_stop_current_return",
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


def build_canonical_sell_semantic_shadow_payload(
    *,
    business_date: str,
    position_management_payload: Mapping[str, Any],
    position_sizing_payload: Mapping[str, Any] | None = None,
    strategy_intelligence_payload: Mapping[str, Any] | None = None,
    prior_campaign_events: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    source_artifacts: Mapping[str, Any] | None = None,
    source_hashes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ps_by_symbol = {_symbol(row): row for row in _rows(position_sizing_payload or {}, "positions", "items") if _symbol(row)}
    si_by_symbol = _strategy_intelligence_by_symbol(strategy_intelligence_payload or {})
    prior = {str(key): list(value or []) for key, value in (prior_campaign_events or {}).items()}
    decisions = [
        _semantic_decision(
            pm_row,
            business_date=business_date,
            ps_row=ps_by_symbol.get(_symbol(pm_row), {}),
            strategy_intelligence=si_by_symbol.get(_symbol(pm_row), {}),
            prior_events=prior.get(_campaign_id(pm_row), []),
        )
        for pm_row in _rows(position_management_payload, "positions", "decisions", "items")
        if _symbol(pm_row)
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "business_date": business_date,
        "producer": PRODUCER,
        "authority_type": AUTHORITY_TYPE,
        "mode": MODE,
        "pit_status": "PIT_CURRENT_STRATEGY_EVIDENCE_ONLY",
        "aggregate_pass_semantics": AGGREGATE_PASS_SEMANTICS,
        "future_information_used": False,
        "later_pnl_used": False,
        "final_campaign_outcome_used": False,
        "outcome_used_for_parameter_selection": False,
        "market_context_logic_changed": False,
        "actual_trading_path_mutated": False,
        "canonical_pm_action_mutated": False,
        "canonical_pc_mutated": False,
        "canonical_ps_quantity_mutated": False,
        "canonical_runtime_planning_mutated": False,
        "pending_mutated": False,
        "submit_mutated": False,
        "execution_mutated": False,
        "production_consumer_count": 0,
        "decisions": decisions,
        "metrics": _metrics(decisions),
        "source_artifacts": dict(source_artifacts or {}),
        "source_hashes": dict(source_hashes or {}),
    }
    return {**payload, "artifact_hash": stable_payload_hash(payload)}


def write_canonical_sell_semantic_shadow_artifact(payload: Mapping[str, Any], output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def materialize_canonical_sell_semantic_shadow_for_day(
    *,
    run_root: Path | str,
    business_date: str,
    prior_campaign_events: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    output_subdir: str = "diagnostic_shadow",
) -> dict[str, Any]:
    run_root = Path(run_root)
    day_dir = run_root / "daily" / business_date
    strategy_dir = day_dir / "strategy"
    pm_path = strategy_dir / "position_management.json"
    ps_path = strategy_dir / "position_sizing.json"
    si_path = strategy_dir / "strategy_intelligence.json"
    payload = build_canonical_sell_semantic_shadow_payload(
        business_date=business_date,
        position_management_payload=_load_json(pm_path),
        position_sizing_payload=_load_json(ps_path),
        strategy_intelligence_payload=_load_json(si_path),
        prior_campaign_events=prior_campaign_events,
        source_artifacts={
            "position_management": str(pm_path),
            "position_sizing": str(ps_path),
            "strategy_intelligence": str(si_path),
        },
        source_hashes={
            "position_management": _file_hash(pm_path),
            "position_sizing": _file_hash(ps_path),
            "strategy_intelligence": _file_hash(si_path),
        },
    )
    output_path = day_dir / output_subdir / "canonical_sell_semantic_shadow.json"
    write_canonical_sell_semantic_shadow_artifact(payload, output_path)
    return {**payload, "artifact_path": str(output_path)}


def materialize_canonical_sell_semantic_shadow_for_run(
    *,
    run_root: Path | str,
    business_dates: Sequence[str] | None = None,
    output_subdir: str = "diagnostic_shadow",
) -> dict[str, Any]:
    run_root = Path(run_root)
    dates = list(business_dates or _completed_business_days(run_root))
    prior_events: dict[str, list[dict[str, Any]]] = {}
    materialized: list[dict[str, Any]] = []
    for business_date in dates:
        pm_path = run_root / "daily" / business_date / "strategy" / "position_management.json"
        if not pm_path.is_file():
            continue
        payload = materialize_canonical_sell_semantic_shadow_for_day(
            run_root=run_root,
            business_date=business_date,
            prior_campaign_events=prior_events,
            output_subdir=output_subdir,
        )
        _merge_prior_events(prior_events, payload)
        materialized.append(
            {
                "business_date": business_date,
                "artifact_path": payload["artifact_path"],
                "evaluated_pm_decision_count": payload["metrics"]["total_position_day_rows"],
                "state_distribution": payload["metrics"]["state_distribution"],
            }
        )
    summary = {
        "schema_version": "phase31_f1d_canonical_sell_semantic_shadow_materialization_summary.v1",
        "producer": PRODUCER,
        "mode": MODE,
        "run_root": str(run_root),
        "output_subdir": output_subdir,
        "materialized_day_count": len(materialized),
        "materialized": materialized,
        "actual_trading_path_mutated": False,
        "future_information_used": False,
        "production_consumer_count": 0,
        "metrics": _summary_metrics(materialized),
    }
    return summary


def stable_payload_hash(payload: Mapping[str, Any]) -> str:
    canonical = {key: value for key, value in dict(payload).items() if key != "artifact_hash"}
    encoded = json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _semantic_decision(
    pm_row: Mapping[str, Any],
    *,
    business_date: str,
    ps_row: Mapping[str, Any],
    strategy_intelligence: Mapping[str, Any],
    prior_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    action = _state(pm_row, "action", "decision", "pm_action")
    reason_codes = [str(code) for code in (pm_row.get("reason_codes") or pm_row.get("decision_reason_codes") or [])]
    si_evidence = _si_evidence(pm_row, strategy_intelligence)
    representability = _representability(action=action, pm_row=pm_row, ps_row=ps_row)
    recovery = _recovery_dimensions(action=action, reason_codes=reason_codes, si_evidence=si_evidence)
    deterioration = _deterioration_dimensions(action=action, reason_codes=reason_codes, si_evidence=si_evidence)
    pit = _pit_proof(business_date=business_date, strategy_intelligence=strategy_intelligence)
    prior_unrepresentable = _prior_unrepresentable_reduce_events(prior_events, business_date=business_date)
    canonical_state, state_reasons, parameter_status = _canonical_state(
        action=action,
        reason_codes=reason_codes,
        representability=representability,
        deterioration=deterioration,
        recovery=recovery,
        prior_unrepresentable_count=len(prior_unrepresentable),
        pit_pass=pit["pit_validation_state"] == "PASS",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "business_date": business_date,
        "symbol": _symbol(pm_row),
        "campaign_id": _campaign_id(pm_row),
        "current_pm_action": action,
        "pm_reasons": reason_codes,
        "pm_intensity": _state(pm_row, "intensity", "reduce_intensity", default=""),
        "pm_confidence": _float_or_none(pm_row.get("confidence") or pm_row.get("action_score")),
        "canonical_sell_state": canonical_state,
        "state_reasons": state_reasons,
        "aggregate_pass_semantics": AGGREGATE_PASS_SEMANTICS,
        "continuation_quality_status": si_evidence["continuation_quality_status"],
        "downside_risk_status": si_evidence["downside_risk_status"],
        "deterioration_dimensions": deterioration,
        "recovery_dimensions": recovery,
        "representability_family": representability["representability_family"],
        "representability_reason": representability["representability_reason"],
        "reduce_unrepresentable": representability["reduce_unrepresentable"],
        "one_lot_flag": representability["one_lot_flag"],
        "minimum_notional_flag": representability["minimum_notional_flag"],
        "current_quantity": representability["current_quantity"],
        "trading_unit": representability["trading_unit"],
        "raw_reduce_quantity": representability["raw_reduce_quantity"],
        "rounded_reduce_quantity": representability["rounded_reduce_quantity"],
        "reduce_final_sell_quantity": representability["reduce_final_sell_quantity"],
        "prior_unrepresentable_reduce_count": len(prior_unrepresentable),
        "prior_unrepresentable_reduce_dates": [str(item.get("business_date")) for item in prior_unrepresentable],
        "persistence_state": "PERSISTENCE_EVIDENCE_PRESENT" if prior_unrepresentable else "NO_PRIOR_UNREPRESENTABLE_REDUCE",
        "pit_proof": pit,
        "parameter_resolution_status": parameter_status,
        "alternative_g_join": _alternative_g_join_state(
            action=action,
            state=canonical_state,
            representability=representability,
            recovery=recovery,
            pit_pass=pit["pit_validation_state"] == "PASS",
        ),
        "future_information_used": False,
        "outcome_used_for_parameter_selection": False,
        "actual_pm_action_mutated": False,
    }


def _canonical_state(
    *,
    action: str,
    reason_codes: Sequence[str],
    representability: Mapping[str, Any],
    deterioration: Mapping[str, Any],
    recovery: Mapping[str, Any],
    prior_unrepresentable_count: int,
    pit_pass: bool,
) -> tuple[str, list[str], str]:
    lower_reasons = {reason.lower() for reason in reason_codes}
    if not pit_pass:
        return UNRESOLVED, ["pit_proof_failed"], "PIT_PROOF_FAILED"
    if lower_reasons & {reason.lower() for reason in EXIT_GRADE_REASONS} or action == "EXIT":
        return EXIT_GRADE, ["same_day_pm_exit_grade_reason_family"], "CANONICAL_EXISTING"
    if action in {"HOLD", "ADD"}:
        if recovery["recovery_present"]:
            return HEALTHY_OR_RECOVERING, ["fresh_pm_hold_add_recovery_evidence"], recovery["reset_policy"]
        return HEALTHY_OR_RECOVERING, ["pm_hold_add_no_exit_grade_reason"], "CANONICAL_EXISTING"
    if action != "REDUCE":
        return UNRESOLVED, ["unsupported_pm_action"], "UNSUPPORTED_ACTION"
    if not representability["reduce_unrepresentable"]:
        if deterioration["deterioration_present"]:
            return WEAKENING_BUT_INTACT, ["representable_reduce_with_current_deterioration"], "CANONICAL_EXISTING"
        return UNRESOLVED, ["reduce_without_deterioration_evidence"], "DETERIORATION_EVIDENCE_MISSING"
    if representability["representability_family"] == "MINIMUM_NOTIONAL":
        return UNRESOLVED, ["minimum_notional_policy_unresolved"], "MINIMUM_NOTIONAL_POLICY_UNRESOLVED"
    if recovery["recovery_present"]:
        return HEALTHY_OR_RECOVERING, ["recovery_guard_present"], recovery["reset_policy"]
    if prior_unrepresentable_count > 0 and deterioration["deterioration_present"]:
        return (
            PERSISTENT_DETERIORATION,
            ["prior_unrepresentable_reduce", "current_deterioration_evidence", "recovery_guard_absent"],
            "UNRESOLVED_FOR_EXIT",
        )
    if deterioration["deterioration_present"] or lower_reasons & {reason.lower() for reason in REDUCE_WEAKENING_REASONS}:
        return WEAKENING_BUT_INTACT, ["current_reduce_weakening_but_intact"], "CANONICAL_EXISTING"
    return UNRESOLVED, ["deterioration_semantics_unresolved"], "DETERIORATION_EVIDENCE_MISSING"


def _representability(*, action: str, pm_row: Mapping[str, Any], ps_row: Mapping[str, Any]) -> dict[str, Any]:
    current_quantity = _float_or_none(ps_row.get("current_quantity") or pm_row.get("current_quantity") or pm_row.get("runtime_position_quantity"))
    trading_unit = _float_or_none(ps_row.get("trading_unit") or ps_row.get("tradable_unit") or _nested(ps_row, "reduce_executability_evidence", "tradable_unit"))
    raw_reduce_quantity = _float_or_none(ps_row.get("raw_reduce_quantity") or _nested(ps_row, "reduce_executability_evidence", "raw_reduce_quantity"))
    rounded_reduce_quantity = _float_or_none(ps_row.get("rounded_reduce_quantity") or _nested(ps_row, "reduce_executability_evidence", "rounded_reduce_quantity"))
    final_reduce_quantity = _float_or_none(
        _first_present(
            ps_row.get("reduce_final_sell_quantity"),
            ps_row.get("final_sell_quantity"),
            _nested(ps_row, "reduce_executability_evidence", "final_sell_quantity"),
        )
    )
    semantic = _state(ps_row, "reduce_execution_semantic", default="")
    is_reduce = action == "REDUCE"
    discrete = bool(is_reduce and (semantic == REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT or (final_reduce_quantity == 0 and rounded_reduce_quantity == 0)))
    minimum = bool(is_reduce and semantic == REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL)
    representable = bool(is_reduce and not discrete and not minimum and (final_reduce_quantity or 0) > 0)
    return {
        "representability_family": "DISCRETE_LOT" if discrete else "MINIMUM_NOTIONAL" if minimum else "REPRESENTABLE" if representable else "NOT_APPLICABLE",
        "representability_reason": semantic,
        "reduce_unrepresentable": bool(discrete or minimum),
        "one_lot_flag": bool(current_quantity is not None and trading_unit is not None and current_quantity <= trading_unit),
        "minimum_notional_flag": minimum,
        "current_quantity": current_quantity,
        "trading_unit": trading_unit,
        "raw_reduce_quantity": raw_reduce_quantity,
        "rounded_reduce_quantity": rounded_reduce_quantity,
        "reduce_final_sell_quantity": final_reduce_quantity,
    }


def _si_evidence(pm_row: Mapping[str, Any], si: Mapping[str, Any]) -> dict[str, Any]:
    continuation = si.get("continuation_quality") if isinstance(si.get("continuation_quality"), Mapping) else {}
    downside = si.get("downside_risk") if isinstance(si.get("downside_risk"), Mapping) else {}
    entry = si.get("entry_admission") if isinstance(si.get("entry_admission"), Mapping) else {}
    profit = si.get("profit_protection_evidence") if isinstance(si.get("profit_protection_evidence"), Mapping) else {}
    attached_profit = pm_row.get("strategy_intelligence_profit_protection_evidence")
    if not profit and isinstance(attached_profit, Mapping):
        profit = attached_profit
    lifecycle = si.get("lifecycle_context") if isinstance(si.get("lifecycle_context"), Mapping) else {}
    return {
        "continuation_quality_status": str(pm_row.get("strategy_intelligence_continuation_quality_status") or continuation.get("status") or "").upper(),
        "downside_risk_status": str(pm_row.get("strategy_intelligence_downside_risk_status") or downside.get("status") or "").upper(),
        "trend_health": _semantic_state(continuation.get("trend_health")),
        "persistence": _semantic_state(continuation.get("persistence")),
        "acceleration_state": _semantic_state(continuation.get("acceleration_state")),
        "participation_quality": _semantic_state(continuation.get("participation_quality")),
        "relative_strength": _semantic_state(continuation.get("relative_strength")),
        "participation_risk": _semantic_state(downside.get("participation_risk")),
        "reversal_risk": _semantic_state(downside.get("reversal_risk")),
        "volatility_risk": _semantic_state(downside.get("volatility_risk")),
        "event_uncertainty": _semantic_state(downside.get("event_uncertainty")),
        "entry_state": str(entry.get("entry_state") or "").upper(),
        "admission_action": str(entry.get("admission_action") or "").upper(),
        "profit_protection_status": str(pm_row.get("strategy_intelligence_profit_protection_status") or profit.get("status") or "").upper(),
        "continuation_deterioration_connection": [str(item).upper() for item in profit.get("continuation_deterioration_connection") or []],
        "downside_risk_rise_connection": [str(item).upper() for item in profit.get("downside_risk_rise_connection") or []],
        "current_campaign_relative_return": _float_or_none(
            pm_row.get("strategy_intelligence_current_campaign_relative_return") or lifecycle.get("current_campaign_relative_return")
        ),
        "observed_campaign_mfe": _float_or_none(pm_row.get("strategy_intelligence_observed_campaign_mfe") or lifecycle.get("observed_campaign_mfe")),
        "observed_giveback": _float_or_none(pm_row.get("strategy_intelligence_observed_giveback") or lifecycle.get("observed_giveback")),
    }


def _deterioration_dimensions(*, action: str, reason_codes: Sequence[str], si_evidence: Mapping[str, Any]) -> dict[str, Any]:
    lower_reasons = {reason.lower() for reason in reason_codes}
    pm = sorted(lower_reasons & ({reason.lower() for reason in REDUCE_WEAKENING_REASONS} | {reason.lower() for reason in EXIT_GRADE_REASONS}))
    nested = [
        str(value)
        for value in (
            si_evidence.get("trend_health"),
            si_evidence.get("persistence"),
            si_evidence.get("acceleration_state"),
            si_evidence.get("participation_quality"),
            si_evidence.get("participation_risk"),
            si_evidence.get("reversal_risk"),
            si_evidence.get("volatility_risk"),
            si_evidence.get("event_uncertainty"),
            si_evidence.get("entry_state"),
            si_evidence.get("admission_action"),
            *(si_evidence.get("continuation_deterioration_connection") or []),
            *(si_evidence.get("downside_risk_rise_connection") or []),
        )
        if value
    ]
    deterioration_states = sorted({value for value in nested if value in DETERIORATION_STATES or value in {"CONTINUATION_WITH_CAUTION", "ADD_REDUCED_ONLY", "NO_ADD"}})
    return {
        "deterioration_present": bool(pm or deterioration_states or action == "EXIT"),
        "pm_deterioration_reasons": pm,
        "nested_deterioration_states": deterioration_states,
        "profit_protection_status": si_evidence.get("profit_protection_status"),
        "current_campaign_relative_return": si_evidence.get("current_campaign_relative_return"),
        "observed_campaign_mfe": si_evidence.get("observed_campaign_mfe"),
        "observed_giveback": si_evidence.get("observed_giveback"),
    }


def _recovery_dimensions(*, action: str, reason_codes: Sequence[str], si_evidence: Mapping[str, Any]) -> dict[str, Any]:
    lower_reasons = {reason.lower() for reason in reason_codes}
    reason_recovery = sorted(lower_reasons & {reason.lower() for reason in RECOVERY_REASONS})
    state_values = [
        str(si_evidence.get("entry_state") or ""),
        str(si_evidence.get("admission_action") or ""),
        str(si_evidence.get("trend_health") or ""),
        str(si_evidence.get("persistence") or ""),
        str(si_evidence.get("participation_quality") or ""),
    ]
    state_recovery = sorted({value for value in state_values if value in RECOVERY_STATES})
    recovery_present = bool(action in {"HOLD", "ADD"} and (reason_recovery or state_recovery))
    reset_policy = "RESET" if action in {"HOLD", "ADD"} and reason_recovery else "DECAY" if recovery_present else "PRESERVE"
    return {
        "recovery_present": recovery_present,
        "pm_recovery_reasons": reason_recovery,
        "nested_recovery_states": state_recovery,
        "reset_policy": reset_policy,
    }


def _pit_proof(*, business_date: str, strategy_intelligence: Mapping[str, Any]) -> dict[str, Any]:
    feature_dates = []
    for key in ("feature_date", "as_of_business_date", "business_date", "_artifact_feature_date", "_artifact_business_date"):
        value = str(strategy_intelligence.get(key) or "")
        if value:
            feature_dates.append(value)
    future_dates = sorted({date for date in feature_dates if date > business_date})
    return {
        "pit_validation_state": "FAIL_FUTURE_DATED_EVIDENCE" if future_dates else "PASS",
        "feature_dates": sorted(set(feature_dates)),
        "future_dates": future_dates,
        "future_information_used": False,
    }


def _alternative_g_join_state(
    *,
    action: str,
    state: str,
    representability: Mapping[str, Any],
    recovery: Mapping[str, Any],
    pit_pass: bool,
) -> dict[str, Any]:
    persistent_candidate = bool(
        action == "REDUCE"
        and representability.get("reduce_unrepresentable")
        and state == PERSISTENT_DETERIORATION
        and not recovery.get("recovery_present")
        and pit_pass
    )
    exit_grade_candidate = bool(
        action == "REDUCE"
        and representability.get("reduce_unrepresentable")
        and state == EXIT_GRADE
        and not recovery.get("recovery_present")
        and pit_pass
    )
    return {
        "alternative_g_persistent_exit_candidate": persistent_candidate,
        "alternative_g_exit_grade_candidate": exit_grade_candidate,
        "pm_action_mutated": False,
    }


def _metrics(decisions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    states = _count_by(decisions, "canonical_sell_state")
    actions = _count_by(decisions, "current_pm_action")
    action_state: dict[str, dict[str, int]] = {}
    for decision in decisions:
        action = str(decision.get("current_pm_action") or "UNKNOWN")
        state = str(decision.get("canonical_sell_state") or "UNKNOWN")
        action_state.setdefault(action, {})
        action_state[action][state] = action_state[action].get(state, 0) + 1
    return {
        "total_position_day_rows": len(decisions),
        "state_distribution": states,
        "pm_action_distribution": actions,
        "pm_action_state_distribution": action_state,
        "healthy_or_recovering_count": states.get(HEALTHY_OR_RECOVERING, 0),
        "weakening_but_intact_count": states.get(WEAKENING_BUT_INTACT, 0),
        "persistent_deterioration_count": states.get(PERSISTENT_DETERIORATION, 0),
        "exit_grade_count": states.get(EXIT_GRADE, 0),
        "unresolved_count": states.get(UNRESOLVED, 0),
        "future_information_used_count": sum(1 for item in decisions if item.get("future_information_used")),
        "production_consumer_count": 0,
    }


def _summary_metrics(materialized: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    state_totals: dict[str, int] = {}
    rows = 0
    for item in materialized:
        rows += int(item.get("evaluated_pm_decision_count") or 0)
        for state, count in (item.get("state_distribution") or {}).items():
            state_totals[state] = state_totals.get(state, 0) + int(count)
    return {
        "total_position_day_rows": rows,
        "state_distribution": state_totals,
    }


def _merge_prior_events(prior_events: dict[str, list[dict[str, Any]]], payload: Mapping[str, Any]) -> None:
    for decision in payload.get("decisions") or []:
        campaign_id = str(decision.get("campaign_id") or "")
        if not campaign_id:
            continue
        if decision.get("current_pm_action") in {"HOLD", "ADD"} and decision.get("recovery_dimensions", {}).get("recovery_present"):
            prior_events[campaign_id] = []
            continue
        if decision.get("current_pm_action") == "REDUCE" and decision.get("reduce_unrepresentable"):
            prior_events.setdefault(campaign_id, []).append(
                {
                    "business_date": decision.get("business_date"),
                    "symbol": decision.get("symbol"),
                    "campaign_id": campaign_id,
                    "current_pm_action": decision.get("current_pm_action"),
                    "reduce_unrepresentable": True,
                    "canonical_sell_state": decision.get("canonical_sell_state"),
                }
            )


def _prior_unrepresentable_reduce_events(prior_events: Sequence[Mapping[str, Any]], *, business_date: str) -> list[dict[str, Any]]:
    return [
        dict(event)
        for event in prior_events
        if str(event.get("business_date") or "") < business_date
        and str(event.get("current_pm_action") or event.get("baseline_pm_action") or "") == "REDUCE"
        and bool(event.get("reduce_unrepresentable", event.get("reduce_unrepresentable_due_to_lot", True)))
    ]


def _strategy_intelligence_by_symbol(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    symbol_map = payload.get("symbol_intelligence")
    if isinstance(symbol_map, Mapping):
        artifact_fields = {
            "_artifact_business_date": payload.get("business_date"),
            "_artifact_feature_date": payload.get("feature_date") or payload.get("as_of_business_date") or payload.get("business_date"),
        }
        return {str(key): {**dict(value), **artifact_fields} for key, value in symbol_map.items() if isinstance(value, Mapping)}
    rows = _rows(payload, "positions", "items")
    return {_symbol(row): row for row in rows if _symbol(row)}


def _rows(payload: Mapping[str, Any], *keys: str) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, Mapping)]
    if not isinstance(payload, Mapping):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, Mapping)]
    return []


def _completed_business_days(run_root: Path) -> list[str]:
    run_state = _load_json(run_root / "run_state.json")
    dates = run_state.get("completed_business_days") if isinstance(run_state, Mapping) else None
    if isinstance(dates, list):
        return [str(date) for date in dates]
    daily = run_root / "daily"
    return [path.name for path in sorted(daily.iterdir()) if path.is_dir()] if daily.is_dir() else []


def _load_json(path: Path | str) -> Any:
    path = Path(path)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _file_hash(path: Path | str) -> str:
    path = Path(path)
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _symbol(row: Mapping[str, Any]) -> str:
    return str(row.get("security_code") or row.get("symbol") or row.get("code") or row.get("ticker") or "")


def _campaign_id(row: Mapping[str, Any]) -> str:
    return str(row.get("position_campaign_id") or row.get("strategy_intelligence_campaign_id") or row.get("campaign_id") or "")


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


def _semantic_state(value: Any) -> str:
    if isinstance(value, Mapping):
        return str(value.get("state") or value.get("status") or "").upper()
    return str(value or "").upper()


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _count_by(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(field) or "UNKNOWN")
        counts[value] = counts.get(value, 0) + 1
    return counts
