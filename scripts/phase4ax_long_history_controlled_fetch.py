#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.config.settings import ConfigurationError, load_settings  # noqa: E402
from ai_fund_lab_v2.data_sources.jquants.client import JQuantsClient  # noqa: E402

PHASE = "Phase4-AX"
PHASE4AW_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4aw_long_history_fetch_dry_run_summary.json")
PHASE4AW_REQUESTS_PATH = Path("reports/candidate_ai/full_range/phase4aw_long_history_fetch_dry_run_requests.json")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ax_long_history_controlled_fetch_summary.json")
REPORT_PATH = Path("docs/phase_reports/phase4ax_long_history_controlled_fetch.md")

READY = "READY_FOR_LONG_HISTORY_RAW_COVERAGE_AUDIT"
PARTIAL_READY = "PARTIAL_FETCH_READY_FOR_RESUME"
BLOCKED_MISSING_AW = "BLOCKED_BY_MISSING_PHASE4AW_SUMMARY"
BLOCKED_AW_NOT_READY = "BLOCKED_BY_PHASE4AW_NOT_READY"
BLOCKED_MISSING_REQUESTS = "BLOCKED_BY_MISSING_DRY_RUN_REQUESTS"
BLOCKED_MISSING_CREDENTIAL = "BLOCKED_BY_MISSING_CREDENTIAL"
BLOCKED_SECRET_SAFETY = "BLOCKED_BY_SECRET_SAFETY"
BLOCKED_RATE_LIMIT = "BLOCKED_BY_RATE_LIMIT_SAFETY"
BLOCKED_FETCH_FAILURE = "BLOCKED_BY_FETCH_FAILURE"
BLOCKED_RAW_WRITE = "BLOCKED_BY_RAW_WRITE_FAILURE"
BLOCKED_MANIFEST = "BLOCKED_BY_MANIFEST_FAILURE"
BLOCKED_OUTPUT_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"

RAW_OUTPUT_DIR = Path(".runtime/data/raw/jquants/equities_bars_daily")
ENDPOINT = "/v2/equities/bars/daily"


def main() -> int:
    summary = run_long_history_controlled_fetch()
    _print_human_summary(summary)
    return 0 if summary.get("status") in {"OK", "PARTIAL"} else 1


