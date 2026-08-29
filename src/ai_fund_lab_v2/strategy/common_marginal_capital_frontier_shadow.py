from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_fund_lab_v2.strategy import marginal_capital_value


SCHEMA_NAME = "canonical_marginal_capital_frontier"
SCHEMA_VERSION = "canonical_marginal_capital_frontier.v1"
PRODUCER = "strategy.common_marginal_capital_frontier_shadow"
ARTIFACT_MODE = "SHADOW_NON_AUTHORITATIVE"
OWNER = "PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_SHADOW"
COMPARISON_REPRESENTATION = "STRUCTURED_PARTIAL_ORDER"
PRODUCTION_CONSUMERS: tuple[str, ...] = ()
PRODUCTION_CONSUMER_COUNT = 0
CASH_CONFLICT_TOLERANCE = 1e-6

SEMANTIC_TYPES = ("NEW_FIRST_LOT", "REENTRY_FIRST_LOT", "ADD_NEXT_LOT", "CASH_OPTIONALITY")
FORBIDDEN_OUTCOME_FIELDS = marginal_capital_value.FORBIDDEN_OUTCOME_FIELDS


def build_canonical_marginal_capital_frontier_payload(
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
    """Build a non-authoritative common marginal capital frontier artifact.

    The optional ADD generation bound is an observability guard for a shadow
    artifact, not investment policy and not production quantity authority.
    """

    pc_members = _rows(portfolio_construction_payload, "portfolio_members", "members")
    ps_by_symbol = {_symbol(row): row for row in _rows(position_sizing_payload or {}, "positions", "position_sizing_decisions", "sizing_decisions") if _symbol(row)}
    portfolio_value = _portfolio_value(portfolio_construction_payload, position_sizing_payload, pc_members)
    cash_state = _cash_state(portfolio_construction_payload, cash_payload)
    safety_state = _safety_state(safety_payload)
    risk_state = _risk_state(portfolio_construction_payload, risk_pacing_payload)
    cap_state = _effective_single_name_cap_state(
        portfolio_construction_payload=portfolio_construction_payload,
        position_sizing_payload=position_sizing_payload or {},
        safety_payload=safety_payload or {},
    )

    candidates: list[dict[str, Any]] = []
    for stable_index, row in enumerate(pc_members, start=1):
        symbol = _symbol(row)
        if not symbol:
            continue
        candidate_row = _row_with_effective_cap(row, cap_state=cap_state)
        if _is_new_first_lot(row):
            candidates.extend(
                _entry_target_lot_candidates(
                    candidate_row,
                    semantic_type="NEW_FIRST_LOT",
                    business_date=business_date,
                    session=session,
                    portfolio_value=portfolio_value,
                    cash_state=cash_state,
                    safety_state=safety_state,
                    risk_state=risk_state,
                    ps_row=ps_by_symbol.get(symbol, {}),
                    stable_index=stable_index,
                )
            )
        elif _is_reentry_first_lot(row):
            candidates.extend(
                _entry_target_lot_candidates(
                    candidate_row,
                    semantic_type="REENTRY_FIRST_LOT",
                    business_date=business_date,
                    session=session,
                    portfolio_value=portfolio_value,
                    cash_state=cash_state,
                    safety_state=safety_state,
                    risk_state=risk_state,
                    ps_row=ps_by_symbol.get(symbol, {}),
                    stable_index=stable_index,
                )
            )
        elif _is_add(row):
            candidates.extend(
                _add_next_lot_candidates(
                    candidate_row,
                    business_date=business_date,
                    session=session,
                    portfolio_value=portfolio_value,
                    cash_state=cash_state,
                    safety_state=safety_state,
                    risk_state=risk_state,
                    ps_row=ps_by_symbol.get(symbol, {}),
                    max_lots=max_add_lots_per_position,
                    stable_index=stable_index,
                )
            )

    candidates.append(_cash_candidate(business_date=business_date, session=session, cash_state=cash_state, safety_state=safety_state, risk_state=risk_state))
    ordered = sorted(candidates, key=_frontier_sort_key)
    _assign_frontier_dispositions(ordered)
    payload = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "artifact_mode": ARTIFACT_MODE,
        "owner": OWNER,
        "producer": PRODUCER,
        "business_date": business_date,
        "session": session,
        "run_id": run_id,
        "comparison_representation": COMPARISON_REPRESENTATION,
        "pit_status": "PIT_CURRENT_DECISION_TIME_EVIDENCE_ONLY",
        "future_information_used": False,
        "historical_outcome_used": False,
        "paper_ledger_input_used": False,
        "selected_or_bought_outcome_used": False,
        "production_consumers": list(PRODUCTION_CONSUMERS),
        "production_consumer_count": PRODUCTION_CONSUMER_COUNT,
        "feeds_position_sizing": False,
        "feeds_runtime_planning": False,
        "feeds_pending": False,
        "feeds_orders": False,
        "feeds_execution": False,
        "feeds_safety_authority": False,
        "production_target_weight_changed": False,
        "production_behavior_changed": False,
        "max_add_lots_per_position": max_add_lots_per_position,
        "add_lot_generation_limit_type": "SHADOW_ENGINEERING_OBSERVABILITY_BOUND_NOT_INVESTMENT_POLICY",
        "portfolio_state_ref": _artifact_ref(source_artifacts, source_hashes, "portfolio_state"),
        "candidate_artifact_refs": _artifact_ref(source_artifacts, source_hashes, "candidate"),
        "pm_artifact_refs": _artifact_ref(source_artifacts, source_hashes, "position_management"),
        "pc_artifact_refs": _artifact_ref(source_artifacts, source_hashes, "portfolio_construction"),
        "risk_pacing_refs": _artifact_ref(source_artifacts, source_hashes, "risk_pacing"),
        "safety_refs": _artifact_ref(source_artifacts, source_hashes, "safety"),
        "cash_state_ref": _artifact_ref(source_artifacts, source_hashes, "cash"),
        "cash_source_status": cash_state.get("cash_source_status", "UNKNOWN"),
        "cash_source_lineage": cash_state.get("cash_source_lineage", []),
        "effective_single_name_cap_authority": cap_state,
        "frontier_candidates": ordered,
        "frontier_result": _frontier_result(ordered),
        "shadow_target_projection": _shadow_target_projection(ordered),
        "released_capital_observation": _released_capital_observation(portfolio_construction_payload, ordered),
        "metrics": _metrics(ordered),
        "determinism_key": _determinism_key(
            business_date=business_date,
            session=session,
            candidates=ordered,
            source_hashes=source_hashes or {},
        ),
    }
    payload["artifact_hash"] = stable_payload_hash(payload)
    return payload


