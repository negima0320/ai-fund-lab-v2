from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Mapping

from ai_fund_lab_v2.strategy.status_contract import status_contract_fields


SCHEMA_VERSION = "buy_quality_decision.v1"
ARTIFACT_SCHEMA_VERSION = "buy_quality_decisions.v1"
PRODUCER_VERSION = "phase26_h_adaptive_buy_quality_producer.v1"
POLICY_VERSION = "phase26_h_adaptive_buy_quality_policy.v1"
PRODUCER = "Production Strategy BUY Quality Resolver"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"

COMPONENT_WEIGHTS = {
    "relative_opportunity_quality": 0.35,
    "market_context_quality_modifier": 0.15,
    "signal_reliability": 0.25,
    "execution_feasibility": 0.10,
    "portfolio_fit": 0.15,
}

BAND_BOUNDARIES = {
    "VERY_HIGH": 0.85,
    "HIGH": 0.72,
    "MEDIUM": 0.55,
    "LOW": 0.35,
}

ACTION_BOUNDARIES = {
    "FULL_ALLOCATION_ELIGIBLE": 0.72,
    "REDUCED_ALLOCATION_ONLY": 0.45,
}

CRITICAL_COMPONENTS = {
    "relative_opportunity_quality",
    "signal_reliability",
}

SUBMITTABLE_ACTIONS = {"FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY"}


@dataclass(frozen=True)
class BuyQualityProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


@dataclass(frozen=True)
class BuyQualitySourceSummary:
    status: str
    business_date: str
    feature_date: str
    source_ref: str
    source_hash: str
    rows: tuple[Mapping[str, Any], ...] = ()
    summary: Mapping[str, Any] | None = None

    def to_dict(self, *, requested_business_date: str) -> dict[str, Any]:
        return {
            "status": self.status,
            "business_date": self.business_date,
            "feature_date": self.feature_date,
            "source_ref": self.source_ref,
            "source_hash": self.source_hash,
            "row_count": len(self.rows),
            "summary": dict(self.summary or {}),
            "business_date_aligned": self.business_date == requested_business_date,
            "feature_date_lte_business_date": bool(self.feature_date and self.feature_date <= requested_business_date),
        }


def produce_buy_quality_artifact(
    *,
    business_date: str,
    candidate_summary: BuyQualitySourceSummary,
    opportunity_summary: BuyQualitySourceSummary,
    market_context_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    current_portfolio_summary: BuyQualitySourceSummary,
    pending_summary: BuyQualitySourceSummary | None = None,
    price_volatility_summary: BuyQualitySourceSummary | None = None,
    corporate_event_artifact_path: Path | str | None = None,
    output_path: Path | str,
    as_of: str | None = None,
) -> BuyQualityProducerResult:
    payload, evidence = build_buy_quality_payload(
        business_date=business_date,
        candidate_summary=candidate_summary,
        opportunity_summary=opportunity_summary,
        market_context_artifact_path=market_context_artifact_path,
        portfolio_policy_artifact_path=portfolio_policy_artifact_path,
        current_portfolio_summary=current_portfolio_summary,
        pending_summary=pending_summary,
        price_volatility_summary=price_volatility_summary,
        corporate_event_artifact_path=corporate_event_artifact_path,
        as_of=as_of,
    )
    validate_buy_quality_artifact(payload)
    artifact_hash = buy_quality_hash(payload)
    final = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final)
    return BuyQualityProducerResult(final["producer_result_status"], ",".join(final.get("reason_codes") or []), str(path), artifact_hash, final, evidence)


