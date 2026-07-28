from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.strategy.status_contract import numeric_resolution, status_contract_fields


SCHEMA_VERSION = "dynamic_cash_exposure.v1"
CONFIG_SCHEMA_VERSION = "dynamic_cash_exposure_config.v1"
PRODUCER_VERSION = "phase22_i_dynamic_cash_exposure_producer.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"

SOURCE_STATUSES_BLOCK = {"BLOCK", "MISSING", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
CASH_POSTURES = {"DEPLOY", "MAINTAIN", "RAISE", "MAXIMIZE_RESERVE", "UNRESOLVED"}
EXPOSURE_POSTURES = {"INCREASE", "MAINTAIN", "REDUCE", "MINIMIZE", "UNRESOLVED"}
CAPITAL_CONSTRAINT_STATUSES = {
    "SUFFICIENT",
    "CASH_CONSTRAINED",
    "EXPOSURE_CONSTRAINED",
    "OPPORTUNITY_CONSTRAINED",
    "POSITION_COUNT_CONSTRAINED",
    "UNCERTAINTY_CONSTRAINED",
    "SAFETY_CONSTRAINED",
    "SOURCE_UNAVAILABLE",
}


class DynamicCashExposureError(RuntimeError):
    pass


class DynamicCashExposureConfigError(DynamicCashExposureError):
    pass


class DynamicCashExposureSchemaError(DynamicCashExposureError):
    pass


class DynamicCashExposureConsumerError(DynamicCashExposureError):
    pass


@dataclass(frozen=True)
class CashExposureSourceSummary:
    status: str
    business_date: str
    feature_date: str
    source_ref: str
    source_hash: str
    summary: Mapping[str, Any]

    def to_dict(self, *, requested_business_date: str) -> dict[str, Any]:
        return {
            "status": self.status,
            "business_date": self.business_date,
            "feature_date": self.feature_date,
            "source_ref": self.source_ref,
            "source_hash": self.source_hash,
            "summary": dict(self.summary),
            "business_date_aligned": self.business_date == requested_business_date,
            "feature_date_lte_business_date": bool(self.feature_date and self.feature_date <= requested_business_date),
        }


@dataclass(frozen=True)
class DynamicCashExposureConfig:
    config_version: str
    config_source: str
    cash_policy: Mapping[str, float]
    exposure_policy: Mapping[str, float]
    regime_rules: Mapping[str, Mapping[str, float]]
    breadth_rules: Mapping[str, Mapping[str, float]]
    volatility_rules: Mapping[str, Mapping[str, float]]
    portfolio_policy_rules: Mapping[str, Mapping[str, Mapping[str, float]]]
    opportunity_capacity_rules: Mapping[str, Any]
    uncertainty_rules: Mapping[str, Mapping[str, float]]
    safety_references: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "config_version": self.config_version,
            "config_source": self.config_source,
            "cash_policy": dict(self.cash_policy),
            "exposure_policy": dict(self.exposure_policy),
            "regime_rules": {k: dict(v) for k, v in self.regime_rules.items()},
            "breadth_rules": {k: dict(v) for k, v in self.breadth_rules.items()},
            "volatility_rules": {k: dict(v) for k, v in self.volatility_rules.items()},
            "portfolio_policy_rules": {k: {kk: dict(vv) for kk, vv in v.items()} for k, v in self.portfolio_policy_rules.items()},
            "opportunity_capacity_rules": dict(self.opportunity_capacity_rules),
            "uncertainty_rules": {k: dict(v) for k, v in self.uncertainty_rules.items()},
            "safety_references": dict(self.safety_references),
        }


@dataclass(frozen=True)
class DynamicCashExposureProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "dynamic_cash_exposure" / business_date / "dynamic_cash_exposure.json"


