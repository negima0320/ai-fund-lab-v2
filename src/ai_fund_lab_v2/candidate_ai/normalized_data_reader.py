from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.candidate_ai.data_loader import (
    CandidateLoaderValidationResult,
    CandidateRealDataLoaderAudit,
    CandidateRealDataLoaderResult,
    LOADER_SCHEMA_VERSION,
    LOADER_VERSION,
    adapt_daily_quotes_normalized,
)
from ai_fund_lab_v2.candidate_ai.loader_manifest import write_candidate_loader_contract_outputs
from ai_fund_lab_v2.candidate_ai.trading_calendar_window import TradingCalendarWindow, build_trading_calendar_window
from ai_fund_lab_v2.data_quality.normalization import DAILY_QUOTES_NORMALIZED_COLLECTION
from ai_fund_lab_v2.data_store import StorageBackendError, create_storage_backend
from ai_fund_lab_v2.runtime import RuntimePaths


@dataclass(frozen=True)
class NormalizedDataDiscovery:
    status: str
    storage_format: str | None
    path: Path | None
    candidates: tuple[Path, ...]
    message: str


@dataclass(frozen=True)
class RealNormalizedDryRunResult:
    status: str
    requested_as_of_date: str | None
    normalized_as_of_date: str | None
    window_start_date: str | None
    input_row_count: int
    filtered_row_count: int
    dropped_future_row_count: int
    code_count: int
    storage_format: str | None
    input_path: str | None
    manifest_path: str | None
    audit_path: str | None
    rows_path: str | None
    calendar_source: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "requested_as_of_date": self.requested_as_of_date,
            "normalized_as_of_date": self.normalized_as_of_date,
            "window_start_date": self.window_start_date,
            "input_row_count": self.input_row_count,
            "filtered_row_count": self.filtered_row_count,
            "dropped_future_row_count": self.dropped_future_row_count,
            "code_count": self.code_count,
            "storage_format": self.storage_format,
            "input_path": self.input_path,
            "manifest_path": self.manifest_path,
            "audit_path": self.audit_path,
            "rows_path": self.rows_path,
            "calendar_source": self.calendar_source,
            "message": self.message,
        }


def discover_daily_quotes_normalized(
    runtime_dir: Path | str = ".runtime",
    *,
    input_format: str = "auto",
) -> NormalizedDataDiscovery:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    base_path = paths.raw_normalized_data / DAILY_QUOTES_NORMALIZED_COLLECTION / "data"
    formats = ("parquet", "jsonl") if input_format == "auto" else (input_format,)
    candidates: list[Path] = []
    for storage_format in formats:
        backend = create_storage_backend(storage_format)
        path = backend.path_for(base_path)
        candidates.append(path)
        if path.exists():
            return NormalizedDataDiscovery(
                status="FOUND",
                storage_format=storage_format,
                path=path,
                candidates=tuple(candidates),
                message=f"found daily_quotes_normalized {storage_format}",
            )
    return NormalizedDataDiscovery(
        status="MISSING",
        storage_format=None,
        path=None,
        candidates=tuple(candidates),
        message="daily_quotes_normalized data not found under runtime raw_normalized path",
    )


def read_daily_quotes_normalized_small_range(
    runtime_dir: Path | str = ".runtime",
    *,
    as_of_date: str | None = None,
    lookback_business_days: int = 60,
    max_codes: int = 10,
    max_rows: int = 1000,
    input_format: str = "auto",
) -> RealNormalizedDryRunResult:
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format=input_format)
    if discovery.status != "FOUND" or discovery.path is None or discovery.storage_format is None:
        return _skipped_result(as_of_date=as_of_date, discovery=discovery, runtime_dir=runtime_dir)
    try:
        backend = create_storage_backend(discovery.storage_format)
        records = backend.read_records(discovery.path)
    except (StorageBackendError, ImportError, RuntimeError) as exc:
        return _skipped_result(
            as_of_date=as_of_date,
            discovery=discovery,
            runtime_dir=runtime_dir,
            message=f"could not read normalized data: {type(exc).__name__}",
        )
    if not records:
        return _skipped_result(
            as_of_date=as_of_date,
            discovery=discovery,
            runtime_dir=runtime_dir,
            message="daily_quotes_normalized data is empty",
        )

    requested_as_of_date = as_of_date or _latest_date(records)
    calendar_records = _read_trading_calendar_records(runtime_dir)
    window = build_trading_calendar_window(
        as_of_date=requested_as_of_date,
        lookback_business_days=lookback_business_days,
        calendar_records=calendar_records,
    )
    source_records = _select_small_range_source_records(
        records,
        window=window,
        max_codes=max_codes,
        max_rows=max_rows,
    )
    loader_result = adapt_daily_quotes_normalized(
        source_records,
        as_of_date=window.normalized_as_of_date,
        lookback_rows=lookback_business_days,
        input_source_path=discovery.path,
        input_manifest_path=_latest_manifest_path(runtime_dir),
    )
    paths = write_candidate_loader_contract_outputs(loader_result.rows, audit=loader_result.audit, runtime_dir=runtime_dir)
    status = "OK" if loader_result.audit.status in {"OK", "WARNING"} and loader_result.rows else "SKIPPED"
    return RealNormalizedDryRunResult(
        status=status,
        requested_as_of_date=requested_as_of_date,
        normalized_as_of_date=window.normalized_as_of_date,
        window_start_date=window.window_start_date,
        input_row_count=loader_result.audit.input_row_count,
        filtered_row_count=loader_result.audit.filtered_row_count,
        dropped_future_row_count=loader_result.audit.dropped_future_row_count,
        code_count=len({str(row["code"]) for row in loader_result.rows}),
        storage_format=discovery.storage_format,
        input_path=str(discovery.path),
        manifest_path=str(paths["manifest"]),
        audit_path=str(paths["audit"]),
        rows_path=str(paths["rows"]),
        calendar_source=window.source,
        message="real normalized dry-run completed" if status == "OK" else "no rows after small-range filtering",
    )


def write_dry_run_summary(result: RealNormalizedDryRunResult, report_dir: Path | str = "reports/candidate_ai") -> Path:
    path = Path(report_dir) / "phase4g_real_normalized_dry_run_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _select_small_range_source_records(
    records: list[dict[str, Any]],
    *,
    window: TradingCalendarWindow,
    max_codes: int,
    max_rows: int,
) -> list[dict[str, Any]]:
    visible_window_records = [
        record
        for record in records
        if window.window_start_date <= str(record.get("Date") or "") <= window.normalized_as_of_date
    ]
    selected_codes = sorted({str(record.get("Code")) for record in visible_window_records if record.get("Code")})[:max_codes]
    if not selected_codes:
        return []
    selected = [
        record
        for record in records
        if str(record.get("Code")) in selected_codes
        and (str(record.get("Date") or "") >= window.window_start_date or str(record.get("Date") or "") > window.normalized_as_of_date)
    ]
    return sorted(selected, key=lambda item: (str(item.get("Code")), str(item.get("Date"))))[:max_rows]


def _read_trading_calendar_records(runtime_dir: Path | str) -> list[dict[str, Any]]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    base_path = paths.raw_data / "jquants" / "trading_calendar" / "data"
    for storage_format in ("parquet", "jsonl"):
        backend = create_storage_backend(storage_format)
        path = backend.path_for(base_path)
        if not path.exists():
            continue
        try:
            return backend.read_records(path)
        except (StorageBackendError, ImportError, RuntimeError):
            continue
    return []


def _latest_date(records: list[dict[str, Any]]) -> str:
    dates = sorted(str(record.get("Date")) for record in records if record.get("Date"))
    return dates[-1] if dates else "1970-01-01"


def _latest_manifest_path(runtime_dir: Path | str) -> str | None:
    path = RuntimePaths(runtime_dir=Path(runtime_dir)).raw_data / "jquants" / "manifest.jsonl"
    return str(path) if path.exists() else None


def _skipped_result(
    *,
    as_of_date: str | None,
    discovery: NormalizedDataDiscovery,
    runtime_dir: Path | str,
    message: str | None = None,
) -> RealNormalizedDryRunResult:
    audit = CandidateRealDataLoaderAudit(
        status="SKIPPED",
        as_of_date=as_of_date or "",
        source_snapshot_id="daily_quotes_normalized:skipped",
        input_source_path=str(discovery.path) if discovery.path is not None else None,
        input_manifest_path=_latest_manifest_path(runtime_dir),
        input_row_count=0,
        filtered_row_count=0,
        dropped_future_row_count=0,
        invalid_row_count=0,
        input_hash_optional=None,
        schema_version=LOADER_SCHEMA_VERSION,
        loader_version=LOADER_VERSION,
        validation=CandidateLoaderValidationResult(is_valid=False, messages=(message or discovery.message,)),
        messages=(message or discovery.message,),
    )
    paths = write_candidate_loader_contract_outputs([], audit=audit, runtime_dir=runtime_dir)
    return RealNormalizedDryRunResult(
        status="SKIPPED",
        requested_as_of_date=as_of_date,
        normalized_as_of_date=None,
        window_start_date=None,
        input_row_count=0,
        filtered_row_count=0,
        dropped_future_row_count=0,
        code_count=0,
        storage_format=discovery.storage_format,
        input_path=str(discovery.path) if discovery.path else None,
        manifest_path=str(paths["manifest"]),
        audit_path=str(paths["audit"]),
        rows_path=str(paths["rows"]),
        calendar_source=None,
        message=message or discovery.message,
    )
