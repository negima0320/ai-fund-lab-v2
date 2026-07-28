from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.strategy.status_contract import numeric_resolution, status_contract_fields


SCHEMA_VERSION = "position_sizing.v1"
CONFIG_SCHEMA_VERSION = "position_sizing_config.v1"
PRODUCER_VERSION = "phase22_j_position_sizing_producer.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"

SOURCE_STATUSES_BLOCK = {"BLOCK", "MISSING", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
SIZING_STATUSES = {
    "SIZED",
    "CAPPED",
    "MINIMUM_NOTIONAL_UNMET",
    "VOLATILITY_UNAVAILABLE",
    "QUALITY_UNAVAILABLE",
    "UPSTREAM_REVIEW_REQUIRED",
    "SAFETY_CONSTRAINED",
    "WITHHELD",
    "UNRESOLVED",
}
PM_ACTIONS = {"NEW", "HOLD", "ADD", "REDUCE", "EXIT", "UNRESOLVED"}
MEMBERSHIP_INTENTS = {"RETAIN", "ADD_CANDIDATE", "REDUCE_CANDIDATE", "REMOVE_CANDIDATE", "EXCLUDE", "UNRESOLVED"}
FORBIDDEN_FIELDS = {"share_quantity", "quantity", "quantity_candidate", "broker_quantity", "order_quantity", "lot_size", "round_lot", "lot_rounding_result", "pending_id", "submit_command"}


class PositionSizingError(RuntimeError):
    pass


class PositionSizingConfigError(PositionSizingError):
    pass


class PositionSizingSchemaError(PositionSizingError):
    pass


class PositionSizingConsumerError(PositionSizingError):
    pass


@dataclass(frozen=True)
class PositionSizingSourceSummary:
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


@dataclass(frozen=True)
class PositionSizingConfig:
    config_version: str
    config_source: str
    sizing_method: str
    opportunity_adjustment: Mapping[str, float]
    volatility_adjustment: Mapping[str, Any]
    pm_intent_adjustment: Mapping[str, float]
    minimum_meaningful_notional: Mapping[str, Any]
    strategy_maximum_position_weight: float
    safety_concentration_reference: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "config_version": self.config_version,
            "config_source": self.config_source,
            "sizing_method": self.sizing_method,
            "opportunity_adjustment": dict(self.opportunity_adjustment),
            "volatility_adjustment": dict(self.volatility_adjustment),
            "pm_intent_adjustment": dict(self.pm_intent_adjustment),
            "minimum_meaningful_notional": dict(self.minimum_meaningful_notional),
            "strategy_maximum_position_weight": self.strategy_maximum_position_weight,
            "safety_concentration_reference": self.safety_concentration_reference,
        }


@dataclass(frozen=True)
class PositionSizingProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "position_sizing" / business_date / "position_sizing.json"


def load_position_sizing_config(path: Path | str) -> PositionSizingConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise PositionSizingConfigError(f"position sizing config missing: {config_path}")
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise PositionSizingConfigError("unsupported position sizing config")
    strategy_cap = _ratio(payload.get("strategy_maximum_position_weight"), None)
    if strategy_cap == 0.20:
        raise PositionSizingConfigError("legacy max_position_weight=0.20 must not be reused as Strategy sizing cap")
    if strategy_cap <= 0:
        raise PositionSizingConfigError("strategy maximum position weight must be positive")
    return PositionSizingConfig(
        config_version=_text(payload, "config_version"),
        config_source=str(config_path),
        sizing_method=_text(payload, "sizing_method"),
        opportunity_adjustment=_numeric_mapping(payload, "opportunity_adjustment"),
        volatility_adjustment=dict(payload.get("volatility_adjustment") or {}),
        pm_intent_adjustment=_numeric_mapping(payload, "pm_intent_adjustment"),
        minimum_meaningful_notional=dict(payload.get("minimum_meaningful_notional") or {}),
        strategy_maximum_position_weight=strategy_cap,
        safety_concentration_reference=_text(payload, "safety_concentration_reference"),
    )


