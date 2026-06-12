from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_fund_lab_v2.data_sources.jquants.client import (
    JQUANTS_DAILY_QUOTES_ENDPOINT,
    JQUANTS_FINS_SUMMARY_ENDPOINT,
    JQUANTS_LISTED_ISSUES_ENDPOINT,
    JQUANTS_TRADING_CALENDAR_ENDPOINT,
    JQuantsClient,
)
from ai_fund_lab_v2.data_store.manifest import ManifestEntry, append_manifest, manifest_path, now_utc, sanitize_request_params
from ai_fund_lab_v2.data_store import MarketDataStore, create_storage_backend
from ai_fund_lab_v2.logging import configure_runtime_logger
from ai_fund_lab_v2.runtime import RuntimePaths

RAW_COLLECTIONS = {
    "daily_quotes": "jquants/equities_bars_daily",
    "listed_issues": "jquants/listed_issues",
    "trading_calendar": "jquants/trading_calendar",
    "fins_summary": "jquants/fins_summary",
}

ENDPOINT_PATHS = {
    "daily_quotes": JQUANTS_DAILY_QUOTES_ENDPOINT,
    "listed_issues": JQUANTS_LISTED_ISSUES_ENDPOINT,
    "trading_calendar": JQUANTS_TRADING_CALENDAR_ENDPOINT,
    "fins_summary": JQUANTS_FINS_SUMMARY_ENDPOINT,
}


@dataclass(frozen=True)
class FetchResult:
    endpoint_name: str
    endpoint: str
    records_saved: int
    output_path: str
    validation_status: str = "UNKNOWN"
    diff_summary: dict[str, Any] | None = None


@dataclass
class JQuantsRawIngestor:
    client: JQuantsClient
    store: MarketDataStore
    paths: RuntimePaths

    def __post_init__(self) -> None:
        self.logger = configure_runtime_logger("ai_fund_lab_v2.jquants_ingestion", self.paths.logs, "jquants_ingestion.log")

    def fetch_and_store(
        self,
        endpoint_name: str,
        *,
        date: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        code: str | None = None,
        max_pages: int = 100,
    ) -> FetchResult:
        if endpoint_name == "daily_quotes":
            daily_from_date = None if date else from_date
            daily_to_date = None if date else to_date
            records = self.client.fetch_all_daily_quotes(
                date=date,
                from_date=daily_from_date,
                to_date=daily_to_date,
                code=code,
                max_pages=max_pages,
            )
        elif endpoint_name == "listed_issues":
            records = self.client.fetch_all_listed_issues(date=date, code=code, max_pages=max_pages)
        elif endpoint_name == "trading_calendar":
            calendar_date = None if from_date or to_date else date
            records = self.client.fetch_all_trading_calendar(
                date=calendar_date,
                from_date=from_date,
                to_date=to_date,
                max_pages=max_pages,
            )
        elif endpoint_name == "fins_summary":
            records = self.client.fetch_all_fins_summary(date=date, code=code, max_pages=max_pages)
        else:
            raise ValueError(f"Unsupported J-Quants endpoint: {endpoint_name}")

        if endpoint_name == "daily_quotes":
            self._log_daily_quote_missing(records, date=date, from_date=from_date, to_date=to_date)

        endpoint = ENDPOINT_PATHS[endpoint_name]
        save_result = self.store.save_raw_with_result(
            records,
            endpoint=endpoint,
            source="jquants",
            collection=RAW_COLLECTIONS[endpoint_name],
            default_target_date=date or from_date or to_date,
            endpoint_name=endpoint_name,
        )
        validation_status = save_result.validation_result.status if save_result.validation_result else "UNKNOWN"
        schema_version = save_result.validation_result.schema_version if save_result.validation_result else None
        diff_summary = save_result.diff_summary.to_dict()
        append_manifest(
            manifest_path(self.paths.raw_data),
            ManifestEntry(
                fetched_at=now_utc(),
                endpoint=endpoint,
                target_date=date,
                from_date=from_date,
                to_date=to_date,
                record_count=len(records),
                storage_format=save_result.storage_format,
                storage_path=str(save_result.path),
                status="OK",
                validation_status=validation_status,
                schema_version=schema_version,
                diff_summary=diff_summary,
                request_params=sanitize_request_params(
                    {
                        "endpoint_name": endpoint_name,
                        "date": date,
                        "from_date": from_date,
                        "to_date": to_date,
                        "code": code,
                        "max_pages": max_pages,
                    }
                ),
            ),
        )
        return FetchResult(endpoint_name, endpoint, len(records), str(save_result.path), validation_status, diff_summary)

    def _log_daily_quote_missing(
        self,
        records: list[dict[str, Any]],
        *,
        date: str | None,
        from_date: str | None,
        to_date: str | None,
    ) -> None:
        if records:
            return
        target = date or from_date or to_date or "unspecified"
        self.logger.warning(
            "J-Quants daily quotes returned no data target_date=%s note=missing_or_non_business_day",
            target,
        )


def raw_output_path(paths: RuntimePaths, endpoint_name: str, storage_format: str = "jsonl") -> str:
    return str(create_storage_backend(storage_format).path_for(paths.raw_data / RAW_COLLECTIONS[endpoint_name] / "data"))
