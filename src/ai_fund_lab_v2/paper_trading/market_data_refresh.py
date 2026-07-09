from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes
from ai_fund_lab_v2.data_sources.jquants import JQuantsClient
from ai_fund_lab_v2.paper_trading.market_data_readiness import check_market_data_readiness
from ai_fund_lab_v2.runtime import RuntimePaths


ENDPOINTS = ("daily_quotes", "listed_info", "trading_calendar")
RAW_COLLECTIONS = {
    "daily_quotes": "jquants/equities_bars_daily",
    "listed_info": "jquants/listed_issues",
    "trading_calendar": "jquants/trading_calendar",
}
RAW_ENDPOINTS = {
    "daily_quotes": "/v2/equities/bars/daily",
    "listed_info": "/v2/equities/master",
    "trading_calendar": "/v2/markets/calendar",
}
NORMALIZED_DAILY_QUOTES_COLLECTION = "jquants/equities_bars_daily"
STATUS_DRY_RUN = "DRY_RUN"
STATUS_COMPLETED = "COMPLETED"
STATUS_PARTIAL = "PARTIAL"
STATUS_PARTIAL_AVAILABLE = "PARTIAL_AVAILABLE"
STATUS_MARKET_DATA_READY_FOR_LATEST_AVAILABLE = "MARKET_DATA_READY_FOR_LATEST_AVAILABLE"
STATUS_API_PARAM_ERROR = "API_PARAM_ERROR"
STATUS_API_AUTH_ERROR = "API_AUTH_ERROR"
STATUS_API_NETWORK_ERROR = "API_NETWORK_ERROR"
STATUS_API_RATE_LIMIT = "API_RATE_LIMIT"
STATUS_API_SERVER_ERROR = "API_SERVER_ERROR"
STATUS_MARKET_DATA_NOT_YET_AVAILABLE = "MARKET_DATA_NOT_YET_AVAILABLE"
STATUS_DATA_FRESHNESS_BLOCKED = "DATA_FRESHNESS_BLOCKED"
STATUS_UNKNOWN_API_ERROR = "UNKNOWN_API_ERROR"
STATUS_FETCH_FAILED = "FETCH_FAILED"
STATUS_BLOCKED = "BLOCKED"
STATUS_FAILED = "FAILED"


class MarketDataFetcher(Protocol):
    def fetch_daily_quotes(self, *, from_date: str, to_date: str) -> list[dict[str, Any]]:
        ...

    def fetch_listed_info(self, *, date: str) -> list[dict[str, Any]]:
        ...

    def fetch_trading_calendar(self, *, from_date: str, to_date: str) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class EndpointRefreshSummary:
    endpoint: str
    status: str
    existing_latest_date: str = ""
    fetched_row_count: int = 0
    raw_path: str = ""
    normalized_path: str = ""
    row_count: int = 0
    min_date: str = ""
    max_date: str = ""
    backup_path: str = ""
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


@dataclass(frozen=True)
class MarketDataRefreshResult:
    status: str
    from_date: str
    to_date: str
    dry_run: bool
    allow_api_fetch: bool
    fetch_mode: str
    backup_existing: bool
    requested_from_date: str
    requested_to_date: str
    latest_successful_daily_quotes_date: str
    latest_normalized_daily_quotes_date: str
    latest_listed_info_date: str
    latest_trading_calendar_date: str
    data_until: str
    unavailable_dates: tuple[str, ...]
    not_yet_available_dates: tuple[str, ...]
    failed_dates: tuple[str, ...]
    required_dates: tuple[str, ...]
    endpoints: tuple[EndpointRefreshSummary, ...]
    manifest_path: str
    markdown_report_path: str
    json_report_path: str
    readiness_result: dict[str, Any]
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    api_error_classification: str = ""
    api_error_diagnostics: tuple[dict[str, Any], ...] = ()
    next_action: str = ""
    jquants_api_fetch_executed: bool = False
    feature_generation_executed: bool = False
    model_retraining_executed: bool = False
    inference_executed: bool = False
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    virtual_fill_executed: bool = False
    live_order_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_dates"] = list(self.required_dates)
        payload["unavailable_dates"] = list(self.unavailable_dates)
        payload["not_yet_available_dates"] = list(self.not_yet_available_dates)
        payload["failed_dates"] = list(self.failed_dates)
        payload["endpoints"] = [endpoint.to_dict() for endpoint in self.endpoints]
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        payload["api_error_diagnostics"] = [dict(item) for item in self.api_error_diagnostics]
        return payload