def produce_position_sizing_artifact(
    *,
    business_date: str,
    portfolio_construction_summary: PositionSizingSourceSummary,
    capital_deployment_summary: PositionSizingSourceSummary,
    dynamic_position_count_summary: PositionSizingSourceSummary,
    dynamic_cash_exposure_summary: PositionSizingSourceSummary,
    position_management_summary: PositionSizingSourceSummary,
    opportunity_summary: PositionSizingSourceSummary,
    current_position_summary: PositionSizingSourceSummary,
    price_volatility_summary: PositionSizingSourceSummary,
    safety_limit_summary: PositionSizingSourceSummary,
    config: PositionSizingConfig | None,
    output_path: Path | str,
    as_of: str | None = None,
    expected_config_hash: str | None = None,
) -> PositionSizingProducerResult:
    payload, evidence = build_position_sizing_payload(
        business_date=business_date,
        portfolio_construction_summary=portfolio_construction_summary,
        capital_deployment_summary=capital_deployment_summary,
        dynamic_position_count_summary=dynamic_position_count_summary,
        dynamic_cash_exposure_summary=dynamic_cash_exposure_summary,
        position_management_summary=position_management_summary,
        opportunity_summary=opportunity_summary,
        current_position_summary=current_position_summary,
        price_volatility_summary=price_volatility_summary,
        safety_limit_summary=safety_limit_summary,
        config=config,
        as_of=as_of,
        expected_config_hash=expected_config_hash,
    )
    validate_position_sizing_artifact(payload)
    artifact_hash = position_sizing_hash(payload)
    final = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final)
    return PositionSizingProducerResult(final["producer_result_status"], ",".join(final.get("reason_codes") or []), str(path), artifact_hash, final, evidence)


