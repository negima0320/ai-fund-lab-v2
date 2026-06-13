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

from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402

PHASE = "Phase4-AW"
PHASE4AV_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4av_long_history_fetch_plan_summary.json")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4aw_long_history_fetch_dry_run_summary.json")
REQUESTS_PATH = Path("reports/candidate_ai/full_range/phase4aw_long_history_fetch_dry_run_requests.json")
REPORT_PATH = Path("docs/phase_reports/phase4aw_long_history_fetch_dry_run.md")

READY_AV = "READY_FOR_LONG_HISTORY_FETCH_DRY_RUN"
READY = "READY_FOR_LONG_HISTORY_CONTROLLED_FETCH"
BLOCKED_SEQUENCE = "BLOCKED_BY_REQUEST_SEQUENCE"
BLOCKED_STORAGE = "BLOCKED_BY_STORAGE_ESTIMATE"
BLOCKED_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"
BLOCKED_DRY_RUN = "BLOCKED_BY_DRY_RUN_FAILURE"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Phase4-AW long history fetch dry-run request sequence.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--phase4av-summary", default=str(PHASE4AV_SUMMARY_PATH))
    parser.add_argument("--summary-path", default=str(SUMMARY_PATH))
    parser.add_argument("--requests-path", default=str(REQUESTS_PATH))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    args = parser.parse_args(argv)
    summary = run_phase4aw_long_history_fetch_dry_run(
        runtime_dir=args.runtime_dir,
        phase4av_summary_path=Path(args.phase4av_summary),
        summary_path=Path(args.summary_path),
        requests_path=Path(args.requests_path),
        report_path=Path(args.report_path),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def run_phase4aw_long_history_fetch_dry_run(
    *,
    runtime_dir: Path | str = ".runtime",
    phase4av_summary_path: Path = PHASE4AV_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
    requests_path: Path = REQUESTS_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    av_summary = _read_json_optional(phase4av_summary_path)
    if av_summary.get("readiness_status") != READY_AV:
        summary = _blocked_summary(
            readiness_status=BLOCKED_DRY_RUN,
            reason="Phase4-AV summary is missing or not ready for long history fetch dry-run.",
            paths=paths,
            summary_path=summary_path,
            requests_path=requests_path,
            report_path=report_path,
        )
        _write_outputs(summary_path, requests_path, report_path, summary, [])
        return summary

    raw_output_path = Path(str(av_summary.get("raw_output_path") or ""))
    normalized_output_path = Path(str(av_summary.get("normalized_output_path") or ""))
    if not _safe_runtime_output_path(paths.runtime_dir, raw_output_path) or not _safe_runtime_output_path(
        paths.runtime_dir, normalized_output_path
    ):
        summary = _blocked_summary(
            readiness_status=BLOCKED_PATH,
            reason="Planned raw or normalized output path is outside runtime dir.",
            paths=paths,
            summary_path=summary_path,
            requests_path=requests_path,
            report_path=report_path,
        )
        _write_outputs(summary_path, requests_path, report_path, summary, [])
        return summary

    target_start_date = str(av_summary.get("preferred_fetch_start_date") or "")
    target_end_date = str(av_summary.get("preferred_fetch_end_date") or "")
    expected_request_count = int(av_summary.get("estimated_request_count") or 0)
    business_days, calendar_source = load_business_days(
        runtime_dir=paths.runtime_dir,
        start_date=target_start_date,
        end_date=target_end_date,
    )
    requests = build_request_sequence(
        business_days=business_days,
        endpoint=str(av_summary.get("endpoint") or "/v2/equities/bars/daily"),
        method="GET",
    )
    request_count = len(requests)
    request_count_match = request_count == expected_request_count
    readiness_status = _resolve_readiness(
        request_count=request_count,
        expected_request_count=expected_request_count,
        request_count_match=request_count_match,
        storage_estimate_mb=float(av_summary.get("storage_estimate_mb") or 0.0),
    )
    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "dry_run_executed": True,
        "api_call_performed": False,
        "fetch_executed": False,
        "credential_read_performed": False,
        "http_client_initialized": False,
        "request_sequence_generated": bool(requests),
        "request_count": request_count,
        "estimated_request_count": expected_request_count,
        "request_count_match": request_count_match,
        "target_start_date": target_start_date,
        "target_end_date": target_end_date,
        "business_day_count": len(business_days),
        "calendar_source": calendar_source,
        "endpoint": str(av_summary.get("endpoint") or "/v2/equities/bars/daily"),
        "method": "GET",
        "rate_limit_policy": av_summary.get("rate_limit_policy"),
        "resume_policy": av_summary.get("resume_policy"),
        "manifest_policy": av_summary.get("manifest_policy"),
        "storage_estimate_mb": av_summary.get("storage_estimate_mb"),
        "raw_output_path": str(raw_output_path),
        "normalized_output_path": str(normalized_output_path),
        "mock_path_unchanged": True,
        "raw_data_modified": False,
        "normalized_data_modified": False,
        "formal_training_possible_after_fetch": av_summary.get("formal_training_possible_after_fetch") is True,
        "requests_artifact_path": str(requests_path),
        "recommended_next_action": _recommended_next_action(readiness_status),
        "normalized_rebuild_executed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(summary_path),
        "report_path": str(report_path),
    }
    _write_outputs(summary_path, requests_path, report_path, summary, requests)
    return summary


def load_business_days(*, runtime_dir: Path, start_date: str, end_date: str) -> tuple[list[str], str]:
    calendar_dates = _load_trading_calendar_business_days(runtime_dir=runtime_dir, start_date=start_date, end_date=end_date)
    expected_weekdays = iter_weekdays(start_date, end_date)
    if len(calendar_dates) == len(expected_weekdays):
        return calendar_dates, "runtime_trading_calendar"
    return expected_weekdays, "calendar_placeholder_weekday"


def build_request_sequence(*, business_days: list[str], endpoint: str, method: str = "GET") -> list[dict[str, Any]]:
    return [
        {
            "request_id": f"phase4aw_daily_quotes_{target_date}",
            "sequence": index + 1,
            "endpoint": endpoint,
            "method": method,
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
        }
        for index, target_date in enumerate(business_days)
    ]


def iter_weekdays(start_date: str, end_date: str) -> list[str]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        return []
    days: list[str] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _load_trading_calendar_business_days(*, runtime_dir: Path, start_date: str, end_date: str) -> list[str]:
    base = runtime_dir / "data" / "raw" / "jquants" / "trading_calendar" / "data"
    records: list[dict[str, Any]] = []
    for format_name in ("parquet", "jsonl"):
        path = create_storage_backend(format_name).path_for(base)
        if path.is_file():
            records = create_storage_backend(format_name).read_records(path)
            if records:
                break
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    days = []
    for record in records:
        value = str(record.get("target_date") or record.get("Date") or "")
        if not value:
            continue
        day = date.fromisoformat(value)
        hol_div = str(record.get("HolDiv") or record.get("HolidayDivision") or "")
        if start <= day <= end and hol_div == "1":
            days.append(value)
    return sorted(set(days))


def _resolve_readiness(
    *,
    request_count: int,
    expected_request_count: int,
    request_count_match: bool,
    storage_estimate_mb: float,
) -> str:
    if request_count <= 0 or expected_request_count <= 0 or not request_count_match:
        return BLOCKED_SEQUENCE
    if storage_estimate_mb > 20_000:
        return BLOCKED_STORAGE
    return READY


def _recommended_next_action(readiness_status: str) -> str:
    if readiness_status == READY:
        return "Phase4-AX Long History Controlled Fetch: execute the approved request sequence with J-Quants credentials."
    if readiness_status == BLOCKED_STORAGE:
        return "Review storage budget and chunking before controlled fetch."
    return "Fix the dry-run request sequence mismatch, then rerun Phase4-AW."


def _blocked_summary(
    *,
    readiness_status: str,
    reason: str,
    paths: RuntimePaths,
    summary_path: Path,
    requests_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "dry_run_executed": False,
        "block_reason": reason,
        "api_call_performed": False,
        "fetch_executed": False,
        "credential_read_performed": False,
        "http_client_initialized": False,
        "request_sequence_generated": False,
        "request_count": 0,
        "estimated_request_count": 0,
        "request_count_match": False,
        "business_day_count": 0,
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
        "runtime_dir": str(paths.runtime_dir),
        "requests_artifact_path": str(requests_path),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
        "recommended_next_action": "Fix the blocking condition, then rerun Phase4-AW.",
    }


def _write_outputs(summary_path: Path, requests_path: Path, report_path: Path, summary: dict[str, Any], requests: list[dict[str, Any]]) -> None:
    _write_json(summary_path, summary)
    _write_json(
        requests_path,
        {
            "phase": PHASE,
            "created_at": _now(),
            "dry_run_only": True,
            "endpoint": summary.get("endpoint"),
            "method": summary.get("method"),
            "target_start_date": summary.get("target_start_date"),
            "target_end_date": summary.get("target_end_date"),
            "request_count": len(requests),
            "requests": requests,
        },
    )
    _write_markdown_report(report_path, summary)


def _write_markdown_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AW Long History Fetch Dry-run",
        "",
        "## Purpose",
        "",
        "Phase4-AW generates a dry-run request sequence for long history daily quotes fetch. It does not read credentials, initialize an HTTP client, call J-Quants, fetch raw data, rebuild normalized data, generate features or labels, rebuild datasets, train, infer, backtest, trade, promote, or switch readers.",
        "",
        "## Summary",
        "",
        f"- status: `{summary.get('status')}`",
        f"- readiness_status: `{summary.get('readiness_status')}`",
        f"- target fetch range: `{summary.get('target_start_date')}` to `{summary.get('target_end_date')}`",
        f"- business_day_count: `{summary.get('business_day_count')}`",
        f"- request_count: `{summary.get('request_count')}`",
        f"- estimated_request_count: `{summary.get('estimated_request_count')}`",
        f"- request_count_match: `{summary.get('request_count_match')}`",
        f"- calendar_source: `{summary.get('calendar_source')}`",
        f"- storage_estimate_mb: `{summary.get('storage_estimate_mb')}`",
        f"- requests_artifact_path: `{summary.get('requests_artifact_path')}`",
        "",
        "## Request Template",
        "",
        f"- endpoint: `{summary.get('endpoint')}`",
        f"- method: `{summary.get('method')}`",
        "- params.date: target business date",
        "- params.code: None",
        "- params.pagination_key: None",
        "",
        "## Policies",
        "",
        f"- rate_limit_policy: {summary.get('rate_limit_policy')}",
        f"- resume_policy: {summary.get('resume_policy')}",
        f"- manifest_policy: {summary.get('manifest_policy')}",
        "",
        "## Scope Guard",
        "",
        f"- api_call_performed: `{summary.get('api_call_performed')}`",
        f"- credential_read_performed: `{summary.get('credential_read_performed')}`",
        f"- http_client_initialized: `{summary.get('http_client_initialized')}`",
        f"- fetch_executed: `{summary.get('fetch_executed')}`",
        f"- raw_data_modified: `{summary.get('raw_data_modified')}`",
        f"- normalized_data_modified: `{summary.get('normalized_data_modified')}`",
        f"- mock_path_unchanged: `{summary.get('mock_path_unchanged')}`",
        f"- training_executed: `{summary.get('training_executed')}`",
        f"- inference_executed: `{summary.get('inference_executed')}`",
        f"- backtest_executed: `{summary.get('backtest_executed')}`",
        f"- trading_executed: `{summary.get('trading_executed')}`",
        "",
        "## Recommended Next Action",
        "",
        str(summary.get("recommended_next_action") or ""),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _safe_runtime_output_path(runtime_dir: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(runtime_dir.resolve())
        return True
    except ValueError:
        return False


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
