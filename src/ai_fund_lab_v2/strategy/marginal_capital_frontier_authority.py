from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_fund_lab_v2.strategy.common_marginal_capital_frontier_shadow import (
    build_canonical_marginal_capital_frontier_payload,
    stable_payload_hash as stable_shadow_payload_hash,
)


SCHEMA_NAME = "canonical_marginal_capital_frontier_authority"
SCHEMA_VERSION = "canonical_marginal_capital_frontier_authority.v1"
PRODUCER = "strategy.marginal_capital_frontier_authority"
OWNER = "PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY"
ARTIFACT_MODE = "PRODUCTION_SHAPED_CONSUMER_DISABLED"
PRODUCTION_CONSUMER_SWITCH_ARTIFACT_MODE = "PRODUCTION_PC_TO_PS_CONSUMER_ENABLED"
COMPARISON_REPRESENTATION = "BOUNDED_CARDINAL_VALUE_CONTRACT"
PRODUCTION_CONSUMER_ENABLED = False
PRODUCTION_CONSUMER_COUNT = 0
PRODUCTION_SWITCH_CONSUMER_COUNT = 1
VALUE_TIE_TOLERANCE = 1e-9
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


def build_marginal_capital_frontier_authority_payload(
    *,
    business_date: str,
    portfolio_construction_payload: Mapping[str, Any],
    position_sizing_payload: Mapping[str, Any] | None = None,
    safety_payload: Mapping[str, Any] | None = None,
    risk_pacing_payload: Mapping[str, Any] | None = None,
    cash_payload: Mapping[str, Any] | None = None,
    source_artifacts: Mapping[str, Any] | None = None,
    source_hashes: Mapping[str, Any] | None = None,
    session: str = "morning",
    run_id: str = "",
    max_add_lots_per_position: int = 3,
) -> dict[str, Any]:
    shadow_payload = build_canonical_marginal_capital_frontier_payload(
        business_date=business_date,
        portfolio_construction_payload=portfolio_construction_payload,
        position_sizing_payload=position_sizing_payload,
        safety_payload=safety_payload,
        risk_pacing_payload=risk_pacing_payload,
        cash_payload=cash_payload,
        source_artifacts=source_artifacts,
        source_hashes=source_hashes,
        session=session,
        run_id=run_id,
        max_add_lots_per_position=max_add_lots_per_position,
    )
    return build_marginal_capital_frontier_authority_payload_from_shadow(
        shadow_payload=shadow_payload,
        portfolio_construction_payload=portfolio_construction_payload,
        source_artifacts=source_artifacts,
        source_hashes=source_hashes,
    )


def build_marginal_capital_frontier_authority_payload_from_shadow(
    *,
    shadow_payload: Mapping[str, Any],
    portfolio_construction_payload: Mapping[str, Any] | None = None,
    source_artifacts: Mapping[str, Any] | None = None,
    source_hashes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    shadow_candidates = _rows(shadow_payload, "frontier_candidates")
    candidates = [_authority_candidate(row) for row in shadow_candidates]
    ordered = sorted(candidates, key=_authority_sort_key)
    cash = next((row for row in ordered if row.get("semantic_type") == "CASH_OPTIONALITY"), None)
    allocation_budget = _allocation_budget_authority(
        shadow_payload=shadow_payload,
        portfolio_construction_payload=portfolio_construction_payload or {},
        candidates=ordered,
        cash_candidate=cash,
    )
    review_reasons = _payload_review_reasons(shadow_payload, ordered)
    if allocation_budget["status"] != "PASS":
        review_reasons.extend(allocation_budget["reason_codes"])
    ambiguous = _ambiguous_top_value(ordered)
    if ambiguous:
        review_reasons.append("ambiguous_cross_type_cardinal_value")

    accepted_targets: list[dict[str, Any]] = []
    frontier_sequence: list[dict[str, Any]] = []
    if not review_reasons and cash and _available(cash) and _is_cash_winner(cash, ordered):
        cash["authority_disposition"] = "CASH_OPTIONALITY_ACCEPTED"
    elif not review_reasons:
        allocation_result = _budget_bounded_acceptance(
            ordered,
            allocation_budget=allocation_budget,
            cash_candidate=cash,
        )
        accepted_targets = allocation_result["accepted_targets"]
        frontier_sequence = allocation_result["frontier_acceptance_sequence"]

    accepted_ids = {candidate_id for target in accepted_targets for candidate_id in target.get("accepted_frontier_candidate_ids", [])}
    for row in ordered:
        if row.get("candidate_id") in accepted_ids:
            row["authority_disposition"] = "ACCEPTED_INCREMENTAL_TARGET"
        elif row.get("authority_disposition") == "PENDING_AUTHORITY_COMPARISON":
            row["authority_disposition"] = _nonaccepted_disposition(row, cash=cash, review_reasons=review_reasons)
    _attach_alternatives(ordered)

    payload = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "artifact_mode": ARTIFACT_MODE,
        "owner": OWNER,
        "producer": PRODUCER,
        "business_date": str(shadow_payload.get("business_date") or ""),
        "session": str(shadow_payload.get("session") or ""),
        "run_id": str(shadow_payload.get("run_id") or ""),
        "comparison_representation": COMPARISON_REPRESENTATION,
        "cardinal_value_contract": {
            "status": "ACTIVE_CONSUMER_DISABLED",
            "value_min": 0.0,
            "value_max": 1.0,
            "higher_is_better": True,
            "tie_tolerance": VALUE_TIE_TOLERANCE,
            "semantic_type_multiplier_used": False,
            "fixed_share_size_rule_used": False,
            "fixed_add_multiplier_used": False,
            "fixed_position_count_rule_used": False,
            "historical_outcome_parameter_selection_used": False,
        },
        "pit_status": "PIT_CURRENT_DECISION_TIME_EVIDENCE_ONLY",
        "future_information_used": False,
        "historical_outcome_used": False,
        "paper_ledger_input_used": False,
        "selected_or_bought_outcome_used": False,
        "production_consumer_enabled": PRODUCTION_CONSUMER_ENABLED,
        "production_consumers": [],
        "production_consumer_count": PRODUCTION_CONSUMER_COUNT,
        "feeds_position_sizing": False,
        "feeds_runtime_planning": False,
        "feeds_pending": False,
        "feeds_orders": False,
        "feeds_execution": False,
        "feeds_safety_authority": False,
        "production_target_weight_changed": False,
        "production_behavior_changed": False,
        "shadow_frontier_schema_version": shadow_payload.get("schema_version"),
        "shadow_frontier_artifact_hash": shadow_payload.get("artifact_hash") or stable_shadow_payload_hash(shadow_payload),
        "shadow_frontier_remains_non_authoritative": True,
        "cash_source_status": shadow_payload.get("cash_source_status", "UNKNOWN"),
        "cash_source_lineage": _strip_forbidden_list(shadow_payload.get("cash_source_lineage") or []),
        "max_add_lots_per_position": int(shadow_payload.get("max_add_lots_per_position") or 0),
        "add_lot_generation_limit_type": shadow_payload.get("add_lot_generation_limit_type"),
        "frontier_candidates": ordered,
        "accepted_incremental_targets": accepted_targets,
        "allocation_budget_authority": allocation_budget,
        "frontier_acceptance_sequence": frontier_sequence,
        "authorized_cash_allocation": _authorized_cash_allocation(allocation_budget, accepted_targets, cash, review_reasons),
        "capital_conservation": _capital_conservation(allocation_budget, accepted_targets, review_reasons),
        "budget_stop_reasons": _budget_stop_reasons(frontier_sequence, allocation_budget, review_reasons),
        "target_gap_authority": _target_gap_authority(accepted_targets, review_reasons),
        "cash_disposition": _cash_disposition(cash, accepted_targets, review_reasons),
        "guardrails": _guardrails(ordered),
        "review_reasons": sorted(set(review_reasons)),
        "authority_result": _authority_result(ordered, accepted_targets, review_reasons),
        "ps_compatibility": {
            "emits_target_weight": True,
            "emits_current_weight": True,
            "emits_accepted_incremental_weight": True,
            "emits_target_gap": True,
            "emits_accepted_candidate_lineage": True,
            "emits_pc_to_ps_final_net_targets": True,
            "production_consumer_enabled": False,
        },
        "source_artifacts": _strip_forbidden_mapping(source_artifacts or {}),
        "source_hashes": _strip_forbidden_mapping(source_hashes or {}),
        "determinism_key": _determinism_key(ordered, shadow_payload),
    }
    boundary = build_pc_to_ps_switch_boundary_validation(payload)
    payload["pc_to_ps_consumer_switch_boundary"] = boundary
    payload["ps_compatibility"]["pc_to_ps_switch_boundary_status"] = boundary["status"]
    payload["ps_compatibility"]["aggregated_ps_target_count"] = boundary["aggregated_ps_target_count"]
    payload["artifact_hash"] = stable_authority_payload_hash(payload)
    return payload