def build_buy_quality_payload(
    *,
    business_date: str,
    candidate_summary: BuyQualitySourceSummary,
    opportunity_summary: BuyQualitySourceSummary,
    market_context_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    current_portfolio_summary: BuyQualitySourceSummary,
    pending_summary: BuyQualitySourceSummary | None = None,
    price_volatility_summary: BuyQualitySourceSummary | None = None,
    corporate_event_artifact_path: Path | str | None = None,
    as_of: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _date(business_date)
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    market_payload = _read_json(market_context_artifact_path)
    policy_payload = _read_json(portfolio_policy_artifact_path)
    corporate_payload = _read_json(corporate_event_artifact_path)
    pending_summary = pending_summary or _empty_summary("pending", business_date)
    price_volatility_summary = price_volatility_summary or _empty_summary("price_volatility", business_date)
    summaries = {
        "candidate": candidate_summary,
        "opportunity": opportunity_summary,
        "current_portfolio": current_portfolio_summary,
        "pending": pending_summary,
        "price_volatility": price_volatility_summary,
    }
    status = "PASS"
    reasons: list[str] = []
    for name, summary in summaries.items():
        if summary.business_date != business_date or not summary.feature_date or summary.feature_date > business_date:
            status = "BLOCK"
            reasons.append(f"{name}_date_mismatch")
        if summary.status == "BLOCK":
            status = "BLOCK"
            reasons.append(f"{name}_block")
        elif summary.status != "PASS" and name in {"candidate", "opportunity", "current_portfolio"} and status != "BLOCK":
            status = "REVIEW_REQUIRED"
            reasons.append(f"{name}_review_required:{summary.status}")

    opportunities = [dict(row) for row in opportunity_summary.rows if isinstance(row, Mapping)]
    candidates_by_symbol = {_symbol(row): dict(row) for row in candidate_summary.rows if _symbol(row)}
    current_by_symbol = {_symbol(row): dict(row) for row in current_portfolio_summary.rows if _symbol(row)}
    pending_symbols = {_symbol(row) for row in pending_summary.rows if _symbol(row)}
    volatility_by_symbol = {_symbol(row): dict(row) for row in price_volatility_summary.rows if _symbol(row)}
    scores = [_finite_float(row.get("expected_edge_score", row.get("runtime_opportunity_score"))) for row in opportunities]
    finite_scores = [score for score in scores if score is not None]
    decisions = []
    for row in opportunities:
        symbol = _symbol(row)
        if not symbol:
            continue
        decision = _decision_for_row(
            business_date=business_date,
            as_of=as_of,
            opportunity=row,
            candidate=candidates_by_symbol.get(symbol, {}),
            current=current_by_symbol.get(symbol, {}),
            pending_symbols=pending_symbols,
            price_volatility=volatility_by_symbol.get(symbol, {}),
            all_scores=finite_scores,
            market_payload=market_payload,
            policy_payload=policy_payload,
            corporate_payload=corporate_payload,
            opportunity_source=opportunity_summary,
            candidate_source=candidate_summary,
        )
        decisions.append(decision)
    if not decisions and status != "BLOCK":
        status = "REVIEW_REQUIRED"
        reasons.append("buy_quality_decisions_missing")

    future = any(summary.feature_date and summary.feature_date > business_date for summary in summaries.values())
    if future:
        status = "BLOCK"
        reasons.append("future_source_date_detected")
    action_counts: dict[str, int] = {}
    band_counts: dict[str, int] = {}
    missing_count = 0
    for decision in decisions:
        action_counts[str(decision["quality_action"])] = action_counts.get(str(decision["quality_action"]), 0) + 1
        band_counts[str(decision["quality_band"])] = band_counts.get(str(decision["quality_band"]), 0) + 1
        missing_count += sum(1 for value in (decision.get("component_statuses") or {}).values() if value in {"NOT_AVAILABLE", "REVIEW_REQUIRED"})
    feature_date = min([summary.feature_date for summary in summaries.values() if summary.feature_date] or [business_date])
    source_artifacts = [
        {"role": "candidate", "path": candidate_summary.source_ref, "required": True, "status": candidate_summary.status},
        {"role": "opportunity", "path": opportunity_summary.source_ref, "required": True, "status": opportunity_summary.status},
        {"role": "market_context", "path": str(market_context_artifact_path or ""), "required": True, "status": _payload_status(market_payload)},
        {"role": "portfolio_policy", "path": str(portfolio_policy_artifact_path or ""), "required": True, "status": _payload_status(policy_payload)},
        {"role": "current_portfolio", "path": current_portfolio_summary.source_ref, "required": True, "status": current_portfolio_summary.status},
        {"role": "pending", "path": pending_summary.source_ref, "required": False, "status": pending_summary.status},
        {"role": "price_volatility", "path": price_volatility_summary.source_ref, "required": False, "status": price_volatility_summary.status},
        {"role": "corporate_event", "path": str(corporate_event_artifact_path or ""), "required": False, "status": _payload_status(corporate_payload)},
    ]
    source_hashes = [
        {"role": "candidate", "path": candidate_summary.source_ref, "sha256": _strip_sha256(candidate_summary.source_hash)},
        {"role": "opportunity", "path": opportunity_summary.source_ref, "sha256": _strip_sha256(opportunity_summary.source_hash)},
        {"role": "current_portfolio", "path": current_portfolio_summary.source_ref, "sha256": _strip_sha256(current_portfolio_summary.source_hash)},
    ]
    payload = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "producer": PRODUCER,
        "policy_version": POLICY_VERSION,
        "business_date": business_date,
        "as_of": as_of,
        "feature_date": feature_date,
        "artifact_lifecycle_status": ARTIFACT_LIFECYCLE_STATUS,
        "producer_result_status": status,
        "runtime_consumer_eligibility": RUNTIME_CONSUMER_ELIGIBILITY,
        **status_contract_fields(
            producer_result_status=status,
            artifact_lifecycle_status=ARTIFACT_LIFECYCLE_STATUS,
            runtime_consumer_eligibility=RUNTIME_CONSUMER_ELIGIBILITY,
            reason_codes=sorted(set(reasons)),
            decision_resolution="RESOLVED" if status == "PASS" else "UNRESOLVED",
        ),
        "component_weights": COMPONENT_WEIGHTS,
        "quality_band_boundaries": BAND_BOUNDARIES,
        "quality_action_boundaries": ACTION_BOUNDARIES,
        "decisions": decisions,
        "decision_count": len(decisions),
        "action_distribution": action_counts,
        "band_distribution": band_counts,
        "missing_evidence_count": missing_count,
        "source_artifacts": source_artifacts,
        "source_hashes": source_hashes,
        "upstream_artifacts": {name: summary.to_dict(requested_business_date=business_date) for name, summary in summaries.items()},
        "temporal_safety": {
            "point_in_time": not future,
            "future_leakage_used": future,
            "feature_date_lte_business_date": feature_date <= business_date,
            "implicit_latest_fallback_used": False,
        },
        "runtime_switch_performed": False,
        "historical_only_branch_used": False,
        "fixed_rank_n_limit_used": False,
        "fixed_raw_score_threshold_used": False,
        "target_position_count_decision_consumer": False,
        "future_information_used": False,
        "historical_result_input_used": False,
        "paper_ledger_input_used": False,
        "reason_codes": sorted(set(reasons)),
    }
    evidence = {
        "schema_version": "phase26_h_buy_quality_producer_evidence.v1",
        "business_date": business_date,
        "producer_result_status": status,
        "decision_count": len(decisions),
        "action_distribution": action_counts,
        "band_distribution": band_counts,
        "missing_evidence_count": missing_count,
        "reason_codes": payload["reason_codes"],
    }
    return payload, evidence


