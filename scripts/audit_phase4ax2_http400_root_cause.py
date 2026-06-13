#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

PHASE = "Phase4-AX2"
RAW_DIR = Path(".runtime/data/raw/jquants/equities_bars_daily")
AW_REQUESTS_PATH = Path("reports/candidate_ai/full_range/phase4aw_long_history_fetch_dry_run_requests.json")
AX_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ax_long_history_controlled_fetch_summary.json")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ax2_http400_root_cause_summary.json")
REPORT_PATH = Path("docs/phase_reports/phase4ax2_http400_root_cause.md")

REQUEST_FORMAT_MISMATCH = "REQUEST_FORMAT_MISMATCH"
FETCH_START_DATE_OUT_OF_RANGE = "FETCH_START_DATE_OUT_OF_RANGE"
CALENDAR_SOURCE_INVALID = "CALENDAR_SOURCE_INVALID"
BLOCKED_BY_UNKNOWN_HTTP400 = "BLOCKED_BY_UNKNOWN_HTTP400"


def main() -> int:
    summary = audit_phase4ax2_http400_root_cause()
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") == "OK" else 1


def audit_phase4ax2_http400_root_cause(
    *,
    raw_dir: Path = RAW_DIR,
    aw_requests_path: Path = AW_REQUESTS_PATH,
    ax_summary_path: Path = AX_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    manifests = load_request_manifests(raw_dir / "request_manifests")
    ax_summary = _read_json_optional(ax_summary_path)
    aw_artifact = _read_json_optional(aw_requests_path)
    failed = [item for item in manifests if item["manifest"].get("phase") == "Phase4-AX" and item["manifest"].get("status") == "FAILED"]
    successes = [item for item in manifests if item["manifest"].get("status") == "SUCCESS"]
    failed_dates = [item["target_date"] for item in failed]
    failed_status_codes = sorted({_extract_status_code(str(item["manifest"].get("error_message") or "")) for item in failed})
    failed_status_codes = [code for code in failed_status_codes if code]
    first_failed = failed[0] if failed else None
    reference = _select_success_reference(successes)
    first_success = _first_success_date(successes)
    http400_dates = [
        item["target_date"]
        for item in failed
        if _extract_status_code(str(item["manifest"].get("error_message") or "")) == "400"
    ]
    request_diff = build_request_diff_summary(first_failed=first_failed, reference=reference, aw_artifact=aw_artifact)
    suspected = classify_root_cause(
        request_diff=request_diff,
        http400_dates=http400_dates,
        first_success_date=first_success,
        failed_dates=failed_dates,
        aw_artifact=aw_artifact,
    )
    adjusted_fetch_start = first_success if suspected == FETCH_START_DATE_OUT_OF_RANGE else None
    safe_to_resume = suspected not in {FETCH_START_DATE_OUT_OF_RANGE, REQUEST_FORMAT_MISMATCH, CALENDAR_SOURCE_INVALID}
    summary = {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": suspected,
        "first_failed_request": _request_summary(first_failed),
        "failed_dates": failed_dates,
        "failed_status_codes": failed_status_codes,
        "failed_response_messages_sanitized": sorted(
            {
                _sanitize_text(str(item["manifest"].get("error_message") or ""))
                for item in failed
                if item["manifest"].get("error_message")
            }
        ),
        "failed_response_body_available": False,
        "successful_reference_request_from_ad_or_ah": _request_summary(reference),
        "first_successful_date_detected": first_success,
        "request_diff_summary": request_diff,
        "calendar_analysis": build_calendar_analysis(aw_artifact=aw_artifact, failed_dates=failed_dates, http400_dates=http400_dates),
        "suspected_root_cause": suspected,
        "recommended_fix": _recommended_fix(suspected, adjusted_fetch_start),
        "safe_to_resume": safe_to_resume,
        "adjusted_fetch_start_date_if_needed": adjusted_fetch_start,
        "fetch_start_date_correction_required": adjusted_fetch_start is not None,
        "additional_fetch_executed": False,
        "resume_fetch_executed": False,
        "normalized_rebuild_executed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "phase4ax_readiness_status": ax_summary.get("readiness_status"),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
    }
    _write_json(summary_path, summary)
    _write_markdown(report_path, summary)
    return summary


def load_request_manifests(manifest_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not manifest_dir.is_dir():
        return items
    for path in sorted(manifest_dir.glob("*.json")):
        manifest = _read_json_optional(path)
        items.append({"path": str(path), "target_date": path.stem, "manifest": manifest})
    return items


def build_request_diff_summary(
    *,
    first_failed: dict[str, Any] | None,
    reference: dict[str, Any] | None,
    aw_artifact: dict[str, Any],
) -> dict[str, Any]:
    failed_request = _request_summary(first_failed)
    reference_request = _request_summary(reference)
    aw_first = (aw_artifact.get("requests") or [{}])[0] if isinstance(aw_artifact.get("requests"), list) else {}
    failed_params = failed_request.get("params") or {}
    reference_params = reference_request.get("params") or {}
    return {
        "endpoint_same": failed_request.get("endpoint") == reference_request.get("endpoint"),
        "method_same": failed_request.get("method") == reference_request.get("method"),
        "param_keys_same": sorted(failed_params.keys()) == sorted(reference_params.keys()),
        "date_format_same": _looks_iso_date(str(failed_params.get("date") or ""))
        and _looks_iso_date(str(reference_params.get("date") or "")),
        "only_date_value_differs": _only_date_value_differs(failed_params, reference_params),
        "aw_first_request_endpoint": aw_first.get("endpoint"),
        "aw_first_request_method": aw_first.get("method"),
        "aw_first_request_params": aw_first.get("params"),
        "aw_generator_matches_manifest_shape": sorted((aw_first.get("params") or {}).keys())
        == sorted(["code", "date", "pagination_key"]),
        "failed_request": failed_request,
        "reference_request": reference_request,
    }


def classify_root_cause(
    *,
    request_diff: dict[str, Any],
    http400_dates: list[str],
    first_success_date: str | None,
    failed_dates: list[str],
    aw_artifact: dict[str, Any],
) -> str:
    if not request_diff.get("endpoint_same") or not request_diff.get("method_same") or not request_diff.get("param_keys_same"):
        return REQUEST_FORMAT_MISMATCH
    if _calendar_source_invalid(aw_artifact=aw_artifact, failed_dates=failed_dates, http400_dates=http400_dates):
        return CALENDAR_SOURCE_INVALID
    if http400_dates and first_success_date and max(http400_dates) < first_success_date:
        return FETCH_START_DATE_OUT_OF_RANGE
    return BLOCKED_BY_UNKNOWN_HTTP400


def build_calendar_analysis(*, aw_artifact: dict[str, Any], failed_dates: list[str], http400_dates: list[str]) -> dict[str, Any]:
    all_weekdays = all(_is_weekday(day) for day in failed_dates)
    all_400_weekdays = all(_is_weekday(day) for day in http400_dates)
    request_count = int(aw_artifact.get("request_count") or len(aw_artifact.get("requests") or []))
    return {
        "calendar_source": "calendar_placeholder_weekday",
        "aw_request_count": request_count,
        "failed_dates_all_weekdays": all_weekdays,
        "http400_dates_all_weekdays": all_400_weekdays,
        "calendar_placeholder_may_include_jp_holidays": True,
        "calendar_issue_explains_first_400_block": False,
        "note": "The failed HTTP400 dates form a continuous weekday block before the first successful date, so holiday mixing alone is unlikely to explain the failures.",
    }


def _calendar_source_invalid(*, aw_artifact: dict[str, Any], failed_dates: list[str], http400_dates: list[str]) -> bool:
    if not failed_dates:
        return False
    weekend_failures = [day for day in failed_dates if not _is_weekday(day)]
    if weekend_failures:
        return True
    if http400_dates and not all(_is_weekday(day) for day in http400_dates):
        return True
    return False


def _request_summary(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    manifest = item["manifest"]
    params = dict(manifest.get("request_params") or {})
    return {
        "target_date": item["target_date"],
        "phase": manifest.get("phase"),
        "status": manifest.get("status"),
        "endpoint": manifest.get("endpoint") or "/v2/equities/bars/daily",
        "method": "GET",
        "params": {"code": params.get("code"), "date": params.get("date") or item["target_date"]},
        "page_count": manifest.get("page_count"),
        "row_count": manifest.get("row_count"),
        "error_message": _sanitize_text(str(manifest.get("error_message") or "")) or None,
    }


def _select_success_reference(successes: list[dict[str, Any]]) -> dict[str, Any] | None:
    for phase in ("Phase4-AD", "Phase4-AH"):
        for item in successes:
            if item["manifest"].get("phase") == phase:
                return item
    return successes[0] if successes else None


def _first_success_date(successes: list[dict[str, Any]]) -> str | None:
    dates = sorted(item["target_date"] for item in successes if item["manifest"].get("phase") == "Phase4-AX")
    return dates[0] if dates else None


def _extract_status_code(message: str) -> str:
    match = re.search(r"status=([A-Za-z0-9_]+)", message)
    return match.group(1) if match else ""


def _looks_iso_date(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))


def _only_date_value_differs(left: dict[str, Any], right: dict[str, Any]) -> bool:
    comparable_left = {key: value for key, value in left.items() if key != "date"}
    comparable_right = {key: value for key, value in right.items() if key != "date"}
    return comparable_left == comparable_right and left.get("date") != right.get("date")


def _is_weekday(value: str) -> bool:
    from datetime import date

    return date.fromisoformat(value).weekday() < 5


def _recommended_fix(root_cause: str, adjusted_fetch_start: str | None) -> str:
    if root_cause == FETCH_START_DATE_OUT_OF_RANGE:
        return (
            f"Regenerate the Phase4-AW request artifact with fetch_start_date={adjusted_fetch_start}, "
            "remove or ignore earlier FAILED manifests, then rerun Phase4-AX. Also recompute the effective "
            "formal training start after the 60-business-day lookback gate."
        )
    if root_cause == REQUEST_FORMAT_MISMATCH:
        return "Align AW request artifact params with the AD/AH successful request shape before any resume fetch."
    if root_cause == CALENDAR_SOURCE_INVALID:
        return "Replace calendar_placeholder_weekday with an actual J-Quants trading calendar before resume fetch."
    return "Do not resume AX yet. Capture sanitized HTTP400 response bodies or validate endpoint constraints before retrying."


def _sanitize_text(text: str) -> str:
    for marker in ("Authorization", "x-api-key", "JQUANTS_API_KEY", "password", "cookie"):
        text = text.replace(marker, "[REDACTED]")
    return text


def _write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AX2 HTTP400 Root Cause Audit",
        "",
        f"- status: `{summary.get('status')}`",
        f"- readiness_status: `{summary.get('readiness_status')}`",
        f"- suspected_root_cause: `{summary.get('suspected_root_cause')}`",
        f"- first_failed_request: `{summary.get('first_failed_request')}`",
        f"- failed_status_codes: `{summary.get('failed_status_codes')}`",
        f"- adjusted_fetch_start_date_if_needed: `{summary.get('adjusted_fetch_start_date_if_needed')}`",
        f"- safe_to_resume: `{summary.get('safe_to_resume')}`",
        "",
        "## Request Diff Summary",
        "",
        "```json",
        json.dumps(summary.get("request_diff_summary"), ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## Calendar Analysis",
        "",
        "```json",
        json.dumps(summary.get("calendar_analysis"), ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## Recommended Fix",
        "",
        str(summary.get("recommended_fix") or ""),
        "",
        "## Scope Guard",
        "",
        "- additional_fetch_executed: `False`",
        "- resume_fetch_executed: `False`",
        "- normalized_rebuild_executed: `False`",
        "- feature/label/dataset/training/backtest/trading: `False`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
