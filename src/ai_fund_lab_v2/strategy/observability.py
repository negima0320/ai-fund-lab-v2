from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "strategy_decision_trace.v1"
PRODUCER_VERSION = "phase22_m_strategy_observability_attribution_producer.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"

EXPECTED_ARTIFACTS = (
    "market_context",
    "corporate_event",
    "portfolio_policy",
    "dynamic_position_count",
    "dynamic_cash_exposure",
    "portfolio_construction",
    "position_sizing",
    "position_management",
    "runtime_planning",
)

DEPENDENCIES = (
    ("market_context", "portfolio_policy"),
    ("corporate_event", "portfolio_policy"),
    ("portfolio_policy", "dynamic_position_count"),
    ("portfolio_policy", "dynamic_cash_exposure"),
    ("dynamic_position_count", "position_sizing"),
    ("dynamic_cash_exposure", "position_sizing"),
    ("portfolio_construction", "position_sizing"),
    ("position_sizing", "position_management"),
    ("portfolio_construction", "runtime_planning"),
    ("position_sizing", "runtime_planning"),
    ("position_management", "runtime_planning"),
)

REASON_CATEGORIES = {
    "Market": ("market", "regime", "breadth", "volatility", "benchmark", "sector"),
    "Event": ("event", "corporate", "earnings", "delisting", "tob", "split"),
    "Candidate": ("candidate",),
    "Opportunity": ("opportunity", "rank", "score"),
    "Portfolio": ("portfolio", "policy", "member", "membership"),
    "Capital": ("capital", "cash", "exposure", "allocation"),
    "Sizing": ("sizing", "weight", "notional", "minimum"),
    "PM": ("pm", "position_management", "hold", "add", "reduce", "exit"),
    "Runtime Planning": ("planning", "pending", "submit", "intent"),
    "Safety": ("safety", "limit", "cap", "concentration"),
    "PIT": ("date", "future", "pit", "feature_date"),
    "Lineage": ("hash", "lineage", "source"),
    "Config": ("config", "threshold", "policy"),
}


class StrategyObservabilityError(RuntimeError):
    pass


class StrategyObservabilitySchemaError(StrategyObservabilityError):
    pass


@dataclass(frozen=True)
class StrategyTraceResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]


