from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from ai_fund_lab_v2.strategy.candidate_opportunity_compatibility import (
    INCOMPATIBLE_DATE,
    INCOMPATIBLE_HASH,
    INCOMPATIBLE_SCHEMA,
    SOURCE_BLOCKED,
    SOURCE_MISSING,
    SOURCE_NOT_ELIGIBLE,
    SOURCE_REVIEW_REQUIRED,
    validate_corporate_event_compatibility,
    validate_market_context_compatibility,
)
from ai_fund_lab_v2.strategy import portfolio_policy
from ai_fund_lab_v2.strategy import strategy_intelligence
from ai_fund_lab_v2.strategy.status_contract import compatibility_status_from_payload, status_contract_fields


SCHEMA_VERSION = "position_management.v1"
PRODUCER_VERSION = "phase22_d_position_management_producer.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"

PM_ACTIONS = {"HOLD", "ADD", "REDUCE", "EXIT", "UNRESOLVED"}
PM_INTENSITIES = {"NONE", "LIGHT", "MEDIUM", "STRONG", "UNRESOLVED"}
SOURCE_AUTHORITY_STATUSES = {"VALID", "MISSING", "STALE", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
PRODUCER_RESULT_STATUSES = {"PASS", "REVIEW_REQUIRED", "BLOCK"}
ARTIFACT_LIFECYCLE_STATUSES = {"DRAFT", "VALIDATED", "REVIEW_REQUIRED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}
RUNTIME_CONSUMER_ELIGIBILITIES = {"ELIGIBLE", "NOT_ELIGIBLE", "REVIEW_REQUIRED", "BLOCKED"}
FORBIDDEN_QUANTITY_FIELDS = {
    "quantity",
    "broker_quantity",
    "runtime_sell_quantity",
    "exit_quantity",
    "reduce_quantity",
    "add_quantity",
    "buy_quantity",
    "order_quantity",
    "sell_percentage",
    "sell_weight_delta",
    "sell_allocation_jpy",
    "lot_rounding_result",
}
BLOCKING_UPSTREAM_STATUSES = {INCOMPATIBLE_SCHEMA, INCOMPATIBLE_DATE, INCOMPATIBLE_HASH, SOURCE_BLOCKED, SOURCE_MISSING}
REVIEW_UPSTREAM_STATUSES = {SOURCE_REVIEW_REQUIRED, SOURCE_NOT_ELIGIBLE}
VALID_GENERATION_STATUSES = {"RESOLVED_COMMITTED", "COMMITTED", "VALID", "PASS", "SHADOW_VALID"}
REGIME_EVENT_CONFIG_SCHEMA_VERSION = "regime_event_position_management_config.v1"
REGIME_EVENT_PRODUCER_VERSION = "phase22_k_regime_event_position_management_producer.v1"


class PositionManagementError(RuntimeError):
    pass


class PositionManagementSchemaError(PositionManagementError):
    pass


class PositionManagementConsumerError(PositionManagementError):
    pass


class PositionManagementConfigError(PositionManagementError):
    pass


@dataclass(frozen=True)
class RegimeEventPMConfig:
    config_version: str
    config_source: str
    regime_rules: Mapping[str, Mapping[str, int]]
    volatility_regime_rules: Mapping[str, Mapping[str, int]]
    corporate_event_rules: Mapping[str, Any]
    technical_health_rules: Mapping[str, float]
    opportunity_persistence_rules: Mapping[str, float]
    holding_period_rules: Mapping[str, int]
    cooldown_rules: Mapping[str, int]
    reentry_rules: Mapping[str, Any]
    conflict_resolution: tuple[str, ...]
    action_intensity: Mapping[str, Mapping[str, str]]
    uncertainty_rules: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": REGIME_EVENT_CONFIG_SCHEMA_VERSION,
            "config_version": self.config_version,
            "config_source": self.config_source,
            "regime_rules": {key: dict(value) for key, value in self.regime_rules.items()},
            "volatility_regime_rules": {key: dict(value) for key, value in self.volatility_regime_rules.items()},
            "corporate_event_rules": dict(self.corporate_event_rules),
            "technical_health_rules": dict(self.technical_health_rules),
            "opportunity_persistence_rules": dict(self.opportunity_persistence_rules),
            "holding_period_rules": dict(self.holding_period_rules),
            "cooldown_rules": dict(self.cooldown_rules),
            "reentry_rules": dict(self.reentry_rules),
            "conflict_resolution": list(self.conflict_resolution),
            "action_intensity": {key: dict(value) for key, value in self.action_intensity.items()},
            "uncertainty_rules": dict(self.uncertainty_rules),
        }


@dataclass(frozen=True)
class PMAcceptedGenerationReference:
    generation_id: str
    generation_status: str
    model_reference: str
    scaler_reference: str
    model_generation_id: str
    scaler_generation_id: str
    model_hash: str
    scaler_hash: str
    feature_schema_hash: str
    accepted_generation_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_id": self.generation_id,
            "generation_status": self.generation_status,
            "model_reference": self.model_reference,
            "scaler_reference": self.scaler_reference,
            "model_generation_id": self.model_generation_id,
            "scaler_generation_id": self.scaler_generation_id,
            "model_hash": self.model_hash,
            "scaler_hash": self.scaler_hash,
            "feature_schema_hash": self.feature_schema_hash,
            "accepted_generation_hash": self.accepted_generation_hash,
            "unscaled_fallback_used": False,
            "generation_binding_validation": validate_generation_binding(self),
        }


@dataclass(frozen=True)
class PMSourceSummary:
    status: str
    business_date: str
    feature_date: str
    source_ref: str
    source_hash: str
    summary: dict[str, Any]

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
class PositionManagementProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "position_management" / business_date / "position_management.json"


def load_regime_event_pm_config(path: Path | str) -> RegimeEventPMConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise PositionManagementConfigError(f"regime/event PM config missing: {config_path}")
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != REGIME_EVENT_CONFIG_SCHEMA_VERSION:
        raise PositionManagementConfigError("unsupported regime/event PM config")
    return RegimeEventPMConfig(
        config_version=_required_text(payload, "config_version"),
        config_source=str(config_path),
        regime_rules=_nested_int_map(payload, "regime_rules"),
        volatility_regime_rules=_nested_int_map(payload, "volatility_regime_rules"),
        corporate_event_rules=dict(payload.get("corporate_event_rules") or {}),
        technical_health_rules=_numeric_map(payload, "technical_health_rules"),
        opportunity_persistence_rules=_numeric_map(payload, "opportunity_persistence_rules"),
        holding_period_rules=_int_map(payload, "holding_period_rules"),
        cooldown_rules=_int_map(payload, "cooldown_rules"),
        reentry_rules=dict(payload.get("reentry_rules") or {}),
        conflict_resolution=tuple(str(item) for item in payload.get("conflict_resolution") or ()),
        action_intensity={str(k): {str(kk): str(vv) for kk, vv in dict(v).items()} for k, v in (payload.get("action_intensity") or {}).items() if isinstance(v, dict)},
        uncertainty_rules=dict(payload.get("uncertainty_rules") or {}),
    )


def default_regime_event_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "regime_event_position_management" / business_date / "position_management.json"


