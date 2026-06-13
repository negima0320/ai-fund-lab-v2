#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.config.settings import ConfigurationError, load_settings  # noqa: E402

PHASE = "Phase4-AY"
ENDPOINT = "/v2/equities/bars/daily"
CHECKED_DATE_MIN = "2021-06-01"
CHECKED_DATE_MAX = "2021-06-14"
USER_EXPECTED_START_DATE = "2021-06-01"
AX2_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ax2_http400_root_cause_summary.json")
RAW_DIR = Path(".runtime/data/raw/jquants/equities_bars_daily")
CALENDAR_JSONL = Path(".runtime/data/raw/jquants/trading_calendar/data.jsonl")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ay_border_date_availability_summary.json")
REPORT_PATH = Path("docs/phase_reports/phase4ay_border_date_availability.md")

READY = "READY_FOR_LONG_HISTORY_REQUEST_REGENERATION"
BLOCKED_UNKNOWN = "BLOCKED_BY_BORDER_DATE_UNKNOWN"
BLOCKED_API_FORMAT = "BLOCKED_BY_API_FORMAT"
BLOCKED_SECRET = "BLOCKED_BY_SECRET_SAFETY"


@dataclass(frozen=True)
class BoundaryResponse:
    target_date: str
    http_status: int | str
    response_message: str
    row_count: int = 0
    payload_keys: tuple[str, ...] = ()


def main() -> int:
    summary = audit_phase4ay_border_date_availability()
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") == "OK" else 1


def audit_phase4ay_border_date_availability(
    *,
    checked_date_min: str = CHECKED_DATE_MIN,
    checked_date_max: str = CHECKED_DATE_MAX,
    user_expected_start_date: str = USER_EXPECTED_START_DATE,
    ax2_summary_path: Path = AX2_SUMMARY_PATH,
    raw_dir: Path = RAW_DIR,
    calendar_jsonl: Path = CALENDAR_JSONL,
    summary_path: Path = SUMMARY_PATH,
    report_path: Path = REPORT_PATH,
    settings_loader: Callable[[], Any] = load_settings,
    requester: Callable[[str, str, float], BoundaryResponse] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    min_interval_seconds: float = 1.0,
) -> dict[str, Any]:
    checked_dates = _date_range(checked_date_min, checked_date_max)
    ax2_summary = _read_json_optional(ax2_summary_path)
    reference = _select_success_reference(load_request_manifests(raw_dir / "request_manifests"))
    calendar = _load_calendar_status(calendar_jsonl)

    credential_read_performed = requester is None
    secret_value = ""
    if requester is None:
        try:
            settings = settings_loader()
            secret_value = settings.jquants.require_api_key()
            requester = _build_live_requester(settings)
        except ConfigurationError as exc:
            summary = _blocked_summary(
                checked_dates=checked_dates,
                readiness_status=BLOCKED_SECRET,
                message=_sanitize_text(str(exc), secret_value),
                credential_read_performed=credential_read_performed,
                summary_path=summary_path,
                report_path=report_path,
            )
            _write_json(summary_path, summary)
            _write_markdown(report_path, summary)
            return summary

    date_status_report: list[dict[str, Any]] = []
    for index, target_date in enumerate(checked_dates):
        if index > 0 and min_interval_seconds > 0:
            sleep(min_interval_seconds)
        response = requester(target_date, secret_value, 30.0)
        safe_message = _sanitize_text(response.response_message, secret_value)
        trading_day_status = _trading_day_status(target_date, calendar)
        date_status_report.append(
            {
                "date": target_date,
                "weekday": _weekday_name(target_date),
                "is_weekday": _is_weekday(target_date),
                "trading_day_status": trading_day_status,
                "request": {
                    "endpoint": ENDPOINT,
                    "method": "GET",
                    "params": {"date": target_date, "code": None, "pagination_key": None},
                    "date_format": "YYYY-MM-DD",
                },
                "http_status": response.http_status,
                "row_count": response.row_count,
                "payload_keys": list(response.payload_keys),
                "response_message_sanitized": safe_message,
                "available": _is_success(response),
            }
        )

    first_successful_date = _first_successful_date(date_status_report)
    first_available_trading_date = _first_available_trading_date(date_status_report)
    corrected_fetch_start = _corrected_fetch_start(
        user_expected_start_date=user_expected_start_date,
        first_successful_date=first_successful_date,
        first_available_trading_date=first_available_trading_date,
    )
    request_diff = _request_diff_summary(reference=reference, first_checked=date_status_report[0] if date_status_report else {})
    readiness_status = _readiness_status(date_status_report, request_diff, corrected_fetch_start)
    root_cause = _root_cause(date_status_report, first_successful_date, corrected_fetch_start, request_diff)
    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "border_audit_executed": True,
        "api_call_performed": True,
        "credential_read_performed": credential_read_performed,
        "secret_value_logged": False,
        "secret_value_written": False,
        "checked_date_min": checked_date_min,
        "checked_date_max": checked_date_max,
        "checked_dates": checked_dates,
        "date_status_report": date_status_report,
        "first_successful_date": first_successful_date,
        "first_available_trading_date": first_available_trading_date,
        "user_expected_start_date": user_expected_start_date,
        "corrected_fetch_start_date": corrected_fetch_start,
        "ax2_first_successful_date": ax2_summary.get("first_successful_date_detected"),
        "contradiction_resolved": corrected_fetch_start is not None,
        "root_cause": root_cause,
        "request_diff_summary": request_diff,
        "failed_manifest_quarantine_required": True,
        "failed_manifest_quarantine_policy": _quarantine_policy(corrected_fetch_start),
        "request_artifact_regeneration_required": True,
        "recommended_next_action": _recommended_next_action(readiness_status, corrected_fetch_start),
        "long_history_resume_fetch_executed": False,
        "normalized_rebuild_executed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "summary_path": str(summary_path),
        "report_path": str(report_path),
    }
    summary_text = json.dumps(summary, ensure_ascii=False)
    if secret_value and secret_value in summary_text:
        summary["status"] = "BLOCKED"
        summary["readiness_status"] = BLOCKED_SECRET
        summary["secret_value_written"] = True
        summary["recommended_next_action"] = "Secret value appeared in summary. Do not proceed until sanitizer is fixed."
    _write_json(summary_path, summary)
    _write_markdown(report_path, summary)
    return summary