def produce_strategy_decision_trace(
    *,
    business_date: str,
    profile: str,
    run_id: str,
    artifact_paths: Mapping[str, Path | str | None],
    output_path: Path | str,
    legacy_context: Mapping[str, Any] | None = None,
    outcome_context: Mapping[str, Any] | None = None,
) -> StrategyTraceResult:
    payload = build_strategy_decision_trace(
        business_date=business_date,
        profile=profile,
        run_id=run_id,
        artifact_paths=artifact_paths,
        legacy_context=legacy_context,
        outcome_context=outcome_context,
    )
    validate_strategy_decision_trace(payload)
    artifact_hash = strategy_decision_trace_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final_payload)
    return StrategyTraceResult(
        status=str(final_payload["overall_status"]),
        reason=",".join(final_payload.get("blocking_reasons") or final_payload.get("review_reasons") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final_payload,
    )


def build_strategy_decision_trace(
    *,
    business_date: str,
    profile: str,
    run_id: str,
    artifact_paths: Mapping[str, Path | str | None],
    legacy_context: Mapping[str, Any] | None = None,
    outcome_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any]] = {}
    artifact_payloads: dict[str, dict[str, Any]] = {}
    blocking: list[str] = []
    review: list[str] = []

    for kind in EXPECTED_ARTIFACTS:
        summary, payload = _artifact_summary(kind, artifact_paths.get(kind), business_date=business_date)
        artifacts[kind] = summary
        if payload:
            artifact_payloads[kind] = payload
        if summary["status"] == "MISSING":
            review.append(f"required_artifact_missing:{kind}")
        if summary["status"] == "BLOCK":
            blocking.extend(summary["blocking_reasons"])
        if summary["producer_result_status"] == "REVIEW_REQUIRED":
            review.extend(f"{kind}:{reason}" for reason in summary["reason_codes"])

    status_propagation = _status_propagation(artifacts)
    reason_aggregation = _reason_aggregation(artifacts)
    per_symbol = _per_symbol_attribution(artifact_payloads)
    portfolio = _portfolio_attribution(artifact_payloads, per_symbol)
    legacy = _legacy_comparison(legacy_context or {}, artifact_payloads)
    outcome = _outcome_boundary(outcome_context or {})

    if outcome["strategy_input_allowed"] or outcome["learning_input_allowed"]:
        blocking.append("outcome_used_as_strategy_or_learning_input")
    if any(item["status"] == "HASH_MISMATCH" for item in artifacts.values()):
        blocking.append("artifact_hash_mismatch")
    if any(item["status"] == "CROSS_DATE" for item in artifacts.values()):
        blocking.append("cross_date_artifact")
    if any(item["lineage_status"] == "REVIEW_REQUIRED" for item in artifacts.values()):
        review.append("source_lineage_missing")

    overall_status = "PASS"
    if blocking:
        overall_status = "BLOCK"
    elif any(item["status"] == "MISSING" for item in artifacts.values()):
        overall_status = "INCOMPLETE_ATTRIBUTION"
    elif review:
        overall_status = "REVIEW_REQUIRED"

    source_artifacts: list[dict[str, Any]] = []
    source_hashes: list[dict[str, Any]] = []
    config_hashes: list[dict[str, Any]] = []
    for kind, summary in artifacts.items():
        source_artifacts.append({"artifact_type": kind, "path": summary["path"], "status": summary["status"]})
        source_hashes.extend({"artifact_type": kind, **item} for item in summary.get("source_hashes") or [])
        if summary.get("config_hash"):
            config_hashes.append({"artifact_type": kind, "config_hash": summary["config_hash"]})

    return {
        "schema_version": SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "business_date": business_date,
        "profile": profile,
        "run_id": run_id,
        "trace_id": f"strategy-trace-{business_date}-{run_id}",
        "overall_status": overall_status,
        "artifact_lifecycle_status": ARTIFACT_LIFECYCLE_STATUS,
        "runtime_consumer_eligibility": RUNTIME_CONSUMER_ELIGIBILITY,
        "artifacts_expected": list(EXPECTED_ARTIFACTS),
        "artifacts_found": sorted(kind for kind, item in artifacts.items() if item["status"] != "MISSING"),
        "artifacts_missing": sorted(kind for kind, item in artifacts.items() if item["status"] == "MISSING"),
        "artifact_inventory": artifacts,
        "dependency_graph": [{"source_artifact": source, "consumer_artifact": consumer} for source, consumer in DEPENDENCIES],
        "market_context": artifacts["market_context"],
        "portfolio_policy": artifacts["portfolio_policy"],
        "dynamic_position_count": artifacts["dynamic_position_count"],
        "dynamic_cash_exposure": artifacts["dynamic_cash_exposure"],
        "portfolio_construction": artifacts["portfolio_construction"],
        "position_sizing": artifacts["position_sizing"],
        "position_management": artifacts["position_management"],
        "runtime_planning": artifacts["runtime_planning"],
        "portfolio_attribution": portfolio,
        "per_symbol_attribution": per_symbol,
        "source_artifacts": source_artifacts,
        "source_hashes": source_hashes,
        "config_hashes": config_hashes,
        "status_propagation": status_propagation,
        "decision_path": _decision_path(artifacts),
        "blocking_reasons": sorted(set(blocking)),
        "review_reasons": sorted(set(review)),
        "reason_code_aggregation": reason_aggregation,
        "legacy_dynamic_comparison": legacy,
        "readiness_summary": _readiness_summary(artifacts),
        "outcome_boundary": outcome,
        "runtime_behavior_changed": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }


def strategy_decision_trace_hash(payload: Mapping[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if key != "artifact_hash"}
    encoded = json.dumps(clean, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_strategy_decision_trace(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "business_date",
        "profile",
        "run_id",
        "trace_id",
        "overall_status",
        "artifact_lifecycle_status",
        "runtime_consumer_eligibility",
        "artifact_inventory",
        "status_propagation",
        "decision_path",
        "blocking_reasons",
        "review_reasons",
        "per_symbol_attribution",
        "portfolio_attribution",
        "reason_code_aggregation",
        "legacy_dynamic_comparison",
        "readiness_summary",
        "outcome_boundary",
        "runtime_behavior_changed",
        "runtime_switch_performed",
    }
    errors = [f"required_field_missing:{field}" for field in sorted(required - set(payload))]
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported_schema_version")
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS:
        errors.append("artifact_lifecycle_status_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY:
        errors.append("runtime_consumer_eligibility_must_be_not_eligible")
    if payload.get("runtime_switch_performed") is not False:
        errors.append("runtime_switch_forbidden")
    outcome = payload.get("outcome_boundary")
    if isinstance(outcome, Mapping):
        if outcome.get("strategy_input_allowed") is not False or outcome.get("learning_input_allowed") is not False:
            errors.append("outcome_must_not_be_strategy_or_learning_input")
    else:
        errors.append("outcome_boundary_not_object")
    if errors:
        raise StrategyObservabilitySchemaError(";".join(errors))
    return {"status": "PASS", "errors": []}


def summarize_strategy_trace(payload: Mapping[str, Any], *, scope: str = "overview") -> dict[str, Any]:
    if scope == "overview":
        return {
            "status": payload.get("overall_status"),
            "business_date": payload.get("business_date"),
            "portfolio": payload.get("portfolio_attribution"),
            "blocking_reasons": payload.get("blocking_reasons") or [],
            "review_reasons": payload.get("review_reasons") or [],
        }
    if scope == "positions":
        return {"status": payload.get("overall_status"), "positions": payload.get("per_symbol_attribution") or []}
    if scope == "lineage":
        return {
            "status": payload.get("overall_status"),
            "dependency_graph": payload.get("dependency_graph") or [],
            "status_propagation": payload.get("status_propagation") or [],
            "source_artifacts": payload.get("source_artifacts") or [],
            "source_hashes": payload.get("source_hashes") or [],
            "config_hashes": payload.get("config_hashes") or [],
        }
    if scope == "shadow":
        return {"status": payload.get("overall_status"), "legacy_dynamic_comparison": payload.get("legacy_dynamic_comparison") or {}}
    if scope == "readiness":
        return {"status": payload.get("overall_status"), "readiness_summary": payload.get("readiness_summary") or []}
    if scope == "full":
        return dict(payload)
    raise StrategyObservabilityError(f"unsupported strategy trace summary scope: {scope}")


def _artifact_summary(kind: str, path_value: Path | str | None, *, business_date: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path_value:
        return _missing_summary(kind), {}
    path = Path(path_value)
    if not path.is_file():
        summary = _missing_summary(kind)
        summary["path"] = str(path)
        return summary, {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        summary = _missing_summary(kind)
        summary.update({"path": str(path), "status": "BLOCK", "blocking_reasons": [f"invalid_json:{kind}"]})
        return summary, {}
    expected_hash = str(payload.get("artifact_hash") or "")
    actual_hash = _payload_hash(payload)
    status = "PASS"
    blocking: list[str] = []
    if expected_hash and expected_hash != actual_hash:
        status = "HASH_MISMATCH"
        blocking.append(f"artifact_hash_mismatch:{kind}")
    if str(payload.get("business_date") or "") != business_date:
        status = "CROSS_DATE"
        blocking.append(f"cross_date_artifact:{kind}")
    lineage_status = "PASS"
    if not isinstance(payload.get("source_artifacts"), list) or not isinstance(payload.get("source_hashes"), list):
        lineage_status = "REVIEW_REQUIRED"
    return {
        "artifact_type": kind,
        "path": str(path),
        "schema_version": str(payload.get("schema_version") or ""),
        "producer_version": str(payload.get("producer_version") or ""),
        "business_date": str(payload.get("business_date") or ""),
        "feature_date": str(payload.get("feature_date") or ""),
        "status": status,
        "artifact_hash": expected_hash,
        "artifact_hash_valid": bool(expected_hash) and expected_hash == actual_hash,
        "artifact_lifecycle_status": str(payload.get("artifact_lifecycle_status") or ""),
        "producer_result_status": str(payload.get("producer_result_status") or ""),
        "source_authority_status": str(payload.get("source_authority_status") or ""),
        "runtime_consumer_eligibility": str(payload.get("runtime_consumer_eligibility") or ""),
        "source_artifacts": list(payload.get("source_artifacts") or []),
        "source_hashes": list(payload.get("source_hashes") or []),
        "config_hash": str(payload.get("config_hash") or ""),
        "reason_codes": sorted(str(item) for item in (payload.get("reason_codes") or [])),
        "confidence": payload.get("confidence"),
        "uncertainty": str(payload.get("uncertainty") or ""),
        "lineage_status": lineage_status,
        "blocking_reasons": blocking,
        "review_gaps": [] if lineage_status == "PASS" else [f"source_lineage_missing:{kind}"],
    }, payload


def _missing_summary(kind: str) -> dict[str, Any]:
    return {
        "artifact_type": kind,
        "path": "",
        "schema_version": "",
        "producer_version": "",
        "business_date": "",
        "feature_date": "",
        "status": "MISSING",
        "artifact_hash": "",
        "artifact_hash_valid": False,
        "artifact_lifecycle_status": "",
        "producer_result_status": "SOURCE_UNAVAILABLE",
        "source_authority_status": "MISSING",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "source_artifacts": [],
        "source_hashes": [],
        "config_hash": "",
        "reason_codes": [f"{kind}_source_unavailable"],
        "confidence": None,
        "uncertainty": "INCOMPLETE_ATTRIBUTION",
        "lineage_status": "REVIEW_REQUIRED",
        "blocking_reasons": [],
        "review_gaps": [f"required_artifact_missing:{kind}"],
    }


def _status_propagation(artifacts: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for source, consumer in DEPENDENCIES:
        source_status = str(artifacts[source].get("producer_result_status") or artifacts[source].get("status") or "")
        consumer_status = str(artifacts[consumer].get("producer_result_status") or artifacts[consumer].get("status") or "")
        reason = "status_observed_no_override"
        if source_status in {"BLOCK", "MISSING", "SOURCE_UNAVAILABLE"}:
            reason = "upstream_unavailable_or_blocked"
        elif source_status == "REVIEW_REQUIRED":
            reason = "upstream_review_required"
        rows.append({"source_artifact": source, "source_status": source_status, "consumer_artifact": consumer, "consumer_status": consumer_status, "propagation_reason": reason})
    return rows


def _decision_path(artifacts: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"artifact_type": kind, "producer_result_status": artifacts[kind].get("producer_result_status"), "runtime_consumer_eligibility": artifacts[kind].get("runtime_consumer_eligibility")}
        for kind in EXPECTED_ARTIFACTS
    ]


def _reason_aggregation(artifacts: Mapping[str, Mapping[str, Any]]) -> dict[str, list[dict[str, str]]]:
    buckets: dict[str, list[dict[str, str]]] = {category: [] for category in REASON_CATEGORIES}
    buckets["Unclassified"] = []
    for kind, summary in artifacts.items():
        for reason in summary.get("reason_codes") or []:
            reason_l = str(reason).lower()
            matched = False
            for category, needles in REASON_CATEGORIES.items():
                if any(needle in reason_l for needle in needles):
                    buckets[category].append({"source_artifact": kind, "reason_code": str(reason)})
                    matched = True
            if not matched:
                buckets["Unclassified"].append({"source_artifact": kind, "reason_code": str(reason)})
    return {key: sorted(value, key=lambda item: (item["source_artifact"], item["reason_code"])) for key, value in sorted(buckets.items())}


def _per_symbol_attribution(payloads: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_symbol: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in _rows(payloads.get("portfolio_construction", {}), "portfolio_members", "positions"):
        code = _code(row)
        if code:
            by_symbol[code].update({"security_code": code, "portfolio_membership_intent": row.get("membership_intent"), "candidate_rank": row.get("input_candidate_order"), "opportunity_rank": row.get("input_opportunity_rank"), "opportunity_score": row.get("input_score"), "portfolio_reason_codes": row.get("reason_codes") or []})
    for row in _rows(payloads.get("position_sizing", {}), "positions"):
        code = _code(row)
        if code:
            by_symbol[code].update({"security_code": code, "target_weight": row.get("target_weight"), "target_notional": row.get("target_notional"), "sizing_status": row.get("sizing_status"), "sizing_reason_codes": row.get("reason_codes") or []})
    for row in _rows(payloads.get("position_management", {}), "positions"):
        code = _code(row)
        if code:
            by_symbol[code].update({"security_code": code, "pm_action": row.get("action"), "pm_intensity": row.get("intensity"), "pm_reason_codes": row.get("reason_codes") or [], "confidence": row.get("confidence"), "uncertainty": row.get("uncertainty")})
    for row in _rows(payloads.get("runtime_planning", {}), "planning_intents", "plans", "runtime_plans"):
        code = _code(row)
        if code:
            by_symbol[code].update({"security_code": code, "runtime_planning_intent": row.get("planning_intent"), "order_side_intent": row.get("order_side_intent"), "runtime_reason_codes": row.get("reason_codes") or []})
    rows = []
    for code in sorted(by_symbol):
        item = by_symbol[code]
        item.setdefault("candidate_eligibility", "SOURCE_UNAVAILABLE")
        item.setdefault("corporate_event_state", "SOURCE_UNAVAILABLE")
        item["share_quantity_decided"] = False
        item["order_price_decided"] = False
        item["source_status"] = "PARTIAL" if any(value is None for value in item.values()) else "OBSERVED"
        rows.append(item)
    return rows


def _portfolio_attribution(payloads: Mapping[str, Mapping[str, Any]], positions: list[dict[str, Any]]) -> dict[str, Any]:
    market = payloads.get("market_context", {})
    policy = payloads.get("portfolio_policy", {})
    dpc = payloads.get("dynamic_position_count", {})
    dce = payloads.get("dynamic_cash_exposure", {})
    sizing = payloads.get("position_sizing", {})
    pm_payload = payloads.get("position_management", {})
    action_counts = Counter(str(row.get("action") or "UNRESOLVED") for row in _rows(pm_payload, "positions"))
    return {
        "market_regime": market.get("regime_state") or market.get("trend_regime"),
        "market_trend": market.get("trend_regime"),
        "breadth": market.get("market_breadth"),
        "volatility": market.get("volatility_regime"),
        "sector_context_count": len(market.get("sector_contexts") or []),
        "portfolio_policy_posture": policy.get("risk_posture") or policy.get("policy_posture"),
        "target_position_count": dpc.get("target_position_count"),
        "target_cash_ratio": dce.get("target_cash_ratio"),
        "portfolio_total_equity": dce.get("portfolio_total_equity"),
        "current_cash": dce.get("current_cash"),
        "current_market_value": dce.get("current_market_value"),
        "pending_reserved_cash": dce.get("pending_reserved_cash"),
        "net_available_cash": dce.get("net_available_cash"),
        "target_cash_amount": dce.get("target_cash_amount"),
        "target_invested_ratio": dce.get("target_invested_ratio") or dce.get("target_gross_exposure_ratio"),
        "target_invested_notional": dce.get("target_invested_notional"),
        "current_invested_ratio": dce.get("current_invested_ratio") or dce.get("current_gross_exposure_ratio"),
        "incremental_deployment_capacity": dce.get("incremental_deployment_capacity"),
        "target_gross_exposure": dce.get("target_gross_exposure_ratio"),
        "eligible_opportunity_count": dpc.get("eligible_opportunity_count") or dpc.get("available_opportunity_count"),
        "meaningful_allocation_position_count": dpc.get("meaningful_allocation_position_count"),
        "actual_target_position_count": dpc.get("actual_target_position_count") or dpc.get("target_position_count"),
        "legacy_max_positions": dpc.get("legacy_active_max_positions"),
        "legacy_max_exposure": (dce.get("shadow_comparison") or {}).get("legacy_max_exposure"),
        "legacy_authority_active": bool(dpc.get("legacy_authority_active", True) and dce.get("legacy_authority_active", True)),
        "strategy_fixed_position_cap_used": dpc.get("strategy_fixed_position_cap_used", False),
        "strategy_fixed_jpy_exposure_cap_used": dce.get("strategy_fixed_jpy_exposure_cap_used", False),
        "safety_constraints_applied": {
            "cash_safety_minimum": dce.get("cash_safety_minimum"),
            "exposure_safety_maximum": dce.get("exposure_safety_maximum"),
            "safety_maximum_position_weight": sizing.get("safety_maximum_position_weight"),
        },
        "target_member_count": len(_rows(payloads.get("portfolio_construction", {}), "portfolio_members", "positions")),
        "total_target_weight": sizing.get("total_target_weight"),
        "residual_cash_ratio": sizing.get("residual_cash_ratio"),
        "positions_count": len(positions),
        "hold_count": action_counts.get("HOLD", 0),
        "add_count": action_counts.get("ADD", 0),
        "reduce_count": action_counts.get("REDUCE", 0),
        "exit_count": action_counts.get("EXIT", 0),
        "unresolved_count": action_counts.get("UNRESOLVED", 0),
    }


def _legacy_comparison(legacy: Mapping[str, Any], payloads: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    dynamic_count = (payloads.get("dynamic_position_count") or {}).get("target_position_count")
    dynamic_exposure = (payloads.get("dynamic_cash_exposure") or {}).get("target_gross_exposure_ratio")
    dynamic_cash = (payloads.get("dynamic_cash_exposure") or {}).get("target_cash_ratio")
    sizing_rows = _rows(payloads.get("position_sizing", {}), "positions")
    pm_rows = _rows(payloads.get("position_management", {}), "positions")
    return {
        "max_positions": _compare(legacy.get("max_positions"), dynamic_count),
        "target_investment_ratio": _compare(legacy.get("target_investment_ratio"), dynamic_exposure),
        "cash_buffer": _compare(legacy.get("cash_buffer"), dynamic_cash),
        "legacy_max_positions_authority_used_by_strategy": bool((payloads.get("dynamic_position_count") or {}).get("strategy_fixed_position_cap_used", False)),
        "legacy_max_exposure_authority_used_by_strategy": bool((payloads.get("dynamic_cash_exposure") or {}).get("legacy_max_exposure_authority_used", False)),
        "strategy_fixed_jpy_exposure_cap_used": bool((payloads.get("dynamic_cash_exposure") or {}).get("strategy_fixed_jpy_exposure_cap_used", False)),
        "allocation": "SOURCE_UNAVAILABLE" if not sizing_rows else "NOT_COMPARABLE",
        "pm_action": "SOURCE_UNAVAILABLE" if not pm_rows else "NOT_COMPARABLE",
        "planning_result": "SOURCE_UNAVAILABLE",
        "evaluation_policy": "read_only_no_good_bad_or_pnl_judgment",
    }


def _compare(legacy: Any, dynamic: Any) -> str:
    if legacy in (None, "") or dynamic in (None, ""):
        return "SOURCE_UNAVAILABLE"
    return "SAME" if legacy == dynamic else "DIFFERENT"


def _readiness_summary(artifacts: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "artifact_type": kind,
            "artifact_lifecycle_status": item.get("artifact_lifecycle_status"),
            "producer_result_status": item.get("producer_result_status"),
            "source_authority_status": item.get("source_authority_status"),
            "runtime_consumer_eligibility": item.get("runtime_consumer_eligibility"),
            "blocking_gaps": item.get("blocking_reasons") or [],
            "review_gaps": item.get("review_gaps") or [],
        }
        for kind, item in sorted(artifacts.items())
    ]


def _outcome_boundary(outcome: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "decision_attribution": "Strategy Artifact reason and lineage only",
        "execution_attribution": "Runtime processing only when supplied",
        "outcome_attribution": "post-decision analysis only",
        "runtime_result_available": bool(outcome.get("runtime_result_available")),
        "execution_result_available": bool(outcome.get("execution_result_available")),
        "outcome_attribution_available": bool(outcome.get("outcome_attribution_available")),
        "strategy_input_allowed": bool(outcome.get("strategy_input_allowed", False)),
        "learning_input_allowed": bool(outcome.get("learning_input_allowed", False)),
    }


def _rows(payload: Mapping[str, Any], *keys: str) -> list[dict[str, Any]]:
    for key in keys:
        rows = payload.get(key)
        if isinstance(rows, list):
            return [dict(row) for row in rows if isinstance(row, Mapping)]
    return []


def _code(row: Mapping[str, Any]) -> str:
    return str(row.get("security_code") or row.get("code") or row.get("symbol") or row.get("local_code") or "")


def _payload_hash(payload: Mapping[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if key != "artifact_hash"}
    encoded = json.dumps(clean, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
