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

PHASE4AG_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ag_real_runtime_extension_fetch_dry_run_summary.json")
PHASE4AG_REQUESTS_PATH = Path("reports/candidate_ai/full_range/phase4ag_real_runtime_extension_fetch_dry_run_requests.json")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ah_controlled_extension_fetch_summary.json")

READY = "READY_FOR_POST_EXTENSION_RAW_COVERAGE_AUDIT"
BLOCKED_MISSING_AG = "BLOCKED_BY_MISSING_PHASE4AG_SUMMARY"
BLOCKED_AG_NOT_READY = "BLOCKED_BY_PHASE4AG_NOT_READY"
BLOCKED_MISSING_REQUESTS = "BLOCKED_BY_MISSING_DRY_RUN_REQUESTS"
BLOCKED_MISSING_CREDENTIAL = "BLOCKED_BY_MISSING_CREDENTIAL"
BLOCKED_SECRET_SAFETY = "BLOCKED_BY_SECRET_SAFETY"
BLOCKED_RATE_LIMIT = "BLOCKED_BY_RATE_LIMIT_SAFETY"
BLOCKED_FETCH_FAILURE = "BLOCKED_BY_EXTENSION_FETCH_FAILURE"
BLOCKED_RAW_WRITE = "BLOCKED_BY_RAW_WRITE_FAILURE"
BLOCKED_MANIFEST = "BLOCKED_BY_MANIFEST_FAILURE"
BLOCKED_OUTPUT_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"

RAW_OUTPUT_DIR = Path(".runtime/data/raw/jquants/equities_bars_daily")
ENDPOINT = "/v2/equities/bars/daily"


def main() -> int:
    summary = run_controlled_extension_fetch()
    _print_human_summary(summary)
    return 0 if summary.get("status") == "OK" else 1