def validate_buy_quality_artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = {"schema_version", "business_date", "producer", "policy_version", "decisions", "component_weights"}
    for field in required:
        if field not in payload:
            errors.append(f"missing:{field}")
    weights = payload.get("component_weights")
    if not isinstance(weights, Mapping):
        errors.append("component_weights_not_object")
    elif abs(sum(float(value) for value in weights.values()) - 1.0) > 0.000001:
        errors.append("component_weights_sum_invalid")
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        errors.append("decisions_not_list")
    else:
        for index, decision in enumerate(decisions):
            errors.extend(_validate_decision(decision, index=index))
    if errors:
        raise ValueError("buy_quality_artifact_invalid:" + ",".join(errors))
    return {"status": "PASS", "errors": []}


def decision_by_symbol(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _symbol(decision): dict(decision)
        for decision in payload.get("decisions") or []
        if isinstance(decision, Mapping) and _symbol(decision)
    }


def quality_allocation_adjustment(decision: Mapping[str, Any] | None) -> float:
    if not isinstance(decision, Mapping):
        return 0.0
    action = str(decision.get("quality_action") or "")
    if action == "FULL_ALLOCATION_ELIGIBLE":
        return 1.0
    if action == "REDUCED_ALLOCATION_ONLY":
        score = _finite_float(decision.get("quality_score"))
        if score is None:
            return 0.0
        return round(max(0.25, min(0.85, score)), 6)
    return 0.0


