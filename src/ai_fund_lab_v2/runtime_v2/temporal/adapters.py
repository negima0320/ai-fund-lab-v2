"""Future component adapters for the shared Temporal Foundation.

These helpers intentionally do not call producers.  They only translate
already-loaded component payloads into Temporal Contract evidence.
"""

from __future__ import annotations

from typing import Any

from ai_fund_lab_v2.runtime_v2.temporal.freshness import (
    evaluate_current_position_freshness,
    evaluate_current_valuation_freshness,
    evaluate_feature_freshness,
    evaluate_market_freshness,
    evaluate_pending_temporal_status,
    evaluate_safety_temporal_status,
)
from ai_fund_lab_v2.runtime_v2.temporal.models import CurrentTemporalState, FreshnessStatus, TemporalContext, TemporalEvidence


def market_temporal_adapter(payload: dict[str, Any], *, context: TemporalContext, artifact_path: str = "") -> TemporalEvidence:
    return evaluate_market_freshness(
        context=context,
        actual_date=str(payload.get("market_date") or payload.get("latest_available_market_date") or "") or None,
        generated_at=str(payload.get("generated_at") or ""),
        expires_at=str(payload.get("expires_at") or ""),
        source=str(payload.get("source") or "market"),
        artifact_path=artifact_path,
    )


def feature_temporal_adapter(payload: dict[str, Any], *, context: TemporalContext, artifact_path: str = "") -> TemporalEvidence:
    return evaluate_feature_freshness(
        context=context,
        actual_date=str(payload.get("feature_date") or payload.get("target_date") or "") or None,
        generated_at=str(payload.get("generated_at") or ""),
        expires_at=str(payload.get("expires_at") or ""),
        source=str(payload.get("source") or "feature"),
        artifact_path=artifact_path,
    )


def current_temporal_adapter(payload: dict[str, Any], *, context: TemporalContext, artifact_path: str = "") -> dict[str, TemporalEvidence]:
    current = CurrentTemporalState(
        position_state_as_of=str(payload.get("position_state_as_of") or payload.get("as_of") or ""),
        valuation_as_of=str(payload.get("valuation_as_of") or payload.get("as_of") or ""),
        last_execution_date=str(payload.get("last_execution_date") or ""),
        last_reconciled_at=str(payload.get("last_reconciled_at") or ""),
        source_market_date=str(payload.get("source_market_date") or payload.get("valuation_as_of") or payload.get("as_of") or ""),
    )
    return {
        "current_position": evaluate_current_position_freshness(context=context, current=current, artifact_path=artifact_path),
        "current_valuation": evaluate_current_valuation_freshness(context=context, current=current, artifact_path=artifact_path),
    }


def broker_temporal_adapter(payload: dict[str, Any], *, context: TemporalContext, artifact_path: str = "") -> TemporalEvidence:
    status = FreshnessStatus.REVIEW_REQUIRED if payload.get("review_required") else FreshnessStatus.READY
    return TemporalEvidence(
        expected_date=context.runtime_business_date,
        actual_date=str(payload.get("broker_business_date") or context.runtime_business_date),
        generated_at=str(payload.get("snapshot_at") or payload.get("generated_at") or ""),
        expires_at=str(payload.get("expires_at") or ""),
        status=status,
        reason="broker_snapshot_review_required" if status == FreshnessStatus.REVIEW_REQUIRED else "broker_snapshot_ready",
        comparison_contract="broker_snapshot_temporal_status",
        source=str(payload.get("source") or "broker_readonly"),
        artifact_path=artifact_path,
    )


def safety_temporal_adapter(payload: dict[str, Any], *, context: TemporalContext, artifact_path: str = "") -> TemporalEvidence:
    return evaluate_safety_temporal_status(
        context=context,
        generated_at=str(payload.get("generated_at") or ""),
        expires_at=str(payload.get("expires_at") or ""),
        dependency_statuses=payload.get("dependency_statuses") or (),
        source=str(payload.get("source") or "runtime_safety"),
        artifact_path=artifact_path,
    )


def pending_temporal_adapter(payload: dict[str, Any], *, context: TemporalContext, artifact_path: str = "") -> TemporalEvidence:
    return evaluate_pending_temporal_status(
        context=context,
        target_session_date=str(payload.get("target_session_date") or ""),
        generated_at=str(payload.get("generated_at") or ""),
        expires_at=str(payload.get("expires_at") or ""),
        source=str(payload.get("source") or "pending"),
        artifact_path=artifact_path,
    )


def data_readiness_temporal_adapter(payload: dict[str, Any], *, context: TemporalContext, artifact_path: str = "") -> TemporalEvidence:
    status = FreshnessStatus(str(payload.get("overall_status") or payload.get("status") or "REVIEW_REQUIRED"))
    return TemporalEvidence(
        expected_date=context.runtime_business_date,
        actual_date=str(payload.get("business_date") or ""),
        generated_at=str(payload.get("generated_at") or ""),
        expires_at=str(payload.get("expires_at") or ""),
        status=status,
        reason=str(payload.get("reason") or "data_readiness_temporal_status"),
        comparison_contract="data_readiness_temporal_status",
        source=str(payload.get("source") or "data_readiness"),
        artifact_path=artifact_path,
    )
