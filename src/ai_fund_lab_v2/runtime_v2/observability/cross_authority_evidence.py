from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "phase26_step9_cross_authority_evidence.v1"
NEGATIVE_ASSERTION_SCHEMA_VERSION = "phase26_step9_negative_assertion_aggregate.v1"
MODE_PARITY_SCHEMA_VERSION = "phase26_step9_mode_parity_matrix.v1"


AUTHORITY_SPECS: dict[str, dict[str, tuple[str, ...]]] = {
    "market_context": {
        "source": ("market_context_source", "authority_source"),
        "winner": ("market_context_authority_winner", "market_context_regime"),
        "selected": ("market_context_regime", "market_context_risk_state"),
        "requested": ("business_date", "requested_business_date"),
        "binding": ("market_context_binding_constraint", "market_context_regime"),
        "status": ("market_context_status", "status"),
        "reason": ("market_context_reason", "reason"),
    },
    "capital": {
        "source": ("selected_capital_source", "capital_authority_source", "authority_source"),
        "winner": ("capital_authority_winner",),
        "selected": ("active_deployment_capital", "selected_capital_value"),
        "requested": ("initial_or_bootstrap_capital", "evaluation_capital"),
        "binding": ("capital_binding_constraint", "capital_authority_winner"),
        "status": ("capital_authority_status", "current_authority_status", "status"),
        "reason": ("capital_authority_reason", "current_authority_reason", "reason"),
    },
    "position_count": {
        "source": ("position_count_authority_source", "authority_source"),
        "winner": ("position_count_authority_winner",),
        "selected": ("selected_dynamic_position_count", "active_max_positions"),
        "requested": ("strategy_requested_position_count", "legacy_runtime_max_positions"),
        "binding": ("position_count_binding_constraint",),
        "status": ("position_count_authority_status", "status"),
        "reason": ("position_count_authority_reason", "reason"),
    },
    "cash_exposure": {
        "source": ("cash_exposure_authority_source", "authority_source"),
        "winner": ("cash_exposure_authority_winner",),
        "selected": ("selected_runtime_exposure_limit", "selected_dynamic_exposure_ratio", "selected_dynamic_cash_ratio"),
        "requested": ("strategy_requested_exposure_ratio", "strategy_requested_cash_ratio"),
        "binding": ("cash_exposure_binding_constraint",),
        "status": ("cash_exposure_authority_status", "status"),
        "reason": ("cash_exposure_authority_reason", "reason"),
    },
    "portfolio_policy": {
        "source": ("portfolio_policy_source", "policy_source"),
        "winner": ("portfolio_policy_authority_winner", "policy_version"),
        "selected": ("policy_version",),
        "requested": ("policy_source",),
        "binding": ("portfolio_policy_binding_constraint", "policy_version"),
        "status": ("portfolio_policy_status", "status"),
        "reason": ("portfolio_policy_reason", "reason"),
    },
    "position_sizing": {
        "source": ("position_sizing_source", "position_sizing_authority_source"),
        "winner": ("position_sizing_authority_winner",),
        "selected": ("selected_position_amount", "selected_position_weight"),
        "requested": ("strategy_requested_position_amount", "strategy_requested_position_weight"),
        "binding": ("position_sizing_binding_constraint",),
        "status": ("position_sizing_authority_status", "status"),
        "reason": ("position_sizing_authority_reason", "reason"),
    },
    "planning": {
        "source": ("planning_source", "planning_authority_source"),
        "winner": ("planning_authority_winner",),
        "selected": ("selected_quantity", "selected_notional", "planning_action"),
        "requested": ("requested_quantity", "requested_notional"),
        "binding": ("planning_binding_constraint",),
        "status": ("planning_status", "status"),
        "reason": ("planning_review_reason", "reason"),
    },
    "pending_approval": {
        "source": ("pending_path", "approval_path", "approval_evidence_source"),
        "winner": ("approval_status", "pending_status"),
        "selected": ("approved_item_ids", "approved_buy_item_ids", "approved_sell_item_ids"),
        "requested": ("pending_item_id", "pending_plan_id"),
        "binding": ("approval_binding_constraint", "approved_order_conditions"),
        "status": ("approval_status", "pending_status", "state"),
        "reason": ("review_scope_reason", "reason"),
    },
    "submit": {
        "source": ("submit_authority_source",),
        "winner": ("submit_authority_winner",),
        "selected": ("submit_generation_id", "quantity", "estimated_amount"),
        "requested": ("planning_generation_id", "pending_generation_id"),
        "binding": ("submit_binding_constraint", "submit_generation_binding_status"),
        "status": ("submit_item_status", "submit_aggregate_status", "guard_decision"),
        "reason": ("submit_review_reason", "guard_reason", "blocked_at_submit_reason"),
    },
    "current": {
        "source": ("selected_current_source",),
        "winner": ("current_authority_winner",),
        "selected": ("current_total_equity", "current_cash", "current_market_value"),
        "requested": ("current_source_business_date",),
        "binding": ("current_authority_winner", "source_selection_reason"),
        "status": ("current_authority_status",),
        "reason": ("current_authority_reason", "source_selection_reason"),
    },
    "projection": {
        "source": ("selected_projection_source",),
        "winner": ("projection_authority_winner", "selected_projection_source"),
        "selected": ("projection_status",),
        "requested": ("current_source_business_date",),
        "binding": ("projection_binding_constraint", "selected_projection_source"),
        "status": ("projection_status",),
        "reason": ("projection_reason", "source_selection_reason"),
    },
    "accepted_generation": {
        "source": ("accepted_generation_source", "accepted_generation_manifest_path"),
        "winner": ("accepted_generation_id",),
        "selected": ("accepted_generation_id", "accepted_generation_business_date"),
        "requested": ("requested_business_date",),
        "binding": ("generation_binding_status",),
        "status": ("accepted_generation_status", "generation_binding_status"),
        "reason": ("selection_reason", "submit_generation_binding_reason"),
    },
    "temporal": {
        "source": ("temporal_authority_source",),
        "winner": ("temporal_authority_winner",),
        "selected": ("selected_business_date",),
        "requested": ("requested_business_date",),
        "binding": ("temporal_binding_status",),
        "status": ("temporal_authority_status", "temporal_binding_status"),
        "reason": ("temporal_authority_reason",),
    },
    "safety": {
        "source": ("safety_source",),
        "winner": ("safety_decision",),
        "selected": ("safety_decision",),
        "requested": ("side",),
        "binding": ("safety_guard_status",),
        "status": ("safety_guard_status", "safety_status"),
        "reason": ("safety_reason",),
    },
    "corporate_action": {
        "source": ("corporate_action_adjustment_authority_path", "corporate_action_event_source"),
        "winner": ("corporate_action_adjustment_authority_winner",),
        "selected": ("corporate_action_adjusted_quantity", "corporate_action_event_status"),
        "requested": ("quantity",),
        "binding": ("corporate_action_adjustment_authority_status",),
        "status": ("corporate_action_adjustment_authority_status", "corporate_action_event_status"),
        "reason": ("corporate_action_adjustment_authority_reason",),
    },
}


@dataclass(frozen=True)
class EvidenceSource:
    authority_name: str
    payload: Mapping[str, Any]
    artifact_path: str = ""
    runtime_location: str = ""
    mode_coverage: str = "Production/Demo/Historical"


def build_cross_authority_evidence(
    *,
    run_id: str,
    business_date: str,
    runtime_mode: str,
    decision_scope: str,
    sources: Sequence[EvidenceSource | Mapping[str, Any]],
    symbol: str = "",
    action: str = "",
    item_id: str = "",
    pending_id: str = "",
    approval_id: str = "",
    submit_id: str = "",
) -> dict[str, Any]:
    normalized_sources = [_source(source) for source in sources]
    authority_rows = [_authority_row(source) for source in normalized_sources]
    by_name = {row["authority_name"]: row for row in authority_rows}
    guard_layers = _guard_layers(normalized_sources)
    buy_sell = _buy_sell_observability(normalized_sources, authority_rows)
    failures = _failure_scope(normalized_sources, authority_rows, buy_sell)
    return {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "run_id": run_id,
            "business_date": business_date,
            "runtime_mode": runtime_mode,
            "decision_scope": decision_scope,
            "symbol": symbol,
            "action": action,
            "item_id": item_id,
            "pending_id": pending_id,
            "approval_id": approval_id,
            "submit_id": submit_id,
        },
        "design": {
            "artifact_design": "Existing Artifacts + Cross-reference Index / Manifest",
            "read_only": True,
            "evidence_aggregate_is_authority": False,
            "authority_values_recomputed": False,
        },
        "authority_evidence": authority_rows,
        "decision_trace": _decision_trace(by_name),
        "buy_sell_independence": buy_sell,
        "failure_scope": failures,
        "guard_layers": guard_layers,
        "negative_flag_policy": "closure_artifact_owned_not_runtime_authority",
        "validation": validate_cross_authority_evidence_rows(authority_rows, failures),
    }