def run_long_history_controlled_fetch(
    *,
    phase4aw_summary_path: Path = PHASE4AW_SUMMARY_PATH,
    phase4aw_requests_path: Path = PHASE4AW_REQUESTS_PATH,
    summary_path: Path = SUMMARY_PATH,
    report_path: Path = REPORT_PATH,
    raw_output_dir: Path = RAW_OUTPUT_DIR,
    settings_loader: Callable[[], Any] = load_settings,
    client_factory: Callable[[Any], Any] | None = None,
    max_pages: int = 100,
    max_consecutive_failures: int = 20,
) -> dict[str, Any]:
    phase4aw = _read_json_optional(phase4aw_summary_path)
    if not phase4aw:
        summary = _blocked_summary(summary_path, BLOCKED_MISSING_AW)
        _write_markdown_report(report_path, summary)
        return summary
    if phase4aw.get("readiness_status") != "READY_FOR_LONG_HISTORY_CONTROLLED_FETCH":
        summary = _blocked_summary(summary_path, BLOCKED_AW_NOT_READY, phase4aw=phase4aw)
        _write_markdown_report(report_path, summary)
        return summary
    artifact = _read_json_optional(phase4aw_requests_path)
    requests = artifact.get("requests") if isinstance(artifact.get("requests"), list) else []
    if not requests:
        summary = _blocked_summary(summary_path, BLOCKED_MISSING_REQUESTS, phase4aw=phase4aw)
        _write_markdown_report(report_path, summary)
        return summary
    if not _output_paths_safe(raw_output_dir):
        summary = _blocked_summary(summary_path, BLOCKED_OUTPUT_PATH, phase4aw=phase4aw, planned_request_count=len(requests))
        _write_markdown_report(report_path, summary)
        return summary
    if max_pages < 1:
        summary = _blocked_summary(summary_path, BLOCKED_RATE_LIMIT, phase4aw=phase4aw, planned_request_count=len(requests))
        _write_markdown_report(report_path, summary)
        return summary

    credential_read_performed = True
    try:
        settings = settings_loader()
        api_key = settings.jquants.require_api_key()
    except ConfigurationError:
        summary = _blocked_summary(
            summary_path,
            BLOCKED_MISSING_CREDENTIAL,
            phase4aw=phase4aw,
            planned_request_count=len(requests),
            credential_read_performed=credential_read_performed,
            secret_present=False,
        )
        _write_markdown_report(report_path, summary)
        return summary
    secret_present = bool(api_key)

    try:
        client = client_factory(settings) if client_factory else JQuantsClient(settings.jquants, settings.runtime_paths)
    except Exception as exc:
        summary = _blocked_summary(
            summary_path,
            BLOCKED_SECRET_SAFETY,
            phase4aw=phase4aw,
            planned_request_count=len(requests),
            credential_read_performed=credential_read_performed,
            secret_present=secret_present,
            error_message=_sanitize_text(str(exc), api_key),
        )
        _write_markdown_report(report_path, summary)
        return summary

    try:
        request_manifest_dir = raw_output_dir / "request_manifests"
        response_dir = raw_output_dir / "responses"
        request_manifest_dir.mkdir(parents=True, exist_ok=True)
        response_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        summary = _blocked_summary(
            summary_path,
            BLOCKED_RAW_WRITE,
            phase4aw=phase4aw,
            planned_request_count=len(requests),
            credential_read_performed=credential_read_performed,
            http_client_initialized=True,
            secret_present=secret_present,
            error_message=_sanitize_text(str(exc), api_key),
        )
        _write_markdown_report(report_path, summary)
        return summary

    executed = succeeded = failed = skipped = pagination_requests = 0
    consecutive_failures = 0
    stopped_early = False
    partial_stop_reason: str | None = None
    fetched_rows: list[dict[str, Any]] = []
    failed_dates: list[str] = []
    partial_warnings: list[str] = []

    for planned_request in requests:
        target_date = _request_date(planned_request)
        if not target_date:
            failed += 1
            failed_dates.append("unknown")
            continue
        manifest_path = request_manifest_dir / f"{target_date}.json"
        existing_manifest = _read_json_optional(manifest_path)
        if existing_manifest.get("status") == "SUCCESS":
            fetched_rows.extend(_read_rows_from_response_files(response_dir=response_dir, target_date=target_date))
            skipped += 1
            consecutive_failures = 0
            continue
        tmp_files = sorted(response_dir.glob(f"{target_date}_page_*.tmp"))
        if tmp_files:
            partial_warnings.extend(str(path) for path in tmp_files)

        executed += 1
        page = 1
        pagination_key: str | None = None
        page_count = 0
        date_rows: list[dict[str, Any]] = []
        try:
            while page <= max_pages:
                payload = client.fetch_daily_quotes(date=target_date, pagination_key=pagination_key)
                response_path = response_dir / f"{target_date}_page_{page:03d}.json"
                _atomic_write_json(
                    response_path,
                    {
                        "phase": PHASE,
                        "endpoint": ENDPOINT,
                        "date": target_date,
                        "page": page,
                        "params": {"date": target_date, "code": None, "pagination_key": pagination_key},
                        "payload": payload,
                        "api_call_performed": True,
                    },
                )
                page_count += 1
                if page > 1:
                    pagination_requests += 1
                rows = payload.get("data") if isinstance(payload, dict) else []
                if isinstance(rows, list):
                    for row in rows:
                        if isinstance(row, dict):
                            enriched = dict(row)
                            enriched.setdefault("target_date", target_date)
                            enriched.setdefault("endpoint", ENDPOINT)
                            enriched.setdefault("pagination_page", page)
                            date_rows.append(enriched)
                pagination_key = payload.get("pagination_key") if isinstance(payload, dict) else None
                if not pagination_key:
                    break
                page += 1
            if pagination_key:
                raise RuntimeError("max_pages exceeded before pagination completed")
            _atomic_write_json(
                manifest_path,
                _request_manifest(
                    target_date=target_date,
                    status="SUCCESS",
                    page_count=page_count,
                    row_count=len(date_rows),
                    error_message=None,
                ),
            )
            fetched_rows.extend(date_rows)
            succeeded += 1
            consecutive_failures = 0
        except Exception as exc:
            failed += 1
            consecutive_failures += 1
            failed_dates.append(target_date)
            _atomic_write_json(
                manifest_path,
                _request_manifest(
                    target_date=target_date,
                    status="FAILED",
                    page_count=page_count,
                    row_count=len(date_rows),
                    error_message=_sanitize_text(str(exc), api_key),
                ),
            )
            if consecutive_failures >= max_consecutive_failures:
                stopped_early = True
                partial_stop_reason = f"stopped after {consecutive_failures} consecutive failed requests"
                break
            continue

    run_manifest = _run_manifest(
        phase4aw=phase4aw,
        planned_request_count=len(requests),
        executed=executed,
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        pagination_requests=pagination_requests,
        raw_output_dir=raw_output_dir,
        secret_present=secret_present,
    )
    try:
        _atomic_write_json(raw_output_dir / "manifest.json", run_manifest)
    except Exception as exc:
        summary = _blocked_summary(
            summary_path,
            BLOCKED_MANIFEST,
            phase4aw=phase4aw,
            planned_request_count=len(requests),
            credential_read_performed=credential_read_performed,
            http_client_initialized=True,
            secret_present=secret_present,
            error_message=_sanitize_text(str(exc), api_key),
        )
        _write_markdown_report(report_path, summary)
        return summary

    fetched_dates = sorted({str(row.get("Date") or row.get("target_date")) for row in fetched_rows if row})
    fetched_codes = sorted({str(row.get("Code") or row.get("code")) for row in fetched_rows if row.get("Code") or row.get("code")})
    completed = succeeded + skipped
    readiness_status = READY if completed == len(requests) and failed == 0 else PARTIAL_READY
    status = "OK" if readiness_status == READY else "PARTIAL"
    summary = {
        "phase": PHASE,
        "status": status,
        "readiness_status": readiness_status,
        "api_call_performed": executed > 0,
        "fetch_executed": executed > 0,
        "credential_read_performed": credential_read_performed,
        "http_client_initialized": True,
        "raw_data_written": bool(fetched_rows),
        "normalized_data_written": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "phase4aw_summary_detected": True,
        "phase4aw_readiness_status": phase4aw.get("readiness_status"),
        "dry_run_requests_detected": True,
        "target_start_date": phase4aw.get("target_start_date"),
        "target_end_date": phase4aw.get("target_end_date"),
        "planned_request_count": len(requests),
        "executed_request_count": executed,
        "succeeded_request_count": succeeded,
        "failed_request_count": failed,
        "skipped_request_count": skipped,
        "completed_request_count": completed,
        "pagination_request_count": pagination_requests,
        "endpoint": ENDPOINT,
        "method": "GET",
        "rate_limit_policy": phase4aw.get("rate_limit_policy"),
        "raw_output_path": str(raw_output_dir) + "/",
        "raw_manifest_path": str(raw_output_dir / "manifest.json"),
        "secret_present": secret_present,
        "secret_fingerprint": _fingerprint_secret(api_key) if secret_present else None,
        "secret_value_logged": False,
        "secret_value_written": False,
        "normalized_output_written": False,
        "mock_path_written": False,
        "isolated_normalized_path_written": False,
        "resume_supported": True,
        "partial_failure_supported": True,
        "existing_raw_preserved": True,
        "partial_tmp_warnings": partial_warnings,
        "stopped_early": stopped_early,
        "partial_stop_reason": partial_stop_reason,
        "failed_dates": failed_dates,
        "fetched_date_min": fetched_dates[0] if fetched_dates else None,
        "fetched_date_max": fetched_dates[-1] if fetched_dates else None,
        "fetched_business_day_count": len(fetched_dates),
        "fetched_row_count": len(fetched_rows),
        "fetched_code_count": len(fetched_codes),
        "recommended_next_action": _recommended_next_action(readiness_status),
    }
    if _contains_secret(summary, api_key) or _contains_secret(run_manifest, api_key):
        summary["status"] = "BLOCKED"
        summary["readiness_status"] = BLOCKED_SECRET_SAFETY
        summary["secret_value_written"] = True
    _write_json(summary_path, summary)
    _write_markdown_report(report_path, summary)
    return summary