class JQuantsAPIFetcher:
    def __init__(self, *, runtime_dir: Path | str = ".runtime") -> None:
        settings = load_settings()
        paths = settings.runtime_paths
        if runtime_dir:
            paths = RuntimePaths(runtime_dir=Path(runtime_dir))
        self.client = JQuantsClient(settings=settings.jquants, paths=paths)

    def fetch_daily_quotes(self, *, from_date: str, to_date: str) -> list[dict[str, Any]]:
        return self.client.fetch_all_daily_quotes(from_date=from_date, to_date=to_date)

    def fetch_daily_quotes_for_date(self, *, target_date: str) -> list[dict[str, Any]]:
        return self.client.fetch_all_daily_quotes(date=target_date)

    def fetch_listed_info(self, *, date: str) -> list[dict[str, Any]]:
        return self.client.fetch_all_listed_issues(date=date)

    def fetch_trading_calendar(self, *, from_date: str, to_date: str) -> list[dict[str, Any]]:
        return self.client.fetch_all_trading_calendar(from_date=from_date, to_date=to_date)


def run_market_data_refresh(
    *,
    from_date: str,
    to_date: str,
    dry_run: bool = True,
    allow_api_fetch: bool = False,
    raw_output_root: Path | str = ".runtime/data/raw",
    normalized_output_root: Path | str = ".runtime/data/raw_normalized",
    manifest_output_root: Path | str = ".runtime/phase9/market_data_refresh",
    backup_existing: bool = True,
    fetch_mode: str = "range",
    fetcher: MarketDataFetcher | None = None,
    today: str | None = None,
    markdown_report_path: Path | str = "docs/phase_reports/phase9i_market_data_refresh_report.md",
    json_report_path: Path | str = "reports/phase_reports/phase9i_market_data_refresh_report.json",
) -> MarketDataRefreshResult:
    warnings: list[str] = []
    blocked: list[str] = []
    normalized_from = _normalize_date(from_date)
    normalized_to = _normalize_date(to_date)
    if fetch_mode not in {"range", "per-date"}:
        raise ValueError("fetch_mode must be one of: range, per-date")
    _validate_date_range(normalized_from, normalized_to, today=today)

    raw_root = Path(raw_output_root)
    normalized_root = Path(normalized_output_root)
    manifest_dir = Path(manifest_output_root) / normalized_to
    manifest_path = manifest_dir / "refresh_manifest.json"
    md_path = Path(markdown_report_path)
    json_path = Path(json_report_path)

    required_dates = tuple(_iter_dates(normalized_from, normalized_to))
    summaries: list[EndpointRefreshSummary] = []
    for endpoint in ENDPOINTS:
        raw_path = _raw_path(raw_root, endpoint)
        normalized_path = _normalized_path(normalized_root, endpoint) if endpoint == "daily_quotes" else ""
        summaries.append(
            EndpointRefreshSummary(
                endpoint=endpoint,
                status=STATUS_DRY_RUN if dry_run else STATUS_BLOCKED,
                existing_latest_date=_latest_date(_read_records(raw_path)),
                raw_path=str(raw_path),
                normalized_path=str(normalized_path),
                blocked_reasons=() if dry_run else ("api_fetch_not_allowed",),
            )
        )

    readiness = _readiness(raw_root=raw_root, normalized_root=normalized_root, decision_for=normalized_to)
    status = STATUS_DRY_RUN
    api_executed = False
    if not dry_run:
        if not allow_api_fetch:
            blocked.append("allow_api_fetch_required")
            status = STATUS_BLOCKED
        else:
            api_executed = True
            summaries, readiness, status, warnings, blocked, date_state = _execute_refresh(
                from_date=normalized_from,
                to_date=normalized_to,
                raw_root=raw_root,
                normalized_root=normalized_root,
                backup_existing=backup_existing,
                fetch_mode=fetch_mode,
                fetcher=fetcher or JQuantsAPIFetcher(),
            )
        if "date_state" not in locals():
            date_state = {}
    else:
        date_state = {}
    latest_success = str(date_state.get("latest_successful_daily_quotes_date") or "")
    latest_normalized = _latest_date(_read_records(_normalized_path(normalized_root, "daily_quotes")))
    latest_listed = _latest_date(_read_records(_raw_path(raw_root, "listed_info")))
    latest_calendar = _latest_date(_read_records(_raw_path(raw_root, "trading_calendar")))
    data_until = _min_nonempty(latest_normalized, latest_listed) or readiness.get("data_until", "")

    result = MarketDataRefreshResult(
        status=status,
        from_date=normalized_from,
        to_date=normalized_to,
        dry_run=dry_run,
        allow_api_fetch=allow_api_fetch,
        fetch_mode=fetch_mode,
        backup_existing=backup_existing,
        requested_from_date=normalized_from,
        requested_to_date=normalized_to,
        latest_successful_daily_quotes_date=latest_success,
        latest_normalized_daily_quotes_date=latest_normalized,
        latest_listed_info_date=latest_listed,
        latest_trading_calendar_date=latest_calendar,
        data_until=str(data_until or ""),
        unavailable_dates=tuple(date_state.get("unavailable_dates", ())),
        not_yet_available_dates=tuple(date_state.get("not_yet_available_dates", ())),
        failed_dates=tuple(date_state.get("failed_dates", ())),
        required_dates=tuple(date_state.get("target_dates") or required_dates),
        endpoints=tuple(summaries),
        manifest_path=str(manifest_path),
        markdown_report_path=str(md_path),
        json_report_path=str(json_path),
        readiness_result=readiness,
        warnings=tuple(warnings),
        blocked_reasons=tuple(blocked),
        api_error_classification=str(date_state.get("api_error_classification") or _classify_blocked_reasons(blocked)),
        api_error_diagnostics=tuple(date_state.get("api_error_diagnostics") or ()),
        next_action=_next_action(str(date_state.get("api_error_classification") or _classify_blocked_reasons(blocked)), blocked),
        jquants_api_fetch_executed=api_executed,
    )
    _write_outputs(result=result, manifest_path=manifest_path, markdown_path=md_path, json_path=json_path)
    return result