def load_request_manifests(manifest_dir: Path) -> list[dict[str, Any]]:
    if not manifest_dir.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(manifest_dir.glob("*.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        items.append({"path": str(path), "target_date": path.stem, "manifest": manifest})
    return items


def _build_live_requester(settings: Any) -> Callable[[str, str, float], BoundaryResponse]:
    base_url = settings.jquants.base_url.rstrip("/")

    def request(target_date: str, api_key: str, timeout: float) -> BoundaryResponse:
        params = urllib.parse.urlencode({"date": target_date})
        url = f"{base_url}{ENDPOINT}?{params}"
        req = urllib.request.Request(url, headers={"x-api-key": api_key}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                payload = json.loads(body) if body else {}
                rows = payload.get("data") if isinstance(payload, dict) else []
                return BoundaryResponse(
                    target_date=target_date,
                    http_status=int(response.status),
                    response_message="OK",
                    row_count=len(rows) if isinstance(rows, list) else 0,
                    payload_keys=tuple(sorted(payload.keys())) if isinstance(payload, dict) else (),
                )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return BoundaryResponse(
                target_date=target_date,
                http_status=int(exc.code),
                response_message=_summarize_body(body) or str(exc.reason),
                row_count=0,
                payload_keys=(),
            )
        except urllib.error.URLError as exc:
            return BoundaryResponse(
                target_date=target_date,
                http_status="url_error",
                response_message=str(exc.reason),
                row_count=0,
                payload_keys=(),
            )

    return request


def _is_success(response: BoundaryResponse) -> bool:
    return response.http_status == 200 and response.row_count > 0


def _first_successful_date(report: list[dict[str, Any]]) -> str | None:
    for item in report:
        if item.get("available") is True:
            return str(item.get("date"))
    return None


def _first_available_trading_date(report: list[dict[str, Any]]) -> str | None:
    for item in report:
        if item.get("available") is True and item.get("trading_day_status") in {"business_day", "weekday_assumption", "calendar_missing_weekday"}:
            return str(item.get("date"))
    return _first_successful_date(report)


def _corrected_fetch_start(
    *,
    user_expected_start_date: str,
    first_successful_date: str | None,
    first_available_trading_date: str | None,
) -> str | None:
    if first_successful_date == user_expected_start_date:
        return user_expected_start_date
    return first_available_trading_date or first_successful_date


def _readiness_status(report: list[dict[str, Any]], request_diff: dict[str, Any], corrected_fetch_start: str | None) -> str:
    if not request_diff.get("endpoint_same", True) or not request_diff.get("method_same", True) or not request_diff.get("param_keys_compatible", True):
        return BLOCKED_API_FORMAT
    if not report or not corrected_fetch_start:
        return BLOCKED_UNKNOWN
    if all(str(item.get("http_status")) in {"400", "url_error"} for item in report):
        return BLOCKED_UNKNOWN
    return READY


def _root_cause(
    report: list[dict[str, Any]],
    first_successful_date: str | None,
    corrected_fetch_start: str | None,
    request_diff: dict[str, Any],
) -> str:
    if not request_diff.get("endpoint_same", True) or not request_diff.get("method_same", True) or not request_diff.get("param_keys_compatible", True):
        return "API request format differs from successful AD/AH request."
    if first_successful_date == USER_EXPECTED_START_DATE:
        return "2021-06-01 is available. AX2 contradiction is resolved as stale/out-of-range manifests before the true J-Quants start date plus prior failed state, not a 2021-06-01 format problem."
    if corrected_fetch_start:
        messages = [
            f"{item.get('date')} status={item.get('http_status')} message={item.get('response_message_sanitized')}"
            for item in report
            if item.get("available") is not True
        ]
        return "First available boundary date is later than 2021-06-01. Failed boundary messages: " + " | ".join(messages[:8])
    return "Border date availability remains unknown."


def _request_diff_summary(*, reference: dict[str, Any] | None, first_checked: dict[str, Any]) -> dict[str, Any]:
    ref = _request_summary(reference)
    checked_request = first_checked.get("request") or {}
    checked_params = checked_request.get("params") or {}
    ref_params = ref.get("params") or {}
    ref_param_keys = set(ref_params.keys())
    checked_keys_without_pagination = {key for key in checked_params.keys() if key != "pagination_key"}
    return {
        "successful_reference_request_from_ad_or_ah": ref,
        "checked_request": checked_request,
        "endpoint_same": not ref or checked_request.get("endpoint") == ref.get("endpoint"),
        "method_same": not ref or checked_request.get("method") == ref.get("method"),
        "param_keys_compatible": not ref or checked_keys_without_pagination == ref_param_keys,
        "date_format_same": _looks_iso_date(str((checked_params or {}).get("date") or "")),
        "only_date_value_differs": bool(ref and _only_date_value_differs(checked_params, ref_params)),
    }


def _request_summary(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    manifest = item["manifest"]
    params = dict(manifest.get("request_params") or {})
    return {
        "target_date": item["target_date"],
        "phase": manifest.get("phase"),
        "status": manifest.get("status"),
        "endpoint": manifest.get("endpoint") or ENDPOINT,
        "method": "GET",
        "params": {"code": params.get("code"), "date": params.get("date") or item["target_date"]},
        "row_count": manifest.get("row_count"),
    }


def _select_success_reference(manifests: list[dict[str, Any]]) -> dict[str, Any] | None:
    successes = [item for item in manifests if item["manifest"].get("status") == "SUCCESS"]
    for phase in ("Phase4-AD", "Phase4-AH"):
        for item in successes:
            if item["manifest"].get("phase") == phase:
                return item
    return successes[0] if successes else None


def _quarantine_policy(corrected_fetch_start: str | None) -> str:
    if corrected_fetch_start:
        return (
            f"Before Phase4-AZ/AX resume, exclude or move Phase4-AX FAILED manifests earlier than "
            f"{corrected_fetch_start} into a quarantine namespace so resume logic does not treat them as rerun targets."
        )
    return "Do not resume. Keep existing FAILED manifests untouched until border availability is resolved."


def _recommended_next_action(readiness_status: str, corrected_fetch_start: str | None) -> str:
    if readiness_status == READY:
        return f"Proceed to Phase4-AZ and regenerate the long-history request artifact from {corrected_fetch_start}."
    if readiness_status == BLOCKED_API_FORMAT:
        return "Fix request format to match AD/AH before regenerating requests."
    return "Do not resume long-history fetch until border date availability is known."


def _load_calendar_status(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    statuses: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        day = str(row.get("Date") or row.get("target_date") or "")
        hol_div = str(row.get("HolDiv") or "")
        if day:
            statuses[day] = "business_day" if hol_div == "1" else "non_business_day"
    return statuses


def _trading_day_status(target_date: str, calendar: dict[str, str]) -> str:
    if target_date in calendar:
        return calendar[target_date]
    return "calendar_missing_weekday" if _is_weekday(target_date) else "calendar_missing_weekend"


def _date_range(start: str, end: str) -> list[str]:
    current = date.fromisoformat(start)
    stop = date.fromisoformat(end)
    values: list[str] = []
    while current <= stop:
        values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def _weekday_name(value: str) -> str:
    return date.fromisoformat(value).strftime("%A")


def _is_weekday(value: str) -> bool:
    return date.fromisoformat(value).weekday() < 5


def _looks_iso_date(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))


def _only_date_value_differs(left: dict[str, Any], right: dict[str, Any]) -> bool:
    clean_left = {key: value for key, value in left.items() if key not in {"date", "pagination_key"}}
    clean_right = {key: value for key, value in right.items() if key != "date"}
    return clean_left == clean_right and left.get("date") != right.get("date")


def _summarize_body(body: str) -> str:
    body = body.strip()
    if not body:
        return ""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body[:500]
    if isinstance(payload, dict):
        for key in ("message", "error", "detail", "title"):
            if payload.get(key):
                return str(payload.get(key))[:500]
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)[:500]
    return str(payload)[:500]


def _sanitize_text(text: str, secret_value: str = "") -> str:
    sanitized = text
    if secret_value:
        sanitized = sanitized.replace(secret_value, "[REDACTED_SECRET]")
    for marker in (
        "Authorization",
        "x-api-key",
        "JQUANTS_API_KEY",
        "api_key",
        "password",
        "cookie",
        "token",
        "Bearer",
    ):
        sanitized = re.sub(re.escape(marker), "[REDACTED]", sanitized, flags=re.IGNORECASE)
    return sanitized


def _blocked_summary(
    *,
    checked_dates: list[str],
    readiness_status: str,
    message: str,
    credential_read_performed: bool,
    summary_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "border_audit_executed": False,
        "api_call_performed": False,
        "credential_read_performed": credential_read_performed,
        "secret_value_logged": False,
        "secret_value_written": False,
        "checked_date_min": checked_dates[0] if checked_dates else None,
        "checked_date_max": checked_dates[-1] if checked_dates else None,
        "checked_dates": checked_dates,
        "date_status_report": [],
        "first_successful_date": None,
        "first_available_trading_date": None,
        "user_expected_start_date": USER_EXPECTED_START_DATE,
        "corrected_fetch_start_date": None,
        "ax2_first_successful_date": None,
        "contradiction_resolved": False,
        "root_cause": message,
        "failed_manifest_quarantine_required": False,
        "failed_manifest_quarantine_policy": "No quarantine decision until border audit succeeds.",
        "request_artifact_regeneration_required": False,
        "recommended_next_action": "Resolve blocking issue before Phase4-AZ.",
        "long_history_resume_fetch_executed": False,
        "normalized_rebuild_executed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "summary_path": str(summary_path),
        "report_path": str(report_path),
    }


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AY Border Date Availability Audit / Fetch Start Correction",
        "",
        f"- status: `{summary.get('status')}`",
        f"- readiness_status: `{summary.get('readiness_status')}`",
        f"- checked_date_range: `{summary.get('checked_date_min')}` to `{summary.get('checked_date_max')}`",
        f"- first_successful_date: `{summary.get('first_successful_date')}`",
        f"- first_available_trading_date: `{summary.get('first_available_trading_date')}`",
        f"- corrected_fetch_start_date: `{summary.get('corrected_fetch_start_date')}`",
        f"- contradiction_resolved: `{summary.get('contradiction_resolved')}`",
        "",
        "## Date Status Report",
        "",
        "```json",
        json.dumps(summary.get("date_status_report"), ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## Request Diff",
        "",
        "```json",
        json.dumps(summary.get("request_diff_summary"), ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## Root Cause",
        "",
        str(summary.get("root_cause") or ""),
        "",
        "## Failed Manifest Quarantine Policy",
        "",
        str(summary.get("failed_manifest_quarantine_policy") or ""),
        "",
        "## Scope Guard",
        "",
        "- long_history_resume_fetch_executed: `False`",
        "- normalized_rebuild_executed: `False`",
        "- feature/label/dataset/training/inference/backtest/trading: `False`",
        "- promotion_performed / reader_switch_performed: `False`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
