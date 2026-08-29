from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.strategy.status_contract import status_contract_fields


SCHEMA_VERSION = "strategy_intelligence.v1"
SEMANTIC_VERSION = "1.4.0"
PRODUCER_VERSION = "phase30_ai_selection_quality_comparator.v1"
PRODUCER = "Production-common Strategy Intelligence Evidence Producer"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"
PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY = "ELIGIBLE"
EDGE_CONTRACT = "EXPECTED_EDGE_RESEARCH_CONTRACT"
CALIBRATION_STATUS = "UNCALIBRATED"
SELECTION_QUALITY_COMPARATOR_SCHEMA_VERSION = "selection_quality_comparator.v1"
SELECTION_QUALITY_TIERS = {
    "HIGH_QUALITY_CONTINUATION",
    "VALID_CONTINUATION",
    "CAUTION_CONTINUATION",
    "INSUFFICIENT_QUALITY",
    "REJECT",
}


@dataclass(frozen=True)
class StrategyIntelligenceProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def produce_strategy_intelligence_artifact(
    *,
    business_date: str,
    candidate_summary: Mapping[str, Any],
    opportunity_summary: Mapping[str, Any],
    current_summary: Mapping[str, Any],
    technical_feature_summary: Mapping[str, Any],
    price_volatility_summary: Mapping[str, Any],
    market_context_artifact_path: Path | str | None,
    corporate_event_artifact_path: Path | str | None,
    buy_quality_artifact_path: Path | str | None,
    portfolio_construction_artifact_path: Path | str | None,
    position_sizing_artifact_path: Path | str | None,
    position_management_artifact_path: Path | str | None,
    runtime_planning_artifact_path: Path | str | None,
    output_path: Path | str,
    position_campaigns_artifact_path: Path | str | None = None,
    as_of: str | None = None,
    production_consumer_connected: bool = False,
    consumer_stage: str = "POST_ACTION_OBSERVABILITY",
) -> StrategyIntelligenceProducerResult:
    payload, evidence = build_strategy_intelligence_payload(
        business_date=business_date,
        candidate_summary=candidate_summary,
        opportunity_summary=opportunity_summary,
        current_summary=current_summary,
        technical_feature_summary=technical_feature_summary,
        price_volatility_summary=price_volatility_summary,
        market_context_artifact_path=market_context_artifact_path,
        corporate_event_artifact_path=corporate_event_artifact_path,
        buy_quality_artifact_path=buy_quality_artifact_path,
        portfolio_construction_artifact_path=portfolio_construction_artifact_path,
        position_sizing_artifact_path=position_sizing_artifact_path,
        position_management_artifact_path=position_management_artifact_path,
        runtime_planning_artifact_path=runtime_planning_artifact_path,
        position_campaigns_artifact_path=position_campaigns_artifact_path,
        as_of=as_of,
        production_consumer_connected=production_consumer_connected,
        consumer_stage=consumer_stage,
    )
    validate_strategy_intelligence_artifact(payload)
    artifact_hash = strategy_intelligence_hash(payload)
    final = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final)
    return StrategyIntelligenceProducerResult(
        status=str(final["producer_result_status"]),
        reason=",".join(final.get("reason_codes") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final,
        evidence=evidence,
    )


def build_strategy_intelligence_payload(
    *,
    business_date: str,
    candidate_summary: Mapping[str, Any],
    opportunity_summary: Mapping[str, Any],
    current_summary: Mapping[str, Any],
    technical_feature_summary: Mapping[str, Any],
    price_volatility_summary: Mapping[str, Any],
    market_context_artifact_path: Path | str | None,
    corporate_event_artifact_path: Path | str | None,
    buy_quality_artifact_path: Path | str | None,
    portfolio_construction_artifact_path: Path | str | None,
    position_sizing_artifact_path: Path | str | None,
    position_management_artifact_path: Path | str | None,
    runtime_planning_artifact_path: Path | str | None,
    position_campaigns_artifact_path: Path | str | None = None,
    as_of: str | None = None,
    production_consumer_connected: bool = False,
    consumer_stage: str = "POST_ACTION_OBSERVABILITY",
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _validate_timestamp_like(as_of, field="as_of")

    market_context = _read_json(market_context_artifact_path)
    corporate_event = _read_json(corporate_event_artifact_path)
    buy_quality = _read_json(buy_quality_artifact_path)
    portfolio_construction = _read_json(portfolio_construction_artifact_path)
    position_sizing = _read_json(position_sizing_artifact_path)
    position_management = _read_json(position_management_artifact_path)
    runtime_planning = _read_json(runtime_planning_artifact_path)
    position_campaigns = _read_json(position_campaigns_artifact_path)

    summaries = {
        "candidate": candidate_summary,
        "opportunity": opportunity_summary,
        "current": current_summary,
        "technical_features": technical_feature_summary,
        "price_volatility": price_volatility_summary,
    }
    payloads = {
        "market_context": market_context,
        "corporate_event": corporate_event,
        "buy_quality": buy_quality,
        "portfolio_construction": portfolio_construction,
        "position_sizing": position_sizing,
        "position_management": position_management,
        "runtime_planning": runtime_planning,
        "position_campaigns": position_campaigns,
    }

    reason_codes: list[str] = []
    future = False
    for name, summary in summaries.items():
        feature_date = str(summary.get("feature_date") or summary.get("business_date") or "")
        if feature_date and feature_date > business_date:
            future = True
            reason_codes.append(f"{name}_future_feature_date")
        if str(summary.get("status") or "") in {"MISSING", "BLOCK"}:
            reason_codes.append(f"{name}_source_{str(summary.get('status')).lower()}")
    downstream_required = consumer_stage != "PRE_ACTION_PRODUCTION_EVIDENCE"
    downstream_optional = {
        "portfolio_construction",
        "position_sizing",
        "position_management",
        "runtime_planning",
    }
    for name, payload in payloads.items():
        if not payload:
            if not downstream_required and name in downstream_optional:
                continue
            reason_codes.append(f"{name}_artifact_missing")
            continue
        feature_date = str(payload.get("feature_date") or payload.get("business_date") or "")
        if feature_date and feature_date > business_date:
            future = True
            reason_codes.append(f"{name}_future_feature_date")
        if _payload_future_leakage(payload):
            future = True
            reason_codes.append(f"{name}_future_leakage_flagged")

    symbol_rows = _symbol_rows(
        business_date=business_date,
        candidate_summary=candidate_summary,
        opportunity_summary=opportunity_summary,
        current_summary=current_summary,
        technical_feature_summary=technical_feature_summary,
        price_volatility_summary=price_volatility_summary,
        market_context=market_context,
        corporate_event=corporate_event,
        buy_quality=buy_quality,
        portfolio_construction=portfolio_construction,
        position_sizing=position_sizing,
        position_management=position_management,
        runtime_planning=runtime_planning,
        position_campaigns=position_campaigns,
    )
    if production_consumer_connected:
        symbol_rows = [_production_evidence_row(row) for row in symbol_rows]
    if not symbol_rows:
        reason_codes.append("symbol_intelligence_empty")
    selection_quality_summary = _selection_quality_summary(symbol_rows, technical_feature_summary=technical_feature_summary)

    producer_status = "BLOCK" if future else "PASS" if symbol_rows else "REVIEW_REQUIRED"
    lineage = _lineage_status(symbol_rows)
    if producer_status == "PASS" and any(item["status"] != "PASS" for item in lineage.values()):
        producer_status = "REVIEW_REQUIRED"
        reason_codes.append("lineage_partial")

    source_artifacts = _source_artifacts(
        business_date=business_date,
        paths={
            "market_context": market_context_artifact_path,
            "corporate_event": corporate_event_artifact_path,
            "buy_quality": buy_quality_artifact_path,
            "portfolio_construction": portfolio_construction_artifact_path,
            "position_sizing": position_sizing_artifact_path,
            "position_management": position_management_artifact_path,
            "runtime_planning": runtime_planning_artifact_path,
            "position_campaigns": position_campaigns_artifact_path,
        },
        summaries=summaries,
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "semantic_version": SEMANTIC_VERSION,
        "producer_version": PRODUCER_VERSION,
        "producer": PRODUCER,
        "producer_identity": {
            "module": __name__,
            "module_file": __file__,
            "artifact_function": "produce_strategy_intelligence_artifact",
            "payload_builder_function": "build_strategy_intelligence_payload",
            "campaign_identity_function": "_lifecycle_context",
            "campaign_join_function": "_current_or_same_day_closed_campaign_by_symbol",
            "producer_version": PRODUCER_VERSION,
            "semantic_version": SEMANTIC_VERSION,
        },
        "business_date": business_date,
        "as_of_business_date": business_date,
        "generated_at": as_of,
        "as_of": as_of,
        "pit_boundary": {
            "business_date": business_date,
            "market_data_as_of": _minimum_feature_date(summaries, payloads, default=business_date),
            "current_state_as_of": business_date,
            "future_information_used": False,
            "latest_fallback_used": False,
            "historical_outcome_used_as_runtime_input": False,
            "test_result_used_as_strategy_input": False,
            "historical_outcome_used_for_production_parameter_selection": False,
        },
        "artifact_lifecycle_status": ARTIFACT_LIFECYCLE_STATUS,
        "runtime_consumer_eligibility": PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY
        if production_consumer_connected
        else RUNTIME_CONSUMER_ELIGIBILITY,
        "producer_result_status": producer_status,
        "reason_codes": sorted(set(reason_codes)),
        **status_contract_fields(
            producer_result_status=producer_status,
            artifact_lifecycle_status=ARTIFACT_LIFECYCLE_STATUS,
            runtime_consumer_eligibility=PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY
            if production_consumer_connected
            else RUNTIME_CONSUMER_ELIGIBILITY,
            reason_codes=sorted(set(reason_codes)),
            decision_resolution="RESOLVED" if producer_status == "PASS" else "UNRESOLVED",
        ),
        "consumer_stage": consumer_stage,
        "shadow_only": not production_consumer_connected,
        "production_authority": False,
        "runtime_switch_performed": False,
        "production_consumer_connected": production_consumer_connected,
        "shadow_output_connected_to_production_action_authority": False,
        "shared_intelligence_not_action_authority": True,
        "new_ai_created": False,
        "production_model_retrained": False,
        "accepted_generation_changed": False,
        "future_information_used": False,
        "historical_outcome_used_as_runtime_input": False,
        "test_result_used_as_strategy_input": False,
        "historical_outcome_used_for_production_parameter_selection": False,
        "eligibility_event_facts": _eligibility_event_facts(corporate_event),
        "selection_quality_comparator_summary": selection_quality_summary,
        "symbol_intelligence": {row["symbol"]: row for row in symbol_rows},
        "symbol_count": len(symbol_rows),
        "run_level_sufficiency": {
            "status": "PASS" if producer_status == "PASS" else "REVIEW_REQUIRED",
            "lineage_status": lineage,
            "missing_inputs": sorted(set(reason_codes)),
        },
        "source_evidence": source_artifacts,
        "shadow_decision_comparison": _shadow_decision_comparison(symbol_rows),
        "lineage": lineage,
    }
    return payload, {
        "lineage": lineage,
        "symbol_count": len(symbol_rows),
        "selection_quality_comparator_summary": selection_quality_summary,
        "reason_codes": sorted(set(reason_codes)),
    }


def validate_strategy_intelligence_artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "schema_version",
        "semantic_version",
        "business_date",
        "as_of_business_date",
        "generated_at",
        "pit_boundary",
        "producer_result_status",
        "runtime_consumer_eligibility",
        "shadow_only",
        "production_authority",
        "symbol_intelligence",
        "shadow_decision_comparison",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError("strategy_intelligence_required_fields_missing:" + ",".join(missing))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("strategy_intelligence_schema_version_unsupported")
    if payload.get("production_authority") is not False:
        raise ValueError("strategy_intelligence_must_not_be_action_authority")
    if payload.get("runtime_consumer_eligibility") not in {
        RUNTIME_CONSUMER_ELIGIBILITY,
        PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY,
    }:
        raise ValueError("strategy_intelligence_runtime_consumer_eligibility_invalid")
    if payload.get("runtime_consumer_eligibility") == PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY:
        if payload.get("production_consumer_connected") is not True:
            raise ValueError("strategy_intelligence_production_consumer_marker_invalid")
        if payload.get("shadow_only") is not False:
            raise ValueError("strategy_intelligence_production_shadow_marker_invalid")
    elif payload.get("shadow_only") is not True:
        raise ValueError("strategy_intelligence_shadow_marker_invalid")
    if payload.get("future_information_used") is not False:
        raise ValueError("strategy_intelligence_future_information_flag_invalid")
    if payload.get("historical_outcome_used_as_runtime_input") is not False:
        raise ValueError("strategy_intelligence_historical_outcome_runtime_input_flag_invalid")
    if payload.get("test_result_used_as_strategy_input") is not False:
        raise ValueError("strategy_intelligence_test_result_strategy_input_flag_invalid")
    if payload.get("historical_outcome_used_for_production_parameter_selection") is not False:
        raise ValueError("strategy_intelligence_parameter_selection_flag_invalid")
    return {"status": "PASS", "schema_version": SCHEMA_VERSION}


def strategy_intelligence_hash(payload: Mapping[str, Any]) -> str:
    return stable_payload_hash({key: value for key, value in payload.items() if key != "artifact_hash"})


def stable_payload_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def load_strategy_intelligence_artifact(path: Path | str | None) -> dict[str, Any]:
    if path is None or not Path(path).is_file():
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    validate_strategy_intelligence_artifact(payload)
    return payload


def validate_strategy_intelligence_compatibility(
    path: Path | str | None,
    *,
    requested_business_date: str,
    production_use_requested: bool = False,
) -> dict[str, Any]:
    if path is None or not Path(path).is_file():
        return {
            "artifact_kind": "strategy_intelligence",
            "artifact_path": str(path or ""),
            "schema_version": "",
            "status": "SOURCE_MISSING",
            "production_decision_allowed": False,
            "production_evidence_allowed": False,
            "reason_codes": ["strategy_intelligence_missing"],
        }
    try:
        payload = load_strategy_intelligence_artifact(path)
    except Exception as exc:
        return {
            "artifact_kind": "strategy_intelligence",
            "artifact_path": str(path),
            "schema_version": "",
            "status": "INCOMPATIBLE_SCHEMA",
            "production_decision_allowed": False,
            "production_evidence_allowed": False,
            "reason_codes": [f"schema_validation_failed:{exc}"],
        }
    expected_hash = str(payload.get("artifact_hash") or "")
    actual_hash = strategy_intelligence_hash(payload)
    business_date = str(payload.get("business_date") or payload.get("as_of_business_date") or "")
    feature_date = str((payload.get("pit_boundary") or {}).get("market_data_as_of") or payload.get("feature_date") or business_date)
    date_ok = business_date == requested_business_date and bool(feature_date) and feature_date <= business_date
    hash_ok = bool(expected_hash) and expected_hash == actual_hash
    future = bool(payload.get("future_information_used") or (payload.get("pit_boundary") or {}).get("future_information_used"))
    eligible = payload.get("runtime_consumer_eligibility") == PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY
    reasons = list(payload.get("reason_codes") or [])
    status = "COMPATIBLE_PRODUCTION_EVIDENCE" if date_ok and hash_ok and not future and eligible else "REVIEW_REQUIRED"
    if not date_ok:
        status = "INCOMPATIBLE_DATE"
        reasons.append("strategy_intelligence_date_mismatch")
    if not hash_ok:
        status = "INCOMPATIBLE_HASH"
        reasons.append("strategy_intelligence_hash_mismatch")
    if future:
        status = "SOURCE_BLOCKED"
        reasons.append("strategy_intelligence_future_leakage")
    if production_use_requested and not eligible:
        status = "SOURCE_NOT_ELIGIBLE"
        reasons.append("strategy_intelligence_not_production_consumer_eligible")
    return {
        "artifact_kind": "strategy_intelligence",
        "artifact_path": str(path),
        "schema_version": str(payload.get("schema_version") or ""),
        "semantic_version": str(payload.get("semantic_version") or ""),
        "status": status,
        "schema_compatible": True,
        "production_decision_allowed": False,
        "production_evidence_allowed": status == "COMPATIBLE_PRODUCTION_EVIDENCE",
        "business_date": business_date,
        "feature_date": feature_date,
        "business_date_aligned": date_ok,
        "feature_date_point_in_time": date_ok and not future,
        "artifact_hash_valid": hash_ok,
        "runtime_consumer_eligibility": str(payload.get("runtime_consumer_eligibility") or ""),
        "production_consumer_connected": bool(payload.get("production_consumer_connected")),
        "reason_codes": sorted(set(str(reason) for reason in reasons)),
    }


def symbol_intelligence_by_symbol(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    symbols = payload.get("symbol_intelligence")
    if not isinstance(symbols, Mapping):
        return {}
    return {
        str(symbol): dict(row)
        for symbol, row in symbols.items()
        if str(symbol) and isinstance(row, Mapping)
    }


def _symbol_rows(
    *,
    business_date: str,
    candidate_summary: Mapping[str, Any],
    opportunity_summary: Mapping[str, Any],
    current_summary: Mapping[str, Any],
    technical_feature_summary: Mapping[str, Any],
    price_volatility_summary: Mapping[str, Any],
    market_context: Mapping[str, Any],
    corporate_event: Mapping[str, Any],
    buy_quality: Mapping[str, Any],
    portfolio_construction: Mapping[str, Any],
    position_sizing: Mapping[str, Any],
    position_management: Mapping[str, Any],
    runtime_planning: Mapping[str, Any],
    position_campaigns: Mapping[str, Any],
) -> list[dict[str, Any]]:
    candidate_by_symbol = _rows_by_symbol(candidate_summary)
    opportunity_by_symbol = _rows_by_symbol(opportunity_summary)
    current_by_symbol = _rows_by_symbol(current_summary)
    technical_by_symbol = _rows_by_symbol(technical_feature_summary)
    volatility_by_symbol = _rows_by_symbol(price_volatility_summary)
    buy_quality_by_symbol = _rows_by_symbol_payload(buy_quality, "decisions")
    pc_by_symbol = _rows_by_symbol_payload(portfolio_construction, "portfolio_members")
    sizing_by_symbol = _rows_by_symbol_payload(position_sizing, "position_sizing")
    pm_by_symbol = _rows_by_symbol_payload(position_management, "decisions")
    plan_by_symbol = _rows_by_symbol_payload(runtime_planning, "plans")
    campaign_by_symbol = _current_or_same_day_closed_campaign_by_symbol(position_campaigns, business_date=business_date)

    symbols = sorted(
        set(candidate_by_symbol)
        | set(opportunity_by_symbol)
        | set(current_by_symbol)
        | set(technical_by_symbol)
        | set(volatility_by_symbol)
        | set(buy_quality_by_symbol)
        | set(pc_by_symbol)
        | set(sizing_by_symbol)
        | set(pm_by_symbol)
        | set(plan_by_symbol)
    )
    event_by_symbol = _event_status_by_symbol(corporate_event)
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        technical = technical_by_symbol.get(symbol, {})
        volatility = volatility_by_symbol.get(symbol, {})
        opportunity = opportunity_by_symbol.get(symbol, {})
        current = current_by_symbol.get(symbol, {})
        bq = buy_quality_by_symbol.get(symbol, {})
        pc = pc_by_symbol.get(symbol, {})
        sizing = sizing_by_symbol.get(symbol, {})
        pm = pm_by_symbol.get(symbol, {})
        plan = plan_by_symbol.get(symbol, {})
        eligibility = _eligibility_for_symbol(
            symbol=symbol,
            business_date=business_date,
            candidate=candidate_by_symbol.get(symbol, {}),
            opportunity=opportunity,
            current=current,
            corporate_event=corporate_event,
            event_status=event_by_symbol.get(symbol, {}),
        )
        cq = _continuation_quality(symbol=symbol, business_date=business_date, technical=technical, market_context=market_context)
        risk = _downside_risk(
            symbol=symbol,
            business_date=business_date,
            technical=technical,
            volatility=volatility,
            market_context=market_context,
            corporate_event=corporate_event,
            event_status=event_by_symbol.get(symbol, {}),
        )
        expected_edge = _expected_edge(
            symbol=symbol,
            opportunity=opportunity,
            buy_quality=bq,
            portfolio_construction=pc,
            position_sizing=sizing,
            continuation_quality=cq,
            downside_risk=risk,
        )
        current_decision = _current_decision(buy_quality=bq, portfolio_construction=pc, position_management=pm, runtime_planning=plan)
        lifecycle = _lifecycle_context(
            symbol=symbol,
            current=current,
            position_management=pm,
            portfolio_construction=pc,
            campaign=campaign_by_symbol.get(symbol, {}),
            campaign_artifact=position_campaigns,
        )
        profit_protection = _profit_protection_evidence(
            lifecycle_context=lifecycle,
            continuation_quality=cq,
            downside_risk=risk,
            current_decision=current_decision,
        )
        entry_admission = _entry_admission(
            symbol=symbol,
            business_date=business_date,
            eligibility=eligibility,
            continuation_quality=cq,
            downside_risk=risk,
            expected_edge=expected_edge,
            lifecycle_context=lifecycle,
            current_decision=current_decision,
        )
        selection_quality = _selection_quality_comparator(
            symbol=symbol,
            business_date=business_date,
            candidate=candidate_by_symbol.get(symbol, {}),
            opportunity=opportunity,
            technical=technical,
            buy_quality=bq,
            eligibility=eligibility,
            continuation_quality=cq,
            downside_risk=risk,
            expected_edge=expected_edge,
            entry_admission=entry_admission,
            current_decision=current_decision,
            market_context=market_context,
        )
        interpretation = _strategy_intelligence_interpretation(
            eligibility=eligibility,
            continuation_quality=cq,
            downside_risk=risk,
            expected_edge=expected_edge,
            lifecycle_context=lifecycle,
            current_decision=current_decision,
            profit_protection_evidence=profit_protection,
            entry_admission=entry_admission,
        )
        rows.append(
            {
                "symbol": symbol,
                "eligibility": eligibility,
                "continuation_quality": cq,
                "downside_risk": risk,
                "expected_edge": expected_edge,
                "entry_admission": entry_admission,
                "selection_quality_comparator": selection_quality,
                "current_decision": current_decision,
                "lifecycle_context": lifecycle,
                "profit_protection_evidence": profit_protection,
                "strategy_intelligence_interpretation": interpretation,
                "provenance": _symbol_provenance(
                    symbol=symbol,
                    candidate=candidate_by_symbol.get(symbol, {}),
                    opportunity=opportunity,
                    current=current,
                    technical=technical,
                    volatility=volatility,
                    buy_quality=bq,
                    portfolio_construction=pc,
                    position_sizing=sizing,
                    position_management=pm,
                    runtime_planning=plan,
                    position_campaign=campaign_by_symbol.get(symbol, {}),
                ),
            }
        )
    return rows


def _production_evidence_row(row: Mapping[str, Any]) -> dict[str, Any]:
    updated = dict(row)
    expected_edge = dict(updated.get("expected_edge") or {})
    expected_edge.update(
        {
            "status": CALIBRATION_STATUS,
            "research_only": False,
            "shadow_only": False,
            "production_evidence": True,
            "economic_units_available": False,
            "not_action_authority": True,
        }
    )
    updated["expected_edge"] = expected_edge

    entry_admission = dict(updated.get("entry_admission") or {})
    entry_admission.update(
        {
            "shadow_only": False,
            "production_evidence": True,
            "not_action_authority": True,
        }
    )
    updated["entry_admission"] = entry_admission

    selection_quality = dict(updated.get("selection_quality_comparator") or {})
    selection_quality.update(
        {
            "shadow_only": False,
            "production_evidence": True,
            "not_action_authority": True,
        }
    )
    updated["selection_quality_comparator"] = selection_quality

    profit_protection = dict(updated.get("profit_protection_evidence") or {})
    profit_protection.update(
        {
            "shadow_only": False,
            "production_evidence": True,
            "not_action_authority": True,
        }
    )
    updated["profit_protection_evidence"] = profit_protection

    interpretation = dict(updated.get("strategy_intelligence_interpretation") or {})
    interpretation.update(
        {
            "interpretation_contract": "STRATEGY_INTELLIGENCE_INTERPRETATION_PRODUCTION_EVIDENCE",
            "shadow_only": False,
            "production_evidence": True,
            "actual_behavior_changed": False,
            "not_action_authority": True,
        }
    )
    updated["strategy_intelligence_interpretation"] = interpretation
    return updated


def _continuation_quality(*, symbol: str, business_date: str, technical: Mapping[str, Any], market_context: Mapping[str, Any]) -> dict[str, Any]:
    del symbol
    missing = []
    optional_gaps = []
    trend = _trend_health(technical)
    persistence = _persistence(technical)
    acceleration = _acceleration(technical)
    exhaustion = _exhaustion(technical)
    participation = _participation(technical)
    relative_strength = _relative_strength(technical=technical, market_context=market_context, business_date=business_date)
    regime = _regime_compatibility(market_context, business_date=business_date)
    for name, item in (
        ("trend_health", trend),
        ("persistence", persistence),
        ("acceleration_state", acceleration),
        ("exhaustion_risk", exhaustion),
        ("participation_quality", participation),
        ("regime_compatibility", regime),
    ):
        if item["evidence_sufficiency"] != "SUFFICIENT":
            missing.extend(item.get("missing_inputs") or [name])
    if relative_strength["evidence_sufficiency"] != "SUFFICIENT":
        optional_gaps.extend(relative_strength.get("missing_inputs") or ["relative_strength"])
    return {
        "status": "PASS" if not missing else "REVIEW_REQUIRED",
        "trend_health": trend,
        "persistence": persistence,
        "acceleration_state": acceleration,
        "exhaustion_risk": exhaustion,
        "participation_quality": participation,
        "relative_strength": relative_strength,
        "regime_compatibility": regime,
        "evidence_sufficiency": "SUFFICIENT" if not missing else "PARTIAL",
        "missing_inputs": sorted(set(str(item) for item in missing)),
        "known_data_gaps": sorted(set(str(item) for item in optional_gaps)),
        "confidence": "MEDIUM" if not missing else "LOW",
        "future_information_used": False,
    }


def _downside_risk(
    *,
    symbol: str,
    business_date: str,
    technical: Mapping[str, Any],
    volatility: Mapping[str, Any],
    market_context: Mapping[str, Any],
    corporate_event: Mapping[str, Any],
    event_status: Mapping[str, Any],
) -> dict[str, Any]:
    del symbol
    reversal = _reversal_risk(technical)
    vol = _volatility_risk(technical=technical, volatility=volatility)
    exhaustion = _exhaustion(technical)
    participation = _participation_risk(technical)
    micro = _microstructure_risk(technical or volatility)
    regime = _regime_risk(market_context, business_date=business_date)
    event = _event_uncertainty(corporate_event=corporate_event, event_status=event_status, business_date=business_date)
    missing: list[str] = []
    for name, item in (
        ("reversal_risk", reversal),
        ("volatility_risk", vol),
        ("exhaustion_risk", exhaustion),
        ("participation_risk", participation),
        ("microstructure_risk", micro),
        ("regime_risk", regime),
        ("event_uncertainty", event),
    ):
        if item["evidence_sufficiency"] not in {"SUFFICIENT", "PARTIAL"}:
            missing.extend(item.get("missing_inputs") or [name])
    return {
        "status": "PASS" if not missing else "REVIEW_REQUIRED",
        "reversal_risk": reversal,
        "volatility_risk": vol,
        "exhaustion_risk": exhaustion,
        "participation_risk": participation,
        "microstructure_risk": micro,
        "regime_risk": regime,
        "event_uncertainty": event,
        "evidence_sufficiency": "SUFFICIENT" if not missing else "PARTIAL",
        "missing_inputs": sorted(set(str(item) for item in missing)),
        "confidence": "MEDIUM" if not missing else "LOW",
        "probabilistic_risk_not_automatic_reject": True,
        "future_information_used": False,
    }


def _expected_edge(
    *,
    symbol: str,
    opportunity: Mapping[str, Any],
    buy_quality: Mapping[str, Any],
    portfolio_construction: Mapping[str, Any],
    position_sizing: Mapping[str, Any],
    continuation_quality: Mapping[str, Any],
    downside_risk: Mapping[str, Any],
) -> dict[str, Any]:
    del symbol
    runtime_score = _optional_float(
        opportunity.get("runtime_opportunity_score", opportunity.get("expected_edge_score", portfolio_construction.get("runtime_opportunity_score")))
    )
    return {
        "status": "SHADOW_ONLY",
        "edge_contract": EDGE_CONTRACT,
        "calibration_status": CALIBRATION_STATUS,
        "research_only": True,
        "shadow_only": True,
        "continuation_opportunity": {
            "state": _state_from_status(continuation_quality.get("status")),
            "source": "continuation_quality",
            "not_calibrated_return": True,
        },
        "payoff_asymmetry": {
            "state": "UNMODELED",
            "evidence_sufficiency": "INSUFFICIENT",
            "missing_inputs": ["calibrated_payoff_distribution"],
        },
        "downside_distribution_proxy": {
            "state": _state_from_status(downside_risk.get("status")),
            "source": "downside_risk",
            "not_calibrated_distribution": True,
        },
        "opportunity_cost_context": {
            "runtime_opportunity_score": runtime_score,
            "score_semantics": "uncalibrated_relative_model_score",
            "calibration_applied": False,
            "economic_units_available": False,
            "buy_quality_action": buy_quality.get("quality_action"),
            "portfolio_membership_intent": portfolio_construction.get("membership_intent"),
        },
        "turnover_consideration": {
            "state": "UNMODELED",
            "evidence_sufficiency": "INSUFFICIENT",
        },
        "incremental_edge_for_add": {
            "state": "DESCRIPTIVE_ONLY",
            "position_sizing_target_notional": position_sizing.get("target_notional"),
            "not_action_authority": True,
        },
        "relative_edge_for_hold_vs_replacement": {
            "state": "DESCRIPTIVE_ONLY",
            "not_action_authority": True,
        },
        "future_information_used": False,
    }


def _trend_health(row: Mapping[str, Any]) -> dict[str, Any]:
    close_ma20 = _optional_float(row.get("trend_close_over_ma_20d"))
    ma5_ma20 = _optional_float(row.get("trend_ma_5_20_ratio"))
    if close_ma20 is None or ma5_ma20 is None:
        return _dimension_missing("trend_health", row, ["trend_close_over_ma_20d", "trend_ma_5_20_ratio"])
    state = "SUPPORTIVE" if close_ma20 >= 1.0 and ma5_ma20 >= 1.0 else "WEAK" if close_ma20 < 1.0 and ma5_ma20 < 1.0 else "MIXED"
    return _dimension("trend_health", state, row, {"trend_close_over_ma_20d": close_ma20, "trend_ma_5_20_ratio": ma5_ma20})


def _persistence(row: Mapping[str, Any]) -> dict[str, Any]:
    values = {name: _optional_float(row.get(name)) for name in ("price_momentum_return_5d", "price_momentum_return_10d", "price_momentum_return_20d")}
    if any(value is None for value in values.values()):
        return _dimension_missing("persistence", row, [name for name, value in values.items() if value is None])
    positives = sum(1 for value in values.values() if value is not None and value > 0)
    state = "SUPPORTIVE" if positives == 3 else "MIXED" if positives else "WEAK"
    return _dimension("persistence", state, row, values)


def _acceleration(row: Mapping[str, Any]) -> dict[str, Any]:
    d5_20 = _optional_float(row.get("momentum_5d_vs_20d_delta"))
    d1_5 = _optional_float(row.get("momentum_1d_vs_5d_delta"))
    if d5_20 is None or d1_5 is None:
        return _dimension_missing("acceleration_state", row, ["momentum_5d_vs_20d_delta", "momentum_1d_vs_5d_delta"])
    state = "ACCELERATING" if d5_20 > 0 and d1_5 > 0 else "DECELERATING" if d5_20 < 0 and d1_5 < 0 else "MIXED"
    return _dimension("acceleration_state", state, row, {"momentum_5d_vs_20d_delta": d5_20, "momentum_1d_vs_5d_delta": d1_5})


def _exhaustion(row: Mapping[str, Any]) -> dict[str, Any]:
    r20 = _optional_float(row.get("price_momentum_return_20d"))
    r1 = _optional_float(row.get("price_momentum_return_1d"))
    r3 = _optional_float(row.get("price_momentum_return_3d"))
    if r20 is None or r1 is None or r3 is None:
        return _dimension_missing("exhaustion_risk", row, ["price_momentum_return_20d", "price_momentum_return_1d", "price_momentum_return_3d"])
    state = "ELEVATED_RISK" if r20 > 0 and (r1 < 0 or r3 < 0) else "MANAGEABLE" if r20 > 0 else "MIXED"
    return _dimension("exhaustion_risk", state, row, {"price_momentum_return_20d": r20, "price_momentum_return_1d": r1, "price_momentum_return_3d": r3})


def _participation(row: Mapping[str, Any]) -> dict[str, Any]:
    ratio = _optional_float(row.get("volume_momentum_ratio_5d"))
    traded = _optional_float(row.get("rolling_median_traded_value_20"))
    if ratio is None:
        return _dimension_missing("participation_quality", row, ["volume_momentum_ratio_5d"])
    state = "SUPPORTIVE" if ratio >= 1.0 else "WEAK"
    return _dimension("participation_quality", state, row, {"volume_momentum_ratio_5d": ratio, "rolling_median_traded_value_20": traded})


def _relative_strength(*, technical: Mapping[str, Any], market_context: Mapping[str, Any], business_date: str) -> dict[str, Any]:
    symbol_5d = _optional_float(technical.get("price_momentum_return_5d"))
    symbol_20d = _optional_float(technical.get("price_momentum_return_20d"))
    metrics = market_context.get("metrics") if isinstance(market_context.get("metrics"), Mapping) else {}
    market_5d = _optional_float(metrics.get("return_5d_equal_weight") or market_context.get("return_5d_equal_weight"))
    market_20d = _optional_float(metrics.get("return_20d_equal_weight") or market_context.get("return_20d_equal_weight"))
    values: dict[str, Any] = {}
    comparisons: list[float] = []
    if symbol_5d is not None and market_5d is not None:
        values["stock_vs_market_return_5d"] = symbol_5d - market_5d
        values["symbol_return_5d"] = symbol_5d
        values["market_return_5d_equal_weight"] = market_5d
        comparisons.append(symbol_5d - market_5d)
    if symbol_20d is not None and market_20d is not None:
        values["stock_vs_market_return_20d"] = symbol_20d - market_20d
        values["symbol_return_20d"] = symbol_20d
        values["market_return_20d_equal_weight"] = market_20d
        comparisons.append(symbol_20d - market_20d)
    missing_inputs = [
        "stock_vs_sector_relative_strength_authority",
        "sector_vs_market_symbol_join_authority",
    ]
    if not comparisons:
        missing = ["explicit_relative_strength_authority", "symbol_return_authority", "market_equal_weight_return_authority", *missing_inputs]
        return {
            "state": "INSUFFICIENT_AUTHORITY",
            "semantic_meaning": "transparent relative strength authority is not available for this symbol/date",
            "authority_connection_status": "INSUFFICIENT_AUTHORITY",
            "evidence_sufficiency": "INSUFFICIENT",
            "missing_inputs": missing,
            "source_references": [_source_ref(item) for item in (technical, market_context) if item],
            "as_of_date": business_date,
            "values": {},
            "rank_or_opportunity_score_used": False,
            "future_information_used": False,
        }
    state = "SUPPORTIVE" if all(value >= 0 for value in comparisons) else "WEAK" if all(value < 0 for value in comparisons) else "MIXED"
    return {
        "state": state,
        "semantic_meaning": "stock-vs-market PIT relative return is connected; stock-vs-sector and sector-vs-market remain explicit gaps",
        "authority_connection_status": "PARTIALLY_CONNECTED",
        "evidence_sufficiency": "PARTIAL",
        "missing_inputs": missing_inputs,
        "source_references": [_source_ref(item) for item in (technical, market_context) if item],
        "as_of_date": business_date,
        "values": values,
        "rank_or_opportunity_score_used": False,
        "future_information_used": False,
    }


def _participation_risk(row: Mapping[str, Any]) -> dict[str, Any]:
    item = _participation(row)
    state = "ELEVATED_RISK" if item["state"] == "WEAK" else "MANAGEABLE" if item["state"] == "SUPPORTIVE" else item["state"]
    return {**item, "state": state, "semantic_meaning": "weak participation may reduce continuation confidence"}


def _reversal_risk(row: Mapping[str, Any]) -> dict[str, Any]:
    item = _exhaustion(row)
    state = "ELEVATED_RISK" if item["state"] == "ELEVATED_RISK" else "MANAGEABLE" if item["state"] == "MANAGEABLE" else item["state"]
    return {**item, "state": state, "semantic_meaning": "strong prior momentum with negative short structure is represented as probabilistic risk, not a veto"}


def _volatility_risk(*, technical: Mapping[str, Any], volatility: Mapping[str, Any]) -> dict[str, Any]:
    vol = _optional_float(technical.get("volatility_return_std_20d", volatility.get("volatility_return_std_20d", volatility.get("volatility_value"))))
    z1 = _optional_float(technical.get("recent_move_volatility_z_1d"))
    z3 = _optional_float(technical.get("recent_move_volatility_z_3d"))
    row = technical or volatility
    if vol is None:
        return _dimension_missing("volatility_risk", row, ["volatility_return_std_20d"])
    state = "ELEVATED_RISK" if (z1 is not None and abs(z1) >= 1.0) or (z3 is not None and abs(z3) >= 1.0) else "OBSERVED"
    return _dimension("volatility_risk", state, row, {"volatility_return_std_20d": vol, "recent_move_volatility_z_1d": z1, "recent_move_volatility_z_3d": z3})


def _microstructure_risk(row: Mapping[str, Any]) -> dict[str, Any]:
    price = _optional_float(row.get("reference_price"))
    traded = _optional_float(row.get("rolling_median_traded_value_20"))
    if price is None:
        return _dimension_missing("microstructure_risk", row, ["reference_price"])
    lot_notional = price * 100.0
    return _dimension(
        "microstructure_risk",
        "OBSERVED",
        row,
        {"reference_price": price, "standard_lot_notional": lot_notional, "rolling_median_traded_value_20": traded},
    )


def _regime_compatibility(market_context: Mapping[str, Any], *, business_date: str) -> dict[str, Any]:
    regime = _market_regime(market_context)
    if not regime:
        return {
            "state": "UNKNOWN",
            "semantic_meaning": "market regime compatibility unavailable",
            "evidence_sufficiency": "INSUFFICIENT",
            "missing_inputs": ["market_context_regime"],
            "source_references": [],
            "as_of_date": business_date,
        }
    return {
        "state": "OBSERVED",
        "semantic_meaning": "PIT market regime is exposed for consumer interpretation without Phase30-J thresholds",
        "evidence_sufficiency": "SUFFICIENT",
        "missing_inputs": [],
        "source_references": [_source_ref(market_context)],
        "as_of_date": str(market_context.get("business_date") or business_date),
        "value": regime,
    }


def _regime_risk(market_context: Mapping[str, Any], *, business_date: str) -> dict[str, Any]:
    item = _regime_compatibility(market_context, business_date=business_date)
    regime = str(item.get("value") or "")
    state = "ELEVATED_RISK" if regime in {"BEAR", "CORRECTION"} else "OBSERVED" if regime else item["state"]
    return {**item, "state": state, "semantic_meaning": "regime stress is evidence for interpretation, not a Phase30-J threshold"}


SPECIAL_RISK_EVENT_TYPES = {
    "DELISTING_PENDING",
    "LISTING_STATUS",
    "SUPERVISION_STATUS",
    "SPECIAL_SUPERVISION_STATUS",
    "ALERT_STATUS",
    "SPECIAL_CAUTION_STATUS",
    "GOVERNANCE_RISK_STATUS",
    "LISTING_REVIEW_STATUS",
}

KNOWN_SYMBOL_EVENT_COVERAGE_VALUES = {
    "AVAILABLE",
    "KNOWN",
    "KNOWN_SAFE",
    "KNOWN_NO_EVENT",
    "NO_EVENT_CONFIRMED",
    "EVENT_PRESENT",
}

UNKNOWN_SYMBOL_EVENT_COVERAGE_VALUES = {
    "",
    "UNKNOWN",
    "MISSING",
    "NOT_IMPLEMENTED",
    "PARTIAL",
    "UNAVAILABLE",
    "SOURCE_UNAVAILABLE",
    "RAW_EXISTS_NOT_CONNECTED",
}


def _event_uncertainty(*, corporate_event: Mapping[str, Any], event_status: Mapping[str, Any], business_date: str) -> dict[str, Any]:
    coverage = str(corporate_event.get("coverage_status") or corporate_event.get("overall_coverage_status") or "").upper()
    symbol_coverage = str(event_status.get("coverage_status") or event_status.get("source_coverage_status") or "").upper()
    event_state = str(event_status.get("event_status") or event_status.get("status") or "").upper()
    source_business_date = str(corporate_event.get("business_date") or "")
    event_facts = [dict(item) for item in event_status.get("event_facts") or [] if isinstance(item, Mapping)]
    special_risk_facts = _special_risk_facts(event_status=event_status, event_facts=event_facts)
    coverage_state = _special_risk_coverage_state_from_event(
        source_coverage=coverage,
        symbol_coverage=symbol_coverage,
        event_state=event_state,
        event_facts=event_facts,
        source_business_date=source_business_date,
        business_date=business_date,
    )
    if _event_source_conflict(corporate_event=corporate_event, event_status=event_status):
        coverage_state = "CONFLICT"
    if special_risk_facts:
        state = "SPECIAL_RISK_PRESENT"
        risk_state = "REVIEW_REQUIRED"
        eligibility_implication = "REVIEW_REQUIRED"
    elif coverage_state == "KNOWN":
        state = "MANAGEABLE"
        risk_state = "NORMAL"
        eligibility_implication = "BUY_ALLOWED"
    else:
        state = "EVENT_COVERAGE_INCOMPLETE"
        risk_state = "UNKNOWN"
        eligibility_implication = "REVIEW_REQUIRED"
    return {
        "state": state,
        "semantic_meaning": "missing event evidence is materialized as uncertainty, not SAFE",
        "authority_type": "SPECIAL_RISK_ELIGIBILITY_AUTHORITY",
        "canonical_producer": "ai_fund_lab_v2.strategy.corporate_event.build_symbol_event_coverage",
        "canonical_artifact": "corporate_event.symbol_event_facts",
        "canonical_field": "symbol_event_facts.<symbol>.coverage_status",
        "temporal_binding": "corporate_event.business_date <= strategy_intelligence.business_date; no future event facts consumed",
        "coverage_state": coverage_state,
        "universe_coverage_state": _universe_coverage_state(corporate_event=corporate_event, coverage_state=coverage_state),
        "negative_evidence_safe_to_use": coverage_state == "KNOWN" and event_state == "KNOWN_NO_EVENT",
        "risk_state": risk_state,
        "eligibility_implication": eligibility_implication,
        "evidence_sufficiency": "PARTIAL" if state == "EVENT_COVERAGE_INCOMPLETE" else "SUFFICIENT",
        "missing_inputs": [] if state in {"MANAGEABLE", "SPECIAL_RISK_PRESENT"} else [_missing_event_authority_reason(coverage_state)],
        "source_references": [_source_ref(corporate_event)] if corporate_event else [],
        "as_of_date": source_business_date or business_date,
        "coverage_status": coverage or "MISSING",
        "symbol_coverage_status": symbol_coverage or "UNKNOWN",
        "event_status": event_state,
        "event_facts": event_facts,
        "special_risk_event_facts": special_risk_facts,
        "future_information_used": False,
    }


def _special_risk_coverage_state_from_event(
    *,
    source_coverage: str,
    symbol_coverage: str,
    event_state: str,
    event_facts: list[dict[str, Any]],
    source_business_date: str,
    business_date: str,
) -> str:
    if source_business_date and business_date and source_business_date[:10] != business_date[:10]:
        return "STALE"
    if source_coverage != "AVAILABLE":
        return "UNKNOWN"
    if event_facts:
        return "KNOWN"
    if event_state in {"KNOWN_NO_EVENT", "NO_EVENT_CONFIRMED"}:
        return "KNOWN"
    if symbol_coverage in UNKNOWN_SYMBOL_EVENT_COVERAGE_VALUES:
        return "UNKNOWN"
    if symbol_coverage in KNOWN_SYMBOL_EVENT_COVERAGE_VALUES:
        return "KNOWN"
    return "UNKNOWN"


def _universe_coverage_state(*, corporate_event: Mapping[str, Any], coverage_state: str) -> str:
    if coverage_state == "STALE":
        return "STALE"
    contract = corporate_event.get("coverage_contract") if isinstance(corporate_event.get("coverage_contract"), Mapping) else {}
    event_absence_authorized = bool(contract.get("event_absence_authorized"))
    coverage = str(corporate_event.get("coverage_status") or corporate_event.get("overall_coverage_status") or "").upper()
    if coverage == "AVAILABLE" and event_absence_authorized:
        return "KNOWN_COMPLETE"
    if coverage == "AVAILABLE":
        return "KNOWN_PARTIAL"
    if coverage in {"PARTIAL"}:
        return "KNOWN_PARTIAL"
    return "UNKNOWN"


def _missing_event_authority_reason(coverage_state: str) -> str:
    if coverage_state == "CONFLICT":
        return "conflicting_event_coverage_authority"
    if coverage_state == "STALE":
        return "stale_event_coverage_authority"
    return "complete_event_coverage_authority"


def _event_source_conflict(*, corporate_event: Mapping[str, Any], event_status: Mapping[str, Any]) -> bool:
    values = [
        corporate_event.get("source_authority_status"),
        corporate_event.get("producer_result_status"),
        *(corporate_event.get("reason_codes") or []),
        *(event_status.get("reason_codes") or []),
    ]
    return any("CONFLICT" in str(value or "").upper() for value in values)


def _special_risk_facts(*, event_status: Mapping[str, Any], event_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    special = [fact for fact in event_facts if _event_fact_type(fact) in SPECIAL_RISK_EVENT_TYPES]
    for event_type in event_status.get("event_types") or ():
        normalized = str(event_type or "").upper()
        if normalized in SPECIAL_RISK_EVENT_TYPES:
            special.append(
                {
                    "event_type": normalized,
                    "event_status": event_status.get("event_status") or "KNOWN_EVENT",
                    "event_dates": list(event_status.get("event_dates") or []),
                    "source_ref": event_status.get("source_ref") or "corporate_event.symbol_event_facts",
                }
            )
    return special


def _event_fact_type(fact: Mapping[str, Any]) -> str:
    return str(
        fact.get("event_type")
        or fact.get("fact_type")
        or fact.get("type")
        or fact.get("category")
        or ""
    ).upper()


def _dimension(name: str, state: str, row: Mapping[str, Any], values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "state": state,
        "semantic_meaning": name,
        "evidence_sufficiency": "SUFFICIENT",
        "missing_inputs": [],
        "source_references": [_source_ref(row)],
        "as_of_date": str(row.get("business_date") or row.get("feature_date") or row.get("target_date") or ""),
        "values": dict(values),
    }


def _dimension_missing(name: str, row: Mapping[str, Any], missing: list[str]) -> dict[str, Any]:
    return {
        "state": "INSUFFICIENT",
        "semantic_meaning": name,
        "evidence_sufficiency": "INSUFFICIENT",
        "missing_inputs": missing,
        "source_references": [_source_ref(row)] if row else [],
        "as_of_date": str(row.get("business_date") or row.get("feature_date") or row.get("target_date") or ""),
        "values": {},
    }


def _eligibility_for_symbol(
    *,
    symbol: str,
    business_date: str,
    candidate: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    current: Mapping[str, Any],
    corporate_event: Mapping[str, Any],
    event_status: Mapping[str, Any],
) -> dict[str, Any]:
    del current
    facts: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    for row in (candidate, opportunity):
        reason = str(row.get("rejection_reason") or row.get("buy_ineligible_reason") or "")
        if reason:
            review.append({"fact_type": "UPSTREAM_ELIGIBILITY_REVIEW", "reason": reason, "source": _source_ref(row)})
    event_uncertainty = _event_uncertainty(corporate_event=corporate_event, event_status=event_status, business_date=business_date)
    if event_uncertainty["state"] == "EVENT_COVERAGE_INCOMPLETE":
        review.append({"fact_type": "EVENT_COVERAGE_INCOMPLETE", "reason": "missing_event_data_not_safe", "source": _source_ref(corporate_event)})
    elif event_uncertainty["state"] == "SPECIAL_RISK_PRESENT":
        review.append({"fact_type": "SPECIAL_RISK_PRESENT", "reason": "special_risk_event_requires_review", "source": _source_ref(corporate_event)})
    blocking_review = list(review)
    status = "PASS" if not facts and not blocking_review else "REVIEW_REQUIRED"
    return {
        "status": status,
        "symbol": symbol,
        "disqualifying_facts": facts,
        "review_required_facts": review,
        "known_data_gaps": ["complete_event_coverage_authority"]
        if event_uncertainty["state"] == "EVENT_COVERAGE_INCOMPLETE"
        else [],
        "probabilistic_risk_not_automatic_reject": True,
        "event_coverage_status": event_uncertainty.get("coverage_status"),
        "special_risk_authority": {
            "authority_type": event_uncertainty.get("authority_type"),
            "canonical_producer": event_uncertainty.get("canonical_producer"),
            "canonical_artifact": event_uncertainty.get("canonical_artifact"),
            "canonical_field": event_uncertainty.get("canonical_field"),
            "coverage_state": event_uncertainty.get("coverage_state"),
            "universe_coverage_state": event_uncertainty.get("universe_coverage_state"),
            "negative_evidence_safe_to_use": event_uncertainty.get("negative_evidence_safe_to_use"),
            "risk_state": event_uncertainty.get("risk_state"),
            "eligibility_implication": event_uncertainty.get("eligibility_implication"),
            "temporal_binding": event_uncertainty.get("temporal_binding"),
            "future_information_used": False,
        },
        "special_risk_coverage_state": event_uncertainty.get("coverage_state"),
        "special_risk_state": event_uncertainty.get("risk_state"),
        "special_risk_eligibility": event_uncertainty.get("eligibility_implication"),
        "missing_required_authorities": ["complete_event_coverage_authority"]
        if event_uncertainty["state"] == "EVENT_COVERAGE_INCOMPLETE"
        else [],
        "future_information_used": False,
    }


def _eligibility_event_facts(corporate_event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS" if corporate_event else "REVIEW_REQUIRED",
        "coverage_status": str(corporate_event.get("coverage_status") or corporate_event.get("overall_coverage_status") or "MISSING"),
        "source_coverage_semantics": str(corporate_event.get("source_coverage_semantics") or ""),
        "missing_event_data_is_safe": False,
        "disqualifying_fact_requires_authoritative_source": True,
        "source_reference": _source_ref(corporate_event) if corporate_event else {},
    }


def _current_decision(
    *,
    buy_quality: Mapping[str, Any],
    portfolio_construction: Mapping[str, Any],
    position_management: Mapping[str, Any],
    runtime_planning: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "buy_quality_action": buy_quality.get("quality_action"),
        "quality_band": buy_quality.get("quality_band"),
        "quality_reason_codes": buy_quality.get("reason_codes") or buy_quality.get("quality_reason_codes") or [],
        "portfolio_membership_intent": portfolio_construction.get("membership_intent"),
        "portfolio_weight_intent": portfolio_construction.get("weight_intent"),
        "semantic_buy_type": portfolio_construction.get("semantic_buy_type")
        or portfolio_construction.get("semantic_entry_type")
        or portfolio_construction.get("entry_type"),
        "portfolio_reason_codes": portfolio_construction.get("reason_codes") or portfolio_construction.get("quality_reason_codes") or [],
        "pm_action": position_management.get("action") or position_management.get("decision"),
        "pm_reason_codes": position_management.get("reason_codes") or position_management.get("pm_reason_codes") or [],
        "reduce_intensity": position_management.get("reduce_intensity"),
        "runtime_planning_action": runtime_planning.get("planning_intent") or runtime_planning.get("order_side_intent") or runtime_planning.get("action"),
        "order_side_intent": runtime_planning.get("order_side_intent"),
        "no_order_reason": runtime_planning.get("no_order_reason") or runtime_planning.get("reason"),
        "planned_quantity": runtime_planning.get("planned_quantity") or runtime_planning.get("quantity"),
        "current_decision_authority_unchanged": True,
    }


def _lifecycle_context(
    *,
    symbol: str,
    current: Mapping[str, Any],
    position_management: Mapping[str, Any],
    portfolio_construction: Mapping[str, Any],
    campaign: Mapping[str, Any],
    campaign_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    quantity = _optional_float(current.get("quantity"))
    market_value = _optional_float(current.get("market_value", current.get("value")))
    avg = _optional_float(current.get("average_price"))
    current_price = market_value / quantity if quantity and market_value is not None else _optional_float(current.get("reference_price") or current.get("price"))
    held = quantity is not None and quantity > 0
    canonical_campaign_available = bool(campaign_artifact)
    campaign_id = str(campaign.get("position_campaign_id") or "").strip()
    opened_date = str(campaign.get("opened_business_date") or campaign.get("campaign_opened_date") or "").strip()
    campaign_status = str(campaign.get("campaign_status") or "").strip()
    campaign_status_upper = campaign_status.upper()
    closed_date = str(campaign.get("closed_business_date") or campaign.get("campaign_closed_date") or "").strip()
    campaign_quantity = _optional_float(campaign.get("current_quantity"))
    quantity_basis = current.get("quantity_basis")
    valuation_price_basis = current.get("valuation_price_basis")
    missing_current = [
        name
        for name, value in (
            ("quantity", quantity),
            ("average_price", avg),
            ("current_market_value", market_value),
            ("quantity_basis", quantity_basis),
            ("valuation_price_basis", valuation_price_basis),
        )
        if value in (None, "")
    ]
    missing_campaign = []
    if held:
        if not campaign_id:
            missing_campaign.append("position_campaign_id")
        if not opened_date:
            missing_campaign.append("campaign_opened_date")
        if not campaign_status:
            missing_campaign.append("campaign_status")
        elif campaign_status_upper != "OPEN":
            missing_campaign.append("campaign_status_not_open")
        if campaign_quantity is not None and quantity is not None and abs(campaign_quantity - quantity) > 1e-9:
            missing_campaign.append("campaign_current_quantity_mismatch")
    if not held:
        authority_status = "NOT_APPLICABLE"
    elif not canonical_campaign_available:
        authority_status = "MISSING"
    elif not missing_current and not missing_campaign:
        authority_status = "COMPLETE"
    else:
        authority_status = "PARTIAL"
    history = _campaign_history_summary(campaign)
    return {
        "symbol": symbol,
        "current_position_state": "HELD" if held else "NO_POSITION",
        "semantic_position_state": "OPEN_HELD_POSITION" if held else "NO_POSITION",
        "position_campaign_id": campaign_id or None,
        "campaign_opened_date": opened_date or None,
        "campaign_closed_date": closed_date or None,
        "campaign_status": campaign_status or None,
        "current_position_authority_status": authority_status,
        "campaign_identity_authority_status": "COMPLETE" if held and campaign_id and opened_date and campaign_status and not missing_campaign else "MISSING" if held else "NOT_APPLICABLE",
        "current_authority_owner": "Runtime Current / PM current position adapter",
        "campaign_authority_owner": "positions/position_campaigns.json",
        "campaign_join_key": "symbol + active/open campaign state",
        "missing_current_authority_fields": missing_current,
        "missing_campaign_authority_fields": missing_campaign,
        "quantity": quantity,
        "current_quantity": quantity,
        "average_price": avg,
        "current_price": current_price,
        "market_value": market_value,
        "current_market_value": market_value,
        "quantity_basis": quantity_basis,
        "valuation_price_basis": valuation_price_basis,
        "campaign_age_business_days": _campaign_age_business_days(opened_date, str(campaign_artifact.get("business_date") or current.get("business_date") or current.get("feature_date") or "")),
        "current_campaign_relative_return": campaign.get("current_campaign_relative_return"),
        "observed_campaign_mfe": campaign.get("observed_campaign_mfe"),
        "observed_giveback": campaign.get("observed_giveback"),
        "add_history_summary": history["add_history_summary"],
        "reduce_history_summary": history["reduce_history_summary"],
        "sell_history_summary": history["sell_history_summary"],
        "buy_history_summary": history["buy_history_summary"],
        "prior_unrepresentable_reduce_summary": history["prior_unrepresentable_reduce_summary"],
        "pm_decision_history_summary": history["pm_decision_history_summary"],
        "entry_premise_snapshot": dict(campaign.get("entry_premise_snapshot") or {})
        if isinstance(campaign.get("entry_premise_snapshot"), Mapping)
        else {},
        "entry_premise_snapshot_status": str(campaign.get("entry_premise_snapshot_status") or ""),
        "campaign_source_reference": _source_ref(campaign_artifact) if campaign_artifact else {},
        "semantic_entry_type": portfolio_construction.get("semantic_entry_type")
        or portfolio_construction.get("semantic_buy_type")
        or portfolio_construction.get("entry_type"),
        "pm_action": position_management.get("action") or position_management.get("decision"),
    }


def _profit_protection_evidence(
    *,
    lifecycle_context: Mapping[str, Any],
    continuation_quality: Mapping[str, Any],
    downside_risk: Mapping[str, Any],
    current_decision: Mapping[str, Any],
) -> dict[str, Any]:
    held = lifecycle_context.get("current_position_state") == "HELD"
    avg = _optional_float(lifecycle_context.get("average_price"))
    current_price = _optional_float(lifecycle_context.get("current_price"))
    embedded_return = (current_price / avg - 1.0) if avg and current_price is not None else None
    observed_mfe = _optional_float(lifecycle_context.get("observed_campaign_mfe"))
    observed_giveback = _optional_float(lifecycle_context.get("observed_giveback"))
    cq_states = _collect_states(continuation_quality)
    risk_states = _collect_states(downside_risk)
    deterioration = sorted(cq_states & {"WEAK", "DECELERATING", "ELEVATED_RISK", "HIGH_RISK"})
    risk_rise = sorted(risk_states & {"ELEVATED_RISK", "HIGH_RISK"})
    pm_action = _canonical_action(current_decision.get("pm_action"))
    applicable = held or pm_action in {"REDUCE", "EXIT", "SELL_EXIT"}
    return {
        "status": "OBSERVED" if applicable and any(value is not None for value in (embedded_return, observed_mfe, observed_giveback)) else "NOT_APPLICABLE" if not applicable else "PARTIAL",
        "shadow_only": True,
        "not_action_authority": True,
        "current_pm_action": current_decision.get("pm_action"),
        "current_position_state": lifecycle_context.get("current_position_state"),
        "embedded_return_observed": embedded_return,
        "observed_campaign_mfe": observed_mfe,
        "observed_giveback": observed_giveback,
        "continuation_deterioration_connection": deterioration,
        "downside_risk_rise_connection": risk_rise,
        "profit_protection_interpretation": "PM_REDUCE_OR_EXIT_CONTEXT_OBSERVED"
        if pm_action in {"REDUCE", "EXIT", "SELL_EXIT"}
        else "HELD_POSITION_PROFIT_CONTEXT_OBSERVED"
        if applicable
        else "NO_HELD_PROFIT_CONTEXT",
        "fixed_profit_threshold_applied": False,
        "future_mfe_used": False,
        "future_peak_used": False,
        "future_information_used": False,
    }


def _entry_admission(
    *,
    symbol: str,
    business_date: str,
    eligibility: Mapping[str, Any],
    continuation_quality: Mapping[str, Any],
    downside_risk: Mapping[str, Any],
    expected_edge: Mapping[str, Any],
    lifecycle_context: Mapping[str, Any],
    current_decision: Mapping[str, Any],
) -> dict[str, Any]:
    current_action = _current_action_context(current_decision=current_decision, lifecycle_context=lifecycle_context)
    lifecycle_intent = "BUY_ADD" if current_action in {"ADD", "BUY_ADD"} else "REENTRY" if str(lifecycle_context.get("semantic_entry_type") or "").upper() == "REENTRY" else "BUY_NEW"
    held = lifecycle_context.get("current_position_state") == "HELD"
    cq_states = _named_states(continuation_quality)
    risk_states = _named_states(downside_risk)
    trend = cq_states.get("trend_health")
    persistence = cq_states.get("persistence")
    acceleration = cq_states.get("acceleration_state")
    exhaustion = cq_states.get("exhaustion_risk")
    participation = cq_states.get("participation_quality")
    relative = cq_states.get("relative_strength")
    regime = cq_states.get("regime_compatibility")
    reversal_risk = risk_states.get("reversal_risk")
    volatility_risk = risk_states.get("volatility_risk")
    participation_risk = risk_states.get("participation_risk")
    regime_risk = risk_states.get("regime_risk")

    reason_codes: list[str] = []
    evidence_sufficient = (
        eligibility.get("status") == "PASS"
        and continuation_quality.get("evidence_sufficiency") == "SUFFICIENT"
        and downside_risk.get("evidence_sufficiency") == "SUFFICIENT"
    )
    strong_medium = trend == "SUPPORTIVE" and persistence == "SUPPORTIVE"
    short_reversal = reversal_risk == "ELEVATED_RISK" or exhaustion == "ELEVATED_RISK"
    decelerating = acceleration == "DECELERATING"
    volatility_elevated = volatility_risk in {"ELEVATED_RISK", "HIGH_RISK"}
    risk_votes = sum(
        1
        for state in (reversal_risk, volatility_risk, exhaustion, participation_risk, regime_risk)
        if state in {"ELEVATED_RISK", "HIGH_RISK", "EVENT_COVERAGE_INCOMPLETE"}
    )

    if eligibility.get("status") != "PASS":
        entry_state = "INSUFFICIENT_ENTRY_EVIDENCE"
        action = "REVIEW_REQUIRED"
        reason_codes.append("entry_eligibility_not_pass")
    elif not evidence_sufficient:
        entry_state = "INSUFFICIENT_ENTRY_EVIDENCE"
        action = "NO_ADD" if held else "BUY_WAIT"
        reason_codes.append("entry_evidence_insufficient")
    elif strong_medium and short_reversal and decelerating and (volatility_elevated or risk_votes >= 2):
        entry_state = "OVERHEATED_DECELERATING_ENTRY"
        action = "NO_ADD" if held else "BUY_WAIT"
        reason_codes.append("strong_trend_short_reversal_decelerating_risk_interaction")
    elif short_reversal and decelerating and relative not in {"SUPPORTIVE", "MIXED"}:
        entry_state = "REVERSAL_RISK_ENTRY"
        action = "NO_ADD" if held else "BUY_WAIT"
        reason_codes.append("reversal_risk_entry_timing")
    elif risk_votes >= 2 or decelerating or short_reversal:
        entry_state = "CONTINUATION_WITH_CAUTION"
        action = "ADD_REDUCED_ONLY" if held else "BUY_NEW_REDUCED_ONLY"
        reason_codes.append("entry_continuation_with_caution")
    elif strong_medium and acceleration in {"ACCELERATING", "MIXED"} and participation in {"SUPPORTIVE", "MIXED"}:
        entry_state = "HEALTHY_CONTINUATION_ENTRY"
        action = "ADD_ALLOWED" if held else "BUY_NEW_ALLOWED"
        reason_codes.append("healthy_continuation_entry")
    else:
        entry_state = "CONTINUATION_WITH_CAUTION"
        action = "ADD_REDUCED_ONLY" if held else "BUY_NEW_REDUCED_ONLY"
        reason_codes.append("entry_mixed_continuation")

    return {
        "schema_version": "entry_admission.v1",
        "as_of_business_date": business_date,
        "symbol": symbol,
        "lifecycle_intent": lifecycle_intent,
        "entry_state": entry_state,
        "admission_action": action,
        "allocation_quality_bias": "FULL" if action in {"BUY_NEW_ALLOWED", "ADD_ALLOWED"} else "REDUCED" if action in {"BUY_NEW_REDUCED_ONLY", "ADD_REDUCED_ONLY"} else "NONE",
        "buy_wait_eligible": action == "BUY_WAIT",
        "evidence_sufficiency": "SUFFICIENT" if evidence_sufficient else "INSUFFICIENT",
        "reason_codes": sorted(set(reason_codes)),
        "consumed_evidence": {
            "eligibility_status": eligibility.get("status"),
            "continuation_quality_status": continuation_quality.get("status"),
            "downside_risk_status": downside_risk.get("status"),
            "expected_edge_calibration_status": expected_edge.get("calibration_status"),
            "trend_health": trend,
            "persistence": persistence,
            "acceleration_state": acceleration,
            "exhaustion_risk": exhaustion,
            "reversal_risk": reversal_risk,
            "volatility_risk": volatility_risk,
            "participation_quality": participation,
            "participation_risk": participation_risk,
            "relative_strength": relative,
            "regime_compatibility": regime,
            "regime_risk": regime_risk,
            "strong_medium_term_structure": strong_medium,
            "short_term_reversal": short_reversal,
            "risk_vote_count": risk_votes,
        },
        "non_pending_buy_wait": True,
        "next_pit_date_reevaluation_required": action == "BUY_WAIT",
        "sell_independent": True,
        "future_commitment": False,
        "not_action_authority": True,
        "shadow_only": True,
        "production_evidence": False,
        "future_information_used": False,
    }


def _selection_quality_comparator(
    *,
    symbol: str,
    business_date: str,
    candidate: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    technical: Mapping[str, Any],
    buy_quality: Mapping[str, Any],
    eligibility: Mapping[str, Any],
    continuation_quality: Mapping[str, Any],
    downside_risk: Mapping[str, Any],
    expected_edge: Mapping[str, Any],
    entry_admission: Mapping[str, Any],
    current_decision: Mapping[str, Any],
    market_context: Mapping[str, Any],
) -> dict[str, Any]:
    cq_states = _named_states(continuation_quality)
    risk_states = _named_states(downside_risk)
    entry_action = str(entry_admission.get("admission_action") or "").upper()
    entry_state = str(entry_admission.get("entry_state") or "").upper()
    buy_quality_action = str(buy_quality.get("quality_action") or current_decision.get("buy_quality_action") or "").upper()
    no_buy_reasons = _selection_no_buy_reasons(opportunity)
    reason_codes: list[str] = []

    eligibility_pass = str(eligibility.get("status") or "") == "PASS"
    cq_sufficient = str(continuation_quality.get("evidence_sufficiency") or "") == "SUFFICIENT"
    risk_sufficient = str(downside_risk.get("evidence_sufficiency") or "") == "SUFFICIENT"
    entry_sufficient = str(entry_admission.get("evidence_sufficiency") or "") == "SUFFICIENT"
    evidence_sufficient = eligibility_pass and cq_sufficient and risk_sufficient and entry_sufficient
    if not evidence_sufficient:
        reason_codes.append("selection_quality_evidence_insufficient")

    trend = cq_states.get("trend_health")
    persistence = cq_states.get("persistence")
    acceleration = cq_states.get("acceleration_state")
    participation = cq_states.get("participation_quality")
    relative = cq_states.get("relative_strength")
    regime = cq_states.get("regime_compatibility")
    reversal = risk_states.get("reversal_risk")
    volatility = risk_states.get("volatility_risk")
    exhaustion = risk_states.get("exhaustion_risk")
    participation_risk = risk_states.get("participation_risk")
    regime_risk = risk_states.get("regime_risk")
    hard_risk = "high_downside_risk_score" in no_buy_reasons or any(
        state == "HIGH_RISK" for state in (reversal, volatility, exhaustion, participation_risk, regime_risk)
    )
    risk_vote_count = sum(
        1
        for state in (reversal, volatility, exhaustion, participation_risk, regime_risk)
        if state in {"ELEVATED_RISK", "HIGH_RISK", "EVENT_COVERAGE_INCOMPLETE"}
    )
    supportive_count = sum(
        1
        for state in (trend, persistence, participation, relative, regime)
        if state in {"SUPPORTIVE", "OBSERVED", "MIXED"}
    )
    market_healthy_proxy = _market_healthy_proxy(technical=technical, market_context=market_context)
    raw_trend_supportive = (
        _optional_float(technical.get("price_momentum_return_5d")) is not None
        and _optional_float(technical.get("price_momentum_return_20d")) is not None
        and (_optional_float(technical.get("price_momentum_return_5d")) or 0.0) > 0.0
        and (_optional_float(technical.get("price_momentum_return_20d")) or 0.0) > 0.0
        and (_optional_float(technical.get("trend_close_over_ma_20d")) or 0.0) >= 1.0
        and (_optional_float(technical.get("trend_ma_5_20_ratio")) or 0.0) >= 1.0
    )

    if not eligibility_pass:
        tier = "REJECT"
        reason_codes.append("selection_quality_eligibility_not_pass")
    elif buy_quality_action in {"REJECT", "BUY_REJECTED"}:
        tier = "REJECT"
        reason_codes.append("selection_quality_buy_quality_reject")
    elif hard_risk:
        tier = "REJECT"
        reason_codes.append("selection_quality_hard_risk_block")
    elif not evidence_sufficient:
        tier = "INSUFFICIENT_QUALITY"
    elif entry_action in {"BUY_WAIT", "NO_ADD"} or entry_state in {"REVERSAL_RISK_ENTRY", "OVERHEATED_DECELERATING_ENTRY"}:
        tier = "CAUTION_CONTINUATION"
        reason_codes.append("selection_quality_entry_wait_or_no_add")
    elif entry_action in {"BUY_NEW_REDUCED_ONLY", "ADD_REDUCED_ONLY"} or risk_vote_count > 0:
        tier = "CAUTION_CONTINUATION"
        reason_codes.append("selection_quality_caution_continuation")
    elif (
        entry_action in {"BUY_NEW_ALLOWED", "ADD_ALLOWED"}
        and trend == "SUPPORTIVE"
        and persistence == "SUPPORTIVE"
        and acceleration in {"ACCELERATING", "MIXED"}
        and participation in {"SUPPORTIVE", "MIXED"}
        and relative in {"SUPPORTIVE", "MIXED", None}
        and raw_trend_supportive
        and risk_vote_count == 0
    ):
        tier = "HIGH_QUALITY_CONTINUATION"
        reason_codes.append("selection_quality_high_quality_continuation")
    elif entry_action in {"BUY_NEW_ALLOWED", "ADD_ALLOWED"} and supportive_count >= 3:
        tier = "VALID_CONTINUATION"
        reason_codes.append("selection_quality_valid_continuation")
    else:
        tier = "CAUTION_CONTINUATION"
        reason_codes.append("selection_quality_mixed_caution")

    if tier in {"HIGH_QUALITY_CONTINUATION", "VALID_CONTINUATION"} and no_buy_reasons & {
        "below_opportunity_top20",
        "non_positive_expected_edge_score",
    }:
        reason_codes.append("rank_score_only_hard_rejection_retired")

    runtime_score = _optional_float(opportunity.get("runtime_opportunity_score", opportunity.get("expected_edge_score")))
    rank = _optional_int(opportunity.get("buy_rank", opportunity.get("rank", opportunity.get("opportunity_rank"))))
    return {
        "schema_version": SELECTION_QUALITY_COMPARATOR_SCHEMA_VERSION,
        "as_of_business_date": business_date,
        "symbol": symbol,
        "tier": tier,
        "reason_codes": sorted(set(reason_codes)),
        "evidence_sufficiency": "SUFFICIENT" if evidence_sufficient else "INSUFFICIENT",
        "rank_score_role": "SUPPORTING_NOT_HARD_REJECTION_AUTHORITY",
        "expected_edge_role": "UNCALIBRATED_SUPPORTING",
        "buy_rank": rank,
        "runtime_opportunity_score": runtime_score,
        "expected_edge_calibration_status": str(expected_edge.get("calibration_status") or CALIBRATION_STATUS),
        "score_only_hard_rejection_retired": True,
        "below_top20_only_hard_rejection_retired": True,
        "market_healthy_proxy": market_healthy_proxy,
        "consumed_evidence": {
            "candidate_order": candidate.get("candidate_order"),
            "buy_rank": rank,
            "runtime_opportunity_score": runtime_score,
            "no_buy_reasons": sorted(no_buy_reasons),
            "entry_state": entry_state,
            "entry_action": entry_action,
            "buy_quality_action": buy_quality_action,
            "trend_health": trend,
            "persistence": persistence,
            "acceleration_state": acceleration,
            "participation_quality": participation,
            "relative_strength": relative,
            "regime_compatibility": regime,
            "reversal_risk": reversal,
            "volatility_risk": volatility,
            "exhaustion_risk": exhaustion,
            "participation_risk": participation_risk,
            "regime_risk": regime_risk,
            "risk_vote_count": risk_vote_count,
            "supportive_dimension_count": supportive_count,
            "raw_trend_supportive": raw_trend_supportive,
        },
        "not_action_authority": True,
        "shadow_only": True,
        "production_evidence": False,
        "future_information_used": False,
    }


def _selection_quality_summary(symbol_rows: list[dict[str, Any]], *, technical_feature_summary: Mapping[str, Any]) -> dict[str, Any]:
    distribution: Counter[str] = Counter()
    candidate_healthy_count = 0
    candidate_rows_with_comparator = 0
    for row in symbol_rows:
        comparator = row.get("selection_quality_comparator") if isinstance(row.get("selection_quality_comparator"), Mapping) else {}
        tier = str(comparator.get("tier") or "MISSING")
        distribution[tier] += 1
        if comparator:
            candidate_rows_with_comparator += 1
        if comparator.get("market_healthy_proxy"):
            candidate_healthy_count += 1
    technical_rows = technical_feature_summary.get("rows") if isinstance(technical_feature_summary.get("rows"), list) else []
    market_healthy_proxy_count = sum(
        1
        for row in technical_rows
        if isinstance(row, Mapping) and _market_healthy_proxy(technical=row, market_context={})
    )
    return {
        "schema_version": "selection_quality_comparator_summary.v1",
        "candidate_quality_tier_distribution": dict(sorted(distribution.items())),
        "candidate_rows_with_comparator": candidate_rows_with_comparator,
        "candidate_healthy_coverage_count": candidate_healthy_count,
        "market_healthy_proxy_count": market_healthy_proxy_count,
        "market_healthy_proxy_source": "technical_feature_summary.rows",
        "rank_score_role": "SUPPORTING_NOT_HARD_REJECTION_AUTHORITY",
        "expected_edge_status": CALIBRATION_STATUS,
        "future_information_used": False,
    }


def _selection_no_buy_reasons(opportunity: Mapping[str, Any]) -> set[str]:
    raw = opportunity.get("no_buy_reason", opportunity.get("no_buy_reasons", ""))
    if isinstance(raw, str):
        return {part.strip() for part in raw.replace(",", "|").split("|") if part.strip()}
    if isinstance(raw, list):
        return {str(part).strip() for part in raw if str(part).strip()}
    return set()


def _market_healthy_proxy(*, technical: Mapping[str, Any], market_context: Mapping[str, Any]) -> bool:
    del market_context
    r5 = _optional_float(technical.get("price_momentum_return_5d"))
    r20 = _optional_float(technical.get("price_momentum_return_20d"))
    close_ma20 = _optional_float(technical.get("trend_close_over_ma_20d"))
    ma5_ma20 = _optional_float(technical.get("trend_ma_5_20_ratio"))
    volume = _optional_float(technical.get("volume_momentum_ratio_5d"))
    return bool(
        r5 is not None
        and r20 is not None
        and close_ma20 is not None
        and ma5_ma20 is not None
        and r5 > 0.0
        and r20 > 0.0
        and close_ma20 >= 1.0
        and ma5_ma20 >= 1.0
        and (volume is None or volume >= 0.8)
    )


def _strategy_intelligence_interpretation(
    *,
    eligibility: Mapping[str, Any],
    continuation_quality: Mapping[str, Any],
    downside_risk: Mapping[str, Any],
    expected_edge: Mapping[str, Any],
    lifecycle_context: Mapping[str, Any],
    current_decision: Mapping[str, Any],
    profit_protection_evidence: Mapping[str, Any],
    entry_admission: Mapping[str, Any],
) -> dict[str, Any]:
    current_action = _current_action_context(current_decision=current_decision, lifecycle_context=lifecycle_context)
    held = lifecycle_context.get("current_position_state") == "HELD"
    cq_status = str(continuation_quality.get("status") or "")
    if current_action in {"REDUCE", "SELL_REDUCE"}:
        state = "PM_REDUCE_EVIDENCE_OBSERVED_SHADOW"
    elif current_action in {"EXIT", "SELL_EXIT"}:
        state = "PM_EXIT_EVIDENCE_OBSERVED_SHADOW"
    elif current_action in {"ADD", "BUY_ADD"}:
        state = "ADD_WORTHINESS_EVIDENCE_SHADOW" if cq_status == "PASS" else "ADD_WORTHINESS_REVIEW_SHADOW"
    elif current_action == "BUY_WAIT":
        state = "BUY_WAIT_CONTEXT_SHADOW"
    elif eligibility.get("status") != "PASS":
        state = "REVIEW_REQUIRED_SHADOW"
    elif str(lifecycle_context.get("semantic_entry_type") or "").upper() == "REENTRY" and current_action in {"BUY_NEW", "REENTRY"}:
        state = "REENTRY_EVIDENCE_SHADOW"
    elif held and cq_status == "PASS":
        state = "HOLD_WORTHINESS_OBSERVED_SHADOW"
    elif held:
        state = "HOLD_REVIEW_SHADOW"
    elif current_action in {"BUY_NEW", "BUY"} and cq_status == "PASS":
        state = "BUY_NEW_CANDIDATE_EVIDENCE_SHADOW"
    else:
        state = "INSUFFICIENT_EVIDENCE_SHADOW"
    return {
        "state": state,
        "interpretation_contract": "STRATEGY_INTELLIGENCE_INTERPRETATION_SHADOW",
        "shadow_only": True,
        "not_action_authority": True,
        "actual_behavior_changed": False,
        "current_action_preserved": True,
        "shared_intelligence_became_action_authority": False,
        "shadow_output_connected_to_production_action_authority": False,
        "lifecycle_context_type": current_action or lifecycle_context.get("current_position_state"),
        "reason_evidence": {
            "eligibility_status": eligibility.get("status"),
            "continuation_quality_status": continuation_quality.get("status"),
            "downside_risk_status": downside_risk.get("status"),
            "expected_edge_status": expected_edge.get("status"),
            "current_position_state": lifecycle_context.get("current_position_state"),
            "current_runtime_action": current_decision.get("runtime_planning_action"),
            "current_pm_action": current_decision.get("pm_action"),
            "current_buy_quality_action": current_decision.get("buy_quality_action"),
            "semantic_entry_type": lifecycle_context.get("semantic_entry_type"),
            "profit_protection_status": profit_protection_evidence.get("status"),
            "entry_state": entry_admission.get("entry_state"),
            "entry_admission_action": entry_admission.get("admission_action"),
        },
        "interpretation_summary": {
            "current_decision_observed": current_decision,
            "shared_intelligence_summary": {
                "eligibility_status": eligibility.get("status"),
                "continuation_quality_status": continuation_quality.get("status"),
                "downside_risk_status": downside_risk.get("status"),
                "expected_edge_calibration_status": expected_edge.get("calibration_status"),
            },
            "profit_protection_summary": profit_protection_evidence,
            "entry_admission_summary": entry_admission,
            "add_vs_hold_separation": current_action in {"ADD", "BUY_ADD"},
            "reduce_exit_authority_preservation": current_action in {"REDUCE", "SELL_REDUCE", "EXIT", "SELL_EXIT"},
        },
    }


def _current_action_context(*, current_decision: Mapping[str, Any], lifecycle_context: Mapping[str, Any]) -> str:
    for value in (
        current_decision.get("pm_action"),
        current_decision.get("runtime_planning_action"),
        current_decision.get("buy_quality_action"),
        current_decision.get("portfolio_membership_intent"),
        lifecycle_context.get("pm_action"),
        lifecycle_context.get("semantic_entry_type"),
    ):
        action = _canonical_action(value)
        if action:
            return action
    return ""


def _canonical_action(value: Any) -> str:
    action = str(value or "").upper()
    aliases = {
        "BUY_ADD": "ADD",
        "SELL_REDUCE": "REDUCE",
        "SELL_EXIT": "EXIT",
    }
    return aliases.get(action, action)


def _symbol_provenance(**items: Any) -> dict[str, Any]:
    refs: dict[str, Any] = {}
    for name, item in items.items():
        if isinstance(item, Mapping):
            refs[name] = _source_ref(item)
    return {
        "feature_refs": refs,
        "future_information_used": False,
        "historical_outcome_used_as_runtime_input": False,
    }


def _shadow_decision_comparison(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "comparison_available": True,
        "current_decision_count": len(rows),
        "strategy_intelligence_interpretation_count": len(rows),
        "actual_trading_behavior_changed": False,
        "shadow_output_connected_to_production_action_authority": False,
        "by_symbol": {
            str(row.get("symbol")): {
                "current_decision": row.get("current_decision"),
                "strategy_intelligence_interpretation": row.get("strategy_intelligence_interpretation"),
            }
            for row in rows
        },
    }


def _lineage_status(rows: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    dimensions = {
        "eligibility": "PASS",
        "continuation_quality": "PASS",
        "downside_risk": "PASS",
        "expected_edge": "PASS",
        "entry_admission": "PASS",
        "shadow_consumer": "PASS",
    }
    if not rows:
        return {name: {"status": "REVIEW_REQUIRED", "reason": "no_symbol_rows"} for name in dimensions}
    for row in rows:
        if (row.get("eligibility") or {}).get("status") != "PASS":
            dimensions["eligibility"] = "REVIEW_REQUIRED"
        if (row.get("continuation_quality") or {}).get("evidence_sufficiency") != "SUFFICIENT":
            dimensions["continuation_quality"] = "REVIEW_REQUIRED"
        if (row.get("downside_risk") or {}).get("evidence_sufficiency") != "SUFFICIENT":
            dimensions["downside_risk"] = "REVIEW_REQUIRED"
        if (row.get("expected_edge") or {}).get("calibration_status") != CALIBRATION_STATUS:
            dimensions["expected_edge"] = "REVIEW_REQUIRED"
        if (row.get("entry_admission") or {}).get("evidence_sufficiency") != "SUFFICIENT":
            dimensions["entry_admission"] = "REVIEW_REQUIRED"
    return {name: {"status": status, "path": "Source -> PIT -> Feature -> Artifact -> Shadow Consumer"} for name, status in dimensions.items()}


def _source_artifacts(*, business_date: str, paths: Mapping[str, Path | str | None], summaries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, path in paths.items():
        p = Path(path) if path else Path("")
        result[name] = {
            "path": str(path or ""),
            "sha256": _file_hash(p) if path else "",
            "required": name in {"runtime_planning", "portfolio_construction"},
            "status": "PASS" if path and p.is_file() else "MISSING",
        }
    for name, summary in summaries.items():
        result[name] = {
            "path": str(summary.get("source_ref") or ""),
            "sha256": str(summary.get("source_hash") or ""),
            "business_date": str(summary.get("business_date") or business_date),
            "feature_date": str(summary.get("feature_date") or ""),
            "status": str(summary.get("status") or ""),
        }
    return result


def _rows_by_symbol(summary: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = summary.get("rows") or ()
    return {_symbol(row): row for row in rows if isinstance(row, Mapping) and _symbol(row)}


def _rows_by_symbol_payload(payload: Mapping[str, Any], key: str) -> dict[str, Mapping[str, Any]]:
    rows = payload.get(key) or payload.get("rows") or payload.get("decisions") or payload.get("plans") or payload.get("positions") or []
    if not isinstance(rows, list):
        return {}
    return {_symbol(row): row for row in rows if isinstance(row, Mapping) and _symbol(row)}


def _symbol(row: Mapping[str, Any]) -> str:
    return str(row.get("security_code") or row.get("symbol") or row.get("code") or row.get("Code") or row.get("broker_issue_code") or "").strip()


def _event_status_by_symbol(corporate_event: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    facts = corporate_event.get("symbol_event_facts")
    if isinstance(facts, Mapping):
        return {str(symbol): item for symbol, item in facts.items() if isinstance(item, Mapping)}
    if isinstance(facts, list):
        return {
            _symbol(item): item
            for item in facts
            if isinstance(item, Mapping) and _symbol(item)
        }
    coverage = corporate_event.get("source_coverage")
    if isinstance(coverage, Mapping):
        return {str(symbol): item for symbol, item in coverage.items() if isinstance(item, Mapping)}
    return {}


def _current_or_same_day_closed_campaign_by_symbol(position_campaigns: Mapping[str, Any], *, business_date: str) -> dict[str, Mapping[str, Any]]:
    campaigns = position_campaigns.get("position_campaigns") if isinstance(position_campaigns.get("position_campaigns"), list) else []
    result: dict[str, Mapping[str, Any]] = {}
    same_day_closed: dict[str, Mapping[str, Any]] = {}
    conflicts: list[str] = []
    for campaign in campaigns:
        if not isinstance(campaign, Mapping):
            continue
        symbol = _symbol(campaign)
        if not symbol:
            continue
        status = str(campaign.get("campaign_status") or "").upper()
        quantity = _optional_float(campaign.get("current_quantity"))
        campaign_id = str(campaign.get("position_campaign_id") or "").strip()
        active = status == "OPEN" or (quantity is not None and quantity > 0)
        if not active:
            if status == "CLOSED" and _campaign_last_exit_date(campaign) == business_date:
                existing_closed = same_day_closed.get(symbol)
                if existing_closed and str(existing_closed.get("position_campaign_id") or "") != campaign_id:
                    conflicts.append(symbol)
                same_day_closed[symbol] = campaign
            continue
        existing = result.get(symbol)
        if existing and str(existing.get("position_campaign_id") or "") != campaign_id:
            conflicts.append(symbol)
        result[symbol] = campaign
    if conflicts:
        raise ValueError("CAMPAIGN_AUTHORITY_CONFLICT:" + ",".join(sorted(set(conflicts))))
    for symbol, campaign in same_day_closed.items():
        result.setdefault(symbol, campaign)
    return result


def _campaign_last_exit_date(campaign: Mapping[str, Any]) -> str:
    last = ""
    for event in campaign.get("events") or ():
        if not isinstance(event, Mapping):
            continue
        side = str(event.get("side") or "").upper()
        stage = str(event.get("stage") or "").upper()
        if side == "SELL" or stage in {"SELL", "REDUCE", "EXIT"}:
            last = str(event.get("business_date") or last)
    return last


def _campaign_history_summary(campaign: Mapping[str, Any]) -> dict[str, Any]:
    events = campaign.get("events") if isinstance(campaign.get("events"), list) else []
    counts: Counter[str] = Counter()
    first_buy = ""
    last_add = ""
    last_reduce = ""
    last_sell = ""
    for event in events:
        if not isinstance(event, Mapping):
            continue
        side = str(event.get("side") or event.get("stage") or "").upper()
        stage = str(event.get("stage") or "").upper()
        date = str(event.get("business_date") or "")
        key = "SELL" if side == "SELL" or stage in {"SELL", "REDUCE", "EXIT"} else "BUY" if side == "BUY" or stage in {"BUY", "ADD"} else stage
        if key:
            counts[key] += 1
        if stage in {"ADD", "REDUCE", "EXIT"}:
            counts[stage] += 1
        if key == "BUY" and not first_buy:
            first_buy = date
        if stage == "ADD" or (key == "BUY" and counts[key] > 1):
            last_add = date or last_add
        if stage == "REDUCE":
            last_reduce = date or last_reduce
        if key == "SELL":
            last_sell = date or last_sell
    decision_history = _pm_decision_history_summary(campaign)
    return {
        "buy_history_summary": {"event_count": counts.get("BUY", 0), "first_buy_date": first_buy or None},
        "add_history_summary": {"event_count": max(counts.get("BUY", 0) - 1, 0), "last_add_date": last_add or None},
        "reduce_history_summary": {"event_count": counts.get("REDUCE", 0), "last_reduce_date": last_reduce or None},
        "sell_history_summary": {"event_count": counts.get("SELL", 0), "last_sell_date": last_sell or None},
        "prior_unrepresentable_reduce_summary": decision_history["prior_unrepresentable_reduce_summary"],
        "pm_decision_history_summary": decision_history["pm_decision_history_summary"],
    }


def _pm_decision_history_summary(campaign: Mapping[str, Any]) -> dict[str, Any]:
    events = campaign.get("pm_decision_evidence_events") if isinstance(campaign.get("pm_decision_evidence_events"), list) else []
    ordered = sorted(
        (event for event in events if isinstance(event, Mapping)),
        key=lambda event: (
            str(event.get("business_date") or ""),
            str(event.get("event_kind") or ""),
            str(event.get("symbol") or ""),
        ),
    )
    active_reduce_dates: list[str] = []
    last_reduce = ""
    last_recovery_reset = ""
    for event in ordered:
        event_date = str(event.get("business_date") or "")
        kind = str(event.get("event_kind") or "").upper()
        recovery_policy = str(event.get("recovery_reset_policy") or "").upper()
        if kind == "RECOVERY_BOUNDARY" and recovery_policy in {"RESET", "DECAY"}:
            active_reduce_dates = []
            last_recovery_reset = event_date or last_recovery_reset
            continue
        if kind != "UNREPRESENTABLE_REDUCE_DECISION":
            continue
        if str(event.get("representability_family") or "").upper() != "DISCRETE_LOT":
            continue
        if bool(event.get("minimum_notional_flag")):
            continue
        try:
            final_reduce = float(event.get("final_reduce_quantity") or 0.0)
        except (TypeError, ValueError):
            final_reduce = 0.0
        if abs(final_reduce) > 1e-9:
            continue
        if event_date:
            active_reduce_dates.append(event_date)
            last_reduce = event_date
    return {
        "prior_unrepresentable_reduce_summary": {
            "schema_version": "phase31_f1i_prior_unrepresentable_reduce_summary.v1",
            "event_count": len(active_reduce_dates),
            "last_reduce_date": last_reduce or None,
            "prior_unrepresentable_reduce_dates": active_reduce_dates,
            "last_recovery_reset_date": last_recovery_reset or None,
            "minimum_notional_excluded": True,
            "decision_evidence_not_execution": True,
            "same_day_self_count_protected": True,
            "future_information_used": False,
        },
        "pm_decision_history_summary": {
            "schema_version": "phase31_f1i_pm_decision_history_summary.v1",
            "event_count": len(ordered),
            "unrepresentable_reduce_count_since_last_recovery": len(active_reduce_dates),
            "source_event_count": len(events),
            "decision_evidence_not_execution": True,
            "fake_execution_event_created": False,
            "future_information_used": False,
        },
    }


def _campaign_age_business_days(opened_date: str, business_date: str) -> int | None:
    if not opened_date or not business_date or opened_date > business_date:
        return None
    from datetime import date

    try:
        start = date.fromisoformat(opened_date[:10])
        end = date.fromisoformat(business_date[:10])
    except ValueError:
        return None
    return max((end - start).days, 0)


def _market_regime(market_context: Mapping[str, Any]) -> str:
    for path in (
        ("market_regime",),
        ("trend_regime",),
        ("regime",),
        ("regime_summary", "trend_regime"),
        ("metrics", "trend_regime"),
    ):
        value: Any = market_context
        for key in path:
            value = value.get(key) if isinstance(value, Mapping) else None
        if value:
            return str(value)
    return ""


def _payload_future_leakage(payload: Mapping[str, Any]) -> bool:
    temporal = payload.get("temporal_safety") if isinstance(payload.get("temporal_safety"), Mapping) else {}
    pit = payload.get("pit_validation") if isinstance(payload.get("pit_validation"), Mapping) else {}
    return bool(
        temporal.get("future_leakage_used")
        or temporal.get("future_rows_consumed")
        or pit.get("future_leakage_used")
        or pit.get("future_rows_consumed")
    )


def _minimum_feature_date(
    summaries: Mapping[str, Mapping[str, Any]],
    payloads: Mapping[str, Mapping[str, Any]],
    *,
    default: str,
) -> str:
    dates = []
    for item in list(summaries.values()) + list(payloads.values()):
        date = str(item.get("feature_date") or item.get("business_date") or "")
        if date:
            dates.append(date)
    return min(dates) if dates else default


def _collect_states(value: Any) -> set[str]:
    states: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "state":
                states.add(str(item))
            else:
                states |= _collect_states(item)
    elif isinstance(value, list):
        for item in value:
            states |= _collect_states(item)
    return states


def _named_states(value: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    if not isinstance(value, Mapping):
        return result
    for key, item in value.items():
        if isinstance(item, Mapping) and item.get("state") not in (None, ""):
            result[str(key)] = str(item.get("state"))
    return result


def _state_from_status(status: Any) -> str:
    return "OBSERVED" if str(status) == "PASS" else "PARTIAL"


def _source_ref(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": str(row.get("source_ref") or row.get("source_path") or row.get("source_artifact_path") or row.get("artifact_path") or ""),
        "hash": str(row.get("source_hash") or row.get("source_content_hash") or row.get("source_artifact_hash") or row.get("artifact_hash") or ""),
        "business_date": str(row.get("business_date") or ""),
        "feature_date": str(row.get("feature_date") or row.get("target_date") or ""),
    }


def _read_json(path: Path | str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed


def _validate_iso_date(value: str, *, field: str) -> None:
    import datetime as _dt

    try:
        _dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}_must_be_iso_date") from exc


def _validate_timestamp_like(value: str, *, field: str) -> None:
    if "T" not in value:
        raise ValueError(f"{field}_must_be_timestamp")
