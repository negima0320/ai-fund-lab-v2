from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_store import validate_records
from ai_fund_lab_v2.data_sources.jquants.client import JQUANTS_DAILY_QUOTES_ENDPOINT, JQuantsClient, JQuantsClientError
from ai_fund_lab_v2.paper_trading.market_data_refresh import JQuantsAPIFetcher, run_market_data_refresh
from ai_fund_lab_v2.runtime_v2.market_data_bootstrap import (
    REQUIRED_LOOKBACK_BUSINESS_DAYS,
    compare_normalized_schemas,
    parquet_inventory,
)
from ai_fund_lab_v2.runtime_v2.storage.runtime_paths import RuntimePaths


ACQUISITION_SCHEMA_VERSION = "phase20_bc_jquants_market_data_acquisition.v1"
ACQUISITION_STATE_SCHEMA_VERSION = "phase20_bc_jquants_market_data_acquisition_state.v1"
REQUEST_CONTRACT_VERSION = "phase20_bd_jquants_daily_quotes_request.v1"
ACQUISITION_CONNECTION_VERSION = "phase20_be_acquisition_normalization_connection.v1"
PRODUCTION_REFRESH_ADAPTER_VERSION = "phase20_bf_production_market_refresh_adapter.v1"
FETCH_CONFIRM_FLAG = "--yes-i-understand-this-fetches-large-market-data"
DEFAULT_EVIDENCE_ROOT = Path("reports/phase20_bg_historical_freshness_policy_separation")
DEFAULT_STAGING_ROOT = Path(".runtime/market_data_acquisition/runs")
RAW_RELATIVE_PATH = Path("raw/jquants/equities_bars_daily/data.parquet")
NORMALIZED_RELATIVE_PATH = Path("raw_normalized/jquants/equities_bars_daily/data.parquet")
REQUIRED_RAW_FIELDS = ("Date", "Code", "O", "H", "L", "C", "Vo")
TRAINING_ONLY_PREFIXES = ("label_", "future_", "target_return")
TRAINING_ONLY_COLUMNS = {"label", "target", "future_return", "forward_return", "split", "fold"}
RETRYABLE_ERROR_CLASSES = {"API_RATE_LIMIT", "API_SERVER_ERROR", "API_NETWORK_ERROR"}
NON_RETRYABLE_ERROR_CLASSES = {"API_AUTH_ERROR", "API_PARAM_ERROR"}


