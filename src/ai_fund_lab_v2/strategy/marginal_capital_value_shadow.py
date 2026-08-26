from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_fund_lab_v2.strategy import marginal_capital_value


SCHEMA_VERSION = "marginal_capital_value_shadow.v1"
PRODUCER = "strategy.marginal_capital_value_shadow"
AUTHORITY_TYPE = "MARGINAL_CAPITAL_VALUE_AUTHORITY_SHADOW"
MODE = "NON_MUTATING_SHADOW"

COMPARISON_CLASSES = marginal_capital_value.COMPARISON_CLASSES


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "marginal_capital_value_shadow" / business_date / "marginal_capital_value_shadow.json"


def build_marginal_capital_value_shadow_payload(
    *,
    business_date: str,
    portfolio_construction_payload: Mapping[str, Any],
    position_sizing_payload: Mapping[str, Any] | None = None,
    runtime_planning_payload: Mapping[str, Any] | None = None,
    pending_payload: Mapping[str, Any] | None = None,
    strategy_planning_authority_payload: Mapping[str, Any] | None = None,
    market_context_payload: Mapping[str, Any] | None = None,
    source_artifacts: Mapping[str, Any] | None = None,
    source_hashes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pc_members = _rows(portfolio_construction_payload, "portfolio_members", "members")
    ps_by_symbol = {_symbol(row): row for row in _rows(position_sizing_payload or {}, "positions", "position_sizing_decisions", "sizing_decisions") if _symbol(row)}
    actual_runtime_items = _actual_runtime_items(runtime_planning_payload or {})
    actual_runtime_order = {item["symbol"]: int(item["actual_runtime_order"]) for item in actual_runtime_items}
    actual_pending_membership = _pending_membership(pending_payload or {})
    pending_cash_authority = _pending_cash_authority(strategy_planning_authority_payload or {})
    pending_cash_items = _pending_cash_items(pending_cash_authority)
    market_context_state = _market_context_state(market_context_payload or {})

    candidate_units = [
        _candidate_unit(
            row,
            ps_by_symbol=ps_by_symbol,
            actual_pc_index=index + 1,
            actual_runtime_order=actual_runtime_order,
            market_context_state=market_context_state,
        )
        for index, row in enumerate(pc_members)
        if _candidate_intent(row) and _accepted_increment(row) > 0
    ]
    ordered = sorted(candidate_units, key=_shadow_sort_key)
    for index, candidate in enumerate(ordered, start=1):
        candidate["canonical_shadow_priority_index"] = index
        candidate["shadow_priority"] = index
    _enrich_pending_cash_causality(ordered, pending_cash_items=pending_cash_items)

    canonical_shadow_order = [_unit_order_row(item) for item in ordered]
    actual_pc_order = [_actual_order_row(item, field="actual_pc_order") for item in sorted(candidate_units, key=lambda item: item["actual_pc_order"])]
    actual_runtime_by_symbol = {item["symbol"]: item for item in actual_runtime_items}
    actual_runtime_cash_batch_order = [
        _actual_runtime_order_row(item, actual_runtime_by_symbol=actual_runtime_by_symbol)
        for item in sorted(
            (item for item in candidate_units if item.get("actual_runtime_order") is not None),
            key=lambda item: item["actual_runtime_order"],
        )
    ]
    order_differences = _order_differences(ordered, actual_pc_order=actual_pc_order, actual_runtime_order=actual_runtime_cash_batch_order)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "business_date": business_date,
        "producer": PRODUCER,
        "authority_type": AUTHORITY_TYPE,
        "mode": MODE,
        "pit_status": "PIT_CURRENT_STRATEGY_EVIDENCE_ONLY",
        "future_information_used": False,
        "candidate_units": ordered,
        "canonical_shadow_order": canonical_shadow_order,
        "actual_pc_order": actual_pc_order,
        "actual_runtime_cash_batch_order": actual_runtime_cash_batch_order,
        "actual_pending_cash_batch_order": [_pending_cash_order_row(item) for item in pending_cash_items],
        "order_differences": order_differences,
        "comparison_status": _comparison_status(ordered),
        "lot_materialization_status": _lot_materialization_status(ordered),
        "pending_cash_authority": pending_cash_authority,
        "pending_cash_causality_status": _pending_cash_causality_status(ordered, pending_cash_authority),
        "source_artifacts": dict(source_artifacts or {}),
        "source_hashes": dict(source_hashes or {}),
        "actual_pending_membership": actual_pending_membership,
        "actual_decision_mutated": False,
        "actual_pc_decision_mutated": False,
        "actual_ps_quantity_mutated": False,
        "actual_runtime_order_mutated": False,
        "actual_pending_mutated": False,
        "actual_submit_mutated": False,
        "actual_submit_or_execution_mutated": False,
        "actual_execution_mutated": False,
        "actual_fill_mutated": False,
        "actual_run_state_mutated": False,
        "actual_trading_path_mutated": False,
        "buy_add_label_priority": False,
        "buy_new_label_priority": False,
        "normal_strategy_cap_changed": False,
        "safety_hard_cap_changed": False,
        "buy_sell_independence_preserved": True,
        "b0_development_cases_reproducible": _b0_development_case_observed(candidate_units),
        "metrics": _metrics(ordered, order_differences),
    }
    payload["metrics"].update(_pending_cash_metrics(ordered))
    return {**payload, "artifact_hash": stable_payload_hash(payload)}


