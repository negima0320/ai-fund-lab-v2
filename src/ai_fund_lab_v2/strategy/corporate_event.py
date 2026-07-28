from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.strategy.status_contract import status_contract_fields


SCHEMA_VERSION = "corporate_event_authority.v1"
PRODUCER_VERSION = "phase22_aa_corporate_event_producer.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"

EVENT_TYPES = {
    "LISTING_STATUS",
    "DELISTING_PENDING",
    "SUPERVISION_STATUS",
    "LIQUIDATION_STATUS",
    "EARNINGS_ANNOUNCEMENT",
    "FORECAST_REVISION",
    "DIVIDEND_REVISION",
    "TOB",
    "MERGER_ACQUISITION",
    "STOCK_SPLIT",
    "REVERSE_SPLIT",
    "CORPORATE_ACTION",
}
EVENT_STATUSES = {"ANNOUNCED", "SCHEDULED", "EFFECTIVE", "DISCLOSED", "UNKNOWN"}
SOURCE_AUTHORITY_STATUSES = {"VALID", "MISSING", "STALE", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
PRODUCER_RESULT_STATUSES = {"PASS", "REVIEW_REQUIRED", "BLOCK"}
ARTIFACT_LIFECYCLE_STATUSES = {"DRAFT", "VALIDATED", "REVIEW_REQUIRED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}
RUNTIME_CONSUMER_ELIGIBILITIES = {"ELIGIBLE", "NOT_ELIGIBLE", "REVIEW_REQUIRED", "BLOCKED"}
COVERAGE_STATUSES = {"AVAILABLE", "PARTIAL", "MISSING", "NOT_IMPLEMENTED"}


class CorporateEventError(RuntimeError):
    pass


class CorporateEventSchemaError(CorporateEventError):
    pass


class CorporateEventConsumerError(CorporateEventError):
    pass


@dataclass(frozen=True)
class CorporateEventInputPaths:
    listed_issues_path: Path
    trading_calendar_path: Path | None = None
    earnings_schedule_path: Path | None = None
    financial_statements_path: Path | None = None
    corporate_actions_path: Path | None = None


@dataclass(frozen=True)
class CorporateEventProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "corporate_event" / business_date / "corporate_event.json"


def resolve_default_input_paths(operations_root: Path | str) -> CorporateEventInputPaths:
    root = Path(operations_root)
    return CorporateEventInputPaths(
        listed_issues_path=root / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet",
        trading_calendar_path=root / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet",
        earnings_schedule_path=root / "jquants" / "raw" / "jquants" / "earnings_calendar" / "data.parquet",
        financial_statements_path=root / "jquants" / "raw" / "jquants" / "statements" / "data.parquet",
        corporate_actions_path=root / "jquants" / "raw" / "jquants" / "corporate_actions" / "data.parquet",
    )


def produce_corporate_event_artifact(
    *,
    business_date: str,
    input_paths: CorporateEventInputPaths,
    output_path: Path | str,
    as_of: str | None = None,
    expected_source_hashes: dict[str, str] | None = None,
    require_full_source_coverage: bool = True,
) -> CorporateEventProducerResult:
    _validate_iso_date(business_date, field="business_date")
    payload, evidence = build_corporate_event_payload(
        business_date=business_date,
        input_paths=input_paths,
        as_of=as_of,
        expected_source_hashes=expected_source_hashes,
        require_full_source_coverage=require_full_source_coverage,
    )
    validate_corporate_event_artifact(payload)
    artifact_hash = corporate_event_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final_payload)
    return CorporateEventProducerResult(
        status=str(final_payload["producer_result_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_corporate_event_payload(
    *,
    business_date: str,
    input_paths: CorporateEventInputPaths,
    as_of: str | None = None,
    expected_source_hashes: dict[str, str] | None = None,
    require_full_source_coverage: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _validate_rfc3339_timestamp(as_of, field="as_of")
    source_status, source_artifacts, source_hashes, source_reasons = resolve_source_authority(
        input_paths=input_paths,
        expected_source_hashes=expected_source_hashes or {},
    )
    events: list[dict[str, Any]] = []
    mapping_reasons: list[str] = []
    future_leakage_used = False
    coverage = _coverage_status(source_artifacts=source_artifacts, require_full_source_coverage=require_full_source_coverage)
    feature_date = business_date
    if source_status != "MISSING":
        events, mapping_reasons, feature_date = build_events_from_listed_issues(
            business_date=business_date,
            listed_issues_path=input_paths.listed_issues_path,
            listed_source_hash=_source_hash_for(source_hashes, "jquants_listed_issues"),
        )
        future_leakage_used = any(reason in {"future_listed_issues_row_detected"} for reason in mapping_reasons)
    effective_source_reasons = source_reasons if require_full_source_coverage else [reason for reason in source_reasons if not reason.endswith("_not_implemented_or_missing")]
    reason_codes = sorted(set([*effective_source_reasons, *mapping_reasons]))
    if require_full_source_coverage and coverage != "AVAILABLE":
        reason_codes.append("corporate_event_source_coverage_incomplete")
    if source_status in {"HASH_MISMATCH", "AUTHORITY_CONFLICT"} or "future_listed_issues_row_rejected" in reason_codes or future_leakage_used or "invalid_event_date_ordering" in reason_codes:
        producer_status = "BLOCK"
    elif source_status in {"MISSING", "STALE"} or coverage != "AVAILABLE" or reason_codes:
        producer_status = "REVIEW_REQUIRED"
    else:
        producer_status = "PASS"
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
        "coverage_status": coverage,
        "events": sorted(events, key=lambda item: item["event_id"]),
        "event_count": len(events),
        "event_taxonomy": sorted(EVENT_TYPES),
        "event_identity": {
            "algorithm": "sha256",
            "fields": ["security_code", "event_type", "announcement_date", "effective_date", "availability_date", "source_reference", "revision_id"],
            "row_order_dependent": False,
        },
        "reason_codes": sorted(set(reason_codes)),
        "source_artifacts": source_artifacts,
        "source_hashes": source_hashes,
        "temporal_safety": {
            "point_in_time": not future_leakage_used,
            "future_leakage_used": future_leakage_used,
            "feature_date_lte_business_date": feature_date <= business_date,
        },
        "no_event_semantics": {
            "empty_events_meaning": "NO_EVENTS_ONLY_WHEN_SOURCE_COVERAGE_AVAILABLE_AND_PRODUCER_PASS",
            "unknown_event_state_when_source_missing": producer_status == "REVIEW_REQUIRED" and source_status == "MISSING",
        },
    }
    evidence = {
        "schema_version": "phase22_aa_corporate_event_producer_evidence.v1",
        "business_date": business_date,
        "source_authority_status": source_status,
        "producer_result_status": producer_status,
        "coverage_status": coverage,
        "future_leakage_used": future_leakage_used,
        "event_count": len(events),
        "reason_codes": payload["reason_codes"],
    }
    return payload, evidence


def resolve_source_authority(
    *,
    input_paths: CorporateEventInputPaths,
    expected_source_hashes: dict[str, str] | None = None,
) -> tuple[str, list[dict[str, Any]], list[dict[str, str]], list[str]]:
    expected = expected_source_hashes or {}
    refs = [
        ("jquants_listed_issues", input_paths.listed_issues_path, True, "listed_status_delisting_partial"),
        ("jquants_trading_calendar", input_paths.trading_calendar_path, False, "business_day_distance"),
        ("jquants_earnings_schedule", input_paths.earnings_schedule_path, False, "earnings_contract"),
        ("jquants_financial_statements", input_paths.financial_statements_path, False, "financial_statement_release"),
        ("jquants_corporate_actions", input_paths.corporate_actions_path, False, "split_merger_tob_dividend_contract"),
    ]
    source_artifacts: list[dict[str, Any]] = []
    source_hashes: list[dict[str, str]] = []
    reasons: list[str] = []
    status = "VALID"
    for role, maybe_path, required, coverage_role in refs:
        path = Path(maybe_path) if maybe_path is not None else None
        exists = bool(path and path.is_file())
        implemented = role in {"jquants_listed_issues", "jquants_trading_calendar"} and exists
        source_artifacts.append(
            {
                "role": role,
                "path": str(path or ""),
                "required": required,
                "exists": exists,
                "coverage_role": coverage_role,
                "implemented": implemented,
            }
        )
        if not exists:
            if required:
                status = "MISSING"
                reasons.append(f"{role}_missing")
            else:
                reasons.append(f"{role}_not_implemented_or_missing")
            continue
        actual = sha256_file(path)
        source_hashes.append({"role": role, "path": str(path), "sha256": actual})
        expected_hash = expected.get(role) or expected.get(str(path))
        if expected_hash and _strip_sha256(expected_hash) != actual:
            status = "HASH_MISMATCH"
            reasons.append(f"{role}_hash_mismatch")
    return status, source_artifacts, sorted(source_hashes, key=lambda item: (item["role"], item["path"])), sorted(set(reasons))


def build_events_from_listed_issues(
    *,
    business_date: str,
    listed_issues_path: Path,
    listed_source_hash: str,
) -> tuple[list[dict[str, Any]], list[str], str]:
    import pandas as pd

    if not Path(listed_issues_path).is_file():
        return [], ["jquants_listed_issues_missing"], business_date
    frame = pd.read_parquet(listed_issues_path)
    if frame.empty:
        return [], ["jquants_listed_issues_empty"], business_date
    date_col = _first_column(frame, ("target_date", "Date", "date", "provider_effective_date"))
    code_col = _first_column(frame, ("code", "Code", "LocalCode", "symbol"))
    if not date_col or not code_col:
        return [], ["listed_issues_required_column_missing"], business_date
    working = frame.copy()
    working["_event_source_date"] = working[date_col].astype(str)
    future_row_count = int((working["_event_source_date"] > business_date).sum())
    working = working[working["_event_source_date"] <= business_date].copy()
    if working.empty:
        if future_row_count:
            return [], ["future_listed_issues_row_rejected"], business_date
        return [], ["no_pit_listed_issues_rows"], business_date
    feature_date = str(working["_event_source_date"].max())
    working = working[working["_event_source_date"] == feature_date].copy()
    working["_security_code"] = working[code_col].astype(str)
    events: list[dict[str, Any]] = []
    reasons: list[str] = []
    for row in working.to_dict(orient="records"):
        code = str(row.get("_security_code") or "")
        if not code:
            continue
        events.extend(_events_from_listed_row(row, security_code=code, business_date=business_date, source_hash=listed_source_hash))
    deduped, conflict = _dedupe_events(events)
    if conflict:
        reasons.append("duplicate_authority_conflict")
    invalid_order = [
        event
        for event in deduped
        if event.get("announcement_date")
        and event.get("effective_date")
        and str(event["announcement_date"]) > str(event["effective_date"])
    ]
    if invalid_order:
        reasons.append("invalid_event_date_ordering")
    return deduped, reasons, feature_date


def validate_corporate_event_artifact(payload: dict[str, Any]) -> dict[str, Any]:
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
        "coverage_status",
        "events",
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
    _enum_check(errors, payload, "coverage_status", COVERAGE_STATUSES)
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS:
        errors.append("phase22_aa_artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY:
        errors.append("phase22_aa_runtime_consumer_eligibility_must_be_not_eligible")
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
    if not isinstance(payload.get("events"), list):
        errors.append("events_not_list")
    else:
        for index, event in enumerate(payload["events"]):
            errors.extend(_validate_event(event, index=index, business_date=str(payload.get("business_date") or "")))
    temporal = payload.get("temporal_safety")
    if not isinstance(temporal, dict):
        errors.append("temporal_safety_not_object")
    elif temporal.get("future_leakage_used") is True and payload.get("producer_result_status") != "BLOCK":
        errors.append("future_leakage_must_block")
    if errors:
        raise CorporateEventSchemaError(";".join(errors))
    return {"status": "PASS", "errors": []}


def verify_source_hashes(payload: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    missing = []
    for item in payload.get("source_hashes") or []:
        path = Path(str(item.get("path") or ""))
        expected = str(item.get("sha256") or "")
        if not path.is_file():
            missing.append(str(path))
            continue
        actual = sha256_file(path)
        if actual != _strip_sha256(expected):
            mismatches.append({"path": str(path), "expected": expected, "actual": actual})
    if mismatches:
        return {"status": "BLOCK", "reason": "source_hash_mismatch", "mismatches": mismatches, "missing": missing}
    if missing:
        return {"status": "REVIEW_REQUIRED", "reason": "source_missing", "mismatches": [], "missing": missing}
    return {"status": "PASS", "reason": "source_hashes_match", "mismatches": [], "missing": []}


def load_corporate_event_fixture(path: Path | str, *, for_production: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_corporate_event_artifact(payload)
    if payload.get("producer_result_status") == "BLOCK":
        raise CorporateEventConsumerError("BLOCK artifact is not fixture-consumable")
    if for_production and payload.get("runtime_consumer_eligibility") != "ELIGIBLE":
        raise CorporateEventConsumerError("Corporate Event artifact is not runtime consumer eligible")
    if payload.get("runtime_consumer_eligibility") == "ELIGIBLE" and payload.get("artifact_lifecycle_status") != "ACCEPTED":
        raise CorporateEventConsumerError("runtime eligible artifact must be ACCEPTED")
    return payload


def produced_but_not_consumed_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "phase22_aa_produced_but_not_consumed_validation.v1",
        "artifact_produced": bool(payload),
        "production_consumer_connected": False,
        "runtime_consumer_eligibility": payload.get("runtime_consumer_eligibility"),
        "legacy_authority_active": True,
        "runtime_switch_performed": False,
        "candidate_behavior_changed": False,
        "opportunity_behavior_changed": False,
        "pm_behavior_changed": False,
        "pending_changed": False,
        "submit_changed": False,
        "status": "PASS"
        if payload and payload.get("runtime_consumer_eligibility") == "NOT_ELIGIBLE"
        else "BLOCK",
    }


def corporate_event_hash(payload: dict[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if key != "artifact_hash"}
    encoded = json.dumps(clean, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _events_from_listed_row(row: dict[str, Any], *, security_code: str, business_date: str, source_hash: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    announcement = _date_or_none(row, ("AnnouncementDate", "DisclosedDate", "DisclosureDate", "Date", "target_date"))
    availability = _date_or_none(row, ("AvailabilityDate", "available_date", "fetched_at", "Date", "target_date"))
    if availability and "T" in availability:
        availability = availability[:10]
    source_reference = f"jquants_listed_issues:{security_code}:{row.get('Date') or row.get('target_date') or business_date}"
    final_trading = _date_or_none(row, ("FinalTradingDate", "final_trading_date", "DelistingDate", "scheduled_delisting_date"))
    delisting_status = str(row.get("DelistingStatus") or row.get("delisting_status") or "").upper()
    listed_status = str(row.get("ListedStatus") or row.get("listed_status") or "").upper()
    supervision = str(row.get("SupervisionStatus") or row.get("supervision_status") or "").upper()
    liquidation = str(row.get("LiquidationStatus") or row.get("liquidation_status") or "").upper()
    if final_trading or delisting_status in {"ANNOUNCED", "SCHEDULED", "PENDING", "DELISTING_PENDING"} or listed_status in {"DELISTING_PENDING", "DELISTED"}:
        events.append(
            _event(
                security_code=security_code,
                event_type="DELISTING_PENDING",
                announcement_date=announcement,
                effective_date=final_trading,
                availability_date=availability or announcement,
                event_status="SCHEDULED" if final_trading and final_trading > business_date else "ANNOUNCED",
                source_reference=source_reference,
                source_hash=source_hash,
                reason_codes=["listed_issues_delisting_fact"],
            )
        )
    if supervision and supervision not in {"NONE", "-", "0"}:
        events.append(
            _event(security_code=security_code, event_type="SUPERVISION_STATUS", announcement_date=announcement, effective_date=None, availability_date=availability or announcement, event_status="ANNOUNCED", source_reference=source_reference, source_hash=source_hash, reason_codes=["listed_issues_supervision_fact"])
        )
    if liquidation and liquidation not in {"NONE", "-", "0"}:
        events.append(
            _event(security_code=security_code, event_type="LIQUIDATION_STATUS", announcement_date=announcement, effective_date=final_trading, availability_date=availability or announcement, event_status="ANNOUNCED", source_reference=source_reference, source_hash=source_hash, reason_codes=["listed_issues_liquidation_fact"])
        )
    return events


def _event(**kwargs: Any) -> dict[str, Any]:
    base = {
        "security_code": kwargs["security_code"],
        "event_type": kwargs["event_type"],
        "announcement_date": kwargs.get("announcement_date"),
        "effective_date": kwargs.get("effective_date"),
        "availability_date": kwargs.get("availability_date"),
        "event_status": kwargs.get("event_status") or "UNKNOWN",
        "source_reference": kwargs.get("source_reference") or "",
        "source_hash": kwargs.get("source_hash") or "",
        "revision_id": kwargs.get("revision_id") or "",
        "confidence": float(kwargs.get("confidence", 1.0)),
        "reason_codes": sorted(set(kwargs.get("reason_codes") or [])),
    }
    base["event_id"] = deterministic_event_id(base)
    return base


def deterministic_event_id(event: dict[str, Any]) -> str:
    payload = {field: event.get(field) for field in ("security_code", "event_type", "announcement_date", "effective_date", "availability_date", "source_reference", "revision_id")}
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"corporate-event-{digest[:24]}"


def _validate_event(event: Any, *, index: int, business_date: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(event, dict):
        return [f"event_not_object:{index}"]
    required = {"security_code", "event_id", "event_type", "event_status", "source_reference", "source_hash", "confidence", "reason_codes"}
    errors.extend(f"event_required_field_missing:{index}:{field}" for field in sorted(required - set(event)))
    if event.get("event_type") not in EVENT_TYPES:
        errors.append(f"invalid_event_type:{index}")
    if event.get("event_status") not in EVENT_STATUSES:
        errors.append(f"invalid_event_status:{index}")
    for field in ("announcement_date", "effective_date", "availability_date"):
        value = event.get(field)
        if value in {None, ""}:
            continue
        try:
            _validate_iso_date(str(value), field=f"events[{index}].{field}")
        except Exception:
            errors.append(f"invalid_event_date_format:{index}:{field}")
    announcement = event.get("announcement_date")
    availability = event.get("availability_date")
    effective = event.get("effective_date")
    if announcement and business_date and str(announcement) > business_date:
        errors.append(f"future_announcement_date:{index}")
    if availability and business_date and str(availability) > business_date:
        errors.append(f"future_availability_date:{index}")
    if announcement and effective and str(announcement) > str(effective):
        errors.append(f"invalid_event_date_ordering:{index}")
    confidence = event.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= float(confidence) <= 1:
        errors.append(f"invalid_event_confidence:{index}")
    if not isinstance(event.get("reason_codes"), list):
        errors.append(f"event_reason_codes_not_list:{index}")
    return errors


def _dedupe_events(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    by_id: dict[str, dict[str, Any]] = {}
    conflict = False
    for event in events:
        existing = by_id.get(event["event_id"])
        if existing is not None and existing != event:
            conflict = True
        by_id[event["event_id"]] = event
    return list(by_id.values()), conflict


def _coverage_status(*, source_artifacts: list[dict[str, Any]], require_full_source_coverage: bool) -> str:
    missing_optional = [item for item in source_artifacts if not item.get("exists") and not item.get("required")]
    missing_required = [item for item in source_artifacts if not item.get("exists") and item.get("required")]
    if missing_required:
        return "MISSING"
    if require_full_source_coverage and missing_optional:
        return "PARTIAL"
    return "AVAILABLE"


def _date_or_none(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is None or str(value) in {"", "NaT", "nan", "None"}:
            continue
        text = str(value)
        if "T" in text:
            text = text[:10]
        try:
            _validate_iso_date(text, field=key)
        except Exception:
            continue
        return text
    return None


def _source_hash_for(source_hashes: list[dict[str, str]], role: str) -> str:
    for item in source_hashes:
        if item.get("role") == role:
            return item.get("sha256") or ""
    return ""


def _enum_check(errors: list[str], payload: dict[str, Any], field: str, allowed: set[str]) -> None:
    if payload.get(field) not in allowed:
        errors.append(f"invalid_enum:{field}")


def _first_column(frame: Any, candidates: tuple[str, ...]) -> str:
    columns = set(frame.columns)
    return next((column for column in candidates if column in columns), "")


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