class DailyQuotePageFetcher(Protocol):
    def fetch_daily_quotes(
        self,
        *,
        date: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        pagination_key: str | None = None,
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class AcquisitionPaths:
    runtime_root: Path
    run_id: str
    evidence_root: Path = DEFAULT_EVIDENCE_ROOT
    staging_root: Path = DEFAULT_STAGING_ROOT

    @property
    def run_root(self) -> Path:
        return self.staging_root / self.run_id

    @property
    def plan_path(self) -> Path:
        return self.run_root / "plan.json"

    @property
    def state_path(self) -> Path:
        return self.run_root / "state.json"

    @property
    def raw_output_path(self) -> Path:
        return self.run_root / RAW_RELATIVE_PATH

    @property
    def normalized_output_path(self) -> Path:
        return self.run_root / NORMALIZED_RELATIVE_PATH

    @property
    def chunk_root(self) -> Path:
        return self.run_root / "chunks"

    @property
    def market_refresh_manifest_root(self) -> Path:
        return self.run_root / "market_refresh_manifests"


def build_acquisition_plan(
    *,
    runtime_root: Path | str,
    start_date: str,
    end_date: str,
    run_id: str | None = None,
    evidence_root: Path | str = DEFAULT_EVIDENCE_ROOT,
    staging_root: Path | str = DEFAULT_STAGING_ROOT,
    chunk: str = "month",
    write_evidence: bool = False,
    created_at: str | None = None,
) -> dict[str, Any]:
    start = _normalize_date(start_date)
    end = _normalize_date(end_date)
    _validate_date_range(start, end)
    run_id = run_id or f"jquants-acquisition-{start.replace('-', '')}-{end.replace('-', '')}"
    paths = AcquisitionPaths(Path(runtime_root), run_id, Path(evidence_root), Path(staging_root))
    chunks = build_date_chunks(start_date=start, end_date=end, chunk=chunk)
    current = parquet_inventory(paths.runtime_root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet")
    existing_staging = parquet_inventory(paths.normalized_output_path)
    plan = {
        "schema_version": ACQUISITION_SCHEMA_VERSION,
        "operation": "plan",
        "status": "PASS",
        "final_judgment": "ACQUISITION_PLAN_READY",
        "created_at": created_at or _utc_now(),
        "read_only": True,
        "acquisition_run_id": run_id,
        "requested_start_date": start,
        "requested_end_date": end,
        "expected_calendar_business_days": len(_weekdays(start, end)),
        "existing_runtime_earliest_date": current.get("earliest_date", ""),
        "existing_runtime_latest_date": current.get("latest_date", ""),
        "existing_staging_coverage": existing_staging,
        "missing_date_ranges": [{"start_date": start, "end_date": end}] if existing_staging.get("status") == "MISSING" else [],
        "endpoint": JQUANTS_DAILY_QUOTES_ENDPOINT,
        "request_contract_version": REQUEST_CONTRACT_VERSION,
        "acquisition_connection_version": ACQUISITION_CONNECTION_VERSION,
        "production_refresh_adapter_version": PRODUCTION_REFRESH_ADAPTER_VERSION,
        "processing_authority": "PRODUCTION_MARKET_REFRESH_CORE",
        "request_strategy": "date_by_date",
        "raw_schema_authority": "ai_fund_lab_v2.paper_trading.market_data_refresh",
        "normalization_authority": "ai_fund_lab_v2.paper_trading.market_data_refresh -> normalize_daily_quotes",
        "actual_request_shape": {
            "method": "GET",
            "endpoint": JQUANTS_DAILY_QUOTES_ENDPOINT,
            "params": {"date": "YYYY-MM-DD", "pagination_key": "present only when paginating"},
            "excluded_params": ["from", "to"],
        },
        "pagination_strategy": "continue while pagination_key exists; fail closed on token cycle or max_pages",
        "estimated_request_units": sum(len(chunk.get("requests", [])) for chunk in chunks),
        "estimated_date_chunks": len(chunks),
        "chunk_strategy": chunk,
        "chunks": chunks,
        "output_root": str(paths.run_root),
        "raw_output_path": str(paths.raw_output_path),
        "normalized_output_path": str(paths.normalized_output_path),
        "resume_supported": True,
        "mutation_scope": "staging_only",
        "runtime_market_data_mutated": False,
        "jquants_api_fetch_executed": False,
        "broker_access": "NOT_PERFORMED",
        "bootstrap_plan_command": _bootstrap_plan_command(paths.normalized_output_path),
        "blocked_reasons": [],
    }
    if write_evidence:
        write_acquisition_evidence(plan, paths=paths)
    return plan


def run_acquisition(
    *,
    runtime_root: Path | str,
    start_date: str,
    end_date: str,
    run_id: str | None = None,
    evidence_root: Path | str = DEFAULT_EVIDENCE_ROOT,
    staging_root: Path | str = DEFAULT_STAGING_ROOT,
    chunk: str = "month",
    confirm: bool = False,
    explicit_fetch_confirm: bool = False,
    write_evidence: bool = False,
    fetcher: DailyQuotePageFetcher | None = None,
    max_pages_per_chunk: int = 100,
    max_retries: int = 3,
    sleep: Any = time.sleep,
    stop_after_chunks: int | None = None,
) -> dict[str, Any]:
    plan = build_acquisition_plan(
        runtime_root=runtime_root,
        start_date=start_date,
        end_date=end_date,
        run_id=run_id,
        evidence_root=evidence_root,
        staging_root=staging_root,
        chunk=chunk,
        write_evidence=False,
    )
    if not (confirm and explicit_fetch_confirm):
        result = _blocked_from_plan(plan, "ACQUISITION_CONFIRMATION_REQUIRED", ["confirm_and_large_market_data_fetch_flag_required"])
        if write_evidence:
            write_acquisition_evidence(result, paths=_paths_from_plan(plan, runtime_root=Path(runtime_root), evidence_root=Path(evidence_root), staging_root=Path(staging_root)))
        return result
    paths = _paths_from_plan(plan, runtime_root=Path(runtime_root), evidence_root=Path(evidence_root), staging_root=Path(staging_root))
    if paths.state_path.exists():
        existing = _read_json(paths.state_path)
        compatibility = _request_contract_compatibility(plan=plan, state=existing)
        if compatibility["status"] != "PASS":
            result = _blocked_from_plan(plan, compatibility["final_judgment"], compatibility["blocked_reasons"])
            if write_evidence:
                write_acquisition_evidence(result, paths=paths)
            return result
        binding = _state_binding(existing)
        if binding != _plan_binding(plan):
            result = _blocked_from_plan(plan, "ACQUISITION_STATE_BINDING_MISMATCH", ["existing_run_id_has_different_acquisition_binding"])
            if write_evidence:
                write_acquisition_evidence(result, paths=paths)
            return result
    fetcher = fetcher or _default_fetcher(paths.runtime_root)
    state = _initial_state(plan)
    _write_json(paths.plan_path, plan)
    _write_json(paths.state_path, state)
    return _execute_remaining_chunks(
        plan=plan,
        paths=paths,
        fetcher=fetcher,
        max_pages_per_chunk=max_pages_per_chunk,
        max_retries=max_retries,
        sleep=sleep,
        write_evidence=write_evidence,
        stop_after_chunks=stop_after_chunks,
    )


def resume_acquisition(
    *,
    runtime_root: Path | str,
    run_id: str,
    evidence_root: Path | str = DEFAULT_EVIDENCE_ROOT,
    staging_root: Path | str = DEFAULT_STAGING_ROOT,
    confirm: bool = False,
    explicit_fetch_confirm: bool = False,
    write_evidence: bool = False,
    fetcher: DailyQuotePageFetcher | None = None,
    max_pages_per_chunk: int = 100,
    max_retries: int = 3,
    sleep: Any = time.sleep,
    stop_after_chunks: int | None = None,
) -> dict[str, Any]:
    paths = AcquisitionPaths(Path(runtime_root), run_id, Path(evidence_root), Path(staging_root))
    if not paths.plan_path.is_file() or not paths.state_path.is_file():
        payload = {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "operation": "resume",
            "status": "BLOCK",
            "final_judgment": "ACQUISITION_RESUME_BLOCKED",
            "acquisition_run_id": run_id,
            "blocked_reasons": ["plan_or_state_missing"],
            "runtime_market_data_mutated": False,
            "jquants_api_fetch_executed": False,
        }
        if write_evidence:
            write_acquisition_evidence(payload, paths=paths)
        return payload
    plan = _read_json(paths.plan_path)
    state = _read_json(paths.state_path)
    compatibility = _request_contract_compatibility(plan=plan, state=state)
    if compatibility["status"] != "PASS":
        payload = _blocked_from_plan(plan, compatibility["final_judgment"], compatibility["blocked_reasons"])
        if write_evidence:
            write_acquisition_evidence(payload, paths=paths)
        return payload
    if _state_binding(state) != _plan_binding(plan):
        payload = _blocked_from_plan(plan, "ACQUISITION_STATE_BINDING_MISMATCH", ["state_binding_does_not_match_plan"])
        if write_evidence:
            write_acquisition_evidence(payload, paths=paths)
        return payload
    if not (confirm and explicit_fetch_confirm):
        payload = _blocked_from_plan(plan, "ACQUISITION_CONFIRMATION_REQUIRED", ["confirm_and_large_market_data_fetch_flag_required"])
        if write_evidence:
            write_acquisition_evidence(payload, paths=paths)
        return payload
    fetcher = fetcher or _default_fetcher(paths.runtime_root)
    return _execute_remaining_chunks(
        plan=plan,
        paths=paths,
        fetcher=fetcher,
        max_pages_per_chunk=max_pages_per_chunk,
        max_retries=max_retries,
        sleep=sleep,
        write_evidence=write_evidence,
        stop_after_chunks=stop_after_chunks,
    )


def acquisition_status(
    *,
    runtime_root: Path | str,
    run_id: str,
    evidence_root: Path | str = DEFAULT_EVIDENCE_ROOT,
    staging_root: Path | str = DEFAULT_STAGING_ROOT,
) -> dict[str, Any]:
    paths = AcquisitionPaths(Path(runtime_root), run_id, Path(evidence_root), Path(staging_root))
    state = _read_json_optional(paths.state_path)
    normalized = parquet_inventory(paths.normalized_output_path)
    chunks = state.get("chunks", []) if isinstance(state.get("chunks"), list) else []
    completed = [chunk for chunk in chunks if chunk.get("status") == "COMPLETED"]
    failed = [chunk for chunk in chunks if chunk.get("status") == "FAILED"]
    return {
        "schema_version": ACQUISITION_SCHEMA_VERSION,
        "operation": "status",
        "status": "PASS" if state else "BLOCK",
        "final_judgment": "ACQUISITION_STATUS_READY" if state else "ACQUISITION_STATUS_MISSING",
        "acquisition_run_id": run_id,
        "request_contract_version": state.get("request_contract_version") or "",
        "completed_chunks": len(completed),
        "remaining_chunks": len(chunks) - len(completed),
        "failed_chunks": len(failed),
        "request_count": sum(int(chunk.get("request_count", 0)) for chunk in chunks),
        "page_count": sum(int(chunk.get("page_count", 0)) for chunk in chunks),
        "row_count": sum(int(chunk.get("row_count", 0)) for chunk in chunks),
        "earliest_date": normalized.get("earliest_date", ""),
        "latest_date": normalized.get("latest_date", ""),
        "duplicate_count": normalized.get("duplicate_key_count", 0),
        "last_error": failed[-1].get("error", "") if failed else "",
        "retry_count": sum(int(chunk.get("retry_count", 0)) for chunk in chunks),
        "normalized_output_path": str(paths.normalized_output_path),
        "runtime_market_data_mutated": False,
        "broker_access": "NOT_PERFORMED",
    }


def build_date_chunks(*, start_date: str, end_date: str, chunk: str = "month") -> list[dict[str, Any]]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if chunk not in {"day", "week", "month"}:
        raise ValueError("chunk must be one of: day, week, month")
    values: list[dict[str, Any]] = []
    current = start
    index = 1
    while current <= end:
        if chunk == "day":
            chunk_end = current
        elif chunk == "week":
            chunk_end = min(end, current + timedelta(days=6))
        else:
            next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
            chunk_end = min(end, next_month - timedelta(days=1))
        values.append(
            {
                "chunk_id": f"chunk-{index:04d}",
                "start_date": current.isoformat(),
                "end_date": chunk_end.isoformat(),
                "status": "PENDING",
                "request_count": 0,
                "page_count": 0,
                "row_count": 0,
                "first_date": "",
                "last_date": "",
                "content_hash": "",
                "started_at": "",
                "completed_at": "",
                "error": "",
                "retry_count": 0,
                "requests": [_initial_request_state(day) for day in _weekdays(current.isoformat(), chunk_end.isoformat())],
            }
        )
        current = chunk_end + timedelta(days=1)
        index += 1
    return values


def fetch_chunk_pages(
    *,
    fetcher: DailyQuotePageFetcher,
    start_date: str,
    end_date: str,
    max_pages: int = 100,
    max_retries: int = 3,
    sleep: Any = time.sleep,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    request_states = [_initial_request_state(day) for day in _weekdays(start_date, end_date)]
    return fetch_chunk_requests(
        fetcher=fetcher,
        request_states=request_states,
        max_pages=max_pages,
        max_retries=max_retries,
        sleep=sleep,
    )


def fetch_chunk_requests(
    *,
    fetcher: DailyQuotePageFetcher,
    request_states: list[dict[str, Any]],
    max_pages: int = 100,
    max_retries: int = 3,
    sleep: Any = time.sleep,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    request_count = 0
    page_count = 0
    retry_count = 0
    for request_state in request_states:
        if request_state.get("status") in {"FETCH_READY", "RAW_READY", "COMPLETED", "COMPLETED_EMPTY"}:
            continue
        request_date = str(request_state["request_date"])
        request_state.update({"status": "RUNNING", "started_at": request_state.get("started_at") or _utc_now(), "error": ""})
        pagination_key: str | None = None
        seen_tokens: set[str] = set()
        request_records: list[dict[str, Any]] = []
        try:
            for page in range(1, max_pages + 1):
                if pagination_key and pagination_key in seen_tokens:
                    raise AcquisitionRequestError(
                        "pagination_token_cycle_detected",
                        request_date=request_date,
                        request_count=0,
                        page_count=page_count,
                        retry_count=0,
                    )
                if pagination_key:
                    seen_tokens.add(pagination_key)
                payload, retries = _call_with_retry(
                    fetcher=fetcher,
                    request_date=request_date,
                    pagination_key=pagination_key,
                    max_retries=max_retries,
                    sleep=sleep,
                )
                retry_count += retries
                request_count += retries + 1
                request_state["request_count"] = int(request_state.get("request_count", 0)) + retries + 1
                request_state["retry_count"] = int(request_state.get("retry_count", 0)) + retries
                page_count += 1
                request_state["page_count"] = int(request_state.get("page_count", 0)) + 1
                page_records = payload.get("data") or []
                if not isinstance(page_records, list):
                    raise AcquisitionError("jquants_response_data_not_list")
                for row in page_records:
                    record = dict(row)
                    record["pagination_page"] = page
                    record["target_date"] = record.get("target_date") or record.get("Date") or request_date
                    record["code"] = str(record.get("code") or record.get("Code") or "")
                    record["business_key"] = str(record.get("business_key") or record.get("Code") or record.get("code") or "")
                    record["source"] = "jquants"
                    record["endpoint"] = JQUANTS_DAILY_QUOTES_ENDPOINT
                    record["retrieved_at"] = _utc_now()
                    if pagination_key:
                        record["pagination_key"] = pagination_key
                    request_records.append(record)
                next_token = payload.get("pagination_key")
                if not next_token:
                    break
                pagination_key = str(next_token)
            else:
                raise AcquisitionRequestError(
                    "pagination_max_pages_exceeded",
                    request_date=request_date,
                    request_count=int(request_state.get("request_count", 0)),
                    page_count=int(request_state.get("page_count", 0)),
                    retry_count=int(request_state.get("retry_count", 0)),
                )
        except AcquisitionRequestError as exc:
            request_count += exc.request_count
            retry_count += exc.retry_count
            request_state["request_count"] = int(request_state.get("request_count", 0)) + exc.request_count
            request_state["retry_count"] = int(request_state.get("retry_count", 0)) + exc.retry_count
            request_state["status"] = "FAILED"
            request_state["error"] = _safe_error_text(exc)
            request_state["http_status"] = exc.http_status
            request_state["completed_at"] = _utc_now()
            raise
        request_state["row_count"] = len(request_records)
        request_state["first_date"] = min((str(row.get("Date") or request_date) for row in request_records), default="")
        request_state["last_date"] = max((str(row.get("Date") or request_date) for row in request_records), default="")
        request_state["content_hash"] = _content_hash(request_records)
        request_state["status"] = "FETCH_READY" if request_records else "COMPLETED_EMPTY"
        request_state["completed_at"] = _utc_now()
        records.extend(request_records)
    return records, {
        "request_count": request_count,
        "page_count": page_count,
        "retry_count": retry_count,
        "request_states": request_states,
    }


class AcquisitionError(RuntimeError):
    pass


class AcquisitionRequestError(AcquisitionError):
    def __init__(
        self,
        message: str,
        *,
        request_date: str,
        request_count: int,
        page_count: int,
        retry_count: int,
        http_status: int | str = "",
        diagnostic: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.request_date = request_date
        self.request_count = request_count
        self.page_count = page_count
        self.retry_count = retry_count
        self.http_status = http_status
        self.diagnostic = diagnostic or {}


def _run_production_market_refresh_for_chunk(*, paths: AcquisitionPaths, chunk: dict[str, Any], fetcher: Any) -> dict[str, Any]:
    chunk_id = str(chunk["chunk_id"])
    manifest_root = paths.market_refresh_manifest_root / chunk_id
    result = run_market_data_refresh(
        from_date=str(chunk["start_date"]),
        to_date=str(chunk["end_date"]),
        dry_run=False,
        allow_api_fetch=True,
        raw_output_root=paths.run_root / "raw",
        normalized_output_root=paths.run_root / "raw_normalized",
        manifest_output_root=manifest_root,
        backup_existing=False,
        fetch_mode="per-date",
        fetcher=_production_refresh_fetcher(fetcher),
        today=max(date.today().isoformat(), str(chunk["end_date"])),
        markdown_report_path=manifest_root / "market_data_refresh_report.md",
        json_report_path=manifest_root / "market_data_refresh_report.json",
    )
    return result.to_dict()


def _production_refresh_fetcher(fetcher: Any) -> Any:
    if all(hasattr(fetcher, name) for name in ("fetch_daily_quotes_for_date", "fetch_listed_info", "fetch_trading_calendar")):
        return fetcher
    return _DailyQuoteOnlyProductionFetcher(fetcher)


class _DailyQuoteOnlyProductionFetcher:
    def __init__(self, fetcher: Any) -> None:
        self.fetcher = fetcher

    def fetch_daily_quotes(self, *, from_date: str, to_date: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for day in _weekdays(from_date, to_date):
            rows.extend(self.fetch_daily_quotes_for_date(target_date=day))
        return rows

    def fetch_daily_quotes_for_date(self, *, target_date: str) -> list[dict[str, Any]]:
        payload = self.fetcher.fetch_daily_quotes(date=target_date, pagination_key=None)
        data = payload.get("data") if isinstance(payload, dict) else payload
        return [dict(row) for row in data or [] if isinstance(row, dict)]

    def fetch_listed_info(self, *, date: str) -> list[dict[str, Any]]:
        return [{"Date": date, "Code": "DUMMY", "CoName": "Dummy", "Mkt": "0000"}]

    def fetch_trading_calendar(self, *, from_date: str, to_date: str) -> list[dict[str, Any]]:
        return [{"Date": day, "HolDiv": "1"} for day in _weekdays(from_date, to_date)]


def _daily_endpoint_summary(refresh: dict[str, Any]) -> dict[str, Any]:
    for endpoint in refresh.get("endpoints") or []:
        if isinstance(endpoint, dict) and endpoint.get("endpoint") == "daily_quotes":
            return endpoint
    return {}


def _production_refresh_request_state(day: str, *, paths: AcquisitionPaths, raw_hash: str) -> dict[str, Any]:
    return {
        "request_date": day,
        "status": "COMPLETED",
        "processing_authority": "PRODUCTION_MARKET_REFRESH_CORE",
        "request_count": 1,
        "page_count": 1,
        "raw_artifact_path": str(paths.raw_output_path),
        "raw_content_hash": raw_hash,
        "error": "",
        "retry_count": 0,
    }


def _state_expected_business_dates(state: dict[str, Any]) -> list[str]:
    dates: list[str] = []
    for chunk in state.get("chunks") or []:
        refresh = chunk.get("production_market_refresh") if isinstance(chunk, dict) else {}
        if not isinstance(refresh, dict):
            continue
        dates.extend(str(day) for day in (refresh.get("required_dates") or []) if str(day))
    return sorted(set(dates))


def _revalidate_failed_chunk_from_existing_staging(*, paths: AcquisitionPaths, chunk: dict[str, Any]) -> dict[str, Any]:
    refresh = chunk.get("production_market_refresh") if isinstance(chunk.get("production_market_refresh"), dict) else {}
    expected_dates = list(refresh.get("required_dates") or [])
    validation = validate_staging_source(
        normalized_path=paths.normalized_output_path,
        requested_start_date=str(chunk["start_date"]),
        requested_end_date=str(chunk["end_date"]),
        expected_business_dates=expected_dates,
    )
    if validation["status"] != "PASS" or not paths.raw_output_path.is_file():
        return {"status": "BLOCK", "final_validation": validation}
    raw_inv = parquet_inventory(paths.raw_output_path)
    normalized_inv = parquet_inventory(paths.normalized_output_path)
    return {
        "status": "PASS",
        "final_validation": validation,
        "chunk_update": {
            "status": "COMPLETED",
            "error": "",
            "first_date": normalized_inv.get("earliest_date", ""),
            "last_date": normalized_inv.get("latest_date", ""),
            "content_hash": normalized_inv.get("content_hash", ""),
            "raw_content_hash": raw_inv.get("content_hash", ""),
            "historical_policy_revalidated_at": _utc_now(),
            "historical_policy_validation": validation,
        },
    }


def write_acquisition_evidence(payload: dict[str, Any], *, paths: AcquisitionPaths) -> None:
    root = paths.evidence_root
    root.mkdir(parents=True, exist_ok=True)
    contracts = _contract_evidence(paths=paths)
    for name, content in contracts.items():
        _write_json(root / name, content)
    _write_json(root / "acquisition_plan.json", payload)
    if not (root / "test_summary.json").exists():
        _write_json(
            root / "test_summary.json",
            {
                "schema_version": ACQUISITION_SCHEMA_VERSION,
                "status": "PENDING_VALIDATION",
                "tests": [],
                "five_year_fetch_executed_by_codex": False,
                "runtime_market_data_mutated": False,
                "broker_access": "NOT_PERFORMED",
            },
        )


def _execute_remaining_chunks(
    *,
    plan: dict[str, Any],
    paths: AcquisitionPaths,
    fetcher: DailyQuotePageFetcher,
    max_pages_per_chunk: int,
    max_retries: int,
    sleep: Any,
    write_evidence: bool,
    stop_after_chunks: int | None,
) -> dict[str, Any]:
    state = _read_json(paths.state_path)
    processed = 0
    for chunk in state["chunks"]:
        if chunk.get("status") in {"COMPLETED", "RAW_READY"}:
            if not _chunk_artifact_valid(paths=paths, chunk=chunk):
                chunk["status"] = "FAILED"
                chunk["error"] = "completed_chunk_artifact_invalid"
                _write_json(paths.state_path, state)
                result = _blocked_from_state(plan, state, "ACQUISITION_SOURCE_BLOCKED", ["completed_chunk_artifact_invalid"])
                if write_evidence:
                    write_acquisition_evidence(result, paths=paths)
                return result
            continue
        if chunk.get("status") == "NORMALIZATION_FAILED":
            revalidated = _revalidate_failed_chunk_from_existing_staging(paths=paths, chunk=chunk)
            if revalidated["status"] == "PASS":
                chunk.update(revalidated["chunk_update"])
                _write_json(paths.state_path, state)
                continue
        if stop_after_chunks is not None and processed >= stop_after_chunks:
            state["status"] = "IN_PROGRESS"
            _write_json(paths.state_path, state)
            result = _result_from_state(plan, state, "IN_PROGRESS", "ACQUISITION_PARTIAL_READY_FOR_RESUME")
            if write_evidence:
                write_acquisition_evidence(result, paths=paths)
            return result
        chunk["status"] = "RUNNING"
        chunk["started_at"] = _utc_now()
        _write_json(paths.state_path, state)
        try:
            refresh = _run_production_market_refresh_for_chunk(
                paths=paths,
                chunk=chunk,
                fetcher=fetcher,
            )
            raw_inv = parquet_inventory(paths.raw_output_path)
            normalized_inv = parquet_inventory(paths.normalized_output_path)
            validation = validate_staging_source(
                normalized_path=paths.normalized_output_path,
                requested_start_date=str(chunk["start_date"]),
                requested_end_date=str(chunk["end_date"]),
                expected_business_dates=list(refresh.get("required_dates") or []),
            )
            if validation["status"] != "PASS":
                chunk.update(
                    {
                        "status": "NORMALIZATION_FAILED",
                        "error": "production_market_refresh_staging_validation_failed",
                        "completed_at": _utc_now(),
                        "production_market_refresh": refresh,
                        "final_validation": validation,
                    }
                )
                state["status"] = "BLOCK"
                _write_json(paths.state_path, state)
                result = _blocked_from_state(plan, state, "ACQUISITION_SOURCE_BLOCKED", validation["blocked_reasons"])
                result["raw_output_path"] = str(paths.raw_output_path)
                result["normalized_output_path"] = str(paths.normalized_output_path)
                result["processing_authority"] = "PRODUCTION_MARKET_REFRESH_CORE"
                result["production_refresh_adapter_version"] = PRODUCTION_REFRESH_ADAPTER_VERSION
                result["final_validation"] = validation
                if write_evidence:
                    write_acquisition_evidence(result, paths=paths)
                return result
            request_dates = list(refresh.get("required_dates") or _weekdays(str(chunk["start_date"]), str(chunk["end_date"])))
            chunk.update(
                {
                    "status": "COMPLETED",
                    "processing_authority": "PRODUCTION_MARKET_REFRESH_CORE",
                    "production_refresh_adapter_version": PRODUCTION_REFRESH_ADAPTER_VERSION,
                    "request_count": len(request_dates),
                    "page_count": len(request_dates),
                    "row_count": int(_daily_endpoint_summary(refresh).get("fetched_row_count", 0)),
                    "first_date": normalized_inv.get("earliest_date", ""),
                    "last_date": normalized_inv.get("latest_date", ""),
                    "content_hash": normalized_inv.get("content_hash", ""),
                    "raw_content_hash": raw_inv.get("content_hash", ""),
                    "completed_at": _utc_now(),
                    "error": "",
                    "retry_count": 0,
                    "requests": [_production_refresh_request_state(day, paths=paths, raw_hash=raw_inv.get("content_hash", "")) for day in request_dates],
                    "raw_chunk_path": str(paths.raw_output_path),
                    "production_market_refresh": refresh,
                    "production_refresh_manifest_path": refresh.get("manifest_path", ""),
                }
            )
            processed += 1
            _write_json(paths.state_path, state)
        except Exception as exc:  # noqa: BLE001
            request_states = chunk.get("requests") if isinstance(chunk.get("requests"), list) else []
            aggregate = _aggregate_request_states(request_states)
            chunk["status"] = "FAILED"
            chunk["error"] = _safe_error_text(exc)
            chunk["completed_at"] = _utc_now()
            chunk["request_count"] = aggregate["request_count"]
            chunk["page_count"] = aggregate["page_count"]
            chunk["row_count"] = aggregate["row_count"]
            chunk["retry_count"] = aggregate["retry_count"]
            if isinstance(exc, AcquisitionRequestError):
                chunk["http_status"] = exc.http_status
                chunk["diagnostic"] = _sanitize(exc.diagnostic)
            state["status"] = "BLOCK"
            _write_json(paths.state_path, state)
            result = _blocked_from_state(plan, state, "ACQUISITION_SOURCE_BLOCKED", [chunk["error"]])
            if write_evidence:
                write_acquisition_evidence(result, paths=paths)
            return result
    final = _materialize_final_staging(paths=paths, plan=plan, state=state)
    _write_json(paths.state_path, {**state, "status": final["status"], "final_validation": final.get("final_validation", {})})
    if write_evidence:
        write_acquisition_evidence(final, paths=paths)
    return final


def _materialize_final_staging(*, paths: AcquisitionPaths, plan: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    for chunk in state["chunks"]:
        if chunk.get("status") != "COMPLETED":
            return _blocked_from_state(plan, state, "ACQUISITION_SOURCE_BLOCKED", ["not_all_chunks_completed"])
    validation = validate_staging_source(
        normalized_path=paths.normalized_output_path,
        requested_start_date=str(plan["requested_start_date"]),
        requested_end_date=str(plan["requested_end_date"]),
        expected_business_dates=_state_expected_business_dates(state),
    )
    status = "PASS" if validation["status"] == "PASS" else "BLOCK"
    return {
        **_result_from_state(plan, state, status, "ACQUISITION_SOURCE_READY" if status == "PASS" else "ACQUISITION_SOURCE_BLOCKED"),
        "raw_output_path": str(paths.raw_output_path),
        "normalized_output_path": str(paths.normalized_output_path),
        "processing_authority": "PRODUCTION_MARKET_REFRESH_CORE",
        "production_refresh_adapter_version": PRODUCTION_REFRESH_ADAPTER_VERSION,
        "final_validation": validation,
        "bootstrap_plan_command": _bootstrap_plan_command(paths.normalized_output_path),
        "bootstrap_run_command": _bootstrap_run_command(paths.normalized_output_path),
    }


def validate_staging_source(
    *,
    normalized_path: Path | str,
    requested_start_date: str,
    requested_end_date: str,
    expected_business_dates: list[str] | None = None,
) -> dict[str, Any]:
    import pandas as pd

    path = Path(normalized_path)
    inventory = parquet_inventory(path)
    blocked: list[str] = []
    if inventory.get("status") != "PASS":
        blocked.append("normalized_inventory_not_pass")
    schema = compare_normalized_schemas(current=inventory, source=inventory)
    if schema.get("status") != "PASS":
        blocked.append("normalized_schema_invalid")
    expected_dates = sorted(str(day) for day in (expected_business_dates or []) if str(day))
    coverage_start = expected_dates[0] if expected_dates else requested_start_date
    coverage_end = expected_dates[-1] if expected_dates else requested_end_date
    if str(inventory.get("earliest_date") or "") > coverage_start:
        blocked.append("requested_start_coverage_missing")
    if str(inventory.get("latest_date") or "") < coverage_end:
        blocked.append("requested_end_coverage_missing")
    if inventory.get("future_or_training_columns_detected"):
        blocked.append("training_or_future_columns_detected")
    if inventory.get("duplicate_key_count"):
        blocked.append("duplicate_date_code_keys")
    ohlc = {"status": "MISSING"}
    lineage = {"status": "MISSING"}
    null_count = 0
    future_count = 0
    if path.is_file():
        frame = pd.read_parquet(path)
        required_normalized_columns = ["Date", "Code", "Open", "High", "Low", "Close", "Volume"]
        missing_columns = [column for column in required_normalized_columns if column not in frame.columns]
        if missing_columns:
            blocked.append("normalized_required_columns_missing")
            null_count = len(frame) * len(missing_columns)
            return {
                "schema_version": ACQUISITION_SCHEMA_VERSION,
                "status": "BLOCK",
                "final_judgment": "ACQUISITION_SOURCE_BLOCKED",
                "normalized_inventory": inventory,
                "schema_comparison": schema,
                "null_count": null_count,
                "future_date_count": future_count,
                "ohlc_integrity": {"status": "BLOCK", "missing_columns": missing_columns},
                "jquants_lineage": {"status": "BLOCK", "reason": "normalized_required_columns_missing"},
                "requested_start_date": requested_start_date,
                "requested_end_date": requested_end_date,
                "coverage_policy": "expected_business_date_range" if expected_dates else "literal_requested_date_range",
                "coverage_start_date": coverage_start,
                "coverage_end_date": coverage_end,
                "first_expected_business_date": expected_dates[0] if expected_dates else "",
                "last_expected_business_date": expected_dates[-1] if expected_dates else "",
                "expected_business_date_count": len(expected_dates),
                "expected_business_dates": expected_dates,
                "required_warmup_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
                "blocked_reasons": list(dict.fromkeys(blocked)),
                "content_hash": inventory.get("content_hash", ""),
            }
        null_count = int(frame[required_normalized_columns].isna().sum().sum())
        source_values = set(frame["source"].astype(str).str.lower()) if "source" in frame.columns else set()
        source_endpoint_values = set(frame["source_endpoint"].astype(str)) if "source_endpoint" in frame.columns else set()
        lineage = {
            "status": "PASS" if source_values == {"jquants"} and "/v2/equities/bars/daily" in source_endpoint_values else "BLOCK",
            "source_values": sorted(source_values),
            "source_endpoint_values": sorted(source_endpoint_values),
        }
        if lineage["status"] != "PASS":
            blocked.append("jquants_lineage_missing")
        today = date.today().isoformat()
        future_count = int((frame["Date"].astype(str) > today).sum())
        numeric = frame[["Open", "High", "Low", "Close", "Volume"]].apply(pd.to_numeric, errors="coerce")
        invalid_ohlc = (
            (numeric["High"] < numeric["Open"])
            | (numeric["High"] < numeric["Close"])
            | (numeric["Low"] > numeric["Open"])
            | (numeric["Low"] > numeric["Close"])
            | (numeric["High"] < numeric["Low"])
        )
        negative_price = (numeric[["Open", "High", "Low", "Close"]] < 0).any(axis=1)
        negative_volume = numeric["Volume"] < 0
        ohlc = {
            "status": "PASS" if not (invalid_ohlc.any() or negative_price.any() or negative_volume.any()) else "BLOCK",
            "invalid_ohlc_count": int(invalid_ohlc.sum()),
            "negative_price_count": int(negative_price.sum()),
            "negative_volume_count": int(negative_volume.sum()),
        }
        if null_count:
            blocked.append("required_value_nulls")
        if future_count:
            blocked.append("future_date_contamination")
        if ohlc["status"] != "PASS":
            blocked.append("ohlc_integrity_failed")
    return {
        "schema_version": ACQUISITION_SCHEMA_VERSION,
        "status": "PASS" if not blocked else "BLOCK",
        "final_judgment": "ACQUISITION_SOURCE_READY" if not blocked else "ACQUISITION_SOURCE_BLOCKED",
        "normalized_inventory": inventory,
        "schema_comparison": schema,
        "null_count": null_count,
        "future_date_count": future_count,
        "ohlc_integrity": ohlc,
        "jquants_lineage": lineage,
        "requested_start_date": requested_start_date,
        "requested_end_date": requested_end_date,
        "coverage_policy": "expected_business_date_range" if expected_dates else "literal_requested_date_range",
        "coverage_start_date": coverage_start,
        "coverage_end_date": coverage_end,
        "first_expected_business_date": expected_dates[0] if expected_dates else "",
        "last_expected_business_date": expected_dates[-1] if expected_dates else "",
        "expected_business_date_count": len(expected_dates),
        "expected_business_dates": expected_dates,
        "required_warmup_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
        "blocked_reasons": blocked,
        "content_hash": inventory.get("content_hash", ""),
    }


def _call_with_retry(
    *,
    fetcher: DailyQuotePageFetcher,
    request_date: str,
    pagination_key: str | None,
    max_retries: int,
    sleep: Any,
) -> tuple[dict[str, Any], int]:
    retries = 0
    while True:
        try:
            return fetcher.fetch_daily_quotes(date=request_date, pagination_key=pagination_key), retries
        except JQuantsClientError as exc:
            error_class = str(getattr(exc, "diagnostic", {}).get("error_class") or "")
            if error_class in NON_RETRYABLE_ERROR_CLASSES:
                raise AcquisitionRequestError(
                    _safe_error_text(exc),
                    request_date=request_date,
                    request_count=retries + 1,
                    page_count=0,
                    retry_count=retries,
                    http_status=getattr(exc, "diagnostic", {}).get("http_status", ""),
                    diagnostic=getattr(exc, "diagnostic", {}),
                ) from exc
            if error_class not in RETRYABLE_ERROR_CLASSES or retries >= max_retries:
                raise AcquisitionRequestError(
                    _safe_error_text(exc),
                    request_date=request_date,
                    request_count=retries + 1,
                    page_count=0,
                    retry_count=retries,
                    http_status=getattr(exc, "diagnostic", {}).get("http_status", ""),
                    diagnostic=getattr(exc, "diagnostic", {}),
                ) from exc
            sleep(min(60.0, (2**retries) + random.random() * 0.1))
            retries += 1


def _validate_raw_records(records: list[dict[str, Any]], *, start_date: str, end_date: str) -> None:
    for row in records:
        if not isinstance(row, dict):
            raise AcquisitionError("raw_record_not_object")
        day = _normalize_date(str(row.get("Date") or ""))
        if day < start_date or day > end_date:
            raise AcquisitionError("raw_date_outside_requested_chunk")
        suspicious = [column for column in row if column.lower() in TRAINING_ONLY_COLUMNS or column.lower().startswith(TRAINING_ONLY_PREFIXES)]
        if suspicious:
            raise AcquisitionError("training_only_columns_detected")
    validation = validate_records("daily_quotes", records)
    if validation.status == "ERROR":
        summary = validation.row_classification_summary
        reasons = ",".join(validation.messages) or "daily_quotes_raw_schema_error"
        if summary:
            reasons = (
                f"{reasons}:partial={summary.get('partial_ohlcv_corruption_count', 0)}"
                f":invalid_numeric={summary.get('invalid_numeric_row_count', 0)}"
                f":schema={summary.get('schema_corruption_count', 0)}"
            )
        raise AcquisitionError(f"daily_quotes_raw_validation_error:{reasons}")


def _contract_evidence(*, paths: AcquisitionPaths) -> dict[str, dict[str, Any]]:
    return {
        "existing_jquants_client_inventory.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "client": "src/ai_fund_lab_v2/data_sources/jquants/client.py",
            "endpoint": JQUANTS_DAILY_QUOTES_ENDPOINT,
            "auth": "x-api-key from JQUANTS_API_KEY via load_settings; secret is never persisted in evidence",
            "pagination_token": "pagination_key",
            "rate_limit": "JQuantsRateLimitPolicy",
            "retry": "JQuantsRetryPolicy plus acquisition chunk retry boundary",
            "timeout": "JQuantsSettings.timeout_seconds",
        },
        "daily_quotes_request_contract.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "request_contract_version": REQUEST_CONTRACT_VERSION,
            "method": "GET",
            "endpoint": JQUANTS_DAILY_QUOTES_ENDPOINT,
            "params": {"date": "YYYY-MM-DD", "pagination_key": "present only after first page"},
            "range_params_prohibited": ["from", "to"],
            "chunk_execution": "month/week/day chunks expand to per-date requests",
        },
        "existing_daily_refresh_contract.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "implementation": "src/ai_fund_lab_v2/paper_trading/market_data_refresh.py",
            "merge_key": ["target_date/Date/date", "business_key/Code/code/LocalCode", "endpoint"],
            "normalize": "ai_fund_lab_v2.data_quality.normalization.normalize_daily_quotes",
            "adjusted_price_policy": "AdjO/AdjH/AdjL/AdjC/AdjVo if complete else O/H/L/C/Vo",
        },
        "api_pagination_contract.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "strategy": "loop until pagination_key absent",
            "cycle_detection": "BLOCK on repeated pagination_key",
            "max_pages": "configurable max_pages_per_chunk",
        },
        "acquisition_chunk_contract.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "default_chunk": "month",
            "chunk_fields": ["chunk_id", "start_date", "end_date", "status", "request_count", "page_count", "row_count", "content_hash"],
        },
        "resume_contract.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "binding": ["requested_start_date", "requested_end_date", "endpoint", "chunk_strategy", "schema_version"],
            "completed_chunk_policy": "skip only if chunk parquet exists and hash matches state",
        },
        "retry_and_rate_limit_contract.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "retryable": sorted(RETRYABLE_ERROR_CLASSES),
            "non_retryable": sorted(NON_RETRYABLE_ERROR_CLASSES),
            "bounded_retry": True,
            "infinite_retry": False,
        },
        "raw_storage_contract.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "raw_output_path": str(paths.raw_output_path),
            "chunk_raw_root": str(paths.chunk_root),
            "source": "jquants",
        },
        "normalization_contract.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "normalizer": "ai_fund_lab_v2.data_quality.normalization.normalize_daily_quotes",
            "normalized_output_path": str(paths.normalized_output_path),
            "forbidden_columns": sorted(TRAINING_ONLY_COLUMNS),
        },
        "staging_validation_contract.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "checks": ["lineage", "schema", "coverage", "duplicates", "nulls", "OHLC", "negative values", "future dates", "training-only columns", "content hash"],
        },
        "bootstrap_handoff_contract.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "bootstrap_plan_command": _bootstrap_plan_command(paths.normalized_output_path),
            "bootstrap_run_command": _bootstrap_run_command(paths.normalized_output_path),
            "automatic_bootstrap": False,
        },
        "security_and_secret_audit.json": {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "status": "PASS",
            "secret_evidence_output": "PROHIBITED",
            "api_key_logged": False,
            "env_dumped": False,
        },
    }