def write_marginal_capital_frontier_authority_artifact(payload: Mapping[str, Any], output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def stable_authority_payload_hash(payload: Mapping[str, Any]) -> str:
    canonical = {key: value for key, value in dict(payload).items() if key != "artifact_hash"}
    return _stable_hash(canonical)


def assert_production_consumer_disabled(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("artifact_mode") == ARTIFACT_MODE
        and payload.get("production_consumer_enabled") is False
        and int(payload.get("production_consumer_count") or 0) == 0
        and payload.get("feeds_position_sizing") is False
        and payload.get("feeds_runtime_planning") is False
        and payload.get("feeds_pending") is False
        and payload.get("feeds_orders") is False
        and payload.get("feeds_execution") is False
        and payload.get("feeds_safety_authority") is False
        and payload.get("production_behavior_changed") is False
    )


def activate_pc_to_ps_production_consumer_switch(authority_payload: Mapping[str, Any]) -> dict[str, Any]:
    payload = _strip_forbidden_mapping(authority_payload)
    boundary = payload.get("pc_to_ps_consumer_switch_boundary") if isinstance(payload.get("pc_to_ps_consumer_switch_boundary"), Mapping) else {}
    review_reasons: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        review_reasons.append("missing_or_invalid_marginal_capital_authority")
    if (payload.get("authority_result") or {}).get("status") != "PASS":
        review_reasons.append("marginal_capital_authority_result_not_pass")
    if (payload.get("capital_conservation") or {}).get("status") != "PASS":
        review_reasons.append("marginal_capital_authority_capital_conservation_not_pass")
    if boundary.get("status") != "PASS":
        review_reasons.append("bf_pc_to_ps_boundary_not_pass")
    if boundary.get("legacy_zero_fallback_allowed") is not False or boundary.get("legacy_target_gap_fallback_allowed") is not False:
        review_reasons.append("legacy_fallback_not_forbidden")
    if payload.get("shadow_frontier_remains_non_authoritative") is not True:
        review_reasons.append("shadow_frontier_authority_boundary_invalid")
    if int(payload.get("production_consumer_count") or 0) != 0:
        review_reasons.append("authority_already_consumed_before_explicit_switch")

    status = "REVIEW_REQUIRED" if review_reasons else "PASS"
    activated_boundary = dict(boundary)
    activated_targets = [dict(row) for row in activated_boundary.get("aggregated_ps_targets") or [] if isinstance(row, Mapping)]
    if status != "PASS":
        activated_targets = []
    activated_boundary.update(
        {
            "status": status,
            "target_aggregation_status": status,
            "production_consumer_enabled": status == "PASS",
            "production_consumer_count": PRODUCTION_SWITCH_CONSUMER_COUNT if status == "PASS" else 0,
            "production_consumers": ["strategy.position_sizing"] if status == "PASS" else [],
            "feeds_position_sizing": status == "PASS",
            "feeds_runtime_planning": False,
            "feeds_pending": False,
            "aggregated_ps_targets": activated_targets,
            "review_reasons": sorted(set(review_reasons or activated_boundary.get("review_reasons") or [])),
        }
    )
    for row in activated_targets:
        row["production_consumer_enabled"] = True
        row["feeds_position_sizing"] = True
        row["target_authority_source"] = "BF_AGGREGATED_PS_BOUNDARY_ONLY"
        row["legacy_target_gap_fallback_allowed"] = False
        row["legacy_zero_fallback_allowed"] = False

    switch = {
        "schema_name": "pc_to_ps_production_consumer_switch",
        "schema_version": "pc_to_ps_production_consumer_switch.v1",
        "owner": "PORTFOLIO_CONSTRUCTION",
        "consumer": "POSITION_SIZING",
        "status": status,
        "target_authority_source": "BF_AGGREGATED_PS_BOUNDARY_ONLY",
        "bf_only_target_authority": status == "PASS",
        "legacy_target_gap_fallback_allowed": False,
        "legacy_zero_fallback_allowed": False,
        "fallback_policy": "FAIL_CLOSED_REVIEW_REQUIRED_NO_LEGACY_ZERO_FALLBACK",
        "production_consumer_enabled": status == "PASS",
        "production_consumer_count": PRODUCTION_SWITCH_CONSUMER_COUNT if status == "PASS" else 0,
        "shadow_frontier_production_consumer_count": 0,
        "ps_quantity_logic_changed": False,
        "runtime_logic_changed": False,
        "pm_reduce_exit_safety_changed": False,
        "production_behavior_changed": status == "PASS",
        "aggregated_ps_target_count": len(activated_targets),
        "review_reasons": sorted(set(review_reasons)),
        "pit_status": "PIT_CURRENT_DECISION_TIME_EVIDENCE_ONLY",
        "future_information_used": False,
        "historical_outcome_used": False,
    }
    payload.update(
        {
            "artifact_mode": PRODUCTION_CONSUMER_SWITCH_ARTIFACT_MODE if status == "PASS" else ARTIFACT_MODE,
            "production_consumer_enabled": status == "PASS",
            "production_consumers": ["strategy.position_sizing"] if status == "PASS" else [],
            "production_consumer_count": PRODUCTION_SWITCH_CONSUMER_COUNT if status == "PASS" else 0,
            "feeds_position_sizing": status == "PASS",
            "feeds_runtime_planning": False,
            "feeds_pending": False,
            "feeds_orders": False,
            "feeds_execution": False,
            "feeds_safety_authority": False,
            "production_target_weight_changed": status == "PASS",
            "production_behavior_changed": status == "PASS",
            "pc_to_ps_consumer_switch_boundary": activated_boundary,
            "production_consumer_switch": switch,
            "review_reasons": sorted(set([*list(payload.get("review_reasons") or []), *review_reasons])),
        }
    )
    payload["artifact_hash"] = stable_authority_payload_hash(payload)
    return payload


def build_pc_to_ps_switch_boundary_validation(authority_payload: Mapping[str, Any]) -> dict[str, Any]:
    review_reasons: list[str] = []
    if authority_payload.get("schema_version") != SCHEMA_VERSION:
        review_reasons.append("missing_or_invalid_authority_payload")
    if authority_payload.get("production_consumer_enabled") is not False or int(authority_payload.get("production_consumer_count") or 0) != 0:
        review_reasons.append("production_consumer_not_disabled")
    if (authority_payload.get("authority_result") or {}).get("status") != "PASS":
        review_reasons.append("authority_result_not_pass")
    if (authority_payload.get("capital_conservation") or {}).get("status") != "PASS":
        review_reasons.append("capital_conservation_not_pass")

    targets = _rows(authority_payload, "accepted_incremental_targets")
    candidates_by_id = {
        str(candidate.get("candidate_id") or ""): candidate
        for candidate in _rows(authority_payload, "frontier_candidates")
        if candidate.get("candidate_id")
    }
    aggregated: list[dict[str, Any]] = []
    seen_identity: set[tuple[str, str, str, int]] = set()
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for target in targets:
        symbol = str(target.get("symbol") or "")
        semantic_type = str(target.get("semantic_type") or "")
        campaign_id = str(target.get("position_campaign_id") or "")
        increment_index = int(target.get("increment_index") or 0)
        identity = (symbol, semantic_type, campaign_id, increment_index)
        if not symbol or semantic_type not in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT", "ADD_NEXT_LOT"}:
            review_reasons.append("invalid_accepted_target_identity")
            continue
        if identity in seen_identity:
            review_reasons.append("duplicate_accepted_target_identity")
        seen_identity.add(identity)
        if semantic_type == "ADD_NEXT_LOT" and not campaign_id:
            review_reasons.append("missing_add_position_campaign_id")
        for candidate_id in target.get("accepted_frontier_candidate_ids") or []:
            candidate = candidates_by_id.get(str(candidate_id))
            if not candidate:
                review_reasons.append("accepted_source_candidate_missing")
                continue
            candidate_validation = _security_comparison_validation(candidate)
            if candidate_validation["status"] != "PASS":
                review_reasons.extend(str(reason) for reason in candidate_validation["reason_codes"])
        groups.setdefault((symbol, semantic_type, campaign_id), []).append(target)

    for (symbol, semantic_type, campaign_id), rows in sorted(groups.items()):
        ordered = sorted(rows, key=lambda row: int(row.get("increment_index") or 0))
        if semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT", "ADD_NEXT_LOT"}:
            expected = list(range(1, len(ordered) + 1))
            actual = [int(row.get("increment_index") or 0) for row in ordered]
            if actual != expected:
                review_reasons.append("non_contiguous_add_lot_sequence" if semantic_type == "ADD_NEXT_LOT" else f"non_contiguous_{semantic_type.lower()}_sequence")
                continue
            previous_target_quantity: int | None = None
            for target_row in ordered:
                pre_quantity = int(target_row.get("pre_quantity") or 0)
                increment_quantity = int(target_row.get("accepted_incremental_quantity") or 0)
                target_quantity = int(target_row.get("target_quantity") or 0)
                if target_quantity != pre_quantity + increment_quantity:
                    review_reasons.append("add_lot_target_quantity_inconsistent" if semantic_type == "ADD_NEXT_LOT" else f"{semantic_type.lower()}_target_quantity_inconsistent")
                    break
                if previous_target_quantity is not None and pre_quantity != previous_target_quantity:
                    review_reasons.append("add_repeated_lot_quantity_progression_inconsistent" if semantic_type == "ADD_NEXT_LOT" else f"{semantic_type.lower()}_lot_quantity_progression_inconsistent")
                    break
                previous_target_quantity = target_quantity
            if semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"} and ordered:
                if int(ordered[0].get("pre_quantity") or 0) != 0:
                    review_reasons.append("entry_lot_initial_pre_quantity_not_zero")
                pc_target = _entry_pc_target_magnitude(ordered)
                if pc_target.get("status") != "PASS":
                    review_reasons.extend(str(reason) for reason in pc_target.get("reason_codes") or ["entry_pc_target_magnitude_review_required"])
                else:
                    max_quantity = int(pc_target.get("pc_target_executable_quantity") or 0)
                    final_quantity = int(ordered[-1].get("target_quantity") or 0)
                    if max_quantity > 0 and final_quantity > max_quantity:
                        review_reasons.append("entry_target_quantity_exceeds_pc_target_magnitude")
        row = _aggregated_ps_target(symbol=symbol, semantic_type=semantic_type, campaign_id=campaign_id, targets=ordered)
        if row.get("final_target_quantity") != int(row.get("current_quantity") or 0) + int(row.get("final_quantity_delta") or 0):
            review_reasons.append("ps_final_quantity_delta_inconsistent")
        aggregated.append(row)

    status = "REVIEW_REQUIRED" if review_reasons else "PASS"
    if status != "PASS":
        aggregated = []
    security_weight = round(sum(float(row.get("accepted_incremental_weight") or 0.0) for row in aggregated), 10)
    security_notional = round(sum(float(row.get("accepted_incremental_notional") or 0.0) for row in aggregated), 6)
    conservation = authority_payload.get("capital_conservation") if isinstance(authority_payload.get("capital_conservation"), Mapping) else {}
    residual_weight = round(
        abs(security_weight - (_number(conservation.get("security_allocation_weight"), 0.0) or 0.0)),
        10,
    )
    residual_notional = round(
        abs(security_notional - (_number(conservation.get("security_allocation_notional"), 0.0) or 0.0)),
        6,
    )
    if status == "PASS" and (residual_weight > 1e-8 or residual_notional > 1e-4):
        status = "REVIEW_REQUIRED"
        review_reasons.append("aggregated_security_allocation_conservation_mismatch")
        aggregated = []

    boundary = {
        "schema_name": "pc_to_ps_consumer_switch_boundary_validator",
        "schema_version": "pc_to_ps_consumer_switch_boundary_validator.v1",
        "owner": "PORTFOLIO_CONSTRUCTION",
        "status": status,
        "artifact_mode": ARTIFACT_MODE,
        "production_consumer_enabled": False,
        "production_consumer_count": 0,
        "feeds_position_sizing": False,
        "feeds_runtime_planning": False,
        "feeds_pending": False,
        "legacy_target_gap_input_used": False,
        "legacy_target_gap_fallback_allowed": False,
        "legacy_zero_fallback_allowed": False,
        "fallback_policy": "FAIL_CLOSED_REVIEW_REQUIRED_NO_LEGACY_ZERO_FALLBACK",
        "target_aggregation_status": status,
        "accepted_incremental_target_count": len(targets) if status == "PASS" else 0,
        "aggregated_ps_target_count": len(aggregated),
        "aggregated_ps_targets": aggregated,
        "multi_lot_net_quantity_target_count": sum(1 for row in aggregated if row.get("accepted_lot_count", 0) > 1),
        "capital_conservation": {
            "status": "PASS" if status == "PASS" else "REVIEW_REQUIRED",
            "security_allocation_weight": security_weight if status == "PASS" else 0.0,
            "security_allocation_notional": security_notional if status == "PASS" else 0.0,
            "source_security_allocation_weight": conservation.get("security_allocation_weight"),
            "source_security_allocation_notional": conservation.get("security_allocation_notional"),
            "residual_weight": residual_weight if status == "PASS" else 0.0,
            "residual_notional": residual_notional if status == "PASS" else 0.0,
        },
        "lineage_status": "PASS" if status == "PASS" else "REVIEW_REQUIRED",
        "review_reasons": sorted(set(review_reasons)),
        "determinism_key": _stable_hash(
            {
                "schema_version": "pc_to_ps_consumer_switch_boundary_validator.v1",
                "business_date": authority_payload.get("business_date"),
                "session": authority_payload.get("session"),
                "targets": aggregated,
            }
        ),
        "pit_status": "PIT_CURRENT_DECISION_TIME_EVIDENCE_ONLY",
        "future_information_used": False,
        "historical_outcome_used": False,
    }
    boundary["boundary_hash"] = _stable_hash(boundary)
    return boundary


def _aggregated_ps_target(
    *,
    symbol: str,
    semantic_type: str,
    campaign_id: str,
    targets: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    first = targets[0]
    last = targets[-1]
    incremental_weight = round(sum(float(target.get("accepted_incremental_weight") or 0.0) for target in targets), 10)
    incremental_notional = round(sum(float(target.get("accepted_incremental_notional") or 0.0) for target in targets), 6)
    quantity_delta = sum(int(target.get("accepted_incremental_quantity") or 0) for target in targets)
    current_quantity = int(first.get("pre_quantity") or 0)
    current_weight = _number(first.get("current_weight"), 0.0) or 0.0
    source_pm_decision_ids = sorted({str(target.get("source_pm_decision_id") or "") for target in targets if target.get("source_pm_decision_id")})
    source_candidate_ids = sorted({str(target.get("source_candidate_id") or "") for target in targets if target.get("source_candidate_id")})
    source_pc_evidence_ids = sorted(
        {
            str(source_id)
            for target in targets
            for source_id in (target.get("source_pc_evidence_ids") or [])
            if source_id
        }
    )
    accepted_candidate_ids = [
        str(candidate_id)
        for target in targets
        for candidate_id in (target.get("accepted_frontier_candidate_ids") or [])
        if candidate_id
    ]
    return {
        "symbol": symbol,
        "semantic_type": semantic_type,
        "position_campaign_id": campaign_id,
        "current_quantity": current_quantity,
        "final_target_quantity": int(last.get("target_quantity") or current_quantity + quantity_delta),
        "final_quantity_delta": quantity_delta,
        "current_weight": round(current_weight, 10),
        "final_target_weight": round(_number(last.get("target_weight"), current_weight + incremental_weight) or 0.0, 10),
        "accepted_incremental_weight": incremental_weight,
        "target_gap": incremental_weight,
        "target_minus_current": incremental_weight,
        "accepted_incremental_notional": incremental_notional,
        "accepted_lot_count": len(targets),
        "accepted_increment_indexes": [int(target.get("increment_index") or 0) for target in targets],
        "accepted_frontier_candidate_ids": accepted_candidate_ids,
        "source_pm_decision_ids": source_pm_decision_ids,
        "source_candidate_ids": source_candidate_ids,
        "source_pc_evidence_ids": source_pc_evidence_ids,
        "campaign_lineage_status": "PASS" if semantic_type != "ADD_NEXT_LOT" or campaign_id else "REVIEW_REQUIRED",
        "runtime_pending_lineage_status": "PASS" if accepted_candidate_ids and source_candidate_ids else "REVIEW_REQUIRED",
        "ps_compatible": True,
        "production_consumer_enabled": False,
        "feeds_position_sizing": False,
        "legacy_target_gap_input_used": False,
        "legacy_target_gap_fallback_allowed": False,
        "legacy_zero_fallback_allowed": False,
        "fallback_policy": "FAIL_CLOSED_REVIEW_REQUIRED_NO_LEGACY_ZERO_FALLBACK",
        "target_weight_reason_codes": sorted({str(reason) for target in targets for reason in (target.get("target_weight_reason_codes") or [])}),
        "capital_value_authority": {
            "schema_version": SCHEMA_VERSION,
            "owner": OWNER,
            "production_consumer_enabled": False,
            "candidate_ids": accepted_candidate_ids,
        },
        "pc_target_magnitude_authority": dict(first.get("pc_target_magnitude_authority") or {}) if isinstance(first.get("pc_target_magnitude_authority"), Mapping) else {},
    }


def _entry_pc_target_magnitude(targets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    authorities = [
        target.get("pc_target_magnitude_authority")
        for target in targets
        if isinstance(target.get("pc_target_magnitude_authority"), Mapping)
    ]
    if not authorities:
        return {
            "status": "REVIEW_REQUIRED",
            "reason_codes": ["missing_entry_pc_target_magnitude_authority"],
        }
    quantities = {
        int(authority.get("pc_target_executable_quantity") or 0)
        for authority in authorities
        if int(authority.get("pc_target_executable_quantity") or 0) > 0
    }
    statuses = {str(authority.get("status") or "").upper() for authority in authorities}
    if statuses != {"PASS"}:
        return {
            "status": "REVIEW_REQUIRED",
            "reason_codes": sorted(
                {
                    str(reason)
                    for authority in authorities
                    for reason in authority.get("reason_codes") or ["entry_pc_target_magnitude_review_required"]
                }
            ),
        }
    if len(quantities) != 1:
        return {
            "status": "REVIEW_REQUIRED",
            "reason_codes": ["conflicting_entry_pc_target_magnitude_authority"],
        }
    return {
        "status": "PASS",
        "pc_target_executable_quantity": next(iter(quantities)),
        "reason_codes": ["entry_pc_target_magnitude_hard_upper_bound_verified"],
    }


def _authority_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    copied = _strip_forbidden_mapping(row)
    value = _bounded_value(row)
    add_admission = _add_admission_authority(row)
    comparison_validation = _security_comparison_validation(row)
    authority_disposition = "PENDING_AUTHORITY_COMPARISON"
    if row.get("shadow_disposition") == "INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED":
        authority_disposition = "INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED"
    elif add_admission["status"] == "BLOCK":
        authority_disposition = "INELIGIBLE_ADD_ADMISSION_BLOCKED"
    elif add_admission["status"] == "REVIEW_REQUIRED":
        authority_disposition = "REVIEW_REQUIRED"
    elif comparison_validation["status"] == "BLOCK":
        authority_disposition = "INELIGIBLE_MARGINAL_CAPITAL_VALUE_BLOCKED"
    elif comparison_validation["status"] == "REVIEW_REQUIRED":
        authority_disposition = "REVIEW_REQUIRED"
    copied.update(
        {
            "authority_schema_version": SCHEMA_VERSION,
            "comparison_representation": COMPARISON_REPRESENTATION,
            "capital_value": value["capital_value"],
            "capital_value_status": value["status"],
            "capital_value_components": value["components"],
            "capital_value_reason_codes": value["reason_codes"],
            "add_admission_authority": add_admission,
            "authority_disposition": authority_disposition,
            "production_authority": True,
            "production_consumer_enabled": False,
            "portfolio_state_mutated": False,
            "ps_compatible_target_fields_available": row.get("semantic_type") != "CASH_OPTIONALITY",
        }
    )
    return copied


def _bounded_value(row: Mapping[str, Any]) -> dict[str, Any]:
    if not _available(row):
        return {
            "status": "NOT_COMPARABLE",
            "capital_value": None,
            "components": {},
            "reason_codes": ["candidate_not_available_for_authority_comparison"],
        }
    add_admission = _add_admission_authority(row)
    if add_admission["status"] != "PASS":
        return {
            "status": "NOT_COMPARABLE",
            "capital_value": None,
            "components": {},
            "reason_codes": list(add_admission["reason_codes"]),
        }
    comparison_validation = _security_comparison_validation(row)
    if comparison_validation["status"] != "PASS":
        return {
            "status": "NOT_COMPARABLE",
            "capital_value": None,
            "components": {},
            "reason_codes": list(comparison_validation["reason_codes"]),
        }
    if row.get("semantic_type") == "CASH_OPTIONALITY":
        preferred = str(row.get("comparison_class") or "").upper() == "CASH_PREFERRED"
        return {
            "status": "PASS",
            "capital_value": 1.0 if preferred else 0.05,
            "components": {
                "opportunity": 1.0 if preferred else 0.05,
                "rank": 1.0 if preferred else 0.05,
                "quality": 1.0 if preferred else 0.05,
                "requalification": 1.0,
                "headroom": 1.0,
            },
            "reason_codes": ["cash_preferred"] if preferred else ["cash_first_class_optionality"],
        }

    desirability = row.get("desirability") if isinstance(row.get("desirability"), Mapping) else {}
    components = desirability.get("components") if isinstance(desirability.get("components"), Mapping) else {}
    risk = row.get("risk_modifiers") if isinstance(row.get("risk_modifiers"), Mapping) else {}
    opportunity = _clamp01(_number(components.get("opportunity"), 0.0) or 0.0)
    quality = _clamp01(_number(components.get("quality"), opportunity) or opportunity)
    rank = _rank_component(_number(components.get("rank")))
    requalification = _requalification_component(row, components)
    single_cap = _number(risk.get("single_name_cap"), 0.0) or 0.0
    headroom = _number(risk.get("headroom_after"), 0.0) or 0.0
    headroom_component = _clamp01(headroom / single_cap) if single_cap > 0 else 0.0
    value = (0.30 * opportunity) + (0.25 * quality) + (0.20 * rank) + (0.15 * requalification) + (0.10 * headroom_component)
    return {
        "status": "PASS",
        "capital_value": round(_clamp01(value), 10),
        "components": {
            "opportunity": round(opportunity, 10),
            "quality": round(quality, 10),
            "rank": round(rank, 10),
            "requalification": round(requalification, 10),
            "headroom": round(headroom_component, 10),
        },
        "reason_codes": ["bounded_decision_time_evidence_value"],
    }


def _add_admission_authority(row: Mapping[str, Any]) -> dict[str, Any]:
    if row.get("semantic_type") != "ADD_NEXT_LOT":
        return {
            "schema_version": "phase32_bz_add_admission_authority.v1",
            "status": "PASS",
            "authority": "NOT_ADD_NEXT_LOT",
            "final_add_eligibility": "NOT_APPLICABLE",
            "reason_codes": ["add_admission_not_applicable"],
            "future_information_used": False,
            "historical_outcome_used": False,
        }
    evidence = _add_evidence(row)
    final_status = _state_from_mapping(
        evidence,
        "final_add_eligibility",
        "final_add_eligibility_status",
        "add_allocation_eligibility_status",
        default="",
    )
    if not final_status:
        final_status = _state_from_mapping(row, "final_add_eligibility", "add_allocation_eligibility_status", default="")
    status = "PASS" if final_status == "PASS" else ("REVIEW_REQUIRED" if not final_status else "BLOCK")
    reasons = ["authoritative_add_investment_evidence_pass"] if status == "PASS" else ["add_investment_evidence_final_eligibility_not_pass"]
    reasons.extend(str(reason) for reason in evidence.get("reason_codes") or evidence.get("final_add_eligibility_reason_codes") or [])
    for key in (
        "expected_edge_improvement_state",
        "incremental_investment_value_state",
        "opportunity_cost_status",
        "same_campaign_continuation_status",
    ):
        value = str(evidence.get(key) or row.get(key) or "")
        if value:
            reasons.append(f"{key}:{value}")
    return {
        "schema_version": "phase32_bz_add_admission_authority.v1",
        "status": status,
        "authority": "AUTHORITATIVE_ADD_INVESTMENT_EVIDENCE_FINAL_ELIGIBILITY",
        "final_add_eligibility": final_status or "MISSING",
        "reason_codes": sorted(set(reasons)),
        "future_information_used": False,
        "historical_outcome_used": False,
    }


def _add_evidence(row: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = row.get("add_investment_evidence")
    if isinstance(direct, Mapping):
        return direct
    for container_key in ("lineage", "desirability"):
        container = row.get(container_key)
        if not isinstance(container, Mapping):
            continue
        raw = container.get("raw_evidence")
        if not isinstance(raw, Mapping):
            continue
        nested = raw.get("add_investment_evidence")
        if isinstance(nested, Mapping):
            return nested
        if any(key in raw for key in ("final_add_eligibility", "add_allocation_eligibility_status")):
            return raw
    return row


def _state_from_mapping(payload: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value):
            return str(value).upper()
    return default


def _accepted_incremental_targets(
    ordered: Sequence[Mapping[str, Any]],
    *,
    starting_cash: float,
    cash_candidate: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    cash_value = _number((cash_candidate or {}).get("capital_value"), 0.0) or 0.0
    remaining_cash = starting_cash
    accepted: list[dict[str, Any]] = []
    accepted_add_lots: dict[str, int] = {}
    accepted_entry_lots: dict[str, int] = {}

    for candidate in ordered:
        if candidate.get("semantic_type") == "CASH_OPTIONALITY" or not _available(candidate):
            continue
        value = _number(candidate.get("capital_value"), -1.0) or -1.0
        if value <= cash_value + VALUE_TIE_TOLERANCE:
            continue
        symbol = str(candidate.get("symbol") or "")
        semantic_type = str(candidate.get("semantic_type") or "")
        increment_index = int(candidate.get("increment_index") or 0)
        campaign_key = f"{symbol}|{candidate.get('position_campaign_id') or ''}"
        if semantic_type == "ADD_NEXT_LOT" and increment_index != accepted_add_lots.get(campaign_key, 0) + 1:
            continue
        if semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"} and increment_index != int(accepted_entry_lots.get(_entry_lot_key(candidate), 0)) + 1:
            continue
        notional = _number(candidate.get("increment_notional"), 0.0) or 0.0
        if notional > remaining_cash + 1e-6:
            continue
        target = _target_from_candidate(candidate, remaining_cash=remaining_cash)
        accepted.append(target)
        remaining_cash = max(remaining_cash - notional, 0.0)
        if semantic_type == "ADD_NEXT_LOT":
            accepted_add_lots[campaign_key] = increment_index
        elif semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"}:
            accepted_entry_lots[_entry_lot_key(candidate)] = increment_index
    return accepted


def _budget_bounded_acceptance(
    ordered: Sequence[Mapping[str, Any]],
    *,
    allocation_budget: Mapping[str, Any],
    cash_candidate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    cash_value = _number((cash_candidate or {}).get("capital_value"), 0.0) or 0.0
    remaining_budget_weight = _number(allocation_budget.get("available_incremental_budget_weight"), 0.0) or 0.0
    remaining_budget_notional = _number(allocation_budget.get("available_incremental_budget_notional"), 0.0) or 0.0
    remaining_cash = _number(allocation_budget.get("starting_cash_notional"), remaining_budget_notional) or 0.0
    accepted: list[dict[str, Any]] = []
    sequence: list[dict[str, Any]] = []
    accepted_add_lots: dict[str, int] = {}
    accepted_entry_lots: dict[str, int] = {}
    consumed_ids: set[str] = set()

    while True:
        pool = [
            row
            for row in ordered
            if row.get("semantic_type") != "CASH_OPTIONALITY"
            and row.get("candidate_id") not in consumed_ids
            and _available(row)
            and _candidate_sequence_ready(row, accepted_add_lots=accepted_add_lots, accepted_entry_lots=accepted_entry_lots)
        ]
        pool = sorted(pool, key=_authority_sort_key)
        top = pool[0] if pool else None
        alternative = pool[1] if len(pool) > 1 else cash_candidate
        step_index = len(sequence) + 1
        if top is None:
            sequence.append(
                _sequence_step(
                    step_index=step_index,
                    remaining_budget_weight=remaining_budget_weight,
                    remaining_budget_notional=remaining_budget_notional,
                    remaining_cash=remaining_cash,
                    candidate_pool=pool,
                    top_candidate=None,
                    cash_candidate=cash_candidate,
                    next_alternative=alternative,
                    decision="STOP_CASH_OPTIONALITY",
                    reason_codes=["no_feasible_security_candidate_remaining"],
                )
            )
            break
        value = _number(top.get("capital_value"), -1.0) or -1.0
        alternative_value = _number((alternative or {}).get("capital_value"), -1.0) if alternative else None
        notional = _number(top.get("increment_notional"), 0.0) or 0.0
        weight = _number(top.get("increment_weight"), 0.0) or 0.0
        if value <= cash_value + VALUE_TIE_TOLERANCE:
            sequence.append(
                _sequence_step(
                    step_index=step_index,
                    remaining_budget_weight=remaining_budget_weight,
                    remaining_budget_notional=remaining_budget_notional,
                    remaining_cash=remaining_cash,
                    candidate_pool=pool,
                    top_candidate=top,
                    cash_candidate=cash_candidate,
                    next_alternative=alternative,
                    decision="STOP_CASH_BEATS_SECURITY",
                    reason_codes=["top_security_not_above_cash_optionality"],
                )
            )
            break
        if alternative and alternative.get("semantic_type") != "CASH_OPTIONALITY" and alternative_value is not None and abs(value - alternative_value) <= VALUE_TIE_TOLERANCE:
            sequence.append(
                _sequence_step(
                    step_index=step_index,
                    remaining_budget_weight=remaining_budget_weight,
                    remaining_budget_notional=remaining_budget_notional,
                    remaining_cash=remaining_cash,
                    candidate_pool=pool,
                    top_candidate=top,
                    cash_candidate=cash_candidate,
                    next_alternative=alternative,
                    decision="STOP_REVIEW_REQUIRED",
                    reason_codes=["ambiguous_next_best_marginal_value"],
                )
            )
            break
        if notional > remaining_budget_notional + 1e-6 or weight > remaining_budget_weight + 1e-10:
            sequence.append(
                _sequence_step(
                    step_index=step_index,
                    remaining_budget_weight=remaining_budget_weight,
                    remaining_budget_notional=remaining_budget_notional,
                    remaining_cash=remaining_cash,
                    candidate_pool=pool,
                    top_candidate=top,
                    cash_candidate=cash_candidate,
                    next_alternative=alternative,
                    decision="STOP_BUDGET_EXHAUSTED_TO_CASH",
                    reason_codes=["next_lot_exceeds_remaining_allocation_budget"],
                )
            )
            break
        top_with_budget = {
            **dict(top),
            "_remaining_budget_weight": remaining_budget_weight,
            "_remaining_budget_notional": remaining_budget_notional,
        }
        target = _target_from_candidate(top_with_budget, remaining_cash=remaining_cash)
        accepted.append(target)
        consumed_ids.add(str(top.get("candidate_id") or ""))
        remaining_budget_weight = round(max(remaining_budget_weight - weight, 0.0), 10)
        remaining_budget_notional = round(max(remaining_budget_notional - notional, 0.0), 6)
        remaining_cash = round(max(remaining_cash - notional, 0.0), 6)
        semantic_type = str(top.get("semantic_type") or "")
        symbol = str(top.get("symbol") or "")
        increment_index = int(top.get("increment_index") or 0)
        campaign_key = f"{symbol}|{top.get('position_campaign_id') or ''}"
        if semantic_type == "ADD_NEXT_LOT":
            accepted_add_lots[campaign_key] = increment_index
        elif semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"}:
            accepted_entry_lots[_entry_lot_key(top)] = increment_index
        sequence.append(
            _sequence_step(
                step_index=step_index,
                remaining_budget_weight=_number(target.get("remaining_budget_before"), remaining_budget_weight + weight) or 0.0,
                remaining_budget_notional=_number(target.get("remaining_budget_notional_before"), remaining_budget_notional + notional) or 0.0,
                remaining_cash=_number(target.get("remaining_cash_before"), remaining_cash + notional) or 0.0,
                candidate_pool=pool,
                top_candidate=top,
                cash_candidate=cash_candidate,
                next_alternative=alternative,
                decision="ACCEPT_INCREMENTAL_TARGET",
                reason_codes=["accepted_under_remaining_allocation_budget"],
                accepted_target=target,
                remaining_budget_weight_after=remaining_budget_weight,
                remaining_budget_notional_after=remaining_budget_notional,
                remaining_cash_after=remaining_cash,
            )
        )
        if remaining_budget_weight <= 1e-10 or remaining_budget_notional <= 1e-6:
            sequence.append(
                _sequence_step(
                    step_index=len(sequence) + 1,
                    remaining_budget_weight=remaining_budget_weight,
                    remaining_budget_notional=remaining_budget_notional,
                    remaining_cash=remaining_cash,
                    candidate_pool=[],
                    top_candidate=None,
                    cash_candidate=cash_candidate,
                    next_alternative=None,
                    decision="STOP_BUDGET_EXHAUSTED",
                    reason_codes=["allocation_budget_exhausted"],
                )
            )
            break
    return {"accepted_targets": accepted, "frontier_acceptance_sequence": sequence}


def _candidate_sequence_ready(
    candidate: Mapping[str, Any],
    *,
    accepted_add_lots: Mapping[str, int],
    accepted_entry_lots: Mapping[str, int],
) -> bool:
    semantic_type = str(candidate.get("semantic_type") or "")
    symbol = str(candidate.get("symbol") or "")
    if semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"}:
        return int(candidate.get("increment_index") or 0) == int(accepted_entry_lots.get(_entry_lot_key(candidate), 0)) + 1
    if semantic_type == "ADD_NEXT_LOT":
        campaign_key = f"{symbol}|{candidate.get('position_campaign_id') or ''}"
        return int(candidate.get("increment_index") or 0) == int(accepted_add_lots.get(campaign_key, 0)) + 1
    return False


def _entry_lot_key(candidate: Mapping[str, Any]) -> str:
    return f"{candidate.get('semantic_type') or ''}|{candidate.get('symbol') or ''}"


def _target_from_candidate(candidate: Mapping[str, Any], *, remaining_cash: float) -> dict[str, Any]:
    current_weight = _number(candidate.get("pre_weight"), 0.0) or 0.0
    incremental_weight = _number(candidate.get("increment_weight"), 0.0) or 0.0
    target_weight = _number(candidate.get("post_weight"), current_weight + incremental_weight) or 0.0
    target_gap = max(target_weight - current_weight, 0.0)
    notional = _number(candidate.get("increment_notional"), 0.0) or 0.0
    portfolio_value = notional / incremental_weight if incremental_weight > 0 else 0.0
    remaining_budget_weight = _number(candidate.get("_remaining_budget_weight"), 0.0) or 0.0
    remaining_budget_notional = _number(candidate.get("_remaining_budget_notional"), 0.0) or 0.0
    return {
        "symbol": candidate.get("symbol"),
        "semantic_type": candidate.get("semantic_type"),
        "position_campaign_id": candidate.get("position_campaign_id"),
        "current_weight": round(current_weight, 10),
        "target_weight": round(target_weight, 10),
        "accepted_incremental_weight": round(incremental_weight, 10),
        "target_gap": round(target_gap, 10),
        "target_minus_current": round(target_gap, 10),
        "accepted_incremental_quantity": int(candidate.get("increment_quantity") or 0),
        "accepted_incremental_notional": round(notional, 6),
        "pre_quantity": int(candidate.get("pre_quantity") or 0),
        "target_quantity": int(candidate.get("post_quantity") or 0),
        "increment_index": int(candidate.get("increment_index") or 0),
        "entry_lot_index": candidate.get("entry_lot_index"),
        "accepted_frontier_candidate_ids": [candidate.get("candidate_id")],
        "source_pm_decision_id": candidate.get("source_pm_decision_id"),
        "source_candidate_id": candidate.get("source_candidate_id"),
        "source_pc_evidence_ids": list(candidate.get("source_pc_evidence_ids") or []),
        "capital_value_authority": {
            "schema_version": SCHEMA_VERSION,
            "owner": OWNER,
            "producer": PRODUCER,
            "candidate_id": candidate.get("candidate_id"),
            "capital_value": candidate.get("capital_value"),
            "capital_value_components": dict(candidate.get("capital_value_components") or {}),
            "production_consumer_enabled": False,
        },
        "pc_target_magnitude_authority": dict(candidate.get("pc_target_magnitude_authority") or {}) if isinstance(candidate.get("pc_target_magnitude_authority"), Mapping) else {},
        "target_weight_reason_codes": list(candidate.get("capital_value_reason_codes") or []),
        "remaining_cash_before": round(remaining_cash, 6),
        "remaining_cash_after": round(max(remaining_cash - notional, 0.0), 6),
        "remaining_budget_before": round(remaining_budget_weight, 10),
        "remaining_budget_after": round(max(remaining_budget_weight - incremental_weight, 0.0), 10),
        "remaining_budget_notional_before": round(remaining_budget_notional or remaining_cash, 6),
        "remaining_budget_notional_after": round(max((remaining_budget_notional or remaining_cash) - notional, 0.0), 6),
        "portfolio_value_basis": round(portfolio_value, 6),
        "ps_compatible": True,
        "production_consumer_enabled": False,
    }


def _payload_review_reasons(shadow_payload: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> list[str]:
    reasons: list[str] = []
    if str(shadow_payload.get("cash_source_status") or "").upper() != "PASS":
        reasons.append(str(shadow_payload.get("cash_source_status") or "cash_source_review_required"))
    if any(row.get("authority_disposition") == "REVIEW_REQUIRED" for row in candidates):
        reasons.append("candidate_review_required")
    if any((row.get("constraints") or {}).get("status") == "REVIEW_REQUIRED" for row in candidates):
        reasons.append("constraint_review_required")
    if any((row.get("observability") or {}).get("status") == "REVIEW_REQUIRED" for row in candidates):
        reasons.append("observability_review_required")
    if any((row.get("feasibility") or {}).get("status") == "REVIEW_REQUIRED" for row in candidates):
        reasons.append("feasibility_review_required")
    return sorted(set(reasons))


def _allocation_budget_authority(
    *,
    shadow_payload: Mapping[str, Any],
    portfolio_construction_payload: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    cash_candidate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    portfolio_value = _portfolio_value(portfolio_construction_payload, candidates)
    starting_cash = _number((cash_candidate or {}).get("feasibility", {}).get("available_cash"), 0.0) or 0.0
    observations = _budget_observations(portfolio_construction_payload, portfolio_value=portfolio_value, starting_cash=starting_cash)
    if not observations:
        return {
            "status": "REVIEW_REQUIRED",
            "owner": "PORTFOLIO_CONSTRUCTION",
            "budget_envelope_owner": "PORTFOLIO_POLICY",
            "reason_codes": ["missing_allocation_budget_authority"],
            "available_incremental_budget_weight": 0.0,
            "available_incremental_budget_notional": 0.0,
            "starting_cash_notional": starting_cash,
            "portfolio_value_basis": portfolio_value,
            "source_observations": [],
            "future_information_used": False,
            "historical_outcome_used": False,
        }
    primary = observations[0]
    conflicts = [
        item
        for item in observations[1:]
        if int(item["priority"]) == int(primary["priority"])
        and abs(float(item["budget_weight"]) - float(primary["budget_weight"])) > 1e-6
    ]
    if conflicts:
        return {
            "status": "REVIEW_REQUIRED",
            "owner": "PORTFOLIO_CONSTRUCTION",
            "budget_envelope_owner": "PORTFOLIO_POLICY",
            "reason_codes": ["conflicting_allocation_budget_authority"],
            "available_incremental_budget_weight": 0.0,
            "available_incremental_budget_notional": 0.0,
            "starting_cash_notional": starting_cash,
            "portfolio_value_basis": portfolio_value,
            "source_observations": observations,
            "future_information_used": False,
            "historical_outcome_used": False,
        }
    budget_weight = min(max(float(primary["budget_weight"]), 0.0), 1.0)
    budget_notional = budget_weight * portfolio_value if portfolio_value > 0 else 0.0
    if starting_cash > 0:
        budget_notional = min(budget_notional, starting_cash)
        budget_weight = budget_notional / portfolio_value if portfolio_value > 0 else 0.0
    envelope = _embedded_budget_envelope(portfolio_construction_payload)
    return {
        "status": "PASS",
        "owner": "PORTFOLIO_CONSTRUCTION",
        "budget_envelope_owner": "PORTFOLIO_POLICY",
        "budget_envelope_schema_version": str(envelope.get("schema_version") or "incremental_capital_budget_envelope.v1"),
        "budget_envelope_hash": str(envelope.get("envelope_hash") or ""),
        "budget_source_role": primary["role"],
        "deployment_capacity_semantic": str(primary.get("deployment_capacity_semantic") or envelope.get("deployment_capacity_semantic") or ""),
        "risk_pacing_intent": str(primary.get("risk_pacing_intent") or envelope.get("risk_pacing_intent") or ""),
        "available_incremental_budget_weight": round(budget_weight, 10),
        "available_incremental_budget_notional": round(budget_notional, 6),
        "starting_cash_notional": round(starting_cash, 6),
        "remaining_budget_weight": round(budget_weight, 10),
        "remaining_budget_notional": round(budget_notional, 6),
        "portfolio_value_basis": round(portfolio_value, 6),
        "cash_source_status": shadow_payload.get("cash_source_status", "UNKNOWN"),
        "cash_source_lineage": _strip_forbidden_list(shadow_payload.get("cash_source_lineage") or []),
        "source_observations": observations,
        "reason_codes": ["allocation_budget_resolved_from_existing_authority"],
        "future_information_used": False,
        "historical_outcome_used": False,
    }


def _budget_observations(
    portfolio_construction_payload: Mapping[str, Any],
    *,
    portfolio_value: float,
    starting_cash: float,
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    observations.extend(
        _budget_observations_from_mapping(
            portfolio_construction_payload,
            priority=1,
            role="portfolio_construction.available_incremental_budget",
            portfolio_value=portfolio_value,
            fields=("available_incremental_budget", "available_incremental_budget_weight"),
        )
    )
    capital_competition = (
        portfolio_construction_payload.get("capital_competition")
        if isinstance(portfolio_construction_payload.get("capital_competition"), Mapping)
        else {}
    )
    multi = (
        capital_competition.get("canonical_multi_allocation_deployment_set")
        if isinstance(capital_competition.get("canonical_multi_allocation_deployment_set"), Mapping)
        else {}
    )
    observations.extend(
        _budget_observations_from_mapping(
            multi,
            priority=2,
            role="portfolio_construction.capital_competition.canonical_multi_allocation_deployment_set.available_incremental_budget",
            portfolio_value=portfolio_value,
            fields=("available_incremental_budget",),
        )
    )
    reconciliation = (
        portfolio_construction_payload.get("incremental_budget_reconciliation")
        if isinstance(portfolio_construction_payload.get("incremental_budget_reconciliation"), Mapping)
        else {}
    )
    observations.extend(
        _budget_observations_from_mapping(
            reconciliation,
            priority=3,
            role="portfolio_construction.incremental_budget_reconciliation.available_incremental_budget",
            portfolio_value=portfolio_value,
            fields=("available_incremental_budget",),
        )
    )
    envelope = _embedded_budget_envelope(portfolio_construction_payload)
    existing_exposure = envelope.get("existing_exposure_context") if isinstance(envelope.get("existing_exposure_context"), Mapping) else {}
    target = _number(existing_exposure.get("target_gross_exposure_ratio"))
    current = _number(existing_exposure.get("gross_exposure_ratio"))
    if target is not None and current is not None:
        observations.append(
            {
                "priority": 4,
                "role": "portfolio_policy.incremental_capital_budget_envelope.gross_exposure_headroom",
                "budget_weight": max(target - current, 0.0),
                "budget_notional": max(target - current, 0.0) * portfolio_value if portfolio_value > 0 else 0.0,
                "deployment_capacity_semantic": envelope.get("deployment_capacity_semantic", ""),
                "risk_pacing_intent": envelope.get("risk_pacing_intent", ""),
            }
        )
    deduped: dict[tuple[str, float], dict[str, Any]] = {}
    for item in observations:
        deduped[(str(item["role"]), round(float(item["budget_weight"]), 10))] = item
    return sorted(deduped.values(), key=lambda item: (int(item["priority"]), str(item["role"])))


def _budget_observations_from_mapping(
    payload: Mapping[str, Any],
    *,
    priority: int,
    role: str,
    portfolio_value: float,
    fields: Sequence[str],
) -> list[dict[str, Any]]:
    observations = []
    for field in fields:
        value = _number(payload.get(field))
        if value is None:
            continue
        budget_weight = value if value <= 1.0 else (value / portfolio_value if portfolio_value > 0 else 0.0)
        observations.append(
            {
                "priority": priority,
                "role": role,
                "field": field,
                "budget_weight": round(max(budget_weight, 0.0), 10),
                "budget_notional": round(max(budget_weight, 0.0) * portfolio_value, 6) if portfolio_value > 0 else 0.0,
            }
        )
    return observations


def _embedded_budget_envelope(portfolio_construction_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    policy = (
        portfolio_construction_payload.get("portfolio_policy_allocation_authority")
        if isinstance(portfolio_construction_payload.get("portfolio_policy_allocation_authority"), Mapping)
        else {}
    )
    envelope = policy.get("incremental_capital_budget_envelope") if isinstance(policy.get("incremental_capital_budget_envelope"), Mapping) else {}
    if envelope:
        return envelope
    capital_competition = (
        portfolio_construction_payload.get("capital_competition")
        if isinstance(portfolio_construction_payload.get("capital_competition"), Mapping)
        else {}
    )
    multi = (
        capital_competition.get("canonical_multi_allocation_deployment_set")
        if isinstance(capital_competition.get("canonical_multi_allocation_deployment_set"), Mapping)
        else {}
    )
    return multi.get("budget_envelope") if isinstance(multi.get("budget_envelope"), Mapping) else {}


def _sequence_step(
    *,
    step_index: int,
    remaining_budget_weight: float,
    remaining_budget_notional: float,
    remaining_cash: float,
    candidate_pool: Sequence[Mapping[str, Any]],
    top_candidate: Mapping[str, Any] | None,
    cash_candidate: Mapping[str, Any] | None,
    next_alternative: Mapping[str, Any] | None,
    decision: str,
    reason_codes: Sequence[str],
    accepted_target: Mapping[str, Any] | None = None,
    remaining_budget_weight_after: float | None = None,
    remaining_budget_notional_after: float | None = None,
    remaining_cash_after: float | None = None,
) -> dict[str, Any]:
    return {
        "step_index": step_index,
        "remaining_budget_before": round(remaining_budget_weight, 10),
        "remaining_budget_notional_before": round(remaining_budget_notional, 6),
        "remaining_cash_before": round(remaining_cash, 6),
        "candidate_pool_hash": _stable_hash({"candidate_ids": [row.get("candidate_id") for row in candidate_pool]}),
        "candidate_pool_count": len(candidate_pool),
        "top_candidate_id": (top_candidate or {}).get("candidate_id"),
        "top_candidate_type": (top_candidate or {}).get("semantic_type"),
        "top_candidate_symbol": (top_candidate or {}).get("symbol"),
        "top_candidate_increment_index": (top_candidate or {}).get("increment_index"),
        "top_candidate_value": (top_candidate or {}).get("capital_value"),
        "cash_candidate_id": (cash_candidate or {}).get("candidate_id"),
        "cash_value": (cash_candidate or {}).get("capital_value"),
        "next_alternative_id": (next_alternative or {}).get("candidate_id"),
        "next_alternative_type": (next_alternative or {}).get("semantic_type"),
        "next_alternative_value": (next_alternative or {}).get("capital_value"),
        "decision": decision,
        "accepted_incremental_weight": (accepted_target or {}).get("accepted_incremental_weight", 0.0),
        "accepted_incremental_notional": (accepted_target or {}).get("accepted_incremental_notional", 0.0),
        "remaining_budget_after": round(remaining_budget_weight_after if remaining_budget_weight_after is not None else remaining_budget_weight, 10),
        "remaining_budget_notional_after": round(
            remaining_budget_notional_after if remaining_budget_notional_after is not None else remaining_budget_notional,
            6,
        ),
        "remaining_cash_after": round(remaining_cash_after if remaining_cash_after is not None else remaining_cash, 6),
        "reason_codes": sorted(set(str(reason) for reason in reason_codes)),
        "production_consumer_enabled": False,
    }


def _authorized_cash_allocation(
    allocation_budget: Mapping[str, Any],
    targets: Sequence[Mapping[str, Any]],
    cash: Mapping[str, Any] | None,
    review_reasons: Sequence[str],
) -> dict[str, Any]:
    budget_weight = _number(allocation_budget.get("available_incremental_budget_weight"), 0.0) or 0.0
    budget_notional = _number(allocation_budget.get("available_incremental_budget_notional"), 0.0) or 0.0
    security_weight = sum(float(target.get("accepted_incremental_weight") or 0.0) for target in targets) if not review_reasons else 0.0
    security_notional = sum(float(target.get("accepted_incremental_notional") or 0.0) for target in targets) if not review_reasons else 0.0
    cash_weight = max(budget_weight - security_weight, 0.0) if not review_reasons else 0.0
    cash_notional = max(budget_notional - security_notional, 0.0) if not review_reasons else 0.0
    return {
        "status": "REVIEW_REQUIRED" if review_reasons else "PASS",
        "candidate_id": (cash or {}).get("candidate_id"),
        "competitor_type": "CASH_OPTIONALITY",
        "authorized_allocation_weight": round(cash_weight, 10),
        "authorized_allocation_notional": round(cash_notional, 6),
        "security_allocation_weight": round(security_weight, 10),
        "security_allocation_notional": round(security_notional, 6),
        "cash_is_first_class": True,
        "cash_is_residual_only": False,
        "reason_codes": sorted(set(review_reasons)) if review_reasons else ["remaining_budget_allocated_to_cash_optionality"],
        "production_consumer_enabled": False,
    }


def _capital_conservation(
    allocation_budget: Mapping[str, Any],
    targets: Sequence[Mapping[str, Any]],
    review_reasons: Sequence[str],
) -> dict[str, Any]:
    budget_weight = _number(allocation_budget.get("available_incremental_budget_weight"), 0.0) or 0.0
    budget_notional = _number(allocation_budget.get("available_incremental_budget_notional"), 0.0) or 0.0
    security_weight = sum(float(target.get("accepted_incremental_weight") or 0.0) for target in targets) if not review_reasons else 0.0
    security_notional = sum(float(target.get("accepted_incremental_notional") or 0.0) for target in targets) if not review_reasons else 0.0
    cash_weight = max(budget_weight - security_weight, 0.0) if not review_reasons else 0.0
    cash_notional = max(budget_notional - security_notional, 0.0) if not review_reasons else 0.0
    weight_delta = round(abs(budget_weight - security_weight - cash_weight), 10)
    notional_delta = round(abs(budget_notional - security_notional - cash_notional), 6)
    status = "REVIEW_REQUIRED" if review_reasons else ("PASS" if weight_delta <= 1e-8 and notional_delta <= 1e-4 else "FAIL")
    return {
        "status": status,
        "available_incremental_budget_weight": round(budget_weight, 10),
        "security_allocation_weight": round(security_weight, 10),
        "authorized_cash_allocation_weight": round(cash_weight, 10),
        "unallocated_residual_weight": 0.0 if status == "PASS" else weight_delta,
        "available_incremental_budget_notional": round(budget_notional, 6),
        "security_allocation_notional": round(security_notional, 6),
        "authorized_cash_allocation_notional": round(cash_notional, 6),
        "unallocated_residual_notional": 0.0 if status == "PASS" else notional_delta,
        "reason_codes": sorted(set(review_reasons)) if review_reasons else ["allocated_plus_cash_equals_budget"],
        "production_consumer_enabled": False,
    }


def _budget_stop_reasons(
    sequence: Sequence[Mapping[str, Any]],
    allocation_budget: Mapping[str, Any],
    review_reasons: Sequence[str],
) -> list[str]:
    if review_reasons:
        return sorted(set(str(reason) for reason in review_reasons))
    reasons = [str(reason) for step in sequence for reason in step.get("reason_codes") or [] if str(reason).startswith(("allocation_budget", "next_lot", "top_security", "no_feasible"))]
    if not reasons and allocation_budget.get("status") == "PASS":
        reasons.append("allocation_budget_active")
    return sorted(set(reasons))


def _portfolio_value(portfolio_construction_payload: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> float:
    for value in (
        portfolio_construction_payload.get("portfolio_total_equity"),
        portfolio_construction_payload.get("portfolio_value"),
        portfolio_construction_payload.get("total_equity"),
    ):
        number = _number(value)
        if number and number > 0:
            return number
    for candidate in candidates:
        notional = _number(candidate.get("increment_notional"))
        weight = _number(candidate.get("increment_weight"))
        if notional and weight and weight > 0:
            return notional / weight
    return 0.0


def _ambiguous_top_value(candidates: Sequence[Mapping[str, Any]]) -> bool:
    comparable = [row for row in candidates if row.get("semantic_type") != "CASH_OPTIONALITY" and _available(row)]
    comparable = sorted(comparable, key=_authority_sort_key)
    if len(comparable) < 2:
        return False
    first, second = comparable[0], comparable[1]
    first_value = _number(first.get("capital_value"))
    second_value = _number(second.get("capital_value"))
    return (
        first_value is not None
        and second_value is not None
        and abs(first_value - second_value) <= VALUE_TIE_TOLERANCE
        and first.get("semantic_type") != second.get("semantic_type")
    )


def _target_gap_authority(targets: Sequence[Mapping[str, Any]], review_reasons: Sequence[str]) -> dict[str, Any]:
    return {
        "status": "REVIEW_REQUIRED" if review_reasons else "PASS",
        "accepted_target_count": len(targets) if not review_reasons else 0,
        "accepted_incremental_weight_total": round(sum(float(target.get("accepted_incremental_weight") or 0.0) for target in targets), 10)
        if not review_reasons
        else 0.0,
        "accepted_incremental_notional_total": round(sum(float(target.get("accepted_incremental_notional") or 0.0) for target in targets), 6)
        if not review_reasons
        else 0.0,
        "targets": list(targets) if not review_reasons else [],
        "ps_compatible": True,
        "production_consumer_enabled": False,
        "reason_codes": sorted(set(review_reasons)),
    }


def _cash_disposition(
    cash: Mapping[str, Any] | None,
    targets: Sequence[Mapping[str, Any]],
    review_reasons: Sequence[str],
) -> dict[str, Any]:
    if cash is None:
        return {"status": "REVIEW_REQUIRED", "reason_codes": ["missing_cash_candidate"]}
    if review_reasons:
        return {"status": "REVIEW_REQUIRED", "candidate_id": cash.get("candidate_id"), "reason_codes": sorted(set(review_reasons))}
    if not targets:
        return {"status": "ACCEPTED_OPTIONALITY", "candidate_id": cash.get("candidate_id"), "capital_value": cash.get("capital_value")}
    return {
        "status": "REJECTED_BY_ACCEPTED_SECURITY_TARGETS",
        "candidate_id": cash.get("candidate_id"),
        "capital_value": cash.get("capital_value"),
        "accepted_security_target_count": len(targets),
    }


def _authority_result(
    candidates: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    review_reasons: Sequence[str],
) -> dict[str, Any]:
    return {
        "status": "REVIEW_REQUIRED" if review_reasons else "PASS",
        "candidate_count_total": len(candidates),
        "candidate_count_by_type": {
            semantic_type: sum(1 for row in candidates if row.get("semantic_type") == semantic_type)
            for semantic_type in ("NEW_FIRST_LOT", "REENTRY_FIRST_LOT", "ADD_NEXT_LOT", "CASH_OPTIONALITY")
        },
        "accepted_target_count": len(targets) if not review_reasons else 0,
        "accepted_candidate_ids": [target.get("accepted_frontier_candidate_ids", [None])[0] for target in targets] if not review_reasons else [],
        "review_reasons": sorted(set(review_reasons)),
    }


def _guardrails(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    dispositions = [str(row.get("authority_disposition") or row.get("shadow_disposition") or "") for row in candidates]
    return {
        "cap_blocked_count": sum(1 for value in dispositions if value == "INFEASIBLE_CAP_BLOCKED"),
        "cash_blocked_count": sum(1 for value in dispositions if value == "INFEASIBLE_INSUFFICIENT_CASH"),
        "safety_blocked_count": sum(1 for value in dispositions if value == "INELIGIBLE_SAFETY_BLOCKED"),
        "risk_pacing_blocked_count": sum(1 for value in dispositions if value == "INELIGIBLE_RISK_PACING_BLOCKED"),
        "no_loss_averaging_blocked_count": sum(1 for value in dispositions if value == "INELIGIBLE_NO_LOSS_AVERAGING_REJECTION"),
        "preserved": True,
    }


def _nonaccepted_disposition(
    row: Mapping[str, Any],
    *,
    cash: Mapping[str, Any] | None,
    review_reasons: Sequence[str],
) -> str:
    if review_reasons:
        return "REVIEW_REQUIRED"
    if not _available(row):
        return str(row.get("shadow_disposition") or "INELIGIBLE_OR_INFEASIBLE")
    if row.get("semantic_type") == "CASH_OPTIONALITY":
        return "CASH_REJECTED_BY_STRONGER_SECURITY" if cash is row else "CASH_OPTIONALITY_REJECTED"
    return "REJECTED_BY_STRONGER_MARGINAL_CAPITAL_VALUE"


def _attach_alternatives(candidates: Sequence[dict[str, Any]]) -> None:
    accepted_or_available = [row for row in candidates if row.get("authority_disposition") == "ACCEPTED_INCREMENTAL_TARGET" or _available(row)]
    for row in candidates:
        alternative = next((candidate for candidate in accepted_or_available if candidate is not row), None)
        row["strongest_alternative"] = _alternative_ref(alternative) if alternative else None
        cash = next((candidate for candidate in candidates if candidate.get("semantic_type") == "CASH_OPTIONALITY"), None)
        if cash and row is not cash:
            row["cash_comparison"] = {
                "cash_candidate_id": cash.get("candidate_id"),
                "cash_capital_value": cash.get("capital_value"),
                "candidate_beats_cash": (_number(row.get("capital_value"), -1.0) or -1.0) > (_number(cash.get("capital_value"), 0.0) or 0.0),
            }


def _alternative_ref(candidate: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not candidate:
        return None
    return {
        "candidate_id": candidate.get("candidate_id"),
        "semantic_type": candidate.get("semantic_type"),
        "symbol": candidate.get("symbol"),
        "increment_index": candidate.get("increment_index"),
        "capital_value": candidate.get("capital_value"),
        "authority_disposition": candidate.get("authority_disposition"),
    }


def _is_cash_winner(cash: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> bool:
    if not _available(cash):
        return False
    cash_value = _number(cash.get("capital_value"), 0.0) or 0.0
    securities = [row for row in candidates if row.get("semantic_type") != "CASH_OPTIONALITY" and _available(row)]
    return not securities or all((_number(row.get("capital_value"), -1.0) or -1.0) <= cash_value + VALUE_TIE_TOLERANCE for row in securities)


def _available(candidate: Mapping[str, Any]) -> bool:
    add_admission = candidate.get("add_admission_authority")
    if isinstance(add_admission, Mapping) and add_admission.get("status") != "PASS":
        return False
    if candidate.get("capital_value_status") is not None and candidate.get("capital_value_status") != "PASS":
        return False
    if _security_comparison_validation(candidate)["status"] != "PASS":
        return False
    return (
        (candidate.get("constraints") or {}).get("status") == "PASS"
        and (candidate.get("feasibility") or {}).get("status") == "PASS"
        and (candidate.get("observability") or {}).get("status") == "PASS"
    )


def _security_comparison_validation(candidate: Mapping[str, Any]) -> dict[str, Any]:
    if candidate.get("semantic_type") == "CASH_OPTIONALITY":
        return {"status": "PASS", "reason_codes": []}
    reasons: list[str] = []
    comparison_class = str(candidate.get("comparison_class") or "").upper()
    if comparison_class == "BLOCKED":
        reasons.append("accepted_source_candidate_comparison_class_blocked")
    marginal_class = _marginal_capital_value_class(candidate)
    if marginal_class == "BLOCKED_OR_NOT_ELIGIBLE":
        reasons.append("accepted_source_candidate_marginal_capital_value_blocked")
    desirability = candidate.get("desirability") if isinstance(candidate.get("desirability"), Mapping) else {}
    desirability_status = str(desirability.get("status") or "").upper()
    if desirability_status and desirability_status != "PASS":
        reasons.append(f"accepted_source_candidate_desirability_not_pass:{desirability_status}")
    if reasons:
        if comparison_class == "BLOCKED" or marginal_class == "BLOCKED_OR_NOT_ELIGIBLE":
            return {"status": "BLOCK", "reason_codes": sorted(set(reasons))}
        return {"status": "REVIEW_REQUIRED", "reason_codes": sorted(set(reasons))}
    return {"status": "PASS", "reason_codes": []}


def _marginal_capital_value_class(candidate: Mapping[str, Any]) -> str:
    direct = str(candidate.get("marginal_capital_value_class") or "").upper()
    if direct:
        return direct
    authority = candidate.get("marginal_capital_value_authority")
    if isinstance(authority, Mapping):
        value = str(authority.get("marginal_capital_value_class") or "").upper()
        if value:
            return value
    lineage = candidate.get("lineage") if isinstance(candidate.get("lineage"), Mapping) else {}
    raw = lineage.get("raw_evidence") if isinstance(lineage.get("raw_evidence"), Mapping) else {}
    raw_value = str(raw.get("marginal_capital_value_class") or "").upper()
    if raw_value:
        return raw_value
    raw_authority = raw.get("marginal_capital_value_authority") if isinstance(raw.get("marginal_capital_value_authority"), Mapping) else {}
    return str(raw_authority.get("marginal_capital_value_class") or "").upper()


def _authority_sort_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    available_rank = 0 if _available(candidate) else 9
    value = _number(candidate.get("capital_value"), -1.0) or -1.0
    return (
        available_rank,
        -value,
        int(candidate.get("increment_index") or 0),
        _semantic_rank(str(candidate.get("semantic_type") or "")),
        str(candidate.get("symbol") or ""),
        str(candidate.get("candidate_id") or ""),
    )


def _semantic_rank(value: str) -> int:
    return {
        "NEW_FIRST_LOT": 0,
        "REENTRY_FIRST_LOT": 1,
        "ADD_NEXT_LOT": 2,
        "CASH_OPTIONALITY": 3,
    }.get(value, 99)


def _requalification_component(row: Mapping[str, Any], components: Mapping[str, Any]) -> float:
    semantic_type = str(row.get("semantic_type") or "")
    if semantic_type == "REENTRY_FIRST_LOT":
        return 1.0 if _state(components.get("recovery")) in {"PASS", "RECOVERED"} else 0.0
    if semantic_type == "ADD_NEXT_LOT":
        states = [_state(components.get("continuation")), _state(components.get("incremental_value")), _state(components.get("cash_opportunity_cost"))]
        positives = sum(1 for value in states if value in {"PASS", "CONTINUING", "POSITIVE", "IMPROVING", "FAVORABLE"})
        return positives / len(states)
    return 1.0 if str(row.get("comparison_class") or "").upper() not in {"INSUFFICIENT", "BLOCKED"} else 0.0


def _rank_component(rank: float | None) -> float:
    if rank is None or rank <= 0:
        return 0.0
    return _clamp01(1.0 / rank)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _state(value: Any) -> str:
    return str(value or "").upper()


def _number(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _rows(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    rows = payload.get(key)
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, Mapping)]
    return []


def _strip_forbidden_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    stripped = {}
    for key, value in payload.items():
        if str(key) in FORBIDDEN_OUTCOME_FIELDS:
            continue
        if isinstance(value, Mapping):
            stripped[str(key)] = _strip_forbidden_mapping(value)
        elif isinstance(value, list):
            stripped[str(key)] = _strip_forbidden_list(value)
        else:
            stripped[str(key)] = value
    return stripped


def _strip_forbidden_list(values: Sequence[Any]) -> list[Any]:
    stripped = []
    for value in values:
        if isinstance(value, Mapping):
            stripped.append(_strip_forbidden_mapping(value))
        elif isinstance(value, list):
            stripped.append(_strip_forbidden_list(value))
        else:
            stripped.append(value)
    return stripped


def _determinism_key(candidates: Sequence[Mapping[str, Any]], shadow_payload: Mapping[str, Any]) -> str:
    return _stable_hash(
        {
            "schema_version": SCHEMA_VERSION,
            "business_date": shadow_payload.get("business_date"),
            "session": shadow_payload.get("session"),
            "shadow_frontier_artifact_hash": shadow_payload.get("artifact_hash"),
            "candidate_ids": [row.get("candidate_id") for row in candidates],
            "capital_values": [row.get("capital_value") for row in candidates],
        }
    )


def _stable_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(payload), ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