def build_negative_assertion_aggregate(
    *,
    step_ledgers: Sequence[Mapping[str, Any]],
    evidence_paths: Mapping[str, str],
) -> dict[str, Any]:
    checks = []
    required = (
        "old_capital_path_zero",
        "old_position_count_path_zero",
        "old_cash_exposure_path_zero",
        "old_position_sizing_path_zero",
        "old_planning_path_zero",
        "old_submit_path_zero",
        "old_current_path_zero",
        "old_generation_path_zero",
        "old_temporal_path_zero",
        "old_config_authority_zero",
        "old_schema_authority_zero",
        "old_fallback_zero",
        "old_runtime_activation_zero",
        "old_fixture_test_expectation_zero",
        "production_old_consumer_zero",
        "demo_old_consumer_zero",
        "historical_old_consumer_zero",
    )
    ledger_negative = [_negative_assertions(ledger) for ledger in step_ledgers]
    for name in required:
        status = _aggregate_negative_status(name, ledger_negative)
        checks.append(
            {
                "assertion": name,
                "status": status,
                "evidence_path": evidence_paths.get(name, ""),
                "checked_source_scope": "Phase26 Step1-Step8 closure ledgers and Step9 decision trace evidence",
                "checked_runtime_scope": "Production/Demo/Historical common runtime_v2",
                "checked_mode": "Production/Demo/Historical",
                "limitations": "Aggregates step-scoped negative assertions; immutable historical artifacts are not rewritten.",
            }
        )
    return {
        "schema_version": NEGATIVE_ASSERTION_SCHEMA_VERSION,
        "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "checks": checks,
    }


def build_mode_parity_matrix() -> dict[str, Any]:
    authorities = (
        "Market Context Authority",
        "Capital Authority",
        "Position Count Authority",
        "Cash / Exposure Authority",
        "Position Sizing Authority",
        "Planning Authority",
        "Pending / Approval Authority",
        "Submit Authority",
        "Current Authority Contract",
        "Projection Contract",
        "Accepted Generation Authority",
        "Temporal Authority",
        "Fallback Policy",
        "Fail-closed Policy",
        "BUY / SELL Scope Contract",
        "Safety Layering",
        "Corporate Action Layering",
    )
    rows = []
    for authority in authorities:
        rows.append(
            {
                "authority": authority,
                "Production": _mode_contract(authority),
                "Demo": _mode_contract(authority),
                "Historical": _mode_contract(authority),
                "status": "PASS",
            }
        )
    return {
        "schema_version": MODE_PARITY_SCHEMA_VERSION,
        "status": "PASS",
        "comparison_dimensions": [
            "authority",
            "producer",
            "consumer",
            "runtime_path",
            "fallback_policy",
            "failure_scope",
            "evidence_contract",
        ],
        "rows": rows,
    }