def buy_quality_hash(payload: Mapping[str, Any]) -> str:
    clean = {k: v for k, v in dict(payload).items() if k != "artifact_hash"}
    encoded = json.dumps(clean, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def stable_payload_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _decision_for_row(
    *,
    business_date: str,
    as_of: str,
    opportunity: Mapping[str, Any],
    candidate: Mapping[str, Any],
    current: Mapping[str, Any],
    pending_symbols: set[str],
    price_volatility: Mapping[str, Any],
    all_scores: list[float],
    market_payload: Mapping[str, Any],
    policy_payload: Mapping[str, Any],
    corporate_payload: Mapping[str, Any],
    opportunity_source: BuyQualitySourceSummary,
    candidate_source: BuyQualitySourceSummary,
) -> dict[str, Any]:
    symbol = _symbol(opportunity)
    score = _finite_float(opportunity.get("expected_edge_score", opportunity.get("runtime_opportunity_score")))
    rank = _int_or_none(opportunity.get("buy_rank", opportunity.get("opportunity_buy_rank", opportunity.get("rank"))))
    row_hash = stable_payload_hash(dict(opportunity))
    source_opportunity_id = str(opportunity.get("opportunity_id") or opportunity.get("source_ref") or f"opportunity-{business_date}-{symbol}-{row_hash[:20]}")
    source_candidate_id = str(candidate.get("candidate_id") or candidate.get("source_ref") or opportunity.get("candidate_id") or "")
    relative = _relative_quality(score=score, rank=rank, scores=all_scores)
    market = _market_quality(market_payload)
    reliability = _signal_reliability(opportunity=opportunity, candidate=candidate, opportunity_source=opportunity_source, business_date=business_date)
    execution = _execution_feasibility(opportunity=opportunity, price_volatility=price_volatility, corporate_payload=corporate_payload)
    fit = _portfolio_fit(symbol=symbol, current=current, pending_symbols=pending_symbols, policy_payload=policy_payload)
    components = {
        "relative_opportunity_quality": relative,
        "market_context_quality_modifier": market,
        "signal_reliability": reliability,
        "execution_feasibility": execution,
        "portfolio_fit": fit,
    }
    component_scores = {name: item["score"] for name, item in components.items()}
    component_statuses = {name: item["status"] for name, item in components.items()}
    reason_codes = sorted({reason for item in components.values() for reason in item["reason_codes"]})
    critical_review = [name for name in CRITICAL_COMPONENTS if component_statuses.get(name) != "PASS"]
    no_buy_reason = str(opportunity.get("no_buy_reason") or "").strip()
    if score is None or score <= 0:
        critical_review.append("relative_opportunity_quality")
        reason_codes.append("non_positive_or_missing_raw_opportunity_score")
    if no_buy_reason:
        critical_review.append("relative_opportunity_quality")
        reason_codes.append(f"opportunity_no_buy_reason_present:{no_buy_reason}")
    if critical_review:
        quality_score = 0.0
        quality_band = "REVIEW_REQUIRED" if "relative_opportunity_quality" not in critical_review else "UNUSABLE"
        quality_action = "REJECT" if no_buy_reason or score is None or score <= 0 else "REVIEW_REQUIRED"
        quality_status = "REJECTED" if quality_action == "REJECT" else "REVIEW_REQUIRED"
        allocation_adjustment = 0.0
    else:
        weighted = sum(float(component_scores[name]) * float(COMPONENT_WEIGHTS[name]) for name in COMPONENT_WEIGHTS)
        quality_score = round(max(0.0, min(1.0, weighted)), 6)
        quality_band = _band(quality_score)
        relative_score = float(component_scores["relative_opportunity_quality"])
        full_allocation_quality_blocked = relative_score < 0.65 or "rank1_weak_population_not_full" in reason_codes
        if quality_score >= ACTION_BOUNDARIES["FULL_ALLOCATION_ELIGIBLE"] and not full_allocation_quality_blocked:
            quality_action = "FULL_ALLOCATION_ELIGIBLE"
        elif quality_score >= ACTION_BOUNDARIES["REDUCED_ALLOCATION_ONLY"]:
            quality_action = "REDUCED_ALLOCATION_ONLY"
            if full_allocation_quality_blocked:
                reason_codes.append("relative_quality_prevents_full_allocation")
        else:
            quality_action = "REJECT"
        quality_status = "PASS" if quality_action in SUBMITTABLE_ACTIONS else "REJECTED"
        allocation_adjustment = quality_allocation_adjustment({"quality_score": quality_score, "quality_action": quality_action})
    decision_id = "bq-" + hashlib.sha256(f"{business_date}|{symbol}|{source_opportunity_id}|{row_hash}".encode("utf-8")).hexdigest()[:24]
    return {
        "schema_version": SCHEMA_VERSION,
        "business_date": business_date,
        "symbol": symbol,
        "security_code": symbol,
        "quality_decision_id": decision_id,
        "quality_status": quality_status,
        "quality_score": quality_score,
        "quality_band": quality_band,
        "quality_action": quality_action,
        "quality_reason_codes": sorted(set(reason_codes)),
        "component_scores": component_scores,
        "component_statuses": component_statuses,
        "component_weights": COMPONENT_WEIGHTS,
        "component_details": components,
        "quality_allocation_adjustment": allocation_adjustment,
        "input_authority_refs": {
            "opportunity": opportunity_source.source_ref,
            "candidate": candidate_source.source_ref,
            "market_context": str(market_payload.get("artifact_hash") or ""),
            "portfolio_policy": str(policy_payload.get("artifact_hash") or ""),
        },
        "PIT_status": "PASS",
        "generated_at": as_of,
        "producer": PRODUCER,
        "policy_version": POLICY_VERSION,
        "source_candidate_id": source_candidate_id,
        "source_opportunity_id": source_opportunity_id,
        "source_opportunity_hash": row_hash,
        "opportunity_buy_rank": rank,
        "runtime_opportunity_score": score,
        "accepted_generation_binding": dict(opportunity_source.summary.get("accepted_generation_binding") or {}),
        "temporal_authority_binding": {
            "business_date": business_date,
            "feature_date": opportunity_source.feature_date,
            "source_business_date": opportunity_source.business_date,
            "future_information_used": False,
        },
        "temporal_binding": {
            "business_date": business_date,
            "feature_date": opportunity_source.feature_date,
            "source_business_date": opportunity_source.business_date,
        },
        "future_information_used": False,
        "historical_result_input_used": False,
        "paper_ledger_input_used": False,
        "target_position_count_decision_consumer": False,
        "fixed_rank_n_limit_used": False,
        "fixed_raw_score_threshold_used": False,
        **_listed_info_metadata(opportunity, candidate),
    }


def _listed_info_metadata(*rows: Mapping[str, Any]) -> dict[str, Any]:
    for row in rows:
        if not row:
            continue
        nested = row.get("listed_info")
        if isinstance(nested, Mapping):
            info = _listed_info_payload(row, nested)
            if info is not None:
                return _listed_info_metadata_fields(info)
        info = _listed_info_payload(row, row)
        if info is not None:
            return _listed_info_metadata_fields(info)
    return {}


def _listed_info_metadata_fields(info: Mapping[str, Any]) -> dict[str, Any]:
    market = str(info.get("market") or "").strip()
    product_category = str(info.get("product_category") or "").strip()
    security_type = str(info.get("security_type") or product_category).strip()
    current_listed = bool(info.get("current_listed", True))
    listed_info = {
        "code": str(info.get("code") or "").strip(),
        "market": market,
        "product_category": product_category,
        "security_type": security_type,
        "current_listed": current_listed,
    }
    return {
        "market": market,
        "market_name": market,
        "product_category": product_category,
        "security_type": security_type,
        "current_listed": current_listed,
        "is_current_listed": current_listed,
        "listed_info": listed_info,
    }


def _listed_info_payload(parent: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any] | None:
    product_category = str(row.get("product_category") or row.get("ProdCat") or "").strip()
    security_type = str(row.get("security_type") or row.get("SecType") or row.get("Type") or product_category).strip()
    market = str(row.get("market") or row.get("MktNm") or row.get("market_name") or "").strip()
    if not product_category and not security_type and not market:
        return None
    code = str(
        row.get("code")
        or row.get("Code")
        or row.get("security_code")
        or row.get("symbol")
        or parent.get("code")
        or parent.get("symbol")
        or parent.get("security_code")
        or ""
    ).strip()
    current_raw = row.get("current_listed", row.get("is_current_listed", True))
    current_listed = str(current_raw).lower() not in {"false", "0", "no", "nan", "none", ""}
    return {
        "code": code,
        "market": market,
        "product_category": product_category,
        "security_type": security_type,
        "current_listed": current_listed,
    }


def _relative_quality(*, score: float | None, rank: int | None, scores: list[float]) -> dict[str, Any]:
    if score is None or not scores:
        return _component(0.0, "REVIEW_REQUIRED", ["relative_opportunity_score_missing"])
    ordered = sorted(scores)
    n = len(ordered)
    percentile = sum(1 for item in ordered if item <= score) / n
    med = median(ordered)
    deviations = [abs(item - med) for item in ordered]
    mad = median(deviations) if deviations else 0.0
    robust_z = 0.0 if mad <= 0 else (score - med) / (1.4826 * mad)
    robust_norm = 1.0 / (1.0 + math.exp(-max(min(robust_z, 6.0), -6.0)))
    positive_ratio = sum(1 for item in ordered if item > 0) / n
    best = max(ordered)
    dispersion = max(ordered) - min(ordered)
    magnitude = max(best, 0.0) / (1.0 + abs(best) + abs(med))
    dispersion_norm = dispersion / (1.0 + dispersion)
    population_strength = max(0.0, min(1.0, 0.35 * positive_ratio + 0.45 * magnitude + 0.20 * dispersion_norm))
    relative_score = max(0.0, min(1.0, 0.45 * percentile + 0.25 * robust_norm + 0.30 * population_strength))
    reasons = [
        "relative_quality_uses_percentile_robust_z_population_strength",
        "rank_not_used_as_fixed_n_gate",
    ]
    if rank == 1 and population_strength < 0.45:
        reasons.append("rank1_weak_population_not_full")
    if n < 5:
        reasons.append("small_population_conservative")
        relative_score = min(relative_score, 0.62)
    return _component(relative_score, "PASS", reasons, {"percentile": round(percentile, 6), "robust_z": round(robust_z, 6), "population_strength": round(population_strength, 6), "population_size": n})


def _market_quality(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not payload:
        return _component(0.55, "NOT_AVAILABLE", ["market_context_missing_conservative_reduction"])
    confidence = _ratio(payload.get("confidence"), 0.5)
    breadth = _ratio(payload.get("breadth_value", payload.get("market_breadth")), 0.5)
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), Mapping) else {}
    volatility = _ratio(metrics.get("volatility_score", payload.get("volatility_score")), 0.5)
    trend_state = str(payload.get("trend_state") or payload.get("market_trend_state") or "").upper()
    trend_continuous = _trend_score(trend_state)
    score = max(0.0, min(1.0, 0.35 * confidence + 0.30 * breadth + 0.20 * trend_continuous + 0.15 * (1.0 - volatility)))
    return _component(score, "PASS", ["market_context_symbol_quality_modifier_no_exposure_duplication"], {"confidence": confidence, "breadth": breadth, "trend_score": trend_continuous, "volatility_risk": volatility})