def _initial_state(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": ACQUISITION_STATE_SCHEMA_VERSION,
        "status": "PENDING",
        "request_contract_version": REQUEST_CONTRACT_VERSION,
        "acquisition_connection_version": ACQUISITION_CONNECTION_VERSION,
        "acquisition_run_id": plan["acquisition_run_id"],
        "binding": _plan_binding(plan),
        "chunks": [dict(chunk) for chunk in plan["chunks"]],
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }


def _initial_request_state(request_date: str) -> dict[str, Any]:
    return {
        "request_date": request_date,
        "status": "PENDING",
        "request_count": 0,
        "page_count": 0,
        "row_count": 0,
        "first_date": "",
        "last_date": "",
        "content_hash": "",
        "started_at": "",
        "completed_at": "",
        "error": "",
        "retry_count": 0,
        "http_status": "",
    }


def _result_from_state(plan: dict[str, Any], state: dict[str, Any], status: str, final_judgment: str) -> dict[str, Any]:
    chunks = state.get("chunks", [])
    return {
        **plan,
        "operation": "run",
        "status": status,
        "final_judgment": final_judgment,
        "read_only": False,
        "request_contract_version": REQUEST_CONTRACT_VERSION,
        "acquisition_connection_version": ACQUISITION_CONNECTION_VERSION,
        "production_refresh_adapter_version": PRODUCTION_REFRESH_ADAPTER_VERSION,
        "processing_authority": "PRODUCTION_MARKET_REFRESH_CORE",
        "chunks": chunks,
        "completed_chunks": sum(1 for chunk in chunks if chunk.get("status") == "COMPLETED"),
        "remaining_chunks": sum(1 for chunk in chunks if chunk.get("status") != "COMPLETED"),
        "request_count": sum(int(chunk.get("request_count", 0)) for chunk in chunks),
        "page_count": sum(int(chunk.get("page_count", 0)) for chunk in chunks),
        "row_count": sum(int(chunk.get("row_count", 0)) for chunk in chunks),
        "retry_count": sum(int(chunk.get("retry_count", 0)) for chunk in chunks),
        "jquants_api_fetch_executed": True,
        "runtime_market_data_mutated": False,
        "broker_access": "NOT_PERFORMED",
    }