def _request_date(request: dict[str, Any]) -> str:
    return str(request.get("date") or request.get("params", {}).get("date") or "")


def _request_manifest(
    *,
    target_date: str,
    status: str,
    page_count: int,
    row_count: int,
    error_message: str | None,
) -> dict[str, Any]:
    return {
        "created_at": _now_utc(),
        "phase": PHASE,
        "endpoint": ENDPOINT,
        "target_date": target_date,
        "status": status,
        "page_count": page_count,
        "row_count": row_count,
        "request_params": {"date": target_date, "code": None},
        "error_message": error_message,
        "secret_value_written": False,
    }


def _run_manifest(
    *,
    phase4aw: dict[str, Any],
    planned_request_count: int,
    executed: int,
    succeeded: int,
    failed: int,
    skipped: int,
    pagination_requests: int,
    raw_output_dir: Path,
    secret_present: bool,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "updated_at": _now_utc(),
        "endpoint": ENDPOINT,
        "target_start_date": phase4aw.get("target_start_date"),
        "target_end_date": phase4aw.get("target_end_date"),
        "planned_request_count": planned_request_count,
        "executed_request_count": executed,
        "succeeded_request_count": succeeded,
        "failed_request_count": failed,
        "skipped_request_count": skipped,
        "completed_request_count": succeeded + skipped,
        "pagination_request_count": pagination_requests,
        "raw_output_path": str(raw_output_dir),
        "secret_present": secret_present,
        "secret_value_logged": False,
        "secret_value_written": False,
        "promotion_status": "not_promoted",
        "normalized_rebuild_performed": False,
        "reader_switch_performed": False,
    }


