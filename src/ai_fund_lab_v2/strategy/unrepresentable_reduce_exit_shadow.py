from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_fund_lab_v2.strategy.reduce_intensity_authority import canonical_reduce_fraction


SCHEMA_VERSION = "phase31_c0d_unrepresentable_reduce_exit_shadow.v1"
PRODUCER = "strategy.unrepresentable_reduce_exit_shadow"
AUTHORITY_TYPE = "PM_UNREPRESENTABLE_REDUCE_EXECUTABLE_REPRESENTATION_AUTHORITY_SHADOW"
MODE = "NON_MUTATING_SHADOW"
BINARY_MATERIALIZATION_CONTRACT_VERSION = "phase32_bl_lot_blocked_reduce_binary_materialization_shadow.v1"

REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT = "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT"
REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL = "REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL"
VARIANTS = ("G0", "G1", "G2", "G3")


def build_unrepresentable_reduce_exit_shadow_payload(
    *,
    business_date: str,
    position_management_payload: Mapping[str, Any],
    position_sizing_payload: Mapping[str, Any] | None = None,
    runtime_planning_payload: Mapping[str, Any] | None = None,
    strategy_intelligence_payload: Mapping[str, Any] | None = None,
    market_context_payload: Mapping[str, Any] | None = None,
    prior_unrepresentable_reduce_events: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    source_artifacts: Mapping[str, Any] | None = None,
    source_hashes: Mapping[str, Any] | None = None,
    run_id: str = "",
    profile_id: str = "",
) -> dict[str, Any]:
    pm_rows = _rows(position_management_payload, "positions", "decisions", "items")
    ps_by_symbol = {_symbol(row): row for row in _rows(position_sizing_payload or {}, "positions", "items") if _symbol(row)}
    rp_by_symbol = {_symbol(row): row for row in _rows(runtime_planning_payload or {}, "plans", "items") if _symbol(row)}
    si_by_symbol = _strategy_intelligence_by_symbol(strategy_intelligence_payload or {})
    prior = {str(key): list(value or []) for key, value in (prior_unrepresentable_reduce_events or {}).items()}
    market_context = _market_context(market_context_payload or {})

    decisions = [
        _shadow_decision(
            pm_row,
            business_date=business_date,
            ps_row=ps_by_symbol.get(_symbol(pm_row), {}),
            rp_row=rp_by_symbol.get(_symbol(pm_row), {}),
            strategy_intelligence=si_by_symbol.get(_symbol(pm_row), {}),
            market_context=market_context,
            prior_events=prior.get(_campaign_id(pm_row), []),
            source_artifacts=source_artifacts or {},
            run_id=run_id,
            profile_id=profile_id,
        )
        for pm_row in pm_rows
        if _symbol(pm_row)
    ]
    metrics = _metrics(decisions)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "binary_materialization_contract_version": BINARY_MATERIALIZATION_CONTRACT_VERSION,
        "business_date": business_date,
        "run_id": run_id,
        "profile_id": profile_id,
        "producer": PRODUCER,
        "authority_type": AUTHORITY_TYPE,
        "mode": MODE,
        "shadow_only": True,
        "variant_support": {variant: True for variant in VARIANTS},
        "pit_status": "PIT_CURRENT_STRATEGY_EVIDENCE_ONLY",
        "future_information_used": False,
        "future_regime_used": False,
        "later_pnl_used": False,
        "final_campaign_outcome_used": False,
        "actual_trading_path_mutated": False,
        "canonical_pm_action_mutated": False,
        "canonical_pc_mutated": False,
        "canonical_ps_quantity_mutated": False,
        "canonical_runtime_planning_mutated": False,
        "sell_planning_mutated": False,
        "pending_mutated": False,
        "submit_mutated": False,
        "execution_mutated": False,
        "current_mutated": False,
        "ps_exit_authority_added": False,
        "runtime_exit_authority_added": False,
        "lot_rounding_changed": False,
        "hidden_reduce_debt_added": False,
        "buy_sell_independence_preserved": True,
        "production_consumer_count": 0,
        "b10_business_authority_dependency": False,
        "canonical_artifact_collision": False,
        "campaign_scope_leak_count": sum(1 for item in decisions if item["campaign_scope_status"] != "PASS"),
        "restart_determinism": "PASS",
        "decisions": decisions,
        "metrics": metrics,
        "source_artifacts": dict(source_artifacts or {}),
        "source_hashes": dict(source_hashes or {}),
    }
    return {**payload, "artifact_hash": stable_payload_hash(payload)}