def write_marginal_capital_value_shadow_artifact(payload: Mapping[str, Any], output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def materialize_marginal_capital_value_shadow_for_day(
    *,
    run_root: Path | str,
    business_date: str,
    output_subdir: str = "diagnostic_shadow",
) -> dict[str, Any]:
    run_root = Path(run_root)
    day_dir = run_root / "daily" / business_date
    strategy_dir = day_dir / "strategy"
    pc_path = strategy_dir / "portfolio_construction.json"
    ps_path = strategy_dir / "position_sizing.json"
    rp_path = strategy_dir / "runtime_planning.json"
    pending_path = day_dir / "morning" / "pending_generation_evidence.json"
    strategy_planning_authority_path = day_dir / "morning" / "strategy_planning_authority_evidence.json"
    payload = build_marginal_capital_value_shadow_payload(
        business_date=business_date,
        portfolio_construction_payload=_load_json(pc_path),
        position_sizing_payload=_load_json(ps_path),
        runtime_planning_payload=_load_json(rp_path),
        pending_payload=_load_json(pending_path),
        strategy_planning_authority_payload=_load_json(strategy_planning_authority_path),
        source_artifacts={
            "portfolio_construction": str(pc_path),
            "position_sizing": str(ps_path),
            "runtime_planning": str(rp_path),
            "pending_generation_evidence": str(pending_path),
            "strategy_planning_authority_evidence": str(strategy_planning_authority_path),
        },
        source_hashes={
            "portfolio_construction": _file_hash(pc_path),
            "position_sizing": _file_hash(ps_path),
            "runtime_planning": _file_hash(rp_path),
            "pending_generation_evidence": _file_hash(pending_path),
            "strategy_planning_authority_evidence": _file_hash(strategy_planning_authority_path),
        },
    )
    output_path = day_dir / output_subdir / "marginal_capital_value_shadow.json"
    write_marginal_capital_value_shadow_artifact(payload, output_path)
    return {**payload, "artifact_path": str(output_path)}


def materialize_marginal_capital_value_shadow_for_run(
    *,
    run_root: Path | str,
    business_dates: Sequence[str] | None = None,
    output_subdir: str = "diagnostic_shadow",
    mixed_new_add_only: bool = True,
) -> dict[str, Any]:
    run_root = Path(run_root)
    dates = list(business_dates or _completed_business_days(run_root))
    materialized: list[dict[str, Any]] = []
    for business_date in dates:
        pc_path = run_root / "daily" / business_date / "strategy" / "portfolio_construction.json"
        if not pc_path.is_file():
            continue
        pc_payload = _load_json(pc_path)
        if mixed_new_add_only and not _has_mixed_new_add_candidates(pc_payload):
            continue
        payload = materialize_marginal_capital_value_shadow_for_day(
            run_root=run_root,
            business_date=business_date,
            output_subdir=output_subdir,
        )
        materialized.append(
            {
                "business_date": business_date,
                "artifact_path": payload["artifact_path"],
                "candidate_count": len(payload.get("candidate_units") or []),
                "comparison_status": payload.get("comparison_status"),
            }
        )
    return {
        "schema_version": "marginal_capital_value_shadow_materialization_summary.v1",
        "run_root": str(run_root),
        "output_subdir": output_subdir,
        "mixed_new_add_only": mixed_new_add_only,
        "materialized_day_count": len(materialized),
        "materialized_item_count": sum(int(item["candidate_count"]) for item in materialized),
        "materialized": materialized,
        "actual_trading_path_mutated": False,
    }


def stable_payload_hash(payload: Mapping[str, Any]) -> str:
    canonical = {key: value for key, value in dict(payload).items() if key != "artifact_hash"}
    encoded = json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _candidate_unit(
    row: Mapping[str, Any],
    *,
    ps_by_symbol: Mapping[str, Mapping[str, Any]],
    actual_pc_index: int,
    actual_runtime_order: Mapping[str, int],
    market_context_state: str,
) -> dict[str, Any]:
    symbol = _symbol(row)
    ps_row = ps_by_symbol.get(symbol, {})
    lifecycle_intent = _candidate_intent(row) or "UNKNOWN"
    expected_edge = _state(row, "expected_edge_improvement_state", "add_expected_edge_improvement_state", default="UNKNOWN")
    incremental_value = _state(row, "incremental_investment_value_state", "add_incremental_investment_value_state", default="UNKNOWN")
    opportunity_cost = _state(row, "opportunity_cost_status", "add_opportunity_cost_status", default="UNKNOWN")
    comparison_class, sufficiency, reasons = _classify(row, lifecycle_intent=lifecycle_intent, expected_edge=expected_edge, incremental_value=incremental_value, opportunity_cost=opportunity_cost)
    accepted_increment = _accepted_increment(row)
    lot_requirement = _lot_requirement(row, ps_row)
    return {
        "symbol": symbol,
        "item_id": str(row.get("item_id") or row.get("member_id") or row.get("portfolio_member_id") or symbol),
        "lifecycle_intent": lifecycle_intent,
        "marginal_capital_value_class": comparison_class,
        "canonical_shadow_priority_index": None,
        "comparison_reason_codes": reasons,
        "source_evidence": _source_evidence(row),
        "add_campaign_evidence": _add_campaign_evidence(row),
        "expected_edge_state": expected_edge,
        "incremental_investment_value_state": incremental_value,
        "opportunity_cost_state": opportunity_cost,
        "opportunity_rank": _number(row.get("input_opportunity_rank") or row.get("opportunity_rank")),
        "market_context_state": str(row.get("market_context_state") or market_context_state or "UNKNOWN"),
        "current_weight": _number(row.get("current_weight"), 0.0),
        "target_weight": _number(row.get("target_weight"), 0.0),
        "accepted_incremental_weight": accepted_increment,
        "lot_aware_quantity_requirement": lot_requirement,
        "lot_feasibility": _lot_feasibility(row, ps_row),
        "concentration_status": str(row.get("concentration_status") or row.get("strategy_cap_status") or row.get("safety_concentration_status") or "UNKNOWN"),
        "comparison_sufficiency": sufficiency,
        "actual_pc_order": actual_pc_index,
        "actual_pc_priority": _number(row.get("construction_priority"), actual_pc_index),
        "actual_runtime_order": actual_runtime_order.get(symbol),
        "actual_runtime_priority": actual_runtime_order.get(symbol),
        "lot_materialization_reason": _lot_materialization_reason(row, ps_row, actual_runtime_order.get(symbol)),
    }


def _classify(
    row: Mapping[str, Any],
    *,
    lifecycle_intent: str,
    expected_edge: str,
    incremental_value: str,
    opportunity_cost: str,
) -> tuple[str, str, list[str]]:
    return marginal_capital_value.classify_candidate({**dict(row), "lifecycle_intent": lifecycle_intent})


def _candidate_intent(row: Mapping[str, Any]) -> str:
    return marginal_capital_value.candidate_intent(row)


def _accepted_increment(row: Mapping[str, Any]) -> float:
    return marginal_capital_value.accepted_increment(row)


def _shadow_sort_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    return marginal_capital_value.sort_key(item)


def _order_differences(
    ordered: Sequence[Mapping[str, Any]],
    *,
    actual_pc_order: Sequence[Mapping[str, Any]],
    actual_runtime_order: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    shadow_index = {str(row["symbol"]): int(row["canonical_shadow_priority_index"]) for row in ordered}
    actual_index = {str(row["symbol"]): int(row["order"]) for row in (actual_runtime_order or actual_pc_order)}
    differences = []
    for item in ordered:
        symbol = str(item["symbol"])
        actual = actual_index.get(symbol)
        shadow = shadow_index[symbol]
        if actual is None or actual == shadow:
            classification = "NO_DIFFERENCE"
        elif item.get("comparison_sufficiency") == "INSUFFICIENT":
            classification = "COMPARISON_INSUFFICIENT"
        elif str(item.get("lot_feasibility") or "").upper() not in {"", "PASS", "UNKNOWN"}:
            classification = "LEGITIMATE_FEASIBILITY_DIFFERENCE"
        else:
            classification = "ACTUAL_ORDER_PROCESSING_ARTIFACT"
        differences.append(
            {
                "symbol": symbol,
                "lifecycle_intent": item.get("lifecycle_intent"),
                "canonical_shadow_priority_index": shadow,
                "actual_order": actual,
                "classification": classification,
            }
        )
    return differences


def _actual_runtime_items(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = _rows(payload, "cash_batch", "cash_batch_order", "buy_cash_batch", "planning_items", "items")
    if not rows:
        rows = _rows(payload, "plans")
    order: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        symbol = _symbol(row)
        if symbol and _is_buyish(row):
            quantity = _number(row.get("planned_quantity") or row.get("quantity") or row.get("quantity_delta_candidate"), 0.0) or 0.0
            price = _number(row.get("reference_price"), 0.0) or 0.0
            planned_notional = _number(
                row.get("reserved_notional")
                or row.get("reserved_buy_notional")
                or row.get("cash_reserved_notional")
                or row.get("planned_notional")
                or row.get("target_notional")
            )
            if planned_notional is None and quantity > 0 and price > 0:
                planned_notional = round(quantity * price, 2)
            status = _runtime_item_status(row)
            order.append(
                {
                    "symbol": symbol,
                    "side": str(row.get("side") or row.get("order_side_intent") or "BUY"),
                    "item_id": str(row.get("planning_id") or row.get("item_id") or row.get("id") or symbol),
                    "planning_intent": str(row.get("planning_intent") or row.get("intent") or row.get("lifecycle_intent") or ""),
                    "quantity": quantity,
                    "planned_notional": planned_notional,
                    "actual_runtime_order": int(_number(row.get("canonical_priority_index") or row.get("priority_index") or row.get("order"), index) or index),
                    "inclusion_state": status,
                    "reason": str(row.get("planning_reason") or row.get("reason") or row.get("no_order_reason") or ""),
                }
            )
    return order


def _pending_membership(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"symbol": _symbol(row), "side": str(row.get("side") or row.get("intent") or row.get("action") or ""), "status": str(row.get("status") or "")}
        for row in _rows(payload, "pending_orders", "pending_items", "items")
        if _symbol(row)
    ]


def _rows(payload: Mapping[str, Any], *keys: str) -> list[Mapping[str, Any]]:
    for key in keys:
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, Mapping)]
    return []


