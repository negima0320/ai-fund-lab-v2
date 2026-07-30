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
EARNINGS_CALENDAR_AUTHORITY_TYPE = "CURRENT_SNAPSHOT_CALENDAR_ONLY"
EARNINGS_CALENDAR_EXCEPTION_SCOPE = "earnings_scheduled_date_only"
EARNINGS_EVENT_WINDOW_CALENDAR_DAYS_BEFORE = 3
EARNINGS_EVENT_WINDOW_CALENDAR_DAYS_AFTER = 1

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
SOURCE_COVERAGE_SEMANTICS = {"FULL", "PARTIAL", "NONE", "UNRESOLVED", "SOURCE_NOT_APPLICABLE"}


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
        financial_statements_path=root / "jquants" / "raw" / "jquants" / "fins_summary" / "data.parquet",
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
    listed_symbols: list[str] = []
    earnings_calendar_authority = _empty_earnings_calendar_authority(business_date=business_date)
    if source_status != "MISSING":
        listed_events, listed_reasons, feature_date, listed_symbols = build_events_from_listed_issues(
            business_date=business_date,
            listed_issues_path=input_paths.listed_issues_path,
            listed_source_hash=_source_hash_for(source_hashes, "jquants_listed_issues"),
        )
        events.extend(listed_events)
        mapping_reasons.extend(listed_reasons)
        earnings_events, earnings_reasons, earnings_feature_date, earnings_calendar_authority = build_events_from_earnings_calendar(
            business_date=business_date,
            earnings_schedule_path=input_paths.earnings_schedule_path,
            earnings_source_hash=_source_hash_for(source_hashes, "jquants_earnings_schedule"),
        )
        events.extend(earnings_events)
        mapping_reasons.extend(earnings_reasons)
        feature_date = min(feature_date, earnings_feature_date) if earnings_feature_date else feature_date
        financial_events, financial_reasons, financial_feature_date = build_events_from_financial_statements(
            business_date=business_date,
            financial_statements_path=input_paths.financial_statements_path,
            financial_source_hash=_source_hash_for(source_hashes, "jquants_financial_statements"),
        )
        events.extend(financial_events)
        mapping_reasons.extend(financial_reasons)
        feature_date = min(feature_date, financial_feature_date) if financial_feature_date else feature_date
        future_leakage_used = any(reason in {"future_listed_issues_row_detected"} for reason in mapping_reasons)
    source_reason_codes_by_role = _source_reason_codes_by_role(mapping_reasons)
    if coverage == "AVAILABLE" and _pit_coverage_incomplete(source_reason_codes_by_role):
        coverage = "PARTIAL"
    coverage_contract = _coverage_contract(
        coverage_status=coverage,
        source_status=source_status,
        require_full_source_coverage=require_full_source_coverage,
    )
    effective_source_reasons = _effective_source_reasons(source_reasons, source_artifacts, require_full_source_coverage=require_full_source_coverage)
    reason_codes = sorted(set([*effective_source_reasons, *mapping_reasons]))
    if require_full_source_coverage and coverage != "AVAILABLE":
        reason_codes.append("corporate_event_source_coverage_incomplete")
    if source_status in {"HASH_MISMATCH", "AUTHORITY_CONFLICT"} or "future_listed_issues_row_rejected" in reason_codes or future_leakage_used or "invalid_event_date_ordering" in reason_codes:
        producer_status = "BLOCK"
    elif source_status in {"MISSING", "STALE"} or coverage != "AVAILABLE" or reason_codes:
        producer_status = "REVIEW_REQUIRED"
    else:
        producer_status = "PASS"
    symbol_coverage = build_symbol_event_coverage(
        business_date=business_date,
        symbols=listed_symbols,
        events=events,
        source_artifacts=source_artifacts,
        event_absence_authorized=bool(coverage_contract["event_absence_authorized"]),
        source_reason_codes_by_role=source_reason_codes_by_role,
    )
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
        "overall_coverage_status": coverage,
        "source_coverage_semantics": coverage_contract["source_coverage_semantics"],
        "coverage_contract": coverage_contract,
        "source_coverage": symbol_coverage["source_coverage"],
        "source_scoped_coverage": build_source_scoped_coverage(business_date=business_date, source_coverage=symbol_coverage["source_coverage"]),
        "earnings_calendar_authority": earnings_calendar_authority,
        "earnings_calendar_authority_type": earnings_calendar_authority.get("authority_type"),
        "earnings_calendar_snapshot_target_date": earnings_calendar_authority.get("snapshot_target_date"),
        "earnings_calendar_snapshot_fetched_at": earnings_calendar_authority.get("snapshot_fetched_at"),
        "earnings_calendar_historical_pit_compliant": earnings_calendar_authority.get("historical_pit_compliant"),
        "earnings_calendar_exception_scope": earnings_calendar_authority.get("exception_scope"),
        "approved_non_pit_calendar_exception_used": bool(earnings_calendar_authority.get("latest_materialized_snapshot_used")),
        "symbol_event_facts": symbol_coverage["symbol_event_facts"],
        "unknown_symbols": symbol_coverage["unknown_symbols"],
        "known_no_event_symbols": symbol_coverage["known_no_event_symbols"],
        "known_event_symbols": symbol_coverage["known_event_symbols"],
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
            "approved_non_pit_calendar_exception_used": bool(earnings_calendar_authority.get("latest_materialized_snapshot_used")),
            "non_calendar_future_leakage_used": future_leakage_used,
            "feature_date_lte_business_date": feature_date <= business_date,
        },
        "pit_validation": {
            "status": "PASS" if not future_leakage_used and feature_date <= business_date else "BLOCK",
            "business_date": business_date,
            "feature_date": feature_date,
            "future_leakage_used": future_leakage_used,
            "non_calendar_future_leakage_used": future_leakage_used,
            "source_date_lte_business_date": feature_date <= business_date,
            "latest_fallback_used": False,
            "non_calendar_latest_fallback_used": False,
            "earnings_calendar_authority": {
                "authority_type": earnings_calendar_authority.get("authority_type"),
                "historical_pit_compliant": earnings_calendar_authority.get("historical_pit_compliant"),
                "exception_scope": earnings_calendar_authority.get("exception_scope"),
            },
        },
        "no_event_semantics": {
            "empty_events_meaning": coverage_contract["empty_events_meaning"],
            "unknown_event_state_when_source_missing": coverage_contract["event_state"] == "UNKNOWN",
            "event_absence_authorized": coverage_contract["event_absence_authorized"],
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
        "symbol_count": len(listed_symbols),
        "unknown_symbol_count": len(symbol_coverage["unknown_symbols"]),
        "known_no_event_symbol_count": len(symbol_coverage["known_no_event_symbols"]),
        "known_event_symbol_count": len(symbol_coverage["known_event_symbols"]),
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
        ("jquants_listed_issues", input_paths.listed_issues_path, True, False, True, "listed_status_delisting_partial"),
        ("jquants_trading_calendar", input_paths.trading_calendar_path, False, True, False, "business_day_distance"),
        ("jquants_earnings_schedule", input_paths.earnings_schedule_path, False, False, True, "earnings_contract"),
        ("jquants_financial_statements", input_paths.financial_statements_path, False, False, True, "financial_statement_release"),
        ("jquants_corporate_actions", input_paths.corporate_actions_path, False, True, False, "split_merger_tob_dividend_contract"),
    ]
    source_artifacts: list[dict[str, Any]] = []
    source_hashes: list[dict[str, str]] = []
    reasons: list[str] = []
    status = "VALID"
    for role, maybe_path, required, optional, coverage_required, coverage_role in refs:
        path = Path(maybe_path) if maybe_path is not None else None
        exists = bool(path and path.is_file())
        implemented = role in {
            "jquants_listed_issues",
            "jquants_trading_calendar",
            "jquants_earnings_schedule",
            "jquants_financial_statements",
        } and exists
        source_artifacts.append(
            {
                "role": role,
                "path": str(path or ""),
                "required": required,
                "optional": optional,
                "coverage_required": coverage_required,
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
) -> tuple[list[dict[str, Any]], list[str], str, list[str]]:
    import pandas as pd

    if not Path(listed_issues_path).is_file():
        return [], ["jquants_listed_issues_missing"], business_date, []
    frame = pd.read_parquet(listed_issues_path)
    if frame.empty:
        return [], ["jquants_listed_issues_empty"], business_date, []
    date_col = _first_column(frame, ("target_date", "Date", "date", "provider_effective_date"))
    code_col = _first_column(frame, ("code", "Code", "LocalCode", "symbol"))
    if not date_col or not code_col:
        return [], ["listed_issues_required_column_missing"], business_date, []
    working = frame.copy()
    working["_event_source_date"] = working[date_col].astype(str)
    future_row_count = int((working["_event_source_date"] > business_date).sum())
    working = working[working["_event_source_date"] <= business_date].copy()
    if working.empty:
        if future_row_count:
            return [], ["future_listed_issues_row_rejected"], business_date, []
        return [], ["no_pit_listed_issues_rows"], business_date, []
    feature_date = str(working["_event_source_date"].max())
    working = working[working["_event_source_date"] == feature_date].copy()
    working["_security_code"] = working[code_col].astype(str)
    symbols = sorted(set(str(code) for code in working["_security_code"] if str(code)))
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
    return deduped, reasons, feature_date, symbols


def build_events_from_financial_statements(
    *,
    business_date: str,
    financial_statements_path: Path | None,
    financial_source_hash: str,
) -> tuple[list[dict[str, Any]], list[str], str]:
    if financial_statements_path is None or not Path(financial_statements_path).is_file():
        return [], [], ""
    import pandas as pd

    frame = pd.read_parquet(financial_statements_path)
    if frame.empty:
        return [], [], business_date
    date_col = _first_column(frame, ("DiscDate", "DisclosedDate", "disclosed_date", "announcement_date", "Date", "target_date"))
    code_col = _first_column(frame, ("Code", "LocalCode", "code", "security_code", "symbol"))
    if not date_col or not code_col:
        return [], ["financial_statements_required_column_missing"], business_date
    working = frame.copy()
    working["_event_source_date"] = working[date_col].astype(str).str[:10]
    future_row_count = int((working["_event_source_date"] > business_date).sum())
    working = working[working["_event_source_date"] <= business_date].copy()
    if working.empty:
        return [], ["future_financial_statements_row_rejected"] if future_row_count else [], business_date
    events: list[dict[str, Any]] = []
    for row in working.to_dict(orient="records"):
        code = str(row.get(code_col) or "")
        if not code:
            continue
        disclosed = _date_or_none(row, (date_col,))
        doc_type = str(row.get("TypeOfDocument") or row.get("document_type") or "")
        disc_no = str(row.get("DiscNo") or row.get("disclosure_number") or "")
        events.append(
            _event(
                security_code=code,
                event_type="EARNINGS_ANNOUNCEMENT",
                announcement_date=disclosed,
                effective_date=None,
                availability_date=disclosed,
                event_status="DISCLOSED",
                source_reference=f"jquants_fins_summary:{code}:{disclosed or business_date}:{disc_no}:{doc_type}",
                source_hash=financial_source_hash,
                revision_id=disc_no,
                reason_codes=["financial_statement_disclosure_fact"],
            )
        )
    deduped, conflict = _dedupe_events(events)
    reasons = ["duplicate_financial_statement_authority_conflict"] if conflict else []
    return deduped, reasons, str(working["_event_source_date"].max())


def build_events_from_earnings_calendar(
    *,
    business_date: str,
    earnings_schedule_path: Path | None,
    earnings_source_hash: str,
) -> tuple[list[dict[str, Any]], list[str], str, dict[str, Any]]:
    authority = _empty_earnings_calendar_authority(business_date=business_date)
    if earnings_schedule_path is None or not Path(earnings_schedule_path).is_file():
        return [], [], "", authority
    import pandas as pd

    frame = pd.read_parquet(earnings_schedule_path)
    if frame.empty:
        return [], [], business_date, {
            **authority,
            "source_name": "jquants_earnings_schedule",
            "source_ref": str(earnings_schedule_path),
            "latest_materialized_snapshot_used": True,
        }
    code_col = _first_column(frame, ("Code", "LocalCode", "code", "security_code", "symbol"))
    scheduled_col = _first_column(frame, ("ScheduledDate", "scheduled_date", "earnings_date", "announcement_date", "Date"))
    snapshot_target_col = _first_column(frame, ("target_date", "snapshot_target_date", "Date"))
    snapshot_fetched_col = _first_column(frame, ("fetched_at", "snapshot_fetched_at"))
    forbidden_future_cols = [
        column
        for column in frame.columns
        if str(column)
        in {
            "DiscDate",
            "DiscTime",
            "NetSales",
            "OperatingProfit",
            "OrdinaryProfit",
            "Profit",
            "EarningsPerShare",
            "Dividend",
            "ForecastRevision",
            "Forecast",
        }
    ]
    ignored_non_scope_cols = [column for column in frame.columns if str(column) in {"PublicationDate", "publication_date", "CoName", "FY", "FQ", "SectorNm", "Section"}]
    authority = {
        **authority,
        "source_name": "jquants_earnings_schedule",
        "source_ref": str(earnings_schedule_path),
        "latest_materialized_snapshot_used": True,
        "scheduled_date_column": scheduled_col,
        "code_column": code_col,
        "snapshot_target_date": _max_date_from_column(frame, snapshot_target_col),
        "snapshot_fetched_at": _max_text_from_column(frame, snapshot_fetched_col),
        "row_count": int(len(frame)),
        "consumer_allowed_fields": ["Code", scheduled_col, snapshot_target_col, snapshot_fetched_col],
        "ignored_non_scope_columns_present": sorted(ignored_non_scope_cols),
        "consumer_forbidden_columns_present": sorted(forbidden_future_cols),
        "event_window": {
            "calendar_days_before": EARNINGS_EVENT_WINDOW_CALENDAR_DAYS_BEFORE,
            "calendar_days_after": EARNINGS_EVENT_WINDOW_CALENDAR_DAYS_AFTER,
        },
    }
    if not code_col or not scheduled_col:
        return [], ["earnings_calendar_required_column_missing"], business_date, authority
    if not _earnings_calendar_snapshot_exception_allowed(source="earnings_calendar", field=scheduled_col, purpose="earnings_event_window"):
        return [], ["earnings_calendar_exception_scope_violation"], business_date, authority
    if forbidden_future_cols:
        return [], ["earnings_calendar_forbidden_future_columns_present"], business_date, authority
    working = frame.copy()
    working["_scheduled_date"] = working[scheduled_col].astype(str).str[:10]
    working = working[working["_scheduled_date"].map(lambda value: _valid_date_text(str(value)))].copy()
    if working.empty:
        return [], ["earnings_calendar_no_valid_scheduled_date"], business_date, authority
    scheduled_min = str(working["_scheduled_date"].min())
    scheduled_max = str(working["_scheduled_date"].max())
    authority = {
        **authority,
        "scheduled_date_min": scheduled_min,
        "scheduled_date_max": scheduled_max,
        "valid_scheduled_row_count": int(len(working)),
    }
    events: list[dict[str, Any]] = []
    skipped_undecided = 0
    outside_window = 0
    for row in working.to_dict(orient="records"):
        code = str(row.get(code_col) or "")
        if not code:
            continue
        scheduled = _date_or_none(row, ("_scheduled_date", scheduled_col))
        if not scheduled:
            skipped_undecided += 1
            continue
        if not _scheduled_date_in_event_window(business_date=business_date, scheduled_date=scheduled):
            outside_window += 1
            continue
        events.append(
            _event(
                security_code=code,
                event_type="EARNINGS_ANNOUNCEMENT",
                announcement_date=None,
                effective_date=scheduled,
                availability_date=business_date,
                event_status="SCHEDULED",
                source_reference=f"jquants_earnings_calendar_current_snapshot:{code}:{scheduled}:{authority.get('snapshot_target_date') or ''}:{authority.get('snapshot_fetched_at') or ''}",
                source_hash=earnings_source_hash,
                revision_id="",
                reason_codes=["earnings_calendar_scheduled_date_current_snapshot_exception"],
            )
        )
    deduped, conflict = _dedupe_events(events)
    reasons: list[str] = []
    if conflict:
        reasons.append("duplicate_earnings_calendar_authority_conflict")
    if skipped_undecided:
        reasons.append("earnings_calendar_undecided_schedule_skipped")
    return deduped, reasons, business_date, {
        **authority,
        "window_event_count": len(deduped),
        "outside_window_row_count": outside_window,
    }


def build_symbol_event_coverage(
    *,
    business_date: str,
    symbols: list[str],
    events: list[dict[str, Any]],
    source_artifacts: list[dict[str, Any]],
    event_absence_authorized: bool,
    source_reason_codes_by_role: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    source_reason_codes_by_role = source_reason_codes_by_role or {}
    symbols = sorted(set(str(symbol) for symbol in symbols if str(symbol)))
    events_by_symbol: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
    for event in events:
        code = str(event.get("security_code") or "")
        if code:
            events_by_symbol.setdefault(code, []).append(event)
    source_coverage = []
    for item in source_artifacts:
        role = str(item.get("role") or "")
        exists = bool(item.get("exists"))
        implemented = bool(item.get("implemented"))
        required = bool(item.get("required"))
        missing_required = bool(item.get("required")) and not exists
        role_reasons = list(source_reason_codes_by_role.get(role) or [])
        if exists and implemented and role_reasons:
            status = "PARTIAL"
            reason_codes = role_reasons
        elif exists and implemented:
            status = "AVAILABLE"
            reason_codes: list[str] = []
        elif missing_required:
            status = "MISSING_REQUIRED"
            reason_codes = [f"{item.get('role')}_missing"]
        elif exists:
            status = "RAW_EXISTS_NOT_CONNECTED"
            reason_codes = [f"{item.get('role')}_not_implemented"]
        else:
            status = "UNKNOWN_DUE_TO_MISSING_COVERAGE"
            reason_codes = [f"{item.get('role')}_not_implemented_or_missing"]
        source_coverage.append(
            {
                "source_name": item.get("role"),
                "business_date": business_date,
                "coverage_status": status,
                "source_ref": item.get("path") or "",
                "implemented": implemented,
                "exists": exists,
                "reason_codes": reason_codes,
            }
        )
    missing_sources = [
        item
        for item in source_coverage
        if item["coverage_status"] == "MISSING_REQUIRED"
        or (not event_absence_authorized and item["coverage_status"] == "PARTIAL")
        or (
            not event_absence_authorized
            and item["coverage_status"] in {"UNKNOWN_DUE_TO_MISSING_COVERAGE", "RAW_EXISTS_NOT_CONNECTED"}
            and any(source.get("role") == item["source_name"] and (source.get("required") or source.get("coverage_required")) for source in source_artifacts)
        )
    ]
    symbol_facts = []
    for symbol in sorted(set([*symbols, *events_by_symbol])):
        symbol_events = events_by_symbol.get(symbol, [])
        if symbol_events:
            event_status = "KNOWN_EVENT"
        elif missing_sources:
            event_status = "UNKNOWN_DUE_TO_MISSING_COVERAGE"
        else:
            event_status = "KNOWN_NO_EVENT"
        symbol_facts.append(
            {
                "security_code": symbol,
                "business_date": business_date,
                "coverage_status": "PARTIAL" if missing_sources else "AVAILABLE",
                "event_status": event_status,
                "event_types": sorted(set(str(event.get("event_type") or "") for event in symbol_events if event.get("event_type"))),
                "event_dates": sorted(set(str(event.get("availability_date") or event.get("announcement_date") or "") for event in symbol_events if event.get("availability_date") or event.get("announcement_date"))),
                "available_at": business_date,
                "source_ref": "corporate_event.source_coverage",
                "reason_codes": sorted(set(reason for item in missing_sources for reason in item.get("reason_codes", []))),
            }
        )
    return {
        "source_coverage": source_coverage,
        "symbol_event_facts": symbol_facts,
        "unknown_symbols": sorted(item["security_code"] for item in symbol_facts if item["event_status"] == "UNKNOWN_DUE_TO_MISSING_COVERAGE"),
        "known_no_event_symbols": sorted(item["security_code"] for item in symbol_facts if item["event_status"] == "KNOWN_NO_EVENT"),
        "known_event_symbols": sorted(item["security_code"] for item in symbol_facts if item["event_status"] == "KNOWN_EVENT"),
    }


def build_source_scoped_coverage(*, business_date: str, source_coverage: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    source_by_name = {str(item.get("source_name") or ""): item for item in source_coverage}
    mapping = {
        "listing_status_coverage": "jquants_listed_issues",
        "earnings_calendar_coverage": "jquants_earnings_schedule",
        "financial_statement_coverage": "jquants_financial_statements",
        "stock_split_coverage": "jquants_corporate_actions",
        "tdnet_disclosure_coverage": "jquants_corporate_actions",
    }
    scoped: dict[str, dict[str, Any]] = {}
    for output_name, source_name in mapping.items():
        item = source_by_name.get(source_name, {})
        reason_codes = list(item.get("reason_codes") or []) if item else [f"{source_name}_not_implemented_or_missing"]
        scoped[output_name] = {
            "business_date": business_date,
            "source_name": source_name,
            "coverage_status": item.get("coverage_status") or "UNKNOWN_DUE_TO_MISSING_COVERAGE",
            "implemented": bool(item.get("implemented")),
            "exists": bool(item.get("exists")),
            "source_ref": item.get("source_ref") or "",
            "reason_codes": reason_codes,
        }
    return scoped


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
    if "source_coverage_semantics" in payload:
        _enum_check(errors, payload, "source_coverage_semantics", SOURCE_COVERAGE_SEMANTICS)
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
    contract = payload.get("coverage_contract")
    if contract is not None and not isinstance(contract, dict):
        errors.append("coverage_contract_not_object")
    elif isinstance(contract, dict) and contract.get("missing_source_treated_as_no_event") is not False:
        errors.append("missing_source_treated_as_no_event_forbidden")
    if not isinstance(temporal, dict):
        errors.append("temporal_safety_not_object")
    elif temporal.get("future_leakage_used") is True and payload.get("producer_result_status") != "BLOCK":
        errors.append("future_leakage_must_block")
    if payload.get("approved_non_pit_calendar_exception_used") is True:
        authority = payload.get("earnings_calendar_authority")
        if not isinstance(authority, dict):
            errors.append("earnings_calendar_authority_metadata_missing")
        else:
            if authority.get("authority_type") != EARNINGS_CALENDAR_AUTHORITY_TYPE:
                errors.append("invalid_earnings_calendar_authority_type")
            if authority.get("exception_scope") != EARNINGS_CALENDAR_EXCEPTION_SCOPE:
                errors.append("invalid_earnings_calendar_exception_scope")
            if authority.get("historical_pit_compliant") is not False:
                errors.append("earnings_calendar_exception_must_be_non_pit_labeled")
            if authority.get("latest_materialized_snapshot_used") is not True:
                errors.append("earnings_calendar_snapshot_usage_not_labeled")
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
    missing_required = [item for item in source_artifacts if not item.get("exists") and item.get("required")]
    missing_coverage_required = [item for item in source_artifacts if not item.get("exists") and item.get("coverage_required")]
    if missing_required:
        return "MISSING"
    if require_full_source_coverage and missing_coverage_required:
        return "PARTIAL"
    return "AVAILABLE"


def _source_reason_codes_by_role(mapping_reasons: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for reason in mapping_reasons:
        if reason.startswith("future_earnings_calendar") or reason.startswith("earnings_calendar_"):
            result.setdefault("jquants_earnings_schedule", []).append(reason)
        elif reason.startswith("future_financial_statements") or reason.startswith("financial_statements_") or reason.startswith("duplicate_financial_statement"):
            result.setdefault("jquants_financial_statements", []).append(reason)
        elif reason.startswith("future_listed_issues") or reason.startswith("listed_issues_") or reason in {"duplicate_authority_conflict", "invalid_event_date_ordering"}:
            result.setdefault("jquants_listed_issues", []).append(reason)
    return {role: sorted(set(reasons)) for role, reasons in result.items()}


def _pit_coverage_incomplete(source_reason_codes_by_role: dict[str, list[str]]) -> bool:
    return any(source_reason_codes_by_role.get(role) for role in ("jquants_earnings_schedule", "jquants_financial_statements", "jquants_listed_issues"))


def _effective_source_reasons(source_reasons: list[str], source_artifacts: list[dict[str, Any]], *, require_full_source_coverage: bool) -> list[str]:
    optional_roles = {str(item.get("role") or "") for item in source_artifacts if item.get("optional")}
    coverage_required_roles = {str(item.get("role") or "") for item in source_artifacts if item.get("coverage_required")}
    effective = []
    for reason in source_reasons:
        role = reason.removesuffix("_not_implemented_or_missing").removesuffix("_missing")
        if role in optional_roles and reason.endswith("_not_implemented_or_missing"):
            continue
        if role in coverage_required_roles and reason.endswith("_not_implemented_or_missing") and not require_full_source_coverage:
            continue
        effective.append(reason)
    return sorted(set(effective))


def _coverage_contract(*, coverage_status: str, source_status: str, require_full_source_coverage: bool) -> dict[str, Any]:
    if source_status == "MISSING" or coverage_status == "MISSING":
        semantics = "NONE"
        event_state = "UNKNOWN"
        blocking_scope = "ALL_EVENT_SENSITIVE_RULES"
        calculation_eligibility = "CALCULATION_NOT_ALLOWED_FOR_EVENT_SENSITIVE_RULES"
        absence_authorized = False
    elif coverage_status == "PARTIAL":
        semantics = "PARTIAL"
        event_state = "PARTIAL_AUTHORITY"
        blocking_scope = "EVENT_SENSITIVE_RULES_ONLY"
        calculation_eligibility = "CALCULATION_ALLOWED_WITH_REVIEW_FOR_EVENT_INDEPENDENT_RULES"
        absence_authorized = False
    elif coverage_status == "AVAILABLE":
        semantics = "FULL" if require_full_source_coverage else "PARTIAL"
        event_state = "KNOWN"
        blocking_scope = "NONE"
        calculation_eligibility = "CALCULATION_ALLOWED"
        absence_authorized = True
    else:
        semantics = "UNRESOLVED"
        event_state = "UNKNOWN"
        blocking_scope = "ALL_EVENT_SENSITIVE_RULES"
        calculation_eligibility = "CALCULATION_NOT_ALLOWED_FOR_EVENT_SENSITIVE_RULES"
        absence_authorized = False
    return {
        "source_coverage_semantics": semantics,
        "event_state": event_state,
        "blocking_scope": blocking_scope,
        "downstream_calculation_scope": calculation_eligibility,
        "event_absence_authorized": absence_authorized,
        "empty_events_meaning": "NO_EVENTS_WITH_AUTHORITY" if absence_authorized else "UNKNOWN_EVENTS_DO_NOT_TREAT_AS_NO_EVENT",
        "partial_coverage_may_pass": False,
        "missing_source_treated_as_no_event": False,
        "silent_default_used": False,
        "external_non_jquants_source_used": False,
    }


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


def _empty_earnings_calendar_authority(*, business_date: str) -> dict[str, Any]:
    return {
        "source_name": "jquants_earnings_schedule",
        "authority_type": EARNINGS_CALENDAR_AUTHORITY_TYPE,
        "latest_materialized_snapshot_used": False,
        "historical_pit_compliant": False,
        "exception_scope": EARNINGS_CALENDAR_EXCEPTION_SCOPE,
        "historical_business_date": business_date,
        "purpose": "earnings_event_window",
        "guardrail": {
            "allowed_source": "earnings_calendar",
            "allowed_field_family": ["ScheduledDate", "scheduled_date", "earnings_date", "announcement_date", "Date"],
            "allowed_purpose": "earnings_event_window",
            "non_calendar_future_leakage_allowed": False,
        },
    }


def _earnings_calendar_snapshot_exception_allowed(*, source: str, field: str, purpose: str) -> bool:
    return (
        source == "earnings_calendar"
        and field in {"ScheduledDate", "scheduled_date", "earnings_date", "announcement_date", "Date"}
        and purpose == "earnings_event_window"
    )


def _scheduled_date_in_event_window(*, business_date: str, scheduled_date: str) -> bool:
    business = date.fromisoformat(business_date)
    scheduled = date.fromisoformat(scheduled_date)
    lower = business.fromordinal(business.toordinal() - EARNINGS_EVENT_WINDOW_CALENDAR_DAYS_AFTER)
    upper = business.fromordinal(business.toordinal() + EARNINGS_EVENT_WINDOW_CALENDAR_DAYS_BEFORE)
    return lower <= scheduled <= upper


def _max_date_from_column(frame: Any, column: str) -> str | None:
    if not column:
        return None
    values = [str(value)[:10] for value in frame[column].dropna().tolist()]
    valid = [value for value in values if _valid_date_text(value)]
    return max(valid) if valid else None


def _max_text_from_column(frame: Any, column: str) -> str | None:
    if not column:
        return None
    values = [str(value) for value in frame[column].dropna().tolist() if str(value) not in {"", "NaT", "nan", "None"}]
    return max(values) if values else None


def _valid_date_text(value: str) -> bool:
    text = value[:10] if "T" in value else value
    try:
        _validate_iso_date(text, field="date")
    except Exception:
        return False
    return True


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