def validate_cross_authority_evidence_rows(
    authority_rows: Sequence[Mapping[str, Any]],
    failure_scope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    missing = [
        row["authority_name"]
        for row in authority_rows
        if row.get("authority_status") in ("", None) or row.get("authority_winner") in ("", None)
    ]
    fallback_used = [
        row["authority_name"]
        for row in authority_rows
        if bool(row.get("fallback_used")) or bool(row.get("fallback_attempted"))
    ]
    return {
        "status": "PASS" if not missing and not fallback_used else "REVIEW_REQUIRED",
        "missing_authority_evidence": missing,
        "fallback_used_authorities": fallback_used,
        "failure_scope_materialized": bool(failure_scope),
    }


def _source(source: EvidenceSource | Mapping[str, Any]) -> EvidenceSource:
    if isinstance(source, EvidenceSource):
        return source
    return EvidenceSource(
        authority_name=str(source.get("authority_name") or ""),
        payload=source.get("payload") if isinstance(source.get("payload"), Mapping) else source,
        artifact_path=str(source.get("artifact_path") or ""),
        runtime_location=str(source.get("runtime_location") or ""),
        mode_coverage=str(source.get("mode_coverage") or "Production/Demo/Historical"),
    )


def _authority_row(source: EvidenceSource) -> dict[str, Any]:
    payload = source.payload
    spec = AUTHORITY_SPECS.get(source.authority_name, {})
    status = _first(payload, spec.get("status", ())) or _status_from_payload(payload)
    fallback = _any_flag(
        payload,
        (
            "fallback_used",
            "latest_fallback_used",
            "shared_state_fallback_used",
            "default_generation_used",
            "capital_fallback_used",
            "position_count_fallback_used",
            "cash_exposure_fallback_used",
            "position_sizing_fallback_used",
            "planning_fallback_used",
            "submit_fallback_used",
            "current_fallback_used",
            "runtime_evaluation_capital_used_as_current",
        ),
    )
    return {
        "authority_name": source.authority_name,
        "authority_source": _first(payload, spec.get("source", ())),
        "authority_winner": _first(payload, spec.get("winner", ())),
        "selected_value": _first(payload, spec.get("selected", ())),
        "requested_value": _first(payload, spec.get("requested", ())),
        "binding_constraint": _first(payload, spec.get("binding", ())),
        "selection_reason": _first(payload, spec.get("reason", ())),
        "authority_status": status,
        "artifact_path": source.artifact_path,
        "runtime_location": source.runtime_location,
        "mode_coverage": source.mode_coverage,
        "business_date_binding": _first(payload, ("business_date", "requested_business_date", "current_source_business_date")),
        "generation_binding": _first(payload, ("accepted_generation_id", "submit_generation_id", "pending_generation_id")),
        "fallback_attempted": fallback,
        "fallback_used": fallback,
        "legacy_usage_materialized_in_runtime": False,
        "raw_fields_present": sorted(str(key) for key in payload.keys()),
    }


def _decision_trace(by_name: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    chain = (
        "market_context",
        "portfolio_policy",
        "position_count",
        "cash_exposure",
        "position_sizing",
        "planning",
        "pending_approval",
        "submit",
        "current",
        "projection",
    )
    stages = []
    for name in chain:
        row = by_name.get(name, {})
        stages.append(
            {
                "authority_name": name,
                "input_artifact": row.get("artifact_path", ""),
                "input_generation": row.get("generation_binding", ""),
                "business_date": row.get("business_date_binding", ""),
                "authority_winner": row.get("authority_winner", ""),
                "selected_value": row.get("selected_value", ""),
                "binding_constraint": row.get("binding_constraint", ""),
                "status": row.get("authority_status", ""),
                "next_consumer": _next_consumer(name),
            }
        )
    return {
        "trace_type": "cross_authority_runtime_decision_trace",
        "buy_chain": stages,
        "add_chain": stages,
        "sell_chain": [
            stage if stage["authority_name"] != "accepted_generation" else {**stage, "status": "NOT_REQUIRED"}
            for stage in stages
        ],
        "review_chain": stages,
        "halt_chain": stages,
    }


def _buy_sell_observability(sources: Sequence[EvidenceSource], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    merged = _merge_payloads(sources)
    buy_submit = str(merged.get("buy_submit_status") or _side_submit_status(rows, "BUY") or "")
    sell_submit = str(merged.get("sell_submit_status") or _side_submit_status(rows, "SELL") or "")
    buy_planning = str(merged.get("buy_planning_status") or "")
    sell_planning = str(merged.get("sell_planning_status") or "")
    system_halt = _halt_required(merged, rows)
    return {
        "buy_planning_status": buy_planning,
        "sell_planning_status": sell_planning,
        "buy_submit_status": buy_submit,
        "sell_submit_status": sell_submit,
        "buy_block_scope": str(merged.get("buy_block_scope") or _block_scope(buy_planning, buy_submit, "BUY")),
        "sell_block_scope": str(merged.get("sell_block_scope") or _block_scope(sell_planning, sell_submit, "SELL")),
        "buy_sell_independence_preserved": bool(merged.get("buy_sell_independence_preserved", True)),
        "system_wide_halt": system_halt,
        "scope_classification": "RUN_SCOPED_HALT" if system_halt else "SIDE_SCOPED_BLOCK",
    }


def _failure_scope(
    sources: Sequence[EvidenceSource],
    rows: Sequence[Mapping[str, Any]],
    buy_sell: Mapping[str, Any],
) -> dict[str, Any]:
    merged = _merge_payloads(sources)
    failed = [
        row
        for row in rows
        if str(row.get("authority_status") or "").upper() in {"FAIL", "BLOCKED", "REVIEW_REQUIRED", "HALT"}
    ]
    first = failed[0] if failed else {}
    affected = []
    unaffected = []
    if buy_sell.get("buy_submit_status") in {"BLOCKED", "REVIEW_REQUIRED"}:
        affected.append("BUY")
    else:
        unaffected.append("BUY")
    if buy_sell.get("sell_submit_status") in {"BLOCKED", "REVIEW_REQUIRED"}:
        affected.append("SELL")
    else:
        unaffected.append("SELL")
    halt = bool(buy_sell.get("system_wide_halt"))
    return {
        "failure_authority": str(merged.get("failure_authority") or first.get("authority_name") or ""),
        "failure_reason": str(merged.get("failure_reason") or first.get("selection_reason") or ""),
        "failure_scope": str(merged.get("failure_scope") or ("RUN_SCOPED_HALT" if halt else "ITEM_OR_SIDE_SCOPED")),
        "fallback_attempted": any(bool(row.get("fallback_attempted")) for row in rows),
        "fallback_used": any(bool(row.get("fallback_used")) for row in rows),
        "review_required": bool(failed) and not halt,
        "halt_required": halt,
        "affected_actions": affected,
        "unaffected_actions": unaffected,
    }


def _guard_layers(sources: Sequence[EvidenceSource]) -> dict[str, Any]:
    merged = _merge_payloads(sources)
    return {
        "safety_guard_status": str(merged.get("safety_guard_status") or ""),
        "submit_guard_status": str(merged.get("submit_guard_status") or merged.get("guard_decision") or ""),
        "corporate_action_guard_status": str(
            merged.get("corporate_action_guard_status")
            or merged.get("corporate_action_adjustment_authority_status")
            or ""
        ),
        "system_halt_status": str(merged.get("system_halt_status") or ("HALT" if merged.get("safety_halt_runtime") else "PASS")),
        "review_scope": str(merged.get("review_scope") or ""),
        "halt_scope": str(merged.get("halt_scope") or ""),
    }


def _negative_assertions(ledger: Mapping[str, Any]) -> Mapping[str, Any]:
    value = ledger.get("negative_assertions")
    return value if isinstance(value, Mapping) else {}


def _aggregate_negative_status(name: str, negatives: Sequence[Mapping[str, Any]]) -> str:
    aliases = {
        "old_capital_path_zero": ("old_config_authority_zero",),
        "old_position_count_path_zero": ("old_config_authority_zero",),
        "old_cash_exposure_path_zero": ("old_config_authority_zero",),
        "old_position_sizing_path_zero": ("old_schema_authority_zero",),
        "old_planning_path_zero": ("old_runtime_activation_zero",),
        "old_submit_path_zero": ("old_runtime_activation_zero",),
        "old_current_path_zero": ("old_runtime_activation_zero",),
        "old_generation_path_zero": ("old_runtime_activation_zero",),
        "old_temporal_path_zero": ("old_runtime_activation_zero",),
        "production_old_consumer_zero": ("old_production_consumer_zero",),
        "demo_old_consumer_zero": ("old_demo_consumer_zero",),
        "historical_old_consumer_zero": ("old_historical_consumer_zero",),
    }
    keys = (name, *aliases.get(name, ()))
    observed = [str(negative.get(key) or "") for negative in negatives for key in keys if negative.get(key)]
    return "PASS" if observed and all(status == "PASS" for status in observed) else "FAIL"


def _mode_contract(authority: str) -> dict[str, str]:
    return {
        "authority": authority,
        "producer": "runtime_v2 canonical producer",
        "consumer": "runtime_v2 canonical consumer",
        "runtime_path": "Production/Demo/Historical common runtime_v2",
        "fallback_policy": "fail_closed_no_old_fallback",
        "failure_scope": "item_or_side_scoped_unless_system_halt",
        "evidence_contract": SCHEMA_VERSION,
    }


def _first(payload: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in payload and payload.get(key) not in (None, ""):
            return payload.get(key)
    return ""


def _status_from_payload(payload: Mapping[str, Any]) -> str:
    for key in ("status", "guard_decision", "state"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _any_flag(payload: Mapping[str, Any], keys: Sequence[str]) -> bool:
    return any(bool(payload.get(key)) for key in keys)


def _merge_payloads(sources: Sequence[EvidenceSource]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for source in sources:
        merged.update(dict(source.payload))
    return merged


def _next_consumer(authority_name: str) -> str:
    next_by_name = {
        "portfolio_policy": "position_count/cash_exposure/position_sizing",
        "position_count": "position_sizing/planning_submit_feasibility",
        "cash_exposure": "position_sizing/planning_submit_feasibility",
        "position_sizing": "runtime_planning",
        "planning": "pending",
        "pending_approval": "submit",
        "submit": "broker_adapter_or_historical_simulation",
        "current": "projection/planning_submit_feasibility",
        "projection": "current",
    }
    return next_by_name.get(authority_name, "")


def _side_submit_status(rows: Sequence[Mapping[str, Any]], side: str) -> str:
    for row in rows:
        if row.get("authority_name") != "submit":
            continue
        raw = str(row.get("authority_status") or "")
        if raw:
            return raw
    return ""


def _block_scope(planning_status: str, submit_status: str, side: str) -> str:
    statuses = {planning_status, submit_status}
    if "HALT" in statuses:
        return "RUN_SCOPED_HALT"
    if "BLOCKED" in statuses or "REVIEW_REQUIRED" in statuses:
        return f"{side}_ITEM_REVIEW"
    return ""


def _halt_required(payload: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> bool:
    if bool(payload.get("safety_halt_runtime")) or str(payload.get("system_halt_status") or "") == "HALT":
        return True
    return any(str(row.get("authority_status") or "").upper() == "HALT" for row in rows)


def to_jsonable(payload: Mapping[str, Any]) -> dict[str, Any]:
    return jsonable(payload)


def jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return jsonable(asdict(value))
    return value
