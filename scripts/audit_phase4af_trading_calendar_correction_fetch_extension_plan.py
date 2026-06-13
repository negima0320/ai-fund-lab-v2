#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.data_store.storage_backends import StorageBackendError, create_storage_backend  # noqa: E402

PHASE4AE_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ae_post_fetch_raw_coverage_summary.json")
RAW_ROOT = Path(".runtime/data/raw/jquants/equities_bars_daily")
TRADING_CALENDAR_BASE_PATH = Path(".runtime/data/raw/jquants/trading_calendar/data")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4af_trading_calendar_correction_fetch_extension_plan_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4af_trading_calendar_correction_fetch_extension_plan_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4af_trading_calendar_correction_fetch_extension_plan_audit.md")

READY_EXTENSION = "READY_FOR_EXTENSION_FETCH_DRY_RUN"
READY_NORMALIZE = "READY_FOR_REAL_RUNTIME_NORMALIZED_REBUILD"
BLOCKED_MISSING_AE = "BLOCKED_BY_MISSING_PHASE4AE_SUMMARY"
BLOCKED_AE_NOT_COVERAGE_GAP = "BLOCKED_BY_PHASE4AE_NOT_COVERAGE_GAP"
BLOCKED_CALENDAR = "BLOCKED_BY_TRADING_CALENDAR_CLASSIFICATION"
BLOCKED_UNEXPECTED_EMPTY = "BLOCKED_BY_UNEXPECTED_EMPTY_TRADING_DATES"
BLOCKED_EXTENSION_PLAN = "BLOCKED_BY_EXTENSION_PLAN"
BLOCKED_OUTPUT_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"
BLOCKED_SECRET = "BLOCKED_BY_SECRET_SAFETY"