def _execute_refresh(
    *,
    from_date: str,
    to_date: str,
    raw_root: Path,
    normalized_root: Path,
    backup_existing: bool,
    fetch_mode: str,
    fetcher: MarketDataFetcher,
) -> tuple[list[EndpointRefreshSummary], dict[str, Any], str, list[str], list[str], dict[str, Any]]:
    summaries: list[EndpointRefreshSummary] = []
    warnings: list[str] = []
    blocked: list[str] = []
    any_failed = False
    date_state: dict[str, Any] = {
        "unavailable_dates": [],
        "not_yet_available_dates": [],
        "failed_dates": [],
        "api_error_diagnostics": [],
    }
    try:
        if fetch_mode == "per-date":
            daily_records, date_state = _fetch_daily_quotes_per_date(
                fetcher=fetcher,
                from_date=from_date,
                to_date=to_date,
                calendar_records=_read_records(_raw_path(raw_root, "trading_calendar")),
            )
        else:
            daily_records = fetcher.fetch_daily_quotes(from_date=from_date, to_date=to_date)
        fetched = {
            "daily_quotes": daily_records,
            "listed_info": fetcher.fetch_listed_info(date=to_date),
            "trading_calendar": fetcher.fetch_trading_calendar(from_date=from_date, to_date=to_date),
        }
    except Exception as exc:
        fetched = {}
        any_failed = True
        diagnostic = _safe_exception_diagnostic(exc)
        if diagnostic:
            date_state.setdefault("api_error_diagnostics", []).append(diagnostic)
        classification = _classify_exception(exc)
        date_state["api_error_classification"] = classification
        blocked.append(classification)
        blocked.append(f"api_fetch_failed:{type(exc).__name__}")

    for endpoint in ENDPOINTS:
        raw_path = _raw_path(raw_root, endpoint)
        existing = _read_records(raw_path)
        existing_latest = _latest_date(existing)
        incoming = [_with_metadata(record, endpoint=endpoint, default_date=to_date) for record in fetched.get(endpoint, [])]
        endpoint_status = STATUS_FAILED if any_failed else STATUS_COMPLETED
        backup_path = _backup_path(raw_path) if backup_existing and raw_path.exists() and not any_failed else ""
        if backup_path:
            Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(raw_path, backup_path)
        if any_failed:
            summaries.append(
                EndpointRefreshSummary(
                    endpoint=endpoint,
                    status=STATUS_FAILED,
                    existing_latest_date=existing_latest,
                    raw_path=str(raw_path),
                    backup_path=backup_path,
                    blocked_reasons=tuple(blocked),
                )
            )
            continue
        merged = _merge_records(existing, incoming)
        _write_records(raw_path, merged)
        normalized_path = ""
        if endpoint == "daily_quotes":
            normalized_records, report = normalize_daily_quotes(merged)
            normalized_path = str(_normalized_path(normalized_root, endpoint))
            backup_normalized = _backup_path(Path(normalized_path)) if backup_existing and Path(normalized_path).exists() else ""
            if backup_normalized:
                Path(backup_normalized).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(normalized_path, backup_normalized)
            _write_records(Path(normalized_path), normalized_records)
            if report.status not in {"OK", "WARN"}:
                warnings.append(f"daily_quotes_normalization_status={report.status}")
        summaries.append(
            EndpointRefreshSummary(
                endpoint=endpoint,
                status=endpoint_status,
                existing_latest_date=existing_latest,
                fetched_row_count=len(incoming),
                raw_path=str(raw_path),
                normalized_path=normalized_path,
                row_count=len(merged),
                min_date=_min_date(merged),
                max_date=_latest_date(merged),
                backup_path=backup_path,
            )
        )
    readiness = _readiness(raw_root=raw_root, normalized_root=normalized_root, decision_for=to_date)
    if readiness.get("status") != "READY":
        blocked.extend(str(item) for item in readiness.get("blocked_reasons", []))
    classification = str(date_state.get("api_error_classification") or "")
    if classification:
        blocked.append(classification)
    if "data_until_before_decision_for" in blocked:
        blocked.append(STATUS_DATA_FRESHNESS_BLOCKED)
    blocked = list(dict.fromkeys(blocked))
    status = _refresh_status(fetch_mode=fetch_mode, blocked=blocked, warnings=warnings, date_state=date_state, readiness=readiness)
    date_state["api_error_classification"] = date_state.get("api_error_classification") or _classify_blocked_reasons(blocked)
    return summaries, readiness, status, warnings, blocked, date_state