def _signal_reliability(*, opportunity: Mapping[str, Any], candidate: Mapping[str, Any], opportunity_source: BuyQualitySourceSummary, business_date: str) -> dict[str, Any]:
    reasons = []
    binding = opportunity_source.summary.get("accepted_generation_binding") if isinstance(opportunity_source.summary, Mapping) else {}
    binding_status = str((binding or {}).get("status") or (binding or {}).get("binding_status") or "PASS").upper() if isinstance(binding, Mapping) else "PASS"
    if binding_status not in {"PASS", "BOUND", "COMMITTED"}:
        return _component(0.0, "REVIEW_REQUIRED", ["accepted_generation_binding_not_pass"])
    if opportunity_source.business_date != business_date or opportunity_source.feature_date > business_date:
        return _component(0.0, "REVIEW_REQUIRED", ["temporal_authority_mismatch"])
    confidence = min(_ratio(opportunity.get("confidence"), 0.75), _ratio(candidate.get("confidence"), 0.75))
    completeness = 1.0 if opportunity else 0.0
    calibration_applied = bool(opportunity_source.summary.get("calibration_applied")) if isinstance(opportunity_source.summary, Mapping) else False
    calibration_factor = 1.0 if calibration_applied else 0.85
    if not calibration_applied:
        reasons.append("calibration_not_applied_raw_score_not_expected_return")
    score = max(0.0, min(1.0, (0.60 * confidence + 0.40 * completeness) * calibration_factor))
    return _component(score, "PASS", reasons or ["signal_reliability_pass"], {"confidence": confidence, "calibration_applied": calibration_applied})


