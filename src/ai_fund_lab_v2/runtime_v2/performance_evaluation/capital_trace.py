from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .daily_evidence import (
    OBS_NOT_AVAILABLE,
    OBS_NOT_OBSERVABLE,
    OBS_UNKNOWN,
    build_daily_evaluation_evidence,
    validate_daily_evaluation_evidence,
)


CAPITAL_TRACE_SCHEMA_VERSION = "phase25_capital_efficiency_trace.v1"
CAPITAL_TRACE_CONTRACT_VERSION = "phase25_a3_capital_efficiency_trace_contract.v1"
CAPITAL_TRACE_PRODUCER = "phase25_capital_efficiency_trace_producer"

COMPOUND_CONFIRMED = "COMPOUND_REINVESTMENT_CONFIRMED"
COMPOUND_PARTIAL = "COMPOUND_REINVESTMENT_PARTIAL"
COMPOUND_NOT_ESTABLISHED = "COMPOUND_REINVESTMENT_NOT_ESTABLISHED"
COMPOUND_AMBIGUOUS = "COMPOUND_REINVESTMENT_AMBIGUOUS"


def materialize_capital_efficiency_trace(
    *,
    run_id: str,
    runtime_test_evidence_root: Path,
    performance_evidence_root: Path,
    business_date: str,
) -> dict[str, Any]:
    run_dir = runtime_test_evidence_root / "runs" / run_id
    if not run_dir.exists():
        return {
            "schema_version": "phase25_capital_efficiency_trace_materialization.v1",
            "status": "PRECONDITION_FAILURE",
            "run_id": run_id,
            "business_date": business_date,
            "error": f"unknown run_id: {run_id}",
            "written": [],
        }

    trace = build_capital_efficiency_trace(
        run_id=run_id,
        run_dir=run_dir,
        business_date=business_date,
        repo_root=Path.cwd(),
    )
    validation = validate_capital_efficiency_trace(trace)
    trace["schema_validation"] = validation
    output_path = performance_evidence_root / run_id / "daily" / business_date / "capital_efficiency_trace.json"
    _write_json_atomic(output_path, trace)
    status = "PASS" if validation["status"] == "PASS" else "REVIEW_REQUIRED"
    return {
        "schema_version": "phase25_capital_efficiency_trace_materialization.v1",
        "status": status,
        "run_id": run_id,
        "business_date": business_date,
        "producer": CAPITAL_TRACE_PRODUCER,
        "runtime_test_evidence_root": str(runtime_test_evidence_root),
        "performance_evidence_root": str(performance_evidence_root),
        "read_only_runtime": True,
        "written": [{"business_date": business_date, "path": str(output_path), "validation_status": validation["status"]}],
    }


