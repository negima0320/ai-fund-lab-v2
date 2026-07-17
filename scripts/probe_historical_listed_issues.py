#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_sources.jquants import ENDPOINT_PATHS, JQuantsClient, JQuantsClientError, JQuantsRawIngestor
from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import raw_output_path
from ai_fund_lab_v2.data_store import MarketDataStore, create_storage_backend
from ai_fund_lab_v2.data_store.manifest import manifest_path, read_manifest, sanitize_request_params
from ai_fund_lab_v2.runtime import RuntimePaths

DEFAULT_PROBE_DATES = ("2021-01-04", "2021-06-15", "2026-06-29", "2026-07-06")
OPTIONAL_NON_BUSINESS_DATE = "2026-06-28"
DEFAULT_PROBE_ROOT = Path(".runtime/operations/jquants/probes/historical_listed_issues")
ENDPOINT_NAME = "listed_issues"
ENDPOINT = ENDPOINT_PATHS[ENDPOINT_NAME]
RUNTIME_ERROR_CLASSIFICATION = "PROBE_RUNTIME_ERROR"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dates = list(args.dates)
    if args.include_non_business_probe and OPTIONAL_NON_BUSINESS_DATE not in dates:
        dates.append(OPTIONAL_NON_BUSINESS_DATE)

    if args.dry_run:
        print(json.dumps(build_dry_run_plan(args, dates), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    settings = load_settings()
    settings.jquants.require_api_key()
    args.probe_root.mkdir(parents=True, exist_ok=True)

    results = []
    for target_date in dates:
        results.append(run_probe_for_date(args, settings, target_date))

    runtime_error_count = sum(1 for result in results if result.get("classification") == RUNTIME_ERROR_CLASSIFICATION)
    summary = {
        "generated_at": now_utc(),
        "endpoint_name": ENDPOINT_NAME,
        "endpoint": ENDPOINT,
        "probe_root": str(args.probe_root),
        "dates": dates,
        "results": results,
        "runtime_error_count": runtime_error_count,
        "overall_status": "FAILED_RUNTIME_ERROR" if runtime_error_count else "COMPLETED_WITH_CLASSIFICATIONS",
    }
    write_json(args.probe_root / "probe_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if runtime_error_count else 0


def run_probe_for_date(args: argparse.Namespace, settings: Any, target_date: str) -> dict[str, Any]:
    date_root = args.probe_root / target_date
    runtime_paths = RuntimePaths(runtime_dir=date_root)
    runtime_paths.ensure_base_dirs()
    store = MarketDataStore(runtime_paths, raw_storage_format=args.storage_format)
    client = JQuantsClient(settings=settings.jquants, paths=runtime_paths)
    ingestor = JQuantsRawIngestor(client=client, store=store, paths=runtime_paths)

    try:
        fetch_result = ingestor.fetch_and_store(ENDPOINT_NAME, date=target_date, max_pages=args.max_pages)
        data_path = Path(fetch_result.output_path)
        storage_format = resolve_storage_format_authority(
            date_root=date_root,
            requested_storage_format=args.storage_format,
            data_path=data_path,
        )
        records = create_storage_backend(storage_format).read_records(data_path)
        probe_result = build_probe_result(
            date_root=date_root,
            target_date=target_date,
            max_pages=args.max_pages,
            storage_format=storage_format,
            fetch_result=fetch_result,
            records=records,
            data_path=data_path,
            error=None,
        )
    except JQuantsClientError as exc:
        probe_result = build_error_result(
            date_root=date_root,
            target_date=target_date,
            max_pages=args.max_pages,
            storage_format=args.storage_format,
            error_class=str(exc.diagnostic.get("error_class") or "UNKNOWN_API_ERROR"),
            diagnostic=sanitize_diagnostic(exc.diagnostic),
            message=str(exc),
        )
    except Exception as exc:
        probe_result = build_runtime_error_result(
            date_root=date_root,
            target_date=target_date,
            max_pages=args.max_pages,
            storage_format=args.storage_format,
            message=f"{exc.__class__.__name__}: {exc}",
        )

    write_json(date_root / "probe_result.json", probe_result)
    return probe_result


def resolve_storage_format_authority(*, date_root: Path, requested_storage_format: str, data_path: Path) -> str:
    entries = read_manifest(manifest_path(date_root / "data" / "raw"))
    latest = entries[-1] if entries else {}
    manifest_format = str(latest.get("storage_format") or "")
    manifest_path_value = str(latest.get("storage_path") or "")
    if manifest_format:
        if manifest_format != requested_storage_format:
            raise RuntimeError(
                "probe storage format mismatch: "
                f"requested={requested_storage_format} manifest={manifest_format}"
            )
        if manifest_path_value and Path(manifest_path_value) != data_path:
            raise RuntimeError(
                "probe storage path mismatch: "
                f"fetch_result={data_path} manifest={manifest_path_value}"
            )
        return manifest_format
    suffix_format = data_path.suffix.lstrip(".")
    if suffix_format and suffix_format != requested_storage_format:
        raise RuntimeError(
            "probe storage suffix mismatch: "
            f"requested={requested_storage_format} suffix={suffix_format}"
        )
    return requested_storage_format


def build_probe_result(
    *,
    date_root: Path,
    target_date: str,
    max_pages: int,
    storage_format: str,
    fetch_result: Any,
    records: list[dict[str, Any]],
    data_path: Path,
    error: dict[str, Any] | None,
) -> dict[str, Any]:
    response_dates = sorted({str(record.get("Date")) for record in records if record.get("Date") not in (None, "")})
    pagination_pages = sorted(
        {
            int(record.get("pagination_page"))
            for record in records
            if str(record.get("pagination_page") or "").isdigit()
        }
    )
    schema = schema_fingerprint(records)
    classification = classify_success(
        request_date=target_date,
        record_count=len(records),
        response_dates=response_dates,
        validation_status=fetch_result.validation_status,
    )
    return {
        "generated_at": now_utc(),
        "classification": classification,
        "endpoint_name": ENDPOINT_NAME,
        "endpoint": ENDPOINT,
        "request_date": target_date,
        "target_date": target_date,
        "fetched_at": latest_manifest_fetched_at(date_root),
        "snapshot_date_semantics": {
            "request_date": "API request parameter date",
            "response_Date": "J-Quants equities master snapshot effective date, not listing date",
            "target_date": "Runtime raw-store target date used for this probe",
            "fetched_at": "UTC time when the provider response was saved locally",
            "snapshot_date": "response Date when present",
            "provider_effective_date": "response Date when present; may differ from request date if provider normalizes",
        },
        "max_pages": max_pages,
        "pagination_pages": pagination_pages,
        "pagination_page_count": len(pagination_pages),
        "row_count": len(records),
        "response_date_min": response_dates[0] if response_dates else "",
        "response_date_max": response_dates[-1] if response_dates else "",
        "response_date_unique": response_dates,
        "source_hash_sha256": sha256_file(data_path),
        "schema_hash_sha256": schema["schema_hash_sha256"],
        "schema_columns": schema["columns"],
        "schema_types": schema["types"],
        "storage_format": storage_format,
        "storage_path": str(data_path),
        "manifest_path": str(manifest_path(date_root / "data" / "raw")),
        "validation_status": fetch_result.validation_status,
        "records_saved": fetch_result.records_saved,
        "diff_summary": fetch_result.diff_summary,
        "error": error,
    }


def build_error_result(
    *,
    date_root: Path,
    target_date: str,
    max_pages: int,
    storage_format: str,
    error_class: str,
    diagnostic: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    return {
        "generated_at": now_utc(),
        "classification": classify_error(error_class, diagnostic),
        "endpoint_name": ENDPOINT_NAME,
        "endpoint": ENDPOINT,
        "request_date": target_date,
        "target_date": target_date,
        "fetched_at": "",
        "max_pages": max_pages,
        "pagination_pages": [],
        "pagination_page_count": 0,
        "row_count": 0,
        "response_date_min": "",
        "response_date_max": "",
        "response_date_unique": [],
        "source_hash_sha256": "",
        "schema_hash_sha256": "",
        "schema_columns": [],
        "schema_types": {},
        "storage_format": "",
        "storage_path": raw_output_path(RuntimePaths(runtime_dir=date_root), ENDPOINT_NAME, storage_format),
        "manifest_path": str(manifest_path(date_root / "data" / "raw")),
        "validation_status": "ERROR",
        "records_saved": 0,
        "diff_summary": {},
        "error": {
            "message": message,
            "diagnostic": diagnostic,
        },
    }


def sanitize_diagnostic(diagnostic: dict[str, Any]) -> dict[str, Any]:
    sanitized = sanitize_request_params(diagnostic)
    for key in list(sanitized):
        if key.lower() in {"secret", "client_secret"}:
            sanitized.pop(key, None)
    return sanitized


def build_runtime_error_result(
    *,
    date_root: Path,
    target_date: str,
    max_pages: int,
    storage_format: str,
    message: str,
) -> dict[str, Any]:
    return {
        "generated_at": now_utc(),
        "classification": RUNTIME_ERROR_CLASSIFICATION,
        "endpoint_name": ENDPOINT_NAME,
        "endpoint": ENDPOINT,
        "request_date": target_date,
        "target_date": target_date,
        "fetched_at": latest_manifest_fetched_at(date_root),
        "max_pages": max_pages,
        "pagination_pages": [],
        "pagination_page_count": 0,
        "row_count": 0,
        "response_date_min": "",
        "response_date_max": "",
        "response_date_unique": [],
        "source_hash_sha256": "",
        "schema_hash_sha256": "",
        "schema_columns": [],
        "schema_types": {},
        "storage_format": storage_format,
        "storage_path": raw_output_path(RuntimePaths(runtime_dir=date_root), ENDPOINT_NAME, storage_format),
        "manifest_path": str(manifest_path(date_root / "data" / "raw")),
        "validation_status": "ERROR",
        "records_saved": 0,
        "diff_summary": {},
        "error": {
            "message": message,
            "diagnostic": {
                "error_class": RUNTIME_ERROR_CLASSIFICATION,
                "secret_safe": True,
            },
        },
    }


def classify_success(
    *,
    request_date: str,
    record_count: int,
    response_dates: list[str],
    validation_status: str,
) -> str:
    if validation_status == "ERROR":
        return "SCHEMA_MISMATCH"
    if record_count == 0:
        return "NO_DATA_FOR_DATE"
    if response_dates == [request_date]:
        return "FETCH_SUPPORTED_EXACT_DATE"
    if response_dates:
        return "FETCH_SUPPORTED_WITH_PROVIDER_DATE_NORMALIZATION"
    return "AMBIGUOUS"


def classify_error(error_class: str, diagnostic: dict[str, Any]) -> str:
    status = diagnostic.get("http_status")
    if error_class == "API_AUTH_ERROR":
        return "AUTHORIZATION_OR_PLAN_LIMIT"
    if status in (401, 403):
        return "AUTHORIZATION_OR_PLAN_LIMIT"
    if status == 400:
        return "DATE_OUT_OF_RETENTION"
    if error_class:
        return "API_ERROR"
    return "AMBIGUOUS"


def schema_fingerprint(records: list[dict[str, Any]]) -> dict[str, Any]:
    columns = sorted({key for record in records for key in record})
    types: dict[str, list[str]] = {}
    for column in columns:
        values = {type(record.get(column)).__name__ for record in records if record.get(column) is not None}
        types[column] = sorted(values) if values else ["null"]
    payload = {"columns": columns, "types": types}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return {
        "columns": columns,
        "types": types,
        "schema_hash_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_manifest_fetched_at(date_root: Path) -> str:
    entries = read_manifest(manifest_path(date_root / "data" / "raw"))
    if not entries:
        return ""
    return str(entries[-1].get("fetched_at") or "")


def build_dry_run_plan(args: argparse.Namespace, dates: list[str]) -> dict[str, Any]:
    command = [
        "PYTHONPATH=src",
        "python3",
        "scripts/probe_historical_listed_issues.py",
        "--probe-root",
        str(args.probe_root),
        "--storage-format",
        args.storage_format,
        "--max-pages",
        str(args.max_pages),
        "--dates",
        *dates,
    ]
    if args.include_non_business_probe:
        command.append("--include-non-business-probe")
    return {
        "status": "DRY_RUN_ONLY_NO_API_FETCH",
        "endpoint_name": ENDPOINT_NAME,
        "endpoint": ENDPOINT,
        "probe_root": str(args.probe_root),
        "dates": dates,
        "required_env": ["JQUANTS_API_KEY"],
        "optional_env": ["JQUANTS_BASE_URL", "JQUANTS_RATE_LIMIT_PER_MINUTE", "JQUANTS_TIMEOUT_SECONDS"],
        "operator_command": " ".join(command),
        "will_not_call": ["broker_api", "order_submit", "runtime_test", "external_notification"],
        "per_date_output": [
            {
                "date": target_date,
                "runtime_dir": str(args.probe_root / target_date),
                "raw_output": raw_output_path(RuntimePaths(runtime_dir=args.probe_root / target_date), ENDPOINT_NAME, args.storage_format),
                "manifest": str(manifest_path(args.probe_root / target_date / "data" / "raw")),
                "probe_result": str(args.probe_root / target_date / "probe_result.json"),
            }
            for target_date in dates
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Probe J-Quants /v2/equities/master historical-date support using the formal "
            "JQuantsClient and JQuantsRawIngestor. Use --dry-run to print the operator plan without fetching."
        )
    )
    parser.add_argument("--dates", nargs="+", default=list(DEFAULT_PROBE_DATES), help="Probe dates as YYYY-MM-DD.")
    parser.add_argument("--include-non-business-probe", action="store_true", help="Also probe 2026-06-28.")
    parser.add_argument("--probe-root", type=Path, default=DEFAULT_PROBE_ROOT)
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--storage-format", choices=("parquet", "jsonl"), default="parquet")
    parser.add_argument("--dry-run", action="store_true", help="Print the command/evidence plan without API access.")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