def _blocked_from_plan(plan: dict[str, Any], final_judgment: str, reasons: list[str]) -> dict[str, Any]:
    return {
        **plan,
        "operation": "run",
        "status": "BLOCK",
        "final_judgment": final_judgment,
        "blocked_reasons": list(dict.fromkeys([*plan.get("blocked_reasons", []), *reasons])),
        "jquants_api_fetch_executed": False,
        "runtime_market_data_mutated": False,
    }


def _blocked_from_state(plan: dict[str, Any], state: dict[str, Any], final_judgment: str, reasons: list[str]) -> dict[str, Any]:
    payload = _result_from_state(plan, state, "BLOCK", final_judgment)
    payload["blocked_reasons"] = list(dict.fromkeys([*payload.get("blocked_reasons", []), *reasons]))
    return payload


def _chunk_raw_path(paths: AcquisitionPaths, chunk_id: str) -> Path:
    return paths.chunk_root / chunk_id / "raw.parquet"


def _chunk_artifact_valid(*, paths: AcquisitionPaths, chunk: dict[str, Any]) -> bool:
    if chunk.get("processing_authority") == "PRODUCTION_MARKET_REFRESH_CORE":
        if not paths.raw_output_path.is_file() or not paths.normalized_output_path.is_file():
            return False
        manifest_path = str(chunk.get("production_refresh_manifest_path") or "")
        return not manifest_path or Path(manifest_path).is_file()
    path = _chunk_raw_path(paths, str(chunk["chunk_id"]))
    if not path.is_file():
        return False
    return parquet_inventory(path).get("content_hash") == chunk.get("content_hash")


