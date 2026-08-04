from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DAILY_EVALUATION_EVIDENCE_SCHEMA_VERSION = "phase25_daily_evaluation_evidence.v1"
DAILY_EVALUATION_EVIDENCE_CONTRACT_VERSION = "phase25_a1_daily_evaluation_evidence_contract.v1"
PRODUCER = "phase25_daily_evaluation_evidence_producer"
METRIC_CONTRACT_VERSION = "phase25_a1_performance_metric_contract.v1"

OBS_NOT_AVAILABLE = {"value": "MISSING", "status": "NOT_AVAILABLE"}
OBS_NOT_OBSERVABLE = {"value": "NOT_OBSERVABLE", "status": "NOT_OBSERVABLE"}
OBS_UNKNOWN = {"value": "UNKNOWN", "status": "UNKNOWN"}


def materialize_daily_evaluation_evidence(
    *,
    run_id: str,
    runtime_test_evidence_root: Path,
    performance_evidence_root: Path,
    business_date: str | None = None,
) -> dict[str, Any]:
    """Materialize Phase25 daily evidence from immutable Runtime Test evidence.

    The producer is read-only with respect to Runtime evidence. It only writes
    post-hoc performance evaluation artifacts under performance_evidence_root.
    """

    run_dir = runtime_test_evidence_root / "runs" / run_id
    if not run_dir.exists():
        return {
            "schema_version": "phase25_daily_evaluation_materialization.v1",
            "status": "PRECONDITION_FAILURE",
            "run_id": run_id,
            "generated_at": _utc_now(),
            "error": f"unknown run_id: {run_id}",
            "written": [],
        }

    run_state = _read_json_optional(run_dir / "run_state.json")
    fresh_summary = _read_json_optional(run_dir / "fresh_run_summary.json")
    days = _completed_business_days(run_state=run_state, fresh_summary=fresh_summary)
    if business_date:
        days = [day for day in days if day == business_date]
    if business_date and not days:
        return {
            "schema_version": "phase25_daily_evaluation_materialization.v1",
            "status": "PRECONDITION_FAILURE",
            "run_id": run_id,
            "business_date": business_date,
            "generated_at": _utc_now(),
            "error": "business_date is not a completed business day for the run",
            "written": [],
        }

    written: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for day in days:
        evidence = build_daily_evaluation_evidence(
            run_id=run_id,
            run_dir=run_dir,
            business_date=day,
            previous_daily_evidence=previous,
        )
        validation = validate_daily_evaluation_evidence(evidence)
        evidence["schema_validation"] = validation
        output_path = performance_evidence_root / run_id / "daily" / day / "daily_evaluation_evidence.json"
        _write_json_atomic(output_path, evidence)
        written.append(
            {
                "business_date": day,
                "path": str(output_path),
                "status": evidence.get("evidence_status"),
                "validation_status": validation["status"],
            }
        )
        previous = evidence

    status = "PASS" if all(row["validation_status"] == "PASS" for row in written) else "REVIEW_REQUIRED"
    return {
        "schema_version": "phase25_daily_evaluation_materialization.v1",
        "status": status,
        "run_id": run_id,
        "business_date": business_date or "",
        "generated_at": _utc_now(),
        "producer": PRODUCER,
        "runtime_test_evidence_root": str(runtime_test_evidence_root),
        "performance_evidence_root": str(performance_evidence_root),
        "read_only_runtime": True,
        "written": written,
    }