def _source_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    return marginal_capital_value.source_evidence(row)


def _add_campaign_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    return marginal_capital_value.add_campaign_evidence(row)


def _lot_requirement(row: Mapping[str, Any], ps_row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "pc_discrete_quantity": _number(row.get("final_allocated_quantity") or row.get("discrete_authorized_quantity")),
        "ps_transaction_quantity_candidate": _number(ps_row.get("transaction_quantity_candidate")),
        "ps_quantity_delta_candidate": _number(ps_row.get("quantity_delta_candidate") or ps_row.get("final_quantity_delta")),
    }


def _lot_materialization_reason(row: Mapping[str, Any], ps_row: Mapping[str, Any], actual_runtime_order: int | None) -> str:
    if actual_runtime_order is None:
        return "NOT_IN_RUNTIME_PLAN"
    quantity = _number(ps_row.get("transaction_quantity_candidate") or ps_row.get("quantity_delta_candidate") or ps_row.get("final_quantity_delta"), 0.0) or 0.0
    if quantity <= 0:
        return "ZERO_QUANTITY_DELTA"
    lot = _lot_feasibility(row, ps_row).upper()
    if lot not in {"", "PASS", "UNKNOWN", "EXECUTABLE_NOW"}:
        return "LOT_NOT_FEASIBLE"
    reason_codes = " ".join(str(code) for code in (ps_row.get("reason_codes") or row.get("reason_codes") or []))
    if "CONCENTRATION" in reason_codes or "CAP" in reason_codes:
        return "CONCENTRATION_BOUND"
    if "BUDGET" in reason_codes:
        return "BUDGET_BOUND"
    return "EXECUTABLE_LOT"