def _fetch_daily_quotes_per_date(
    *,
    fetcher: MarketDataFetcher,
    from_date: str,
    to_date: str,
    calendar_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    successful: list[str] = []
    unavailable: list[str] = []
    not_yet_available: list[str] = []
    failed: list[str] = []
    diagnostics: list[dict[str, Any]] = []
    target_dates = _business_dates(from_date, to_date, calendar_records=calendar_records)
    for target_date in target_dates:
        try:
            fetch_for_date = getattr(fetcher, "fetch_daily_quotes_for_date", None)
            daily = fetch_for_date(target_date=target_date) if fetch_for_date else fetcher.fetch_daily_quotes(from_date=target_date, to_date=target_date)
        except Exception as exc:
            diagnostic = _safe_exception_diagnostic(exc)
            if diagnostic:
                diagnostic = {**diagnostic, "date": diagnostic.get("date") or target_date}
                diagnostics.append(diagnostic)
            if target_date == to_date:
                not_yet_available.append(target_date)
            else:
                failed.append(f"{target_date}:{type(exc).__name__}")
            continue
        if not daily:
            if target_date == to_date:
                not_yet_available.append(target_date)
            else:
                unavailable.append(target_date)
            continue
        successful.append(target_date)
        records.extend(daily)
    return records, {
        "target_dates": target_dates,
        "successful_dates": successful,
        "latest_successful_daily_quotes_date": max(successful, default=""),
        "unavailable_dates": unavailable,
        "not_yet_available_dates": not_yet_available,
        "failed_dates": failed,
        "api_error_diagnostics": diagnostics,
        "api_error_classification": _dominant_api_error_classification(diagnostics),
    }


def _business_dates(from_date: str, to_date: str, *, calendar_records: list[dict[str, Any]]) -> list[str]:
    if calendar_records:
        if _latest_date(calendar_records) < to_date:
            return [day for day in _iter_dates(from_date, to_date) if date.fromisoformat(day).weekday() < 5]
        values = []
        for record in calendar_records:
            day = _record_date(record)
            if not day or day < from_date or day > to_date:
                continue
            holdiv_value = record.get("HolDiv")
            if holdiv_value is None:
                holdiv_value = record.get("holiday_division")
            holdiv = "" if holdiv_value is None else str(holdiv_value)
            if holdiv in {"1", "BusinessDay", "business_day", ""}:
                values.append(day)
        if values:
            return sorted(set(values))
    return [day for day in _iter_dates(from_date, to_date) if date.fromisoformat(day).weekday() < 5]


def _refresh_status(
    *,
    fetch_mode: str,
    blocked: list[str],
    warnings: list[str],
    date_state: dict[str, Any],
    readiness: dict[str, Any],
) -> str:
    if fetch_mode != "per-date":
        return STATUS_PARTIAL if blocked or warnings else STATUS_COMPLETED
    successful = date_state.get("successful_dates") or []
    failed = date_state.get("failed_dates") or []
    not_yet = date_state.get("not_yet_available_dates") or []
    classification = str(date_state.get("api_error_classification") or "")
    if not successful and (failed or not_yet or blocked):
        if classification in {
            STATUS_API_PARAM_ERROR,
            STATUS_API_AUTH_ERROR,
            STATUS_API_NETWORK_ERROR,
            STATUS_API_RATE_LIMIT,
            STATUS_API_SERVER_ERROR,
            STATUS_UNKNOWN_API_ERROR,
        }:
            return classification
        if not_yet and not failed:
            return STATUS_MARKET_DATA_NOT_YET_AVAILABLE
        return STATUS_FETCH_FAILED
    if readiness.get("status") == "READY" and not failed:
        if not_yet:
            return STATUS_PARTIAL_AVAILABLE
        return STATUS_MARKET_DATA_READY_FOR_LATEST_AVAILABLE
    if successful:
        return STATUS_PARTIAL_AVAILABLE
    return STATUS_FETCH_FAILED


def _write_outputs(
    *,
    result: MarketDataRefreshResult,
    manifest_path: Path,
    markdown_path: Path,
    json_path: Path,
) -> None:
    payload = _sanitize(result.to_dict())
    for path in (manifest_path, markdown_path, json_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-I Market Data Refresh Report",
        "",
        f"- status: {payload['status']}",
        f"- from_date: {payload['from_date']}",
        f"- to_date: {payload['to_date']}",
        f"- dry_run: {payload['dry_run']}",
        f"- allow_api_fetch: {payload['allow_api_fetch']}",
        f"- fetch_mode: {payload.get('fetch_mode', 'range')}",
            f"- data_until: {payload.get('data_until', '')}",
            f"- api_error_classification: {payload.get('api_error_classification', '')}",
            f"- next_action: {payload.get('next_action', '')}",
            "",
        "## Endpoints",
        "",
        "| endpoint | status | existing_latest | fetched_rows | rows | max_date | raw_path | normalized_path |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for endpoint in payload["endpoints"]:
        lines.append(
            "| {endpoint} | {status} | {existing_latest_date} | {fetched_row_count} | {row_count} | {max_date} | `{raw_path}` | `{normalized_path}` |".format(
                **endpoint
            )
        )
    lines.extend(
        [
            "",
            "## Readiness",
            "",
            f"- status: {payload['readiness_result'].get('status')}",
            f"- data_until: {payload['readiness_result'].get('data_until')}",
            f"- blocked_reasons: {', '.join(payload['readiness_result'].get('blocked_reasons') or [])}",
            f"- latest_successful_daily_quotes_date: {payload.get('latest_successful_daily_quotes_date')}",
            f"- latest_normalized_daily_quotes_date: {payload.get('latest_normalized_daily_quotes_date')}",
            f"- latest_listed_info_date: {payload.get('latest_listed_info_date')}",
            f"- latest_trading_calendar_date: {payload.get('latest_trading_calendar_date')}",
            "",
            "## Safety Flags",
            "",
        ]
    )
    for key in (
        "jquants_api_fetch_executed",
        "feature_generation_executed",
        "model_retraining_executed",
        "inference_executed",
        "broker_order_api_called",
        "open_d_started",
        "unlock_trade_called",
        "virtual_fill_executed",
        "live_order_allowed",
    ):
        lines.append(f"- {key}: {payload[key]}")
    if payload.get("blocked_reasons"):
        lines.extend(["", "## Blocked Reasons", ""])
        lines.extend(f"- {reason}" for reason in payload["blocked_reasons"])
    if payload.get("api_error_diagnostics"):
        lines.extend(["", "## API Error Diagnostics", ""])
        for diagnostic in payload["api_error_diagnostics"]:
            lines.append(
                "- endpoint={endpoint} date={date} error_class={error_class} network_error_type={network_error_type} http_status={http_status} url_host={url_host}".format(
                    endpoint=diagnostic.get("endpoint", ""),
                    date=diagnostic.get("date", ""),
                    error_class=diagnostic.get("error_class", ""),
                    network_error_type=diagnostic.get("network_error_type", ""),
                    http_status=diagnostic.get("http_status", ""),
                    url_host=diagnostic.get("url_host", ""),
                )
            )
    if payload.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in payload["warnings"])
    lines.append("")
    return "\n".join(lines)


def _readiness(*, raw_root: Path, normalized_root: Path, decision_for: str) -> dict[str, Any]:
    return check_market_data_readiness(
        decision_for=decision_for,
        daily_quotes_path=_normalized_path(normalized_root, "daily_quotes"),
        listed_info_path=_raw_path(raw_root, "listed_info"),
    ).to_dict()


def _raw_path(raw_root: Path, endpoint: str) -> Path:
    return raw_root / RAW_COLLECTIONS[endpoint] / "data.parquet"


def _normalized_path(normalized_root: Path, endpoint: str) -> Path:
    if endpoint != "daily_quotes":
        return Path("")
    return normalized_root / NORMALIZED_DAILY_QUOTES_COLLECTION / "data.parquet"


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    if path.suffix.lower() == ".parquet":
        import pandas as pd

        frame = pd.read_parquet(path)
        return frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(item) for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("data", "rows", "items"):
                if isinstance(payload.get(key), list):
                    return [dict(item) for item in payload[key] if isinstance(item, dict)]
            return [payload]
    return []


def _write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".parquet":
        import pandas as pd

        pd.DataFrame(records).to_parquet(path, index=False)
        return
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _with_metadata(record: dict[str, Any], *, endpoint: str, default_date: str) -> dict[str, Any]:
    normalized = dict(record)
    normalized["target_date"] = normalized.get("target_date") or normalized.get("Date") or normalized.get("date") or default_date
    normalized["code"] = str(normalized.get("code") or normalized.get("Code") or normalized.get("LocalCode") or "")
    normalized["business_key"] = str(
        normalized.get("business_key")
        or normalized.get("code")
        or normalized.get("Code")
        or normalized.get("LocalCode")
        or normalized.get("Date")
        or normalized.get("date")
        or normalized.get("target_date")
        or ""
    )
    normalized["source"] = "jquants"
    normalized["endpoint"] = RAW_ENDPOINTS[endpoint]
    normalized["fetched_at"] = normalized.get("fetched_at") or datetime.now(timezone.utc).isoformat()
    return normalized


def _merge_records(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {_record_key(record): record for record in existing}
    for record in incoming:
        merged[_record_key(record)] = record
    return sorted(merged.values(), key=_record_key)


def _record_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("target_date") or record.get("Date") or record.get("date") or ""),
        str(record.get("business_key") or record.get("Code") or record.get("code") or record.get("LocalCode") or ""),
        str(record.get("endpoint") or ""),
    )