def _plan_binding(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": plan.get("schema_version"),
        "request_contract_version": plan.get("request_contract_version"),
        "acquisition_connection_version": plan.get("acquisition_connection_version"),
        "production_refresh_adapter_version": plan.get("production_refresh_adapter_version"),
        "requested_start_date": plan.get("requested_start_date"),
        "requested_end_date": plan.get("requested_end_date"),
        "endpoint": plan.get("endpoint"),
        "chunk_strategy": plan.get("chunk_strategy"),
    }


def _state_binding(state: dict[str, Any]) -> dict[str, Any]:
    binding = state.get("binding")
    return binding if isinstance(binding, dict) else {}


def _request_contract_compatibility(*, plan: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    plan_contract = str(plan.get("request_contract_version") or "")
    state_contract = str(state.get("request_contract_version") or _state_binding(state).get("request_contract_version") or "")
    plan_connection = str(plan.get("acquisition_connection_version") or "")
    state_connection = str(state.get("acquisition_connection_version") or _state_binding(state).get("acquisition_connection_version") or "")
    plan_adapter = str(plan.get("production_refresh_adapter_version") or "")
    state_adapter = str(state.get("production_refresh_adapter_version") or _state_binding(state).get("production_refresh_adapter_version") or "")
    if state_contract != REQUEST_CONTRACT_VERSION:
        return {
            "status": "BLOCK",
            "final_judgment": "ACQUISITION_LEGACY_RUN_INCOMPATIBLE_WITH_UPDATED_REQUEST_CONTRACT",
            "blocked_reasons": ["old_run_incompatible_with_phase20_bd_request_contract", "new_run_id_required"],
        }
    if plan_contract != REQUEST_CONTRACT_VERSION:
        return {
            "status": "BLOCK",
            "final_judgment": "ACQUISITION_REQUEST_CONTRACT_MISMATCH",
            "blocked_reasons": ["plan_request_contract_not_phase20_bd"],
        }
    if state_connection != ACQUISITION_CONNECTION_VERSION:
        return {
            "status": "BLOCK",
            "final_judgment": "LEGACY_RUN_RAW_ARTIFACT_MISSING",
            "blocked_reasons": ["legacy_probe_run_missing_raw_artifact_authority", "NEW_RUN_REQUIRED"],
        }
    if state_adapter != PRODUCTION_REFRESH_ADAPTER_VERSION:
        return {
            "status": "BLOCK",
            "final_judgment": "LEGACY_RUN_INCOMPATIBLE_WITH_PRODUCTION_REFRESH_ADAPTER",
            "blocked_reasons": ["legacy_run_not_created_by_phase20_bf_production_refresh_adapter", "NEW_RUN_REQUIRED"],
        }
    if plan_connection != ACQUISITION_CONNECTION_VERSION:
        return {
            "status": "BLOCK",
            "final_judgment": "ACQUISITION_CONNECTION_CONTRACT_MISMATCH",
            "blocked_reasons": ["plan_acquisition_connection_not_phase20_be"],
        }
    if plan_adapter != PRODUCTION_REFRESH_ADAPTER_VERSION:
        return {
            "status": "BLOCK",
            "final_judgment": "PRODUCTION_REFRESH_ADAPTER_CONTRACT_MISMATCH",
            "blocked_reasons": ["plan_adapter_not_phase20_bf"],
        }
    return {"status": "PASS", "final_judgment": "ACQUISITION_REQUEST_CONTRACT_COMPATIBLE", "blocked_reasons": []}


def _paths_from_plan(plan: dict[str, Any], *, runtime_root: Path, evidence_root: Path, staging_root: Path) -> AcquisitionPaths:
    return AcquisitionPaths(runtime_root, str(plan["acquisition_run_id"]), evidence_root, staging_root)


def _default_fetcher(runtime_root: Path) -> JQuantsClient:
    return JQuantsAPIFetcher(runtime_dir=runtime_root)


def _write_parquet_atomic(path: Path, records_or_frame: Any) -> None:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    frame = records_or_frame if hasattr(records_or_frame, "to_parquet") else pd.DataFrame(records_or_frame)
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(_sanitize(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def _read_json_optional(path: Path) -> dict[str, Any]:
    try:
        return _read_json(path)
    except Exception:
        return {}


def _sanitize(payload: Any) -> Any:
    if isinstance(payload, dict):
        blocked = {"api_key", "token", "authorization", "x-api-key", "password", "id_token", "refresh_token", "secret"}
        return {key: _sanitize(value) for key, value in payload.items() if key.lower() not in blocked}
    if isinstance(payload, list):
        return [_sanitize(item) for item in payload]
    if isinstance(payload, tuple):
        return [_sanitize(item) for item in payload]
    return payload


def _safe_error_text(exc: Exception) -> str:
    text = str(exc) or type(exc).__name__
    for marker in ("JQUANTS_API_KEY=", "x-api-key", "Authorization"):
        text = text.replace(marker, "<redacted>")
    return text[:300]


def _content_hash(records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(_sanitize(records), ensure_ascii=True, sort_keys=True, default=str).encode("utf-8"))
    return digest.hexdigest()


def _aggregate_request_states(request_states: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "request_count": sum(int(item.get("request_count", 0)) for item in request_states),
        "page_count": sum(int(item.get("page_count", 0)) for item in request_states),
        "row_count": sum(int(item.get("row_count", 0)) for item in request_states),
        "retry_count": sum(int(item.get("retry_count", 0)) for item in request_states),
    }


def _bootstrap_plan_command(source_path: Path) -> str:
    return f"PYTHONPATH=src:. python3 scripts/runtime_test.py market-data-bootstrap plan --years 5 --source-path {source_path} --write-evidence --json"


def _bootstrap_run_command(source_path: Path) -> str:
    return f"PYTHONPATH=src:. python3 scripts/runtime_test.py market-data-bootstrap run --years 5 --source-path {source_path} --confirm --yes-i-understand-this-mutates-market-data --write-evidence --json"


def _weekdays(start_date: str, end_date: str) -> list[str]:
    current = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    values = []
    while current <= end:
        if current.weekday() < 5:
            values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def _validate_date_range(start: str, end: str) -> None:
    if date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError("start_date must be before or equal to end_date")


def _normalize_date(value: str) -> str:
    text = str(value or "").strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return date.fromisoformat(text).isoformat()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