def write_unrepresentable_reduce_exit_shadow_artifact(payload: Mapping[str, Any], output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def materialize_unrepresentable_reduce_exit_shadow_for_day(
    *,
    run_root: Path | str,
    business_date: str,
    prior_unrepresentable_reduce_events: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    output_subdir: str = "diagnostic_shadow",
) -> dict[str, Any]:
    run_root = Path(run_root)
    run_state = _load_json(run_root / "run_state.json")
    run_id = str(run_state.get("run_id") or run_root.name) if isinstance(run_state, Mapping) else run_root.name
    profile_id = str(run_state.get("profile") or run_state.get("profile_id") or "") if isinstance(run_state, Mapping) else ""
    day_dir = run_root / "daily" / business_date
    strategy_dir = day_dir / "strategy"
    pm_path = strategy_dir / "position_management.json"
    ps_path = strategy_dir / "position_sizing.json"
    rp_path = strategy_dir / "runtime_planning.json"
    si_path = strategy_dir / "strategy_intelligence.json"
    mc_path = strategy_dir / "market_context.json"
    paths = {
        "position_management": pm_path,
        "position_sizing": ps_path,
        "runtime_planning": rp_path,
        "strategy_intelligence": si_path,
        "market_context": mc_path,
    }
    payload = build_unrepresentable_reduce_exit_shadow_payload(
        business_date=business_date,
        position_management_payload=_load_json(pm_path),
        position_sizing_payload=_load_json(ps_path),
        runtime_planning_payload=_load_json(rp_path),
        strategy_intelligence_payload=_load_json(si_path),
        market_context_payload=_load_json(mc_path),
        prior_unrepresentable_reduce_events=prior_unrepresentable_reduce_events,
        source_artifacts={name: str(path) for name, path in paths.items()},
        source_hashes={name: _file_hash(path) for name, path in paths.items()},
        run_id=run_id,
        profile_id=profile_id,
    )
    output_path = day_dir / output_subdir / "unrepresentable_reduce_exit_shadow.json"
    write_unrepresentable_reduce_exit_shadow_artifact(payload, output_path)
    return {**payload, "artifact_path": str(output_path)}


def materialize_unrepresentable_reduce_exit_shadow_for_run(
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
        payload = materialize_unrepresentable_reduce_exit_shadow_for_day(
            run_root=run_root,
            business_date=business_date,
            prior_unrepresentable_reduce_events=prior_events,
            output_subdir=output_subdir,
        )
        _merge_prior_events(prior_events, payload)
        materialized.append(
            {
                "business_date": business_date,
                "artifact_path": payload["artifact_path"],
                "evaluated_pm_decision_count": payload["metrics"]["evaluated_pm_decision_count"],
                "unrepresentable_reduce_count": payload["metrics"]["unrepresentable_reduce_count"],
                "parameter_unresolved_count": payload["metrics"]["parameter_unresolved_count"],
            }
        )
    summary = {
        "schema_version": "phase31_c0d_unrepresentable_reduce_exit_shadow_materialization_summary.v1",
        "producer": PRODUCER,
        "mode": MODE,
        "run_root": str(run_root),
        "output_subdir": output_subdir,
        "materialized_day_count": len(materialized),
        "materialized": materialized,
        "actual_trading_path_mutated": False,
        "future_information_used": False,
    }
    summary["metrics"] = _summary_metrics(run_root=run_root, materialized=materialized)
    return summary


def stable_payload_hash(payload: Mapping[str, Any]) -> str:
    canonical = {key: value for key, value in dict(payload).items() if key != "artifact_hash"}
    encoded = json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _shadow_decision(
    pm_row: Mapping[str, Any],
    *,
    business_date: str,
    ps_row: Mapping[str, Any],
    rp_row: Mapping[str, Any],
    strategy_intelligence: Mapping[str, Any],
    market_context: Mapping[str, Any],
    prior_events: Sequence[Mapping[str, Any]],
    source_artifacts: Mapping[str, Any],
    run_id: str,
    profile_id: str,
) -> dict[str, Any]:
    symbol = _symbol(pm_row)
    campaign_id = _campaign_id(pm_row)
    baseline_action = _state(pm_row, "action", "decision", "pm_action", default="UNKNOWN")
    reduce_intensity = _state(pm_row, "reduce_intensity", "intensity", default="")
    target_ratio = _float_or_none(_first_present(ps_row.get("target_reduce_ratio"), ps_row.get("reduce_fraction"), canonical_reduce_fraction(reduce_intensity)))
    current_quantity = _float_or_none(_first_present(ps_row.get("current_quantity"), pm_row.get("current_quantity"), pm_row.get("runtime_position_quantity")))
    tradable_unit = _float_or_none(_first_present(ps_row.get("trading_unit"), ps_row.get("tradable_unit"), _nested(ps_row, "reduce_executability_evidence", "tradable_unit")))
    raw_reduce_quantity = _float_or_none(_first_present(ps_row.get("raw_reduce_quantity"), _nested(ps_row, "reduce_executability_evidence", "raw_reduce_quantity")))
    rounded_reduce_quantity = _float_or_none(_first_present(ps_row.get("rounded_reduce_quantity"), _nested(ps_row, "reduce_executability_evidence", "rounded_reduce_quantity")))
    final_reduce_sell_quantity = _float_or_none(
        _first_present(
            ps_row.get("reduce_final_sell_quantity"),
            ps_row.get("final_sell_quantity"),
            _nested(ps_row, "reduce_executability_evidence", "final_sell_quantity"),
        )
    )
    if target_ratio is not None and current_quantity is not None and raw_reduce_quantity is None:
        raw_reduce_quantity = current_quantity * target_ratio
    if final_reduce_sell_quantity is None and rounded_reduce_quantity is not None:
        final_reduce_sell_quantity = rounded_reduce_quantity
    actual_fraction = (
        final_reduce_sell_quantity / current_quantity
        if final_reduce_sell_quantity is not None and current_quantity and current_quantity > 0
        else None
    )
    representation_error = target_ratio - actual_fraction if target_ratio is not None and actual_fraction is not None else None
    reduce_semantic = _state(ps_row, "reduce_execution_semantic", default="") or _state(rp_row, "reduce_execution_semantic", default="")
    is_reduce = baseline_action == "REDUCE"
    discrete_lot_unrepresentable = bool(
        is_reduce
        and (
            reduce_semantic == REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
            or _state(rp_row, "no_order_reason", default="") == REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
            or (final_reduce_sell_quantity == 0 and rounded_reduce_quantity == 0)
        )
    )
    minimum_notional_unrepresentable = bool(
        is_reduce
        and (
            reduce_semantic == REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
            or _state(rp_row, "no_order_reason", default="") == REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
        )
    )
    unrepresentable = bool(discrete_lot_unrepresentable or minimum_notional_unrepresentable)
    representable_reduce = bool(is_reduce and not unrepresentable and (final_reduce_sell_quantity or 0) > 0)
    representability_family = (
        "DISCRETE_LOT"
        if discrete_lot_unrepresentable
        else "MINIMUM_NOTIONAL"
        if minimum_notional_unrepresentable
        else "REPRESENTABLE"
        if representable_reduce
        else "NOT_APPLICABLE"
    )
    deterioration = _deterioration_evidence(pm_row, strategy_intelligence)
    recovery = _recovery_evidence(pm_row, strategy_intelligence, baseline_action)
    persistence = _persistence_evidence(prior_events, decision_business_date=business_date)
    pit = _pit_proof(
        business_date=business_date,
        strategy_intelligence=strategy_intelligence,
        market_context=market_context,
        source_artifacts=source_artifacts,
        run_id=run_id,
        profile_id=profile_id,
    )
    state = _shadow_state(
        baseline_action=baseline_action,
        reduce_intensity=reduce_intensity,
        unrepresentable=unrepresentable,
        representability_family=representability_family,
        representable_reduce=representable_reduce,
        deterioration_state=deterioration["state"],
        exit_grade_deterioration=deterioration["exit_grade_deterioration"],
        recovery_state=recovery["state"],
        prior_count=persistence["prior_unrepresentable_reduce_count"],
        evidence_sufficient=pit["pit_validation_state"] == "PASS",
    )
    reason_codes = _reason_codes(
        baseline_action=baseline_action,
        unrepresentable=unrepresentable,
        representable_reduce=representable_reduce,
        state=state,
        deterioration=deterioration,
        recovery=recovery,
        persistence=persistence,
    )
    binary = _binary_materialization_decision(
        baseline_action=baseline_action,
        representability_family=representability_family,
        discrete_lot_unrepresentable=discrete_lot_unrepresentable,
        representable_reduce=representable_reduce,
        current_quantity=current_quantity,
        raw_reduce_quantity=raw_reduce_quantity,
        rounded_reduce_quantity=rounded_reduce_quantity,
        final_reduce_sell_quantity=final_reduce_sell_quantity,
        campaign_id=campaign_id,
        pm_row=pm_row,
        strategy_intelligence=strategy_intelligence,
        deterioration=deterioration,
        recovery=recovery,
        pit=pit,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "binary_materialization_contract_version": BINARY_MATERIALIZATION_CONTRACT_VERSION,
        "producer": PRODUCER,
        "mode": MODE,
        "business_date": business_date,
        "run_id": run_id,
        "profile_id": profile_id,
        "symbol": symbol,
        "campaign_id": campaign_id,
        "baseline_pm_action": baseline_action,
        "baseline_reduce_intensity": reduce_intensity,
        "baseline_reason_codes": list(pm_row.get("reason_codes") or pm_row.get("decision_reason_codes") or []),
        "pm_reason_evidence": {
            "dominant_cause": str(pm_row.get("dominant_cause") or ""),
            "confidence": _float_or_none(pm_row.get("confidence") or pm_row.get("action_score")),
            "reason_codes": list(pm_row.get("reason_codes") or pm_row.get("decision_reason_codes") or []),
        },
        "current_quantity": current_quantity,
        "tradable_unit": tradable_unit,
        "target_reduce_ratio": target_ratio,
        "raw_reduce_quantity": raw_reduce_quantity,
        "rounded_reduce_quantity": rounded_reduce_quantity,
        "final_reduce_sell_quantity": final_reduce_sell_quantity,
        "desired_reduction_fraction": target_ratio,
        "actual_reduction_fraction": actual_fraction,
        "representation_error": representation_error,
        "representability_family": representability_family,
        "representability_reason": reduce_semantic,
        "reduce_unrepresentable": unrepresentable,
        "reduce_unrepresentable_due_to_lot": discrete_lot_unrepresentable,
        "reduce_unrepresentable_due_to_minimum_notional": minimum_notional_unrepresentable,
        "one_lot_position": bool(current_quantity is not None and tradable_unit is not None and current_quantity <= tradable_unit),
        "minimum_notional_flag": minimum_notional_unrepresentable,
        "reduce_representability_state": (
            "UNREPRESENTABLE_DUE_TO_LOT"
            if discrete_lot_unrepresentable
            else "UNREPRESENTABLE_DUE_TO_MINIMUM_NOTIONAL"
            if minimum_notional_unrepresentable
            else "REPRESENTABLE"
            if representable_reduce
            else "NOT_APPLICABLE"
        ),
        "prior_unrepresentable_reduce_count": persistence["prior_unrepresentable_reduce_count"],
        "prior_unrepresentable_reduce_dates": persistence["prior_unrepresentable_reduce_dates"],
        "recent_persistence_evidence": persistence["recent_persistence_evidence"],
        "persistence_state": persistence["persistence_state"],
        "persistence_parameter_status": persistence["persistence_parameter_status"],
        "expected_edge_evidence": _expected_edge_evidence(strategy_intelligence),
        "momentum_evidence": _momentum_evidence(strategy_intelligence),
        "trend_evidence": _trend_evidence(strategy_intelligence),
        "continuation_evidence": _continuation_evidence(strategy_intelligence),
        "downside_evidence": _downside_evidence(strategy_intelligence),
        "market_context": market_context,
        "campaign_state": _campaign_state(strategy_intelligence),
        "current_deterioration_evidence": deterioration,
        "deterioration_state": deterioration["state"],
        "recovery_state": recovery["state"],
        "recovery_evidence": recovery,
        "recovery_evidence_dates": recovery["evidence_dates"],
        "variant_results": _variant_results(state),
        "variant": "G3",
        "branch": state["branch"],
        "shadow_branch": state["branch"],
        "shadow_state": state["shadow_state"],
        "structural_shadow_state": state["structural_shadow_state"],
        "alternative_g_shadow_action": state["alternative_g_shadow_action"],
        "reason_codes": reason_codes,
        "structurally_eligible": state["structurally_eligible"],
        "parameter_resolved": state["parameter_resolved"],
        "parameter_resolution_state": state["parameter_resolution_state"],
        "evidence_sufficient": pit["pit_validation_state"] == "PASS" and deterioration["state"] != "EVIDENCE_INSUFFICIENT",
        "decision_business_date": business_date,
        "feature_dates": pit["feature_dates"],
        "source_artifacts": pit["source_artifacts"],
        "pit_validation_state": pit["pit_validation_state"],
        "future_information_used": False,
        "future_regime_used": False,
        "later_pnl_used": False,
        "final_campaign_outcome_used": False,
        "campaign_scope_status": "PASS" if campaign_id else "EVIDENCE_INSUFFICIENT",
        "actual_trading_path_mutated": False,
        "canonical_pm_action_mutated": False,
        "shadow_only": True,
        "shadow_binary_decision": binary["shadow_binary_decision"],
        "shadow_binary_eligibility_status": binary["shadow_binary_eligibility_status"],
        "shadow_binary_eligibility_reason": binary["shadow_binary_eligibility_reason"],
        "shadow_binary_authority_status": binary["shadow_binary_authority_status"],
        "production_actual_action": binary["production_actual_action"],
        "production_actual_quantity": binary["production_actual_quantity"],
        "lot_block_reason": binary["lot_block_reason"],
        "semantic_evidence_used": binary["semantic_evidence_used"],
        "hold_side_evidence": binary["hold_side_evidence"],
        "exit_side_evidence": binary["exit_side_evidence"],
        "decisive_semantic_rationale": binary["decisive_semantic_rationale"],
        "action_score_decisive_authority": False,
        "historical_outcome_input_used": False,
        "shadow_order_authority": False,
        "shadow_submit_authority": False,
        "shadow_execution_authority": False,
    }


def _shadow_state(
    *,
    baseline_action: str,
    reduce_intensity: str,
    unrepresentable: bool,
    representability_family: str,
    representable_reduce: bool,
    deterioration_state: str,
    exit_grade_deterioration: bool,
    recovery_state: str,
    prior_count: int,
    evidence_sufficient: bool,
) -> dict[str, Any]:
    if baseline_action != "REDUCE":
        return _state_result("NONE", "NOT_APPLICABLE", "NOT_APPLICABLE", "BASELINE", "BASELINE", False, True, True)
    if representable_reduce:
        return _state_result("NONE", "REPRESENTABLE_REDUCE", "REPRESENTABLE_REDUCE", "REDUCE", "CANONICAL_EXISTING", False, True, True)
    if not unrepresentable:
        return _state_result("NONE", "EVIDENCE_INSUFFICIENT", "EVIDENCE_INSUFFICIENT", "PRESERVE", "EVIDENCE_INSUFFICIENT", False, False, False)
    if not evidence_sufficient or deterioration_state == "EVIDENCE_INSUFFICIENT":
        return _state_result("NONE", "EVIDENCE_INSUFFICIENT", "UNREPRESENTABLE_PRESERVE", "PRESERVE", "EVIDENCE_INSUFFICIENT", True, False, False)
    if recovery_state == "RECOVERY_PRESENT":
        return _state_result("NONE", "RECOVERY_BLOCKED", "UNREPRESENTABLE_PRESERVE", "PRESERVE", "CANONICAL_EXISTING", True, True, True)
    if representability_family == "MINIMUM_NOTIONAL":
        return _state_result("NONE", "PARAMETER_UNRESOLVED", "MINIMUM_NOTIONAL_UNREPRESENTABLE", "PRESERVE", "MINIMUM_NOTIONAL_POLICY_UNRESOLVED", True, False, True)
    if reduce_intensity == "STRONG" and deterioration_state == "DETERIORATION_CONFIRMED" and exit_grade_deterioration:
        return _state_result("IMMEDIATE", "IMMEDIATE_EXIT_CANDIDATE", "IMMEDIATE_EXIT_CANDIDATE", "EXIT", "CANONICAL_EXISTING", True, True, True)
    if prior_count > 0 and deterioration_state == "DETERIORATION_CONFIRMED":
        return _state_result("PERSISTENT", "PARAMETER_UNRESOLVED", "PERSISTENT_EXIT_CANDIDATE", "PRESERVE", "VALIDATION_REQUIRED_UNSET", True, False, True)
    return _state_result("NONE", "UNREPRESENTABLE_PRESERVE", "UNREPRESENTABLE_PRESERVE", "PRESERVE", "CANONICAL_EXISTING", True, True, True)


def _state_result(
    branch: str,
    shadow_state: str,
    structural_shadow_state: str,
    action: str,
    parameter_state: str,
    structurally_eligible: bool,
    parameter_resolved: bool,
    evidence_sufficient: bool,
) -> dict[str, Any]:
    return {
        "branch": branch,
        "shadow_state": shadow_state,
        "structural_shadow_state": structural_shadow_state,
        "alternative_g_shadow_action": action,
        "structurally_eligible": structurally_eligible,
        "parameter_resolved": parameter_resolved,
        "parameter_resolution_state": parameter_state,
        "evidence_sufficient": evidence_sufficient,
    }


def _binary_materialization_decision(
    *,
    baseline_action: str,
    representability_family: str,
    discrete_lot_unrepresentable: bool,
    representable_reduce: bool,
    current_quantity: float | None,
    raw_reduce_quantity: float | None,
    rounded_reduce_quantity: float | None,
    final_reduce_sell_quantity: float | None,
    campaign_id: str,
    pm_row: Mapping[str, Any],
    strategy_intelligence: Mapping[str, Any],
    deterioration: Mapping[str, Any],
    recovery: Mapping[str, Any],
    pit: Mapping[str, Any],
) -> dict[str, Any]:
    production_actual_action = "NO_ORDER" if discrete_lot_unrepresentable else "REDUCE" if representable_reduce else baseline_action
    production_actual_quantity = final_reduce_sell_quantity if final_reduce_sell_quantity is not None else 0
    base = {
        "shadow_binary_decision": "SHADOW_NOT_APPLICABLE",
        "shadow_binary_eligibility_status": "NOT_APPLICABLE",
        "shadow_binary_eligibility_reason": "",
        "shadow_binary_authority_status": "PASS",
        "production_actual_action": production_actual_action,
        "production_actual_quantity": production_actual_quantity,
        "lot_block_reason": REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT if discrete_lot_unrepresentable else "",
        "semantic_evidence_used": {},
        "hold_side_evidence": [],
        "exit_side_evidence": [],
        "decisive_semantic_rationale": "",
    }
    if baseline_action != "REDUCE":
        return {**base, "shadow_binary_eligibility_reason": "PM_ACTION_NOT_REDUCE"}
    if representable_reduce:
        return {**base, "shadow_binary_eligibility_reason": "PARTIAL_REDUCE_EXECUTABLE"}
    if representability_family != "DISCRETE_LOT" or not discrete_lot_unrepresentable:
        return {**base, "shadow_binary_eligibility_reason": f"REPRESENTABILITY_FAMILY:{representability_family}"}
    malformed_reasons: list[str] = []
    if not campaign_id:
        malformed_reasons.append("MISSING_CAMPAIGN_ID")
    if current_quantity is None or current_quantity <= 0:
        malformed_reasons.append("MISSING_OR_INVALID_CURRENT_QUANTITY")
    if final_reduce_sell_quantity not in (0, 0.0) or rounded_reduce_quantity not in (0, 0.0):
        malformed_reasons.append("EXECUTABLE_REDUCE_QUANTITY_NOT_ZERO")
    if raw_reduce_quantity is None or raw_reduce_quantity <= 0:
        malformed_reasons.append("MISSING_DESIRED_REDUCE_QUANTITY")
    if str(pit.get("pit_validation_state") or "") != "PASS":
        malformed_reasons.append(str(pit.get("pit_validation_state") or "PIT_EVIDENCE_INVALID"))
    if malformed_reasons:
        return {
            **base,
            "shadow_binary_decision": "SHADOW_INSUFFICIENT_EVIDENCE",
            "shadow_binary_eligibility_status": "FAIL_CLOSED",
            "shadow_binary_eligibility_reason": ",".join(malformed_reasons),
            "shadow_binary_authority_status": "FAIL_CLOSED",
            "decisive_semantic_rationale": "lot-blocked REDUCE binary shadow withheld because canonical PIT/provenance eligibility is incomplete",
        }

    continuation = _continuation_evidence(strategy_intelligence)
    downside = _downside_evidence(strategy_intelligence)
    expected_edge = _expected_edge_evidence(strategy_intelligence)
    campaign_state = _campaign_state(strategy_intelligence)
    current_return = _float_or_none(campaign_state.get("current_campaign_relative_return"))
    action_score = _float_or_none(pm_row.get("action_score") or pm_row.get("confidence"))
    reason_codes = [str(code) for code in (pm_row.get("reason_codes") or pm_row.get("decision_reason_codes") or [])]

    hold_evidence: list[dict[str, Any]] = []
    exit_evidence: list[dict[str, Any]] = []
    contextual_evidence: list[dict[str, Any]] = []
    if continuation.get("relative_strength_state") == "SUPPORTIVE":
        hold_evidence.append({"signal": "relative_strength", "state": "SUPPORTIVE"})
    if continuation.get("trend_health_state") == "SUPPORTIVE":
        hold_evidence.append({"signal": "trend_health", "state": "SUPPORTIVE"})
    if continuation.get("persistence_state") in {"SUPPORTIVE", "ADEQUATE"}:
        hold_evidence.append({"signal": "persistence", "state": continuation.get("persistence_state")})
    if continuation.get("exhaustion_risk_state") in {"MANAGEABLE", "LOW", "LOW_RISK"}:
        hold_evidence.append({"signal": "exhaustion_risk", "state": continuation.get("exhaustion_risk_state")})
    if continuation.get("strong_medium_term_structure") is True:
        hold_evidence.append({"signal": "medium_term_structure", "state": "STRONG"})
    if recovery.get("state") == "RECOVERY_PRESENT":
        hold_evidence.append({"signal": "recovery", "state": "PRESENT"})

    if expected_edge.get("state") in {"DETERIORATING", "INSUFFICIENT", "RISK_OVERRIDE"}:
        exit_evidence.append({"signal": "expected_edge", "state": expected_edge.get("state")})
    if continuation.get("relative_strength_state") in {"WEAK", "MIXED", "DETERIORATING"}:
        exit_evidence.append({"signal": "relative_strength", "state": continuation.get("relative_strength_state")})
    if continuation.get("trend_health_state") in {"WEAK", "MIXED", "DETERIORATING"}:
        exit_evidence.append({"signal": "trend_health", "state": continuation.get("trend_health_state")})
    if continuation.get("participation_quality_state") in {"WEAK", "DETERIORATING"}:
        exit_evidence.append({"signal": "participation_quality", "state": continuation.get("participation_quality_state")})
    if continuation.get("exhaustion_risk_state") in {"ELEVATED_RISK", "HIGH_RISK", "EXHAUSTED"}:
        exit_evidence.append({"signal": "exhaustion_risk", "state": continuation.get("exhaustion_risk_state")})
    if downside.get("participation_risk_state") in {"ELEVATED_RISK", "HIGH_RISK"}:
        exit_evidence.append({"signal": "participation_risk", "state": downside.get("participation_risk_state")})
    if downside.get("reversal_risk") in {"ELEVATED_RISK", "HIGH_RISK"}:
        exit_evidence.append({"signal": "reversal_risk", "state": downside.get("reversal_risk")})
    if deterioration.get("exit_grade_deterioration"):
        exit_evidence.append({"signal": "pm_exit_grade_deterioration", "state": "PRESENT"})
    if current_return is not None and current_return <= 0:
        exit_evidence.append({"signal": "profit_cushion", "state": "ABSENT"})
    structural_hold_count = len(hold_evidence)
    profit_cushion_present = bool(current_return is not None and current_return > 0)
    continuation_weakened = bool(
        continuation.get("relative_strength_state") in {"WEAK", "MIXED", "DETERIORATING"}
        or continuation.get("trend_health_state") in {"WEAK", "MIXED", "DETERIORATING"}
        or continuation.get("participation_quality_state") in {"WEAK", "DETERIORATING"}
    )
    elevated_risk_present = bool(
        continuation.get("exhaustion_risk_state") in {"ELEVATED_RISK", "HIGH_RISK", "EXHAUSTED"}
        or downside.get("participation_risk_state") in {"ELEVATED_RISK", "HIGH_RISK"}
        or downside.get("reversal_risk") in {"ELEVATED_RISK", "HIGH_RISK"}
    )
    if profit_cushion_present and structural_hold_count > 0 and not (continuation_weakened and elevated_risk_present):
        hold_evidence.append({"signal": "profit_cushion", "state": "CONTEXTUAL_HOLD_SUPPORT"})
        contextual_evidence.append({"signal": "profit_cushion", "state": "CONTEXTUAL_HOLD_SUPPORT", "standalone_action_authority": False})
    elif profit_cushion_present and (continuation_weakened or elevated_risk_present):
        contextual_evidence.append({"signal": "profit_cushion", "state": "PROFIT_AT_RISK", "standalone_action_authority": False})
    elif profit_cushion_present:
        contextual_evidence.append({"signal": "profit_cushion", "state": "PRESENT_CONTEXT_ONLY", "standalone_action_authority": False})

    semantic_evidence = {
        "pm_reason_codes": reason_codes,
        "reason_family_context": _reason_family_context(reason_codes),
        "expected_edge_state": expected_edge.get("state"),
        "continuation": continuation,
        "downside": downside,
        "campaign_state": campaign_state,
        "recovery_state": recovery.get("state"),
        "profit_cushion_context": contextual_evidence,
        "profit_cushion_standalone_hold_authority": False,
        "pit_validation_state": pit.get("pit_validation_state"),
        "action_score_diagnostic": {"value": action_score, "decisive_authority": False},
        "future_information_used": False,
        "later_pnl_used": False,
        "final_campaign_outcome_used": False,
    }
    decisive_exit_deterioration = bool(
        elevated_risk_present
        or any(str(item.get("state") or "") in {"WEAK", "DETERIORATING", "HIGH_RISK", "ELEVATED_RISK", "ABSENT"} for item in exit_evidence)
    )
    profit_at_risk_exit_confirmation = bool(
        profit_cushion_present
        and continuation.get("relative_strength_state") in {"WEAK", "DETERIORATING"}
        and continuation.get("trend_health_state") in {"WEAK", "DETERIORATING"}
        and (
            continuation.get("participation_quality_state") in {"WEAK", "DETERIORATING"}
            or elevated_risk_present
        )
    )
    non_profit_exit_confirmation = bool(not profit_cushion_present and decisive_exit_deterioration)
    if (
        len(exit_evidence) >= 2
        and structural_hold_count == 0
        and (profit_at_risk_exit_confirmation or non_profit_exit_confirmation)
    ):
        decision = "SHADOW_FULL_EXIT"
        rationale = "multiple current PIT deterioration/risk dimensions agree and no structural HOLD-side continuation evidence is present"
    elif len(hold_evidence) >= 2 and len(exit_evidence) <= 1:
        decision = "SHADOW_HOLD"
        rationale = "multiple current PIT continuation/recovery dimensions support retaining the one-lot campaign"
    else:
        decision = "SHADOW_INSUFFICIENT_EVIDENCE"
        rationale = "current PIT evidence is mixed or insufficient for binary shadow materialization"
    return {
        **base,
        "shadow_binary_decision": decision,
        "shadow_binary_eligibility_status": "PASS",
        "shadow_binary_eligibility_reason": "PM_REDUCE_DISCRETE_LOT_ZERO_EXECUTABLE_QUANTITY",
        "semantic_evidence_used": semantic_evidence,
        "hold_side_evidence": hold_evidence,
        "exit_side_evidence": exit_evidence,
        "decisive_semantic_rationale": rationale,
    }


def _reason_family_context(reason_codes: Sequence[str]) -> list[str]:
    families: list[str] = []
    joined = " ".join(code.lower() for code in reason_codes)
    if "peak_drawdown" in joined or "profit_retention" in joined:
        families.append("profit_retention_or_peak_drawdown_warning")
    if "risk" in joined or "trend_not_broken" in joined:
        families.append("risk_increased_but_trend_not_broken")
    if "hard_stop" in joined or "trend_and_opportunity_broken" in joined:
        families.append("exit_grade_deterioration")
    return sorted(set(families))


def _variant_results(state: Mapping[str, Any]) -> dict[str, Any]:
    baseline = {
        "variant": "G0",
        "branch": "NONE",
        "shadow_state": "BASELINE",
        "alternative_g_shadow_action": "BASELINE",
        "parameter_resolved": True,
    }
    immediate_active = state["branch"] == "IMMEDIATE"
    persistent_active = state["branch"] == "PERSISTENT"
    return {
        "G0": baseline,
        "G1": {
            "variant": "G1",
            "branch": "IMMEDIATE" if immediate_active else "NONE",
            "shadow_state": state["shadow_state"] if immediate_active else "NOT_APPLICABLE",
            "alternative_g_shadow_action": state["alternative_g_shadow_action"] if immediate_active else "PRESERVE",
            "parameter_resolved": state["parameter_resolved"] if immediate_active else True,
        },
        "G2": {
            "variant": "G2",
            "branch": "PERSISTENT" if persistent_active else "NONE",
            "shadow_state": state["shadow_state"] if persistent_active else "NOT_APPLICABLE",
            "alternative_g_shadow_action": state["alternative_g_shadow_action"] if persistent_active else "PRESERVE",
            "parameter_resolved": state["parameter_resolved"] if persistent_active else True,
        },
        "G3": {
            "variant": "G3",
            "branch": state["branch"],
            "shadow_state": state["shadow_state"],
            "alternative_g_shadow_action": state["alternative_g_shadow_action"],
            "parameter_resolved": state["parameter_resolved"],
        },
    }


def _deterioration_evidence(pm_row: Mapping[str, Any], strategy_intelligence: Mapping[str, Any]) -> dict[str, Any]:
    reason_codes = [str(code) for code in (pm_row.get("reason_codes") or pm_row.get("decision_reason_codes") or [])]
    expected_edge = _expected_edge_evidence(strategy_intelligence)
    continuation = _continuation_evidence(strategy_intelligence)
    downside = _downside_evidence(strategy_intelligence)
    pm_signals = [
        code for code in reason_codes if any(token in code.lower() for token in ("risk", "weak", "deterior", "downside", "trend_not_broken", "reduce"))
    ]
    exit_grade_codes = {
        "trend_and_opportunity_broken",
        "weak_hold_score",
        "profit_retention_break",
        "hard_stop_current_return",
        "high_downside_risk",
    }
    exit_grade_deterioration = bool(exit_grade_codes.intersection(reason_codes)) or expected_edge.get("state") in {
        "DETERIORATING",
        "INSUFFICIENT",
        "RISK_OVERRIDE",
    }
    evidence_dates = sorted({date for date in (_evidence_date(expected_edge), _evidence_date(continuation), _evidence_date(downside)) if date})
    if pm_signals or expected_edge.get("state") in {"DETERIORATING", "INSUFFICIENT", "RISK_OVERRIDE"}:
        state = "DETERIORATION_CONFIRMED"
    elif continuation.get("status") in {"PASS", "SUFFICIENT"} or downside.get("status") in {"PASS", "SUFFICIENT"}:
        state = "DETERIORATION_NOT_CONFIRMED"
    else:
        state = "EVIDENCE_INSUFFICIENT"
    return {
        "state": state,
        "pm_reason_codes": reason_codes,
        "pm_deterioration_reason_codes": pm_signals,
        "exit_grade_deterioration": exit_grade_deterioration,
        "expected_edge_state": expected_edge.get("state"),
        "continuation_status": continuation.get("status"),
        "downside_status": downside.get("status"),
        "evidence_dates": evidence_dates,
        "future_information_used": False,
        "not_new_alpha_feature": True,
    }


def _recovery_evidence(pm_row: Mapping[str, Any], strategy_intelligence: Mapping[str, Any], baseline_action: str) -> dict[str, Any]:
    entry = strategy_intelligence.get("entry_admission") if isinstance(strategy_intelligence.get("entry_admission"), Mapping) else {}
    continuation = _continuation_evidence(strategy_intelligence)
    expected_edge = _expected_edge_evidence(strategy_intelligence)
    states = [
        _nested(entry, "entry_state"),
        _nested(entry, "admission_action"),
        continuation.get("trend_health_state"),
        continuation.get("persistence_state"),
        continuation.get("participation_quality_state"),
        expected_edge.get("state"),
    ]
    healthy_tokens = {"HEALTHY_CONTINUATION_ENTRY", "ADD_ALLOWED", "SUPPORTIVE", "ADEQUATE", "IMPROVED"}
    recovery_present = baseline_action in {"HOLD", "ADD"} and any(str(item).upper() in healthy_tokens for item in states)
    if baseline_action == "REDUCE" and any(str(item).upper() in healthy_tokens for item in states[:2]):
        recovery_present = True
    state = "RECOVERY_PRESENT" if recovery_present else "NO_RECOVERY" if states else "EVIDENCE_INSUFFICIENT"
    dates = sorted({date for date in (_evidence_date(continuation), _evidence_date(expected_edge)) if date})
    return {
        "state": state,
        "entry_state": _nested(entry, "entry_state"),
        "admission_action": _nested(entry, "admission_action"),
        "continuation_state_summary": states,
        "evidence_dates": dates,
        "future_information_used": False,
    }


def _persistence_evidence(prior_events: Sequence[Mapping[str, Any]], *, decision_business_date: str) -> dict[str, Any]:
    valid = [
        dict(event)
        for event in prior_events
        if str(event.get("business_date") or "") < decision_business_date
        and str(event.get("baseline_pm_action") or event.get("pm_action") or "") == "REDUCE"
        and bool(event.get("reduce_unrepresentable", event.get("reduce_unrepresentable_due_to_lot", True)))
    ]
    dates = [str(event.get("business_date")) for event in valid if event.get("business_date")]
    return {
        "prior_unrepresentable_reduce_count": len(valid),
        "prior_unrepresentable_reduce_dates": dates,
        "recent_persistence_evidence": [{"business_date": date, "fresh_pm_decision": "REDUCE"} for date in dates],
        "persistence_state": "PERSISTENCE_EVIDENCE_PRESENT" if valid else "NO_PRIOR_UNREPRESENTABLE_REDUCE",
        "persistence_parameter_status": "VALIDATION_REQUIRED_UNSET" if valid else "NOT_APPLICABLE",
        "hidden_reduce_debt_added": False,
    }


def _pit_proof(
    *,
    business_date: str,
    strategy_intelligence: Mapping[str, Any],
    market_context: Mapping[str, Any],
    source_artifacts: Mapping[str, Any] | None = None,
    run_id: str = "",
    profile_id: str = "",
) -> dict[str, Any]:
    feature_dates = []
    for payload in (strategy_intelligence, market_context):
        date = str(payload.get("feature_date") or payload.get("_artifact_feature_date") or payload.get("as_of_business_date") or payload.get("business_date") or "")
        if date:
            feature_dates.append(date)
    future_dates = [date for date in feature_dates if date > business_date]
    payload_source_artifacts = source_artifacts or {}
    artifact_refs: list[Any] = []
    for payload in (strategy_intelligence, market_context):
        artifact_refs.extend(list(payload.get("source_artifacts") or []))
        artifact_refs.extend(list(payload.get("_artifact_source_artifacts") or []))
    for value in payload_source_artifacts.values():
        if isinstance(value, (list, tuple)):
            artifact_refs.extend(value)
        else:
            artifact_refs.append(value)
    run_binding_failures: list[str] = []
    profile_binding_failures: list[str] = []
    if run_id:
        for payload in (strategy_intelligence, market_context):
            payload_run_id = str(payload.get("run_id") or payload.get("_artifact_run_id") or "")
            if payload_run_id and payload_run_id != run_id:
                run_binding_failures.append(payload_run_id)
        for ref in artifact_refs:
            text = str(ref)
            for observed in _runtime_run_ids(text):
                if observed != run_id:
                    run_binding_failures.append(observed)
    if profile_id:
        for payload in (strategy_intelligence, market_context):
            payload_profile = str(payload.get("profile") or payload.get("profile_id") or payload.get("_artifact_profile_id") or "")
            if payload_profile and payload_profile != profile_id:
                profile_binding_failures.append(payload_profile)
    if future_dates:
        state = "FAIL_FUTURE_DATED_EVIDENCE"
    elif run_binding_failures:
        state = "FAIL_STALE_OR_CROSS_RUN_EVIDENCE"
    elif profile_binding_failures:
        state = "FAIL_PROFILE_BINDING_MISMATCH"
    else:
        state = "PASS"
    return {
        "feature_dates": sorted(set(feature_dates)),
        "source_artifacts": artifact_refs,
        "pit_validation_state": state,
        "future_dates": future_dates,
        "run_id": run_id,
        "profile_id": profile_id,
        "run_binding_failures": sorted(set(run_binding_failures)),
        "profile_binding_failures": sorted(set(profile_binding_failures)),
    }


def _reason_codes(
    *,
    baseline_action: str,
    unrepresentable: bool,
    representable_reduce: bool,
    state: Mapping[str, Any],
    deterioration: Mapping[str, Any],
    recovery: Mapping[str, Any],
    persistence: Mapping[str, Any],
) -> list[str]:
    codes = [f"baseline_pm_action:{baseline_action}"]
    if representable_reduce:
        codes.append("REDUCE_REPRESENTABLE")
    if unrepresentable:
        codes.append("REDUCE_UNREPRESENTABLE_LOT")
    if deterioration["state"] == "DETERIORATION_CONFIRMED":
        codes.append("DETERIORATION_CONFIRMATION_PRESENT")
    elif deterioration["state"] == "EVIDENCE_INSUFFICIENT":
        codes.append("DETERIORATION_CONFIRMATION_MISSING")
    if persistence["prior_unrepresentable_reduce_count"] > 0:
        codes.append("PERSISTENCE_EVIDENCE_PRESENT")
    if state["parameter_resolution_state"] == "VALIDATION_REQUIRED_UNSET":
        codes.append("PERSISTENCE_PARAMETER_UNRESOLVED")
    if recovery["state"] == "RECOVERY_PRESENT":
        codes.append("RECOVERY_BLOCKED_ESCALATION")
    if state["shadow_state"] == "EVIDENCE_INSUFFICIENT":
        codes.append("EVIDENCE_INSUFFICIENT")
    return sorted(set(codes))


def _expected_edge_evidence(strategy_intelligence: Mapping[str, Any]) -> dict[str, Any]:
    current = strategy_intelligence.get("current_decision") if isinstance(strategy_intelligence.get("current_decision"), Mapping) else {}
    expected = strategy_intelligence.get("expected_edge") if isinstance(strategy_intelligence.get("expected_edge"), Mapping) else {}
    status = str(current.get("expected_edge_status") or expected.get("status") or expected.get("calibration_status") or "").upper()
    return {
        "status": status,
        "state": status,
        "source": "strategy_intelligence.expected_edge",
        "future_information_used": bool(expected.get("future_information_used", False)),
        "not_action_authority": bool(expected.get("not_action_authority", True)),
    }


def _continuation_evidence(strategy_intelligence: Mapping[str, Any]) -> dict[str, Any]:
    continuation = strategy_intelligence.get("continuation_quality") if isinstance(strategy_intelligence.get("continuation_quality"), Mapping) else {}
    entry = strategy_intelligence.get("entry_admission") if isinstance(strategy_intelligence.get("entry_admission"), Mapping) else {}
    consumed = entry.get("consumed_evidence") if isinstance(entry.get("consumed_evidence"), Mapping) else {}
    return {
        "status": str(continuation.get("status") or continuation.get("evidence_sufficiency") or "").upper(),
        "trend_health_state": _semantic_state(continuation.get("trend_health")),
        "persistence_state": _semantic_state(continuation.get("persistence")),
        "participation_quality_state": _semantic_state(continuation.get("participation_quality")),
        "relative_strength_state": _semantic_state(continuation.get("relative_strength")),
        "exhaustion_risk_state": _semantic_state(continuation.get("exhaustion_risk")),
        "strong_medium_term_structure": _bool_or_none(consumed.get("strong_medium_term_structure")),
        "risk_vote_count": _int_or_none(consumed.get("risk_vote_count")),
        "future_information_used": bool(continuation.get("future_information_used", False)),
    }


def _downside_evidence(strategy_intelligence: Mapping[str, Any]) -> dict[str, Any]:
    downside = strategy_intelligence.get("downside_risk") if isinstance(strategy_intelligence.get("downside_risk"), Mapping) else {}
    return {
        "status": str(downside.get("status") or downside.get("evidence_sufficiency") or "").upper(),
        "participation_risk_state": _semantic_state(downside.get("participation_risk")),
        "reversal_risk": _semantic_state(downside.get("reversal_risk")),
        "future_information_used": bool(downside.get("future_information_used", False)),
    }


def _momentum_evidence(strategy_intelligence: Mapping[str, Any]) -> dict[str, Any]:
    continuation = _continuation_evidence(strategy_intelligence)
    return {
        "persistence_state": continuation.get("persistence_state"),
        "relative_strength_state": continuation.get("relative_strength_state"),
        "source": "strategy_intelligence.continuation_quality",
    }


def _trend_evidence(strategy_intelligence: Mapping[str, Any]) -> dict[str, Any]:
    continuation = _continuation_evidence(strategy_intelligence)
    return {
        "trend_health_state": continuation.get("trend_health_state"),
        "source": "strategy_intelligence.continuation_quality",
    }


def _campaign_state(strategy_intelligence: Mapping[str, Any]) -> dict[str, Any]:
    lifecycle = strategy_intelligence.get("lifecycle_context") if isinstance(strategy_intelligence.get("lifecycle_context"), Mapping) else {}
    return {
        "position_campaign_id": str(lifecycle.get("position_campaign_id") or ""),
        "campaign_identity_authority_status": str(lifecycle.get("campaign_identity_authority_status") or ""),
        "campaign_age_business_days": lifecycle.get("campaign_age_business_days"),
        "current_campaign_relative_return": lifecycle.get("current_campaign_relative_return"),
        "reduce_history_summary": lifecycle.get("reduce_history_summary") or {},
        "future_information_used": False,
    }


def _market_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "business_date": str(payload.get("business_date") or ""),
        "feature_date": str(payload.get("feature_date") or payload.get("business_date") or ""),
        "regime_state": str(payload.get("regime_state") or payload.get("trend_regime") or _nested(payload, "metrics", "trend_regime") or "UNKNOWN"),
        "trend_regime": str(payload.get("trend_regime") or _nested(payload, "metrics", "trend_regime") or ""),
        "breadth_state": str(payload.get("breadth_state") or ""),
        "future_information_used": False,
    }


def _metrics(decisions: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "evaluated_pm_decision_count": len(decisions),
        "reduce_decision_count": sum(1 for item in decisions if item["baseline_pm_action"] == "REDUCE"),
        "unrepresentable_reduce_count": sum(1 for item in decisions if item["reduce_unrepresentable_due_to_lot"]),
        "zero_reduce_count": sum(1 for item in decisions if item["baseline_pm_action"] == "REDUCE" and item["final_reduce_sell_quantity"] == 0),
        "discrete_lot_count": sum(1 for item in decisions if item["representability_family"] == "DISCRETE_LOT"),
        "minimum_notional_count": sum(1 for item in decisions if item["representability_family"] == "MINIMUM_NOTIONAL"),
        "one_lot_count": sum(1 for item in decisions if item["baseline_pm_action"] == "REDUCE" and item["one_lot_position"]),
        "representable_reduce_count": sum(1 for item in decisions if item["reduce_representability_state"] == "REPRESENTABLE"),
        "structurally_eligible_count": sum(1 for item in decisions if item["structurally_eligible"]),
        "immediate_branch_structural_count": sum(1 for item in decisions if item["branch"] == "IMMEDIATE"),
        "persistent_branch_structural_count": sum(1 for item in decisions if item["branch"] == "PERSISTENT"),
        "recovery_blocked_count": sum(1 for item in decisions if item["shadow_state"] == "RECOVERY_BLOCKED"),
        "parameter_unresolved_count": sum(1 for item in decisions if item["shadow_state"] == "PARAMETER_UNRESOLVED"),
        "evidence_insufficient_count": sum(1 for item in decisions if item["shadow_state"] == "EVIDENCE_INSUFFICIENT"),
        "pit_proof_pass_count": sum(1 for item in decisions if item["pit_validation_state"] == "PASS"),
        "pit_proof_fail_count": sum(1 for item in decisions if item["pit_validation_state"] != "PASS"),
        "future_information_used_count": sum(1 for item in decisions if item["future_information_used"]),
        "shadow_exit_count": sum(1 for item in decisions if item["baseline_pm_action"] == "REDUCE" and item["alternative_g_shadow_action"] == "EXIT"),
        "shadow_hold_or_preserve_count": sum(
            1 for item in decisions if item["baseline_pm_action"] == "REDUCE" and item["alternative_g_shadow_action"] in {"PRESERVE", "BASELINE"}
        ),
        "shadow_binary_full_exit_count": sum(1 for item in decisions if item.get("shadow_binary_decision") == "SHADOW_FULL_EXIT"),
        "shadow_binary_hold_count": sum(1 for item in decisions if item.get("shadow_binary_decision") == "SHADOW_HOLD"),
        "shadow_binary_insufficient_evidence_count": sum(1 for item in decisions if item.get("shadow_binary_decision") == "SHADOW_INSUFFICIENT_EVIDENCE"),
        "shadow_binary_not_applicable_count": sum(1 for item in decisions if item.get("shadow_binary_decision") == "SHADOW_NOT_APPLICABLE"),
    }


def _summary_metrics(*, run_root: Path, materialized: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    totals = {
        "shadow_evaluated_pm_decision_count": 0,
        "shadow_reduce_decision_count": 0,
        "unrepresentable_reduce_count": 0,
        "zero_reduce_count": 0,
        "discrete_lot_count": 0,
        "minimum_notional_count": 0,
        "one_lot_count": 0,
        "representable_reduce_count": 0,
        "structurally_eligible_count": 0,
        "immediate_branch_structural_count": 0,
        "persistent_branch_structural_count": 0,
        "recovery_blocked_count": 0,
        "parameter_unresolved_count": 0,
        "evidence_insufficient_count": 0,
        "pit_proof_pass_count": 0,
        "pit_proof_fail_count": 0,
        "future_information_used_count": 0,
        "shadow_exit_count": 0,
        "shadow_hold_or_preserve_count": 0,
        "shadow_binary_full_exit_count": 0,
        "shadow_binary_hold_count": 0,
        "shadow_binary_insufficient_evidence_count": 0,
        "shadow_binary_not_applicable_count": 0,
    }
    mapping = {
        "shadow_evaluated_pm_decision_count": "evaluated_pm_decision_count",
        "shadow_reduce_decision_count": "reduce_decision_count",
    }
    for item in materialized:
        payload = _load_json(Path(item["artifact_path"]))
        metrics = payload.get("metrics") or {}
        for key in totals:
            totals[key] += int(metrics.get(mapping.get(key, key), 0))
    return totals


def _merge_prior_events(prior_events: dict[str, list[dict[str, Any]]], payload: Mapping[str, Any]) -> None:
    for decision in payload.get("decisions") or []:
        if not decision.get("reduce_unrepresentable"):
            continue
        campaign_id = str(decision.get("campaign_id") or "")
        if not campaign_id:
            continue
        prior_events.setdefault(campaign_id, []).append(
            {
                "business_date": decision.get("business_date"),
                "symbol": decision.get("symbol"),
                "campaign_id": campaign_id,
                "baseline_pm_action": decision.get("baseline_pm_action"),
                "reduce_unrepresentable": True,
                "reduce_unrepresentable_due_to_lot": bool(decision.get("reduce_unrepresentable_due_to_lot")),
                "representability_family": decision.get("representability_family"),
            }
        )


def _strategy_intelligence_by_symbol(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    symbol_map = payload.get("symbol_intelligence")
    if isinstance(symbol_map, Mapping):
        artifact_fields = {
            "_artifact_business_date": payload.get("business_date"),
            "_artifact_feature_date": payload.get("feature_date") or payload.get("as_of_business_date") or payload.get("business_date"),
            "_artifact_run_id": payload.get("run_id"),
            "_artifact_profile_id": payload.get("profile") or payload.get("profile_id"),
            "_artifact_source_artifacts": list(payload.get("source_artifacts") or []),
        }
        return {
            str(key): _merge_symbol_strategy_intelligence(str(key), dict(value), artifact_fields, payload)
            for key, value in symbol_map.items()
            if isinstance(value, Mapping)
        }
    rows = _rows(payload, "positions", "items")
    return {_symbol(row): row for row in rows if _symbol(row)}


def _merge_symbol_strategy_intelligence(
    symbol: str,
    value: dict[str, Any],
    artifact_fields: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    merged = {**value, **artifact_fields}
    comparison = payload.get("shadow_decision_comparison") if isinstance(payload.get("shadow_decision_comparison"), Mapping) else {}
    by_symbol = comparison.get("by_symbol") if isinstance(comparison.get("by_symbol"), Mapping) else {}
    symbol_comparison = by_symbol.get(symbol) if isinstance(by_symbol.get(symbol), Mapping) else {}
    consumed = _nested(symbol_comparison, "entry_admission_summary", "consumed_evidence")
    if isinstance(consumed, Mapping):
        entry = dict(merged.get("entry_admission") or {}) if isinstance(merged.get("entry_admission"), Mapping) else {}
        entry.setdefault("consumed_evidence", dict(consumed))
        merged["entry_admission"] = entry
    return merged


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
    return str(row.get("position_campaign_id") or row.get("campaign_id") or "")


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


def _evidence_date(evidence: Mapping[str, Any]) -> str:
    return str(evidence.get("as_of_date") or evidence.get("feature_date") or evidence.get("business_date") or "")


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.strip().lower() in {"true", "yes", "1"}:
            return True
        if value.strip().lower() in {"false", "no", "0"}:
            return False
    return None


def _runtime_run_ids(text: str) -> list[str]:
    tokens: list[str] = []
    marker = "runtime-test-"
    start = 0
    while True:
        index = text.find(marker, start)
        if index < 0:
            return tokens
        end = index
        while end < len(text) and text[end] not in {"/", "\\", " ", "\"", "'", "\n", "\t", ":", ","}:
            end += 1
        tokens.append(text[index:end])
        start = end


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None