def _execution_feasibility(*, opportunity: Mapping[str, Any], price_volatility: Mapping[str, Any], corporate_payload: Mapping[str, Any]) -> dict[str, Any]:
    reasons = []
    if not price_volatility:
        return _component(0.70, "NOT_AVAILABLE", ["price_volatility_missing_noncritical_conservative_reduction"])
    liquidity = _ratio(price_volatility.get("liquidity_score", price_volatility.get("turnover_score")), 0.70)
    downside = _ratio(opportunity.get("downside_risk_score"), 0.45)
    event_penalty = 0.0
    if corporate_payload and str(corporate_payload.get("producer_result_status") or corporate_payload.get("status") or "").upper() not in {"PASS", ""}:
        event_penalty = 0.10
        reasons.append("corporate_event_not_pass_conservative_reduction")
    score = max(0.0, min(1.0, 0.65 * liquidity + 0.35 * (1.0 - downside) - event_penalty))
    return _component(score, "PASS", reasons or ["execution_feasibility_available"], {"liquidity": liquidity, "downside_risk": downside})


def _portfolio_fit(*, symbol: str, current: Mapping[str, Any], pending_symbols: set[str], policy_payload: Mapping[str, Any]) -> dict[str, Any]:
    current_weight = _ratio(current.get("current_weight", current.get("weight")), 0.0)
    single_name_cap = _ratio(policy_payload.get("single_name_weight_cap"), 0.18)
    exposure = _ratio(policy_payload.get("target_gross_exposure", policy_payload.get("target_gross_exposure_ratio")), 0.75)
    concentration_room = 1.0 if single_name_cap <= 0 else max(0.0, min(1.0, 1.0 - current_weight / single_name_cap))
    pending_penalty = 0.35 if symbol in pending_symbols else 0.0
    score = max(0.0, min(1.0, 0.70 * concentration_room + 0.30 * min(exposure, 1.0) - pending_penalty))
    reasons = ["portfolio_fit_not_position_count_gate"]
    if symbol in pending_symbols:
        reasons.append("active_pending_same_symbol_conservative_reduction")
    return _component(score, "PASS", reasons, {"current_weight": current_weight, "single_name_cap": single_name_cap, "target_gross_exposure": exposure})