REQUIRED_NON_EMPTY_TRADING_DAYS = 60
ENDPOINT = "/v2/equities/bars/daily"
SECRET_MARKERS = ("Authorization", "x-api-key", "password", "cookie", "id_token", "refresh_token")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    phase4ae_summary_path: Path = PHASE4AE_SUMMARY_PATH,
    raw_root: Path = RAW_ROOT,
    trading_calendar_base_path: Path = TRADING_CALENDAR_BASE_PATH,
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = build_extension_plan_summary(
        phase4ae_summary_path=phase4ae_summary_path,
        raw_root=raw_root,
        trading_calendar_base_path=trading_calendar_base_path,
        summary_path=summary_path,
    )
    checks = {
        "summary_exists": summary_path.is_file(),
        "phase4ae_summary_detected": summary.get("phase4ae_summary_detected") is True,
        "calendar_classification_produced": summary.get("calendar_classification_status") in {"OK", "ERROR"},
        "empty_response_dates_classified": len(summary.get("original_empty_response_dates") or [])
        == len(summary.get("expected_empty_market_closed_dates") or [])
        + len(summary.get("unexpected_empty_trading_dates") or []),
        "coverage_decision_produced": summary.get("readiness_status")
        in {
            READY_EXTENSION,
            READY_NORMALIZE,
            BLOCKED_MISSING_AE,
            BLOCKED_AE_NOT_COVERAGE_GAP,
            BLOCKED_CALENDAR,
            BLOCKED_UNEXPECTED_EMPTY,
            BLOCKED_EXTENSION_PLAN,
            BLOCKED_OUTPUT_PATH,
            BLOCKED_SECRET,
        },
        "no_live_no_fetch": summary.get("api_call_performed") is False
        and summary.get("additional_fetch_executed") is False
        and summary.get("credential_read_performed") is False
        and summary.get("http_client_initialized") is False,
        "no_raw_or_normalized_write": summary.get("raw_data_written") is False
        and summary.get("normalized_data_written") is False,
        "no_promotion_or_reader_switch": summary.get("promotion_performed") is False
        and summary.get("reader_switch_performed") is False,
        "feature_label_training_backtest_trading_not_executed": summary.get("feature_generation_executed") is False
        and summary.get("label_generation_executed") is False
        and summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "secret_not_detected": summary.get("secret_value_detected") is False,
        "extension_plan_defined_when_required": (
            summary.get("extension_fetch_required") is False
            or int(summary.get("extension_request_count") or 0) == int(summary.get("true_missing_non_empty_trading_day_count") or 0)
        ),
    }
    result = {
        "phase": "Phase4-AF",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4af_trading_calendar_correction_fetch_extension_plan.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def build_extension_plan_summary(
    *,
    phase4ae_summary_path: Path = PHASE4AE_SUMMARY_PATH,
    raw_root: Path = RAW_ROOT,
    trading_calendar_base_path: Path = TRADING_CALENDAR_BASE_PATH,
    summary_path: Path = SUMMARY_PATH,
) -> dict[str, Any]:
    phase4ae = _read_json_optional(phase4ae_summary_path)
    if not phase4ae:
        return _write_summary(summary_path, _blocked_summary(BLOCKED_MISSING_AE))
    if phase4ae.get("readiness_status") != "BLOCKED_BY_COVERAGE_GAP":
        return _write_summary(summary_path, _blocked_summary(BLOCKED_AE_NOT_COVERAGE_GAP, phase4ae=phase4ae))
    if not _output_paths_safe(raw_root):
        return _write_summary(summary_path, _blocked_summary(BLOCKED_OUTPUT_PATH, phase4ae=phase4ae))

    calendar_records = _load_calendar_records(trading_calendar_base_path)
    if not calendar_records:
        return _write_summary(summary_path, _blocked_summary(BLOCKED_CALENDAR, phase4ae=phase4ae))
    calendar = _calendar_by_date(calendar_records)

    original_empty_dates = sorted(str(day) for day in phase4ae.get("empty_response_dates") or [])
    fetched_non_empty_dates = sorted(str(day) for day in phase4ae.get("fetched_dates") or [])
    requested_dates = _load_requested_dates(raw_root)
    response_dates = _load_response_dates(raw_root)

    expected_empty_market_closed_dates: list[str] = []
    unexpected_empty_trading_dates: list[str] = []
    market_closed_dates: list[str] = []
    for target_date in original_empty_dates:
        if is_market_open_day(target_date, calendar):
            unexpected_empty_trading_dates.append(target_date)
        else:
            expected_empty_market_closed_dates.append(target_date)
            market_closed_dates.append(target_date)

    fetched_non_empty_trading_dates = [day for day in fetched_non_empty_dates if is_market_open_day(day, calendar)]
    fetched_non_empty_count = len(fetched_non_empty_trading_dates)
    true_missing_count = max(0, REQUIRED_NON_EMPTY_TRADING_DAYS - fetched_non_empty_count)
    coverage_sufficient = fetched_non_empty_count >= REQUIRED_NON_EMPTY_TRADING_DAYS
    extension_required = not coverage_sufficient and not unexpected_empty_trading_dates

    extension_dates: list[str] = []
    if extension_required and fetched_non_empty_trading_dates:
        extension_dates = plan_previous_market_open_dates(
            before_date=fetched_non_empty_trading_dates[0],
            count=true_missing_count,
            calendar=calendar,
            existing_dates=set(fetched_non_empty_trading_dates),
        )
    expected_after_extension = fetched_non_empty_count + len(extension_dates)

    june_1 = classify_date(
        "2026-06-01",
        calendar=calendar,
        requested_dates=set(requested_dates),
        response_dates=set(response_dates),
        fetched_non_empty_dates=set(fetched_non_empty_dates),
        empty_response_dates=set(original_empty_dates),
    )

    secret_detected = _has_secret_terms({"phase4ae": phase4ae, "calendar_sample": calendar_records[:5]})
    readiness_status = _readiness_status(
        secret_detected=secret_detected,
        unexpected_empty_trading_dates=unexpected_empty_trading_dates,
        coverage_sufficient=coverage_sufficient,
        extension_required=extension_required,
        extension_dates=extension_dates,
        true_missing_count=true_missing_count,
    )
    summary = {
        "status": "OK" if readiness_status in {READY_EXTENSION, READY_NORMALIZE} else "BLOCKED",
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "additional_fetch_executed": False,
        "credential_read_performed": False,
        "http_client_initialized": False,
        "raw_data_written": False,
        "normalized_data_written": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "phase4ae_summary_detected": True,
        "phase4ae_readiness_status": phase4ae.get("readiness_status"),
        "calendar_classification_status": "ERROR" if readiness_status == BLOCKED_CALENDAR else "OK",
        "original_empty_response_dates": original_empty_dates,
        "market_closed_dates": sorted(set(market_closed_dates)),
        "unexpected_empty_trading_dates": unexpected_empty_trading_dates,
        "expected_empty_market_closed_dates": expected_empty_market_closed_dates,
        "fetched_non_empty_dates": fetched_non_empty_dates,
        "fetched_non_empty_trading_dates": fetched_non_empty_trading_dates,
        "fetched_non_empty_trading_day_count": fetched_non_empty_count,
        "required_non_empty_trading_day_count": REQUIRED_NON_EMPTY_TRADING_DAYS,
        "true_missing_non_empty_trading_day_count": true_missing_count,
        "coverage_sufficient_after_calendar_correction": coverage_sufficient,
        "current_effective_date_min": fetched_non_empty_trading_dates[0] if fetched_non_empty_trading_dates else None,
        "current_effective_date_max": fetched_non_empty_trading_dates[-1] if fetched_non_empty_trading_dates else None,
        "latest_non_empty_date": fetched_non_empty_trading_dates[-1] if fetched_non_empty_trading_dates else None,
        "target_end_date_recommended": fetched_non_empty_trading_dates[-1] if fetched_non_empty_trading_dates else None,
        "extension_fetch_required": extension_required,
        "extension_fetch_start_date": extension_dates[0] if extension_dates else None,
        "extension_fetch_end_date": extension_dates[-1] if extension_dates else None,
        "extension_request_count": len(extension_dates),
        "extension_requested_dates": extension_dates,
        "expected_non_empty_trading_day_count_after_extension": expected_after_extension,
        "june_1_classification": june_1,
        "merge_policy_defined": True,
        "merge_policy": (
            "Extension fetch writes only new request/response manifests for extension_requested_dates under the same raw root; "
            "existing successful request manifests and response files are preserved and not overwritten."
        ),
        "existing_raw_preserved": True,
        "existing_success_manifest_preserved": True,
        "extension_plan_defined": extension_required is False or len(extension_dates) == true_missing_count,
        "secret_value_detected": secret_detected,
        "normalized_output_written": False,
        "mock_path_written": False,
        "isolated_normalized_path_written": False,
        "recommended_next_action": _recommended_next_action(
            readiness_status=readiness_status,
            extension_required=extension_required,
        ),
    }
    return _write_summary(summary_path, summary)


def is_market_open_day(target_date: str, calendar: dict[str, dict[str, Any]]) -> bool:
    parsed = date.fromisoformat(target_date)
    if parsed.weekday() >= 5:
        return False
    if target_date in known_japan_market_closed_dates(parsed.year):
        return False
    record = calendar.get(target_date)
    if record is None:
        return True
    hol_div = str(record.get("HolDiv") or record.get("HolidayDivision") or "")
    if hol_div in {"0", "2"}:
        return False
    return True


def known_japan_market_closed_dates(year: int) -> set[str]:
    fixed_by_year: dict[int, set[str]] = {
        2026: {
            "2026-01-01",
            "2026-01-02",
            "2026-01-12",
            "2026-02-11",
            "2026-02-23",
            "2026-03-20",
            "2026-04-29",
            "2026-05-04",
            "2026-05-05",
            "2026-05-06",
            "2026-07-20",
            "2026-08-11",
            "2026-09-21",
            "2026-09-22",
            "2026-09-23",
            "2026-10-12",
            "2026-11-03",
            "2026-11-23",
            "2026-12-31",
        }
    }
    return fixed_by_year.get(year, {f"{year}-01-01", f"{year}-01-02", f"{year}-12-31"})


def classify_date(
    target_date: str,
    *,
    calendar: dict[str, dict[str, Any]],
    requested_dates: set[str],
    response_dates: set[str],
    fetched_non_empty_dates: set[str],
    empty_response_dates: set[str],
) -> dict[str, Any]:
    is_requested = target_date in requested_dates
    response_exists = target_date in response_dates
    is_non_empty = target_date in fetched_non_empty_dates
    is_empty = target_date in empty_response_dates
    is_open = is_market_open_day(target_date, calendar)
    if is_non_empty:
        classification = "fetched_non_empty_trading_date" if is_open else "fetched_non_empty_market_closed_date"
    elif is_empty:
        classification = "unexpected_empty_trading_date" if is_open else "expected_empty_market_closed"
    elif not is_requested and not response_exists:
        classification = "missing_requested_trading_date" if is_open else "not_requested_market_closed"
    else:
        classification = "requested_without_non_empty_data" if is_open else "requested_market_closed_without_data"
    return {
        "date": target_date,
        "requested": is_requested,
        "response_file_exists": response_exists,
        "data_empty": is_empty,
        "data_non_empty": is_non_empty,
        "market_open": is_open,
        "classification": classification,
        "note": (
            "2026-06-01 was not part of the AD extension requests because it existed as the isolated current date; "
            "do not use it as latest raw coverage until raw daily quotes are explicitly fetched."
            if target_date == "2026-06-01" and not is_requested and not response_exists
            else ""
        ),
    }


def plan_previous_market_open_dates(
    *,
    before_date: str,
    count: int,
    calendar: dict[str, dict[str, Any]],
    existing_dates: set[str],
) -> list[str]:
    if count <= 0:
        return []
    current = date.fromisoformat(before_date) - timedelta(days=1)
    planned: list[str] = []
    guard = 0
    while len(planned) < count and guard < 370:
        value = current.isoformat()
        if value not in existing_dates and is_market_open_day(value, calendar):
            planned.append(value)
        current -= timedelta(days=1)
        guard += 1
    return sorted(planned)


def _readiness_status(
    *,
    secret_detected: bool,
    unexpected_empty_trading_dates: list[str],
    coverage_sufficient: bool,
    extension_required: bool,
    extension_dates: list[str],
    true_missing_count: int,
) -> str:
    if secret_detected:
        return BLOCKED_SECRET
    if unexpected_empty_trading_dates:
        return BLOCKED_UNEXPECTED_EMPTY
    if coverage_sufficient:
        return READY_NORMALIZE
    if extension_required and len(extension_dates) == true_missing_count:
        return READY_EXTENSION
    return BLOCKED_EXTENSION_PLAN


def _blocked_summary(status: str, *, phase4ae: dict[str, Any] | None = None) -> dict[str, Any]:
    phase4ae = phase4ae or {}
    return {
        "status": "BLOCKED",
        "readiness_status": status,
        "api_call_performed": False,
        "additional_fetch_executed": False,
        "credential_read_performed": False,
        "http_client_initialized": False,
        "raw_data_written": False,
        "normalized_data_written": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "phase4ae_summary_detected": bool(phase4ae),
        "phase4ae_readiness_status": phase4ae.get("readiness_status"),
        "calendar_classification_status": "ERROR",
        "original_empty_response_dates": list(phase4ae.get("empty_response_dates") or []),
        "market_closed_dates": [],
        "unexpected_empty_trading_dates": [],
        "expected_empty_market_closed_dates": [],
        "fetched_non_empty_dates": list(phase4ae.get("fetched_dates") or []),
        "fetched_non_empty_trading_day_count": int(phase4ae.get("fetched_business_day_count") or 0),
        "required_non_empty_trading_day_count": REQUIRED_NON_EMPTY_TRADING_DAYS,
        "true_missing_non_empty_trading_day_count": max(
            0, REQUIRED_NON_EMPTY_TRADING_DAYS - int(phase4ae.get("fetched_business_day_count") or 0)
        ),
        "coverage_sufficient_after_calendar_correction": False,
        "current_effective_date_min": phase4ae.get("fetched_date_min"),
        "current_effective_date_max": phase4ae.get("fetched_date_max"),
        "latest_non_empty_date": phase4ae.get("fetched_date_max"),
        "target_end_date_recommended": phase4ae.get("fetched_date_max"),
        "extension_fetch_required": False,
        "extension_fetch_start_date": None,
        "extension_fetch_end_date": None,
        "extension_request_count": 0,
        "extension_requested_dates": [],
        "expected_non_empty_trading_day_count_after_extension": int(phase4ae.get("fetched_business_day_count") or 0),
        "june_1_classification": {},
        "merge_policy_defined": False,
        "existing_raw_preserved": True,
        "existing_success_manifest_preserved": True,
        "extension_plan_defined": False,
        "secret_value_detected": False,
        "normalized_output_written": False,
        "mock_path_written": False,
        "isolated_normalized_path_written": False,
        "recommended_next_action": "Resolve the blocking condition before Phase4-AG.",
    }


def _load_calendar_records(base_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for storage_format in ("jsonl", "parquet"):
        backend = create_storage_backend(storage_format)
        path = backend.path_for(base_path)
        if not path.exists():
            continue
        try:
            records = backend.read_records(path)
            if records:
                break
        except (StorageBackendError, ImportError, RuntimeError):
            continue
    return records


def _calendar_by_date(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(record.get("Date") or record.get("target_date")): dict(record)
        for record in records
        if str(record.get("Date") or record.get("target_date") or "")
    }


def _load_requested_dates(raw_root: Path) -> list[str]:
    dates: set[str] = set()
    for path in sorted((raw_root / "request_manifests").glob("*.json")):
        record = _read_json_optional(path)
        value = str(record.get("target_date") or record.get("request_params", {}).get("date") or path.stem)
        if value:
            dates.add(value)
    return sorted(dates)


def _load_response_dates(raw_root: Path) -> list[str]:
    dates: set[str] = set()
    for path in sorted((raw_root / "responses").glob("*.json")):
        record = _read_json_optional(path)
        value = str(record.get("date") or record.get("params", {}).get("date") or path.name.split("_page_")[0])
        if value:
            dates.add(value)
    return sorted(dates)


def _output_paths_safe(raw_root: Path) -> bool:
    text = str(raw_root)
    return "raw/jquants/equities_bars_daily" in text and "raw_normalized" not in text


def _recommended_next_action(*, readiness_status: str, extension_required: bool) -> str:
    if readiness_status == READY_EXTENSION and extension_required:
        return "Phase4-AG Real Runtime Extension Fetch Dry-run: render extension_requested_dates without API calls."
    if readiness_status == READY_NORMALIZE:
        return "Phase4-AG Real Runtime Normalized Rebuild from Raw."
    return "Resolve the blocking condition and rerun Phase4-AF."


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "phase4ae_readiness_status",
        "original_empty_response_dates",
        "expected_empty_market_closed_dates",
        "unexpected_empty_trading_dates",
        "fetched_non_empty_trading_day_count",
        "required_non_empty_trading_day_count",
        "true_missing_non_empty_trading_day_count",
        "coverage_sufficient_after_calendar_correction",
        "latest_non_empty_date",
        "target_end_date_recommended",
        "extension_fetch_required",
        "extension_fetch_start_date",
        "extension_fetch_end_date",
        "extension_request_count",
        "extension_requested_dates",
        "expected_non_empty_trading_day_count_after_extension",
        "june_1_classification",
        "merge_policy_defined",
        "recommended_next_action",
    )
    return {key: summary.get(key) for key in keys}


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_summary(path: Path, summary: dict[str, Any]) -> dict[str, Any]:
    _write_json(path, summary)
    return summary


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AF Trading Calendar Correction / Fetch Range Extension Plan Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- readiness_status: `{result.get('readiness_status')}`",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Checks", ""])
    for name, value in result["checks"].items():
        mark = "OK" if value else "NG"
        lines.append(f"- {mark}: `{name}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- Phase4-AF is a no-live plan and audit only.",
            "- It does not call APIs, fetch, refetch, write raw/normalized data, promote data, switch readers, generate features, generate labels, train, infer, backtest, trade, place orders, or update Portfolio state.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _has_secret_terms(payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    return any(marker in text for marker in SECRET_MARKERS)


if __name__ == "__main__":
    raise SystemExit(main())