def _latest_date(records: list[dict[str, Any]]) -> str:
    return max((_record_date(record) for record in records if _record_date(record)), default="")


def _min_nonempty(*values: str) -> str:
    present = [value for value in values if value]
    return min(present) if present else ""


def _min_date(records: list[dict[str, Any]]) -> str:
    return min((_record_date(record) for record in records if _record_date(record)), default="")


def _record_date(record: dict[str, Any]) -> str:
    return _normalize_date(str(record.get("Date") or record.get("date") or record.get("target_date") or ""))


def _backup_path(path: Path) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return str(path.with_name(f"{path.name}.backup_{stamp}"))


def _validate_date_range(from_date: str, to_date: str, *, today: str | None) -> None:
    if not from_date or not to_date:
        raise ValueError("from_date and to_date are required.")
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)
    current = date.fromisoformat(today) if today else date.today()
    if start > end:
        raise ValueError("from_date must be before or equal to to_date.")
    if end > current:
        raise ValueError("to_date must not be in the future.")


def _normalize_date(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return date.fromisoformat(text).isoformat()


def _iter_dates(from_date: str, to_date: str) -> list[str]:
    current = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)
    values: list[str] = []
    while current <= end:
        values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def _sanitize(payload: Any) -> Any:
    if isinstance(payload, dict):
        blocked = {"api_key", "token", "authorization", "x-api-key", "password", "id_token", "refresh_token", "secret"}
        return {key: _sanitize(value) for key, value in payload.items() if key.lower() not in blocked}
    if isinstance(payload, list):
        return [_sanitize(item) for item in payload]
    if isinstance(payload, tuple):
        return [_sanitize(item) for item in payload]
    return payload


