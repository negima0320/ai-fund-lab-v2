"""Temporal comparison helpers for Runtime v2."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from ai_fund_lab_v2.runtime_v2.temporal.models import (
    CurrentTemporalState,
    FreshnessStatus,
    TemporalContext,
    TemporalEvidence,
)


STATUS_PRECEDENCE: dict[FreshnessStatus, int] = {
    FreshnessStatus.NOT_REQUIRED: 0,
    FreshnessStatus.READY: 1,
    FreshnessStatus.VALID_CARRYOVER: 2,
    FreshnessStatus.DATA_NOT_YET_AVAILABLE: 3,
    FreshnessStatus.MISSING: 4,
    FreshnessStatus.DATE_MISMATCH: 5,
    FreshnessStatus.STALE: 6,
    FreshnessStatus.EXPIRED: 7,
    FreshnessStatus.REVIEW_REQUIRED: 8,
    FreshnessStatus.HALT: 9,
}


def worst_freshness_status(statuses: Iterable[FreshnessStatus | str]) -> FreshnessStatus:
    parsed = [_status(status) for status in statuses]
    if not parsed:
        return FreshnessStatus.NOT_REQUIRED
    return max(parsed, key=lambda status: STATUS_PRECEDENCE[status])


def evaluate_market_freshness(
    *,
    context: TemporalContext,
    actual_date: str | None,
    generated_at: str = "",
    expires_at: str = "",
    source: str = "market",
    artifact_path: str = "",
    now: datetime | None = None,
) -> TemporalEvidence:
    expected = context.latest_expected_trading_date
    actual = actual_date or ""
    if not actual:
        return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.MISSING, "market_evidence_missing", "market_latest_expected_trading_date", source, artifact_path)
    if actual == expected:
        if context.is_non_trading_carryover_day:
            return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.VALID_CARRYOVER, "market_valid_non_trading_day_carryover", "market_latest_expected_trading_date", source, artifact_path)
        return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.READY, "market_evidence_ready", "market_latest_expected_trading_date", source, artifact_path)
    if actual < expected:
        if context.publication_window and (
            context.publication_window.is_before_available(now) or context.publication_window.is_within_grace(now)
        ):
            return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.DATA_NOT_YET_AVAILABLE, "market_data_not_yet_available", "market_publication_window", source, artifact_path)
        return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.STALE, "market_evidence_stale_after_publication_window", "market_publication_window", source, artifact_path)
    return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.DATE_MISMATCH, "market_date_mismatch", "market_latest_expected_trading_date", source, artifact_path)


def evaluate_feature_freshness(
    *,
    context: TemporalContext,
    actual_date: str | None,
    generated_at: str = "",
    expires_at: str = "",
    source: str = "feature",
    artifact_path: str = "",
    now: datetime | None = None,
) -> TemporalEvidence:
    expected = context.latest_available_market_date or context.latest_expected_trading_date
    actual = actual_date or ""
    if not actual:
        return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.MISSING, "feature_artifact_missing", "feature_date_matches_accepted_market_evidence", source, artifact_path)
    if actual == expected:
        if context.is_non_trading_carryover_day and expected == context.latest_expected_trading_date:
            return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.VALID_CARRYOVER, "feature_valid_non_trading_day_carryover", "feature_date_matches_accepted_market_evidence", source, artifact_path)
        return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.READY, "feature_evidence_ready", "feature_date_matches_accepted_market_evidence", source, artifact_path)
    if actual < expected:
        if context.publication_window and (
            context.publication_window.is_before_available(now) or context.publication_window.is_within_grace(now)
        ):
            return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.DATA_NOT_YET_AVAILABLE, "feature_waiting_for_market_publication", "feature_date_matches_accepted_market_evidence", source, artifact_path)
        return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.STALE, "feature_artifact_stale", "feature_date_matches_accepted_market_evidence", source, artifact_path)
    return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.DATE_MISMATCH, "feature_date_mismatch", "feature_date_matches_accepted_market_evidence", source, artifact_path)


def evaluate_current_position_freshness(
    *,
    context: TemporalContext,
    current: CurrentTemporalState | None,
    generated_at: str = "",
    expires_at: str = "",
    source: str = "current",
    artifact_path: str = "",
) -> TemporalEvidence:
    expected = context.runtime_business_date
    if current is None or not current.position_state_as_of:
        return _evidence(expected, "", generated_at, expires_at, FreshnessStatus.MISSING, "current_position_state_missing", "current_position_state_contract", source, artifact_path)
    if current.last_execution_date and current.position_state_as_of < current.last_execution_date:
        return _evidence(expected, current.position_state_as_of, generated_at, expires_at, FreshnessStatus.DATE_MISMATCH, "position_state_before_last_execution", "current_position_state_contract", source, artifact_path)
    if current.position_state_as_of <= expected:
        return _evidence(expected, current.position_state_as_of, generated_at, expires_at, FreshnessStatus.READY, "current_position_ready_no_fill_carry_allowed", "current_position_state_contract", source, artifact_path)
    return _evidence(expected, current.position_state_as_of, generated_at, expires_at, FreshnessStatus.DATE_MISMATCH, "current_position_future_date", "current_position_state_contract", source, artifact_path)


def evaluate_current_valuation_freshness(
    *,
    context: TemporalContext,
    current: CurrentTemporalState | None,
    generated_at: str = "",
    expires_at: str = "",
    source: str = "current",
    artifact_path: str = "",
    now: datetime | None = None,
) -> TemporalEvidence:
    actual = ""
    if current is not None:
        actual = current.source_market_date or current.valuation_as_of
    evidence = evaluate_market_freshness(
        context=context,
        actual_date=actual or None,
        generated_at=generated_at,
        expires_at=expires_at,
        source=source,
        artifact_path=artifact_path,
        now=now,
    )
    return TemporalEvidence(
        expected_date=evidence.expected_date,
        actual_date=evidence.actual_date,
        generated_at=evidence.generated_at,
        expires_at=evidence.expires_at,
        status=evidence.status,
        reason=evidence.reason.replace("market", "current_valuation", 1),
        comparison_contract="current_valuation_source_market_date",
        source=evidence.source,
        artifact_path=evidence.artifact_path,
    )


def evaluate_pending_temporal_status(
    *,
    context: TemporalContext,
    target_session_date: str | None,
    generated_at: str = "",
    expires_at: str = "",
    source: str = "pending",
    artifact_path: str = "",
    now: datetime | None = None,
) -> TemporalEvidence:
    expected = context.trading_session_date
    actual = target_session_date or ""
    if expires_at and now is not None and _parse_datetime(expires_at) < now:
        return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.EXPIRED, "pending_expired", "pending_target_session_date", source, artifact_path)
    if not actual:
        return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.MISSING, "pending_target_session_date_missing", "pending_target_session_date", source, artifact_path)
    if actual == expected:
        return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.READY, "pending_temporal_status_ready", "pending_target_session_date", source, artifact_path)
    return _evidence(expected, actual, generated_at, expires_at, FreshnessStatus.DATE_MISMATCH, "pending_target_session_date_mismatch", "pending_target_session_date", source, artifact_path)


def evaluate_broker_snapshot_freshness(
    *,
    context: TemporalContext,
    snapshot_at: str,
    max_age_seconds: int,
    generated_at: str = "",
    expires_at: str = "",
    source: str = "broker_readonly",
    artifact_path: str = "",
    now: datetime | None = None,
) -> TemporalEvidence:
    if not snapshot_at:
        return _evidence(context.runtime_business_date, "", generated_at, expires_at, FreshnessStatus.MISSING, "broker_snapshot_missing", "broker_snapshot_wall_clock_freshness", source, artifact_path)
    parsed = _parse_datetime_or_none(snapshot_at)
    if parsed is None:
        return _evidence(context.runtime_business_date, snapshot_at[:10], generated_at, expires_at, FreshnessStatus.REVIEW_REQUIRED, "broker_snapshot_timestamp_invalid_or_timezone_missing", "broker_snapshot_wall_clock_freshness", source, artifact_path)
    if now is None:
        return _evidence(context.runtime_business_date, parsed.date().isoformat(), generated_at, expires_at, FreshnessStatus.REVIEW_REQUIRED, "broker_snapshot_evaluation_time_missing", "broker_snapshot_wall_clock_freshness", source, artifact_path)
    age = max(0, int((now - parsed).total_seconds()))
    if age > max_age_seconds:
        return _evidence(context.runtime_business_date, parsed.date().isoformat(), generated_at, expires_at, FreshnessStatus.STALE, "broker_snapshot_stale", "broker_snapshot_wall_clock_freshness", source, artifact_path)
    return _evidence(context.runtime_business_date, parsed.date().isoformat(), generated_at, expires_at, FreshnessStatus.READY, "broker_snapshot_ready", "broker_snapshot_wall_clock_freshness", source, artifact_path)


def evaluate_safety_temporal_status(
    *,
    context: TemporalContext,
    generated_at: str,
    expires_at: str,
    dependency_statuses: Iterable[FreshnessStatus | str] = (),
    source: str = "safety",
    artifact_path: str = "",
    now: datetime | None = None,
) -> TemporalEvidence:
    if not generated_at:
        return _evidence(context.runtime_business_date, "", generated_at, expires_at, FreshnessStatus.MISSING, "safety_decision_missing", "safety_decision_validity", source, artifact_path)
    if expires_at and now is not None and _parse_datetime(expires_at) < now:
        return _evidence(context.runtime_business_date, context.runtime_business_date, generated_at, expires_at, FreshnessStatus.EXPIRED, "safety_decision_expired", "safety_decision_validity", source, artifact_path)
    worst = worst_freshness_status(dependency_statuses)
    if worst == FreshnessStatus.HALT:
        return _evidence(context.runtime_business_date, context.runtime_business_date, generated_at, expires_at, FreshnessStatus.HALT, "safety_dependency_halt", "safety_dependency_temporal_status", source, artifact_path)
    if STATUS_PRECEDENCE[worst] >= STATUS_PRECEDENCE[FreshnessStatus.REVIEW_REQUIRED]:
        return _evidence(context.runtime_business_date, context.runtime_business_date, generated_at, expires_at, FreshnessStatus.REVIEW_REQUIRED, "safety_dependency_review_required", "safety_dependency_temporal_status", source, artifact_path)
    if STATUS_PRECEDENCE[worst] >= STATUS_PRECEDENCE[FreshnessStatus.STALE]:
        return _evidence(context.runtime_business_date, context.runtime_business_date, generated_at, expires_at, FreshnessStatus.REVIEW_REQUIRED, "safety_dependency_not_ready", "safety_dependency_temporal_status", source, artifact_path)
    return _evidence(context.runtime_business_date, context.runtime_business_date, generated_at, expires_at, FreshnessStatus.READY, "safety_temporal_status_ready", "safety_decision_validity", source, artifact_path)


def _evidence(
    expected_date: str,
    actual_date: str,
    generated_at: str,
    expires_at: str,
    status: FreshnessStatus,
    reason: str,
    comparison_contract: str,
    source: str,
    artifact_path: str,
) -> TemporalEvidence:
    return TemporalEvidence(
        expected_date=expected_date,
        actual_date=actual_date,
        generated_at=generated_at,
        expires_at=expires_at,
        status=status,
        reason=reason,
        comparison_contract=comparison_contract,
        source=source,
        artifact_path=artifact_path,
    )


def _status(value: FreshnessStatus | str) -> FreshnessStatus:
    if isinstance(value, FreshnessStatus):
        return value
    return FreshnessStatus(str(value))


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_datetime_or_none(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed
