#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.data.jquants_fetch_policy import jquants_common_policy_manifest  # noqa: E402

PHASE = "Phase4-AY"
PHASE4AV_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4av_long_history_fetch_plan_summary.json")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ay_long_history_request_regeneration_summary.json")
REQUESTS_PATH = Path("reports/candidate_ai/full_range/phase4ay_long_history_corrected_requests.json")
REPORT_PATH = Path("docs/phase_reports/phase4ay_long_history_request_regeneration.md")

READY = "READY_FOR_LONG_HISTORY_CONTROLLED_FETCH_RETRY"
BLOCKED_SEQUENCE = "BLOCKED_BY_REQUEST_REGENERATION"
BLOCKED_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"

CORRECTED_FETCH_START_DATE = "2021-06-01"
FETCH_END_DATE = "2026-06-12"
ENDPOINT = "/v2/equities/bars/daily"
RAW_OUTPUT_PATH = ".runtime/data/raw/jquants/equities_bars_daily"
NORMALIZED_OUTPUT_PATH = ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate corrected Phase4-AY long-history request artifact.")
    parser.add_argument("--phase4av-summary", default=str(PHASE4AV_SUMMARY_PATH))
    parser.add_argument("--summary-path", default=str(SUMMARY_PATH))
    parser.add_argument("--requests-path", default=str(REQUESTS_PATH))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    args = parser.parse_args(argv)
    summary = regenerate_long_history_requests(
        phase4av_summary_path=Path(args.phase4av_summary),
        summary_path=Path(args.summary_path),
        requests_path=Path(args.requests_path),
        report_path=Path(args.report_path),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") == "OK" else 1


def regenerate_long_history_requests(
    *,
    corrected_fetch_start_date: str = CORRECTED_FETCH_START_DATE,
    fetch_end_date: str = FETCH_END_DATE,
    phase4av_summary_path: Path = PHASE4AV_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
    requests_path: Path = REQUESTS_PATH,
    report_path: Path = REPORT_PATH,
    raw_output_path: str = RAW_OUTPUT_PATH,
    normalized_output_path: str = NORMALIZED_OUTPUT_PATH,
) -> dict[str, Any]:
    av_summary = _read_json_optional(phase4av_summary_path)
    business_days = iter_weekdays(corrected_fetch_start_date, fetch_end_date)
    requests = build_request_sequence(business_days=business_days, endpoint=ENDPOINT)
    excluded_dates = iter_weekdays(str(av_summary.get("preferred_fetch_start_date") or "2021-03-09"), _previous_day(corrected_fetch_start_date))
    original_estimated_request_count = int(av_summary.get("estimated_request_count") or 0)
    original_storage_estimate_mb = float(av_summary.get("storage_estimate_mb") or 0.0)
    storage_estimate_mb = _recalculate_storage_estimate(
        original_estimated_request_count=original_estimated_request_count,
        original_storage_estimate_mb=original_storage_estimate_mb,
        corrected_request_count=len(requests),
    )
    common_policy = jquants_common_policy_manifest(endpoint=ENDPOINT, rate_limit_per_minute=60)
    path_safe = _is_runtime_path(raw_output_path) and _is_runtime_path(normalized_output_path)
    no_pre_start_dates = all(request["params"]["date"] >= corrected_fetch_start_date for request in requests)
    readiness_status = READY if requests and no_pre_start_dates and path_safe else (BLOCKED_PATH if not path_safe else BLOCKED_SEQUENCE)
    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "request_regeneration_executed": True,
        "api_call_performed": False,
        "credential_read_performed": False,
        "http_client_initialized": False,
        "fetch_executed": False,
        "corrected_fetch_start_date": corrected_fetch_start_date,
        "fetch_end_date": fetch_end_date,
        "target_start_date": corrected_fetch_start_date,
        "target_end_date": fetch_end_date,
        "business_day_count": len(business_days),
        "request_count": len(requests),
        "original_estimated_request_count": original_estimated_request_count,
        "excluded_pre_start_request_count": len(excluded_dates),
        "excluded_pre_start_date_min": excluded_dates[0] if excluded_dates else None,
        "excluded_pre_start_date_max": excluded_dates[-1] if excluded_dates else None,
        "first_request_date": requests[0]["params"]["date"] if requests else None,
        "last_request_date": requests[-1]["params"]["date"] if requests else None,
        "request_artifact_generated": bool(requests),
        "request_artifact_path": str(requests_path),
        "request_artifact_has_pre_20210601_dates": not no_pre_start_dates,
        "endpoint": ENDPOINT,
        "method": "GET",
        "calendar_source": "calendar_placeholder_weekday",
        "rate_limit_policy": common_policy["rate_limit_policy"],
        "retry_policy": common_policy["retry_policy"],
        "endpoint_capability": common_policy["endpoint_capability"],
        "resume_policy": (
            "Use corrected request artifact only. Skip SUCCESS manifests for dates in artifact; rerun missing/FAILED "
            "dates in artifact; exclude Phase4-AX FAILED manifests before 2021-06-01 from resume targets."
        ),
        "failed_manifest_quarantine_required": True,
        "failed_manifest_quarantine_policy": (
            "Treat Phase4-AX FAILED manifests dated 2021-03-09 through 2021-05-31 as out-of-scope legacy failures. "
            "Do not delete them; move to a quarantine namespace or filter them out in retry/resume logic."
        ),
        "manifest_policy": "Write corrected request artifact under reports; controlled fetch manifests remain under .runtime/data/raw/jquants/equities_bars_daily.",
        "original_storage_estimate_mb": round(original_storage_estimate_mb, 2),
        "storage_estimate_mb": round(storage_estimate_mb, 2),
        "raw_output_path": raw_output_path,
        "normalized_output_path": normalized_output_path,
        "safe_to_resume_after_correction": readiness_status == READY,
        "mock_path_unchanged": True,
        "raw_data_modified": False,
        "normalized_data_modified": False,
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
        "recommended_next_action": _recommended_next_action(readiness_status),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
    }
    _write_outputs(summary_path, requests_path, report_path, summary, requests)
    return summary