def run_controlled_extension_fetch(
    *,
    phase4ag_summary_path: Path = PHASE4AG_SUMMARY_PATH,
    phase4ag_requests_path: Path = PHASE4AG_REQUESTS_PATH,
    summary_path: Path = SUMMARY_PATH,
    raw_output_dir: Path = RAW_OUTPUT_DIR,
    settings_loader: Callable[[], Any] = load_settings,
    client_factory: Callable[[Any], Any] | None = None,
    max_pages: int = 100,
) -> dict[str, Any]:
    phase4ag = _read_json_optional(phase4ag_summary_path)
    if not phase4ag:
        return _write_blocked(summary_path, BLOCKED_MISSING_AG)
    if phase4ag.get("readiness_status") != "READY_FOR_CONTROLLED_EXTENSION_FETCH":
        return _write_blocked(summary_path, BLOCKED_AG_NOT_READY, phase4ag=phase4ag)
    artifact = _read_json_optional(phase4ag_requests_path)
    requests = artifact.get("requests") if isinstance(artifact.get("requests"), list) else []
    if not requests:
        return _write_blocked(summary_path, BLOCKED_MISSING_REQUESTS, phase4ag=phase4ag)
    if not _output_paths_safe(raw_output_dir):
        return _write_blocked(summary_path, BLOCKED_OUTPUT_PATH, phase4ag=phase4ag, planned_count=len(requests))
    if max_pages < 1:
        return _write_blocked(summary_path, BLOCKED_RATE_LIMIT, phase4ag=phase4ag, planned_count=len(requests))

    allowed_dates = set(str(day) for day in phase4ag.get("extension_requested_dates") or [])
    request_dates = {str(request.get("date") or request.get("params", {}).get("date")) for request in requests}
    if request_dates != allowed_dates:
        return _write_blocked(summary_path, BLOCKED_MISSING_REQUESTS, phase4ag=phase4ag, planned_count=len(requests))

    credential_read_performed = True
    try:
        settings = settings_loader()
        api_key = settings.jquants.require_api_key()
    except ConfigurationError:
        return _write_blocked(
            summary_path,
            BLOCKED_MISSING_CREDENTIAL,
            phase4ag=phase4ag,
            planned_count=len(requests),
            credential_read_performed=credential_read_performed,
            secret_present=False,
        )
    secret_present = bool(api_key)

    try:
        client = client_factory(settings) if client_factory else JQuantsClient(settings.jquants, settings.runtime_paths)
    except Exception as exc:
        return _write_blocked(
            summary_path,
            BLOCKED_SECRET_SAFETY,
            phase4ag=phase4ag,
            planned_count=len(requests),
            credential_read_performed=credential_read_performed,
            secret_present=secret_present,
            error_message=_sanitize_text(str(exc), api_key),
        )

    try:
        raw_output_dir.mkdir(parents=True, exist_ok=True)
        request_manifest_dir = raw_output_dir / "request_manifests"
        response_dir = raw_output_dir / "responses"
        request_manifest_dir.mkdir(parents=True, exist_ok=True)
        response_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return _write_blocked(
            summary_path,
            BLOCKED_RAW_WRITE,
            phase4ag=phase4ag,
            planned_count=len(requests),
            credential_read_performed=credential_read_performed,
            http_client_initialized=True,
            secret_present=secret_present,
            error_message=_sanitize_text(str(exc), api_key),
        )

    executed = succeeded = failed = skipped = pagination_requests = 0
    fetched_rows: list[dict[str, Any]] = []
    failed_dates: list[str] = []
    partial_warnings: list[str] = []

    for planned_request in requests:
        target_date = str(planned_request.get("date") or planned_request.get("params", {}).get("date") or "")
        if target_date not in allowed_dates:
            failed += 1
            failed_dates.append(target_date or "unknown")
            continue
        manifest_path = request_manifest_dir / f"{target_date}.json"
        existing_manifest = _read_json_optional(manifest_path)
        if existing_manifest.get("status") == "SUCCESS":
            fetched_rows.extend(_read_rows_from_response_files(response_dir=response_dir, target_date=target_date))
            skipped += 1
            continue
        tmp_files = sorted(response_dir.glob(f"{target_date}_page_*.tmp"))
        if tmp_files:
            partial_warnings.extend(str(path) for path in tmp_files)

        executed += 1
        page = 1
        pagination_key: str | None = None
        date_rows: list[dict[str, Any]] = []
        page_count = 0
        try:
            while page <= max_pages:
                payload = client.fetch_daily_quotes(date=target_date, pagination_key=pagination_key)
                response_path = response_dir / f"{target_date}_page_{page:03d}.json"
                _atomic_write_json(
                    response_path,
                    {
                        "phase": "Phase4-AH",
                        "endpoint": ENDPOINT,
                        "date": target_date,
                        "page": page,
                        "params": {"date": target_date, "code": None, "pagination_key": pagination_key},
                        "payload": payload,
                        "api_call_performed": True,
                        "extension_fetch": True,
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
        except Exception as exc:
            failed += 1
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
            continue

    existing_run_manifest = _read_json_optional(raw_output_dir / "manifest.json")
    run_manifest = _merged_run_manifest(
        existing_run_manifest=existing_run_manifest,
        phase4ag=phase4ag,
        planned_count=len(requests),
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
        return _write_blocked(
            summary_path,
            BLOCKED_MANIFEST,
            phase4ag=phase4ag,
            planned_count=len(requests),
            credential_read_performed=credential_read_performed,
            http_client_initialized=True,
            secret_present=secret_present,
            error_message=_sanitize_text(str(exc), api_key),
        )

    fetched_dates = sorted({str(row.get("Date") or row.get("target_date")) for row in fetched_rows if row})
    fetched_codes = sorted({str(row.get("Code")) for row in fetched_rows if row.get("Code")})
    status = "OK" if failed == 0 else "BLOCKED"
    readiness_status = READY if failed == 0 else BLOCKED_FETCH_FAILURE
    summary = {
        "status": status,
        "readiness_status": readiness_status,
        "api_call_performed": executed > 0,
        "extension_fetch_executed": executed > 0,
        "credential_read_performed": credential_read_performed,
        "http_client_initialized": True,
        "raw_data_written": bool(fetched_rows),
        "raw_manifest_updated": True,
        "normalized_data_written": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "phase4ag_summary_detected": True,
        "phase4ag_readiness_status": phase4ag.get("readiness_status"),
        "dry_run_requests_detected": True,
        "extension_fetch_start_date": phase4ag.get("extension_fetch_start_date"),
        "extension_fetch_end_date": phase4ag.get("extension_fetch_end_date"),
        "extension_requested_dates": list(phase4ag.get("extension_requested_dates") or []),
        "planned_extension_request_count": len(requests),
        "executed_extension_request_count": executed,
        "succeeded_extension_request_count": succeeded,
        "failed_extension_request_count": failed,
        "skipped_extension_request_count": skipped,
        "completed_extension_request_count": succeeded + skipped,
        "pagination_request_count": pagination_requests,
        "endpoint": ENDPOINT,
        "method": "GET",
        "rate_limit_policy": phase4ag.get("rate_limit_policy"),
        "retry_policy": phase4ag.get("retry_policy"),
        "raw_output_path": str(raw_output_dir) + "/",
        "raw_manifest_path": str(raw_output_dir / "manifest.json"),
        "secret_present": secret_present,
        "secret_fingerprint": _fingerprint_secret(api_key) if secret_present else None,
        "secret_value_logged": False,
        "secret_value_written": False,
        "normalized_output_written": False,
        "mock_path_written": False,
        "isolated_normalized_path_written": False,
        "existing_raw_preserved": True,
        "existing_success_manifest_preserved": True,
        "resume_supported": True,
        "partial_failure_supported": True,
        "partial_tmp_warnings": partial_warnings,
        "failed_dates": failed_dates,
        "fetched_extension_date_min": fetched_dates[0] if fetched_dates else None,
        "fetched_extension_date_max": fetched_dates[-1] if fetched_dates else None,
        "fetched_extension_date_count": len(fetched_dates),
        "fetched_extension_row_count": len(fetched_rows),
        "fetched_extension_code_count": len(fetched_codes),
        "recommended_next_action": "Phase4-AI Post-extension Raw Coverage Audit before any normalization.",
    }
    if _contains_secret(summary, api_key) or _contains_secret(run_manifest, api_key):
        summary["status"] = "BLOCKED"
        summary["readiness_status"] = BLOCKED_SECRET_SAFETY
        summary["secret_value_written"] = True
    _write_json(summary_path, summary)
    return summary


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
        "phase": "Phase4-AH",
        "endpoint": ENDPOINT,
        "target_date": target_date,
        "status": status,
        "page_count": page_count,
        "row_count": row_count,
        "request_params": {"date": target_date, "code": None},
        "merge_mode": "extension_date_only",
        "error_message": error_message,
        "secret_value_written": False,
    }


def _merged_run_manifest(
    *,
    existing_run_manifest: dict[str, Any],
    phase4ag: dict[str, Any],
    planned_count: int,
    executed: int,
    succeeded: int,
    failed: int,
    skipped: int,
    pagination_requests: int,
    raw_output_dir: Path,
    secret_present: bool,
) -> dict[str, Any]:
    previous_planned = int(existing_run_manifest.get("planned_request_count") or 0)
    previous_succeeded = int(existing_run_manifest.get("succeeded_request_count") or 0)
    previous_failed = int(existing_run_manifest.get("failed_request_count") or 0)
    previous_skipped = int(existing_run_manifest.get("skipped_request_count") or 0)
    previous_completed = int(existing_run_manifest.get("completed_request_count") or (previous_succeeded + previous_skipped))
    previous_pagination = int(existing_run_manifest.get("pagination_request_count") or 0)
    return {
        **existing_run_manifest,
        "phase": "Phase4-AH",
        "updated_at": _now_utc(),
        "endpoint": ENDPOINT,
        "target_start_date": existing_run_manifest.get("target_start_date"),
        "target_end_date": existing_run_manifest.get("target_end_date"),
        "extension_fetch_start_date": phase4ag.get("extension_fetch_start_date"),
        "extension_fetch_end_date": phase4ag.get("extension_fetch_end_date"),
        "planned_request_count": previous_planned + planned_count,
        "extension_planned_request_count": planned_count,
        "extension_executed_request_count": executed,
        "extension_succeeded_request_count": succeeded,
        "extension_failed_request_count": failed,
        "extension_skipped_request_count": skipped,
        "executed_request_count": int(existing_run_manifest.get("executed_request_count") or 0) + executed,
        "succeeded_request_count": previous_succeeded + succeeded,
        "failed_request_count": previous_failed + failed,
        "skipped_request_count": previous_skipped + skipped,
        "completed_request_count": previous_completed + succeeded + skipped,
        "pagination_request_count": previous_pagination + pagination_requests,
        "raw_output_path": str(raw_output_dir),
        "secret_present": secret_present,
        "secret_value_logged": False,
        "secret_value_written": False,
        "promotion_status": "not_promoted",
        "normalized_rebuild_performed": False,
    }


def _write_blocked(
    summary_path: Path,
    readiness_status: str,
    *,
    phase4ag: dict[str, Any] | None = None,
    planned_count: int = 0,
    credential_read_performed: bool = False,
    http_client_initialized: bool = False,
    secret_present: bool = False,
    error_message: str | None = None,
) -> dict[str, Any]:
    phase4ag = phase4ag or {}
    summary = {
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "extension_fetch_executed": False,
        "credential_read_performed": credential_read_performed,
        "http_client_initialized": http_client_initialized,
        "raw_data_written": False,
        "raw_manifest_updated": False,
        "normalized_data_written": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "phase4ag_summary_detected": bool(phase4ag),
        "phase4ag_readiness_status": phase4ag.get("readiness_status"),
        "dry_run_requests_detected": False,
        "extension_fetch_start_date": phase4ag.get("extension_fetch_start_date"),
        "extension_fetch_end_date": phase4ag.get("extension_fetch_end_date"),
        "extension_requested_dates": list(phase4ag.get("extension_requested_dates") or []),
        "planned_extension_request_count": planned_count or int(phase4ag.get("extension_request_count") or 0),
        "executed_extension_request_count": 0,
        "succeeded_extension_request_count": 0,
        "failed_extension_request_count": 0,
        "skipped_extension_request_count": 0,
        "completed_extension_request_count": 0,
        "pagination_request_count": 0,
        "endpoint": ENDPOINT,
        "method": "GET",
        "rate_limit_policy": phase4ag.get("rate_limit_policy"),
        "retry_policy": phase4ag.get("retry_policy"),
        "raw_output_path": str(RAW_OUTPUT_DIR) + "/",
        "raw_manifest_path": str(RAW_OUTPUT_DIR / "manifest.json"),
        "secret_present": secret_present,
        "secret_value_logged": False,
        "secret_value_written": False,
        "normalized_output_written": False,
        "mock_path_written": False,
        "isolated_normalized_path_written": False,
        "existing_raw_preserved": True,
        "existing_success_manifest_preserved": True,
        "resume_supported": True,
        "partial_failure_supported": True,
        "fetched_extension_date_min": None,
        "fetched_extension_date_max": None,
        "fetched_extension_date_count": 0,
        "fetched_extension_row_count": 0,
        "fetched_extension_code_count": 0,
        "error_message": error_message,
        "recommended_next_action": "Resolve the blocking condition before Phase4-AI.",
    }
    _write_json(summary_path, summary)
    return summary


def _output_paths_safe(raw_output_dir: Path) -> bool:
    raw = str(raw_output_dir)
    return (
        raw.endswith(".runtime/data/raw/jquants/equities_bars_daily")
        or raw.endswith("runtime/data/raw/jquants/equities_bars_daily")
        or "raw/jquants/equities_bars_daily" in raw
    ) and "raw_normalized" not in raw


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


def _fingerprint_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _contains_secret(payload: dict[str, Any], secret: str) -> bool:
    if not secret:
        return False
    return secret in json.dumps(payload, ensure_ascii=True)


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


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _print_human_summary(summary: dict[str, Any]) -> None:
    print("Phase4-AH controlled extension raw fetch")
    print(f"status={summary.get('status')}")
    print(f"readiness_status={summary.get('readiness_status')}")
    print(f"extension_date_range={summary.get('extension_fetch_start_date')}..{summary.get('extension_fetch_end_date')}")
    print(f"planned_extension_request_count={summary.get('planned_extension_request_count')}")
    print(f"executed_extension_request_count={summary.get('executed_extension_request_count')}")
    print(f"succeeded_extension_request_count={summary.get('succeeded_extension_request_count')}")
    print(f"failed_extension_request_count={summary.get('failed_extension_request_count')}")
    print(f"skipped_extension_request_count={summary.get('skipped_extension_request_count')}")
    print(f"raw_manifest_path={summary.get('raw_manifest_path')}")
    print(f"secret_present={summary.get('secret_present')}")
    print("secret_value_logged=false")


if __name__ == "__main__":
    raise SystemExit(main())
