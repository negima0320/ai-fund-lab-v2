from __future__ import annotations

from typing import Any, Iterable


SOURCE_CALCULATION_INVALID = "SOURCE_CALCULATION_INVALID"
SOURCE_VALIDATION_REVIEW_REQUIRED = "SOURCE_VALIDATION_REVIEW_REQUIRED"
SOURCE_LIFECYCLE_DRAFT = "SOURCE_LIFECYCLE_DRAFT"
SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE = "SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE"
SOURCE_HUMAN_REVIEW_REQUIRED = "SOURCE_HUMAN_REVIEW_REQUIRED"
SOURCE_INPUT_MISSING = "SOURCE_INPUT_MISSING"
SOURCE_PIT_INVALID = "SOURCE_PIT_INVALID"

CALCULATION_ALLOWED = "CALCULATION_ALLOWED"
CALCULATION_ALLOWED_WITH_REVIEW = "CALCULATION_ALLOWED_WITH_REVIEW"
CALCULATION_NOT_ALLOWED = "CALCULATION_NOT_ALLOWED"

RESOLVED = "RESOLVED"
UNRESOLVED = "UNRESOLVED"
EXPLICIT_ZERO = "EXPLICIT_ZERO"


def split_reason_codes(reason_codes: Iterable[Any]) -> dict[str, list[str]]:
    direct: list[str] = []
    propagated: list[str] = []
    for reason in sorted({str(item) for item in reason_codes if str(item)}):
        if reason.startswith("upstream_") or "_review_required:" in reason or "_block:" in reason:
            propagated.append(reason)
        else:
            direct.append(reason)
    return {"direct_reason_codes": direct, "propagated_reason_codes": propagated}


def status_contract_fields(
    *,
    producer_result_status: str,
    artifact_lifecycle_status: str,
    runtime_consumer_eligibility: str,
    reason_codes: Iterable[Any],
    validation_status: str | None = None,
    decision_resolution: str | None = None,
    calculation_stop_reasons: Iterable[str] = (),
) -> dict[str, Any]:
    producer_status = str(producer_result_status or "")
    lifecycle_status = str(artifact_lifecycle_status or "")
    consumer_status = str(runtime_consumer_eligibility or "")
    split = split_reason_codes(reason_codes)
    lifecycle_reason_codes = [SOURCE_LIFECYCLE_DRAFT] if lifecycle_status == "DRAFT" else []
    consumer_reason_codes = [SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE] if consumer_status == "NOT_ELIGIBLE" else []
    stop_reasons = sorted({str(item) for item in calculation_stop_reasons if str(item)})
    if validation_status is None:
        validation_status = "PASS" if producer_status == "PASS" else ("BLOCK" if producer_status == "BLOCK" else "REVIEW_REQUIRED")
    if decision_resolution is None:
        decision_resolution = RESOLVED if producer_status == "PASS" else UNRESOLVED
    if producer_status == "BLOCK" or stop_reasons:
        downstream_eligibility = CALCULATION_NOT_ALLOWED
    elif producer_status == "REVIEW_REQUIRED" or lifecycle_reason_codes or consumer_reason_codes:
        downstream_eligibility = CALCULATION_ALLOWED_WITH_REVIEW
    else:
        downstream_eligibility = CALCULATION_ALLOWED
    human_review_reasons = []
    if producer_status == "REVIEW_REQUIRED":
        human_review_reasons.append(SOURCE_VALIDATION_REVIEW_REQUIRED)
    human_review_reasons.extend(lifecycle_reason_codes)
    human_review_reasons.extend(consumer_reason_codes)
    if stop_reasons:
        human_review_reasons.extend(stop_reasons)
    return {
        "producer_calculation_completed": producer_status != "BLOCK",
        "validation_status": validation_status,
        "artifact_lifecycle_status": lifecycle_status,
        "runtime_consumer_eligibility": consumer_status,
        "human_review_status": "REQUIRED" if human_review_reasons else "NOT_REQUIRED",
        "human_review_reason_codes": sorted(set(human_review_reasons)),
        "downstream_calculation_eligibility": downstream_eligibility,
        "decision_resolution": decision_resolution,
        "direct_reason_codes": split["direct_reason_codes"],
        "propagated_reason_codes": split["propagated_reason_codes"],
        "lifecycle_reason_codes": lifecycle_reason_codes,
        "consumer_eligibility_reason_codes": consumer_reason_codes,
        "calculation_stop_reason_codes": stop_reasons,
    }


def compatibility_status_from_payload(
    payload: dict[str, Any],
    *,
    compatible_status: str,
    source_review_required: str,
    source_blocked: str,
) -> str:
    producer_status = str(payload.get("producer_result_status") or "")
    consumer_status = str(payload.get("runtime_consumer_eligibility") or "")
    if producer_status == "BLOCK" or consumer_status == "BLOCKED":
        return source_blocked
    if producer_status == "REVIEW_REQUIRED":
        return source_review_required
    return compatible_status


def numeric_resolution(value: Any, *, unresolved: bool, explicit_zero: bool = False) -> str:
    if unresolved:
        return UNRESOLVED
    if explicit_zero or value == 0 or value == 0.0:
        return EXPLICIT_ZERO
    return RESOLVED