def build_request_sequence(*, business_days: list[str], endpoint: str) -> list[dict[str, Any]]:
    return [
        {
            "request_id": f"phase4ay_daily_quotes_{target_date}",
            "sequence": index + 1,
            "endpoint": endpoint,
            "method": "GET",
            "params": {
                "date": target_date,
                "code": None,
                "pagination_key": None,
            },
            "pagination": {
                "enabled": True,
                "initial_pagination_key": None,
                "next_pagination_key_placeholder": "<response.pagination_key>",
            },
            "dry_run_only": True,
            "api_call_performed": False,
        }
        for index, target_date in enumerate(business_days)
    ]


def iter_weekdays(start_date: str, end_date: str) -> list[str]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        return []
    values: list[str] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def _previous_day(value: str) -> str:
    return (date.fromisoformat(value) - timedelta(days=1)).isoformat()


def _recalculate_storage_estimate(
    *,
    original_estimated_request_count: int,
    original_storage_estimate_mb: float,
    corrected_request_count: int,
) -> float:
    if original_estimated_request_count <= 0 or original_storage_estimate_mb <= 0:
        return corrected_request_count * 2.37
    return original_storage_estimate_mb * corrected_request_count / original_estimated_request_count


def _is_runtime_path(value: str) -> bool:
    return value == ".runtime" or value.startswith(".runtime/")


def _recommended_next_action(readiness_status: str) -> str:
    if readiness_status == READY:
        return "Proceed to Phase4-AZ Long History Controlled Fetch Retry using the corrected request artifact."
    return "Fix request artifact regeneration blockers before controlled fetch retry."


def _write_outputs(summary_path: Path, requests_path: Path, report_path: Path, summary: dict[str, Any], requests: list[dict[str, Any]]) -> None:
    artifact = {
        "phase": PHASE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corrected_fetch_start_date": summary.get("corrected_fetch_start_date"),
        "fetch_end_date": summary.get("fetch_end_date"),
        "request_count": len(requests),
        "endpoint": ENDPOINT,
        "method": "GET",
        "api_call_performed": False,
        "credential_read_performed": False,
        "fetch_executed": False,
        "requests": requests,
    }
    _write_json(summary_path, summary)
    _write_json(requests_path, artifact)
    _write_markdown(report_path, summary)


def _write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AY Long History Request Regeneration",
        "",
        f"- status: `{summary.get('status')}`",
        f"- readiness_status: `{summary.get('readiness_status')}`",
        f"- corrected_fetch_start_date: `{summary.get('corrected_fetch_start_date')}`",
        f"- fetch_end_date: `{summary.get('fetch_end_date')}`",
        f"- request_count: `{summary.get('request_count')}`",
        f"- excluded_pre_start_request_count: `{summary.get('excluded_pre_start_request_count')}`",
        f"- safe_to_resume_after_correction: `{summary.get('safe_to_resume_after_correction')}`",
        f"- storage_estimate_mb: `{summary.get('storage_estimate_mb')}`",
        "",
        "## Resume / Quarantine Policy",
        "",
        str(summary.get("failed_manifest_quarantine_policy") or ""),
        "",
        "## Scope Guard",
        "",
        "- api_call_performed: `False`",
        "- credential_read_performed: `False`",
        "- fetch_executed: `False`",
        "- normalized/feature/label/dataset/training/inference/backtest/trading: `False`",
        "- promotion_performed / reader_switch_performed: `False`",
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