def load_dynamic_cash_exposure_config(path: Path | str) -> DynamicCashExposureConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise DynamicCashExposureConfigError(f"dynamic cash exposure config missing: {config_path}")
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise DynamicCashExposureConfigError("unsupported dynamic cash exposure config")
    cash = _policy(payload, "cash_policy", ("minimum_cash_ratio", "baseline_target_cash_ratio", "maximum_cash_ratio"))
    exposure = _policy(payload, "exposure_policy", ("minimum_gross_exposure_ratio", "baseline_target_gross_exposure_ratio", "maximum_gross_exposure_ratio"))
    if not cash["minimum_cash_ratio"] <= cash["baseline_target_cash_ratio"] <= cash["maximum_cash_ratio"]:
        raise DynamicCashExposureConfigError("invalid cash policy hierarchy")
    if not exposure["minimum_gross_exposure_ratio"] <= exposure["baseline_target_gross_exposure_ratio"] <= exposure["maximum_gross_exposure_ratio"]:
        raise DynamicCashExposureConfigError("invalid exposure policy hierarchy")
    return DynamicCashExposureConfig(
        config_version=_text(payload, "config_version"),
        config_source=str(config_path),
        cash_policy=cash,
        exposure_policy=exposure,
        regime_rules=_rule_map(payload, "regime_rules"),
        breadth_rules=_rule_map(payload, "breadth_rules"),
        volatility_rules=_rule_map(payload, "volatility_rules"),
        portfolio_policy_rules=_nested_rule_map(payload, "portfolio_policy_rules"),
        opportunity_capacity_rules=dict(payload.get("opportunity_capacity_rules") or {}),
        uncertainty_rules=_rule_map(payload, "uncertainty_rules"),
        safety_references=dict(payload.get("safety_references") or {}),
    )


def produce_dynamic_cash_exposure_artifact(
    *,
    business_date: str,
    market_context_summary: CashExposureSourceSummary,
    portfolio_policy_summary: CashExposureSourceSummary,
    dynamic_position_count_summary: CashExposureSourceSummary,
    candidate_summary: CashExposureSourceSummary,
    opportunity_summary: CashExposureSourceSummary,
    current_cash_summary: CashExposureSourceSummary,
    current_exposure_summary: CashExposureSourceSummary,
    pending_reservation_summary: CashExposureSourceSummary,
    safety_limit_summary: CashExposureSourceSummary,
    config: DynamicCashExposureConfig | None,
    output_path: Path | str,
    as_of: str | None = None,
    expected_config_hash: str | None = None,
) -> DynamicCashExposureProducerResult:
    payload, evidence = build_dynamic_cash_exposure_payload(
        business_date=business_date,
        market_context_summary=market_context_summary,
        portfolio_policy_summary=portfolio_policy_summary,
        dynamic_position_count_summary=dynamic_position_count_summary,
        candidate_summary=candidate_summary,
        opportunity_summary=opportunity_summary,
        current_cash_summary=current_cash_summary,
        current_exposure_summary=current_exposure_summary,
        pending_reservation_summary=pending_reservation_summary,
        safety_limit_summary=safety_limit_summary,
        config=config,
        as_of=as_of,
        expected_config_hash=expected_config_hash,
    )
    validate_dynamic_cash_exposure_artifact(payload)
    artifact_hash = dynamic_cash_exposure_hash(payload)
    final = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final)
    return DynamicCashExposureProducerResult(final["producer_result_status"], ",".join(final.get("reason_codes") or []), str(path), artifact_hash, final, evidence)


def build_dynamic_cash_exposure_payload(
    *,
    business_date: str,
    market_context_summary: CashExposureSourceSummary,
    portfolio_policy_summary: CashExposureSourceSummary,
    dynamic_position_count_summary: CashExposureSourceSummary,
    candidate_summary: CashExposureSourceSummary,
    opportunity_summary: CashExposureSourceSummary,
    current_cash_summary: CashExposureSourceSummary,
    current_exposure_summary: CashExposureSourceSummary,
    pending_reservation_summary: CashExposureSourceSummary,
    safety_limit_summary: CashExposureSourceSummary,
    config: DynamicCashExposureConfig | None,
    as_of: str | None = None,
    expected_config_hash: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _date(business_date)
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _timestamp(as_of)
    summaries = {
        "market_context": market_context_summary,
        "portfolio_policy": portfolio_policy_summary,
        "dynamic_position_count": dynamic_position_count_summary,
        "candidate": candidate_summary,
        "opportunity": opportunity_summary,
        "current_cash": current_cash_summary,
        "current_exposure": current_exposure_summary,
        "pending_reservation": pending_reservation_summary,
        "safety_limit": safety_limit_summary,
    }
    status = "PASS"
    source_status = "VALID"
    reasons: list[str] = []
    for name, summary in summaries.items():
        if summary.business_date != business_date or not summary.feature_date or summary.feature_date > business_date:
            status = "BLOCK"
            reasons.append(f"{name}_date_mismatch")
        if summary.status in SOURCE_STATUSES_BLOCK:
            status = "BLOCK"
            source_status = "AUTHORITY_CONFLICT"
            reasons.append(f"{name}_block:{summary.status}")
        elif summary.status != "PASS" and status != "BLOCK":
            status = "REVIEW_REQUIRED"
            reasons.append(f"{name}_review_required:{summary.status}")
    config_hash = ""
    config_source_hash = ""
    config_payload = None
    if config is None:
        if status != "BLOCK":
            status = "REVIEW_REQUIRED"
        reasons.append("dynamic_cash_exposure_config_required")
    else:
        config_payload = config.to_dict()
        config_hash = stable_payload_hash(config_payload)
        config_source_hash = sha256_file(Path(config.config_source)) if Path(config.config_source).is_file() else config_hash
        if expected_config_hash and _strip_sha256(expected_config_hash) != config_hash:
            status = "BLOCK"
            source_status = "HASH_MISMATCH"
            reasons.append("dynamic_cash_exposure_config_hash_mismatch")
    safety_min_cash = _ratio(safety_limit_summary.summary.get("minimum_cash_ratio"), 0.0)
    safety_max_exposure = _ratio(safety_limit_summary.summary.get("maximum_gross_exposure_ratio"), 1.0)
    if safety_limit_summary.status != "PASS" and status != "BLOCK":
        status = "REVIEW_REQUIRED"
        reasons.append("safety_cash_exposure_limit_review_required")
    if safety_min_cash + safety_max_exposure > 1.0:
        status = "BLOCK"
        reasons.append("inconsistent_safety_cash_exposure_limits")

    unresolved_target = config is None or status != "PASS"
    if unresolved_target:
        minimum_cash = max(safety_min_cash, 0.0)
        target_cash = None
        maximum_cash = 0.0 if config is None else float(config.cash_policy["maximum_cash_ratio"])
        minimum_exposure = 0.0
        target_exposure = None
        maximum_exposure = min(safety_max_exposure, float(config.exposure_policy["maximum_gross_exposure_ratio"])) if config else safety_max_exposure
        cash_posture = "UNRESOLVED"
        exposure_posture = "UNRESOLVED"
        capital_status = "SOURCE_UNAVAILABLE" if status != "BLOCK" else "SOURCE_UNAVAILABLE"
        confidence = 0.0
        uncertainty = "UPSTREAM_REVIEW_REQUIRED" if status == "REVIEW_REQUIRED" else "BLOCKING_INPUT"
    else:
        decision = _decide(config, market_context_summary.summary, portfolio_policy_summary.summary, dynamic_position_count_summary.summary, opportunity_summary.summary, safety_min_cash, safety_max_exposure)
        minimum_cash = decision["minimum_cash_ratio"]
        target_cash = decision["target_cash_ratio"]
        maximum_cash = decision["maximum_cash_ratio"]
        minimum_exposure = decision["minimum_gross_exposure_ratio"]
        target_exposure = decision["target_gross_exposure_ratio"]
        maximum_exposure = decision["maximum_gross_exposure_ratio"]
        cash_posture = decision["cash_posture"]
        exposure_posture = decision["exposure_posture"]
        capital_status = decision["capital_constraint_status"]
        confidence = decision["confidence"]
        uncertainty = decision["uncertainty"]
        reasons.extend(decision["reason_codes"])
    if target_cash is not None and target_cash < safety_min_cash:
        status = "BLOCK"; reasons.append("target_cash_below_safety_minimum")
    if target_exposure is not None and target_exposure > safety_max_exposure:
        status = "BLOCK"; reasons.append("target_exposure_above_safety_maximum")

    current_cash = _amount(current_cash_summary.summary, "current_cash", "cash", "buying_power")
    current_market_value = _amount(current_exposure_summary.summary, "current_market_value", "gross_exposure", "market_value")
    pending_reserved_cash = _amount(pending_reservation_summary.summary, "pending_reserved_cash", "reserved_cash", "cash_required")
    pending_reserved_exposure = _amount(pending_reservation_summary.summary, "pending_reserved_exposure", "reserved_exposure", "target_notional")
    required_operational_reserve = round((current_cash + current_market_value) * safety_min_cash, 2)
    portfolio_total_equity = round(current_cash + current_market_value, 2)
    net_available_cash = round(max(current_cash - pending_reserved_cash - required_operational_reserve, 0.0), 2)
    target_cash_amount = None if target_cash is None else round(portfolio_total_equity * target_cash, 2)
    target_invested_notional = None if target_exposure is None else round(portfolio_total_equity * target_exposure, 2)
    current_invested_ratio = round(current_market_value / portfolio_total_equity, 6) if portfolio_total_equity > 0 else 0.0
    incremental_deployment_capacity = None if target_invested_notional is None else round(max(target_invested_notional - current_market_value - pending_reserved_exposure, 0.0), 2)
    if pending_reserved_cash and pending_reserved_exposure and abs(pending_reserved_cash - pending_reserved_exposure) > 0.01:
        if status != "BLOCK":
            status = "REVIEW_REQUIRED"
        reasons.append("pending_cash_and_exposure_reservation_differ_review_required")

    feature_date = min([s.feature_date for s in summaries.values() if s.feature_date] or [business_date])
    future = any(s.feature_date and s.feature_date > business_date for s in summaries.values())
    source_hashes = [{"role": name, "path": s.source_ref, "sha256": _strip_sha256(s.source_hash)} for name, s in summaries.items()]
    if config:
        source_hashes.append({"role": "dynamic_cash_exposure_config", "path": config.config_source, "sha256": config_source_hash})
    payload = {
        "schema_version": SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "business_date": business_date,
        "as_of": as_of,
        "feature_date": feature_date,
        "artifact_lifecycle_status": ARTIFACT_LIFECYCLE_STATUS,
        "source_authority_status": source_status,
        "producer_result_status": "BLOCK" if future else status,
        "runtime_consumer_eligibility": RUNTIME_CONSUMER_ELIGIBILITY,
        **status_contract_fields(
            producer_result_status="BLOCK" if future else status,
            artifact_lifecycle_status=ARTIFACT_LIFECYCLE_STATUS,
            runtime_consumer_eligibility=RUNTIME_CONSUMER_ELIGIBILITY,
            reason_codes=sorted(set([*reasons, *(["future_source_date_detected"] if future else [])])),
            decision_resolution=numeric_resolution(target_exposure, unresolved=target_exposure is None),
        ),
        "target_cash_ratio_resolution": numeric_resolution(target_cash, unresolved=target_cash is None),
        "target_gross_exposure_ratio_resolution": numeric_resolution(target_exposure, unresolved=target_exposure is None),
        "minimum_cash_ratio": round(minimum_cash, 6),
        "target_cash_ratio": None if target_cash is None else round(target_cash, 6),
        "maximum_cash_ratio": round(maximum_cash, 6),
        "minimum_gross_exposure_ratio": round(minimum_exposure, 6),
        "target_gross_exposure_ratio": None if target_exposure is None else round(target_exposure, 6),
        "maximum_gross_exposure_ratio": round(maximum_exposure, 6),
        "portfolio_total_equity": portfolio_total_equity,
        "current_cash": round(current_cash, 2),
        "current_market_value": round(current_market_value, 2),
        "pending_reserved_cash": round(pending_reserved_cash, 2),
        "pending_reserved_exposure": round(pending_reserved_exposure, 2),
        "required_operational_reserve": required_operational_reserve,
        "net_available_cash": net_available_cash,
        "target_cash_amount": target_cash_amount,
        "target_invested_ratio": None if target_exposure is None else round(target_exposure, 6),
        "target_invested_notional": target_invested_notional,
        "current_invested_ratio": current_invested_ratio,
        "incremental_deployment_capacity": incremental_deployment_capacity,
        "source_as_of": as_of,
        "strategy_fixed_jpy_exposure_cap_used": False,
        "legacy_max_exposure_authority_used": False,
        "pending_deduction_count": 1 if pending_reserved_cash or pending_reserved_exposure else 0,
        "current_cash_ratio": _ratio(current_cash_summary.summary.get("current_cash_ratio"), 0.0),
        "current_gross_exposure_ratio": _ratio(current_exposure_summary.summary.get("current_gross_exposure_ratio"), current_invested_ratio),
        "cash_posture": cash_posture,
        "exposure_posture": exposure_posture,
        "capital_constraint_status": capital_status,
        "dynamic_position_count_reference": dynamic_position_count_summary.source_ref,
        "market_context_reference": market_context_summary.source_ref,
        "portfolio_policy_reference": portfolio_policy_summary.source_ref,
        "safety_limit_reference": safety_limit_summary.source_ref,
        "config_reference": config.config_source if config else "",
        "config_hash": f"sha256:{config_hash}" if config_hash else "",
        "config_payload": config_payload,
        "cash_safety_minimum": safety_min_cash,
        "exposure_safety_maximum": safety_max_exposure,
        "implied_average_position_exposure": _implied_average(target_exposure, dynamic_position_count_summary.summary.get("target_position_count")),
        "confidence": confidence,
        "uncertainty": uncertainty,
        "reason_codes": sorted(set([*reasons, *(["future_source_date_detected"] if future else [])])),
        "upstream_artifacts": {name: s.to_dict(requested_business_date=business_date) for name, s in summaries.items()},
        "source_artifacts": [{"role": name, "path": s.source_ref, "required": True, "status": s.status} for name, s in summaries.items()],
        "source_hashes": source_hashes,
        "temporal_safety": {"point_in_time": not future, "future_leakage_used": future, "feature_date_lte_business_date": feature_date <= business_date, "implicit_latest_fallback_used": False, "previous_day_dynamic_cash_exposure_copied": False},
        "shadow_comparison": {"legacy_target_investment_ratio": 0.85, "legacy_cash_buffer": 0.05, "legacy_max_exposure": 850000, "legacy_max_exposure_authority_used": False, "dynamic_target_cash_ratio": None if target_cash is None else round(target_cash, 6), "dynamic_target_gross_exposure_ratio": None if target_exposure is None else round(target_exposure, 6), "dynamic_target_invested_notional": target_invested_notional, "runtime_behavior_changed": False},
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "lot_rounding_decided": False,
    }
    return payload, {"schema_version": "phase22_i_dynamic_cash_exposure_evidence.v1", "producer_result_status": payload["producer_result_status"], "reason_codes": payload["reason_codes"]}


def validate_dynamic_cash_exposure_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    required = {"schema_version","business_date","as_of","feature_date","artifact_lifecycle_status","source_authority_status","producer_result_status","runtime_consumer_eligibility","minimum_cash_ratio","target_cash_ratio","maximum_cash_ratio","minimum_gross_exposure_ratio","target_gross_exposure_ratio","maximum_gross_exposure_ratio","portfolio_total_equity","current_cash","current_market_value","pending_reserved_cash","net_available_cash","target_cash_amount","target_invested_ratio","target_invested_notional","current_invested_ratio","incremental_deployment_capacity","strategy_fixed_jpy_exposure_cap_used","legacy_max_exposure_authority_used","current_cash_ratio","current_gross_exposure_ratio","cash_posture","exposure_posture","capital_constraint_status","confidence","uncertainty","reason_codes","source_artifacts","source_hashes","temporal_safety"}
    errors = [f"required_field_missing:{f}" for f in sorted(required - set(payload))]
    if payload.get("schema_version") != SCHEMA_VERSION: errors.append("unsupported_schema_version")
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS: errors.append("artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY: errors.append("runtime_consumer_eligibility_must_be_not_eligible")
    target_unresolved = payload.get("target_gross_exposure_ratio_resolution") == "UNRESOLVED"
    cash = [
        None if target_unresolved and f == "target_cash_ratio" and payload.get(f) is None else _ratio_field(errors, payload, f)
        for f in ("minimum_cash_ratio","target_cash_ratio","maximum_cash_ratio")
    ]
    exp = [
        None if target_unresolved and f == "target_gross_exposure_ratio" and payload.get(f) is None else _ratio_field(errors, payload, f)
        for f in ("minimum_gross_exposure_ratio","target_gross_exposure_ratio","maximum_gross_exposure_ratio")
    ]
    if all(v is not None for v in cash) and not cash[0] <= cash[1] <= cash[2]: errors.append("invalid_cash_ratio_hierarchy")
    if all(v is not None for v in exp) and not exp[0] <= exp[1] <= exp[2]: errors.append("invalid_exposure_ratio_hierarchy")
    if payload.get("cash_posture") not in CASH_POSTURES: errors.append("invalid_cash_posture")
    if payload.get("exposure_posture") not in EXPOSURE_POSTURES: errors.append("invalid_exposure_posture")
    if payload.get("capital_constraint_status") not in CAPITAL_CONSTRAINT_STATUSES: errors.append("invalid_capital_constraint_status")
    total_equity = _amount(payload, "portfolio_total_equity")
    target_invested_ratio = None if target_unresolved and payload.get("target_invested_ratio") is None else _ratio_field(errors, payload, "target_invested_ratio")
    target_notional = payload.get("target_invested_notional")
    if target_unresolved and target_notional is None:
        pass
    elif isinstance(target_notional, bool) or not isinstance(target_notional, (int, float)):
        errors.append("invalid_amount:target_invested_notional")
    elif target_invested_ratio is not None and abs(round(total_equity * target_invested_ratio, 2) - float(target_notional)) > 0.01:
        errors.append("target_invested_ratio_notional_mismatch")
    if payload.get("strategy_fixed_jpy_exposure_cap_used") is not False:
        errors.append("strategy_fixed_jpy_exposure_cap_must_not_be_used")
    if payload.get("legacy_max_exposure_authority_used") is not False:
        errors.append("legacy_max_exposure_authority_must_not_be_used")
    temporal = payload.get("temporal_safety") if isinstance(payload.get("temporal_safety"), dict) else {}
    if temporal.get("implicit_latest_fallback_used") is not False: errors.append("implicit_latest_fallback_forbidden")
    if temporal.get("previous_day_dynamic_cash_exposure_copied") is not False: errors.append("previous_day_copy_forbidden")
    if payload.get("production_consumer_connected") is not False or payload.get("runtime_switch_performed") is not False: errors.append("runtime_connection_forbidden")
    for field in ("position_sizing_decided","allocation_decided","quantity_decided","lot_rounding_decided"):
        if payload.get(field) is not False: errors.append(f"{field}_must_be_false")
    if errors:
        raise DynamicCashExposureSchemaError(";".join(errors))
    return {"status": "PASS", "errors": []}


def verify_source_hashes(payload: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    for item in payload.get("source_hashes") or []:
        path = Path(str(item.get("path") or ""))
        if path.is_file() and sha256_file(path) != _strip_sha256(str(item.get("sha256") or "")):
            mismatches.append(str(path))
    return {"status": "BLOCK" if mismatches else "PASS", "mismatches": mismatches}


def load_dynamic_cash_exposure_fixture(path: Path | str, *, for_production: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_dynamic_cash_exposure_artifact(payload)
    if for_production:
        raise DynamicCashExposureConsumerError("Phase22-I Dynamic Cash Exposure is not production-consumable")
    return payload


def dynamic_cash_exposure_hash(payload: dict[str, Any]) -> str:
    return stable_payload_hash({k: v for k, v in payload.items() if k != "artifact_hash"})


def stable_payload_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _decide(config: DynamicCashExposureConfig, market: Mapping[str, Any], policy: Mapping[str, Any], count: Mapping[str, Any], opportunity: Mapping[str, Any], safety_min_cash: float, safety_max_exposure: float) -> dict[str, Any]:
    cash = float(config.cash_policy["baseline_target_cash_ratio"])
    exposure = float(config.exposure_policy["baseline_target_gross_exposure_ratio"])
    reasons = []
    for rules, key in ((config.regime_rules, str(market.get("trend_regime") or "RANGE")), (config.breadth_rules, str(market.get("market_breadth") or "NEUTRAL")), (config.volatility_rules, str(market.get("volatility_regime") or "NORMAL"))):
        rule = rules.get(key) or {"cash_delta": 0, "exposure_delta": 0}
        cash += float(rule.get("cash_delta", 0)); exposure += float(rule.get("exposure_delta", 0)); reasons.append(key)
    risk = str(policy.get("risk_posture") or "BALANCED")
    rule = (config.portfolio_policy_rules.get("risk_posture") or {}).get(risk) or {"cash_delta": 0, "exposure_delta": 0}
    cash += float(rule.get("cash_delta", 0)); exposure += float(rule.get("exposure_delta", 0))
    uncertainty = str(market.get("uncertainty") or policy.get("uncertainty") or "LOW")
    rule = config.uncertainty_rules.get(uncertainty) or config.uncertainty_rules.get("MEDIUM", {})
    cash += float(rule.get("cash_delta", 0)); exposure += float(rule.get("exposure_delta", 0))
    if int(opportunity.get("available_opportunity_count") or opportunity.get("valid_opportunity_count") or 0) < int(config.opportunity_capacity_rules.get("low_opportunity_count_threshold") or 0):
        cash += float(config.opportunity_capacity_rules.get("low_opportunity_cash_delta") or 0)
        exposure += float(config.opportunity_capacity_rules.get("low_opportunity_exposure_delta") or 0)
        reasons.append("low_opportunity_capacity")
    min_cash = max(float(config.cash_policy["minimum_cash_ratio"]), safety_min_cash)
    max_cash = float(config.cash_policy["maximum_cash_ratio"])
    min_exp = float(config.exposure_policy["minimum_gross_exposure_ratio"])
    max_exp = min(float(config.exposure_policy["maximum_gross_exposure_ratio"]), safety_max_exposure)
    cash = max(min_cash, min(cash, max_cash))
    exposure = max(min_exp, min(exposure, max_exp))
    balanced_cash = float(config.cash_policy["baseline_target_cash_ratio"])
    balanced_exp = float(config.exposure_policy["baseline_target_gross_exposure_ratio"])
    return {
        "minimum_cash_ratio": min_cash, "target_cash_ratio": cash, "maximum_cash_ratio": max_cash,
        "minimum_gross_exposure_ratio": min_exp, "target_gross_exposure_ratio": exposure, "maximum_gross_exposure_ratio": max_exp,
        "cash_posture": "DEPLOY" if cash < balanced_cash else ("RAISE" if cash > balanced_cash else "MAINTAIN"),
        "exposure_posture": "INCREASE" if exposure > balanced_exp else ("REDUCE" if exposure < balanced_exp else "MAINTAIN"),
        "capital_constraint_status": "UNCERTAINTY_CONSTRAINED" if uncertainty in {"HIGH","UPSTREAM_REVIEW_REQUIRED"} else "SUFFICIENT",
        "confidence": min(_ratio(market.get("confidence"), 1.0), _ratio(policy.get("confidence"), 1.0), _ratio(count.get("confidence"), 1.0)),
        "uncertainty": uncertainty,
        "reason_codes": reasons,
    }


def _implied_average(exposure: float | None, count: Any) -> float | None:
    if exposure is None:
        return None
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        return None
    return round(exposure / count, 6)


def _policy(payload: Mapping[str, Any], key: str, fields: tuple[str, ...]) -> dict[str, float]:
    obj = payload.get(key)
    if not isinstance(obj, dict): raise DynamicCashExposureConfigError(f"{key} required")
    return {f: _ratio(obj.get(f), None) for f in fields}


def _rule_map(payload: Mapping[str, Any], key: str) -> dict[str, dict[str, float]]:
    obj = payload.get(key)
    if not isinstance(obj, dict): raise DynamicCashExposureConfigError(f"{key} required")
    return {str(k): {"cash_delta": float(v.get("cash_delta", 0)), "exposure_delta": float(v.get("exposure_delta", 0))} for k, v in obj.items() if isinstance(v, dict)}


def _nested_rule_map(payload: Mapping[str, Any], key: str) -> dict[str, dict[str, dict[str, float]]]:
    obj = payload.get(key)
    if not isinstance(obj, dict): raise DynamicCashExposureConfigError(f"{key} required")
    return {str(k): _rule_map({k: v}, k) for k, v in obj.items() if isinstance(v, dict)}


def _ratio(value: Any, default: float | None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if default is None: raise DynamicCashExposureConfigError("ratio required")
        return default
    if not 0 <= float(value) <= 1:
        raise DynamicCashExposureConfigError("ratio out of range")
    return float(value)


def _amount(payload: Mapping[str, Any], *fields: str) -> float:
    for field in fields:
        value = payload.get(field)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return max(float(value), 0.0)
    rows = payload.get("rows")
    if isinstance(rows, list):
        return sum(_amount(row, *fields) for row in rows if isinstance(row, Mapping))
    return 0.0


def _ratio_field(errors: list[str], payload: dict[str, Any], field: str) -> float | None:
    try: return _ratio(payload.get(field), None)
    except Exception: errors.append(f"invalid_ratio:{field}"); return None


def _text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value: raise DynamicCashExposureConfigError(f"{field} required")
    return value


def _date(value: str) -> None:
    if date.fromisoformat(value).isoformat() != value: raise ValueError("invalid date")


def _timestamp(value: str) -> None:
    if datetime.fromisoformat(value.replace("Z","+00:00")).tzinfo is None: raise ValueError("timestamp timezone required")


def _strip_sha256(value: str) -> str:
    return value[7:] if value.startswith("sha256:") else value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
