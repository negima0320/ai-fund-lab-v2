"""Legacy PM ADD compatibility observer for Runtime v2 planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetPosition, CurrentAssetState
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingOrderPlan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy
from ai_fund_lab_v2.runtime_v2.cash_exposure_authority import CashExposureAuthority
from ai_fund_lab_v2.runtime_v2.position_sizing_authority import PositionSizingAuthority
from ai_fund_lab_v2.runtime_v2.safety_decision import RuntimeSafetyDecision

LEGACY_ADD_COMPATIBILITY_SCHEMA_VERSION = "legacy_pm_add_compatibility.v1"
LEGACY_ADD_ARTIFACT_TYPE = "legacy_pm_add_compatibility"
LEGACY_ADD_MIGRATION_STATE = "NON_DECISION_COMPATIBILITY"
LEGACY_ADD_AUTHORITY_MODE = "COMPATIBILITY_TELEMETRY_ONLY"
LEGACY_ADD_DECISION_EFFECT = "NONE"
LEGACY_ADD_NO_AUTHORITY = "NONE"
LEGACY_ADD_COMPATIBILITY_REASON = "LEGACY_ADD_NON_DECISION_COMPATIBILITY"
LEGACY_ADD_DEDUP_FIELDS = ("run_id", "business_date", "symbol", "position_campaign_id", "decision_id")


@dataclass(frozen=True)
class AddConsumerResult:
    status: str
    reason: str
    accepted_items: tuple[PendingOrderItem, ...]
    rejected: tuple[dict[str, Any], ...]
    requested_count: int
    accepted_count: int
    rejected_count: int
    compatibility: tuple[dict[str, Any], ...] = ()
    compatibility_artifact: dict[str, Any] | None = None
    migration_state: str = ""
    decision_effect: str = ""
    quantity_authority: str = ""
    pending_authority: str = ""
    approval_authority: str = ""
    submit_authority: str = ""
    telemetry_only: bool = False
    double_authority_guard_status: str = ""

    def to_evidence(self) -> dict[str, Any]:
        return {
            "add_consumer_status": self.status,
            "add_consumer_reason": self.reason,
            "requested_count": self.requested_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "accepted_pending_item_ids": [item.pending_item_id for item in self.accepted_items],
            "rejected": list(self.rejected),
            "migration_state": self.migration_state,
            "decision_effect": self.decision_effect,
            "quantity_authority": self.quantity_authority,
            "pending_authority": self.pending_authority,
            "approval_authority": self.approval_authority,
            "submit_authority": self.submit_authority,
            "telemetry_only": self.telemetry_only,
            "compatibility_count": len(self.compatibility),
            "compatibility": list(self.compatibility),
            "compatibility_artifact": dict(self.compatibility_artifact or {}),
            "double_authority_guard_status": self.double_authority_guard_status,
        }


def build_add_pending_items(
    *,
    add_decisions: Sequence[Any],
    asset_state: CurrentAssetState,
    current_positions: Mapping[str, CurrentAssetPosition],
    existing_buy_pending: PendingOrderPlan | None,
    business_date: str,
    target_session_date: str,
    environment: str,
    capital_deployment_policy: CapitalDeploymentPolicy | None,
    safety_decision: RuntimeSafetyDecision | None,
    cash_exposure_authority: CashExposureAuthority | None = None,
    position_sizing_authorities: Mapping[str, PositionSizingAuthority] | None = None,
) -> AddConsumerResult:
    add_candidates = tuple(
        decision
        for decision in add_decisions
        if str(getattr(decision, "source_decision", "") or "").upper() == "ADD"
    )
    if not add_candidates:
        return AddConsumerResult("NOT_REQUIRED", "ADD decision missing", (), (), 0, 0, 0)
    artifact = build_legacy_add_compatibility_artifact(
        add_decisions=add_candidates,
        business_date=business_date,
        target_session_date=target_session_date,
        environment=environment,
    )
    guard = evaluate_legacy_add_double_authority_guard(artifact)
    status = "BLOCKED" if guard["status"] == "BLOCKED" else LEGACY_ADD_MIGRATION_STATE
    return AddConsumerResult(
        status,
        LEGACY_ADD_COMPATIBILITY_REASON,
        (),
        (),
        len(add_candidates),
        0,
        0,
        compatibility=tuple(artifact["compatibility"]),
        compatibility_artifact=artifact,
        migration_state=LEGACY_ADD_MIGRATION_STATE,
        decision_effect=LEGACY_ADD_DECISION_EFFECT,
        quantity_authority=LEGACY_ADD_NO_AUTHORITY,
        pending_authority=LEGACY_ADD_NO_AUTHORITY,
        approval_authority=LEGACY_ADD_NO_AUTHORITY,
        submit_authority=LEGACY_ADD_NO_AUTHORITY,
        telemetry_only=True,
        double_authority_guard_status=str(guard["status"]),
    )


def build_legacy_add_compatibility_artifact(
    *,
    add_decisions: Sequence[Any],
    business_date: str,
    target_session_date: str = "",
    environment: str = "",
    run_id: str = "",
    accepted_generation: str = "",
    canonical_position_intent_ref: str = "",
    canonical_target_portfolio_decision_ref: str = "",
) -> dict[str, Any]:
    records = tuple(
        _compatibility_record(
            decision,
            business_date=business_date,
            target_session_date=target_session_date,
            environment=environment,
            run_id=run_id,
            accepted_generation=accepted_generation,
            canonical_position_intent_ref=canonical_position_intent_ref,
            canonical_target_portfolio_decision_ref=canonical_target_portfolio_decision_ref,
        )
        for decision in add_decisions
        if str(getattr(decision, "source_decision", "") or "").upper() == "ADD"
    )
    guard = evaluate_legacy_add_double_authority_guard({"compatibility": list(records)})
    return {
        "schema_version": LEGACY_ADD_COMPATIBILITY_SCHEMA_VERSION,
        "artifact_type": LEGACY_ADD_ARTIFACT_TYPE,
        "migration_state": LEGACY_ADD_MIGRATION_STATE,
        "authority_mode": LEGACY_ADD_AUTHORITY_MODE,
        "decision_effect": LEGACY_ADD_DECISION_EFFECT,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "environment": environment,
        "run_id": run_id,
        "accepted_generation": accepted_generation,
        "quantity_authority": LEGACY_ADD_NO_AUTHORITY,
        "pending_authority": LEGACY_ADD_NO_AUTHORITY,
        "approval_authority": LEGACY_ADD_NO_AUTHORITY,
        "submit_authority": LEGACY_ADD_NO_AUTHORITY,
        "telemetry_only": True,
        "compatibility_count": len(records),
        "compatibility": list(records),
        "double_authority_guard": guard,
        "review_status": "PASS" if guard["status"] == "PASS" else "REVIEW_REQUIRED",
    }


def evaluate_legacy_add_double_authority_guard(
    compatibility_artifact: Mapping[str, Any],
    *,
    canonical_authority_records: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    legacy_records = tuple(
        record
        for record in compatibility_artifact.get("compatibility", ())
        if isinstance(record, Mapping)
    )
    duplicate_keys = _duplicate_dedup_keys(legacy_records)
    canonical_keys = {
        _dedup_key(record)
        for record in canonical_authority_records
        if _record_has_add_authority(record)
    }
    legacy_authority_keys = {
        _dedup_key(record)
        for record in legacy_records
        if _record_has_add_authority(record)
    }
    overlaps = sorted(key for key in legacy_authority_keys if key in canonical_keys)
    status = "BLOCKED" if duplicate_keys or overlaps else "PASS"
    return {
        "status": status,
        "dedup_key_fields": list(LEGACY_ADD_DEDUP_FIELDS),
        "legacy_record_count": len(legacy_records),
        "canonical_authority_record_count": len(canonical_authority_records),
        "duplicate_legacy_dedup_keys": duplicate_keys,
        "canonical_legacy_authority_overlaps": overlaps,
        "conflict_behavior": "BLOCKED" if status == "BLOCKED" else "PASS",
        "fail_open_allowed": False,
    }


def validate_legacy_add_compatibility_lineage(
    compatibility_artifact: Mapping[str, Any],
    *,
    expected_business_date: str,
    expected_accepted_generation: str = "",
    expected_campaign_by_symbol: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    records = tuple(
        record
        for record in compatibility_artifact.get("compatibility", ())
        if isinstance(record, Mapping)
    )
    reason_codes: list[str] = []
    for record in records:
        if str(record.get("business_date") or "") != expected_business_date:
            reason_codes.append("BUSINESS_DATE_MISMATCH")
        if expected_accepted_generation and str(record.get("accepted_generation") or "") != expected_accepted_generation:
            reason_codes.append("ACCEPTED_GENERATION_MISMATCH")
        campaign_by_symbol = expected_campaign_by_symbol or {}
        symbol = str(record.get("symbol") or "")
        expected_campaign = str(campaign_by_symbol.get(symbol) or "")
        if expected_campaign and str(record.get("position_campaign_id") or "") != expected_campaign:
            reason_codes.append("POSITION_CAMPAIGN_MISMATCH")
    guard = evaluate_legacy_add_double_authority_guard(compatibility_artifact)
    if guard["status"] != "PASS":
        reason_codes.append("DEDUP_KEY_CONFLICT")
    unique_reasons = sorted(set(reason_codes))
    return {
        "status": "PASS" if not unique_reasons else "REVIEW_REQUIRED",
        "reason_codes": unique_reasons,
        "record_count": len(records),
        "double_authority_guard": guard,
        "fail_open_allowed": False,
    }


def _compatibility_record(
    decision: Any,
    *,
    business_date: str,
    target_session_date: str,
    environment: str,
    run_id: str,
    accepted_generation: str,
    canonical_position_intent_ref: str,
    canonical_target_portfolio_decision_ref: str,
) -> dict[str, Any]:
    symbol = str(getattr(decision, "symbol", "") or "").strip()
    decision_id = str(getattr(decision, "source_decision_id", "") or getattr(decision, "decision_id", "") or "")
    campaign_id = str(
        getattr(decision, "position_campaign_id", "")
        or getattr(decision, "source_position_campaign_id", "")
        or "UNKNOWN"
    )
    effective_run_id = str(run_id or getattr(decision, "run_id", "") or "UNKNOWN")
    lineage = {
        "source_decision_artifact": str(getattr(decision, "source_decision_artifact", "") or ""),
        "source_pm_decision_id": decision_id,
        "canonical_position_intent_ref": canonical_position_intent_ref
        or str(getattr(decision, "canonical_position_intent_ref", "") or "NOT_CONNECTED"),
        "canonical_target_portfolio_decision_ref": canonical_target_portfolio_decision_ref
        or str(getattr(decision, "canonical_target_portfolio_decision_ref", "") or "NOT_CONNECTED"),
    }
    record = {
        "schema_version": LEGACY_ADD_COMPATIBILITY_SCHEMA_VERSION,
        "artifact_type": "legacy_pm_add_compatibility_row",
        "migration_state": LEGACY_ADD_MIGRATION_STATE,
        "authority_mode": LEGACY_ADD_AUTHORITY_MODE,
        "decision_effect": LEGACY_ADD_DECISION_EFFECT,
        "run_id": effective_run_id,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "environment": environment,
        "accepted_generation": str(accepted_generation or getattr(decision, "accepted_generation", "") or ""),
        "symbol": symbol,
        "position_campaign_id": campaign_id,
        "decision_id": decision_id,
        "source_pm_decision_id": decision_id,
        "source_pm_intent": "ADD",
        "canonical_position_intent_ref": lineage["canonical_position_intent_ref"],
        "canonical_target_portfolio_decision_ref": lineage["canonical_target_portfolio_decision_ref"],
        "compatibility_status": "PASS",
        "compatibility_reason_codes": [LEGACY_ADD_COMPATIBILITY_REASON],
        "legacy_path_would_have_been_invoked": True,
        "quantity_authority": LEGACY_ADD_NO_AUTHORITY,
        "pending_authority": LEGACY_ADD_NO_AUTHORITY,
        "approval_authority": LEGACY_ADD_NO_AUTHORITY,
        "submit_authority": LEGACY_ADD_NO_AUTHORITY,
        "telemetry_only": True,
        "lineage": lineage,
        "review_status": "PASS",
    }
    record["dedup_key"] = _dedup_key(record)
    return record


def _dedup_key(record: Mapping[str, Any]) -> str:
    return "|".join(str(record.get(field) or "UNKNOWN") for field in LEGACY_ADD_DEDUP_FIELDS)


def _duplicate_dedup_keys(records: Sequence[Mapping[str, Any]]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        key = _dedup_key(record)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return sorted(duplicates)


def _record_has_add_authority(record: Mapping[str, Any]) -> bool:
    return (
        str(record.get("decision_effect") or "").upper() != LEGACY_ADD_DECISION_EFFECT
        or str(record.get("quantity_authority") or "").upper() != LEGACY_ADD_NO_AUTHORITY
        or str(record.get("pending_authority") or "").upper() != LEGACY_ADD_NO_AUTHORITY
        or str(record.get("approval_authority") or "").upper() != LEGACY_ADD_NO_AUTHORITY
        or str(record.get("submit_authority") or "").upper() != LEGACY_ADD_NO_AUTHORITY
    )