def produce_position_management_artifact(
    *,
    business_date: str,
    market_context_artifact_path: Path | str | None,
    corporate_event_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    existing_pm_decisions: Iterable[Mapping[str, Any]],
    position_lifecycle_summary: PMSourceSummary,
    technical_feature_summary: PMSourceSummary,
    opportunity_summary: PMSourceSummary,
    accepted_generation_reference: PMAcceptedGenerationReference,
    output_path: Path | str,
    as_of: str | None = None,
    runtime_current_positions: Iterable[Mapping[str, Any]] | None = None,
    strategy_intelligence_artifact_path: Path | str | None = None,
) -> PositionManagementProducerResult:
    payload, evidence = build_position_management_payload(
        business_date=business_date,
        market_context_artifact_path=market_context_artifact_path,
        corporate_event_artifact_path=corporate_event_artifact_path,
        portfolio_policy_artifact_path=portfolio_policy_artifact_path,
        existing_pm_decisions=existing_pm_decisions,
        runtime_current_positions=runtime_current_positions,
        position_lifecycle_summary=position_lifecycle_summary,
        technical_feature_summary=technical_feature_summary,
        opportunity_summary=opportunity_summary,
        accepted_generation_reference=accepted_generation_reference,
        as_of=as_of,
        strategy_intelligence_artifact_path=strategy_intelligence_artifact_path,
    )
    validate_position_management_artifact(payload)
    artifact_hash = position_management_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final_payload)
    return PositionManagementProducerResult(
        status=str(final_payload["producer_result_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_position_management_payload(
    *,
    business_date: str,
    market_context_artifact_path: Path | str | None,
    corporate_event_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    existing_pm_decisions: Iterable[Mapping[str, Any]],
    position_lifecycle_summary: PMSourceSummary,
    technical_feature_summary: PMSourceSummary,
    opportunity_summary: PMSourceSummary,
    accepted_generation_reference: PMAcceptedGenerationReference,
    as_of: str | None = None,
    runtime_current_positions: Iterable[Mapping[str, Any]] | None = None,
    strategy_intelligence_artifact_path: Path | str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _validate_rfc3339_timestamp(as_of, field="as_of")
    market_result = validate_market_context_compatibility(
        market_context_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    ).to_dict()
    corporate_result = validate_corporate_event_compatibility(
        corporate_event_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    ).to_dict()
    portfolio_result = validate_portfolio_policy_compatibility(
        portfolio_policy_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )
    si_result = strategy_intelligence.validate_strategy_intelligence_compatibility(
        strategy_intelligence_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )
    existing_decision_rows = [dict(row) for row in existing_pm_decisions if isinstance(row, Mapping)]
    runtime_current_connected = runtime_current_positions is not None
    runtime_current_rows = [dict(row) for row in (runtime_current_positions or ()) if isinstance(row, Mapping)]
    positions, position_reasons = _positions_from_runtime_current(
        runtime_current_rows,
        existing_pm_decisions=existing_decision_rows,
        business_date=business_date,
        accepted_generation_reference=accepted_generation_reference,
    )
    if not positions and not runtime_current_connected:
        positions, position_reasons = _positions_from_existing_decisions(existing_decision_rows, business_date=business_date)
    authoritative_empty_portfolio = runtime_current_connected and not positions and not position_reasons
    generation_validation = validate_generation_binding(accepted_generation_reference)
    source_status = "VALID"
    reason_codes: list[str] = list(position_reasons)
    upstream_statuses = [market_result["status"], corporate_result["status"], portfolio_result["status"]]
    if not authoritative_empty_portfolio and strategy_intelligence_artifact_path is not None:
        upstream_statuses.append(si_result["status"])
    if any(status in BLOCKING_UPSTREAM_STATUSES for status in upstream_statuses):
        producer_status = "BLOCK"
        reason_codes.extend([f"upstream_block:{status}" for status in upstream_statuses if status in BLOCKING_UPSTREAM_STATUSES])
        source_status = "HASH_MISMATCH" if INCOMPATIBLE_HASH in upstream_statuses else ("MISSING" if SOURCE_MISSING in upstream_statuses else "AUTHORITY_CONFLICT")
    elif any(status in REVIEW_UPSTREAM_STATUSES for status in upstream_statuses):
        producer_status = "REVIEW_REQUIRED"
        reason_codes.extend([f"upstream_review_required:{status}" for status in upstream_statuses if status in REVIEW_UPSTREAM_STATUSES])
    else:
        producer_status = "PASS"

    summaries = {
        "position_lifecycle": position_lifecycle_summary.to_dict(requested_business_date=business_date),
        "technical_features": technical_feature_summary.to_dict(requested_business_date=business_date),
        "opportunity": opportunity_summary.to_dict(requested_business_date=business_date),
    }
    pm_source_required = not authoritative_empty_portfolio
    for name, summary in (
        ("position_lifecycle", position_lifecycle_summary),
        ("technical_features", technical_feature_summary),
        ("opportunity", opportunity_summary),
    ):
        if not _summary_aligned(summary, business_date=business_date):
            producer_status = "BLOCK"
            reason_codes.append(f"{name}_date_mismatch")
        if not pm_source_required:
            continue
        if summary.status == "BLOCK":
            producer_status = "BLOCK"
            reason_codes.append(f"{name}_block")
        elif summary.status != "PASS" and producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
            reason_codes.append(f"{name}_review_required")
    if generation_validation["status"] == "BLOCK":
        producer_status = "BLOCK"
        reason_codes.extend(generation_validation["reason_codes"])
        source_status = "AUTHORITY_CONFLICT"
    if not positions and not runtime_current_connected:
        if producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
        reason_codes.append("position_management_shadow_positions_required")
    elif not positions and position_reasons:
        if producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
    positions, si_reasons = _attach_strategy_intelligence_positions(
        positions,
        strategy_intelligence_artifact_path=strategy_intelligence_artifact_path,
    )
    reason_codes.extend(si_reasons)
    if any(item.get("action") == "UNRESOLVED" for item in positions) and producer_status != "BLOCK":
        producer_status = "REVIEW_REQUIRED"

    feature_date = min(
        [
            value
            for value in (
                market_result.get("feature_date"),
                corporate_result.get("feature_date"),
                portfolio_result.get("feature_date"),
                si_result.get("feature_date"),
                position_lifecycle_summary.feature_date,
                technical_feature_summary.feature_date,
                opportunity_summary.feature_date,
            )
            if value
        ]
        or [business_date]
    )
    future_leakage_used = any(
        value and value > business_date
        for value in (
            feature_date,
            position_lifecycle_summary.feature_date,
            technical_feature_summary.feature_date,
            opportunity_summary.feature_date,
        )
    )
    if future_leakage_used:
        producer_status = "BLOCK"
        reason_codes.append("future_feature_or_lifecycle_date_detected")

    source_artifacts = [
        {"role": "market_context", "path": str(market_context_artifact_path or ""), "required": True, "status": market_result["status"]},
        {"role": "corporate_event", "path": str(corporate_event_artifact_path or ""), "required": True, "status": corporate_result["status"]},
        {"role": "portfolio_policy", "path": str(portfolio_policy_artifact_path or ""), "required": True, "status": portfolio_result["status"]},
        {"role": "strategy_intelligence", "path": str(strategy_intelligence_artifact_path or ""), "required": pm_source_required and strategy_intelligence_artifact_path is not None, "status": si_result["status"]},
        {"role": "position_lifecycle", "path": position_lifecycle_summary.source_ref, "required": pm_source_required, "status": position_lifecycle_summary.status},
        {"role": "technical_features", "path": technical_feature_summary.source_ref, "required": pm_source_required, "status": technical_feature_summary.status},
        {"role": "opportunity_summary", "path": opportunity_summary.source_ref, "required": pm_source_required, "status": opportunity_summary.status},
        {"role": "accepted_generation", "path": accepted_generation_reference.generation_id, "required": True, "status": generation_validation["status"]},
        {"role": "model", "path": accepted_generation_reference.model_reference, "required": True, "status": generation_validation["model_hash_status"]},
        {"role": "scaler", "path": accepted_generation_reference.scaler_reference, "required": True, "status": generation_validation["scaler_hash_status"]},
    ]
    pm_decision_source_path = str(next((row.get("_source_artifact_path") for row in existing_decision_rows if row.get("_source_artifact_path")), ""))
    pm_decision_source_hash = str(next((row.get("_source_artifact_hash") for row in existing_decision_rows if row.get("_source_artifact_hash")), ""))
    pm_decision_business_date = str(next((row.get("_source_business_date") for row in existing_decision_rows if row.get("_source_business_date")), ""))
    if pm_decision_source_path:
        pm_business_date_status = "PASS" if pm_decision_business_date == business_date else "DATE_MISMATCH"
        if pm_business_date_status != "PASS":
            producer_status = "BLOCK"
            reason_codes.append("position_management_decisions_date_mismatch")
            source_status = "AUTHORITY_CONFLICT"
        source_artifacts.append(
            {
                "role": "position_management_decisions",
                "path": pm_decision_source_path,
                "required": True,
                "status": pm_business_date_status,
                "business_date": pm_decision_business_date,
                "decision_count": len(existing_decision_rows),
                "pm_decision_ids": [
                    str(row.get("pm_decision_id") or row.get("decision_id") or "")
                    for row in existing_decision_rows
                    if row.get("pm_decision_id") or row.get("decision_id")
                ],
                "decision_types": sorted(
                    {
                        str(row.get("decision_type") or row.get("decision") or row.get("action") or "").upper()
                        for row in existing_decision_rows
                        if row.get("decision_type") or row.get("decision") or row.get("action")
                    }
                ),
            }
        )
    source_hashes = [
        {"role": "position_lifecycle", "path": position_lifecycle_summary.source_ref, "sha256": _strip_sha256(position_lifecycle_summary.source_hash)},
        {"role": "technical_features", "path": technical_feature_summary.source_ref, "sha256": _strip_sha256(technical_feature_summary.source_hash)},
        {"role": "opportunity_summary", "path": opportunity_summary.source_ref, "sha256": _strip_sha256(opportunity_summary.source_hash)},
        {"role": "accepted_generation", "path": accepted_generation_reference.generation_id, "sha256": _strip_sha256(accepted_generation_reference.accepted_generation_hash)},
        {"role": "model", "path": accepted_generation_reference.model_reference, "sha256": _strip_sha256(accepted_generation_reference.model_hash)},
        {"role": "scaler", "path": accepted_generation_reference.scaler_reference, "sha256": _strip_sha256(accepted_generation_reference.scaler_hash)},
        *(
            [{"role": "strategy_intelligence", "path": str(strategy_intelligence_artifact_path), "sha256": sha256_file(Path(strategy_intelligence_artifact_path))}]
            if strategy_intelligence_artifact_path and Path(strategy_intelligence_artifact_path).is_file()
            else []
        ),
    ]
    if pm_decision_source_path:
        source_hashes.append(
            {
                "role": "position_management_decisions",
                "path": pm_decision_source_path,
                "sha256": _strip_sha256(pm_decision_source_hash),
            }
        )
    required_hash_roles = {item["role"] for item in source_artifacts if item["required"]}
    if not all(item["sha256"] for item in source_hashes if item["role"] in required_hash_roles):
        if producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
        reason_codes.append("source_lineage_hash_required")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "business_date": business_date,
        "as_of": as_of,
        "feature_date": feature_date,
        "artifact_lifecycle_status": ARTIFACT_LIFECYCLE_STATUS,
        "source_authority_status": source_status,
        "producer_result_status": producer_status,
        "runtime_consumer_eligibility": RUNTIME_CONSUMER_ELIGIBILITY,
        **status_contract_fields(
            producer_result_status=producer_status,
            artifact_lifecycle_status=ARTIFACT_LIFECYCLE_STATUS,
            runtime_consumer_eligibility=RUNTIME_CONSUMER_ELIGIBILITY,
            reason_codes=sorted(set(reason_codes)),
            decision_resolution="RESOLVED" if producer_status == "PASS" else "UNRESOLVED",
        ),
        "positions": positions,
        "position_count": len(positions),
        "runtime_current_position_adapter": {
            "status": "PASS" if positions else "EMPTY_PORTFOLIO" if authoritative_empty_portfolio else "MISSING",
            "source": position_lifecycle_summary.source_ref,
            "source_hash": position_lifecycle_summary.source_hash,
            "runtime_current_connected": runtime_current_connected,
            "authoritative_empty_portfolio": authoritative_empty_portfolio,
            "input_row_count": len(runtime_current_rows),
            "output_position_count": len(positions),
            "direct_position_copy_used": False,
            "fixed_empty_positions_used": False,
            "hold_fallback_used": False,
        },
        "action_taxonomy": sorted(PM_ACTIONS),
        "intensity_taxonomy": sorted(PM_INTENSITIES),
        "quantity_decided": False,
        "minimum_holding_decided": False,
        "cooldown_decided": False,
        "reason_codes": sorted(set(reason_codes)),
        "upstream_artifacts": {
            "market_context": market_result,
            "corporate_event": corporate_result,
            "portfolio_policy": portfolio_result,
            "strategy_intelligence": si_result,
            **summaries,
        },
        "accepted_generation_reference": accepted_generation_reference.to_dict(),
        "model_reference": {
            "path": accepted_generation_reference.model_reference,
            "hash": accepted_generation_reference.model_hash,
            "generation_id": accepted_generation_reference.model_generation_id,
        },
        "scaler_reference": {
            "path": accepted_generation_reference.scaler_reference,
            "hash": accepted_generation_reference.scaler_hash,
            "generation_id": accepted_generation_reference.scaler_generation_id,
        },
        "source_artifacts": source_artifacts,
        "source_hashes": source_hashes,
        "temporal_safety": {
            "point_in_time": not future_leakage_used,
            "future_leakage_used": future_leakage_used,
            "feature_date_lte_business_date": feature_date <= business_date,
            "implicit_latest_fallback_used": False,
            "previous_day_pm_artifact_copied": False,
        },
        "production_consumer_connected": False,
        "strategy_intelligence_production_consumer_connected": True,
        "existing_pm_authority_active": True,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    evidence = {
        "schema_version": "phase22_d_position_management_producer_evidence.v1",
        "business_date": business_date,
        "producer_result_status": producer_status,
        "market_context_status": market_result["status"],
        "corporate_event_status": corporate_result["status"],
        "portfolio_policy_status": portfolio_result["status"],
        "generation_binding_status": generation_validation["status"],
        "quantity_decided": False,
        "reason_codes": payload["reason_codes"],
    }
    return payload, evidence


def produce_regime_event_position_management_artifact(
    *,
    business_date: str,
    position_rows: Iterable[Mapping[str, Any]],
    market_context_summary: PMSourceSummary,
    corporate_event_summary: PMSourceSummary,
    portfolio_policy_summary: PMSourceSummary,
    opportunity_summary: PMSourceSummary,
    position_sizing_summary: PMSourceSummary,
    position_lifecycle_summary: PMSourceSummary,
    technical_feature_summary: PMSourceSummary,
    current_position_summary: PMSourceSummary,
    config: RegimeEventPMConfig | None,
    output_path: Path | str,
    as_of: str | None = None,
    expected_config_hash: str | None = None,
) -> PositionManagementProducerResult:
    payload, evidence = build_regime_event_position_management_payload(
        business_date=business_date,
        position_rows=position_rows,
        market_context_summary=market_context_summary,
        corporate_event_summary=corporate_event_summary,
        portfolio_policy_summary=portfolio_policy_summary,
        opportunity_summary=opportunity_summary,
        position_sizing_summary=position_sizing_summary,
        position_lifecycle_summary=position_lifecycle_summary,
        technical_feature_summary=technical_feature_summary,
        current_position_summary=current_position_summary,
        config=config,
        as_of=as_of,
        expected_config_hash=expected_config_hash,
    )
    validate_position_management_artifact(payload)
    artifact_hash = position_management_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final_payload)
    return PositionManagementProducerResult(
        status=str(final_payload["producer_result_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_regime_event_position_management_payload(
    *,
    business_date: str,
    position_rows: Iterable[Mapping[str, Any]],
    market_context_summary: PMSourceSummary,
    corporate_event_summary: PMSourceSummary,
    portfolio_policy_summary: PMSourceSummary,
    opportunity_summary: PMSourceSummary,
    position_sizing_summary: PMSourceSummary,
    position_lifecycle_summary: PMSourceSummary,
    technical_feature_summary: PMSourceSummary,
    current_position_summary: PMSourceSummary,
    config: RegimeEventPMConfig | None,
    as_of: str | None = None,
    expected_config_hash: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _validate_rfc3339_timestamp(as_of, field="as_of")
    summaries = {
        "market_context": market_context_summary,
        "corporate_event": corporate_event_summary,
        "portfolio_policy": portfolio_policy_summary,
        "opportunity": opportunity_summary,
        "position_sizing": position_sizing_summary,
        "position_lifecycle": position_lifecycle_summary,
        "technical_features": technical_feature_summary,
        "current_position": current_position_summary,
    }
    producer_status = "PASS"
    source_status = "VALID"
    reason_codes: list[str] = []
    for name, summary in summaries.items():
        if not _summary_aligned(summary, business_date=business_date):
            producer_status = "BLOCK"
            reason_codes.append(f"{name}_date_mismatch")
        if summary.status in {"BLOCK", "MISSING", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}:
            producer_status = "BLOCK"
            source_status = "AUTHORITY_CONFLICT"
            reason_codes.append(f"{name}_block:{summary.status}")
        elif summary.status != "PASS" and producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
            reason_codes.append(f"{name}_review_required:{summary.status}")
    config_hash = ""
    config_source_hash = ""
    config_payload = None
    if config is None:
        if producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
        reason_codes.append("regime_event_pm_config_required")
    else:
        config_payload = config.to_dict()
        config_hash = stable_payload_hash(config_payload)
        config_source_hash = sha256_file(Path(config.config_source)) if Path(config.config_source).is_file() else config_hash
        if expected_config_hash and _strip_sha256(expected_config_hash) != config_hash:
            producer_status = "BLOCK"
            source_status = "HASH_MISMATCH"
            reason_codes.append("regime_event_pm_config_hash_mismatch")

    future_leakage_used = any(summary.feature_date and summary.feature_date > business_date for summary in summaries.values())
    if future_leakage_used:
        producer_status = "BLOCK"
        reason_codes.append("future_feature_or_event_date_detected")
    rows = list(position_rows)
    positions: list[dict[str, Any]]
    if not rows:
        if producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
        reason_codes.append("current_position_rows_required")
        positions = []
    elif config is None or producer_status != "PASS":
        positions = [_unresolved_regime_event_position(row, reason="upstream_review_required") for row in rows]
    else:
        positions = [_decide_regime_event_position(row, market_context_summary.summary, corporate_event_summary.summary, portfolio_policy_summary.summary, position_sizing_summary.summary, config, business_date) for row in rows]
        if any(item["action"] == "UNRESOLVED" for item in positions) and producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
        if any("future_event_knowledge_leakage" in item.get("reason_codes", []) for item in positions):
            producer_status = "BLOCK"
            reason_codes.append("future_event_knowledge_leakage")

    feature_date = min([summary.feature_date for summary in summaries.values() if summary.feature_date] or [business_date])
    source_hashes = [{"role": name, "path": summary.source_ref, "sha256": _strip_sha256(summary.source_hash)} for name, summary in summaries.items()]
    if config:
        source_hashes.append({"role": "regime_event_pm_config", "path": config.config_source, "sha256": config_source_hash})
    payload = {
        "schema_version": SCHEMA_VERSION,
        "producer_version": REGIME_EVENT_PRODUCER_VERSION,
        "business_date": business_date,
        "as_of": as_of,
        "feature_date": feature_date,
        "artifact_lifecycle_status": ARTIFACT_LIFECYCLE_STATUS,
        "source_authority_status": source_status,
        "producer_result_status": producer_status,
        "runtime_consumer_eligibility": RUNTIME_CONSUMER_ELIGIBILITY,
        **status_contract_fields(
            producer_result_status=producer_status,
            artifact_lifecycle_status=ARTIFACT_LIFECYCLE_STATUS,
            runtime_consumer_eligibility=RUNTIME_CONSUMER_ELIGIBILITY,
            reason_codes=sorted(set(reason_codes)),
            decision_resolution="RESOLVED" if producer_status == "PASS" else "UNRESOLVED",
        ),
        "positions": positions,
        "position_count": len(positions),
        "action_taxonomy": sorted(PM_ACTIONS),
        "intensity_taxonomy": sorted(PM_INTENSITIES),
        "quantity_decided": False,
        "minimum_holding_decided": True,
        "cooldown_decided": True,
        "regime_rules_defined": config is not None,
        "corporate_event_rules_defined": config is not None,
        "technical_health_rules_defined": config is not None,
        "holding_period_rules_defined": config is not None,
        "cooldown_rules_defined": config is not None,
        "reentry_rules_defined": config is not None,
        "conflict_resolution_defined": config is not None,
        "config_reference": config.config_source if config else "",
        "config_hash": f"sha256:{config_hash}" if config_hash else "",
        "config_payload": config_payload,
        "reason_codes": sorted(set(reason_codes)),
        "upstream_artifacts": {name: summary.to_dict(requested_business_date=business_date) for name, summary in summaries.items()},
        "accepted_generation_reference": {"generation_status": "NOT_CHANGED_BY_PHASE22_K", "unscaled_fallback_used": False},
        "model_reference": {"path": "", "hash": "", "generation_id": "NOT_CHANGED_BY_PHASE22_K"},
        "scaler_reference": {"path": "", "hash": "", "generation_id": "NOT_CHANGED_BY_PHASE22_K"},
        "source_artifacts": [{"role": name, "path": summary.source_ref, "required": True, "status": summary.status} for name, summary in summaries.items()],
        "source_hashes": source_hashes,
        "temporal_safety": {
            "point_in_time": not future_leakage_used,
            "future_leakage_used": future_leakage_used,
            "feature_date_lte_business_date": feature_date <= business_date,
            "implicit_latest_fallback_used": False,
            "previous_day_pm_artifact_copied": False,
        },
        "shadow_comparison": _shadow_comparison(positions),
        "production_consumer_connected": False,
        "existing_pm_authority_active": True,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    evidence = {
        "schema_version": "phase22_k_regime_event_position_management_evidence.v1",
        "business_date": business_date,
        "producer_result_status": producer_status,
        "positions_evaluated": len(positions),
        "reason_codes": payload["reason_codes"],
    }
    return payload, evidence


def validate_portfolio_policy_compatibility(
    path: Path | str | None,
    *,
    requested_business_date: str,
    production_use_requested: bool = False,
) -> dict[str, Any]:
    if path is None or not Path(path).is_file():
        return _missing_upstream("portfolio_policy", requested_business_date, str(path or ""))
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        portfolio_policy.validate_portfolio_policy_artifact(payload)
    except Exception as exc:
        return {
            **_missing_upstream("portfolio_policy", requested_business_date, str(path)),
            "status": INCOMPATIBLE_SCHEMA,
            "reason_codes": [f"schema_validation_failed:{exc}"],
        }
    expected_hash = str(payload.get("artifact_hash") or "")
    actual_hash = portfolio_policy.portfolio_policy_hash(payload)
    business_date = str(payload.get("business_date") or "")
    feature_date = str(payload.get("feature_date") or "")
    date_ok = business_date == requested_business_date and bool(feature_date) and feature_date <= business_date
    status = "COMPATIBLE_NOT_CONNECTED"
    if not date_ok:
        status = INCOMPATIBLE_DATE
    elif not expected_hash or expected_hash != actual_hash:
        status = INCOMPATIBLE_HASH
    else:
        status = compatibility_status_from_payload(
            payload,
            compatible_status="COMPATIBLE_NOT_CONNECTED",
            source_review_required=SOURCE_REVIEW_REQUIRED,
            source_blocked=SOURCE_BLOCKED,
        )
    reasons = list(payload.get("reason_codes") or [])
    if production_use_requested:
        reasons.append("production_use_rejected")
    return {
        "artifact_kind": "portfolio_policy",
        "artifact_path": str(path),
        "schema_version": str(payload.get("schema_version") or ""),
        "status": status,
        "schema_compatible": True,
        "shadow_read_allowed": status in {"COMPATIBLE_NOT_CONNECTED", SOURCE_NOT_ELIGIBLE, SOURCE_REVIEW_REQUIRED},
        "production_decision_allowed": False,
        "business_date": business_date,
        "feature_date": feature_date,
        "business_date_aligned": date_ok,
        "feature_date_point_in_time": date_ok and (payload.get("temporal_safety") or {}).get("future_leakage_used") is not True,
        "artifact_hash_valid": bool(expected_hash) and expected_hash == actual_hash,
        "lifecycle_status": str(payload.get("artifact_lifecycle_status") or ""),
        "producer_result_status": str(payload.get("producer_result_status") or ""),
        "runtime_consumer_eligibility": str(payload.get("runtime_consumer_eligibility") or ""),
        "reason_codes": sorted(set(reasons)),
    }


def validate_generation_binding(reference: PMAcceptedGenerationReference) -> dict[str, Any]:
    reason_codes: list[str] = []
    if reference.generation_status not in VALID_GENERATION_STATUSES:
        reason_codes.append("accepted_generation_status_invalid")
    if not reference.generation_id:
        reason_codes.append("accepted_generation_id_missing")
    if reference.model_generation_id != reference.generation_id:
        reason_codes.append("model_generation_mismatch")
    if reference.scaler_generation_id != reference.generation_id:
        reason_codes.append("scaler_generation_mismatch")
    model_hash_status = _file_hash_status(reference.model_reference, reference.model_hash)
    scaler_hash_status = _file_hash_status(reference.scaler_reference, reference.scaler_hash)
    if model_hash_status == "BLOCK":
        reason_codes.append("model_hash_mismatch")
    if scaler_hash_status == "BLOCK":
        reason_codes.append("scaler_hash_mismatch")
    if not reference.scaler_reference:
        reason_codes.append("unscaled_fallback_forbidden")
    return {
        "status": "BLOCK" if reason_codes else "PASS",
        "reason_codes": sorted(set(reason_codes)),
        "same_generation": reference.model_generation_id == reference.scaler_generation_id == reference.generation_id,
        "model_hash_status": model_hash_status,
        "scaler_hash_status": scaler_hash_status,
        "unscaled_fallback_used": False,
    }


def validate_position_management_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = {
        "schema_version",
        "business_date",
        "as_of",
        "feature_date",
        "artifact_lifecycle_status",
        "source_authority_status",
        "producer_result_status",
        "runtime_consumer_eligibility",
        "positions",
        "action_taxonomy",
        "intensity_taxonomy",
        "quantity_decided",
        "minimum_holding_decided",
        "cooldown_decided",
        "reason_codes",
        "upstream_artifacts",
        "accepted_generation_reference",
        "model_reference",
        "scaler_reference",
        "source_artifacts",
        "source_hashes",
        "temporal_safety",
    }
    errors.extend(f"required_field_missing:{field}" for field in sorted(required - set(payload)))
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported_schema_version")
    _enum_check(errors, payload, "artifact_lifecycle_status", ARTIFACT_LIFECYCLE_STATUSES)
    _enum_check(errors, payload, "source_authority_status", SOURCE_AUTHORITY_STATUSES)
    _enum_check(errors, payload, "producer_result_status", PRODUCER_RESULT_STATUSES)
    _enum_check(errors, payload, "runtime_consumer_eligibility", RUNTIME_CONSUMER_ELIGIBILITIES)
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS:
        errors.append("phase22_d_artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY:
        errors.append("phase22_d_runtime_consumer_eligibility_must_be_not_eligible")
    if payload.get("quantity_decided") is not False:
        errors.append("phase22_d_quantity_must_not_be_decided")
    is_regime_event_producer = payload.get("producer_version") == REGIME_EVENT_PRODUCER_VERSION
    if payload.get("minimum_holding_decided") is not (True if is_regime_event_producer else False):
        errors.append("phase22_d_minimum_holding_must_not_be_decided")
    if payload.get("cooldown_decided") is not (True if is_regime_event_producer else False):
        errors.append("phase22_d_cooldown_must_not_be_decided")
    for field in ("business_date", "feature_date"):
        try:
            _validate_iso_date(str(payload.get(field) or ""), field=field)
        except Exception:
            errors.append(f"invalid_date_format:{field}")
    try:
        _validate_rfc3339_timestamp(str(payload.get("as_of") or ""), field="as_of")
    except Exception:
        errors.append("invalid_timestamp_format:as_of")
    if str(payload.get("feature_date") or "9999-99-99") > str(payload.get("business_date") or ""):
        errors.append("feature_date_after_business_date")
    if not isinstance(payload.get("positions"), list):
        errors.append("positions_not_list")
    else:
        for index, position in enumerate(payload["positions"]):
            errors.extend(_validate_position(position, index=index))
    if not isinstance(payload.get("source_artifacts"), list) or not payload.get("source_artifacts"):
        errors.append("source_artifacts_missing")
    if not isinstance(payload.get("source_hashes"), list) or not payload.get("source_hashes"):
        errors.append("source_hashes_missing")
    temporal = payload.get("temporal_safety")
    if not isinstance(temporal, dict):
        errors.append("temporal_safety_not_object")
    else:
        if temporal.get("future_leakage_used") is True and payload.get("producer_result_status") != "BLOCK":
            errors.append("future_leakage_must_block")
        if temporal.get("implicit_latest_fallback_used") is not False:
            errors.append("implicit_latest_fallback_forbidden")
        if temporal.get("previous_day_pm_artifact_copied") is not False:
            errors.append("previous_day_pm_copy_forbidden")
    if errors:
        raise PositionManagementSchemaError(";".join(errors))
    return {"status": "PASS", "errors": []}


def verify_source_hashes(payload: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    missing = []
    for item in payload.get("source_hashes") or []:
        path_text = str(item.get("path") or "")
        expected = _strip_sha256(str(item.get("sha256") or ""))
        if not path_text:
            missing.append(path_text)
            continue
        path = Path(path_text)
        if not path.is_file():
            continue
        actual = sha256_file(path)
        if actual != expected:
            mismatches.append({"path": str(path), "expected": expected, "actual": actual})
    if mismatches:
        return {"status": "BLOCK", "reason": "source_hash_mismatch", "mismatches": mismatches, "missing": missing}
    if missing:
        return {"status": "REVIEW_REQUIRED", "reason": "source_missing", "mismatches": [], "missing": missing}
    return {"status": "PASS", "reason": "source_hashes_match", "mismatches": [], "missing": []}


def load_position_management_fixture(path: Path | str, *, for_production: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_position_management_artifact(payload)
    if payload.get("producer_result_status") == "BLOCK":
        raise PositionManagementConsumerError("BLOCK Position Management artifact is not fixture-consumable")
    if for_production:
        raise PositionManagementConsumerError("Phase22-D Position Management artifact is not production-consumable")
    if payload.get("runtime_consumer_eligibility") != "NOT_ELIGIBLE":
        raise PositionManagementConsumerError("Phase22-D Position Management must remain NOT_ELIGIBLE")
    return payload


def produced_but_not_consumed_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    upstream = payload.get("upstream_artifacts") if isinstance(payload.get("upstream_artifacts"), dict) else {}
    return {
        "schema_version": "phase22_d_produced_not_consumed_validation.v1",
        "position_management_artifact_produced": bool(payload),
        "position_management_schema_valid": True,
        "market_context_shadow_read": bool((upstream.get("market_context") or {}).get("shadow_read_allowed")),
        "corporate_event_shadow_read": bool((upstream.get("corporate_event") or {}).get("shadow_read_allowed")),
        "portfolio_policy_shadow_read": bool((upstream.get("portfolio_policy") or {}).get("shadow_read_allowed")),
        "position_management_production_consumer_connected": False,
        "existing_pm_authority_active": True,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
        "existing_pm_behavior_changed": False,
        "pm_action_changed": False,
        "pm_intensity_changed": False,
        "pm_model_changed": False,
        "pm_scaler_changed": False,
        "pm_feature_vector_changed": False,
        "sell_planning_quantity_authority_changed": False,
        "pending_changed": False,
        "submit_changed": False,
        "status": "PASS" if payload and payload.get("runtime_consumer_eligibility") == "NOT_ELIGIBLE" else "BLOCK",
    }


def position_management_hash(payload: dict[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if key != "artifact_hash"}
    return stable_payload_hash(clean)


def stable_payload_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _decide_regime_event_position(
    row: Mapping[str, Any],
    market: Mapping[str, Any],
    event_summary: Mapping[str, Any],
    policy: Mapping[str, Any],
    sizing: Mapping[str, Any],
    config: RegimeEventPMConfig,
    business_date: str,
) -> dict[str, Any]:
    code = str(row.get("security_code") or row.get("symbol") or "")
    reasons: list[str] = []
    market_state = _market_state(market)
    event_state, event_action, event_reason = _event_state(row, event_summary, config, business_date)
    technical_state = _technical_state(row, config)
    opportunity_state = _opportunity_state(row, config)
    holding_state = _holding_period_state(_int_value(row.get("holding_days"), 0), config)
    cooldown_state = _cooldown_state(row, config)
    reentry_state = _reentry_state(row, event_state, opportunity_state, technical_state, config)
    reasons.extend([f"market:{market_state}", f"event:{event_state}", f"technical:{technical_state}", f"opportunity:{opportunity_state}", f"holding:{holding_state}", f"cooldown:{cooldown_state}", f"reentry:{reentry_state}"])
    if event_reason:
        reasons.append(event_reason)

    action = "HOLD"
    priority = 60
    hard_invalidation = bool(row.get("hard_invalidation") or row.get("listed_status") == "DELISTING")
    if hard_invalidation:
        action, priority = "EXIT", 100
        reasons.append("hard_invalidation_exit")
    elif event_action in {"EXIT", "REDUCE"}:
        action, priority = event_action, 95 if event_action == "EXIT" else 80
        reasons.append("corporate_event_action")
    elif technical_state == "BREAKDOWN" or opportunity_state == "INVALIDATED":
        action, priority = "EXIT", 90
        reasons.append("technical_or_opportunity_invalidation")
    elif technical_state in {"WEAKENING", "VOLATILITY_EXPANSION"} or market_state in {"BEAR", "CORRECTION", "HIGH_VOLATILITY"} or opportunity_state == "WEAKENING":
        action, priority = "REDUCE", 75
        reasons.append("reduce_by_risk_or_deterioration")
    elif _add_allowed(row, market_state, event_state, technical_state, opportunity_state, cooldown_state, policy, sizing):
        action, priority = "ADD", 70
        reasons.append("add_by_regime_opportunity_sizing_alignment")
    elif market_state == "UNCERTAIN" or event_state == "SOURCE_UNAVAILABLE" or opportunity_state == "UNAVAILABLE" or technical_state == "UNAVAILABLE":
        action, priority = "UNRESOLVED", 10
        reasons.append("source_unavailable_no_hold_fallback")
    else:
        action, priority = "HOLD", 50
        reasons.append("hold_by_continuation_without_add_or_reduce")

    if action == "ADD" and event_state in {"EARNINGS_NEAR", "EVENT_RESTRICTED"}:
        action, priority = "HOLD", 65
        reasons.append("add_blocked_by_event_restriction")
    if action == "ADD" and market_state in {"BEAR", "CORRECTION", "HIGH_VOLATILITY"}:
        action, priority = "REDUCE" if technical_state != "HEALTHY" else "HOLD", 72
        reasons.append("add_blocked_by_regime")
    if action == "ADD" and cooldown_state != "CLEAR":
        action, priority = "HOLD", 62
        reasons.append("add_blocked_by_cooldown")

    intensity = _intensity(action, technical_state, market_state, config)
    current_weight = _float_value(row.get("current_weight"), 0.0)
    target_weight = _float_value(row.get("target_weight"), _float_value(sizing.get("target_weight"), current_weight))
    confidence = min(_float_value(row.get("confidence"), 0.8), _float_value(market.get("confidence"), 1.0), _float_value(policy.get("confidence"), 1.0))
    uncertainty = "LOW" if action != "UNRESOLVED" else "SOURCE_REVIEW_REQUIRED"
    return {
        "position_id": str(row.get("position_id") or row.get("current_position_reference") or f"phase22-k-{code}"),
        "security_code": code,
        "current_position_reference": str(row.get("current_position_reference") or row.get("position_id") or code),
        "market_context_state": market_state,
        "corporate_event_state": event_state,
        "opportunity_persistence_state": opportunity_state,
        "technical_health_state": technical_state,
        "holding_period_state": holding_state,
        "cooldown_state": cooldown_state,
        "reentry_state": reentry_state,
        "action": action,
        "intensity": intensity,
        "action_intensity": intensity,
        "action_priority": priority,
        "confidence": round(max(min(confidence, 1.0), 0.0), 6),
        "uncertainty": uncertainty,
        "reason_codes": sorted(set(reasons)),
        "quantity_decided": False,
        "target_weight_reference": str(row.get("target_weight_reference") or ""),
        "target_notional_reference": str(row.get("target_notional_reference") or ""),
        "legacy_pm_action": str(row.get("legacy_pm_action") or row.get("legacy_action") or ""),
        "lifecycle_reference": str(row.get("lifecycle_reference") or ""),
        "opportunity_reference": str(row.get("opportunity_reference") or ""),
        "market_context_reference": str(row.get("market_context_reference") or ""),
        "corporate_event_reference": str(row.get("corporate_event_reference") or ""),
        "portfolio_policy_reference": str(row.get("portfolio_policy_reference") or ""),
        "position_sizing_reference": str(row.get("position_sizing_reference") or ""),
        "current_weight": round(current_weight, 6),
        "target_weight": round(target_weight, 6),
    }


def _unresolved_regime_event_position(row: Mapping[str, Any], *, reason: str) -> dict[str, Any]:
    code = str(row.get("security_code") or row.get("symbol") or "")
    return {
        "position_id": str(row.get("position_id") or f"phase22-k-{code}"),
        "security_code": code,
        "current_position_reference": str(row.get("current_position_reference") or row.get("position_id") or code),
        "market_context_state": "UNRESOLVED",
        "corporate_event_state": "UNRESOLVED",
        "opportunity_persistence_state": "UNRESOLVED",
        "technical_health_state": "UNRESOLVED",
        "holding_period_state": "UNRESOLVED",
        "cooldown_state": "UNRESOLVED",
        "reentry_state": "UNRESOLVED",
        "action": "UNRESOLVED",
        "intensity": "UNRESOLVED",
        "action_intensity": "UNRESOLVED",
        "action_priority": 0,
        "confidence": 0.0,
        "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
        "reason_codes": [reason, "hold_fallback_forbidden"],
        "quantity_decided": False,
        "target_weight_reference": str(row.get("target_weight_reference") or ""),
        "target_notional_reference": str(row.get("target_notional_reference") or ""),
        "legacy_pm_action": str(row.get("legacy_pm_action") or ""),
        "lifecycle_reference": str(row.get("lifecycle_reference") or ""),
        "opportunity_reference": str(row.get("opportunity_reference") or ""),
        "market_context_reference": str(row.get("market_context_reference") or ""),
        "corporate_event_reference": str(row.get("corporate_event_reference") or ""),
        "portfolio_policy_reference": str(row.get("portfolio_policy_reference") or ""),
    }


def _market_state(market: Mapping[str, Any]) -> str:
    trend = str(market.get("trend_regime") or "UNCERTAIN").upper()
    volatility = str(market.get("volatility_regime") or "").upper()
    uncertainty = str(market.get("uncertainty") or "").upper()
    if uncertainty in {"HIGH", "UPSTREAM_REVIEW_REQUIRED", "THRESHOLD_OR_SOURCE_REVIEW_REQUIRED"}:
        return "UNCERTAIN"
    if volatility == "HIGH":
        return "HIGH_VOLATILITY"
    return trend if trend in {"BULL", "RANGE", "BEAR", "CORRECTION", "RECOVERY"} else "UNCERTAIN"


def _event_state(row: Mapping[str, Any], event_summary: Mapping[str, Any], config: RegimeEventPMConfig, business_date: str) -> tuple[str, str, str]:
    if str(event_summary.get("coverage_status") or "AVAILABLE").upper() in {"SOURCE_UNAVAILABLE", "REVIEW_REQUIRED", "UNAVAILABLE"}:
        return "SOURCE_UNAVAILABLE", "", "corporate_event_source_unavailable"
    announced_at = str(row.get("event_announced_at") or event_summary.get("announced_at") or business_date)
    if announced_at > business_date:
        return "FUTURE_ANNOUNCEMENT_LEAKAGE", "EXIT", "future_event_knowledge_leakage"
    event_type = str(row.get("event_type") or event_summary.get("event_type") or "NONE").upper()
    days = _int_value(row.get("days_to_earnings_business", event_summary.get("days_to_earnings_business")), 999)
    rules = config.corporate_event_rules
    if event_type in {"DELISTING", "TOB"}:
        return event_type, str(rules.get(f"{event_type.lower()}_action") or "EXIT"), f"{event_type.lower()}_hard_event"
    if event_type == "MERGER":
        return "EVENT_RESTRICTED", str(rules.get("merger_action") or "REDUCE"), "merger_event_restriction"
    if event_type == "SPLIT":
        return "SPLIT_ANNOUNCED", str(rules.get("split_action") or "HOLD"), "split_announced_no_quantity_change"
    if 0 <= days <= int(rules.get("earnings_near_business_days") or 3):
        return "EARNINGS_NEAR", str(rules.get("earnings_near_default_action") or "HOLD"), "earnings_near_add_restricted"
    if days < 999:
        return "EARNINGS_DISTANT", "", "earnings_distant"
    return "NONE", "", ""


def _technical_state(row: Mapping[str, Any], config: RegimeEventPMConfig) -> str:
    rules = config.technical_health_rules
    if row.get("technical_status") in {"MISSING", "REVIEW_REQUIRED"}:
        return "UNAVAILABLE"
    close_ma = _float_value(row.get("trend_close_over_ma_20d"), 1.0)
    momentum = _float_value(row.get("price_momentum_return_20d"), 0.0)
    vol = _float_value(row.get("volatility_return_std_20d"), 0.0)
    if close_ma < float(rules.get("breakdown_close_over_ma_20d", 0.97)):
        return "BREAKDOWN"
    if vol >= float(rules.get("volatility_expansion_threshold", 0.06)):
        return "VOLATILITY_EXPANSION"
    if momentum <= float(rules.get("weak_momentum_20d", -0.02)):
        return "WEAKENING"
    if momentum >= float(rules.get("healthy_min_momentum_20d", 0.03)) and close_ma >= 1.0:
        return "HEALTHY"
    return "NEUTRAL"


def _opportunity_state(row: Mapping[str, Any], config: RegimeEventPMConfig) -> str:
    if row.get("opportunity_status") in {"MISSING", "REVIEW_REQUIRED"}:
        return "UNAVAILABLE"
    score = row.get("opportunity_score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return "UNAVAILABLE"
    rules = config.opportunity_persistence_rules
    if float(score) <= float(rules.get("invalidated_score_max", 0.15)):
        return "INVALIDATED"
    if float(score) <= float(rules.get("weak_score_max", 0.35)):
        return "WEAKENING"
    if float(score) >= float(rules.get("strong_score_min", 0.7)):
        return "STRONG"
    return "NEUTRAL"


def _holding_period_state(days: int, config: RegimeEventPMConfig) -> str:
    rules = config.holding_period_rules
    if days <= int(rules.get("new_max_days", 2)):
        return "NEW"
    if days <= int(rules.get("early_max_days", 7)):
        return "EARLY"
    if days <= int(rules.get("mature_max_days", 30)):
        return "MATURE"
    if days <= int(rules.get("extended_max_days", 60)):
        return "EXTENDED"
    return "STALE"


def _cooldown_state(row: Mapping[str, Any], config: RegimeEventPMConfig) -> str:
    rules = config.cooldown_rules
    if _int_value(row.get("days_since_exit"), 999) < int(rules.get("post_exit_reentry_cooldown_business_days", 10)):
        return "POST_EXIT_REENTRY_COOLDOWN"
    if _int_value(row.get("days_since_reduce"), 999) < int(rules.get("post_reduce_add_cooldown_business_days", 5)):
        return "POST_REDUCE_ADD_COOLDOWN"
    if _int_value(row.get("days_since_add"), 999) < int(rules.get("add_cooldown_business_days", 3)):
        return "ADD_COOLDOWN"
    return "CLEAR"


def _reentry_state(row: Mapping[str, Any], event_state: str, opportunity_state: str, technical_state: str, config: RegimeEventPMConfig) -> str:
    if _int_value(row.get("days_since_exit"), 999) < int(config.cooldown_rules.get("post_exit_reentry_cooldown_business_days", 10)):
        return "COOLDOWN_ACTIVE"
    if event_state in {"EARNINGS_NEAR", "EVENT_RESTRICTED", "SOURCE_UNAVAILABLE"}:
        return "EVENT_RESTRICTED"
    if opportunity_state != "STRONG" or technical_state not in {"HEALTHY", "NEUTRAL"}:
        return "NOT_RECOVERED"
    return "ELIGIBLE"


def _add_allowed(row: Mapping[str, Any], market_state: str, event_state: str, technical_state: str, opportunity_state: str, cooldown_state: str, policy: Mapping[str, Any], sizing: Mapping[str, Any]) -> bool:
    if market_state in {"BEAR", "CORRECTION", "HIGH_VOLATILITY", "UNCERTAIN"}:
        return False
    if event_state not in {"NONE", "EARNINGS_DISTANT"}:
        return False
    if cooldown_state != "CLEAR":
        return False
    if opportunity_state != "STRONG" or technical_state != "HEALTHY":
        return False
    if str(policy.get("add_permission") or policy.get("entry_posture") or "ALLOWED").upper() in {"FORBIDDEN", "BLOCKED", "WITHHOLD"}:
        return False
    target = _float_value(row.get("target_weight"), _float_value(sizing.get("target_weight"), 0.0))
    current = _float_value(row.get("current_weight"), 0.0)
    return target > current


def _intensity(action: str, technical_state: str, market_state: str, config: RegimeEventPMConfig) -> str:
    table = config.action_intensity.get(action) or {}
    if action == "REDUCE" and (technical_state == "BREAKDOWN" or market_state in {"BEAR", "CORRECTION"}):
        return str(table.get("strong") or "STRONG")
    if action == "ADD" and technical_state == "HEALTHY" and market_state in {"BULL", "RECOVERY"}:
        return str(table.get("strong") or "MEDIUM")
    return str(table.get("default") or ("NONE" if action in {"HOLD", "EXIT"} else "UNRESOLVED"))


def _shadow_comparison(positions: list[dict[str, Any]]) -> dict[str, Any]:
    differences = []
    for item in positions:
        legacy = str(item.get("legacy_pm_action") or "")
        dynamic = str(item.get("action") or "")
        if legacy and dynamic and legacy != dynamic:
            differences.append({"security_code": item.get("security_code"), "legacy_pm_action": legacy, "dynamic_pm_action": dynamic})
    return {
        "legacy_pm_action_count": sum(1 for item in positions if item.get("legacy_pm_action")),
        "dynamic_pm_action_count": len(positions),
        "action_differences": differences,
        "legacy_add_intent": any(item.get("legacy_pm_action") == "ADD" for item in positions),
        "dynamic_add_intent": any(item.get("action") == "ADD" for item in positions),
        "legacy_reduce_intent": any(item.get("legacy_pm_action") == "REDUCE" for item in positions),
        "dynamic_reduce_intent": any(item.get("action") == "REDUCE" for item in positions),
        "legacy_exit_intent": any(item.get("legacy_pm_action") == "EXIT" for item in positions),
        "dynamic_exit_intent": any(item.get("action") == "EXIT" for item in positions),
        "would_change_add_planning": any(item.get("action") == "ADD" for item in positions),
        "would_change_sell_planning": any(item.get("action") in {"REDUCE", "EXIT"} for item in positions),
        "runtime_behavior_changed": False,
    }


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise PositionManagementConfigError(f"{field} required")
    return value


def _nested_int_map(payload: Mapping[str, Any], field: str) -> dict[str, dict[str, int]]:
    obj = payload.get(field)
    if not isinstance(obj, dict):
        raise PositionManagementConfigError(f"{field} required")
    return {str(k): {str(kk): int(vv) for kk, vv in dict(v).items()} for k, v in obj.items() if isinstance(v, dict)}


def _numeric_map(payload: Mapping[str, Any], field: str) -> dict[str, float]:
    obj = payload.get(field)
    if not isinstance(obj, dict):
        raise PositionManagementConfigError(f"{field} required")
    return {str(k): float(v) for k, v in obj.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


def _int_map(payload: Mapping[str, Any], field: str) -> dict[str, int]:
    obj = payload.get(field)
    if not isinstance(obj, dict):
        raise PositionManagementConfigError(f"{field} required")
    return {str(k): int(v) for k, v in obj.items() if isinstance(v, int) and not isinstance(v, bool)}


def _float_value(value: Any, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def _int_value(value: Any, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return int(value)


def _normalized_pm_action(decision: Mapping[str, Any]) -> str:
    for field in ("action", "decision", "decision_type"):
        value = _normalized_text(decision.get(field))
        if value:
            return value
    return "UNRESOLVED"


def _normalized_pm_decision_ref(decision: Mapping[str, Any]) -> str:
    return str(decision.get("decision_id") or decision.get("pm_decision_id") or "")


def _pm_action_field_conflicts(decision: Mapping[str, Any]) -> list[str]:
    values = {
        field: value
        for field in ("action", "decision", "decision_type")
        if (value := _normalized_text(decision.get(field)))
    }
    supported = {field: value for field, value in values.items() if value in PM_ACTIONS}
    if len(set(supported.values())) <= 1:
        return []
    return [
        "pm_action_field_conflict:"
        + ",".join(f"{field}={value}" for field, value in supported.items())
    ]


def _attach_strategy_intelligence_positions(
    positions: list[dict[str, Any]],
    *,
    strategy_intelligence_artifact_path: Path | str | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not positions:
        return positions, []
    if strategy_intelligence_artifact_path is None:
        return positions, ["strategy_intelligence_not_connected"]
    if not Path(strategy_intelligence_artifact_path).is_file():
        return [
            {
                **position,
                "action": "UNRESOLVED",
                "intensity": "UNRESOLVED",
                "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
                "strategy_intelligence_consumer_status": "MISSING_ARTIFACT",
                "reason_codes": sorted(set([*list(position.get("reason_codes") or []), "strategy_intelligence_missing_fail_closed"])),
            }
            for position in positions
        ], ["strategy_intelligence_missing_fail_closed"]
    payload = strategy_intelligence.load_strategy_intelligence_artifact(strategy_intelligence_artifact_path)
    by_symbol = strategy_intelligence.symbol_intelligence_by_symbol(payload)
    updated: list[dict[str, Any]] = []
    reasons: list[str] = []
    for position in positions:
        code = str(position.get("security_code") or position.get("symbol") or "").strip()
        evidence = by_symbol.get(code)
        if not evidence:
            patched = {
                **position,
                "action": "UNRESOLVED",
                "intensity": "UNRESOLVED",
                "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
                "strategy_intelligence_consumer_status": "MISSING_SYMBOL_EVIDENCE",
                "reason_codes": sorted(set([*list(position.get("reason_codes") or []), "strategy_intelligence_symbol_missing_fail_closed"])),
            }
            updated.append(patched)
            reasons.append(f"strategy_intelligence_symbol_missing:{code}")
            continue
        action = str(position.get("action") or "").upper()
        cq = evidence.get("continuation_quality") if isinstance(evidence.get("continuation_quality"), Mapping) else {}
        risk = evidence.get("downside_risk") if isinstance(evidence.get("downside_risk"), Mapping) else {}
        profit = evidence.get("profit_protection_evidence") if isinstance(evidence.get("profit_protection_evidence"), Mapping) else {}
        lifecycle = evidence.get("lifecycle_context") if isinstance(evidence.get("lifecycle_context"), Mapping) else {}
        hold_evidence = _structured_hold_worthiness_evidence(lifecycle=lifecycle, cq=cq, risk=risk, profit=profit)
        add_evidence = _structured_add_worthiness_evidence(lifecycle=lifecycle, cq=cq, risk=risk, profit=profit)
        position_reasons = list(position.get("reason_codes") or [])
        if action == "ADD" and add_evidence["status"] != "PASS":
            action = "HOLD"
            position_reasons.append("structured_add_worthiness_no_add")
        elif action == "HOLD" and hold_evidence["status"] != "PASS":
            action = "UNRESOLVED"
            position_reasons.append("structured_hold_worthiness_review_required")
        elif action in {"REDUCE", "EXIT"}:
            position_reasons.append("strategy_intelligence_sell_side_evidence_connected")
        elif action == "HOLD":
            position_reasons.append("structured_hold_worthiness_pass")
        patched = {
            **position,
            "action": action,
            "intensity": "NONE" if action == "HOLD" else position.get("intensity"),
            "position_campaign_id": str(lifecycle.get("position_campaign_id") or position.get("position_campaign_id") or ""),
            "strategy_intelligence_consumer_status": "CONNECTED",
            "strategy_intelligence_artifact_path": str(strategy_intelligence_artifact_path),
            "strategy_intelligence_artifact_hash": str(payload.get("artifact_hash") or ""),
            "strategy_intelligence_continuation_quality_status": str(cq.get("status") or ""),
            "strategy_intelligence_downside_risk_status": str(risk.get("status") or ""),
            "strategy_intelligence_profit_protection_status": str(profit.get("status") or ""),
            "strategy_intelligence_campaign_id": str(lifecycle.get("position_campaign_id") or ""),
            "strategy_intelligence_campaign_age_business_days": lifecycle.get("campaign_age_business_days"),
            "strategy_intelligence_current_campaign_relative_return": lifecycle.get("current_campaign_relative_return"),
            "strategy_intelligence_observed_campaign_mfe": lifecycle.get("observed_campaign_mfe"),
            "strategy_intelligence_observed_giveback": lifecycle.get("observed_giveback"),
            "strategy_intelligence_hold_worthiness_evidence": hold_evidence,
            "strategy_intelligence_add_worthiness_evidence": add_evidence,
            "strategy_intelligence_profit_protection_evidence": dict(profit),
            "strategy_intelligence_not_action_authority": True,
            "strategy_intelligence_production_evidence": True,
            "reason_codes": sorted(set(position_reasons)),
        }
        updated.append(patched)
    return updated, sorted(set(reasons))


def _structured_hold_worthiness_evidence(
    *,
    lifecycle: Mapping[str, Any],
    cq: Mapping[str, Any],
    risk: Mapping[str, Any],
    profit: Mapping[str, Any],
) -> dict[str, Any]:
    campaign_status = str(lifecycle.get("campaign_identity_authority_status") or "").upper()
    cq_status = str(cq.get("status") or "").upper()
    risk_status = str(risk.get("status") or "").upper()
    reasons: list[str] = []
    if campaign_status != "COMPLETE":
        reasons.append("canonical_campaign_identity_missing")
    if cq_status != "PASS":
        reasons.append("continuation_quality_not_pass")
    if risk_status in {"BLOCK", "FAIL_CLOSED"}:
        reasons.append("downside_risk_blocks_hold")
    status = "PASS" if not reasons else "REVIEW_REQUIRED"
    return {
        "schema_version": "phase30_ac_hold_worthiness_evidence.v1",
        "status": status,
        "campaign_identity_authority_status": campaign_status,
        "campaign_age_business_days": lifecycle.get("campaign_age_business_days"),
        "current_campaign_relative_return": lifecycle.get("current_campaign_relative_return"),
        "observed_campaign_mfe": lifecycle.get("observed_campaign_mfe"),
        "observed_giveback": lifecycle.get("observed_giveback"),
        "add_history_summary": lifecycle.get("add_history_summary") or {},
        "reduce_history_summary": lifecycle.get("reduce_history_summary") or {},
        "continuation_quality_status": cq_status,
        "downside_risk_status": risk_status,
        "profit_protection_status": str(profit.get("status") or ""),
        "profit_protection_evidence_used": True,
        "not_action_authority": True,
        "reason_codes": sorted(set(reasons)),
        "future_information_used": False,
    }


def _structured_add_worthiness_evidence(
    *,
    lifecycle: Mapping[str, Any],
    cq: Mapping[str, Any],
    risk: Mapping[str, Any],
    profit: Mapping[str, Any],
) -> dict[str, Any]:
    campaign_status = str(lifecycle.get("campaign_identity_authority_status") or "").upper()
    cq_status = str(cq.get("status") or "").upper()
    risk_status = str(risk.get("status") or "").upper()
    add_history = lifecycle.get("add_history_summary") if isinstance(lifecycle.get("add_history_summary"), Mapping) else {}
    reduce_history = lifecycle.get("reduce_history_summary") if isinstance(lifecycle.get("reduce_history_summary"), Mapping) else {}
    reasons: list[str] = []
    if campaign_status != "COMPLETE":
        reasons.append("canonical_campaign_identity_missing")
    if cq_status != "PASS":
        reasons.append("incremental_continuation_quality_not_pass")
    if risk_status not in {"PASS", "REVIEW_REQUIRED", ""}:
        reasons.append("downside_risk_blocks_add")
    if int(add_history.get("event_count") or 0) >= 5:
        reasons.append("prior_add_history_limits_incremental_add")
    if int(reduce_history.get("event_count") or 0) > 0:
        reasons.append("prior_reduce_history_requires_add_review")
    status = "PASS" if not reasons else "NO_ADD"
    return {
        "schema_version": "phase30_ac_add_worthiness_evidence.v1",
        "status": status,
        "campaign_identity_authority_status": campaign_status,
        "campaign_age_business_days": lifecycle.get("campaign_age_business_days"),
        "current_campaign_relative_return": lifecycle.get("current_campaign_relative_return"),
        "observed_campaign_mfe": lifecycle.get("observed_campaign_mfe"),
        "observed_giveback": lifecycle.get("observed_giveback"),
        "add_history_summary": add_history,
        "reduce_history_summary": reduce_history,
        "continuation_quality_status": cq_status,
        "downside_risk_status": risk_status,
        "profit_protection_status": str(profit.get("status") or ""),
        "hold_worthy_equals_add_worthy": False,
        "not_action_authority": True,
        "reason_codes": sorted(set(reasons)),
        "future_information_used": False,
    }


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().upper()


def _positions_from_existing_decisions(
    decisions: Iterable[Mapping[str, Any]],
    *,
    business_date: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    positions: list[dict[str, Any]] = []
    reasons: list[str] = []
    for index, decision in enumerate(decisions, start=1):
        action = _normalized_pm_action(decision)
        action_conflicts = _pm_action_field_conflicts(decision)
        security_code = str(decision.get("security_code") or decision.get("symbol") or decision.get("code") or "").strip()
        decision_ref = _normalized_pm_decision_ref(decision)
        position_id = str(decision.get("position_id") or decision_ref or f"phase22-d-shadow-{business_date}-{security_code or index}")
        intensity = str(decision.get("intensity") or decision.get("reduce_intensity") or ("NONE" if action in {"HOLD", "EXIT"} else "UNRESOLVED")).upper()
        if action not in PM_ACTIONS:
            reasons.append(f"invalid_action:{security_code or index}")
            action = "UNRESOLVED"
        if intensity not in PM_INTENSITIES:
            reasons.append(f"invalid_intensity:{security_code or index}")
            intensity = "UNRESOLVED"
        reason_codes = [*_reason_codes(decision), *action_conflicts]
        position = {
            "position_id": position_id,
            "security_code": security_code,
            "action": action,
            "intensity": intensity,
            "confidence": _confidence(decision),
            "uncertainty": str(decision.get("uncertainty") or "UPSTREAM_REVIEW_REQUIRED"),
            "reason_codes": reason_codes,
            "lifecycle_reference": str(decision.get("lifecycle_reference") or decision.get("decision_trace_path") or ""),
            "opportunity_reference": str(decision.get("opportunity_reference") or decision.get("opportunity_path") or ""),
            "market_context_reference": str(decision.get("market_context_reference") or ""),
            "corporate_event_reference": str(decision.get("corporate_event_reference") or ""),
            "portfolio_policy_reference": str(decision.get("portfolio_policy_reference") or ""),
            "feature_vector_hash": str(decision.get("feature_vector_hash") or ""),
            "source_pm_decision_ref": decision_ref,
        }
        positions.append(position)
    return positions, reasons


def _positions_from_runtime_current(
    current_rows: Iterable[Mapping[str, Any]],
    *,
    existing_pm_decisions: Iterable[Mapping[str, Any]],
    business_date: str,
    accepted_generation_reference: PMAcceptedGenerationReference,
) -> tuple[list[dict[str, Any]], list[str]]:
    decisions_by_symbol = {
        str(row.get("security_code") or row.get("symbol") or row.get("code") or "").strip(): row
        for row in existing_pm_decisions
        if str(row.get("security_code") or row.get("symbol") or row.get("code") or "").strip()
    }
    positions: list[dict[str, Any]] = []
    reasons: list[str] = []
    for index, row in enumerate(current_rows, start=1):
        symbol = str(row.get("security_code") or row.get("symbol") or row.get("code") or row.get("issue_code") or "").strip()
        quantity = _float_value(row.get("quantity"), 0.0)
        if not symbol:
            reasons.append(f"runtime_current_symbol_missing:{index}")
            continue
        if quantity <= 0:
            reasons.append(f"runtime_current_non_positive_quantity:{symbol}")
            continue
        decision = decisions_by_symbol.get(symbol, {})
        action = _normalized_pm_action(decision)
        action_conflicts = _pm_action_field_conflicts(decision)
        intensity = str(decision.get("intensity") or decision.get("reduce_intensity") or ("NONE" if action in {"HOLD", "EXIT"} else "UNRESOLVED")).upper()
        if action not in PM_ACTIONS:
            reasons.append(f"invalid_action:{symbol}")
            action = "UNRESOLVED"
        if intensity not in PM_INTENSITIES:
            reasons.append(f"invalid_intensity:{symbol}")
            intensity = "UNRESOLVED"
        position_id = str(row.get("position_id") or row.get("current_position_reference") or f"runtime-current-{business_date}-{symbol}")
        lifecycle_id = str(
            row.get("position_lifecycle_id")
            or row.get("lifecycle_reference")
            or row.get("source_execution_id")
            or row.get("acquired_at")
            or position_id
        )
        reason_codes = [*_reason_codes(decision), *action_conflicts] if decision else ["runtime_current_position_requires_strategy_pm_evaluation"]
        positions.append(
            {
                "position_id": position_id,
                "security_code": symbol,
                "current_position_reference": str(row.get("current_position_reference") or position_id),
                "action": action,
                "intensity": intensity,
                "confidence": _confidence(decision) if decision else 0.0,
                "uncertainty": str(decision.get("uncertainty") or "UPSTREAM_REVIEW_REQUIRED"),
                "reason_codes": reason_codes,
                "lifecycle_reference": lifecycle_id,
                "opportunity_reference": str(decision.get("opportunity_reference") or row.get("opportunity_reference") or symbol),
                "market_context_reference": str(decision.get("market_context_reference") or ""),
                "corporate_event_reference": str(decision.get("corporate_event_reference") or ""),
                "portfolio_policy_reference": str(decision.get("portfolio_policy_reference") or ""),
                "feature_vector_hash": str(decision.get("feature_vector_hash") or row.get("technical_feature_hash") or ""),
                "source_pm_decision_ref": _normalized_pm_decision_ref(decision),
                "adapter_source": "runtime_current_position_adapter",
                "adapter_contract_version": "runtime_current_holdings_to_strategy_pm.v1",
                "adapter_source_contract": {
                    "position_id": position_id,
                    "symbol": symbol,
                    "quantity": quantity,
                    "average_price": _float_value(row.get("average_price"), 0.0),
                    "acquired_at": str(row.get("acquired_at") or row.get("opened_at") or ""),
                    "business_date": business_date,
                    "position_state_as_of": str(row.get("position_state_as_of") or row.get("as_of") or business_date),
                    "valuation_date": str(row.get("valuation_date") or row.get("valuation_as_of") or row.get("as_of") or business_date),
                    "position_lifecycle_id": lifecycle_id,
                    "accepted_generation_id": accepted_generation_reference.generation_id,
                    "accepted_generation_hash": accepted_generation_reference.accepted_generation_hash,
                    "technical_features_join_key": {
                        "code": symbol,
                        "target_date": business_date,
                    },
                    "direct_position_copy_used": False,
                },
            }
        )
    return positions, reasons


def _validate_position(position: Any, *, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(position, dict):
        return [f"position_not_object:{index}"]
    required = {
        "position_id",
        "security_code",
        "action",
        "intensity",
        "confidence",
        "uncertainty",
        "reason_codes",
        "lifecycle_reference",
        "opportunity_reference",
        "market_context_reference",
        "corporate_event_reference",
        "portfolio_policy_reference",
    }
    errors.extend(f"position_required_field_missing:{index}:{field}" for field in sorted(required - set(position)))
    if position.get("action") not in PM_ACTIONS:
        errors.append(f"invalid_action:{index}")
    if position.get("intensity") not in PM_INTENSITIES:
        errors.append(f"invalid_intensity:{index}")
    if not position.get("position_id"):
        errors.append(f"position_id_empty:{index}")
    if not position.get("security_code"):
        errors.append(f"security_code_empty:{index}")
    confidence = position.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= float(confidence) <= 1:
        errors.append(f"invalid_confidence:{index}")
    if not isinstance(position.get("reason_codes"), list):
        errors.append(f"reason_codes_not_list:{index}")
    for field in sorted(FORBIDDEN_QUANTITY_FIELDS & set(position)):
        errors.append(f"quantity_field_forbidden:{index}:{field}")
    return errors


def _summary_aligned(summary: PMSourceSummary, *, business_date: str) -> bool:
    return summary.business_date == business_date and bool(summary.feature_date) and summary.feature_date <= business_date


def _missing_upstream(kind: str, requested_business_date: str, path: str) -> dict[str, Any]:
    return {
        "artifact_kind": kind,
        "artifact_path": path,
        "schema_version": "",
        "status": SOURCE_MISSING,
        "schema_compatible": False,
        "shadow_read_allowed": False,
        "production_decision_allowed": False,
        "business_date": requested_business_date,
        "feature_date": "",
        "business_date_aligned": False,
        "feature_date_point_in_time": False,
        "artifact_hash_valid": False,
        "reason_codes": ["artifact_missing"],
    }


def _file_hash_status(path_text: str, expected_hash: str) -> str:
    if not path_text or not expected_hash:
        return "BLOCK"
    path = Path(path_text)
    if not path.is_file():
        return "PASS"
    return "PASS" if sha256_file(path) == _strip_sha256(expected_hash) else "BLOCK"


def _confidence(decision: Mapping[str, Any]) -> float:
    value = decision.get("confidence", decision.get("selected_action_score", decision.get("action_score", 0.0)))
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric < 0:
        return 0.0
    if numeric > 1:
        return 1.0
    return round(numeric, 8)


def _reason_codes(decision: Mapping[str, Any]) -> list[str]:
    existing = decision.get("reason_codes", decision.get("decision_reason_codes"))
    if isinstance(existing, list):
        return [str(item) for item in existing if str(item)]
    text = str(decision.get("reason") or decision.get("action_reason") or decision.get("exit_reason") or decision.get("decision") or "")
    return [part.strip() for part in text.replace(";", "|").split("|") if part.strip()]


def _enum_check(errors: list[str], payload: dict[str, Any], field: str, allowed: set[str]) -> None:
    if payload.get(field) not in allowed:
        errors.append(f"invalid_enum:{field}")


def _validate_iso_date(value: str, *, field: str) -> None:
    try:
        parsed = date.fromisoformat(value)
    except Exception as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must be normalized YYYY-MM-DD")


def _validate_rfc3339_timestamp(value: str, *, field: str) -> None:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except Exception as exc:
        raise ValueError(f"{field} must be RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")


def _strip_sha256(value: str) -> str:
    return value[7:] if value.startswith("sha256:") else value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
