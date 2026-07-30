"""Pending Safety Authority helpers."""

from __future__ import annotations


HISTORICAL_NEUTRAL_SAFETY_AUTHORITY = "historical_initial_no_external_effect"
HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION = "historical_replay_neutral_safety_v1"
HISTORICAL_NEUTRAL_SAFETY_SOURCE = "data_readiness_historical_temporal_authority"
HISTORICAL_NEUTRAL_SAFETY_DECISIONS = {"NEUTRAL", "ALLOW"}


def historical_neutral_safety_decision_id(business_date: str) -> str:
    return f"historical-neutral-safety:{business_date}"


def is_historical_neutral_safety_authority(
    *,
    safety_decision: str,
    safety_policy_version: str,
    safety_source: str,
) -> bool:
    return (
        str(safety_decision or "").upper() in HISTORICAL_NEUTRAL_SAFETY_DECISIONS
        and str(safety_policy_version or "") == HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION
        and str(safety_source or "") == HISTORICAL_NEUTRAL_SAFETY_SOURCE
    )


def materialize_historical_pending_safety_context(
    *,
    safety_decision_id: str,
    safety_policy_version: str,
    safety_source: str,
    safety_decision: str,
    safety_reason: str,
    safety_business_date: str,
    runtime_test_run_id: str = "",
    runtime_test_profile_id: str = "",
    runtime_test_evidence_root: str = "",
) -> dict[str, str]:
    decision = str(safety_decision or "").upper()
    if not is_historical_neutral_safety_authority(
        safety_decision=decision,
        safety_policy_version=safety_policy_version,
        safety_source=safety_source,
    ):
        return {}
    context = {
        "safety_authority": HISTORICAL_NEUTRAL_SAFETY_AUTHORITY,
        "safety_decision_id": str(safety_decision_id or historical_neutral_safety_decision_id(safety_business_date)),
        "safety_policy_version": HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION,
        "safety_source": HISTORICAL_NEUTRAL_SAFETY_SOURCE,
        "safety_decision": decision,
        "safety_reason": str(safety_reason or "historical_neutral_no_event_safety_ready"),
        "safety_business_date": str(safety_business_date),
        "temporal_authority_business_date": str(safety_business_date),
    }
    if runtime_test_run_id:
        context["runtime_test_run_id"] = str(runtime_test_run_id)
    if runtime_test_profile_id:
        context["runtime_test_profile_id"] = str(runtime_test_profile_id)
    if runtime_test_evidence_root:
        context["runtime_test_evidence_root"] = str(runtime_test_evidence_root)
    return context