def build_position_sizing_payload(
    *,
    business_date: str,
    portfolio_construction_summary: PositionSizingSourceSummary,
    capital_deployment_summary: PositionSizingSourceSummary,
    dynamic_position_count_summary: PositionSizingSourceSummary,
    dynamic_cash_exposure_summary: PositionSizingSourceSummary,
    position_management_summary: PositionSizingSourceSummary,
    opportunity_summary: PositionSizingSourceSummary,
    current_position_summary: PositionSizingSourceSummary,
    price_volatility_summary: PositionSizingSourceSummary,
    safety_limit_summary: PositionSizingSourceSummary,
    config: PositionSizingConfig | None,
    as_of: str | None = None,
    expected_config_hash: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _date(business_date)
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _timestamp(as_of)
    summaries = {
        "portfolio_construction": portfolio_construction_summary,
        "capital_deployment": capital_deployment_summary,
        "dynamic_position_count": dynamic_position_count_summary,
        "dynamic_cash_exposure": dynamic_cash_exposure_summary,
        "position_management": position_management_summary,
        "opportunity": opportunity_summary,
        "current_position": current_position_summary,
        "price_volatility": price_volatility_summary,
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
        reasons.append("position_sizing_config_required")
    else:
        config_payload = config.to_dict()
        config_hash = stable_payload_hash(config_payload)
        config_source_hash = sha256_file(Path(config.config_source)) if Path(config.config_source).is_file() else config_hash
        if expected_config_hash and _strip_sha256(expected_config_hash) != config_hash:
            status = "BLOCK"
            source_status = "HASH_MISMATCH"
            reasons.append("position_sizing_config_hash_mismatch")

    target_count_raw = dynamic_position_count_summary.summary.get("target_position_count")
    target_exposure_raw = dynamic_cash_exposure_summary.summary.get("target_gross_exposure_ratio")
    target_count_unresolved = target_count_raw is None
    target_exposure_unresolved = target_exposure_raw is None
    target_count = None if target_count_unresolved else _positive_int(target_count_raw, 0)
    target_exposure = None if target_exposure_unresolved else _ratio(target_exposure_raw, 0.0)
    if (target_count_unresolved or target_exposure_unresolved) and status != "BLOCK":
        status = "REVIEW_REQUIRED"
        reasons.append("position_count_or_exposure_unresolved")
    portfolio_value = _positive_float(
        current_position_summary.summary.get("portfolio_total_equity", current_position_summary.summary.get("portfolio_value")),
        0.0,
    )
    if portfolio_value <= 0:
        if status != "BLOCK":
            status = "REVIEW_REQUIRED"
        reasons.append("portfolio_total_equity_required_for_asset_proportional_sizing")
    safety_authority = _resolve_safety_maximum_position_weight(safety_limit_summary)
    safety_cap = safety_authority["safety_maximum_position_weight"]
    if safety_authority["safety_authority_status"] == "BLOCK":
        status = "BLOCK"
        reasons.append(str(safety_authority["reason_code"]))
    elif safety_authority["safety_authority_status"] != "PASS" and status != "BLOCK":
        status = "REVIEW_REQUIRED"
        reasons.append(str(safety_authority["reason_code"]))
    if safety_cap == 0.20:
        status = "BLOCK"
        reasons.append("legacy_0_20_implicit_safety_concentration_forbidden")
    if (
        config
        and safety_authority["safety_authority_status"] == "PASS"
        and safety_cap is not None
        and not safety_authority["explicit_zero_cap"]
        and config.strategy_maximum_position_weight > safety_cap
    ):
        status = "BLOCK"
        reasons.append("configured_max_position_weight_above_safety_cap")
    effective_cap = min(config.strategy_maximum_position_weight, safety_cap) if config and safety_cap is not None else None

    sizing_rows = _rows_with_price_volatility(portfolio_construction_summary.rows, price_volatility_summary)
    positions: list[dict[str, Any]] = []
    if config is None or status != "PASS":
        positions = [_unresolved_position(row, config=config, safety_cap=effective_cap) for row in sizing_rows]
        total_target_weight = 0.0
    else:
        positions, sizing_reasons = _size_positions(
            config=config,
            rows=sizing_rows,
            target_count=target_count or 0,
            target_exposure=target_exposure or 0.0,
            portfolio_value=portfolio_value,
            safety_cap=safety_cap or 0.0,
        )
        reasons.extend(sizing_reasons)
        if any(item["sizing_status"] in {"QUALITY_UNAVAILABLE", "VOLATILITY_UNAVAILABLE", "MINIMUM_NOTIONAL_UNMET", "WITHHELD"} for item in positions):
            status = "REVIEW_REQUIRED"
        total_target_weight = round(sum(float(item["target_weight"]) for item in positions), 6)
        if target_exposure is not None and total_target_weight > target_exposure + 0.000001:
            status = "BLOCK"
            reasons.append("aggregate_target_weight_above_exposure_cap")
        if safety_cap is not None and any(float(item["target_weight"]) > safety_cap + 0.000001 for item in positions):
            status = "BLOCK"
            reasons.append("produced_position_weight_above_safety_cap")

    feature_date = min([s.feature_date for s in summaries.values() if s.feature_date] or [business_date])
    future = any(s.feature_date and s.feature_date > business_date for s in summaries.values())
    if future:
        status = "BLOCK"
        reasons.append("future_source_date_detected")
    source_hashes = [{"role": name, "path": s.source_ref, "sha256": _strip_sha256(s.source_hash)} for name, s in summaries.items()]
    if config:
        source_hashes.append({"role": "position_sizing_config", "path": config.config_source, "sha256": config_source_hash})

    payload = {
        "schema_version": SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "business_date": business_date,
        "as_of": as_of,
        "feature_date": feature_date,
        "artifact_lifecycle_status": ARTIFACT_LIFECYCLE_STATUS,
        "source_authority_status": source_status,
        "producer_result_status": status,
        "runtime_consumer_eligibility": RUNTIME_CONSUMER_ELIGIBILITY,
        **status_contract_fields(
            producer_result_status=status,
            artifact_lifecycle_status=ARTIFACT_LIFECYCLE_STATUS,
            runtime_consumer_eligibility=RUNTIME_CONSUMER_ELIGIBILITY,
            reason_codes=sorted(set(reasons)),
            decision_resolution="UNRESOLVED" if target_count_unresolved or target_exposure_unresolved or status != "PASS" else "RESOLVED",
        ),
        "sizing_method": config.sizing_method if config else "",
        "target_gross_exposure_ratio": None if target_exposure is None else round(target_exposure, 6),
        "target_gross_exposure_ratio_resolution": numeric_resolution(target_exposure, unresolved=target_exposure is None),
        "target_position_count": target_count,
        "target_position_count_resolution": numeric_resolution(target_count, unresolved=target_count is None),
        "portfolio_value": round(portfolio_value, 2),
        "portfolio_total_equity": round(portfolio_value, 2),
        "minimum_meaningful_notional_policy": dict(config.minimum_meaningful_notional) if config else {},
        "strategy_maximum_position_weight": config.strategy_maximum_position_weight if config else None,
        "strategy_maximum_position_weight_source": f"{config.config_source}#strategy_maximum_position_weight" if config else "",
        "safety_maximum_position_weight": safety_cap,
        "safety_maximum_position_weight_source": safety_authority["safety_maximum_position_weight_source"],
        "safety_authority_status": safety_authority["safety_authority_status"],
        "effective_maximum_position_weight": effective_cap,
        "effective_maximum_position_weight_derivation": safety_authority["effective_maximum_position_weight_derivation"] if config else "position_sizing_config_missing",
        "explicit_zero_cap": safety_authority["explicit_zero_cap"],
        "emergency_brake_active": safety_authority["emergency_brake_active"],
        "market_context_risk_state": _extract_market_context_risk_state(dynamic_cash_exposure_summary),
        "dynamic_position_count": target_count,
        "dynamic_position_count_resolution": numeric_resolution(target_count, unresolved=target_count is None),
        "dynamic_cash_exposure": None if target_exposure is None else round(target_exposure, 6),
        "dynamic_cash_exposure_resolution": numeric_resolution(target_exposure, unresolved=target_exposure is None),
        "aggregate_exposure_cap": None if target_exposure is None else round(target_exposure, 6),
        "aggregate_exposure_cap_resolution": numeric_resolution(target_exposure, unresolved=target_exposure is None),
        "safety_authority_resolution": safety_authority,
        "positions": positions,
        "positions_sized": sum(1 for item in positions if item["sizing_status"] in {"SIZED", "CAPPED"}),
        "positions_withheld": sum(1 for item in positions if item["sizing_status"] not in {"SIZED", "CAPPED"}),
        "total_target_weight": round(sum(float(item["target_weight"]) for item in positions), 6),
        "residual_cash_ratio": round(max(1.0 - sum(float(item["target_weight"]) for item in positions), 0.0), 6),
        "concrete_target_weight_decided": status == "PASS",
        "target_notional_decided": status == "PASS",
        "share_quantity_decided": False,
        "lot_rounding_decided": False,
        "order_price_decided": False,
        "pending_decided": False,
        "submit_decided": False,
        "config_reference": config.config_source if config else "",
        "config_hash": f"sha256:{config_hash}" if config_hash else "",
        "config_payload": config_payload,
        "reason_codes": sorted(set(reasons)),
        "reason_code_contract": {
            "configured_max_position_weight_above_safety_cap": "Config maximum position weight exceeds the independent safety concentration cap before any position is produced.",
            "produced_position_weight_above_safety_cap": "At least one produced target position weight exceeds the independent safety concentration cap.",
            "aggregate_target_weight_above_exposure_cap": "Produced total target weight exceeds target gross exposure.",
            "missing_safety_maximum_position_weight_authority": "Safety concentration authority is missing and must not be represented as a zero cap.",
            "explicit_zero_safety_cap_without_authority": "A zero safety concentration cap requires explicit emergency or risk-off authority.",
        },
        "upstream_artifacts": {name: s.to_dict(requested_business_date=business_date) for name, s in summaries.items()},
        "source_artifacts": [{"role": name, "path": s.source_ref, "required": True, "status": s.status} for name, s in summaries.items()],
        "source_hashes": source_hashes,
        "temporal_safety": {"point_in_time": not future, "future_leakage_used": future, "feature_date_lte_business_date": feature_date <= business_date, "implicit_latest_fallback_used": False, "previous_day_position_sizing_copied": False},
        "shadow_comparison": {"legacy_max_position_weight": 0.20, "legacy_quantity_result": "downstream_runtime_authority_preserved", "would_change_buy_allocation": status == "PASS", "would_change_add_allocation": status == "PASS", "would_change_reduce_target": status == "PASS", "would_change_exit_target": status == "PASS", "runtime_behavior_changed": False},
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    return payload, {"schema_version": "phase22_j_position_sizing_evidence.v1", "producer_result_status": status, "reason_codes": payload["reason_codes"]}


def validate_position_sizing_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    required = {"schema_version","business_date","as_of","feature_date","artifact_lifecycle_status","source_authority_status","producer_result_status","runtime_consumer_eligibility","target_gross_exposure_ratio","target_position_count","positions","total_target_weight","residual_cash_ratio","concrete_target_weight_decided","target_notional_decided","share_quantity_decided","lot_rounding_decided","source_artifacts","source_hashes","temporal_safety","strategy_maximum_position_weight","strategy_maximum_position_weight_source","safety_maximum_position_weight","safety_maximum_position_weight_source","safety_authority_status","effective_maximum_position_weight","effective_maximum_position_weight_derivation","explicit_zero_cap","emergency_brake_active","market_context_risk_state","dynamic_position_count","dynamic_cash_exposure","aggregate_exposure_cap"}
    errors = [f"required_field_missing:{f}" for f in sorted(required - set(payload))]
    if payload.get("schema_version") != SCHEMA_VERSION: errors.append("unsupported_schema_version")
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS: errors.append("artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY: errors.append("runtime_consumer_eligibility_must_be_not_eligible")
    target_unresolved = (
        payload.get("target_gross_exposure_ratio_resolution") == "UNRESOLVED"
        or payload.get("target_position_count_resolution") == "UNRESOLVED"
    )
    target_exposure = None if target_unresolved and payload.get("target_gross_exposure_ratio") is None else _ratio_field(errors, payload, "target_gross_exposure_ratio")
    total = _ratio_field(errors, payload, "total_target_weight")
    if target_exposure is not None and total is not None and total > target_exposure + 0.000001:
        errors.append("aggregate_target_weight_above_exposure_cap")
    safety_cap = _optional_ratio_field(errors, payload, "safety_maximum_position_weight")
    _optional_ratio_field(errors, payload, "effective_maximum_position_weight")
    if payload.get("safety_authority_status") not in {"PASS", "REVIEW_REQUIRED", "BLOCK"}:
        errors.append("invalid_safety_authority_status")
    if safety_cap is None and payload.get("safety_authority_status") == "PASS":
        errors.append("safety_cap_required_when_authority_pass")
    if safety_cap == 0 and payload.get("explicit_zero_cap") is not True:
        errors.append("zero_safety_cap_requires_explicit_zero_cap")
    if safety_cap == 0.20:
        errors.append("legacy_0_20_implicit_safety_concentration_forbidden")
    if target_unresolved:
        for field in ("target_position_count", "dynamic_position_count"):
            if payload.get(field) is not None:
                errors.append(f"unresolved_count_must_be_null:{field}")
        for field in ("dynamic_cash_exposure", "aggregate_exposure_cap"):
            if payload.get(field) is not None:
                errors.append(f"unresolved_ratio_must_be_null:{field}")
    positions = payload.get("positions")
    if not isinstance(positions, list):
        errors.append("positions_not_list")
    else:
        for index, position in enumerate(positions):
            errors.extend(_validate_position(position, index=index, safety_cap=safety_cap))
    for field in sorted(FORBIDDEN_FIELDS & set(payload)):
        errors.append(f"quantity_or_runtime_field_forbidden:{field}")
    for field in ("share_quantity_decided","lot_rounding_decided","order_price_decided","pending_decided","submit_decided","production_consumer_connected","runtime_switch_performed"):
        if payload.get(field) is not False:
            errors.append(f"{field}_must_be_false")
    temporal = payload.get("temporal_safety") if isinstance(payload.get("temporal_safety"), dict) else {}
    if temporal.get("implicit_latest_fallback_used") is not False: errors.append("implicit_latest_fallback_forbidden")
    if temporal.get("previous_day_position_sizing_copied") is not False: errors.append("previous_day_copy_forbidden")
    if errors:
        raise PositionSizingSchemaError(";".join(errors))
    return {"status": "PASS", "errors": []}


def verify_source_hashes(payload: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    for item in payload.get("source_hashes") or []:
        path = Path(str(item.get("path") or ""))
        if path.is_file() and sha256_file(path) != _strip_sha256(str(item.get("sha256") or "")):
            mismatches.append(str(path))
    return {"status": "BLOCK" if mismatches else "PASS", "mismatches": mismatches}


def load_position_sizing_fixture(path: Path | str, *, for_production: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_position_sizing_artifact(payload)
    if for_production:
        raise PositionSizingConsumerError("Phase22-J Position Sizing is not production-consumable")
    return payload


def position_sizing_hash(payload: dict[str, Any]) -> str:
    return stable_payload_hash({k: v for k, v in payload.items() if k != "artifact_hash"})


def stable_payload_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _size_positions(*, config: PositionSizingConfig, rows: tuple[Mapping[str, Any], ...], target_count: int, target_exposure: float, portfolio_value: float, safety_cap: float) -> tuple[list[dict[str, Any]], list[str]]:
    if target_count <= 0 or target_exposure <= 0:
        return ([_unresolved_position(row, config=config, safety_cap=safety_cap) for row in rows], ["position_count_or_exposure_unresolved"])
    base = target_exposure / float(target_count)
    raw: list[dict[str, Any]] = []
    reasons: list[str] = []
    max_weight = min(config.strategy_maximum_position_weight, safety_cap)
    for row in rows:
        item = _raw_position(row, config=config, base=base, max_weight=max_weight, portfolio_value=portfolio_value)
        raw.append(item)
    active_total = sum(float(item["capped_weight"]) for item in raw if item["sizing_status"] in {"SIZED", "CAPPED"})
    scale = min(1.0, target_exposure / active_total) if active_total > 0 else 0.0
    positions = []
    for item in raw:
        if item["sizing_status"] in {"SIZED", "CAPPED"}:
            target_weight = round(float(item["capped_weight"]) * scale, 6)
            target_notional = round(target_weight * portfolio_value, 2)
            min_notional = float(item["minimum_meaningful_notional"])
            if 0 < target_notional < min_notional:
                item = {**item, "target_weight": 0.0, "weight_delta": round(0.0 - float(item["current_weight"]), 6), "target_notional": 0.0, "sizing_status": "MINIMUM_NOTIONAL_UNMET", "uncertainty": "MINIMUM_NOTIONAL_UNMET", "reason_codes": sorted(set(item["reason_codes"] + ["minimum_meaningful_notional_unmet"]))}
            else:
                current_notional = round(float(item["current_weight"]) * portfolio_value, 2)
                incremental = round(target_notional - current_notional, 2)
                item = {**item, "target_weight": target_weight, "weight_delta": round(target_weight - float(item["current_weight"]), 6), "target_notional": target_notional, "current_notional": current_notional, "incremental_target_notional": incremental, "incremental_buy_notional": round(max(incremental, 0.0), 2)}
        positions.append(item)
    return positions, reasons


def _raw_position(row: Mapping[str, Any], *, config: PositionSizingConfig, base: float, max_weight: float, portfolio_value: float) -> dict[str, Any]:
    code = str(row.get("security_code") or row.get("symbol") or "")
    membership = str(row.get("membership_intent") or "UNRESOLVED").upper()
    pm_action = str(row.get("pm_action") or ("NEW" if membership == "ADD_CANDIDATE" else "HOLD")).upper()
    if pm_action not in PM_ACTIONS:
        pm_action = "UNRESOLVED"
    current_weight = _ratio(row.get("current_weight"), 0.0)
    quality = _quality_multiplier(row, config)
    vol = _volatility_multiplier(row, config)
    reasons = [f"pm_action:{pm_action}", f"membership_intent:{membership}"]
    status = "SIZED"
    uncertainty = "LOW"
    if quality is None:
        quality = 0.0
        status = "QUALITY_UNAVAILABLE"
        uncertainty = "QUALITY_UNAVAILABLE"
        reasons.append("quality_missing_fail_closed")
    if vol is None:
        vol = 0.0
        status = "VOLATILITY_UNAVAILABLE"
        uncertainty = "VOLATILITY_UNAVAILABLE"
        reasons.append("volatility_missing_fail_closed")
    adjusted = base * quality * vol * float(config.pm_intent_adjustment.get(pm_action, 1.0))
    if pm_action == "EXIT" or membership in {"REMOVE_CANDIDATE", "EXCLUDE"}:
        adjusted = 0.0
    elif pm_action == "REDUCE":
        adjusted = min(adjusted, current_weight * 0.5)
    elif pm_action == "ADD":
        adjusted = max(adjusted, current_weight + base * 0.25)
    elif pm_action == "HOLD" and current_weight > 0:
        adjusted = max(min(adjusted, max_weight), min(current_weight, max_weight))
    capped = min(max(adjusted, 0.0), max_weight)
    if capped < adjusted:
        status = "CAPPED"
        reasons.append("position_concentration_cap_applied")
    price = _positive_float(row.get("reference_price"), 0.0)
    min_notional = _minimum_notional(config, price)
    target = round(capped, 6) if status in {"SIZED", "CAPPED"} else 0.0
    return {
        "security_code": code,
        "position_reference": str(row.get("position_reference") or row.get("member_id") or code),
        "membership_intent": membership,
        "pm_action": pm_action,
        "current_weight": round(current_weight, 6),
        "base_weight": round(base, 6),
        "quality_adjustment": round(quality, 6),
        "volatility_adjustment": round(vol, 6),
        "pm_intent_adjustment": round(float(config.pm_intent_adjustment.get(pm_action, 1.0)), 6),
        "adjusted_weight": round(max(adjusted, 0.0), 6),
        "capped_weight": round(capped, 6),
        "target_weight": target,
        "weight_delta": round(target - current_weight, 6),
        "target_notional": round(target * portfolio_value, 2),
        "current_notional": round(current_weight * portfolio_value, 2),
        "incremental_target_notional": round((target - current_weight) * portfolio_value, 2),
        "incremental_buy_notional": round(max((target - current_weight) * portfolio_value, 0.0), 2),
        "minimum_meaningful_notional": round(min_notional, 2),
        "maximum_position_weight": round(max_weight, 6),
        "sizing_priority": _positive_int(row.get("allocation_priority") or row.get("construction_priority"), 999),
        "sizing_status": status,
        "confidence": round(min(_ratio(row.get("confidence"), 1.0), _ratio(row.get("opportunity_confidence"), 1.0)), 6),
        "uncertainty": uncertainty,
        "reason_codes": sorted(set(reasons)),
    }


def _unresolved_position(row: Mapping[str, Any], *, config: PositionSizingConfig | None, safety_cap: float | None) -> dict[str, Any]:
    max_weight = min(config.strategy_maximum_position_weight, safety_cap) if config and safety_cap is not None else safety_cap or 0.0
    current_weight = _ratio(row.get("current_weight"), 0.0)
    return {
        "security_code": str(row.get("security_code") or row.get("symbol") or ""),
        "position_reference": str(row.get("position_reference") or row.get("member_id") or row.get("security_code") or ""),
        "membership_intent": str(row.get("membership_intent") or "UNRESOLVED").upper(),
        "pm_action": str(row.get("pm_action") or "UNRESOLVED").upper(),
        "current_weight": round(current_weight, 6),
        "base_weight": 0.0,
        "quality_adjustment": 0.0,
        "volatility_adjustment": 0.0,
        "pm_intent_adjustment": 0.0,
        "adjusted_weight": 0.0,
        "capped_weight": 0.0,
        "target_weight": 0.0,
        "weight_delta": round(0.0 - current_weight, 6),
        "target_notional": 0.0,
        "current_notional": 0.0,
        "incremental_target_notional": 0.0,
        "incremental_buy_notional": 0.0,
        "minimum_meaningful_notional": 0.0,
        "maximum_position_weight": round(max_weight, 6),
        "sizing_priority": _positive_int(row.get("allocation_priority") or row.get("construction_priority"), 999),
        "sizing_status": "UPSTREAM_REVIEW_REQUIRED",
        "confidence": 0.0,
        "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
        "reason_codes": ["upstream_review_required"],
    }


def _quality_multiplier(row: Mapping[str, Any], config: PositionSizingConfig) -> float | None:
    score = row.get("opportunity_score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return None
    adj = config.opportunity_adjustment
    lo = float(adj["score_min"]); hi = float(adj["score_max"])
    if hi <= lo:
        raise PositionSizingConfigError("invalid score range")
    normalized = min(max((float(score) - lo) / (hi - lo), 0.0), 1.0)
    multiplier = 1.0 + (normalized - 0.5) * float(adj["quality_multiplier_strength"])
    return min(max(multiplier, float(adj["minimum_multiplier"])), float(adj["maximum_multiplier"]))


def _volatility_multiplier(row: Mapping[str, Any], config: PositionSizingConfig) -> float | None:
    value = row.get("volatility")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) <= 0:
        return None
    adj = config.volatility_adjustment
    vol = min(max(float(value), float(adj["minimum_volatility"])), float(adj["maximum_volatility"]))
    multiplier = float(adj["reference_volatility"]) / vol
    return min(max(multiplier, float(adj["minimum_multiplier"])), float(adj["maximum_multiplier"]))


def _minimum_notional(config: PositionSizingConfig, price: float) -> float:
    policy = config.minimum_meaningful_notional
    base = _positive_float(policy.get("base_jpy"), 0.0)
    unit = _positive_float(policy.get("tradable_unit"), 100.0)
    buffer = _ratio(policy.get("price_buffer_ratio"), 0.0)
    round_lot_notional = price * unit * (1.0 + buffer) if price > 0 else 0.0
    return max(base, round_lot_notional)


def _resolve_safety_maximum_position_weight(safety_limit_summary: PositionSizingSourceSummary) -> dict[str, Any]:
    summary = dict(safety_limit_summary.summary or {})
    status = "PASS" if safety_limit_summary.status == "PASS" else "REVIEW_REQUIRED"
    reason = "safety_maximum_position_weight_resolved"
    source = ""
    value: Any = None
    if "maximum_position_weight" in summary:
        value = summary.get("maximum_position_weight")
        source = f"{safety_limit_summary.source_ref}#maximum_position_weight"
    else:
        concentration = summary.get("concentration")
        if isinstance(concentration, Mapping) and "maximum_position_weight" in concentration:
            value = concentration.get("maximum_position_weight")
            source = f"{safety_limit_summary.source_ref}#concentration.maximum_position_weight"
    explicit_zero = bool(summary.get("explicit_zero_cap") or summary.get("emergency_brake_active") or summary.get("hard_risk_off_active"))
    emergency = bool(summary.get("emergency_brake_active") or summary.get("hard_risk_off_active"))
    if value is None:
        return {
            "safety_authority_status": "REVIEW_REQUIRED" if safety_limit_summary.status != "PASS" else "BLOCK",
            "reason_code": "safety_concentration_limit_review_required" if safety_limit_summary.status != "PASS" else "missing_safety_maximum_position_weight_authority",
            "safety_maximum_position_weight": None,
            "safety_maximum_position_weight_source": source,
            "explicit_zero_cap": explicit_zero,
            "emergency_brake_active": emergency,
            "effective_maximum_position_weight_derivation": "missing_safety_authority_no_effective_cap",
        }
    try:
        cap = _ratio(value, None)
    except PositionSizingConfigError:
        return {
            "safety_authority_status": "BLOCK",
            "reason_code": "invalid_safety_maximum_position_weight_authority",
            "safety_maximum_position_weight": None,
            "safety_maximum_position_weight_source": source,
            "explicit_zero_cap": explicit_zero,
            "emergency_brake_active": emergency,
            "effective_maximum_position_weight_derivation": "invalid_safety_authority_no_effective_cap",
        }
    if cap == 0.0 and not explicit_zero:
        status = "BLOCK"
        reason = "explicit_zero_safety_cap_without_authority"
    return {
        "safety_authority_status": status,
        "reason_code": reason,
        "safety_maximum_position_weight": cap,
        "safety_maximum_position_weight_source": source,
        "explicit_zero_cap": cap == 0.0 and explicit_zero,
        "emergency_brake_active": emergency,
        "effective_maximum_position_weight_derivation": "min(strategy_maximum_position_weight, safety_maximum_position_weight)",
    }


def _extract_market_context_risk_state(dynamic_cash_exposure_summary: PositionSizingSourceSummary) -> str:
    summary = dynamic_cash_exposure_summary.summary or {}
    for key in ("market_context_risk_state", "risk_state", "risk_posture", "market_regime"):
        value = summary.get(key)
        if isinstance(value, str) and value:
            return value
    return "UNRESOLVED"


def _rows_with_price_volatility(
    rows: tuple[Mapping[str, Any], ...],
    price_volatility_summary: PositionSizingSourceSummary,
) -> tuple[Mapping[str, Any], ...]:
    if not rows or price_volatility_summary.status != "PASS":
        return rows
    volatility_by_code: dict[str, float] = {}
    for row in price_volatility_summary.rows:
        if not isinstance(row, Mapping):
            continue
        code = str(row.get("symbol") or row.get("code") or row.get("security_code") or "")
        value = row.get("volatility_value", row.get("volatility_return_std_20d"))
        if not code or isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) <= 0:
            continue
        volatility_by_code[code] = float(value)
    if not volatility_by_code:
        return rows
    enriched: list[Mapping[str, Any]] = []
    for row in rows:
        code = str(row.get("security_code") or row.get("symbol") or row.get("code") or "")
        if code in volatility_by_code and row.get("volatility") in (None, ""):
            enriched.append({**dict(row), "volatility": volatility_by_code[code], "volatility_source": price_volatility_summary.source_ref})
        else:
            enriched.append(row)
    return tuple(enriched)


def _validate_position(position: Any, *, index: int, safety_cap: float | None) -> list[str]:
    errors: list[str] = []
    if not isinstance(position, dict):
        return [f"position_not_object:{index}"]
    required = {"security_code","membership_intent","pm_action","current_weight","base_weight","quality_adjustment","volatility_adjustment","adjusted_weight","capped_weight","target_weight","weight_delta","target_notional","current_notional","incremental_target_notional","incremental_buy_notional","minimum_meaningful_notional","maximum_position_weight","sizing_status","confidence","uncertainty","reason_codes"}
    errors.extend(f"position_required_field_missing:{index}:{f}" for f in sorted(required - set(position)))
    if position.get("sizing_status") not in SIZING_STATUSES:
        errors.append(f"invalid_sizing_status:{index}")
    for field in ("current_weight","base_weight","adjusted_weight","capped_weight","target_weight","maximum_position_weight","confidence"):
        _ratio_field(errors, position, field, prefix=f"position:{index}:")
    for field in ("quality_adjustment","volatility_adjustment","pm_intent_adjustment"):
        value = position.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 10:
            errors.append(f"invalid_multiplier:position:{index}:{field}")
    target = _ratio_field(errors, position, "target_weight", prefix=f"position:{index}:")
    maximum = _ratio_field(errors, position, "maximum_position_weight", prefix=f"position:{index}:")
    if target is not None and maximum is not None and target > maximum + 0.000001:
        errors.append(f"target_weight_above_position_cap:{index}")
    if target is not None and safety_cap is not None and target > safety_cap + 0.000001:
        errors.append(f"target_weight_above_safety_cap:{index}")
    for field in ("target_notional", "current_notional", "incremental_buy_notional"):
        if isinstance(position.get(field), bool) or not isinstance(position.get(field), (int, float)) or float(position.get(field)) < 0:
            errors.append(f"invalid_notional:{index}:{field}")
    if isinstance(position.get("incremental_target_notional"), bool) or not isinstance(position.get("incremental_target_notional"), (int, float)):
        errors.append(f"invalid_notional:{index}:incremental_target_notional")
    for field in sorted(FORBIDDEN_FIELDS & set(position)):
        errors.append(f"quantity_or_runtime_field_forbidden:{index}:{field}")
    if not isinstance(position.get("reason_codes"), list):
        errors.append(f"reason_codes_not_list:{index}")
    return errors


def _numeric_mapping(payload: Mapping[str, Any], key: str) -> dict[str, float]:
    obj = payload.get(key)
    if not isinstance(obj, dict):
        raise PositionSizingConfigError(f"{key} required")
    result: dict[str, float] = {}
    for name, value in obj.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        result[str(name)] = float(value)
    return result


def _ratio(value: Any, default: float | None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if default is None: raise PositionSizingConfigError("ratio required")
        return default
    if not 0 <= float(value) <= 1:
        raise PositionSizingConfigError("ratio out of range")
    return float(value)


def _ratio_field(errors: list[str], payload: Mapping[str, Any], field: str, *, prefix: str = "") -> float | None:
    try: return _ratio(payload.get(field), None)
    except Exception: errors.append(f"invalid_ratio:{prefix}{field}"); return None


def _optional_ratio_field(errors: list[str], payload: Mapping[str, Any], field: str, *, prefix: str = "") -> float | None:
    if payload.get(field) is None:
        return None
    return _ratio_field(errors, payload, field, prefix=prefix)


def _positive_float(value: Any, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(float(value), 0.0)


def _positive_int(value: Any, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return default
    return int(value)


def _text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise PositionSizingConfigError(f"{field} required")
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