def _blocked_summary(
    summary_path: Path,
    readiness_status: str,
    *,
    phase4aw: dict[str, Any] | None = None,
    planned_request_count: int = 0,
    credential_read_performed: bool = False,
    http_client_initialized: bool = False,
    secret_present: bool = False,
    error_message: str | None = None,
) -> dict[str, Any]:
    phase4aw = phase4aw or {}
    summary = {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "fetch_executed": False,
        "credential_read_performed": credential_read_performed,
        "http_client_initialized": http_client_initialized,
        "raw_data_written": False,
        "normalized_data_written": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "phase4aw_summary_detected": bool(phase4aw),
        "phase4aw_readiness_status": phase4aw.get("readiness_status"),
        "dry_run_requests_detected": False,
        "target_start_date": phase4aw.get("target_start_date"),
        "target_end_date": phase4aw.get("target_end_date"),
        "planned_request_count": planned_request_count or int(phase4aw.get("request_count") or 0),
        "executed_request_count": 0,
        "succeeded_request_count": 0,
        "failed_request_count": 0,
        "skipped_request_count": 0,
        "completed_request_count": 0,
        "pagination_request_count": 0,
        "endpoint": ENDPOINT,
        "method": "GET",
        "rate_limit_policy": phase4aw.get("rate_limit_policy"),
        "raw_output_path": str(RAW_OUTPUT_DIR) + "/",
        "raw_manifest_path": str(RAW_OUTPUT_DIR / "manifest.json"),
        "secret_present": secret_present,
        "secret_value_logged": False,
        "secret_value_written": False,
        "normalized_output_written": False,
        "mock_path_written": False,
        "isolated_normalized_path_written": False,
        "resume_supported": True,
        "partial_failure_supported": True,
        "existing_raw_preserved": True,
        "fetched_date_min": None,
        "fetched_date_max": None,
        "fetched_business_day_count": 0,
        "fetched_row_count": 0,
        "fetched_code_count": 0,
        "error_message": error_message,
        "recommended_next_action": "Resolve the blocking condition before Phase4-AY.",
    }
    _write_json(summary_path, summary)
    return summary


def _recommended_next_action(readiness_status: str) -> str:
    if readiness_status == READY:
        return "Phase4-AY Long History Raw Coverage Audit before normalization."
    if readiness_status == PARTIAL_READY:
        return "Rerun Phase4-AX to resume failed or missing request manifests before Phase4-AY."
    return "Resolve the blocking fetch condition before continuing."


def _output_paths_safe(raw_output_dir: Path) -> bool:
    raw = str(raw_output_dir)
    return (
        raw.endswith(".runtime/data/raw/jquants/equities_bars_daily")
        or raw.endswith("runtime/data/raw/jquants/equities_bars_daily")
        or "raw/jquants/equities_bars_daily" in raw
    ) and "raw_normalized" not in raw


def _fingerprint_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _contains_secret(payload: dict[str, Any], secret: str) -> bool:
    if not secret:
        return False
    return secret in json.dumps(payload, ensure_ascii=True)