def write_canonical_marginal_capital_frontier_artifact(payload: Mapping[str, Any], output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def materialize_canonical_marginal_capital_frontier_for_day(
    *,
    run_root: Path | str,
    business_date: str,
    output_subdir: str = "diagnostic_shadow",
) -> dict[str, Any]:
    run_root = Path(run_root)
    day_dir = run_root / "daily" / business_date
    strategy_dir = day_dir / "strategy"
    morning_dir = day_dir / "morning"
    valuation_dir = day_dir / "current_valuation_refresh"
    pc_path = strategy_dir / "portfolio_construction.json"
    ps_path = strategy_dir / "position_sizing.json"
    portfolio_policy_path = strategy_dir / "portfolio_policy.json"
    valuation_projection_path = valuation_dir / "valuation_projection.json"
    safety_path = valuation_dir / "safety_authority_decision.json"
    if not safety_path.is_file():
        safety_path = morning_dir / "safety_decision.json"
    pc_payload = _load_json(pc_path)
    portfolio_policy_payload = _load_json(portfolio_policy_path)
    valuation_projection_payload = _load_json(valuation_projection_path)
    cash_state = resolve_shadow_cash_state_for_day(
        portfolio_construction_payload=pc_payload,
        portfolio_policy_payload=portfolio_policy_payload,
        valuation_projection_payload=valuation_projection_payload,
        source_artifacts={
            "portfolio_policy": str(portfolio_policy_path),
            "valuation_projection": str(valuation_projection_path),
            "portfolio_construction": str(pc_path),
        },
        source_hashes={
            "portfolio_policy": _file_hash(portfolio_policy_path),
            "valuation_projection": _file_hash(valuation_projection_path),
            "portfolio_construction": _file_hash(pc_path),
        },
    )
    payload = build_canonical_marginal_capital_frontier_payload(
        business_date=business_date,
        portfolio_construction_payload=pc_payload,
        position_sizing_payload=_load_json(ps_path),
        safety_payload=_load_json(safety_path),
        cash_payload=cash_state,
        run_id=run_root.name,
        source_artifacts={
            "portfolio_construction": str(pc_path),
            "position_sizing": str(ps_path),
            "safety": str(safety_path),
            "cash": cash_state.get("cash_source_path", ""),
            "portfolio_policy": str(portfolio_policy_path),
            "valuation_projection": str(valuation_projection_path),
        },
        source_hashes={
            "portfolio_construction": _file_hash(pc_path),
            "position_sizing": _file_hash(ps_path),
            "safety": _file_hash(safety_path),
            "cash": cash_state.get("cash_source_hash", ""),
            "portfolio_policy": _file_hash(portfolio_policy_path),
            "valuation_projection": _file_hash(valuation_projection_path),
        },
    )
    output_path = day_dir / output_subdir / "canonical_marginal_capital_frontier.json"
    write_canonical_marginal_capital_frontier_artifact(payload, output_path)
    return {**payload, "artifact_path": str(output_path)}


def stable_payload_hash(payload: Mapping[str, Any]) -> str:
    canonical = {key: value for key, value in dict(payload).items() if key != "artifact_hash"}
    return _stable_hash(canonical)


def assert_shadow_frontier_not_production_consumer(payload: Mapping[str, Any]) -> bool:
    return (
        payload.get("artifact_mode") == ARTIFACT_MODE
        and int(payload.get("production_consumer_count") or 0) == 0
        and payload.get("feeds_position_sizing") is False
        and payload.get("feeds_runtime_planning") is False
        and payload.get("feeds_pending") is False
        and payload.get("feeds_orders") is False
        and payload.get("feeds_execution") is False
        and payload.get("feeds_safety_authority") is False
        and payload.get("production_behavior_changed") is False
    )


def resolve_shadow_cash_state_for_day(
    *,
    portfolio_construction_payload: Mapping[str, Any] | None = None,
    portfolio_policy_payload: Mapping[str, Any] | None = None,
    valuation_projection_payload: Mapping[str, Any] | None = None,
    source_artifacts: Mapping[str, Any] | None = None,
    source_hashes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    observations = _cash_observations(
        portfolio_policy_payload=portfolio_policy_payload or {},
        valuation_projection_payload=valuation_projection_payload or {},
        portfolio_construction_payload=portfolio_construction_payload or {},
        source_artifacts=source_artifacts or {},
        source_hashes=source_hashes or {},
    )
    if not observations:
        return {
            "cash_source_status": "REVIEW_REQUIRED",
            "cash_source_reason": "missing_decision_time_cash_evidence",
            "cash_source_lineage": [],
            "available_cash": None,
        }
    primary = observations[0]
    primary_priority = int(primary["priority"])
    conflicts = [
        item
        for item in observations[1:]
        if int(item["priority"]) == primary_priority
        if abs(float(item["available_cash"]) - float(primary["available_cash"])) > CASH_CONFLICT_TOLERANCE
    ]
    if conflicts:
        return {
            "cash_source_status": "REVIEW_REQUIRED",
            "cash_source_reason": "conflicting_decision_time_cash_evidence",
            "cash_source_lineage": observations,
            "available_cash": None,
        }
    available_cash = float(primary["available_cash"])
    return {
        "cash_source_status": "PASS",
        "cash_source_reason": "decision_time_cash_resolved",
        "cash_source_priority": primary["priority"],
        "cash_source_role": primary["role"],
        "cash_source_path": primary["path"],
        "cash_source_hash": primary["sha256"],
        "cash_source_lineage": observations,
        "available_cash": available_cash,
        "cash": available_cash,
        "buying_power": available_cash,
    }


def _security_candidate(
    row: Mapping[str, Any],
    *,
    semantic_type: str,
    business_date: str,
    session: str,
    portfolio_value: float,
    cash_state: Mapping[str, Any],
    safety_state: Mapping[str, Any],
    risk_state: Mapping[str, Any],
    ps_row: Mapping[str, Any],
    increment_index: int,
    pre_quantity: int,
    stable_index: int,
) -> dict[str, Any]:
    symbol = _symbol(row)
    trading_unit = int(_number(row.get("trading_unit") or ps_row.get("trading_unit"), 100) or 100)
    reference_price = _number(row.get("reference_price") or ps_row.get("reference_price") or row.get("price"), 0.0) or 0.0
    increment_quantity = int(_number(row.get("increment_quantity") or ps_row.get("transaction_quantity_candidate"), trading_unit) or trading_unit)
    if increment_quantity <= 0:
        increment_quantity = trading_unit
    increment_quantity = max(trading_unit, (increment_quantity // trading_unit) * trading_unit)
    current_quantity = int(_number(row.get("current_quantity") or row.get("quantity") or pre_quantity, pre_quantity) or 0)
    pre_quantity = pre_quantity if semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT", "ADD_NEXT_LOT"} else current_quantity
    post_quantity = pre_quantity + increment_quantity
    increment_notional = round(reference_price * increment_quantity, 6)
    pre_weight = _number(row.get("current_weight"), None)
    if semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"} and portfolio_value > 0 and reference_price > 0:
        pre_weight = (pre_quantity * reference_price) / portfolio_value
    elif pre_weight is None and portfolio_value > 0 and reference_price > 0:
        pre_weight = (pre_quantity * reference_price) / portfolio_value
    pre_weight = pre_weight or 0.0
    increment_weight = (increment_notional / portfolio_value) if portfolio_value > 0 else 0.0
    if semantic_type == "ADD_NEXT_LOT":
        pre_weight = pre_weight + increment_weight * max(increment_index - 1, 0)
    post_weight = pre_weight + increment_weight
    cap_authority = row.get("effective_single_name_cap_authority") if isinstance(row.get("effective_single_name_cap_authority"), Mapping) else {}
    single_name_cap = _number(cap_authority.get("effective_single_name_cap"), None)
    if single_name_cap is None:
        single_name_cap = _number(row.get("single_name_cap") or row.get("max_position_weight") or row.get("strategy_single_name_cap"), None)
    desirability = _desirability(row, semantic_type=semantic_type, business_date=business_date)
    production_admission = _production_first_lot_admission(row, semantic_type=semantic_type)
    feasibility = _feasibility(
        reference_price=reference_price,
        increment_quantity=increment_quantity,
        increment_notional=increment_notional,
        cash_state=cash_state,
        post_weight=post_weight,
        single_name_cap=single_name_cap,
        cap_authority=cap_authority,
    )
    constraints = _constraints(
        row,
        semantic_type=semantic_type,
        safety_state=safety_state,
        risk_state=risk_state,
        feasibility=feasibility,
        production_admission=production_admission,
        position_campaign_id=_campaign_id(row),
    )
    observability = _observability(row, semantic_type=semantic_type, reference_price=reference_price, portfolio_value=portfolio_value)
    candidate = {
        "business_date": business_date,
        "session": session,
        "symbol": symbol,
        "position_campaign_id": _campaign_id(row),
        "semantic_type": semantic_type,
        "candidate_id": "",
        "increment_index": increment_index,
        "pre_quantity": pre_quantity,
        "post_quantity": post_quantity,
        "increment_quantity": increment_quantity,
        "increment_quantity_source_authority": str(row.get("increment_quantity_source_authority") or ""),
        "pc_target_magnitude_authority": dict(row.get("pc_target_magnitude_authority") or {}) if isinstance(row.get("pc_target_magnitude_authority"), Mapping) else {},
        "entry_lot_index": increment_index if semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"} else None,
        "effective_single_name_cap_authority": dict(cap_authority),
        "pre_weight": round(pre_weight, 10),
        "post_weight": round(post_weight, 10),
        "increment_weight": round(increment_weight, 10),
        "reference_price": reference_price,
        "increment_notional": increment_notional,
        "source_pm_decision_id": str(row.get("pm_decision_id") or row.get("source_pm_decision_id") or ""),
        "source_candidate_id": str(row.get("candidate_id") or row.get("source_candidate_id") or row.get("opportunity_decision_id") or ""),
        "source_pc_evidence_ids": _source_pc_evidence_ids(row),
        "desirability": desirability,
        "risk_modifiers": _risk_modifiers(row, risk_state=risk_state, pre_weight=pre_weight, post_weight=post_weight, single_name_cap=single_name_cap),
        "production_admission": production_admission,
        "feasibility": feasibility,
        "constraints": constraints,
        "observability": observability,
        "lineage": _lineage(row),
        "diminishing_marginal_context": _diminishing_context(
            semantic_type=semantic_type,
            increment_index=increment_index,
            pre_weight=pre_weight,
            post_weight=post_weight,
            single_name_cap=single_name_cap,
            cash_before=_number(cash_state.get("available_cash"), 0.0) or 0.0,
            increment_notional=increment_notional,
        ),
        "comparison_class": desirability["comparison_class"],
        "comparison_representation": COMPARISON_REPRESENTATION,
        "strongest_alternative": None,
        "cash_comparison": None,
        "shadow_disposition": "PENDING_COMPARISON",
        "reason_codes": [],
        "stable_tie_order": 0,
        "hypothetical_only": True,
        "portfolio_state_mutated": False,
        "production_authority": False,
    }
    candidate["reason_codes"] = _candidate_reason_codes(candidate)
    candidate["candidate_id"] = _candidate_id(candidate)
    return candidate


def _entry_target_lot_candidates(
    row: Mapping[str, Any],
    *,
    semantic_type: str,
    business_date: str,
    session: str,
    portfolio_value: float,
    cash_state: Mapping[str, Any],
    safety_state: Mapping[str, Any],
    risk_state: Mapping[str, Any],
    ps_row: Mapping[str, Any],
    stable_index: int,
) -> list[dict[str, Any]]:
    trading_unit = int(_number(row.get("trading_unit") or ps_row.get("trading_unit"), 100) or 100)
    reference_price = _number(row.get("reference_price") or ps_row.get("reference_price") or row.get("price"), 0.0) or 0.0
    authority = _entry_target_magnitude_authority(
        row,
        ps_row=ps_row,
        semantic_type=semantic_type,
        portfolio_value=portfolio_value,
        reference_price=reference_price,
        trading_unit=trading_unit,
        cash_state=cash_state,
        safety_state=safety_state,
        risk_state=risk_state,
    )
    max_quantity = int(authority.get("pc_target_executable_quantity") or 0)
    increment_quantity = trading_unit
    diagnostic_non_deployable = max_quantity <= 0 and str(authority.get("status") or "").upper() in {"BLOCK", "REVIEW_REQUIRED"}
    max_lots = 1 if diagnostic_non_deployable else max(1, max_quantity // increment_quantity)
    candidates: list[dict[str, Any]] = []
    for index in range(1, max_lots + 1):
        pre_quantity = increment_quantity * (index - 1)
        if not diagnostic_non_deployable and pre_quantity + increment_quantity > max_quantity:
            break
        prior_notional = increment_quantity * reference_price * (index - 1)
        base_cash = _number(cash_state.get("available_cash"), 0.0) or 0.0
        hypothetical = dict(row)
        hypothetical["increment_quantity"] = increment_quantity
        hypothetical["increment_quantity_source_authority"] = "PC_TARGET_MAGNITUDE_TRADING_UNIT_EXPANSION"
        hypothetical["pc_target_magnitude_authority"] = authority
        one_lot_authority = authority.get("minimum_executable_one_lot_authority") if isinstance(authority.get("minimum_executable_one_lot_authority"), Mapping) else {}
        if str(one_lot_authority.get("decision") or "") == "ADMIT_ONE_LOT":
            hypothetical["target_weight"] = authority.get("target_weight")
            resolution = dict(hypothetical.get("target_weight_resolution") or {}) if isinstance(hypothetical.get("target_weight_resolution"), Mapping) else {}
            resolution["zero_weight_reason"] = ""
            resolution["resolved_weight"] = authority.get("target_weight")
            hypothetical["target_weight_resolution"] = resolution
        hypothetical_cash = {**dict(cash_state), "available_cash": max(base_cash - prior_notional, 0.0)}
        candidates.append(
            _security_candidate(
                hypothetical,
                semantic_type=semantic_type,
                business_date=business_date,
                session=session,
                portfolio_value=portfolio_value,
                cash_state=hypothetical_cash,
                safety_state=safety_state,
                risk_state=risk_state,
                ps_row=ps_row,
                increment_index=index,
                pre_quantity=pre_quantity,
                stable_index=stable_index,
            )
        )
    return candidates


def _add_next_lot_candidates(
    row: Mapping[str, Any],
    *,
    business_date: str,
    session: str,
    portfolio_value: float,
    cash_state: Mapping[str, Any],
    safety_state: Mapping[str, Any],
    risk_state: Mapping[str, Any],
    ps_row: Mapping[str, Any],
    max_lots: int,
    stable_index: int,
) -> list[dict[str, Any]]:
    symbol = _symbol(row)
    trading_unit = int(_number(row.get("trading_unit") or ps_row.get("trading_unit"), 100) or 100)
    reference_price = _number(row.get("reference_price") or ps_row.get("reference_price") or row.get("price"), 0.0) or 0.0
    current_quantity = int(_number(row.get("current_quantity") or row.get("quantity"), 0) or 0)
    if current_quantity <= 0 and portfolio_value > 0 and reference_price > 0:
        current_quantity = int(((_number(row.get("current_weight"), 0.0) or 0.0) * portfolio_value) / reference_price)
        current_quantity = (current_quantity // trading_unit) * trading_unit
    increment_quantity = _lot_increment_quantity(row, ps_row=ps_row, trading_unit=trading_unit)
    candidates = []
    for index in range(1, max(1, max_lots) + 1):
        hypothetical = dict(row)
        hypothetical["increment_quantity"] = increment_quantity
        hypothetical["increment_quantity_source_authority"] = "PS_PREFLIGHT_TRANSACTION_QUANTITY_CANDIDATE" if ps_row.get("transaction_quantity_candidate") not in (None, "") else "PC_OR_TRADING_UNIT_DEFAULT"
        pre_quantity = current_quantity + increment_quantity * (index - 1)
        prior_notional = increment_quantity * reference_price * (index - 1)
        base_cash = _number(cash_state.get("available_cash"), 0.0) or 0.0
        hypothetical_cash = {**dict(cash_state), "available_cash": max(base_cash - prior_notional, 0.0)}
        candidates.append(
            _security_candidate(
                hypothetical,
                semantic_type="ADD_NEXT_LOT",
                business_date=business_date,
                session=session,
                portfolio_value=portfolio_value,
                cash_state=hypothetical_cash,
                safety_state=safety_state,
                risk_state=risk_state,
                ps_row=ps_row,
                increment_index=index,
                pre_quantity=pre_quantity,
                stable_index=stable_index,
            )
        )
    return candidates


def _entry_target_magnitude_authority(
    row: Mapping[str, Any],
    *,
    ps_row: Mapping[str, Any],
    semantic_type: str,
    portfolio_value: float,
    reference_price: float,
    trading_unit: int,
    cash_state: Mapping[str, Any],
    safety_state: Mapping[str, Any],
    risk_state: Mapping[str, Any],
) -> dict[str, Any]:
    target_weight = _number(row.get("target_weight"), None)
    quality_bound = _quality_authorized_entry_target_weight(row)
    quality_enforced = bool(row.get("quality_target_upper_bound_enforced"))
    if not quality_enforced:
        resolution = row.get("target_weight_resolution") if isinstance(row.get("target_weight_resolution"), Mapping) else {}
        quality_enforced = bool(resolution.get("quality_target_upper_bound_enforced"))
    effective_target_weight = target_weight
    sublot_prezero_quality_target = _is_sublot_quality_zeroed_entry(row)
    if quality_bound is not None:
        if sublot_prezero_quality_target:
            effective_target_weight = quality_bound
            quality_enforced = True
        elif effective_target_weight is None:
            effective_target_weight = quality_bound
        else:
            effective_target_weight = min(effective_target_weight, quality_bound)
        if target_weight is not None and quality_bound < target_weight - 1e-12:
            quality_enforced = True
    sources: list[dict[str, Any]] = []
    for role, payload in _entry_target_quantity_sources(row, ps_row=ps_row):
        quantity = _number(payload.get("final_allocated_quantity") or payload.get("discrete_authorized_quantity") or payload.get("executable_quantity_delta") or payload.get("quantity_delta_candidate") or payload.get("target_quantity"))
        status = str(payload.get("status") or payload.get("authority_status") or "PASS").upper()
        if quantity is None or quantity <= 0 or status not in {"PASS", "AUTHORITATIVE", "OK"}:
            continue
        rounded_quantity = int(quantity)
        rounded_quantity = (rounded_quantity // trading_unit) * trading_unit
        quality_quantity = _weight_to_trading_unit_quantity(
            effective_target_weight,
            portfolio_value=portfolio_value,
            reference_price=reference_price,
            trading_unit=trading_unit,
        )
        if quality_enforced and quality_quantity is not None:
            rounded_quantity = min(rounded_quantity, quality_quantity)
        if rounded_quantity > 0:
            sources.append({"role": role, "quantity": rounded_quantity, "status": status})

    computed_quantity = 0
    if effective_target_weight is not None and effective_target_weight > 0 and portfolio_value > 0 and reference_price > 0 and trading_unit > 0:
        raw = int((effective_target_weight * portfolio_value) / reference_price)
        computed_quantity = (raw // trading_unit) * trading_unit
        if computed_quantity > 0:
            sources.append({"role": "pc.target_weight_floor_to_trading_unit", "quantity": computed_quantity, "status": "PASS"})

    top_quantity = sources[0]["quantity"] if sources else 0
    conflicts = [source for source in sources[1:] if int(source["quantity"]) != int(top_quantity)]
    status = "PASS"
    reasons = ["pc_target_magnitude_resolved"]
    one_lot_authority: dict[str, Any] = {}
    if conflicts:
        status = "REVIEW_REQUIRED"
        reasons = ["conflicting_pc_target_quantity_authority"]
    elif top_quantity <= 0 and quality_enforced and effective_target_weight is not None and effective_target_weight > 0:
        one_lot_authority = _minimum_executable_one_lot_authority(
            row,
            semantic_type=semantic_type,
            quality_authorized_target_weight=effective_target_weight,
            pre_quality_base_target_weight=_number(row.get("pre_quality_base_target_weight"), target_weight),
            portfolio_value=portfolio_value,
            reference_price=reference_price,
            trading_unit=trading_unit,
            cash_state=cash_state,
            safety_state=safety_state,
            risk_state=risk_state,
        )
        decision = str(one_lot_authority.get("decision") or "")
        if decision == "ADMIT_ONE_LOT":
            top_quantity = trading_unit
            status = "PASS"
            reasons = ["minimum_executable_one_lot_authority_admitted"]
            target_weight = _number(one_lot_authority.get("one_lot_weight"), effective_target_weight)
        elif decision == "REVIEW_REQUIRED":
            status = "REVIEW_REQUIRED"
            reasons = list(one_lot_authority.get("reason_codes") or ["minimum_executable_one_lot_authority_review_required"])
        else:
            status = "BLOCK"
            reasons = ["lot_minimum_exceeds_quality_authorized_target", *list(one_lot_authority.get("reason_codes") or [])]
    elif top_quantity <= 0 and target_weight is not None and target_weight > 0:
        top_quantity = trading_unit
        reasons = ["pc_target_weight_positive_but_below_one_lot_preserves_legacy_first_lot"]
    elif top_quantity <= 0:
        status = "REVIEW_REQUIRED"
        top_quantity = trading_unit
        reasons = ["missing_pc_target_quantity_or_weight_authority"]

    return {
        "schema_version": "pc_entry_target_magnitude_authority.v1",
        "status": status,
        "owner": "PORTFOLIO_CONSTRUCTION",
        "semantic_type": semantic_type,
        "target_weight": target_weight,
        "pre_quality_base_target_weight": _number(row.get("pre_quality_base_target_weight"), target_weight),
        "quality_authorized_target_weight": effective_target_weight,
        "quality_target_upper_bound_enforced": quality_enforced,
        "pc_target_executable_quantity": int(top_quantity),
        "trading_unit": trading_unit,
        "minimum_executable_one_lot_authority": one_lot_authority,
        "source_observations": sources,
        "reason_codes": reasons,
        "hard_upper_bound": True,
        "future_information_used": False,
        "historical_outcome_used": False,
    }


def _is_sublot_quality_zeroed_entry(row: Mapping[str, Any]) -> bool:
    target_weight = _number(row.get("target_weight"), None)
    if target_weight is None or target_weight > 0:
        return False
    quality_bound = _quality_authorized_entry_target_weight(row)
    if quality_bound is None or quality_bound <= 0:
        return False
    if not _entry_quality_ceiling_enforced(row, quality_bound):
        return False
    resolution = row.get("target_weight_resolution") if isinstance(row.get("target_weight_resolution"), Mapping) else {}
    zero_reasons = {
        str(row.get("zero_weight_reason") or ""),
        str(row.get("lot_first_rebatch_skip_reason") or ""),
        str(resolution.get("zero_weight_reason") or ""),
    }
    lot_reallocation = resolution.get("lot_aware_final_reallocation") if isinstance(resolution.get("lot_aware_final_reallocation"), Mapping) else {}
    zero_reasons.add(str(lot_reallocation.get("blocker_reason") or ""))
    lot_resolution = row.get("phase29_l19_lot_resolution") if isinstance(row.get("phase29_l19_lot_resolution"), Mapping) else {}
    zero_reasons.add(str(lot_resolution.get("blocked_reason") or ""))
    zero_reasons.add(str(lot_resolution.get("blocker_reason") or ""))
    return "lot_minimum_exceeds_quality_authorized_target" in zero_reasons


def _entry_quality_ceiling_enforced(row: Mapping[str, Any], quality_authorized_target_weight: float | None) -> bool:
    if quality_authorized_target_weight is None:
        return False
    if bool(row.get("quality_target_upper_bound_enforced")):
        return True
    resolution = row.get("target_weight_resolution") if isinstance(row.get("target_weight_resolution"), Mapping) else {}
    if bool(resolution.get("quality_target_upper_bound_enforced")):
        return True
    pre_quality_base = _number(row.get("pre_quality_base_target_weight"), None)
    if pre_quality_base is None:
        pre_quality_base = _number(resolution.get("pre_quality_base_target_weight"), None)
    if pre_quality_base is None:
        for adjustment in resolution.get("adjustments") or []:
            if not isinstance(adjustment, Mapping):
                continue
            if str(adjustment.get("authority") or "") != "ADAPTIVE_BUY_QUALITY_AUTHORITY":
                continue
            pre_quality_base = _number(
                adjustment.get("pre_quality_base_target_weight")
                if "pre_quality_base_target_weight" in adjustment
                else adjustment.get("pre_quality_base_weight"),
                None,
            )
            if pre_quality_base is not None:
                break
    if pre_quality_base is None:
        return False
    return quality_authorized_target_weight < pre_quality_base - CASH_CONFLICT_TOLERANCE


def _minimum_executable_one_lot_authority(
    row: Mapping[str, Any],
    *,
    semantic_type: str,
    quality_authorized_target_weight: float,
    pre_quality_base_target_weight: float | None,
    portfolio_value: float,
    reference_price: float,
    trading_unit: int,
    cash_state: Mapping[str, Any],
    safety_state: Mapping[str, Any],
    risk_state: Mapping[str, Any],
) -> dict[str, Any]:
    one_lot_notional = round(reference_price * trading_unit, 6) if reference_price > 0 and trading_unit > 0 else 0.0
    one_lot_weight = (one_lot_notional / portfolio_value) if portfolio_value > 0 else None
    cap_authority = row.get("effective_single_name_cap_authority") if isinstance(row.get("effective_single_name_cap_authority"), Mapping) else {}
    strategy_cap = _number(cap_authority.get("strategy_single_name_cap") or row.get("strategy_single_name_cap") or row.get("single_name_cap"), None)
    safety_cap = _number(cap_authority.get("safety_hard_cap") or row.get("safety_hard_cap") or row.get("safety_hard_cap_weight"), None)
    effective_cap = _number(cap_authority.get("effective_single_name_cap") or row.get("single_name_cap"), None)
    entry_action = _state(row, "entry_admission_action", "quality_action", "buy_quality_action", default="")
    entry_state = _state(row, "entry_admission_state", default="")
    quality_action = _state(row, "quality_action", "buy_quality_action", default="")
    opportunity_quality = marginal_capital_value.classify_opportunity_quality(_row_for_quality(row, semantic_type), business_date=str(row.get("business_date") or ""))
    opportunity_class = str(opportunity_quality.get("canonical_opportunity_quality_class") or "")
    cash_status = str(cash_state.get("cash_source_status") or "PASS").upper()
    available_cash = _number(cash_state.get("available_cash"), 0.0) or 0.0
    risk_status = _state(risk_state, "status", "risk_pacing_status", "decision", default="")
    decision = "ADMIT_ONE_LOT"
    reason_codes: list[str] = ["minimum_executable_one_lot_evaluated"]
    review_reasons: list[str] = []
    block_reasons: list[str] = []

    if semantic_type not in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"}:
        block_reasons.append("minimum_one_lot_not_applicable_to_semantic_type")
    if one_lot_weight is None or one_lot_weight <= 0 or one_lot_notional <= 0:
        review_reasons.append("missing_one_lot_weight_or_notional")
    if quality_authorized_target_weight <= 0:
        block_reasons.append("quality_authorized_target_not_positive")
    if bool(row.get("current_position")) or int(_number(row.get("current_quantity") or row.get("quantity"), 0) or 0) > 0:
        block_reasons.append("minimum_one_lot_current_quantity_not_zero")
    if entry_action in {"REJECT", "REJECT_BUY_NEW", "BUY_REJECTED", "BUY_WAIT", "TEMPORARY_BUY_INELIGIBLE", "REVIEW_REQUIRED"}:
        block_reasons.append(f"entry_admission_blocks_one_lot:{entry_action}")
    if quality_action in {"REJECT", "BUY_REJECTED", "BUY_WAIT", "REVIEW_REQUIRED"}:
        block_reasons.append(f"buy_quality_blocks_one_lot:{quality_action}")
    if entry_state in {"OVERHEATED_DECELERATING_ENTRY", "REVERSAL_RISK_ENTRY"}:
        block_reasons.append(f"entry_state_blocks_one_lot:{entry_state}")
    if cap_authority and cap_authority.get("status") != "PASS":
        review_reasons.extend(str(reason) for reason in cap_authority.get("reason_codes") or ["effective_single_name_cap_review_required"])
    if safety_state.get("blocked") is True:
        block_reasons.append("safety_blocked")
    if risk_state.get("blocked") is True or risk_status in {"BLOCK", "BLOCKED", "FAIL", "HALT"}:
        block_reasons.append("risk_pacing_blocked")
    if cash_status != "PASS":
        review_reasons.append(str(cash_state.get("cash_source_reason") or "cash_source_review_required"))
    elif one_lot_notional > available_cash:
        block_reasons.append("insufficient_cash_for_minimum_one_lot")
    if effective_cap is None:
        review_reasons.append("missing_effective_single_name_cap_authority")
    elif one_lot_weight is not None and one_lot_weight > effective_cap + CASH_CONFLICT_TOLERANCE:
        block_reasons.append("minimum_one_lot_exceeds_effective_single_name_cap")
    if safety_cap is not None and one_lot_weight is not None and one_lot_weight > safety_cap + CASH_CONFLICT_TOLERANCE:
        block_reasons.append("minimum_one_lot_exceeds_safety_hard_cap")
    if opportunity_class in {"INSUFFICIENT", "BLOCKED", ""}:
        review_reasons.append("minimum_one_lot_opportunity_quality_insufficient")
    elif opportunity_class not in {"STRONG", "COMPARABLE_HIGH", "COMPARABLE_MARGINAL"}:
        block_reasons.append(f"minimum_one_lot_opportunity_quality_not_supportive:{opportunity_class}")
    elif (
        opportunity_class == "COMPARABLE_MARGINAL"
        and pre_quality_base_target_weight is not None
        and one_lot_weight is not None
        and one_lot_weight > float(pre_quality_base_target_weight) + CASH_CONFLICT_TOLERANCE
    ):
        block_reasons.append("minimum_one_lot_exceeds_pre_quality_base_target")

    if review_reasons:
        decision = "REVIEW_REQUIRED"
        reason_codes.extend(review_reasons)
    elif block_reasons:
        decision = "BLOCK"
        reason_codes.extend(block_reasons)
    else:
        reason_codes.append("minimum_executable_one_lot_admitted_by_bounded_pc_authority")
        if opportunity_class == "COMPARABLE_MARGINAL":
            reason_codes.append("comparable_marginal_one_lot_representable_deferred_to_common_frontier")
        else:
            reason_codes.append(f"opportunity_quality_supports_one_lot:{opportunity_class}")

    overshoot_weight = round(max((one_lot_weight or 0.0) - quality_authorized_target_weight, 0.0), 10)
    one_lot_to_target_ratio = round((one_lot_weight or 0.0) / quality_authorized_target_weight, 6) if quality_authorized_target_weight > 0 and one_lot_weight else None
    target_to_one_lot_ratio = round(quality_authorized_target_weight / one_lot_weight, 6) if one_lot_weight and one_lot_weight > 0 else None
    return {
        "schema_version": "minimum_executable_one_lot_authority.v1",
        "authority_type": "PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION",
        "owner": "PORTFOLIO_CONSTRUCTION",
        "decision": decision,
        "decision_alias": "ADMIT" if decision == "ADMIT_ONE_LOT" else decision,
        "reason": "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED" if decision == "ADMIT_ONE_LOT" else "MINIMUM_EXECUTABLE_ONE_LOT_NOT_ADMITTED",
        "semantic_type": semantic_type,
        "intent": "BUY_NEW" if semantic_type == "NEW_FIRST_LOT" else "REENTRY",
        "symbol": _symbol(row),
        "current_quantity": int(_number(row.get("current_quantity") or row.get("quantity"), 0) or 0),
        "quality_authorized_target_weight": round(quality_authorized_target_weight, 10),
        "pre_quality_base_target_weight": pre_quality_base_target_weight,
        "quality_allocation_adjustment": _number(row.get("quality_allocation_adjustment"), None),
        "one_lot_weight": round(one_lot_weight or 0.0, 10),
        "one_lot_notional": one_lot_notional,
        "trading_unit": trading_unit,
        "overshoot_weight": overshoot_weight,
        "target_to_one_lot_ratio": target_to_one_lot_ratio,
        "one_lot_to_target_ratio": one_lot_to_target_ratio,
        "projected_post_trade_weight": round(one_lot_weight or 0.0, 10),
        "buy_quality_evidence": {
            "quality_action": quality_action,
            "quality_score": _number(row.get("quality_score") or row.get("buy_quality_score"), None),
            "quality_band": str(row.get("quality_band") or ""),
        },
        "opportunity_rank_evidence": {
            "input_opportunity_rank": _number(row.get("input_opportunity_rank") or row.get("opportunity_rank") or row.get("opportunity_buy_rank"), None),
            "runtime_opportunity_score": _number(row.get("runtime_opportunity_score") or row.get("opportunity_score"), None),
            "canonical_opportunity_quality_class": opportunity_class,
            "reason_codes": list(opportunity_quality.get("opportunity_quality_reason_codes") or []),
        },
        "entry_state_evidence": {
            "entry_admission_action": entry_action,
            "entry_admission_state": entry_state,
            "entry_admission_evidence_sufficiency": _state(row, "entry_admission_evidence_sufficiency", default=""),
        },
        "regime_risk_evidence": {
            "market_context_state": risk_state.get("market_context_state", ""),
            "risk_pacing_state": risk_state.get("risk_pacing_state", ""),
        },
        "strategy_cap_status": {
            "status": "PASS" if effective_cap is not None and one_lot_weight is not None and one_lot_weight <= effective_cap + CASH_CONFLICT_TOLERANCE else "BLOCK_OR_REVIEW",
            "strategy_cap": strategy_cap,
            "effective_single_name_cap": effective_cap,
        },
        "safety_cap_status": {
            "status": "PASS" if safety_cap is None or (one_lot_weight is not None and one_lot_weight <= safety_cap + CASH_CONFLICT_TOLERANCE) else "BLOCK",
            "safety_cap": safety_cap,
            "safety_blocked": bool(safety_state.get("blocked")),
        },
        "risk_pacing_status": {
            "status": "BLOCK" if risk_state.get("blocked") is True else "PASS",
            "risk_pacing_state": risk_state.get("risk_pacing_state", ""),
        },
        "cash_budget_status": {
            "status": "PASS" if cash_status == "PASS" and one_lot_notional <= available_cash else ("REVIEW_REQUIRED" if cash_status != "PASS" else "BLOCK"),
            "available_cash": available_cash,
            "one_lot_notional": one_lot_notional,
        },
        "source_lineage": _lineage(row),
        "reason_codes": sorted(set(reason_codes)),
        "future_information_used": False,
        "historical_outcome_used": False,
    }


def _quality_authorized_entry_target_weight(row: Mapping[str, Any]) -> float | None:
    direct = _number(row.get("quality_authorized_target_weight"), None)
    if direct is not None:
        return max(direct, 0.0)
    resolution = row.get("target_weight_resolution") if isinstance(row.get("target_weight_resolution"), Mapping) else {}
    resolved = _number(resolution.get("quality_authorized_target_weight"), None)
    if resolved is not None:
        return max(resolved, 0.0)
    for adjustment in resolution.get("adjustments") or []:
        if not isinstance(adjustment, Mapping):
            continue
        if str(adjustment.get("authority") or "") != "ADAPTIVE_BUY_QUALITY_AUTHORITY":
            continue
        weight = _number(adjustment.get("post_quality_target_weight"), None)
        if weight is not None:
            return max(weight, 0.0)
    return None


def _weight_to_trading_unit_quantity(
    weight: float | None,
    *,
    portfolio_value: float,
    reference_price: float,
    trading_unit: int,
) -> int | None:
    if weight is None:
        return None
    if weight <= 0 or portfolio_value <= 0 or reference_price <= 0 or trading_unit <= 0:
        return 0
    raw = int((weight * portfolio_value) / reference_price)
    return (raw // trading_unit) * trading_unit


def _entry_target_quantity_sources(row: Mapping[str, Any], *, ps_row: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    sources: list[tuple[str, Mapping[str, Any]]] = []
    for role, payload in (
        ("pc.phase29_l19_lot_resolution", row.get("phase29_l19_lot_resolution")),
        ("position_sizing.phase29_l19_lot_resolution", ps_row.get("phase29_l19_lot_resolution")),
        ("pc.lot_resolution", row.get("lot_resolution")),
        ("position_sizing.lot_resolution", ps_row.get("lot_resolution")),
    ):
        if not isinstance(payload, Mapping):
            continue
        sources.append((role, payload))
        nested = payload.get("pc_positive_executable_quantity_authority")
        if isinstance(nested, Mapping):
            sources.append((f"{role}.pc_positive_executable_quantity_authority", nested))
    return sources


def _lot_increment_quantity(row: Mapping[str, Any], *, ps_row: Mapping[str, Any], trading_unit: int) -> int:
    increment_quantity = int(_number(row.get("increment_quantity") or ps_row.get("transaction_quantity_candidate"), trading_unit) or trading_unit)
    if increment_quantity <= 0:
        increment_quantity = trading_unit
    return max(trading_unit, (increment_quantity // trading_unit) * trading_unit)


def _row_with_effective_cap(row: Mapping[str, Any], *, cap_state: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(row)
    row_cap = _number(copied.get("single_name_cap") or copied.get("max_position_weight") or copied.get("strategy_single_name_cap"), None)
    selected = dict(cap_state)
    if selected.get("status") == "PASS":
        copied["single_name_cap"] = selected.get("effective_single_name_cap")
    elif row_cap is not None:
        selected = {
            "status": "PASS",
            "authority_type": "EFFECTIVE_SINGLE_NAME_CONCENTRATION_CAP_AUTHORITY",
            "strategy_single_name_cap": row_cap,
            "safety_hard_cap": None,
            "effective_single_name_cap": row_cap,
            "cap_source_role": "portfolio_construction.member.single_name_cap",
            "reason_codes": ["effective_single_name_cap_resolved_from_member_cap"],
            "future_information_used": False,
            "historical_outcome_used": False,
        }
        copied["single_name_cap"] = row_cap
    copied["effective_single_name_cap_authority"] = selected
    return copied


def _effective_single_name_cap_state(
    *,
    portfolio_construction_payload: Mapping[str, Any],
    position_sizing_payload: Mapping[str, Any],
    safety_payload: Mapping[str, Any],
) -> dict[str, Any]:
    strategy_observations = _cap_observations(
        ("single_name_weight_cap", "strategy_maximum_position_weight", "strategy_single_name_cap"),
        portfolio_construction_payload,
        position_sizing_payload,
        safety_payload,
    )
    safety_observations = _cap_observations(
        ("safety_maximum_position_weight", "maximum_position_weight", "max_position_weight"),
        position_sizing_payload,
        safety_payload,
    )
    effective_observations = _cap_observations(("effective_maximum_position_weight",), position_sizing_payload)
    strategy_cap = _consistent_cap(strategy_observations)
    safety_cap = _consistent_cap(safety_observations)
    effective_cap = _consistent_cap(effective_observations)
    reasons: list[str] = []
    if strategy_cap is None:
        reasons.append("missing_strategy_single_name_cap_authority")
    if safety_cap is None and effective_cap is None:
        reasons.append("missing_safety_or_effective_single_name_cap_authority")
    if strategy_cap is not None and safety_cap is not None and effective_cap is not None:
        expected_effective = min(strategy_cap, safety_cap)
        if abs(expected_effective - effective_cap) > CASH_CONFLICT_TOLERANCE:
            reasons.append("conflicting_effective_single_name_cap_authority")
    if _has_conflicting_caps(strategy_observations):
        reasons.append("ambiguous_strategy_single_name_cap_authority")
    if _has_conflicting_caps(safety_observations):
        reasons.append("ambiguous_safety_single_name_cap_authority")
    if _has_conflicting_caps(effective_observations):
        reasons.append("ambiguous_effective_single_name_cap_authority")
    if reasons:
        return {
            "status": "REVIEW_REQUIRED",
            "authority_type": "EFFECTIVE_SINGLE_NAME_CONCENTRATION_CAP_AUTHORITY",
            "strategy_single_name_cap": strategy_cap,
            "safety_hard_cap": safety_cap,
            "effective_single_name_cap": None,
            "source_observations": [*strategy_observations, *safety_observations, *effective_observations],
            "reason_codes": sorted(set(reasons)),
            "future_information_used": False,
            "historical_outcome_used": False,
        }
    selected_effective = effective_cap if effective_cap is not None else min(strategy_cap, safety_cap)  # type: ignore[arg-type]
    return {
        "status": "PASS",
        "authority_type": "EFFECTIVE_SINGLE_NAME_CONCENTRATION_CAP_AUTHORITY",
        "strategy_single_name_cap": strategy_cap,
        "safety_hard_cap": safety_cap,
        "effective_single_name_cap": selected_effective,
        "cap_source_role": "min(strategy_single_name_cap,safety_hard_cap)",
        "source_observations": [*strategy_observations, *safety_observations, *effective_observations],
        "reason_codes": ["effective_single_name_cap_resolved"],
        "future_information_used": False,
        "historical_outcome_used": False,
    }


def _cap_observations(fields: Sequence[str], *payloads: Mapping[str, Any]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for payload_index, payload in enumerate(payloads, start=1):
        for field in fields:
            value = _number(payload.get(field), None)
            if value is None:
                continue
            observations.append(
                {
                    "field": field,
                    "value": value,
                    "priority": payload_index,
                }
            )
    return observations


def _consistent_cap(observations: Sequence[Mapping[str, Any]]) -> float | None:
    if not observations:
        return None
    top_priority = min(int(item.get("priority") or 0) for item in observations)
    values = [float(item["value"]) for item in observations if int(item.get("priority") or 0) == top_priority]
    return values[0] if values else None


def _has_conflicting_caps(observations: Sequence[Mapping[str, Any]]) -> bool:
    if not observations:
        return False
    top_priority = min(int(item.get("priority") or 0) for item in observations)
    values = [float(item["value"]) for item in observations if int(item.get("priority") or 0) == top_priority]
    return any(abs(value - values[0]) > CASH_CONFLICT_TOLERANCE for value in values[1:])


def _cash_candidate(
    *,
    business_date: str,
    session: str,
    cash_state: Mapping[str, Any],
    safety_state: Mapping[str, Any],
    risk_state: Mapping[str, Any],
) -> dict[str, Any]:
    cash_source_status = str(cash_state.get("cash_source_status") or "PASS").upper()
    desirability_class = "CASH_PREFERRED" if cash_state.get("cash_preferred") is True else "CASH_AVAILABLE"
    candidate = {
        "business_date": business_date,
        "session": session,
        "symbol": "CASH",
        "position_campaign_id": "",
        "semantic_type": "CASH_OPTIONALITY",
        "candidate_id": "",
        "increment_index": 0,
        "pre_quantity": 0,
        "post_quantity": 0,
        "increment_quantity": 0,
        "pre_weight": None,
        "post_weight": None,
        "increment_weight": None,
        "reference_price": None,
        "increment_notional": _number(cash_state.get("comparison_notional")),
        "source_pm_decision_id": "",
        "source_candidate_id": "",
        "source_pc_evidence_ids": [],
        "desirability": {
            "category": "DESIRABILITY",
            "comparison_class": desirability_class,
            "components": {
                "cash_optionality": cash_state.get("cash_optionality", "AVAILABLE"),
                "market_context": risk_state.get("market_context_state", ""),
                "risk_pacing": risk_state.get("risk_pacing_state", ""),
            },
            "reason_codes": ["cash_first_class_alternative"],
            "raw_evidence": _strip_forbidden(cash_state),
        },
        "risk_modifiers": {
            "category": "RISK_MODIFIER",
            "market_context": risk_state.get("market_context_state", ""),
            "risk_pacing": risk_state.get("risk_pacing_state", ""),
            "safety_status": safety_state.get("status", ""),
        },
        "feasibility": {
            "category": "FEASIBILITY",
            "status": "PASS" if cash_source_status == "PASS" else "REVIEW_REQUIRED",
            "reason_codes": ["cash_is_always_feasible_as_optionality"] if cash_source_status == "PASS" else [str(cash_state.get("cash_source_reason") or "cash_source_review_required")],
            "available_cash": _number(cash_state.get("available_cash"), 0.0) or 0.0,
        },
        "constraints": {
            "category": "CONSTRAINT",
            "status": "PASS",
            "reason_codes": [],
        },
        "observability": {
            "category": "OBSERVABILITY",
            "status": "PASS" if cash_source_status == "PASS" else "REVIEW_REQUIRED",
            "reason_codes": [] if cash_source_status == "PASS" else [str(cash_state.get("cash_source_reason") or "cash_source_review_required")],
        },
        "lineage": {
            "source_artifacts": [item.get("path") for item in cash_state.get("cash_source_lineage", []) if item.get("path")],
            "source_hashes": [item.get("sha256") for item in cash_state.get("cash_source_lineage", []) if item.get("sha256")],
            "future_information_used": False,
            "cash_source_lineage": list(cash_state.get("cash_source_lineage", [])),
        },
        "diminishing_marginal_context": {},
        "comparison_class": desirability_class,
        "comparison_representation": COMPARISON_REPRESENTATION,
        "strongest_alternative": None,
        "cash_comparison": {"self": True, "status": "CASH_CANDIDATE"},
        "shadow_disposition": "PENDING_COMPARISON",
        "reason_codes": ["cash_first_class_alternative"],
        "stable_tie_order": 999999,
        "hypothetical_only": True,
        "portfolio_state_mutated": False,
        "production_authority": False,
    }
    candidate["candidate_id"] = _candidate_id(candidate)
    return candidate


def _desirability(row: Mapping[str, Any], *, semantic_type: str, business_date: str) -> dict[str, Any]:
    opportunity_quality = marginal_capital_value.classify_opportunity_quality(_row_for_quality(row, semantic_type), business_date=business_date)
    comparison_class = str(opportunity_quality.get("canonical_opportunity_quality_class") or "INSUFFICIENT")
    if semantic_type == "REENTRY_FIRST_LOT" and _state(row, "reentry_recovery_status", "reentry_recovery", default="") in {"PASS", "RECOVERED"}:
        reason = "reentry_recovery_evidence_present"
    elif semantic_type == "ADD_NEXT_LOT":
        reason = "pm_add_next_lot_candidate"
    else:
        reason = "new_first_lot_candidate"
    return {
        "category": "DESIRABILITY",
        "status": "PASS" if comparison_class not in {"INSUFFICIENT", "BLOCKED"} else "REVIEW_REQUIRED",
        "comparison_class": comparison_class,
        "components": {
            "opportunity": _number(row.get("runtime_opportunity_score") or row.get("opportunity_score")),
            "rank": _number(row.get("input_opportunity_rank") or row.get("opportunity_rank") or row.get("opportunity_buy_rank")),
            "quality": _number(row.get("quality_score") or row.get("buy_quality_score")),
            "continuation": _state(row, "same_campaign_continuation_status", "continuation_status", default=""),
            "recovery": _state(row, "reentry_recovery_status", "reentry_recovery", default=""),
            "incremental_value": _state(row, "incremental_investment_value_state", "add_incremental_investment_value_state", default=""),
            "cash_opportunity_cost": _state(row, "opportunity_cost_status", "add_opportunity_cost_status", default=""),
        },
        "reason_codes": [reason, *list(opportunity_quality.get("opportunity_quality_reason_codes") or [])],
        "raw_evidence": marginal_capital_value.source_evidence(row),
    }


def _row_for_quality(row: Mapping[str, Any], semantic_type: str) -> dict[str, Any]:
    copied = dict(row)
    if semantic_type == "ADD_NEXT_LOT":
        copied["current_position"] = True
        copied["pm_action"] = "ADD"
        copied.setdefault("membership_intent", "RETAIN")
        return copied
    copied["current_position"] = False
    copied["membership_intent"] = "ADD_CANDIDATE"
    copied.setdefault("pm_action", "NEW")
    return copied


def _feasibility(
    *,
    reference_price: float,
    increment_quantity: int,
    increment_notional: float,
    cash_state: Mapping[str, Any],
    post_weight: float,
    single_name_cap: float | None,
    cap_authority: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    status = "PASS"
    cash_source_status = str(cash_state.get("cash_source_status") or "PASS").upper()
    available_cash = _number(cash_state.get("available_cash"), 0.0) or 0.0
    if cash_source_status != "PASS":
        status = "REVIEW_REQUIRED"
        reasons.append(str(cash_state.get("cash_source_reason") or "cash_source_review_required"))
    if reference_price <= 0 or increment_quantity <= 0:
        status = "FAIL"
        reasons.append("lot_infeasible_missing_price_or_quantity")
    if cash_source_status == "PASS" and increment_notional > available_cash:
        status = "FAIL"
        reasons.append("insufficient_cash")
    if cap_authority and cap_authority.get("status") != "PASS":
        status = "REVIEW_REQUIRED"
        reasons.extend(str(reason) for reason in cap_authority.get("reason_codes") or ["effective_single_name_cap_review_required"])
    elif single_name_cap is None:
        status = "REVIEW_REQUIRED"
        reasons.append("missing_effective_single_name_cap_authority")
    elif post_weight > single_name_cap:
        status = "FAIL"
        reasons.append("cap_blocked")
    return {
        "category": "FEASIBILITY",
        "status": status,
        "reason_codes": reasons or ["feasible"],
        "available_cash": available_cash,
        "reference_price": reference_price,
        "increment_notional": increment_notional,
        "post_weight": round(post_weight, 10),
        "single_name_cap": single_name_cap,
        "effective_single_name_cap": single_name_cap,
        "effective_single_name_cap_authority": dict(cap_authority),
    }


def _constraints(
    row: Mapping[str, Any],
    *,
    semantic_type: str,
    safety_state: Mapping[str, Any],
    risk_state: Mapping[str, Any],
    feasibility: Mapping[str, Any],
    production_admission: Mapping[str, Any],
    position_campaign_id: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    status = "PASS"
    if feasibility.get("status") == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
        reasons.extend(str(reason) for reason in feasibility.get("reason_codes") or [])
    elif feasibility.get("status") != "PASS":
        status = "BLOCK"
        reasons.extend(str(reason) for reason in feasibility.get("reason_codes") or [])
    if semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"}:
        admission_status = str(production_admission.get("status") or "").upper()
        if admission_status == "REVIEW_REQUIRED":
            status = "REVIEW_REQUIRED"
            reasons.extend(str(reason) for reason in production_admission.get("reason_codes") or [])
        elif admission_status != "PASS":
            status = "BLOCK"
            reasons.extend(str(reason) for reason in production_admission.get("reason_codes") or [])
        target_magnitude = row.get("pc_target_magnitude_authority") if isinstance(row.get("pc_target_magnitude_authority"), Mapping) else {}
        target_magnitude_status = str(target_magnitude.get("status") or "").upper()
        if admission_status == "PASS" and target_magnitude_status == "REVIEW_REQUIRED":
            status = "REVIEW_REQUIRED"
            reasons.extend(str(reason) for reason in target_magnitude.get("reason_codes") or [])
        elif admission_status == "PASS" and target_magnitude_status == "BLOCK":
            status = "BLOCK"
            reasons.extend(str(reason) for reason in target_magnitude.get("reason_codes") or [])
    if safety_state.get("blocked") is True or _state(row, "safety_status", "safety_decision", default="") in {"BLOCK", "BLOCKED", "FAIL"}:
        status = "BLOCK"
        reasons.append("safety_blocked")
    if risk_state.get("blocked") is True or _state(row, "risk_pacing_status", "risk_pacing_decision", default="") in {"BLOCK", "BLOCKED", "FAIL"}:
        status = "BLOCK"
        reasons.append("risk_pacing_blocked")
    if semantic_type == "ADD_NEXT_LOT" and not position_campaign_id:
        status = "REVIEW_REQUIRED"
        reasons.append("stale_or_missing_campaign_identity")
    if semantic_type == "ADD_NEXT_LOT" and _state(row, "no_loss_averaging_status", default="") in {"FAIL", "BLOCK", "BLOCKED"}:
        status = "BLOCK"
        reasons.append("no_loss_averaging_rejection")
    return {
        "category": "CONSTRAINT",
        "status": status,
        "reason_codes": sorted(set(reasons)),
    }


def _production_first_lot_admission(row: Mapping[str, Any], *, semantic_type: str) -> dict[str, Any]:
    if semantic_type == "ADD_NEXT_LOT":
        return {
            "category": "PRODUCTION_ADMISSION",
            "status": "NOT_APPLICABLE",
            "authority": "ADD_NEXT_LOT_PM_CAMPAIGN_AND_PC_ADD_CONTRACT",
            "reason_codes": ["add_next_lot_not_gated_by_new_first_lot_admission"],
            "future_information_used": False,
            "historical_outcome_used": False,
        }
    if semantic_type not in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"}:
        return {
            "category": "PRODUCTION_ADMISSION",
            "status": "NOT_APPLICABLE",
            "authority": "NON_SECURITY_OR_UNKNOWN_SEMANTIC_TYPE",
            "reason_codes": ["production_admission_not_applicable"],
            "future_information_used": False,
            "historical_outcome_used": False,
        }

    reasons: list[str] = []
    target_weight = _number(row.get("target_weight"), None)
    membership = str(row.get("membership_intent") or "").upper()
    resolution = row.get("target_weight_resolution") if isinstance(row.get("target_weight_resolution"), Mapping) else {}
    resolution_status = str(resolution.get("status") or "").upper()
    zero_weight_reason = str(resolution.get("zero_weight_reason") or row.get("zero_weight_reason") or "")

    if target_weight is None:
        return {
            "category": "PRODUCTION_ADMISSION",
            "status": "REVIEW_REQUIRED",
            "authority": "PC_TARGET_WEIGHT_PRODUCTION_ADMISSION",
            "target_weight": None,
            "membership_intent": membership,
            "reason_codes": ["missing_pc_target_weight_production_admission"],
            "future_information_used": False,
            "historical_outcome_used": False,
        }
    if resolution_status and resolution_status not in {"PASS", "NOT_APPLICABLE"}:
        reasons.append("pc_target_weight_resolution_not_pass")
    if membership in {"EXCLUDE", "AVOID", "NOT_SELECTED", "INELIGIBLE"}:
        reasons.append("pc_first_lot_non_deployable_membership")
    if target_weight <= 0.0:
        reasons.append("pc_first_lot_target_weight_zero")
    if zero_weight_reason:
        reasons.append(f"pc_first_lot_zero_weight_reason_{zero_weight_reason}")

    status = "BLOCK" if reasons else "PASS"
    return {
        "category": "PRODUCTION_ADMISSION",
        "status": status,
        "authority": "PC_TARGET_WEIGHT_PRODUCTION_ADMISSION",
        "semantic_type": semantic_type,
        "target_weight": target_weight,
        "membership_intent": membership,
        "target_weight_resolution_status": resolution_status,
        "zero_weight_reason": zero_weight_reason,
        "reason_codes": sorted(set(reasons)) if reasons else ["pc_first_lot_positive_target_weight_admitted"],
        "future_information_used": False,
        "historical_outcome_used": False,
    }


def _observability(row: Mapping[str, Any], *, semantic_type: str, reference_price: float, portfolio_value: float) -> dict[str, Any]:
    reasons: list[str] = []
    if reference_price <= 0:
        reasons.append("missing_reference_price")
    if portfolio_value <= 0:
        reasons.append("missing_portfolio_value")
    if semantic_type == "ADD_NEXT_LOT" and not _campaign_id(row):
        reasons.append("missing_position_campaign_id")
    if semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"} and not (
        row.get("candidate_id") or row.get("opportunity_decision_id") or row.get("runtime_opportunity_score") is not None
    ):
        reasons.append("missing_candidate_or_opportunity_evidence")
    return {
        "category": "OBSERVABILITY",
        "status": "PASS" if not reasons else "REVIEW_REQUIRED",
        "reason_codes": reasons,
    }


def _risk_modifiers(row: Mapping[str, Any], *, risk_state: Mapping[str, Any], pre_weight: float, post_weight: float, single_name_cap: float | None) -> dict[str, Any]:
    headroom_before = max(single_name_cap - pre_weight, 0.0) if single_name_cap is not None else None
    headroom_after = max(single_name_cap - post_weight, 0.0) if single_name_cap is not None else None
    return {
        "category": "RISK_MODIFIER",
        "current_weight": round(pre_weight, 10),
        "post_lot_weight": round(post_weight, 10),
        "single_name_cap": single_name_cap,
        "headroom_before": round(headroom_before, 10) if headroom_before is not None else None,
        "headroom_after": round(headroom_after, 10) if headroom_after is not None else None,
        "market_context": risk_state.get("market_context_state", ""),
        "risk_pacing": risk_state.get("risk_pacing_state", ""),
        "downside": _state(row, "downside_status", "strategy_intelligence_downside_risk_status", default=""),
    }


def _diminishing_context(
    *,
    semantic_type: str,
    increment_index: int,
    pre_weight: float,
    post_weight: float,
    single_name_cap: float | None,
    cash_before: float,
    increment_notional: float,
) -> dict[str, Any]:
    if semantic_type not in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT", "ADD_NEXT_LOT"}:
        return {"status": "NOT_APPLICABLE"}
    sources = [
        "increased_initial_entry_allocation" if semantic_type in {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT"} else "increased_single_name_concentration",
        "reduced_remaining_headroom",
        "reduced_cash_optionality",
    ]
    return {
        "status": "OBSERVED",
        "increment_index": increment_index,
        "diminishing_sources": sources,
        "headroom_before": round(max(single_name_cap - pre_weight, 0.0), 10) if single_name_cap is not None else None,
        "headroom_after": round(max(single_name_cap - post_weight, 0.0), 10) if single_name_cap is not None else None,
        "cash_before": round(cash_before, 6),
        "cash_after": round(max(cash_before - increment_notional, 0.0), 6),
        "fixed_penalty_coefficient_used": False,
    }


def _frontier_sort_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    disposition_rank = 0
    if candidate.get("semantic_type") == "CASH_OPTIONALITY" and candidate.get("comparison_class") == "CASH_PREFERRED":
        disposition_rank = -1
    elif (candidate.get("constraints") or {}).get("status") in {"BLOCK", "REVIEW_REQUIRED"}:
        disposition_rank = 20
    elif (candidate.get("observability") or {}).get("status") != "PASS":
        disposition_rank = 15
    return (
        disposition_rank,
        _class_rank(str(candidate.get("comparison_class") or "")),
        _number((candidate.get("desirability") or {}).get("components", {}).get("rank"), 999999) or 999999,
        int(candidate.get("increment_index") or 0),
        _semantic_rank(str(candidate.get("semantic_type") or "")),
        str(candidate.get("symbol") or ""),
        str(candidate.get("candidate_id") or ""),
    )


def _assign_frontier_dispositions(ordered: list[dict[str, Any]]) -> None:
    winner = next((row for row in ordered if _candidate_available(row)), None)
    runner_up = next((row for row in ordered if row is not winner and _candidate_available(row)), None)
    cash = next((row for row in ordered if row.get("semantic_type") == "CASH_OPTIONALITY"), None)
    for row in ordered:
        if not _candidate_available(row):
            row["shadow_disposition"] = _blocked_disposition(row)
        elif row is winner:
            row["shadow_disposition"] = "SHADOW_WINNER"
        else:
            row["shadow_disposition"] = "SHADOW_REJECTED_STRONGER_ALTERNATIVE"
        if winner and row is not winner:
            row["strongest_alternative"] = _alternative_ref(winner)
        elif runner_up:
            row["strongest_alternative"] = _alternative_ref(runner_up)
        if cash and row is not cash:
            row["cash_comparison"] = {
                "cash_candidate_id": cash.get("candidate_id"),
                "cash_disposition": cash.get("shadow_disposition"),
                "candidate_beats_cash": _frontier_sort_key(row) < _frontier_sort_key(cash),
            }


def _candidate_available(candidate: Mapping[str, Any]) -> bool:
    return (
        (candidate.get("constraints") or {}).get("status") == "PASS"
        and (candidate.get("feasibility") or {}).get("status") == "PASS"
        and (candidate.get("observability") or {}).get("status") == "PASS"
    )


def _blocked_disposition(candidate: Mapping[str, Any]) -> str:
    constraints = candidate.get("constraints") or {}
    feasibility = candidate.get("feasibility") or {}
    observability = candidate.get("observability") or {}
    reasons = set(str(reason) for reason in constraints.get("reason_codes") or feasibility.get("reason_codes") or [])
    pc_target = candidate.get("pc_target_magnitude_authority") if isinstance(candidate.get("pc_target_magnitude_authority"), Mapping) else {}
    one_lot_authority = pc_target.get("minimum_executable_one_lot_authority") if isinstance(pc_target.get("minimum_executable_one_lot_authority"), Mapping) else {}
    one_lot_decision = str(one_lot_authority.get("decision") or "").upper()
    if one_lot_decision == "REVIEW_REQUIRED":
        return "REVIEW_REQUIRED"
    if one_lot_decision == "BLOCK":
        one_lot_reasons = set(str(reason) for reason in one_lot_authority.get("reason_codes") or [])
        if any("cap" in reason for reason in one_lot_reasons):
            return "INFEASIBLE_CAP_BLOCKED"
        return "INFEASIBLE_LOT"
    if "pc_first_lot_target_weight_zero" in reasons or "pc_first_lot_non_deployable_membership" in reasons:
        return "INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED"
    if constraints.get("status") == "REVIEW_REQUIRED" or observability.get("status") == "REVIEW_REQUIRED":
        return "REVIEW_REQUIRED"
    if "safety_blocked" in reasons:
        return "INELIGIBLE_SAFETY_BLOCKED"
    if "risk_pacing_blocked" in reasons:
        return "INELIGIBLE_RISK_PACING_BLOCKED"
    if "cap_blocked" in reasons:
        return "INFEASIBLE_CAP_BLOCKED"
    if "insufficient_cash" in reasons:
        return "INFEASIBLE_INSUFFICIENT_CASH"
    if "lot_infeasible_missing_price_or_quantity" in reasons or "lot_minimum_exceeds_quality_authorized_target" in reasons:
        return "INFEASIBLE_LOT"
    if "no_loss_averaging_rejection" in reasons:
        return "INELIGIBLE_NO_LOSS_AVERAGING_REJECTION"
    return "INELIGIBLE_OR_INFEASIBLE"


def _frontier_result(ordered: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    winner = next((row for row in ordered if row.get("shadow_disposition") == "SHADOW_WINNER"), None)
    runner_up = next((row for row in ordered if row is not winner and _candidate_available(row)), None)
    cash = next((row for row in ordered if row.get("semantic_type") == "CASH_OPTIONALITY"), None)
    return {
        "frontier_id": _stable_hash({"business_date": ordered[0]["business_date"] if ordered else "", "candidate_ids": [row.get("candidate_id") for row in ordered]}),
        "candidate_count_total": len(ordered),
        "candidate_count_by_type": {semantic_type: sum(1 for row in ordered if row.get("semantic_type") == semantic_type) for semantic_type in SEMANTIC_TYPES},
        "eligible_candidate_count": sum(1 for row in ordered if _candidate_available(row)),
        "infeasible_candidate_count": sum(1 for row in ordered if not _candidate_available(row)),
        "winner_candidate_id": winner.get("candidate_id") if winner else None,
        "runner_up_candidate_id": runner_up.get("candidate_id") if runner_up else None,
        "strongest_rejected_alternative_id": runner_up.get("candidate_id") if runner_up else None,
        "cash_candidate_id": cash.get("candidate_id") if cash else None,
        "cash_frontier_disposition": cash.get("shadow_disposition") if cash else "MISSING",
        "comparison_representation": COMPARISON_REPRESENTATION,
        "winner_reason_codes": list(winner.get("reason_codes") or []) if winner else ["no_available_winner"],
    }


def _shadow_target_projection(ordered: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    accepted = [row for row in ordered if row.get("shadow_disposition") == "SHADOW_WINNER" and row.get("semantic_type") != "CASH_OPTIONALITY"]
    by_symbol: dict[str, list[Mapping[str, Any]]] = {}
    for row in accepted:
        by_symbol.setdefault(str(row.get("symbol") or ""), []).append(row)
    projections = []
    for symbol, rows in sorted(by_symbol.items()):
        final = max(rows, key=lambda row: int(row.get("increment_index") or 0))
        projections.append(
            {
                "symbol": symbol,
                "semantic_type": final.get("semantic_type"),
                "shadow_target_quantity": final.get("post_quantity"),
                "shadow_target_weight": final.get("post_weight"),
                "shadow_incremental_quantity": sum(int(row.get("increment_quantity") or 0) for row in rows),
                "shadow_incremental_weight": round(sum(float(row.get("increment_weight") or 0.0) for row in rows), 10),
                "accepted_shadow_candidate_ids": [row.get("candidate_id") for row in rows],
                "production_target_weight_unchanged": True,
                "production_order_unchanged": True,
            }
        )
    return {
        "status": "SHADOW_NON_AUTHORITATIVE",
        "projections": projections,
        "accepted_shadow_candidate_count": len(accepted),
        "production_target_weight_unchanged": True,
        "production_order_unchanged": True,
    }


def _released_capital_observation(portfolio_construction_payload: Mapping[str, Any], ordered: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    released = _number(portfolio_construction_payload.get("released_capital") or portfolio_construction_payload.get("released_notional"), 0.0) or 0.0
    winner = next((row for row in ordered if row.get("shadow_disposition") == "SHADOW_WINNER"), None)
    return {
        "status": "OBSERVABLE" if released > 0 else "NO_RELEASED_CAPITAL_OBSERVED",
        "released_capital_source": str(portfolio_construction_payload.get("released_capital_source") or "NONE"),
        "released_notional": released,
        "frontier_destination": winner.get("semantic_type") if winner else None,
        "destination_candidate_id": winner.get("candidate_id") if winner else None,
        "strongest_add_candidate_id": _first_type(ordered, "ADD_NEXT_LOT"),
        "strongest_new_candidate_id": _first_type(ordered, "NEW_FIRST_LOT"),
        "cash_disposition": next((row.get("shadow_disposition") for row in ordered if row.get("semantic_type") == "CASH_OPTIONALITY"), "MISSING"),
    }


def _metrics(ordered: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "frontier_candidate_count": len(ordered),
        "candidate_count_by_type": {semantic_type: sum(1 for row in ordered if row.get("semantic_type") == semantic_type) for semantic_type in SEMANTIC_TYPES},
        "add_next_lot_candidate_count": sum(1 for row in ordered if row.get("semantic_type") == "ADD_NEXT_LOT"),
        "add_lot_1_count": sum(1 for row in ordered if row.get("semantic_type") == "ADD_NEXT_LOT" and row.get("increment_index") == 1),
        "add_lot_2_count": sum(1 for row in ordered if row.get("semantic_type") == "ADD_NEXT_LOT" and row.get("increment_index") == 2),
        "add_lot_3_plus_count": sum(1 for row in ordered if row.get("semantic_type") == "ADD_NEXT_LOT" and int(row.get("increment_index") or 0) >= 3),
        "cash_win_count": sum(1 for row in ordered if row.get("semantic_type") == "CASH_OPTIONALITY" and row.get("shadow_disposition") == "SHADOW_WINNER"),
        "cap_blocked_count": sum(1 for row in ordered if row.get("shadow_disposition") == "INFEASIBLE_CAP_BLOCKED"),
        "safety_blocked_count": sum(1 for row in ordered if row.get("shadow_disposition") == "INELIGIBLE_SAFETY_BLOCKED"),
        "risk_pacing_blocked_count": sum(1 for row in ordered if row.get("shadow_disposition") == "INELIGIBLE_RISK_PACING_BLOCKED"),
        "insufficient_cash_count": sum(1 for row in ordered if row.get("shadow_disposition") == "INFEASIBLE_INSUFFICIENT_CASH"),
        "lot_infeasible_count": sum(1 for row in ordered if row.get("shadow_disposition") == "INFEASIBLE_LOT"),
        "review_required_count": sum(1 for row in ordered if row.get("shadow_disposition") == "REVIEW_REQUIRED"),
        "production_consumer_count": PRODUCTION_CONSUMER_COUNT,
    }


def _candidate_reason_codes(candidate: Mapping[str, Any]) -> list[str]:
    reasons = []
    for section in ("desirability", "production_admission", "feasibility", "constraints", "observability"):
        value = candidate.get(section)
        if isinstance(value, Mapping):
            reasons.extend(str(reason) for reason in value.get("reason_codes") or [])
    return sorted(set(reasons))


def _candidate_id(candidate: Mapping[str, Any]) -> str:
    identity = {
        "schema_version": SCHEMA_VERSION,
        "business_date": candidate.get("business_date"),
        "session": candidate.get("session"),
        "semantic_type": candidate.get("semantic_type"),
        "symbol": candidate.get("symbol"),
        "position_campaign_id": candidate.get("position_campaign_id"),
        "increment_index": candidate.get("increment_index"),
        "pre_quantity": candidate.get("pre_quantity"),
        "post_quantity": candidate.get("post_quantity"),
        "reference_price": candidate.get("reference_price"),
        "source_pm_decision_id": candidate.get("source_pm_decision_id"),
        "source_candidate_id": candidate.get("source_candidate_id"),
        "source_pc_evidence_ids": candidate.get("source_pc_evidence_ids"),
    }
    return "cmcf-" + _stable_hash(identity)[:24]


def _determinism_key(*, business_date: str, session: str, candidates: Sequence[Mapping[str, Any]], source_hashes: Mapping[str, Any]) -> str:
    return _stable_hash(
        {
            "schema_version": SCHEMA_VERSION,
            "business_date": business_date,
            "session": session,
            "candidate_ids": [row.get("candidate_id") for row in candidates],
            "source_hashes": dict(source_hashes),
        }
    )


def _first_type(ordered: Sequence[Mapping[str, Any]], semantic_type: str) -> str | None:
    row = next((item for item in ordered if item.get("semantic_type") == semantic_type), None)
    return str(row.get("candidate_id")) if row else None


def _alternative_ref(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "semantic_type": candidate.get("semantic_type"),
        "symbol": candidate.get("symbol"),
        "increment_index": candidate.get("increment_index"),
        "shadow_disposition": candidate.get("shadow_disposition"),
    }


def _portfolio_value(
    portfolio_construction_payload: Mapping[str, Any],
    position_sizing_payload: Mapping[str, Any] | None,
    pc_members: Sequence[Mapping[str, Any]],
) -> float:
    for value in (
        portfolio_construction_payload.get("portfolio_total_equity"),
        portfolio_construction_payload.get("portfolio_value"),
        portfolio_construction_payload.get("total_equity"),
        (position_sizing_payload or {}).get("portfolio_total_equity"),
        (position_sizing_payload or {}).get("portfolio_value"),
    ):
        number = _number(value)
        if number and number > 0:
            return number
    for row in pc_members:
        number = _number(row.get("portfolio_value") or row.get("portfolio_total_equity"))
        if number and number > 0:
            return number
    return 0.0


def _cash_state(portfolio_construction_payload: Mapping[str, Any], cash_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(cash_payload or {})
    if payload.get("cash_source_status") == "REVIEW_REQUIRED":
        return {
            **payload,
            "cash_preferred": bool(payload.get("cash_preferred") or portfolio_construction_payload.get("cash_winner") is True),
        }
    available = _cash_notional_from_mapping(payload)
    source_status = str(payload.get("cash_source_status") or "").upper()
    if available is None:
        available = _cash_notional_from_mapping(portfolio_construction_payload)
        source_status = "PASS" if available is not None else "REVIEW_REQUIRED"
    if available is None:
        return {
            **payload,
            "available_cash": None,
            "cash_source_status": "REVIEW_REQUIRED",
            "cash_source_reason": payload.get("cash_source_reason") or "missing_decision_time_cash_evidence",
            "cash_preferred": bool(payload.get("cash_preferred") or portfolio_construction_payload.get("cash_winner") is True),
        }
    return {
        **payload,
        "available_cash": available,
        "cash_source_status": source_status or "PASS",
        "cash_source_reason": payload.get("cash_source_reason") or "explicit_or_portfolio_construction_cash",
        "cash_preferred": bool(payload.get("cash_preferred") or portfolio_construction_payload.get("cash_winner") is True),
    }


def _cash_observations(
    *,
    portfolio_policy_payload: Mapping[str, Any],
    valuation_projection_payload: Mapping[str, Any],
    portfolio_construction_payload: Mapping[str, Any],
    source_artifacts: Mapping[str, Any],
    source_hashes: Mapping[str, Any],
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    observations.extend(
        _cash_observations_from_mapping(
            portfolio_policy_payload.get("current_cash_summary") if isinstance(portfolio_policy_payload.get("current_cash_summary"), Mapping) else {},
            priority=1,
            role="portfolio_policy.current_cash_summary",
            path=str(source_artifacts.get("portfolio_policy") or ""),
            sha256=str(source_hashes.get("portfolio_policy") or ""),
        )
    )
    policy_authority = (
        portfolio_policy_payload.get("portfolio_policy_allocation_authority")
        if isinstance(portfolio_policy_payload.get("portfolio_policy_allocation_authority"), Mapping)
        else {}
    )
    observations.extend(
        _cash_observations_from_mapping(
            policy_authority.get("cash_context") if isinstance(policy_authority.get("cash_context"), Mapping) else {},
            priority=2,
            role="portfolio_policy.portfolio_policy_allocation_authority.cash_context",
            path=str(source_artifacts.get("portfolio_policy") or ""),
            sha256=str(source_hashes.get("portfolio_policy") or ""),
        )
    )
    observations.extend(
        _cash_observations_from_mapping(
            policy_authority.get("available_cash_context") if isinstance(policy_authority.get("available_cash_context"), Mapping) else {},
            priority=3,
            role="portfolio_policy.portfolio_policy_allocation_authority.available_cash_context",
            path=str(source_artifacts.get("portfolio_policy") or ""),
            sha256=str(source_hashes.get("portfolio_policy") or ""),
        )
    )
    observations.extend(
        _cash_observations_from_mapping(
            valuation_projection_payload,
            priority=4,
            role="current_valuation_refresh.valuation_projection",
            path=str(source_artifacts.get("valuation_projection") or ""),
            sha256=str(source_hashes.get("valuation_projection") or ""),
        )
    )
    observations.extend(
        _cash_observations_from_mapping(
            portfolio_policy_payload,
            priority=5,
            role="portfolio_policy.top_level",
            path=str(source_artifacts.get("portfolio_policy") or ""),
            sha256=str(source_hashes.get("portfolio_policy") or ""),
        )
    )
    observations.extend(
        _cash_observations_from_mapping(
            portfolio_construction_payload,
            priority=6,
            role="portfolio_construction.top_level",
            path=str(source_artifacts.get("portfolio_construction") or ""),
            sha256=str(source_hashes.get("portfolio_construction") or ""),
        )
    )
    deduped: dict[tuple[str, float], dict[str, Any]] = {}
    for item in observations:
        deduped[(str(item["role"]), float(item["available_cash"]))] = item
    return sorted(deduped.values(), key=lambda item: (int(item["priority"]), str(item["role"])))


def _cash_notional_from_mapping(payload: Mapping[str, Any]) -> float | None:
    for field in ("available_cash", "buying_power", "cash", "current_cash", "cash_available", "net_available_cash"):
        value = _number(payload.get(field))
        if value is not None:
            return value
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    for field in ("available_cash", "buying_power", "cash", "current_cash", "cash_available", "net_available_cash"):
        value = _number(summary.get(field))
        if value is not None:
            return value
    return None


def _cash_observations_from_mapping(
    payload: Mapping[str, Any],
    *,
    priority: int,
    role: str,
    path: str,
    sha256: str,
    fields: Sequence[str] = ("available_cash", "buying_power", "cash", "current_cash", "cash_available", "net_available_cash"),
) -> list[dict[str, Any]]:
    observations = []
    for field in fields:
        value = _number(payload.get(field))
        if value is not None:
            observations.append(
                {
                    "priority": priority,
                    "role": role,
                    "field": field,
                    "available_cash": value,
                    "path": path,
                    "sha256": sha256,
                    "pit_safe": True,
                }
            )
    return observations


def _safety_state(safety_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(safety_payload or {})
    status = str(payload.get("status") or payload.get("decision") or payload.get("safety_status") or "").upper()
    return {**payload, "status": status, "blocked": status in {"BLOCK", "BLOCKED", "FAIL", "HALT"}}


def _risk_state(portfolio_construction_payload: Mapping[str, Any], risk_pacing_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    policy = portfolio_construction_payload.get("portfolio_policy_allocation_authority") if isinstance(portfolio_construction_payload.get("portfolio_policy_allocation_authority"), Mapping) else {}
    risk = policy.get("risk_pacing_evidence") if isinstance(policy.get("risk_pacing_evidence"), Mapping) else {}
    payload = {**risk, **dict(risk_pacing_payload or {})}
    status = str(payload.get("status") or payload.get("risk_pacing_status") or payload.get("decision") or "").upper()
    return {
        **payload,
        "risk_pacing_state": str(payload.get("risk_pacing_intent") or payload.get("deployment_capacity_semantic") or status),
        "market_context_state": str(payload.get("market_quality_state") or payload.get("market_context_state") or ""),
        "blocked": status in {"BLOCK", "BLOCKED", "FAIL", "HALT"} or payload.get("risk_pacing_blocked") is True,
    }


def _is_new_first_lot(row: Mapping[str, Any]) -> bool:
    semantic = str(row.get("semantic_buy_type") or row.get("lifecycle_intent") or "").upper()
    membership = str(row.get("membership_intent") or "").upper()
    pm_action = str(row.get("pm_action") or "").upper()
    return not bool(row.get("current_position")) and semantic not in {"REENTRY", "REENTRY_FIRST_LOT"} and (
        semantic in {"BUY_NEW", "NEW_FIRST_LOT", "NEW"} or membership == "ADD_CANDIDATE" or pm_action in {"NEW", "BUY_NEW"}
    )


def _is_reentry_first_lot(row: Mapping[str, Any]) -> bool:
    semantic = str(row.get("semantic_buy_type") or row.get("lifecycle_intent") or row.get("buy_type") or "").upper()
    return not bool(row.get("current_position")) and semantic in {"REENTRY", "REENTRY_FIRST_LOT", "BUY_REENTRY"}


def _is_add(row: Mapping[str, Any]) -> bool:
    return bool(row.get("current_position")) and str(row.get("pm_action") or row.get("action") or "").upper() == "ADD"


def _campaign_id(row: Mapping[str, Any]) -> str:
    return str(row.get("position_campaign_id") or row.get("current_position_campaign_id") or row.get("campaign_id") or "")


def _source_pc_evidence_ids(row: Mapping[str, Any]) -> list[str]:
    values = [
        row.get("pc_decision_id"),
        row.get("portfolio_member_id"),
        row.get("member_id"),
        row.get("item_id"),
        row.get("target_weight_authority_id"),
    ]
    return [str(value) for value in values if value]


def _lineage(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_artifacts": [
            value
            for value in (
                row.get("candidate_artifact_path"),
                row.get("opportunity_artifact_path"),
                row.get("buy_quality_artifact_path"),
                row.get("strategy_intelligence_artifact_path"),
                row.get("portfolio_construction_artifact_path"),
                row.get("position_management_artifact_path"),
            )
            if value
        ],
        "source_hashes": [
            value
            for value in (
                row.get("candidate_artifact_hash"),
                row.get("opportunity_artifact_hash"),
                row.get("buy_quality_artifact_hash"),
                row.get("strategy_intelligence_artifact_hash"),
                row.get("portfolio_construction_artifact_hash"),
                row.get("position_management_artifact_hash"),
            )
            if value
        ],
        "future_information_used": False,
        "historical_outcome_used": False,
        "raw_evidence": _strip_forbidden(row),
    }


def _strip_forbidden(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in payload.items() if str(key) not in FORBIDDEN_OUTCOME_FIELDS}


def _artifact_ref(source_artifacts: Mapping[str, Any] | None, source_hashes: Mapping[str, Any] | None, key: str) -> dict[str, Any]:
    return {
        "path": (source_artifacts or {}).get(key, ""),
        "sha256": (source_hashes or {}).get(key, ""),
        "required_for_production": False,
    }


def _class_rank(value: str) -> int:
    return {
        "CASH_PREFERRED": 0,
        "STRONG": 1,
        "COMPARABLE_HIGH": 2,
        "COMPARABLE_MARGINAL": 3,
        "WEAK_VALID": 4,
        "CASH_AVAILABLE": 5,
        "INSUFFICIENT": 8,
        "BLOCKED": 9,
    }.get(value, 7)


def _semantic_rank(value: str) -> int:
    return {semantic_type: index for index, semantic_type in enumerate(SEMANTIC_TYPES)}.get(value, 99)


def _rows(payload: Mapping[str, Any], *keys: str) -> list[Mapping[str, Any]]:
    for key in keys:
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, Mapping)]
    return []


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


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(payload), ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