def _safe_exception_diagnostic(exc: Exception) -> dict[str, Any]:
    diagnostic = getattr(exc, "diagnostic", None)
    if not isinstance(diagnostic, dict):
        return {}
    allowed = {
        "endpoint",
        "date",
        "from_date",
        "to_date",
        "error_class",
        "network_error_type",
        "http_status",
        "url_host",
    }
    return {key: diagnostic.get(key, "") for key in sorted(allowed)}


def _classify_exception(exc: Exception) -> str:
    diagnostic = _safe_exception_diagnostic(exc)
    classification = str(diagnostic.get("error_class") or "")
    if classification:
        return classification
    name = type(exc).__name__
    if name == "JQuantsClientError":
        return STATUS_UNKNOWN_API_ERROR
    return STATUS_FETCH_FAILED


def _dominant_api_error_classification(diagnostics: list[dict[str, Any]]) -> str:
    classifications = [str(item.get("error_class") or "") for item in diagnostics if item.get("error_class")]
    if not classifications:
        return ""
    priority = [
        STATUS_API_AUTH_ERROR,
        STATUS_API_NETWORK_ERROR,
        STATUS_API_RATE_LIMIT,
        STATUS_API_PARAM_ERROR,
        STATUS_API_SERVER_ERROR,
        STATUS_UNKNOWN_API_ERROR,
    ]
    for item in priority:
        if item in classifications:
            return item
    return classifications[0]