def _lot_feasibility(row: Mapping[str, Any], ps_row: Mapping[str, Any]) -> str:
    resolution = ps_row.get("phase29_l19_lot_resolution") if isinstance(ps_row.get("phase29_l19_lot_resolution"), Mapping) else {}
    return str(
        row.get("lot_first_feasibility_classification")
        or resolution.get("one_lot_feasibility_status")
        or ps_row.get("one_lot_feasibility_status")
        or "UNKNOWN"
    )


def _pending_cash_authority(payload: Mapping[str, Any]) -> dict[str, Any]:
    lineage = payload.get("lineage") if isinstance(payload.get("lineage"), Mapping) else {}
    batch = lineage.get("cash_feasible_buy_batch") if isinstance(lineage.get("cash_feasible_buy_batch"), Mapping) else {}
    if not batch and isinstance(payload.get("cash_feasible_buy_batch"), Mapping):
        batch = payload.get("cash_feasible_buy_batch")  # type: ignore[assignment]
    if not batch:
        return {
            "status": "NOT_AVAILABLE",
            "producer": "runtime_v2.planning.strategy_authority._cash_feasible_buy_batch",
            "artifact": "strategy_planning_authority_evidence.json#lineage.cash_feasible_buy_batch",
            "field": "lineage.cash_feasible_buy_batch",
            "reserved_notional_source": "runtime_v2.order_reservation.resolve_order_cash_reservation",
            "item_processing_order_source": "cash_feasible_buy_batch.items[].canonical_priority_index",
            "temporal_binding": "business_date morning planning decision-time authority evidence",
        }
    items = _rows(batch, "items")
    return {
        "status": str(batch.get("status") or "UNKNOWN"),
        "contract_id": str(batch.get("contract_id") or ""),
        "producer": "runtime_v2.planning.strategy_authority._cash_feasible_buy_batch",
        "artifact": "strategy_planning_authority_evidence.json#lineage.cash_feasible_buy_batch",
        "field": "lineage.cash_feasible_buy_batch",
        "reserved_notional_source": str(
            batch.get("canonical_reserved_notional_producer") or "runtime_v2.order_reservation.resolve_order_cash_reservation"
        ),
        "pending_review_scope_artifact": "pending_generation_evidence.json + pending_order_plan referenced by strategy_planning_authority_evidence.pending_path",
        "item_processing_order_source": "cash_feasible_buy_batch.items[].canonical_priority_index",
        "temporal_binding": "business_date morning planning decision-time authority evidence",
        "selection_semantic": str(batch.get("selection_semantic") or ""),
        "cash_pruned_item_semantic": str(batch.get("cash_pruned_item_semantic") or "DEFERRED_INSUFFICIENT_RESERVED_CASH"),
        "starting_cash": _number(batch.get("starting_cash")),
        "starting_buying_power": _number(batch.get("starting_buying_power")),
        "final_reserved_notional_total": _number(batch.get("final_reserved_notional_total")),
        "remaining_reserved_cash": _number(batch.get("remaining_reserved_cash")),
        "candidate_buy_count": int(_number(batch.get("candidate_buy_count"), len(items)) or 0),
        "included_buy_count": int(_number(batch.get("included_buy_count"), 0.0) or 0),
        "cash_pruned_count": int(_number(batch.get("cash_pruned_count"), 0.0) or 0),
        "items": _pending_cash_items_from_batch(batch),
    }