def build_capital_efficiency_trace(
    *,
    run_id: str,
    run_dir: Path,
    business_date: str,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    daily_dir = run_dir / "daily" / business_date
    daily_evidence = _load_or_build_daily_evidence(run_id=run_id, run_dir=run_dir, business_date=business_date)

    fresh_summary = _read_json_optional(run_dir / "fresh_run_summary.json")
    current_manifest = _read_json_optional(daily_dir / "current_valuation_refresh" / "current_valuation_manifest.json")
    current_state = _candidate_current(current_manifest)
    portfolio_policy = _read_json_optional(daily_dir / "strategy" / "portfolio_policy.json")
    portfolio_construction = _read_json_optional(daily_dir / "strategy" / "portfolio_construction.json")
    position_sizing = _read_json_optional(daily_dir / "strategy" / "position_sizing.json")
    runtime_planning = _read_json_optional(daily_dir / "strategy" / "runtime_planning.json")
    planning_evidence = _read_json_optional(daily_dir / "morning" / "planning_evidence.json")
    submitted_order_authority = _read_json_optional(daily_dir / "execution" / "submitted_order_authority.json")
    fills_payload = _read_json_optional(daily_dir / "execution" / "fills.json")
    capital_deployment = _read_json_optional(repo_root / "configs" / "runtime_v2" / "capital_deployment.json")

    source_refs = _source_artifact_refs(
        {
            "daily_evaluation_evidence": _daily_evidence_path(run_id=run_id, business_date=business_date),
            "current_valuation_manifest": daily_dir / "current_valuation_refresh" / "current_valuation_manifest.json",
            "portfolio_policy": daily_dir / "strategy" / "portfolio_policy.json",
            "portfolio_construction": daily_dir / "strategy" / "portfolio_construction.json",
            "position_sizing": daily_dir / "strategy" / "position_sizing.json",
            "runtime_planning": daily_dir / "strategy" / "runtime_planning.json",
            "planning_evidence": daily_dir / "morning" / "planning_evidence.json",
            "submitted_order_authority": daily_dir / "execution" / "submitted_order_authority.json",
            "fills": daily_dir / "execution" / "fills.json",
            "capital_deployment_config": repo_root / "configs" / "runtime_v2" / "capital_deployment.json",
        }
    )

    capital_authority = _capital_authority(
        daily_evidence=daily_evidence,
        current_state=current_state,
        portfolio_policy=portfolio_policy,
        position_sizing=position_sizing,
        capital_deployment=capital_deployment,
    )
    symbol_traces = _symbol_traces(
        business_date=business_date,
        daily_evidence=daily_evidence,
        current_state=current_state,
        position_sizing=position_sizing,
        portfolio_construction=portfolio_construction,
        runtime_planning=runtime_planning,
        submitted_order_authority=submitted_order_authority,
        fills_payload=fills_payload,
    )
    opportunity_pipeline = _opportunity_pipeline(symbol_traces=symbol_traces, daily_evidence=daily_evidence)
    compound = _compound_reinvestment_judgment(
        capital_authority=capital_authority,
        symbol_traces=symbol_traces,
    )
    daily_summary = _daily_summary(
        daily_evidence=daily_evidence,
        capital_authority=capital_authority,
        symbol_traces=symbol_traces,
        opportunity_pipeline=opportunity_pipeline,
        compound=compound,
    )
    missing_fields = _missing_fields(daily_summary=daily_summary, symbol_traces=symbol_traces, capital_authority=capital_authority)
    warnings = _warnings(capital_authority=capital_authority, compound=compound, daily_evidence=daily_evidence)
    authority_conflicts = _authority_conflicts(capital_authority=capital_authority)
    fingerprint_seed = {
        "schema_version": CAPITAL_TRACE_SCHEMA_VERSION,
        "run_id": run_id,
        "business_date": business_date,
        "source_artifact_refs": source_refs,
    }
    return {
        "schema_version": CAPITAL_TRACE_SCHEMA_VERSION,
        "contract_version": CAPITAL_TRACE_CONTRACT_VERSION,
        "producer": CAPITAL_TRACE_PRODUCER,
        "generated_at": _deterministic_generated_at(run_id=run_id, business_date=business_date),
        "artifact_fingerprint": _stable_hash(fingerprint_seed),
        "run_id": run_id,
        "business_date": business_date,
        "read_only_runtime": True,
        "daily_summary": daily_summary,
        "capital_authority_trace": capital_authority,
        "symbol_traces": symbol_traces,
        "opportunity_pipeline": opportunity_pipeline,
        "compound_reinvestment": compound,
        "authority_conflicts": authority_conflicts,
        "missing_fields": sorted(set(missing_fields)),
        "warnings": sorted(set(warnings)),
        "source_artifact_refs": source_refs,
        "temporal_safety": {
            "producer_mode": "READ_ONLY_POST_HOC",
            "runtime_evidence_mutated": False,
            "strategy_evidence_mutated": False,
            "future_data_policy": "PIT_SAFE_RUN_SCOPED_EVIDENCE_ONLY",
        },
    }


def validate_capital_efficiency_trace(payload: dict[str, Any]) -> dict[str, Any]:
    required = [
        "schema_version",
        "run_id",
        "business_date",
        "producer",
        "daily_summary",
        "symbol_traces",
        "opportunity_pipeline",
        "compound_reinvestment",
        "authority_conflicts",
        "missing_fields",
        "warnings",
        "source_artifact_refs",
        "temporal_safety",
    ]
    missing = [field for field in required if field not in payload]
    status = "PASS" if not missing and payload.get("schema_version") == CAPITAL_TRACE_SCHEMA_VERSION else "REVIEW_REQUIRED"
    return {
        "schema_version": "phase25_capital_efficiency_trace_validation.v1",
        "status": status,
        "missing_top_level_fields": missing,
        "schema_version_match": payload.get("schema_version") == CAPITAL_TRACE_SCHEMA_VERSION,
    }


def _capital_authority(
    *,
    daily_evidence: dict[str, Any],
    current_state: dict[str, Any],
    portfolio_policy: dict[str, Any],
    position_sizing: dict[str, Any],
    capital_deployment: dict[str, Any],
) -> dict[str, Any]:
    capital = daily_evidence.get("capital") if isinstance(daily_evidence.get("capital"), dict) else {}
    total_equity = _value(capital.get("total_equity"))
    initial = _value(((daily_evidence.get("returns") or {}) if isinstance(daily_evidence.get("returns"), dict) else {}).get("initial_equity"))
    eval_capital = _number(capital_deployment.get("evaluation_capital"))
    max_exposure = _number(capital_deployment.get("max_exposure"))
    current_market_value = _value(capital.get("market_value"))
    target_gross = _value(capital.get("target_gross_exposure_ratio"))
    deployable_by_target = total_equity * target_gross - current_market_value if None not in (total_equity, target_gross, current_market_value) else None
    deployable_by_cap = max_exposure - current_market_value if None not in (max_exposure, current_market_value) else None
    deployable_cash = _min_present(deployable_by_target, deployable_by_cap, _value(capital.get("cash")))
    return {
        "initial_capital": _obs(initial),
        "runtime_evaluation_capital": capital.get("runtime_evaluation_capital", OBS_NOT_AVAILABLE),
        "current_cash": capital.get("cash", OBS_NOT_AVAILABLE),
        "current_buying_power": capital.get("buying_power", OBS_NOT_AVAILABLE),
        "current_market_value": capital.get("market_value", OBS_NOT_AVAILABLE),
        "current_total_equity": capital.get("total_equity", OBS_NOT_AVAILABLE),
        "portfolio_policy_cash_reserve_ratio": _obs(_number(portfolio_policy.get("cash_reserve_ratio"), portfolio_policy.get("cash_reserve"))),
        "portfolio_policy_target_gross_exposure_ratio": _obs(_number(position_sizing.get("aggregate_exposure_cap"), portfolio_policy.get("target_gross_exposure_ratio"))),
        "portfolio_policy_position_count_target": _obs(_number(portfolio_policy.get("target_position_count"), portfolio_policy.get("resolved_opportunity_capacity"), position_sizing.get("dynamic_position_count"))),
        "capital_deployment_evaluation_capital": _obs(eval_capital),
        "capital_deployment_max_exposure": _obs(max_exposure),
        "capital_deployment_deployable_cash": _obs(deployable_cash, "DERIVED"),
        "capital_deployment_limit": _obs(_min_present(eval_capital, max_exposure), "DERIVED"),
        "position_sizing_capital_base": _obs(_number(position_sizing.get("portfolio_total_equity"), position_sizing.get("portfolio_value"))),
        "position_sizing_capital_base_matches_current_total_equity": {
            "value": bool(total_equity is not None and _number(position_sizing.get("portfolio_total_equity"), position_sizing.get("portfolio_value")) == total_equity),
            "status": "DERIVED" if total_equity is not None and position_sizing else "NOT_OBSERVABLE",
        },
        "fixed_cap_presence": {
            "value": bool(eval_capital or max_exposure),
            "status": "AVAILABLE" if capital_deployment else "NOT_OBSERVABLE",
        },
        "fixed_cap_binding_status": _fixed_cap_binding_status(current_market_value=current_market_value, max_exposure=max_exposure),
        "current_state_environment": current_state.get("environment", "UNKNOWN") if current_state else "UNKNOWN",
    }


def _symbol_traces(
    *,
    business_date: str,
    daily_evidence: dict[str, Any],
    current_state: dict[str, Any],
    position_sizing: dict[str, Any],
    portfolio_construction: dict[str, Any],
    runtime_planning: dict[str, Any],
    submitted_order_authority: dict[str, Any],
    fills_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    sizing_by_symbol = {str(row.get("position_reference") or row.get("symbol") or "").split("-")[-1]: row for row in _rows(position_sizing, "positions")}
    # Prefer explicit symbols when available.
    sizing_by_symbol.update({str(row.get("symbol") or row.get("security_code") or row.get("position_reference") or "").split("-")[-1]: row for row in _rows(position_sizing, "positions")})
    construction_by_symbol = {str(row.get("symbol") or row.get("security_code") or ""): row for row in _rows(portfolio_construction, "portfolio_members")}
    planning_by_symbol = {str(row.get("security_code") or row.get("symbol") or ""): row for row in _rows(runtime_planning, "plans")}
    fills_by_symbol = _fills_by_symbol(fills_payload)
    submitted_by_symbol = _submitted_by_symbol(submitted_order_authority)
    if planning_by_symbol:
        symbols = sorted(set(planning_by_symbol) | set(fills_by_symbol) | set(submitted_by_symbol))
    else:
        symbols = sorted(set(sizing_by_symbol) | set(construction_by_symbol) | set(fills_by_symbol) | set(submitted_by_symbol))
    if not symbols and daily_evidence.get("opportunity_utilization", {}).get("status") == "NOT_OBSERVABLE":
        return []
    traces: list[dict[str, Any]] = []
    capital = daily_evidence.get("capital") if isinstance(daily_evidence.get("capital"), dict) else {}
    total_equity = capital.get("total_equity", OBS_NOT_AVAILABLE)
    runtime_eval = capital.get("runtime_evaluation_capital", OBS_NOT_AVAILABLE)
    for symbol in symbols:
        sizing = sizing_by_symbol.get(symbol, {})
        construction = construction_by_symbol.get(symbol, {})
        planning = planning_by_symbol.get(symbol, {})
        submitted = submitted_by_symbol.get(symbol, {})
        fill = fills_by_symbol.get(symbol, {})
        planning_qty = _number(planning.get("planned_quantity"), planning.get("target_quantity_candidate"), planning.get("quantity_delta_candidate"))
        target_notional = _number(sizing.get("target_notional"), sizing.get("incremental_target_notional"))
        after_caps = _number(sizing.get("incremental_buy_notional"), sizing.get("target_notional"))
        primary, secondary, reason_status = _binding_constraint(planning=planning, sizing=sizing, construction=construction)
        pipeline_status, reached, rejection = _pipeline_status(
            sizing=sizing,
            construction=construction,
            planning=planning,
            submitted=submitted,
            fill=fill,
            primary_binding=primary,
        )
        trace = {
            "business_date": business_date,
            "symbol": symbol,
            "opportunity_id": _first_non_empty(
                sizing.get("opportunity_row_id"),
                construction.get("opportunity_row_id"),
                planning.get("opportunity_row_id"),
                OBS_NOT_OBSERVABLE,
            ),
            "opportunity_status": _first_non_empty(
                ((planning.get("opportunity_authority") or {}) if isinstance(planning.get("opportunity_authority"), dict) else {}).get("opportunity_status"),
                "AVAILABLE" if sizing or construction or planning else "NOT_OBSERVABLE",
            ),
            "eligibility_status": _first_non_empty(
                ((planning.get("opportunity_authority") or {}) if isinstance(planning.get("opportunity_authority"), dict) else {}).get("opportunity_eligibility"),
                "NOT_OBSERVABLE",
            ),
            "current_total_equity": total_equity,
            "runtime_evaluation_capital": runtime_eval,
            "position_sizing_capital_base": _obs(_number(position_sizing.get("portfolio_total_equity"), position_sizing.get("portfolio_value"))),
            "target_weight": _obs(_number(sizing.get("target_weight"), construction.get("target_weight"))),
            "target_notional_before_caps": _obs(target_notional),
            "target_notional_after_caps": _obs(after_caps),
            "reference_price": _obs(_number(sizing.get("reference_price"))),
            "raw_target_quantity": _obs(_number(sizing.get("target_quantity_candidate"))),
            "lot_adjusted_quantity": _obs(_number(sizing.get("quantity_delta_candidate"), sizing.get("target_quantity_candidate"))),
            "capital_feasible_quantity": OBS_NOT_OBSERVABLE,
            "position_count_feasible_quantity": OBS_NOT_OBSERVABLE,
            "safety_feasible_quantity": OBS_NOT_OBSERVABLE,
            "planned_quantity": _obs(planning_qty),
            "submitted_quantity": _obs(_number(submitted.get("quantity")), "DERIVED") if submitted else OBS_NOT_OBSERVABLE,
            "executed_quantity": _obs(_number(fill.get("quantity")), "DERIVED") if fill else _obs(0, "DERIVED"),
            "executed_notional": _obs(_number(fill.get("notional")), "DERIVED") if fill else _obs(0, "DERIVED"),
            "planning_planned_notional": _obs(_planned_notional(planning=planning, sizing=sizing), "DERIVED"),
            "primary_binding_constraint": primary,
            "secondary_constraints": secondary,
            "binding_constraint": primary,
            "binding_constraint_status": reason_status,
            "pipeline_status": pipeline_status,
            "pipeline_reached_stages": reached,
            "rejection_reason": rejection,
            "planning_intent": planning.get("planning_intent", "NOT_OBSERVABLE"),
            "planning_reason": planning.get("planning_reason") or planning.get("no_order_reason") or "NOT_OBSERVABLE",
            "source_artifact_refs": _symbol_source_refs(sizing=sizing, construction=construction, planning=planning),
        }
        traces.append(trace)
    return traces


def _opportunity_pipeline(*, symbol_traces: list[dict[str, Any]], daily_evidence: dict[str, Any]) -> dict[str, Any]:
    opp = daily_evidence.get("opportunity_utilization") if isinstance(daily_evidence.get("opportunity_utilization"), dict) else {}
    counts = {
        "generated_opportunity_count": opp.get("generated_opportunity_count", OBS_NOT_OBSERVABLE),
        "eligible_opportunity_count": opp.get("eligible_opportunity_count", OBS_NOT_OBSERVABLE),
        "sized_opportunity_count": _obs(sum(1 for row in symbol_traces if "SIZED" in row.get("pipeline_reached_stages", [])), "DERIVED") if symbol_traces else OBS_NOT_OBSERVABLE,
        "planned_buy_count": opp.get("planned_buy_count", OBS_NOT_OBSERVABLE),
        "submitted_buy_count": opp.get("submitted_buy_count", OBS_NOT_OBSERVABLE),
        "executed_buy_count": opp.get("executed_buy_count", OBS_NOT_OBSERVABLE),
    }
    return {
        "status": opp.get("status", "NOT_OBSERVABLE"),
        "counts": counts,
        "symbol_pipeline": [
            {
                "symbol": row["symbol"],
                "opportunity_id": row["opportunity_id"],
                "pipeline_status": row["pipeline_status"],
                "rejection_reason": row["rejection_reason"],
                "primary_binding_constraint": row["primary_binding_constraint"],
            }
            for row in symbol_traces
        ],
    }


def _compound_reinvestment_judgment(*, capital_authority: dict[str, Any], symbol_traces: list[dict[str, Any]]) -> dict[str, Any]:
    sizing_dynamic = bool((capital_authority.get("position_sizing_capital_base_matches_current_total_equity") or {}).get("value"))
    post_profit_actions = [
        row
        for row in symbol_traces
        if _value(row.get("current_total_equity")) and _value(row.get("runtime_evaluation_capital")) and _value(row.get("current_total_equity")) > _value(row.get("runtime_evaluation_capital")) and _value(row.get("executed_quantity")) and _value(row.get("executed_quantity")) > 0
    ]
    reasons: list[str] = []
    if sizing_dynamic:
        reasons.append("POSITION_SIZING_USES_CURRENT_TOTAL_EQUITY")
    else:
        reasons.append("POSITION_SIZING_CAPITAL_BASE_NOT_CONFIRMED_DYNAMIC")
    if not post_profit_actions:
        reasons.append("NO_POST_PROFIT_BUY_OR_ADD_EXECUTION_SAMPLE_ON_THIS_DATE")
    fixed_cap_status = str((capital_authority.get("fixed_cap_binding_status") or {}).get("status") or "")
    if fixed_cap_status != "DERIVED":
        reasons.append("FIXED_CAP_BINDING_NOT_FULLY_OBSERVABLE")
    status = COMPOUND_AMBIGUOUS
    if sizing_dynamic and not post_profit_actions:
        status = COMPOUND_AMBIGUOUS
    return {
        "status": status,
        "sizing_base_layer": {
            "position_sizing_capital_base": capital_authority.get("position_sizing_capital_base", OBS_NOT_AVAILABLE),
            "current_total_equity": capital_authority.get("current_total_equity", OBS_NOT_AVAILABLE),
            "initial_capital": capital_authority.get("initial_capital", OBS_NOT_AVAILABLE),
        },
        "downstream_cap_layer": {
            "capital_deployment_evaluation_capital": capital_authority.get("capital_deployment_evaluation_capital", OBS_NOT_AVAILABLE),
            "capital_deployment_max_exposure": capital_authority.get("capital_deployment_max_exposure", OBS_NOT_AVAILABLE),
            "aggregate_feasibility_limit": OBS_NOT_OBSERVABLE,
            "submit_capital_limit": OBS_NOT_OBSERVABLE,
            "fixed_cap_binding_status": capital_authority.get("fixed_cap_binding_status", OBS_NOT_OBSERVABLE),
        },
        "actual_deployment_layer": {
            "planned_notional": _obs(sum(_value(row.get("planning_planned_notional")) or 0.0 for row in symbol_traces), "DERIVED"),
            "submitted_notional": OBS_NOT_OBSERVABLE,
            "executed_notional": _obs(sum(_value(row.get("executed_notional")) or 0.0 for row in symbol_traces), "DERIVED"),
        },
        "reasons": reasons,
    }


def _daily_summary(
    *,
    daily_evidence: dict[str, Any],
    capital_authority: dict[str, Any],
    symbol_traces: list[dict[str, Any]],
    opportunity_pipeline: dict[str, Any],
    compound: dict[str, Any],
) -> dict[str, Any]:
    capital = daily_evidence.get("capital") if isinstance(daily_evidence.get("capital"), dict) else {}
    total_equity = _value(capital.get("total_equity"))
    initial = _value(capital_authority.get("initial_capital"))
    target_gross = _value(capital.get("target_gross_exposure_ratio"))
    actual_gross = _value(capital.get("gross_exposure_ratio"))
    counts = opportunity_pipeline.get("counts") if isinstance(opportunity_pipeline.get("counts"), dict) else {}
    return {
        "initial_capital": capital_authority.get("initial_capital", OBS_NOT_AVAILABLE),
        "runtime_evaluation_capital": capital_authority.get("runtime_evaluation_capital", OBS_NOT_AVAILABLE),
        "current_total_equity": capital_authority.get("current_total_equity", OBS_NOT_AVAILABLE),
        "equity_gain_vs_initial": _obs(total_equity - initial if None not in (total_equity, initial) else None, "DERIVED"),
        "target_gross_exposure": capital.get("target_gross_exposure_ratio", OBS_NOT_AVAILABLE),
        "actual_gross_exposure": capital.get("gross_exposure_ratio", OBS_NOT_AVAILABLE),
        "unused_exposure_capacity": _obs(target_gross - actual_gross if None not in (target_gross, actual_gross) else None, "DERIVED"),
        "policy_cash_buffer": capital.get("policy_cash_buffer", OBS_NOT_AVAILABLE),
        "pending_reserved_cash": capital.get("pending_reserved_cash", OBS_NOT_OBSERVABLE),
        "deployable_cash": capital_authority.get("capital_deployment_deployable_cash", OBS_NOT_AVAILABLE),
        "idle_cash": capital.get("idle_cash", OBS_NOT_AVAILABLE),
        "generated_opportunity_count": counts.get("generated_opportunity_count", OBS_NOT_OBSERVABLE),
        "eligible_opportunity_count": counts.get("eligible_opportunity_count", OBS_NOT_OBSERVABLE),
        "sized_opportunity_count": counts.get("sized_opportunity_count", OBS_NOT_OBSERVABLE),
        "planned_buy_count": counts.get("planned_buy_count", OBS_NOT_OBSERVABLE),
        "submitted_buy_count": counts.get("submitted_buy_count", OBS_NOT_OBSERVABLE),
        "executed_buy_count": counts.get("executed_buy_count", OBS_NOT_OBSERVABLE),
        "total_target_buy_notional": _obs(sum(_value(row.get("target_notional_after_caps")) or 0.0 for row in symbol_traces), "DERIVED"),
        "total_planned_buy_notional": _obs(sum(_value(row.get("planning_planned_notional")) or 0.0 for row in symbol_traces), "DERIVED"),
        "total_submitted_buy_notional": OBS_NOT_OBSERVABLE,
        "total_executed_buy_notional": capital.get("executed_buy_notional", OBS_NOT_AVAILABLE),
        "compound_reinvestment_status": compound["status"],
        "compound_reinvestment_reasons": compound["reasons"],
    }


def _binding_constraint(*, planning: dict[str, Any], sizing: dict[str, Any], construction: dict[str, Any]) -> tuple[str, list[str], str]:
    text = _reason_text(planning, sizing, construction)
    constraints: list[str] = []
    if "minimum_notional" in text or "min_notional" in text:
        constraints.append("MIN_NOTIONAL")
    if "safety" in text:
        constraints.append("SAFETY")
    if "position_count" in text or "max_position" in text:
        constraints.append("POSITION_COUNT")
    if "lot" in text:
        constraints.append("LOT_SIZE")
    if "price" in text:
        constraints.append("REFERENCE_PRICE")
    if "no_action" in text or "no_order" in text or "zero_delta" in text or "member_not_selected" in text:
        constraints.append("PLANNING_POLICY")
    if not constraints:
        return "UNKNOWN", [], "NOT_OBSERVABLE"
    return constraints[0], constraints[1:], "AVAILABLE"


def _pipeline_status(*, sizing: dict[str, Any], construction: dict[str, Any], planning: dict[str, Any], submitted: dict[str, Any], fill: dict[str, Any], primary_binding: str) -> tuple[str, list[str], str]:
    reached: list[str] = []
    if sizing or construction or planning:
        reached.append("GENERATED")
    if _opportunity_eligible(planning):
        reached.append("ELIGIBLE")
    if sizing:
        reached.append("SIZED")
    if construction and construction.get("target_membership") is True:
        reached.append("SELECTED_FOR_MEMBERSHIP")
    if planning and _number(planning.get("planned_quantity"), planning.get("target_quantity_candidate"), planning.get("quantity_delta_candidate")) and _number(planning.get("planned_quantity"), planning.get("target_quantity_candidate"), planning.get("quantity_delta_candidate")) > 0:
        reached.append("PLANNED")
    if submitted:
        reached.append("SUBMITTED")
    if fill and _number(fill.get("quantity")) and _number(fill.get("quantity")) > 0:
        reached.append("EXECUTED")
    if "EXECUTED" in reached:
        return "EXECUTED", reached, "NOT_APPLICABLE"
    if "SUBMITTED" in reached:
        return "SUBMITTED", reached, "NOT_APPLICABLE"
    if "PLANNED" in reached:
        return "PLANNED", reached, "NOT_APPLICABLE"
    if sizing or planning:
        rejection = "UNKNOWN" if primary_binding == "UNKNOWN" else primary_binding
        return "REJECTED", reached, rejection
    return "NOT_OBSERVABLE", reached, "UNKNOWN"


def _authority_conflicts(*, capital_authority: dict[str, Any]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    runtime_eval = _value(capital_authority.get("runtime_evaluation_capital"))
    current_equity = _value(capital_authority.get("current_total_equity"))
    sizing_base = _value(capital_authority.get("position_sizing_capital_base"))
    if runtime_eval is not None and current_equity is not None and runtime_eval != current_equity:
        conflicts.append(
            {
                "conflict_id": "runtime_evaluation_capital_vs_current_total_equity",
                "status": "AVAILABLE",
                "runtime_evaluation_capital": runtime_eval,
                "current_total_equity": current_equity,
            }
        )
    if sizing_base is not None and runtime_eval is not None and sizing_base != runtime_eval:
        conflicts.append(
            {
                "conflict_id": "position_sizing_capital_base_vs_runtime_evaluation_capital",
                "status": "AVAILABLE",
                "position_sizing_capital_base": sizing_base,
                "runtime_evaluation_capital": runtime_eval,
            }
        )
    return conflicts


def _missing_fields(*, daily_summary: dict[str, Any], symbol_traces: list[dict[str, Any]], capital_authority: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for key, value in daily_summary.items():
        if _is_missing_status(value):
            missing.append(f"daily_summary.{key}")
    for key, value in capital_authority.items():
        if _is_missing_status(value):
            missing.append(f"capital_authority_trace.{key}")
    for index, row in enumerate(symbol_traces):
        for key, value in row.items():
            if _is_missing_status(value):
                missing.append(f"symbol_traces[{index}].{key}")
    return missing


def _warnings(*, capital_authority: dict[str, Any], compound: dict[str, Any], daily_evidence: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if compound["status"] == COMPOUND_AMBIGUOUS:
        warnings.append("COMPOUND_REINVESTMENT_AMBIGUOUS")
    if capital_authority.get("fixed_cap_presence", {}).get("value") is True:
        warnings.append("FIXED_CAPITAL_POLICY_PRESENT")
    if "BENCHMARK_MISSING" in daily_evidence.get("warnings", []):
        warnings.append("BENCHMARK_MISSING_IN_DAILY_EVIDENCE")
    return warnings


def _load_or_build_daily_evidence(*, run_id: str, run_dir: Path, business_date: str) -> dict[str, Any]:
    existing = _read_json_optional(_daily_evidence_path(run_id=run_id, business_date=business_date))
    if existing and validate_daily_evaluation_evidence(existing).get("status") == "PASS":
        return existing
    return build_daily_evaluation_evidence(run_id=run_id, run_dir=run_dir, business_date=business_date)


def _daily_evidence_path(*, run_id: str, business_date: str) -> Path:
    return Path("reports") / "performance_evaluations" / run_id / "daily" / business_date / "daily_evaluation_evidence.json"


def _fixed_cap_binding_status(*, current_market_value: float | None, max_exposure: float | None) -> dict[str, Any]:
    if current_market_value is None or max_exposure is None:
        return OBS_NOT_OBSERVABLE
    if current_market_value < max_exposure:
        return {"value": False, "status": "DERIVED", "reason": "current_market_value_below_max_exposure"}
    if current_market_value >= max_exposure:
        return {"value": True, "status": "DERIVED", "reason": "current_market_value_at_or_above_max_exposure"}
    return OBS_UNKNOWN


def _fills_by_symbol(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in _rows(payload, "fills"):
        symbol = str(row.get("symbol") or row.get("security_code") or "")
        if not symbol:
            continue
        qty = _number(row.get("quantity"))
        notional = _value(row.get("gross_notional"))
        current = result.setdefault(symbol, {"quantity": 0.0, "notional": 0.0})
        current["quantity"] += qty or 0.0
        current["notional"] += notional or 0.0
    return result


def _submitted_by_symbol(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    refs = payload.get("execution_references") if isinstance(payload, dict) else None
    if not isinstance(refs, list):
        return result
    for row in refs:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or row.get("security_code") or "")
        if not symbol:
            continue
        qty = _number(row.get("quantity"), row.get("submitted_quantity"), row.get("accepted_quantity"))
        result[symbol] = {"quantity": qty}
    return result


def _planned_notional(*, planning: dict[str, Any], sizing: dict[str, Any]) -> float | None:
    quantity = _number(planning.get("planned_quantity"), planning.get("target_quantity_candidate"), planning.get("quantity_delta_candidate"))
    price = _number(sizing.get("reference_price"))
    if quantity is None or price is None:
        return None
    return quantity * price


def _symbol_source_refs(*, sizing: dict[str, Any], construction: dict[str, Any], planning: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for role, row in (("position_sizing", sizing), ("portfolio_construction", construction), ("runtime_planning", planning)):
        path = row.get("opportunity_artifact_path") or row.get("input_opportunity_rank_source_path") or ""
        if path:
            refs.append({"role": role, "opportunity_artifact_path": path, "opportunity_artifact_hash": row.get("opportunity_artifact_hash") or row.get("input_opportunity_rank_source_hash") or ""})
    return refs


def _opportunity_eligible(planning: dict[str, Any]) -> bool:
    authority = planning.get("opportunity_authority") if isinstance(planning.get("opportunity_authority"), dict) else {}
    return str(authority.get("opportunity_eligibility") or "") == "BUY_ELIGIBLE" or str(authority.get("opportunity_status") or "") == "PASS"


def _source_artifact_refs(paths: dict[str, Path]) -> list[dict[str, Any]]:
    return [
        {
            "role": role,
            "path": str(path),
            "exists": path.exists(),
            "sha256": _sha256_file(path) if path.exists() and path.is_file() else "",
        }
        for role, path in sorted(paths.items())
    ]


def _candidate_current(current_manifest: dict[str, Any]) -> dict[str, Any]:
    artifact = current_manifest.get("artifact") if isinstance(current_manifest.get("artifact"), dict) else {}
    current = artifact.get("candidate_current") if isinstance(artifact.get("candidate_current"), dict) else {}
    return current


def _reason_text(*rows: dict[str, Any]) -> str:
    parts: list[str] = []
    for row in rows:
        for key in ("planning_reason", "no_order_reason", "reason", "quantity_status", "planning_intent", "sizing_reason", "membership_reason", "weight_reason"):
            value = row.get(key)
            if value not in (None, ""):
                parts.append(str(value))
        for key in ("reason_codes", "direct_reason_codes"):
            value = row.get(key)
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
    return " ".join(parts).lower()


def _is_missing_status(value: Any) -> bool:
    return isinstance(value, dict) and str(value.get("status") or "") in {"NOT_AVAILABLE", "NOT_OBSERVABLE", "UNKNOWN"}


def _obs(value: Any, status: str = "AVAILABLE") -> dict[str, Any]:
    number = _number(value)
    if number is None:
        if status == "NOT_OBSERVABLE":
            return OBS_NOT_OBSERVABLE
        if status == "UNKNOWN":
            return OBS_UNKNOWN
        return OBS_NOT_AVAILABLE
    if float(number).is_integer():
        number = int(number)
    return {"value": number, "status": status}


def _value(value: Any) -> float | None:
    if isinstance(value, dict):
        if str(value.get("status") or "") in {"NOT_AVAILABLE", "NOT_OBSERVABLE", "UNKNOWN"}:
            return None
        return _number(value.get("value"))
    return _number(value)


def _number(*values: Any) -> float | None:
    for value in values:
        if isinstance(value, dict):
            value = value.get("value")
        if value in (None, "", "MISSING", "NOT_AVAILABLE", "NOT_OBSERVABLE", "UNKNOWN"):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _min_present(*values: float | None) -> float | None:
    present = [value for value in values if value is not None]
    return min(present) if present else None


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key) if isinstance(payload, dict) else None
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return ""


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def _deterministic_generated_at(*, run_id: str, business_date: str) -> str:
    return f"deterministic:{_stable_hash({'run_id': run_id, 'business_date': business_date})[:16]}"