def build_daily_evaluation_evidence(
    *,
    run_id: str,
    run_dir: Path,
    business_date: str,
    previous_daily_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = _read_json_optional(run_dir / "plan.json")
    run_state = _read_json_optional(run_dir / "run_state.json")
    final_summary = _read_json_optional(run_dir / "final_summary.json")
    fresh_summary = _read_json_optional(run_dir / "fresh_run_summary.json")
    daily_dir = run_dir / "daily" / business_date

    current_manifest = _read_json_optional(daily_dir / "current_valuation_refresh" / "current_valuation_manifest.json")
    valuation_projection = _read_json_optional(daily_dir / "current_valuation_refresh" / "valuation_projection.json")
    valuation_apply = _read_json_optional(daily_dir / "current_valuation_refresh" / "valuation_apply_evidence.json")
    current_state = _candidate_current(current_manifest)

    portfolio_policy = _read_json_optional(daily_dir / "strategy" / "portfolio_policy.json")
    position_sizing = _read_json_optional(daily_dir / "strategy" / "position_sizing.json")
    runtime_planning = _read_json_optional(daily_dir / "strategy" / "runtime_planning.json")
    planning_evidence = _read_json_optional(daily_dir / "morning" / "planning_evidence.json")
    submitted_order_authority = _read_json_optional(daily_dir / "execution" / "submitted_order_authority.json")
    fills_payload = _read_json_optional(daily_dir / "execution" / "fills.json")
    benchmark_snapshot = _read_json_optional(daily_dir / "benchmark" / "benchmark_snapshot.json")

    source_refs = _source_artifact_refs(
        {
            "run_state": run_dir / "run_state.json",
            "plan": run_dir / "plan.json",
            "fresh_run_summary": run_dir / "fresh_run_summary.json",
            "final_summary": run_dir / "final_summary.json",
            "current_valuation_manifest": daily_dir / "current_valuation_refresh" / "current_valuation_manifest.json",
            "valuation_projection": daily_dir / "current_valuation_refresh" / "valuation_projection.json",
            "valuation_apply_evidence": daily_dir / "current_valuation_refresh" / "valuation_apply_evidence.json",
            "portfolio_policy": daily_dir / "strategy" / "portfolio_policy.json",
            "position_sizing": daily_dir / "strategy" / "position_sizing.json",
            "runtime_planning": daily_dir / "strategy" / "runtime_planning.json",
            "planning_evidence": daily_dir / "morning" / "planning_evidence.json",
            "submitted_order_authority": daily_dir / "execution" / "submitted_order_authority.json",
            "fills": daily_dir / "execution" / "fills.json",
            "benchmark_snapshot": daily_dir / "benchmark" / "benchmark_snapshot.json",
        }
    )

    capital = _build_capital(
        current_state=current_state,
        valuation_projection=valuation_projection,
        portfolio_policy=portfolio_policy,
        position_sizing=position_sizing,
        fills_payload=fills_payload,
    )
    returns = _build_returns(capital=capital, previous_daily_evidence=previous_daily_evidence, fresh_summary=fresh_summary)
    risk = _build_risk(capital=capital, previous_daily_evidence=previous_daily_evidence)
    activity = _build_activity(fills_payload=fills_payload)
    opportunity_utilization = _build_opportunity_utilization(
        runtime_planning=runtime_planning,
        planning_evidence=planning_evidence,
        submitted_order_authority=submitted_order_authority,
        fills_payload=fills_payload,
    )
    benchmark = _build_benchmark(benchmark_snapshot=benchmark_snapshot)

    missing_fields = _missing_fields(capital=capital, returns=returns, risk=risk, opportunity_utilization=opportunity_utilization)
    warnings = _warnings(
        current_state=current_state,
        valuation_apply=valuation_apply,
        benchmark=benchmark,
        opportunity_utilization=opportunity_utilization,
    )
    evidence_status = "AVAILABLE" if not missing_fields else "PARTIAL"

    return {
        "schema_version": DAILY_EVALUATION_EVIDENCE_SCHEMA_VERSION,
        "contract_version": DAILY_EVALUATION_EVIDENCE_CONTRACT_VERSION,
        "producer": PRODUCER,
        "generated_at": _utc_now(),
        "run_id": run_id,
        "business_date": business_date,
        "source_revision": _source_revision(run_state=run_state),
        "runtime_mode": _first_non_empty(plan.get("mode"), fresh_summary.get("mode"), current_state.get("environment"), "UNKNOWN"),
        "run_eligibility_status": _run_eligibility_status(run_state=run_state, final_summary=final_summary),
        "metric_contract_version": METRIC_CONTRACT_VERSION,
        "source_artifact_refs": source_refs,
        "evidence_status": evidence_status,
        "capital": capital,
        "returns": returns,
        "risk": risk,
        "activity": activity,
        "opportunity_utilization": opportunity_utilization,
        "benchmark": benchmark,
        "attribution_inputs": {
            "status": "PARTIAL",
            "reason": "Daily evidence retains inputs only; attribution materialization is out of scope for Phase25-A2.",
        },
        "missing_fields": missing_fields,
        "warnings": warnings,
        "temporal_safety": {
            "runtime_evidence_mutated": False,
            "strategy_evidence_mutated": False,
            "producer_mode": "READ_ONLY_POST_HOC",
            "future_data_policy": "PIT_SAFE_RUN_SCOPED_EVIDENCE_ONLY",
        },
    }


def validate_daily_evaluation_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    required = [
        "schema_version",
        "run_id",
        "business_date",
        "source_revision",
        "runtime_mode",
        "run_eligibility_status",
        "metric_contract_version",
        "source_artifact_refs",
        "evidence_status",
        "capital",
        "returns",
        "risk",
        "activity",
        "opportunity_utilization",
        "benchmark",
        "attribution_inputs",
        "missing_fields",
        "warnings",
    ]
    missing = [field for field in required if field not in payload]
    capital = payload.get("capital") if isinstance(payload.get("capital"), dict) else {}
    capital_required = [
        "initial_or_bootstrap_capital",
        "runtime_evaluation_capital_used_as_current",
        "buying_power",
        "cash",
        "market_value",
        "total_equity",
        "cash_ratio",
        "gross_exposure_ratio",
        "net_exposure_ratio",
        "position_count",
        "idle_cash",
        "target_gross_exposure_ratio",
        "target_cash_reserve_ratio",
        "policy_cash_buffer",
        "pending_reserved_cash",
        "actual_deployed_notional",
        "executed_buy_notional",
        "executed_sell_notional",
    ]
    missing_capital = [field for field in capital_required if field not in capital]
    opp = payload.get("opportunity_utilization") if isinstance(payload.get("opportunity_utilization"), dict) else {}
    opp_required = [
        "generated_opportunity_count",
        "eligible_opportunity_count",
        "planned_buy_count",
        "submitted_buy_count",
        "executed_buy_count",
        "reject_reason_counts",
    ]
    missing_opp = [field for field in opp_required if field not in opp]
    status = "PASS" if not missing and not missing_capital and not missing_opp else "REVIEW_REQUIRED"
    return {
        "schema_version": "phase25_daily_evaluation_evidence_validation.v1",
        "status": status,
        "missing_top_level_fields": missing,
        "missing_capital_fields": missing_capital,
        "missing_opportunity_utilization_fields": missing_opp,
    }


def _build_capital(
    *,
    current_state: dict[str, Any],
    valuation_projection: dict[str, Any],
    portfolio_policy: dict[str, Any],
    position_sizing: dict[str, Any],
    fills_payload: dict[str, Any],
) -> dict[str, Any]:
    cash = _pick_number(current_state, valuation_projection, keys=("cash",))
    buying_power = _pick_number(current_state, valuation_projection, keys=("buying_power",))
    market_value = _pick_number(current_state, valuation_projection, keys=("market_value", "new_total_market_value"))
    total_equity = _pick_number(current_state, valuation_projection, keys=("total_equity",))
    position_count = _position_count(current_state=current_state, valuation_projection=valuation_projection)
    target_cash = _number(portfolio_policy.get("cash_reserve_ratio"), portfolio_policy.get("cash_reserve"))
    target_gross = _number(position_sizing.get("aggregate_exposure_cap"), position_sizing.get("dynamic_cash_exposure"))
    executed = _execution_notional(fills_payload=fills_payload)
    policy_cash_buffer = total_equity * target_cash if total_equity is not None and target_cash is not None else None
    pending_reserved_cash = None
    gross_exposure = market_value / total_equity if _positive(total_equity) and market_value is not None else None
    cash_ratio = cash / total_equity if _positive(total_equity) and cash is not None else None
    idle_cash = cash - (policy_cash_buffer or 0.0) - (pending_reserved_cash or 0.0) if cash is not None and policy_cash_buffer is not None else None
    return {
        "initial_or_bootstrap_capital": _observed_number(
            current_state.get("initial_or_bootstrap_capital")
            or current_state.get("initial_capital")
            or current_state.get("bootstrap_capital")
            or current_state.get("runtime_evaluation_capital")
        ),
        "runtime_evaluation_capital_used_as_current": {"value": False, "status": "OBSERVED"},
        "buying_power": _observed_number(buying_power),
        "cash": _observed_number(cash),
        "market_value": _observed_number(market_value),
        "total_equity": _observed_number(total_equity),
        "cash_ratio": _observed_number(cash_ratio, status="DERIVED"),
        "gross_exposure_ratio": _observed_number(gross_exposure, status="DERIVED"),
        "net_exposure_ratio": _observed_number(gross_exposure, status="DERIVED"),
        "position_count": _observed_number(position_count),
        "idle_cash": _observed_number(idle_cash, status="DERIVED"),
        "target_gross_exposure_ratio": _observed_number(target_gross),
        "target_cash_reserve_ratio": _observed_number(target_cash),
        "policy_cash_buffer": _observed_number(policy_cash_buffer, status="DERIVED"),
        "pending_reserved_cash": OBS_NOT_OBSERVABLE,
        "actual_deployed_notional": _observed_number(market_value),
        "executed_buy_notional": _observed_number(executed["buy"], status=executed["status"]),
        "executed_sell_notional": _observed_number(executed["sell"], status=executed["status"]),
        "authority": "EOD_CURRENT_AFTER_EXECUTION_AND_CURRENT_VALUATION_REFRESH",
    }


def _build_returns(*, capital: dict[str, Any], previous_daily_evidence: dict[str, Any] | None, fresh_summary: dict[str, Any]) -> dict[str, Any]:
    equity = _value(capital.get("total_equity"))
    previous_equity = _value(((previous_daily_evidence or {}).get("capital") or {}).get("total_equity"))
    initial = _number(fresh_summary.get("initial_cash"), fresh_summary.get("initial_equity"))
    daily_return = (equity / previous_equity - 1.0) if _positive(equity) and _positive(previous_equity) else None
    cumulative = (equity / initial - 1.0) if _positive(equity) and _positive(initial) else None
    return {
        "daily_return": _observed_number(daily_return, status="DERIVED"),
        "cumulative_return": _observed_number(cumulative, status="DERIVED"),
        "previous_total_equity": _observed_number(previous_equity),
        "initial_equity": _observed_number(initial),
    }


def _build_risk(*, capital: dict[str, Any], previous_daily_evidence: dict[str, Any] | None) -> dict[str, Any]:
    equity = _value(capital.get("total_equity"))
    previous_risk = (previous_daily_evidence or {}).get("risk") if isinstance((previous_daily_evidence or {}).get("risk"), dict) else {}
    previous_peak = _value(previous_risk.get("running_peak_equity"))
    peak = max(value for value in (equity, previous_peak) if value is not None) if any(value is not None for value in (equity, previous_peak)) else None
    drawdown = (equity - peak) / peak if _positive(equity) and _positive(peak) else None
    return {
        "running_peak_equity": _observed_number(peak, status="DERIVED"),
        "drawdown": _observed_number(drawdown, status="DERIVED"),
    }


def _build_activity(*, fills_payload: dict[str, Any]) -> dict[str, Any]:
    fills = _rows(fills_payload, "fills")
    buy_count = sum(1 for row in fills if str(row.get("side") or "").upper() == "BUY")
    sell_count = sum(1 for row in fills if str(row.get("side") or "").upper() == "SELL")
    notional = _execution_notional(fills_payload=fills_payload)
    status = "AVAILABLE" if fills_payload else "NOT_OBSERVABLE"
    return {
        "trade_count": {"value": buy_count + sell_count, "status": status},
        "buy_execution_count": {"value": buy_count, "status": status},
        "sell_execution_count": {"value": sell_count, "status": status},
        "turnover_inputs": {
            "buy_execution_notional": _observed_number(notional["buy"], status=notional["status"]),
            "sell_execution_notional": _observed_number(notional["sell"], status=notional["status"]),
            "total_execution_notional": _observed_number(notional["buy"] + notional["sell"], status=notional["status"]),
        },
    }


def _build_opportunity_utilization(
    *,
    runtime_planning: dict[str, Any],
    planning_evidence: dict[str, Any],
    submitted_order_authority: dict[str, Any],
    fills_payload: dict[str, Any],
) -> dict[str, Any]:
    plans = _rows(runtime_planning, "plans")
    lineage_items = _rows(planning_evidence.get("lineage") if isinstance(planning_evidence.get("lineage"), dict) else {}, "items")
    source_rows = plans if plans else lineage_items
    source_status = "AVAILABLE" if source_rows else "NOT_OBSERVABLE"

    eligible = _count_eligible_opportunities(source_rows) if source_rows else None
    planned_buy = sum(1 for row in source_rows if _is_planned_buy(row)) if source_rows else None
    fills = _rows(fills_payload, "fills")
    executed_buy = sum(1 for row in fills if str(row.get("side") or "").upper() == "BUY") if fills_payload else None
    submitted_buy = _submitted_buy_count(submitted_order_authority)
    reject_counts = _reject_reason_counts(source_rows) if source_rows else _not_observable_reject_counts()
    pipeline = [
        {"stage": "Generated Opportunity", "count": _observed_number(len(source_rows), status=source_status) if source_rows else OBS_NOT_OBSERVABLE},
        {"stage": "Eligible", "count": _observed_number(eligible, status="DERIVED" if source_rows else "NOT_OBSERVABLE")},
        {"stage": "Planned", "count": _observed_number(planned_buy, status="DERIVED" if source_rows else "NOT_OBSERVABLE")},
        {"stage": "Submitted", "count": submitted_buy},
        {"stage": "Executed", "count": _observed_number(executed_buy, status="DERIVED" if fills_payload else "NOT_OBSERVABLE")},
    ]
    return {
        "status": source_status,
        "authority": "RUN_SCOPED_STRATEGY_RUNTIME_PLANNING_AND_EXECUTION_EVIDENCE",
        "generated_opportunity_count": _observed_number(len(source_rows), status=source_status) if source_rows else OBS_NOT_OBSERVABLE,
        "eligible_opportunity_count": _observed_number(eligible, status="DERIVED" if source_rows else "NOT_OBSERVABLE"),
        "planned_buy_count": _observed_number(planned_buy, status="DERIVED" if source_rows else "NOT_OBSERVABLE"),
        "submitted_buy_count": submitted_buy,
        "executed_buy_count": _observed_number(executed_buy, status="DERIVED" if fills_payload else "NOT_OBSERVABLE"),
        "reject_reason_counts": reject_counts,
        "pipeline": pipeline,
        "classification_policy": "EVIDENCE_ONLY_NO_INFERENCE; unclassified observable rejects become unknown_constraint_count.",
    }


def _build_benchmark(*, benchmark_snapshot: dict[str, Any]) -> dict[str, Any]:
    if not benchmark_snapshot:
        return {"status": "MISSING", "benchmark_source": "NOT_CONFIRMED", "daily_return": OBS_NOT_AVAILABLE}
    return {
        "status": str(benchmark_snapshot.get("status") or "MISSING"),
        "benchmark_id": benchmark_snapshot.get("benchmark_id", ""),
        "benchmark_name": benchmark_snapshot.get("benchmark_name", ""),
        "benchmark_source": benchmark_snapshot.get("benchmark_source", "NOT_CONFIRMED"),
        "daily_return": benchmark_snapshot.get("daily_return", OBS_NOT_AVAILABLE),
    }


def _candidate_current(current_manifest: dict[str, Any]) -> dict[str, Any]:
    artifact = current_manifest.get("artifact") if isinstance(current_manifest.get("artifact"), dict) else {}
    current = artifact.get("candidate_current") if isinstance(artifact.get("candidate_current"), dict) else {}
    return current


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


def _missing_fields(*, capital: dict[str, Any], returns: dict[str, Any], risk: dict[str, Any], opportunity_utilization: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for prefix, payload in (("capital", capital), ("returns", returns), ("risk", risk), ("opportunity_utilization", opportunity_utilization)):
        for key, value in payload.items():
            if isinstance(value, dict) and str(value.get("status") or "") in {"NOT_AVAILABLE", "NOT_OBSERVABLE", "UNKNOWN"}:
                missing.append(f"{prefix}.{key}")
    return sorted(missing)


def _warnings(
    *,
    current_state: dict[str, Any],
    valuation_apply: dict[str, Any],
    benchmark: dict[str, Any],
    opportunity_utilization: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if not current_state:
        warnings.append("CURRENT_VALUATION_CANDIDATE_CURRENT_NOT_OBSERVABLE")
    if valuation_apply and str(valuation_apply.get("status") or "") not in {"PASS", "APPLIED", "READY"}:
        warnings.append("CURRENT_VALUATION_APPLY_STATUS_NOT_PASS")
    if benchmark.get("status") == "MISSING":
        warnings.append("BENCHMARK_MISSING")
    if opportunity_utilization.get("status") == "NOT_OBSERVABLE":
        warnings.append("OPPORTUNITY_UTILIZATION_NOT_OBSERVABLE")
    return warnings


def _run_eligibility_status(*, run_state: dict[str, Any], final_summary: dict[str, Any]) -> str:
    status = str(final_summary.get("status") or run_state.get("status") or "UNKNOWN")
    if status in {"PASS", "COMPLETED", "CLOSED"}:
        return "COMPLETE"
    if status == "ABANDONED":
        return "DIAGNOSTIC_ONLY_ABANDONED"
    if status in {"HALT", "REVIEW_REQUIRED"}:
        return "DIAGNOSTIC_ONLY_REVIEW_REQUIRED"
    return status


def _source_revision(*, run_state: dict[str, Any]) -> dict[str, Any]:
    baseline = run_state.get("source_baseline") if isinstance(run_state.get("source_baseline"), dict) else {}
    return {
        "source_commit": baseline.get("source_commit", ""),
        "source_dirty": baseline.get("source_dirty", OBS_UNKNOWN),
        "registry_hash": baseline.get("registry_hash", ""),
        "accepted_artifact_hash": baseline.get("accepted_artifact_hash", ""),
    }


def _completed_business_days(*, run_state: dict[str, Any], fresh_summary: dict[str, Any]) -> list[str]:
    days = run_state.get("completed_business_days") or fresh_summary.get("completed_days") or []
    return sorted(str(day) for day in days if str(day))


def _execution_notional(*, fills_payload: dict[str, Any]) -> dict[str, Any]:
    if not fills_payload:
        return {"buy": None, "sell": None, "status": "NOT_OBSERVABLE"}
    buy = 0.0
    sell = 0.0
    for row in _rows(fills_payload, "fills"):
        side = str(row.get("side") or "").upper()
        notional = _value(row.get("gross_notional"))
        if notional is None:
            qty = _number(row.get("quantity"))
            price = _number(row.get("execution_price"), row.get("price"))
            notional = qty * price if qty is not None and price is not None else None
        if notional is None:
            continue
        if side == "BUY":
            buy += notional
        if side == "SELL":
            sell += notional
    return {"buy": buy, "sell": sell, "status": "DERIVED"}


def _submitted_buy_count(submitted_order_authority: dict[str, Any]) -> dict[str, Any]:
    if not submitted_order_authority:
        return OBS_NOT_OBSERVABLE
    refs = submitted_order_authority.get("execution_references")
    if isinstance(refs, list):
        buy_refs = [row for row in refs if isinstance(row, dict) and str(row.get("side") or row.get("order_side") or "").upper() == "BUY"]
        if buy_refs or any(isinstance(row, dict) and str(row.get("side") or row.get("order_side") or "") for row in refs):
            return {"value": len(buy_refs), "status": "DERIVED"}
    action = str(submitted_order_authority.get("submit_action") or submitted_order_authority.get("execution_action") or "")
    if action == "NO_ACTION":
        return {"value": 0, "status": "AVAILABLE"}
    count = submitted_order_authority.get("submitted_order_count")
    if count in (0, "0"):
        return {"value": 0, "status": "AVAILABLE"}
    return OBS_UNKNOWN


def _count_eligible_opportunities(rows: list[dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        authority = row.get("opportunity_authority") if isinstance(row.get("opportunity_authority"), dict) else {}
        eligibility = str(authority.get("opportunity_eligibility") or row.get("opportunity_eligibility") or "")
        status = str(authority.get("opportunity_status") or row.get("opportunity_status") or "")
        if eligibility == "BUY_ELIGIBLE" or status == "PASS":
            count += 1
    return count


def _is_planned_buy(row: dict[str, Any]) -> bool:
    intent = str(row.get("planning_intent") or "").upper()
    side = str(row.get("order_side_intent") or "").upper()
    quantity = _number(row.get("planned_quantity"), row.get("target_quantity_candidate"), row.get("quantity_delta_candidate"))
    return intent in {"BUY_NEW", "BUY_ADD"} or side == "BUY" or (quantity is not None and quantity > 0 and intent.startswith("BUY"))


def _reject_reason_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = {
        "capital_constraint_count": 0,
        "position_count_constraint_count": 0,
        "safety_constraint_count": 0,
        "eligibility_constraint_count": 0,
        "lot_size_constraint_count": 0,
        "price_constraint_count": 0,
        "planning_rejection_count": 0,
        "unknown_constraint_count": 0,
    }
    for row in rows:
        if _is_planned_buy(row):
            continue
        reasons = _reason_text(row)
        matched = False
        if any(token in reasons for token in ("capital", "cash", "exposure", "minimum_notional")):
            buckets["capital_constraint_count"] += 1
            matched = True
        if any(token in reasons for token in ("position_count", "max_position", "maximum_position", "max_positions")):
            buckets["position_count_constraint_count"] += 1
            matched = True
        if "safety" in reasons:
            buckets["safety_constraint_count"] += 1
            matched = True
        if "eligib" in reasons or "not_eligible" in reasons:
            buckets["eligibility_constraint_count"] += 1
            matched = True
        if "lot" in reasons:
            buckets["lot_size_constraint_count"] += 1
            matched = True
        if "price" in reasons:
            buckets["price_constraint_count"] += 1
            matched = True
        intent = str(row.get("planning_intent") or "").upper()
        if intent in {"NO_ACTION", "NO_ORDER"} or "no_action" in reasons or "no_order" in reasons:
            buckets["planning_rejection_count"] += 1
            matched = True
        if not matched:
            buckets["unknown_constraint_count"] += 1
    return {key: {"value": value, "status": "DERIVED"} for key, value in buckets.items()}


def _not_observable_reject_counts() -> dict[str, Any]:
    return {
        key: OBS_NOT_OBSERVABLE
        for key in (
            "capital_constraint_count",
            "position_count_constraint_count",
            "safety_constraint_count",
            "eligibility_constraint_count",
            "lot_size_constraint_count",
            "price_constraint_count",
            "planning_rejection_count",
            "unknown_constraint_count",
        )
    }


def _reason_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("planning_reason", "no_order_reason", "reason", "quantity_status", "pending_eligibility", "planning_intent"):
        value = row.get(key)
        if value not in (None, ""):
            parts.append(str(value))
    for key in ("reason_codes", "direct_reason_codes"):
        value = row.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
    return " ".join(parts).lower()


def _position_count(*, current_state: dict[str, Any], valuation_projection: dict[str, Any]) -> int | None:
    positions = current_state.get("positions")
    if isinstance(positions, list):
        return len(positions)
    count = _number(current_state.get("position_count"), valuation_projection.get("position_count"), valuation_projection.get("valued_position_count"))
    return int(count) if count is not None else None


def _pick_number(*payloads: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for payload in payloads:
        for key in keys:
            value = _number(payload.get(key))
            if value is not None:
                return value
    return None


def _observed_number(value: Any, status: str = "AVAILABLE") -> dict[str, Any]:
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


def _positive(value: Any) -> bool:
    number = _number(value)
    return number is not None and number > 0


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
