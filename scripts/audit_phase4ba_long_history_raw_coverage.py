#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

PHASE = "Phase4-BA"
RAW_DIR = Path(".runtime/data/raw/jquants/equities_bars_daily")
AZ_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4az_long_history_controlled_fetch_retry_summary.json")
AY_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ay_long_history_request_regeneration_summary.json")
AY_REQUESTS_PATH = Path("reports/candidate_ai/full_range/phase4ay_long_history_corrected_requests.json")
AV_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4av_long_history_fetch_plan_summary.json")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ba_long_history_raw_coverage_summary.json")
REPORT_PATH = Path("docs/phase_reports/phase4ba_long_history_raw_coverage.md")

READY = "READY_FOR_LONG_HISTORY_NORMALIZED_REBUILD"
BLOCKED_COVERAGE = "BLOCKED_BY_RAW_COVERAGE_GAP"
BLOCKED_NON_BOUNDARY = "BLOCKED_BY_NON_BOUNDARY_FAILURES"
BLOCKED_SCHEMA = "BLOCKED_BY_RAW_SCHEMA"
BLOCKED_MANIFEST = "BLOCKED_BY_MANIFEST_INCONSISTENCY"
BLOCKED_SECRET = "BLOCKED_BY_SECRET_LEAK"

BOUNDARY_FAILED_DATES = {
    "2021-06-01",
    "2021-06-02",
    "2021-06-03",
    "2021-06-04",
    "2021-06-07",
    "2021-06-08",
    "2021-06-09",
    "2021-06-10",
    "2021-06-11",
}
REQUIRED_ROW_KEYS = {"Date", "Code"}
PRICE_KEYS = {"O", "H", "L", "C", "AdjO", "AdjH", "AdjL", "AdjC"}


def main() -> int:
    summary = audit_phase4ba_long_history_raw_coverage()
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") == "OK" else 1