def _read_rows_from_response_files(*, response_dir: Path, target_date: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for response_path in sorted(response_dir.glob(f"{target_date}_page_*.json")):
        payload = _read_json_optional(response_path).get("payload")
        page_rows = payload.get("data") if isinstance(payload, dict) else []
        if isinstance(page_rows, list):
            for row in page_rows:
                if isinstance(row, dict):
                    enriched = dict(row)
                    enriched.setdefault("target_date", target_date)
                    rows.append(enriched)
    return rows


def _sanitize_text(text: str, secret: str | None = None) -> str:
    sanitized = text
    if secret:
        sanitized = sanitized.replace(secret, "[REDACTED]")
    for marker in ("Authorization", "x-api-key"):
        sanitized = sanitized.replace(marker, "[REDACTED_HEADER]")
    return sanitized


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _write_markdown_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AX Long History Controlled Fetch",
        "",
        f"- status: `{summary.get('status')}`",
        f"- readiness_status: `{summary.get('readiness_status')}`",
        f"- target range: `{summary.get('target_start_date')}` to `{summary.get('target_end_date')}`",
        f"- planned/executed/succeeded/failed/skipped/completed: `{summary.get('planned_request_count')}` / `{summary.get('executed_request_count')}` / `{summary.get('succeeded_request_count')}` / `{summary.get('failed_request_count')}` / `{summary.get('skipped_request_count')}` / `{summary.get('completed_request_count')}`",
        f"- pagination_request_count: `{summary.get('pagination_request_count')}`",
        f"- fetched date range: `{summary.get('fetched_date_min')}` to `{summary.get('fetched_date_max')}`",
        f"- fetched_business_day_count: `{summary.get('fetched_business_day_count')}`",
        f"- fetched_row_count: `{summary.get('fetched_row_count')}`",
        f"- fetched_code_count: `{summary.get('fetched_code_count')}`",
        f"- raw_output_path: `{summary.get('raw_output_path')}`",
        f"- raw_manifest_path: `{summary.get('raw_manifest_path')}`",
        "",
        "## Safety",
        "",
        f"- credential_read_performed: `{summary.get('credential_read_performed')}`",
        f"- secret_present: `{summary.get('secret_present')}`",
        f"- secret_value_logged: `{summary.get('secret_value_logged')}`",
        f"- secret_value_written: `{summary.get('secret_value_written')}`",
        f"- normalized_data_written: `{summary.get('normalized_data_written')}`",
        f"- mock_path_written: `{summary.get('mock_path_written')}`",
        f"- isolated_normalized_path_written: `{summary.get('isolated_normalized_path_written')}`",
        f"- feature_generation_executed: `{summary.get('feature_generation_executed')}`",
        f"- label_generation_executed: `{summary.get('label_generation_executed')}`",
        f"- dataset_rebuild_executed: `{summary.get('dataset_rebuild_executed')}`",
        f"- training_executed: `{summary.get('training_executed')}`",
        f"- inference_executed: `{summary.get('inference_executed')}`",
        f"- backtest_executed: `{summary.get('backtest_executed')}`",
        f"- trading_executed: `{summary.get('trading_executed')}`",
        f"- promotion_performed: `{summary.get('promotion_performed')}`",
        f"- reader_switch_performed: `{summary.get('reader_switch_performed')}`",
        "",
        "## Recommended Next Action",
        "",
        str(summary.get("recommended_next_action") or ""),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _print_human_summary(summary: dict[str, Any]) -> None:
    print("Phase4-AX long history controlled raw fetch")
    print(f"status={summary.get('status')}")
    print(f"readiness_status={summary.get('readiness_status')}")
    print(f"target_date_range={summary.get('target_start_date')}..{summary.get('target_end_date')}")
    print(f"planned_request_count={summary.get('planned_request_count')}")
    print(f"executed_request_count={summary.get('executed_request_count')}")
    print(f"succeeded_request_count={summary.get('succeeded_request_count')}")
    print(f"failed_request_count={summary.get('failed_request_count')}")
    print(f"skipped_request_count={summary.get('skipped_request_count')}")
    print(f"raw_manifest_path={summary.get('raw_manifest_path')}")
    print(f"secret_present={summary.get('secret_present')}")
    print("secret_value_logged=false")


if __name__ == "__main__":
    raise SystemExit(main())