def _component(score: float, status: str, reason_codes: list[str], details: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "score": round(max(0.0, min(1.0, float(score))), 6),
        "status": status,
        "reason_codes": sorted(set(reason_codes)),
        "details": dict(details or {}),
    }


def _band(score: float) -> str:
    if score >= BAND_BOUNDARIES["VERY_HIGH"]:
        return "VERY_HIGH"
    if score >= BAND_BOUNDARIES["HIGH"]:
        return "HIGH"
    if score >= BAND_BOUNDARIES["MEDIUM"]:
        return "MEDIUM"
    if score >= BAND_BOUNDARIES["LOW"]:
        return "LOW"
    return "UNUSABLE"


def _trend_score(state: str) -> float:
    if state in {"BULL", "UPTREND", "STRONG_UP"}:
        return 0.85
    if state in {"RANGE", "NEUTRAL", "BALANCED"}:
        return 0.60
    if state in {"BEAR", "DOWNTREND", "WEAK"}:
        return 0.35
    return 0.55


def _validate_decision(decision: Any, *, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(decision, Mapping):
        return [f"decision_not_object:{index}"]
    required = {"schema_version", "business_date", "symbol", "quality_decision_id", "quality_status", "quality_score", "quality_band", "quality_action", "component_scores", "component_statuses", "component_weights", "PIT_status", "producer", "policy_version"}
    for field in required:
        if field not in decision:
            errors.append(f"decision_missing:{index}:{field}")
    score = _finite_float(decision.get("quality_score"))
    if score is None or not 0.0 <= score <= 1.0:
        errors.append(f"decision_quality_score_invalid:{index}")
    if decision.get("quality_action") not in {"FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY", "REVIEW_REQUIRED", "REJECT"}:
        errors.append(f"decision_quality_action_invalid:{index}")
    if decision.get("future_information_used") is not False:
        errors.append(f"future_information_used:{index}")
    if decision.get("historical_result_input_used") is not False:
        errors.append(f"historical_result_input_used:{index}")
    if decision.get("paper_ledger_input_used") is not False:
        errors.append(f"paper_ledger_input_used:{index}")
    return errors


def _empty_summary(name: str, business_date: str) -> BuyQualitySourceSummary:
    return BuyQualitySourceSummary(status="PASS", business_date=business_date, feature_date=business_date, source_ref="", source_hash="", rows=(), summary={"reason": f"{name}_not_required"})


def _read_json(path: Path | str | None) -> dict[str, Any]:
    if path is None:
        return {}
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _payload_status(payload: Mapping[str, Any]) -> str:
    return str(payload.get("producer_result_status") or payload.get("status") or ("PASS" if payload else "MISSING")).upper()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _symbol(row: Mapping[str, Any]) -> str:
    return str(row.get("symbol") or row.get("security_code") or row.get("code") or "").strip()


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(float(value)):
        return None
    return float(value)


def _ratio(value: Any, default: float) -> float:
    parsed = _finite_float(value)
    if parsed is None:
        return default
    return max(0.0, min(1.0, float(parsed)))


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        return None


def _date(value: str) -> None:
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise ValueError(f"invalid_date:{value}")


def _strip_sha256(value: str) -> str:
    return value.removeprefix("sha256:")