def audit_phase4ba_long_history_raw_coverage(
    *,
    raw_dir: Path = RAW_DIR,
    az_summary_path: Path = AZ_SUMMARY_PATH,
    ay_summary_path: Path = AY_SUMMARY_PATH,
    ay_requests_path: Path = AY_REQUESTS_PATH,
    av_summary_path: Path = AV_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    az_summary = _read_json_optional(az_summary_path)
    ay_summary = _read_json_optional(ay_summary_path)
    ay_requests = _read_json_optional(ay_requests_path)
    av_summary = _read_json_optional(av_summary_path)
    manifest_dir = raw_dir / "request_manifests"
    response_dir = raw_dir / "responses"
    request_manifests = _load_request_manifests(manifest_dir)
    response_files = sorted(response_dir.glob("*_page_*.json"))

    failed_dates = sorted(
        str(manifest.get("target_date") or target_date)
        for target_date, manifest in request_manifests.items()
        if manifest.get("status") == "FAILED" and _date_in_corrected_artifact(target_date, ay_requests)
    )
    boundary_failed_dates = [day for day in failed_dates if day in BOUNDARY_FAILED_DATES]
    non_boundary_failed_dates = [day for day in failed_dates if day not in BOUNDARY_FAILED_DATES]

    raw_stats = _scan_raw_responses(response_files)
    fetched_dates = raw_stats["fetched_dates"]
    fetched_date_min = fetched_dates[0] if fetched_dates else None
    fetched_date_max = fetched_dates[-1] if fetched_dates else None
    lookback = int(av_summary.get("lookback_business_days") or 60)
    label_horizon = int(av_summary.get("label_horizon_business_days") or 20)
    first_trainable = _nth_business_date(fetched_dates, lookback)
    last_label = _last_label_target_date(fetched_dates, label_horizon)
    split = _split_counts(
        fetched_dates=fetched_dates,
        first_trainable=first_trainable,
        last_label=last_label,
        av_summary=av_summary,
    )

    manifest_consistency_status = _manifest_consistency_status(
        ay_requests=ay_requests,
        request_manifests=request_manifests,
        response_files=response_files,
        succeeded_count=int(az_summary.get("succeeded_request_count") or 0),
        skipped_count=int(az_summary.get("skipped_request_count") or 0),
        failed_count=int(az_summary.get("failed_request_count") or 0),
    )
    secret_value_detected = _secret_detected(
        [az_summary, ay_summary, av_summary, {"request_manifest_sample": list(request_manifests.values())[:20]}]
    )
    formal_training_coverage_sufficient = (
        bool(first_trainable)
        and bool(last_label)
        and split["train_target_date_count_estimate"] > 0
        and split["validation_target_date_count_estimate"] > 0
        and split["test_target_date_count_estimate"] > 0
    )
    boundary_failures_blocking = bool(non_boundary_failed_dates) or not formal_training_coverage_sufficient
    readiness_status = _readiness_status(
        secret_value_detected=secret_value_detected,
        raw_schema_status=raw_stats["raw_schema_status"],
        manifest_consistency_status=manifest_consistency_status,
        non_boundary_failed_dates=non_boundary_failed_dates,
        formal_training_coverage_sufficient=formal_training_coverage_sufficient,
    )
    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "audit_executed": True,
        "api_call_performed": False,
        "fetch_executed": False,
        "additional_fetch_executed": False,
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
        "fetched_date_min": fetched_date_min,
        "fetched_date_max": fetched_date_max,
        "fetched_business_day_count": len(fetched_dates),
        "row_count": raw_stats["row_count"],
        "code_count": raw_stats["code_count"],
        "raw_response_file_count": len(response_files),
        "request_manifest_count": len(request_manifests),
        "completed_request_count": int(az_summary.get("completed_request_count") or 0),
        "succeeded_request_count": int(az_summary.get("succeeded_request_count") or 0),
        "skipped_request_count": int(az_summary.get("skipped_request_count") or 0),
        "failed_request_count": int(az_summary.get("failed_request_count") or len(failed_dates)),
        "failed_dates": failed_dates,
        "boundary_failed_dates": boundary_failed_dates,
        "non_boundary_failed_dates": non_boundary_failed_dates,
        "boundary_failure_policy": (
            "Treat 2021-06-01 through 2021-06-11 failures as expected unavailable start-boundary dates. "
            "They do not block normalization if 60-business-day lookback and 20-business-day label horizon coverage remain sufficient."
        ),
        "boundary_failures_blocking": boundary_failures_blocking,
        "duplicate_date_code_count": raw_stats["duplicate_date_code_count"],
        "raw_schema_status": raw_stats["raw_schema_status"],
        "raw_schema_errors": raw_stats["raw_schema_errors"][:20],
        "manifest_consistency_status": manifest_consistency_status,
        "secret_value_detected": secret_value_detected,
        "lookback_business_days": lookback,
        "label_horizon_business_days": label_horizon,
        "first_trainable_target_date": first_trainable,
        "last_label_target_date": last_label,
        **split,
        "formal_training_coverage_sufficient": formal_training_coverage_sufficient,
        "recommended_next_action": _recommended_next_action(readiness_status),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(summary_path, summary)
    _write_markdown(report_path, summary)
    return summary


def _scan_raw_responses(response_files: list[Path]) -> dict[str, Any]:
    row_count = 0
    global_codes: set[str] = set()
    dates: set[str] = set()
    date_codes: dict[str, set[str]] = defaultdict(set)
    duplicate_date_code_count = 0
    schema_errors: list[str] = []
    for path in response_files:
        payload = _read_json_optional(path)
        rows = payload.get("payload", {}).get("data") if isinstance(payload.get("payload"), dict) else []
        if not isinstance(rows, list):
            schema_errors.append(f"{path}: payload.data is not list")
            continue
        for row in rows:
            if not isinstance(row, dict):
                schema_errors.append(f"{path}: row is not object")
                continue
            row_count += 1
            missing = REQUIRED_ROW_KEYS - set(row.keys())
            if missing:
                schema_errors.append(f"{path}: missing {sorted(missing)}")
                continue
            if not PRICE_KEYS.intersection(row.keys()):
                schema_errors.append(f"{path}: missing price columns")
            target_date = str(row.get("Date") or row.get("target_date") or "")
            code = str(row.get("Code") or row.get("code") or "")
            if target_date:
                dates.add(target_date)
            if code:
                global_codes.add(code)
            if target_date and code:
                if code in date_codes[target_date]:
                    duplicate_date_code_count += 1
                else:
                    date_codes[target_date].add(code)
    return {
        "row_count": row_count,
        "code_count": len(global_codes),
        "fetched_dates": sorted(dates),
        "duplicate_date_code_count": duplicate_date_code_count,
        "raw_schema_status": "OK" if not schema_errors else "ERROR",
        "raw_schema_errors": schema_errors,
    }


def _load_request_manifests(manifest_dir: Path) -> dict[str, dict[str, Any]]:
    if not manifest_dir.is_dir():
        return {}
    manifests: dict[str, dict[str, Any]] = {}
    for path in manifest_dir.glob("*.json"):
        manifest = _read_json_optional(path)
        manifests[path.stem] = manifest
    return manifests


def _date_in_corrected_artifact(target_date: str, artifact: dict[str, Any]) -> bool:
    requests = artifact.get("requests") if isinstance(artifact.get("requests"), list) else []
    if not requests:
        return target_date >= "2021-06-01"
    return target_date in {str(request.get("params", {}).get("date") or request.get("date") or "") for request in requests}


def _manifest_consistency_status(
    *,
    ay_requests: dict[str, Any],
    request_manifests: dict[str, dict[str, Any]],
    response_files: list[Path],
    succeeded_count: int,
    skipped_count: int,
    failed_count: int,
) -> str:
    requests = ay_requests.get("requests") if isinstance(ay_requests.get("requests"), list) else []
    request_dates = {str(request.get("params", {}).get("date") or request.get("date") or "") for request in requests}
    manifest_dates = {date for date in request_manifests if date in request_dates}
    if requests and len(manifest_dates) != len(request_dates):
        return "ERROR"
    manifest_success = sum(1 for date, manifest in request_manifests.items() if date in request_dates and manifest.get("status") == "SUCCESS")
    manifest_failed = sum(1 for date, manifest in request_manifests.items() if date in request_dates and manifest.get("status") == "FAILED")
    if manifest_success != succeeded_count + skipped_count:
        return "ERROR"
    if manifest_failed != failed_count:
        return "ERROR"
    response_dates = {_date_from_response_path(path) for path in response_files}
    response_dates.discard("")
    if not response_dates.issubset(manifest_dates):
        return "ERROR"
    return "OK"


def _date_from_response_path(path: Path) -> str:
    return path.name.split("_page_", 1)[0] if "_page_" in path.name else ""


def _nth_business_date(dates: list[str], lookback: int) -> str | None:
    if len(dates) <= lookback:
        return None
    return dates[lookback]


def _last_label_target_date(dates: list[str], horizon: int) -> str | None:
    if len(dates) <= horizon:
        return None
    return dates[-(horizon + 1)]


def _split_counts(*, fetched_dates: list[str], first_trainable: str | None, last_label: str | None, av_summary: dict[str, Any]) -> dict[str, Any]:
    train_start = str(av_summary.get("train_split_start") or "2021-06-01")
    train_end = str(av_summary.get("train_split_end") or "2024-12-31")
    validation_start = str(av_summary.get("validation_split_start") or "2025-01-01")
    validation_end = str(av_summary.get("validation_split_end") or "2025-12-31")
    test_start = str(av_summary.get("test_split_start") or "2026-01-01")
    test_end = str(av_summary.get("test_split_end") or "2026-05-15")
    eligible_dates = [day for day in fetched_dates if (not first_trainable or day >= first_trainable) and (not last_label or day <= last_label)]
    return {
        "train_split_start_effective": max(train_start, first_trainable) if first_trainable else None,
        "train_split_end": train_end,
        "validation_split_start": validation_start,
        "validation_split_end": validation_end,
        "test_split_start": test_start,
        "test_split_end_effective": min(test_end, last_label) if last_label else None,
        "train_target_date_count_estimate": _count_between(eligible_dates, train_start, train_end),
        "validation_target_date_count_estimate": _count_between(eligible_dates, validation_start, validation_end),
        "test_target_date_count_estimate": _count_between(eligible_dates, test_start, test_end),
    }


def _count_between(values: list[str], start: str, end: str) -> int:
    return sum(1 for value in values if start <= value <= end)


def _readiness_status(
    *,
    secret_value_detected: bool,
    raw_schema_status: str,
    manifest_consistency_status: str,
    non_boundary_failed_dates: list[str],
    formal_training_coverage_sufficient: bool,
) -> str:
    if secret_value_detected:
        return BLOCKED_SECRET
    if raw_schema_status != "OK":
        return BLOCKED_SCHEMA
    if manifest_consistency_status != "OK":
        return BLOCKED_MANIFEST
    if non_boundary_failed_dates:
        return BLOCKED_NON_BOUNDARY
    if not formal_training_coverage_sufficient:
        return BLOCKED_COVERAGE
    return READY


def _recommended_next_action(readiness_status: str) -> str:
    if readiness_status == READY:
        return "Proceed to Phase4-BB Long History Normalized Rebuild using isolated real_runtime normalized output paths."
    if readiness_status == BLOCKED_NON_BOUNDARY:
        return "Resume or inspect non-boundary failed raw requests before normalization."
    if readiness_status == BLOCKED_COVERAGE:
        return "Extend raw coverage or adjust training range before normalized rebuild."
    return "Fix raw integrity or safety blocker before normalized rebuild."


def _secret_detected(payloads: list[Any]) -> bool:
    text = json.dumps(payloads, ensure_ascii=False, sort_keys=True).lower()
    forbidden = ("jquants_api_key", "authorization", "x-api-key", "refresh token", "id token", "password", "cookie", "bearer")
    return any(term in text for term in forbidden)


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-BA Long History Raw Coverage Audit",
        "",
        f"- status: `{summary.get('status')}`",
        f"- readiness_status: `{summary.get('readiness_status')}`",
        f"- fetched date range: `{summary.get('fetched_date_min')}` to `{summary.get('fetched_date_max')}`",
        f"- fetched_business_day_count: `{summary.get('fetched_business_day_count')}`",
        f"- row/code count: `{summary.get('row_count')}` / `{summary.get('code_count')}`",
        f"- raw_response_file_count: `{summary.get('raw_response_file_count')}`",
        f"- request_manifest_count: `{summary.get('request_manifest_count')}`",
        f"- failed dates: `{summary.get('failed_dates')}`",
        f"- boundary_failed_dates: `{summary.get('boundary_failed_dates')}`",
        f"- non_boundary_failed_dates: `{summary.get('non_boundary_failed_dates')}`",
        f"- first_trainable_target_date: `{summary.get('first_trainable_target_date')}`",
        f"- last_label_target_date: `{summary.get('last_label_target_date')}`",
        f"- formal_training_coverage_sufficient: `{summary.get('formal_training_coverage_sufficient')}`",
        "",
        "## Boundary Failure Policy",
        "",
        str(summary.get("boundary_failure_policy") or ""),
        "",
        "## Split Coverage",
        "",
        f"- train_target_date_count_estimate: `{summary.get('train_target_date_count_estimate')}`",
        f"- validation_target_date_count_estimate: `{summary.get('validation_target_date_count_estimate')}`",
        f"- test_target_date_count_estimate: `{summary.get('test_target_date_count_estimate')}`",
        "",
        "## Safety",
        "",
        f"- secret_value_detected: `{summary.get('secret_value_detected')}`",
        "- api/fetch/normalized/feature/label/dataset/training/inference/backtest/trading: `False`",
        "",
        "## Recommended Next Action",
        "",
        str(summary.get("recommended_next_action") or ""),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