def _classify_blocked_reasons(blocked: list[str]) -> str:
    for classification in (
        STATUS_API_AUTH_ERROR,
        STATUS_API_NETWORK_ERROR,
        STATUS_API_RATE_LIMIT,
        STATUS_API_PARAM_ERROR,
        STATUS_API_SERVER_ERROR,
        STATUS_DATA_FRESHNESS_BLOCKED,
        STATUS_UNKNOWN_API_ERROR,
    ):
        if classification in blocked:
            return classification
    if any("api_fetch_failed" in item for item in blocked):
        return STATUS_UNKNOWN_API_ERROR
    if "data_until_before_decision_for" in blocked:
        return STATUS_DATA_FRESHNESS_BLOCKED
    return ""


def _next_action(classification: str, blocked: list[str]) -> str:
    if classification == STATUS_API_NETWORK_ERROR:
        return "check_network_connectivity"
    if classification == STATUS_API_AUTH_ERROR:
        return "refresh_token"
    if classification == STATUS_API_RATE_LIMIT:
        return "retry_later"
    if classification == STATUS_API_PARAM_ERROR:
        return "review_api_parameters"
    if classification == STATUS_API_SERVER_ERROR:
        return "check_api_status"
    if classification == STATUS_DATA_FRESHNESS_BLOCKED or "data_until_before_decision_for" in blocked:
        return "retry_later"
    if classification == STATUS_MARKET_DATA_NOT_YET_AVAILABLE:
        return "retry_later"
    if classification == STATUS_UNKNOWN_API_ERROR:
        return "check_api_status"
    return ""