def _pending_cash_items(authority_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = authority_payload.get("items")
    if isinstance(items, list):
        return [dict(row) for row in items if isinstance(row, Mapping) and _symbol(row)]
    return []


def _pending_cash_items_from_batch(batch: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [_pending_cash_item(row, index=index) for index, row in enumerate(_rows(batch, "items"), start=1) if _symbol(row)]


def _pending_cash_item(row: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    decision = str(row.get("decision") or "UNKNOWN").upper()
    reason = str(row.get("reason") or "")
    reserved_notional = _number(row.get("reserved_notional"), 0.0) or 0.0
    final_state = _final_pending_state(decision, reason)
    return {
        "symbol": _symbol(row),
        "actual_pending_order": int(_number(row.get("canonical_priority_index"), index) or index),
        "pre_batch_cash": None,
        "required_reserved_notional": reserved_notional,
        "cumulative_reserved_before_item": _number(row.get("reserved_cash_before_item")),
        "remaining_cash_before_item": _number(row.get("remaining_cash_before_item") or row.get("cash_before_item")),
        "included_reserved_notional": reserved_notional if final_state in {"INCLUDE", "REVIEW"} else 0.0,
        "remaining_cash_after_item": _number(row.get("reserved_cash_after_item") or row.get("remaining_cash_after_item")),
        "final_pending_state": final_state,
        "final_pending_scope": "BUY_CASH_FEASIBLE_BATCH",
        "final_cash_feasibility_result": _final_cash_feasibility_result(final_state, reason),
        "final_cash_reason_code": reason,
        "typed_guard_class": _typed_guard_class(final_state, reason),
        "typed_guard_code": _typed_guard_code(final_state, reason),
        "source_submit_feasibility_status": str(row.get("source_submit_feasibility_status") or ""),
        "source_violated_policy": str(row.get("source_violated_policy") or ""),
        "pending_item_id": str(row.get("pending_item_id") or ""),
    }


def _pending_cash_batch_from_authority_source(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    lineage = payload.get("lineage") if isinstance(payload.get("lineage"), Mapping) else {}
    batch = lineage.get("cash_feasible_buy_batch") if isinstance(lineage.get("cash_feasible_buy_batch"), Mapping) else {}
    if not batch and isinstance(payload.get("cash_feasible_buy_batch"), Mapping):
        batch = payload.get("cash_feasible_buy_batch")  # type: ignore[assignment]
    return batch


def _enrich_pending_cash_causality(rows: Sequence[dict[str, Any]], *, pending_cash_items: Sequence[Mapping[str, Any]]) -> None:
    by_symbol = {str(item.get("symbol")): dict(item) for item in pending_cash_items}
    ordered_pending = sorted((dict(item) for item in pending_cash_items), key=lambda item: int(item.get("actual_pending_order") or 999999))
    pre_batch_cash = None
    if ordered_pending:
        first = ordered_pending[0]
        pre_batch_cash = first.get("remaining_cash_before_item")
    for item in ordered_pending:
        item["pre_batch_cash"] = pre_batch_cash
        by_symbol[str(item.get("symbol"))] = item

    shadow_by_symbol = {str(row.get("symbol")): int(row.get("canonical_shadow_priority_index") or 999999) for row in rows}
    row_by_symbol = {str(row.get("symbol")): row for row in rows}
    prior_included_by_symbol: dict[str, list[dict[str, Any]]] = {}
    included_so_far: list[dict[str, Any]] = []
    for item in ordered_pending:
        symbol = str(item.get("symbol") or "")
        prior_included_by_symbol[symbol] = list(included_so_far)
        if item.get("final_pending_state") in {"INCLUDE", "REVIEW"} and float(item.get("included_reserved_notional") or 0.0) > 0:
            included_so_far.append(item)

    for row in rows:
        symbol = str(row.get("symbol") or "")
        item = by_symbol.get(symbol)
        if not item:
            row["actual_pending_order"] = None
            row["pending_cash_causality"] = {"status": "NOT_AVAILABLE", "cash_causality_classification": _upstream_classification(row)}
            continue
        causality = dict(item)
        classification = _cash_causality_classification(
            row=row,
            pending_item=item,
            prior_included=prior_included_by_symbol.get(symbol, []),
            shadow_by_symbol=shadow_by_symbol,
            row_by_symbol=row_by_symbol,
        )
        causality["cash_causality_classification"] = classification
        causality["starving_prior_items"] = _starving_prior_items(
            row=row,
            prior_included=prior_included_by_symbol.get(symbol, []),
            shadow_by_symbol=shadow_by_symbol,
            row_by_symbol=row_by_symbol,
        )
        row["actual_pending_order"] = item.get("actual_pending_order")
        row["pending_cash_causality"] = causality


def _final_pending_state(decision: str, reason: str) -> str:
    text = f"{decision} {reason}".upper()
    if "DEFERRED_INSUFFICIENT_RESERVED_CASH" in text:
        return "PRUNE"
    if "REVIEW" in text:
        return "REVIEW"
    if decision in {"INCLUDE", "PASS"}:
        return "INCLUDE"
    return decision or "UNKNOWN"


def _final_cash_feasibility_result(final_state: str, reason: str) -> str:
    if final_state == "PRUNE" and "DEFERRED_INSUFFICIENT_RESERVED_CASH" in reason.upper():
        return "FAIL"
    if final_state == "INCLUDE":
        return "PASS"
    if final_state == "REVIEW":
        return "REVIEW_REQUIRED"
    return "UNKNOWN"


def _typed_guard_class(final_state: str, reason: str) -> str:
    if final_state == "PRUNE" and "DEFERRED_INSUFFICIENT_RESERVED_CASH" in reason.upper():
        return "PENDING_RESERVED_CASH"
    if final_state == "REVIEW":
        return "PENDING_REVIEW_OR_SAFETY"
    if final_state == "INCLUDE":
        return "PENDING_CASH_FEASIBILITY_PASS"
    return "UNKNOWN"


def _typed_guard_code(final_state: str, reason: str) -> str:
    if final_state == "PRUNE" and "DEFERRED_INSUFFICIENT_RESERVED_CASH" in reason.upper():
        return "DEFERRED_INSUFFICIENT_RESERVED_CASH"
    if final_state == "REVIEW":
        return reason or "REVIEW_REQUIRED"
    if final_state == "INCLUDE":
        return "planning_submit_feasibility_pass"
    return reason or "UNKNOWN"


def _cash_causality_classification(
    *,
    row: Mapping[str, Any],
    pending_item: Mapping[str, Any],
    prior_included: Sequence[Mapping[str, Any]],
    shadow_by_symbol: Mapping[str, int],
    row_by_symbol: Mapping[str, Mapping[str, Any]],
) -> str:
    final_state = str(pending_item.get("final_pending_state") or "").upper()
    if final_state == "INCLUDE":
        return "NO_ACTUAL_STARVATION"
    if final_state == "REVIEW":
        return "LEGITIMATE_REVIEW_OR_SAFETY"
    if final_state != "PRUNE":
        upstream = _upstream_classification(row)
        if upstream != "NO_ACTUAL_STARVATION":
            return upstream
        return "UNRESOLVED"
    if str(pending_item.get("final_cash_reason_code") or "").upper() != "DEFERRED_INSUFFICIENT_RESERVED_CASH":
        return "LEGITIMATE_FEASIBILITY_PRUNE"

    shadow_priority = int(row.get("canonical_shadow_priority_index") or 999999)
    lower_value_prior = [
        item
        for item in prior_included
        if shadow_by_symbol.get(str(item.get("symbol") or ""), 999999) > shadow_priority
    ]
    if lower_value_prior:
        return "CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM"
    if any(
        shadow_by_symbol.get(str(item.get("symbol") or ""), 999999) < shadow_priority
        for item in prior_included
        if str(item.get("symbol") or "") in row_by_symbol
    ):
        return "LEGITIMATE_CANONICAL_LOWER_PRIORITY"
    return "LEGITIMATE_FEASIBILITY_PRUNE"


def _upstream_classification(row: Mapping[str, Any]) -> str:
    reason = str(row.get("lot_materialization_reason") or "").upper()
    concentration = str(row.get("concentration_status") or "").upper()
    if reason == "ZERO_QUANTITY_DELTA":
        return "NOT_REACHED_DUE_TO_UPSTREAM_ZERO_QUANTITY"
    if "LOT" in reason or str(row.get("lot_feasibility") or "").upper() not in {"", "PASS", "UNKNOWN", "EXECUTABLE_NOW"}:
        return "LOT_CONSTRAINT"
    if "CONCENTRATION" in reason or "CONCENTRATION" in concentration or "CAP" in concentration:
        return "CONCENTRATION_CONSTRAINT"
    return "NO_ACTUAL_STARVATION"


def _starving_prior_items(
    *,
    row: Mapping[str, Any],
    prior_included: Sequence[Mapping[str, Any]],
    shadow_by_symbol: Mapping[str, int],
    row_by_symbol: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    shadow_priority = int(row.get("canonical_shadow_priority_index") or 999999)
    rows: list[dict[str, Any]] = []
    for item in prior_included:
        symbol = str(item.get("symbol") or "")
        prior_shadow = shadow_by_symbol.get(symbol)
        if prior_shadow is None or prior_shadow <= shadow_priority:
            continue
        prior_row = row_by_symbol.get(symbol, {})
        rows.append(
            {
                "symbol": symbol,
                "lifecycle_intent": prior_row.get("lifecycle_intent", "UNKNOWN"),
                "shadow_priority": prior_shadow,
                "actual_pending_order": item.get("actual_pending_order"),
                "included_reserved_notional": item.get("included_reserved_notional"),
            }
        )
    return rows


def _pending_cash_order_row(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "symbol": item.get("symbol"),
        "order": item.get("actual_pending_order"),
        "final_pending_state": item.get("final_pending_state"),
        "required_reserved_notional": item.get("required_reserved_notional"),
        "remaining_cash_before_item": item.get("remaining_cash_before_item"),
        "remaining_cash_after_item": item.get("remaining_cash_after_item"),
        "reason": item.get("final_cash_reason_code"),
    }


def _pending_cash_causality_status(rows: Sequence[Mapping[str, Any]], authority: Mapping[str, Any]) -> str:
    if authority.get("status") == "NOT_AVAILABLE":
        return "NOT_AVAILABLE"
    if any((row.get("pending_cash_causality") or {}).get("status") == "NOT_AVAILABLE" for row in rows):
        return "PARTIAL"
    return "PASS"


def _comparison_status(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "NO_CANDIDATES"
    if any(row.get("comparison_sufficiency") == "INSUFFICIENT" for row in rows):
        return "COMPARISON_INSUFFICIENT_PRESENT"
    return "PASS"


def _lot_materialization_status(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "NO_CANDIDATES"
    if any(str(row.get("lot_feasibility") or "").upper() not in {"PASS", "UNKNOWN", ""} for row in rows):
        return "LOT_MATERIALIZATION_REVIEW_REQUIRED"
    return "LOT_AWARE_EVIDENCE_PRESERVED"


def _metrics(rows: Sequence[Mapping[str, Any]], differences: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_count": len(rows),
        "buy_new_count": sum(1 for row in rows if row.get("lifecycle_intent") == "BUY_NEW"),
        "buy_add_count": sum(1 for row in rows if row.get("lifecycle_intent") == "BUY_ADD"),
        "comparison_insufficient_count": sum(1 for row in rows if row.get("comparison_sufficiency") == "INSUFFICIENT"),
        "order_difference_count": sum(1 for row in differences if row.get("classification") != "NO_DIFFERENCE"),
    }


def _pending_cash_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cash_rows = [row for row in rows if isinstance(row.get("pending_cash_causality"), Mapping)]
    starvation = [
        row
        for row in cash_rows
        if (row.get("pending_cash_causality") or {}).get("cash_causality_classification")
        == "CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM"
    ]
    strong_starvation = [row for row in starvation if row.get("marginal_capital_value_class") == "ELIGIBLE_STRONG"]
    lower_included = [
        prior
        for row in starvation
        for prior in (row.get("pending_cash_causality") or {}).get("starving_prior_items", [])
    ]
    unexplained = [
        row
        for row in cash_rows
        if (row.get("pending_cash_causality") or {}).get("final_pending_state") == "PRUNE"
        and (row.get("pending_cash_causality") or {}).get("cash_causality_classification") == "UNRESOLVED"
    ]
    inversion_no_cash = [
        row
        for row in cash_rows
        if row.get("actual_pending_order") != row.get("canonical_shadow_priority_index")
        and (row.get("pending_cash_causality") or {}).get("cash_causality_classification") == "NO_ACTUAL_STARVATION"
    ]
    return {
        "pending_cash_causality_reconstructed_count": sum(
            1 for row in cash_rows if (row.get("pending_cash_causality") or {}).get("final_pending_state")
        ),
        "pending_cash_causality_unresolved_count": sum(
            1
            for row in rows
            if (row.get("pending_cash_causality") or {}).get("cash_causality_classification") in {"UNRESOLVED", None}
        ),
        "actual_starvation_count": len(starvation),
        "actual_starvation_notional": round(
            sum(float((row.get("pending_cash_causality") or {}).get("required_reserved_notional") or 0.0) for row in starvation),
            2,
        ),
        "strong_add_new_starved_count": len(strong_starvation),
        "strong_add_new_starved_notional": round(
            sum(float((row.get("pending_cash_causality") or {}).get("required_reserved_notional") or 0.0) for row in strong_starvation),
            2,
        ),
        "cash_prune_lower_canonical_included_count": len(lower_included),
        "unexplained_cash_prune_count": len(unexplained),
        "order_inversion_without_cash_effect_count": len(inversion_no_cash),
    }


def _has_mixed_new_add_candidates(payload: Mapping[str, Any]) -> bool:
    has_new = False
    has_add = False
    for row in _rows(payload, "portfolio_members", "members"):
        intent = _candidate_intent(row)
        if intent == "BUY_NEW" and _accepted_increment(row) > 0:
            has_new = True
        if intent == "BUY_ADD" and _accepted_increment(row) > 0:
            has_add = True
    return has_new and has_add


def _completed_business_days(run_root: Path) -> list[str]:
    state_path = run_root / "run_state.json"
    if not state_path.is_file():
        return sorted(path.name for path in (run_root / "daily").iterdir() if path.is_dir())
    state = _load_json(state_path)
    days = state.get("completed_business_days")
    return [str(day) for day in days] if isinstance(days, list) else []


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unit_order_row(item: Mapping[str, Any]) -> dict[str, Any]:
    return {"symbol": item["symbol"], "lifecycle_intent": item["lifecycle_intent"], "order": item["canonical_shadow_priority_index"]}


def _actual_order_row(item: Mapping[str, Any], *, field: str) -> dict[str, Any]:
    return {"symbol": item["symbol"], "lifecycle_intent": item["lifecycle_intent"], "order": item[field]}


def _actual_runtime_order_row(item: Mapping[str, Any], *, actual_runtime_by_symbol: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    runtime = actual_runtime_by_symbol.get(str(item["symbol"]), {})
    return {
        "symbol": item["symbol"],
        "lifecycle_intent": item["lifecycle_intent"],
        "order": item["actual_runtime_order"],
        "side": runtime.get("side", "BUY"),
        "item_id": runtime.get("item_id", ""),
        "quantity": runtime.get("quantity"),
        "planned_notional": runtime.get("planned_notional"),
        "inclusion_state": runtime.get("inclusion_state", "UNKNOWN"),
        "reason": runtime.get("reason", ""),
    }


def _market_context_state(payload: Mapping[str, Any]) -> str:
    return str(payload.get("market_context_state") or payload.get("canonical_market_context_state") or payload.get("risk_state") or "UNKNOWN")


def _b0_development_case_observed(rows: Sequence[Mapping[str, Any]]) -> bool:
    return any(str(row.get("symbol")) == "94320" for row in rows)


def _is_buyish(row: Mapping[str, Any]) -> bool:
    value = str(row.get("side") or row.get("order_side_intent") or row.get("action") or row.get("intent") or row.get("lifecycle_intent") or row.get("planning_intent") or "").upper()
    return value in {"", "BUY", "BUY_NEW", "BUY_ADD", "ADD"}


def _runtime_item_status(row: Mapping[str, Any]) -> str:
    text = " ".join(
        str(row.get(field) or "")
        for field in ("planning_reason", "reason", "no_order_reason", "pending_eligibility", "human_review_status")
    ).upper()
    if "DEFERRED_INSUFFICIENT_RESERVED_CASH" in text:
        return "RESERVED_CASH_PRUNE"
    if "REVIEW" in text:
        return "REVIEW_REQUIRED"
    if _number(row.get("planned_quantity") or row.get("quantity_delta_candidate"), 0.0):
        return "INCLUDED"
    return "ZERO_QUANTITY_DELTA"


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


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Materialize non-mutating marginal capital value shadow artifacts for an existing runtime-test run.")
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--business-date", action="append", dest="business_dates")
    parser.add_argument("--output-subdir", default="diagnostic_shadow")
    parser.add_argument("--all-completed-days", action="store_true")
    parser.add_argument("--include-non-mixed-days", action="store_true")
    args = parser.parse_args(argv)
    if args.business_dates and not args.all_completed_days:
        dates = args.business_dates
    else:
        dates = None
    summary = materialize_marginal_capital_value_shadow_for_run(
        run_root=args.run_root,
        business_dates=dates,
        output_subdir=args.output_subdir,
        mixed_new_add_only=not args.include_non_mixed_days,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
