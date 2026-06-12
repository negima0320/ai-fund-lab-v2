from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.data_quality.fetch_plan import FetchPlanBuilder
from ai_fund_lab_v2.data_quality.normalization import DAILY_QUOTES_NORMALIZED_COLLECTION, DAILY_QUOTES_NORMALIZED_ENDPOINT
from ai_fund_lab_v2.data_quality.trading_calendar import iter_dates
from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import ENDPOINT_PATHS, RAW_COLLECTIONS
from ai_fund_lab_v2.data_store import MarketDataStore, create_storage_backend, manifest_path, read_manifest, validate_records
from ai_fund_lab_v2.runtime import RuntimePaths


@dataclass(frozen=True)
class QualityReport:
    endpoint_name: str
    expected_dates: list[str]
    fetched_dates: list[str]
    missing_dates: list[str]
    empty_dates: list[str]
    duplicate_key_count: int
    record_count: int
    status: str
    validation: dict[str, Any]
    schema_version: int
    latest_manifest: dict[str, Any] | None
    storage_count_mismatch: bool
    normalized: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RawQualityChecker:
    store: MarketDataStore
    paths: RuntimePaths
    fetch_plan_builder: FetchPlanBuilder

    def check(self, endpoint_name: str, from_date: str, to_date: str) -> QualityReport:
        expected_dates = self._expected_dates(endpoint_name, from_date, to_date)
        records = self.store.read_raw_collection(RAW_COLLECTIONS[endpoint_name])
        fetched_dates = sorted({str(record.get("target_date")) for record in records if record.get("target_date")})
        missing_dates = [day for day in expected_dates if day not in fetched_dates]
        empty_dates = list(missing_dates)
        duplicate_key_count = self._duplicate_key_count(records)
        validation = validate_records(endpoint_name, records).to_dict()
        latest_manifest = self._latest_manifest(endpoint_name)
        storage_count_mismatch = self._storage_count_mismatch(endpoint_name)
        status = self._status(endpoint_name, missing_dates, duplicate_key_count, validation["status"], storage_count_mismatch)
        normalized = self._normalized_summary(endpoint_name)
        return QualityReport(
            endpoint_name=endpoint_name,
            expected_dates=expected_dates,
            fetched_dates=fetched_dates,
            missing_dates=missing_dates,
            empty_dates=empty_dates,
            duplicate_key_count=duplicate_key_count,
            record_count=len(records),
            status=status,
            validation=validation,
            schema_version=int(validation["schema_version"]),
            latest_manifest=latest_manifest,
            storage_count_mismatch=storage_count_mismatch,
            normalized=normalized,
        )

    def check_many(self, endpoint_name: str, from_date: str, to_date: str) -> list[QualityReport]:
        endpoint_names = list(ENDPOINT_PATHS) if endpoint_name == "all" else [endpoint_name]
        return [self.check(name, from_date, to_date) for name in endpoint_names]

    def save_reports(self, reports: list[QualityReport], output: str) -> tuple[Path | None, Path | None]:
        report_dir = self.paths.reports / "jquants_raw_quality"
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        json_path: Path | None = None
        markdown_path: Path | None = None
        if output in ("json", "both"):
            json_path = report_dir / f"quality_{stamp}.json"
            json_path.write_text(json.dumps([report.to_dict() for report in reports], ensure_ascii=False, indent=2), encoding="utf-8")
        if output in ("markdown", "both"):
            markdown_path = report_dir / f"quality_{stamp}.md"
            markdown_path.write_text(render_markdown(reports), encoding="utf-8")
        return json_path, markdown_path

    def _expected_dates(self, endpoint_name: str, from_date: str, to_date: str) -> list[str]:
        if endpoint_name == "trading_calendar":
            return iter_dates(from_date, to_date)
        return [item.date for item in self.fetch_plan_builder.build_fetch_plan(endpoint_name, from_date, to_date) if item.date]

    def _duplicate_key_count(self, records: list[dict[str, Any]]) -> int:
        keys = [
            (
                str(record.get("target_date")),
                str(record.get("business_key") or record.get("code")),
                str(record.get("endpoint")),
            )
            for record in records
        ]
        return sum(count - 1 for count in Counter(keys).values() if count > 1)

    def _status(
        self,
        endpoint_name: str,
        missing_dates: list[str],
        duplicate_key_count: int,
        validation_status: str,
        storage_count_mismatch: bool,
    ) -> str:
        if validation_status == "ERROR":
            return "ERROR"
        if duplicate_key_count or validation_status == "WARNING" or storage_count_mismatch:
            return "WARNING"
        if endpoint_name == "fins_summary":
            return "OK"
        if missing_dates:
            return "WARNING"
        return "OK"

    def _latest_manifest(self, endpoint_name: str) -> dict[str, Any] | None:
        endpoint = ENDPOINT_PATHS[endpoint_name]
        rows = [row for row in read_manifest(manifest_path(self.paths.raw_data)) if row.get("endpoint") == endpoint]
        return rows[-1] if rows else None

    def _storage_count_mismatch(self, endpoint_name: str) -> bool:
        base_path = self.paths.raw_data / RAW_COLLECTIONS[endpoint_name] / "data"
        jsonl_records = create_storage_backend("jsonl").read_records(create_storage_backend("jsonl").path_for(base_path))
        parquet_records = create_storage_backend("parquet").read_records(create_storage_backend("parquet").path_for(base_path))
        return bool(jsonl_records and parquet_records and len(jsonl_records) != len(parquet_records))

    def _normalized_summary(self, endpoint_name: str) -> dict[str, Any] | None:
        if endpoint_name != "daily_quotes":
            return None
        base_path = self.paths.raw_normalized_data / DAILY_QUOTES_NORMALIZED_COLLECTION / "data"
        records: list[dict[str, Any]] = []
        storage_format = "missing"
        storage_path = ""
        for candidate in ("parquet", "jsonl"):
            backend = create_storage_backend(candidate)
            path = backend.path_for(base_path)
            if path.exists():
                storage_format = candidate
                storage_path = str(path)
                records = backend.read_records(path)
                break
        validation = validate_records(DAILY_QUOTES_NORMALIZED_ENDPOINT, records).to_dict() if records else None
        latest_normalized_manifest = self._latest_normalized_manifest()
        return {
            "endpoint_name": DAILY_QUOTES_NORMALIZED_ENDPOINT,
            "schema_version": 2,
            "record_count": len(records),
            "storage_format": storage_format,
            "storage_path": storage_path,
            "validation": validation,
            "latest_manifest": latest_normalized_manifest,
        }

    def _latest_normalized_manifest(self) -> dict[str, Any] | None:
        rows = [
            row
            for row in read_manifest(manifest_path(self.paths.raw_data))
            if row.get("event_type") == "NORMALIZED" and row.get("normalized_endpoint") == DAILY_QUOTES_NORMALIZED_ENDPOINT
        ]
        return rows[-1] if rows else None


def render_markdown(reports: list[QualityReport]) -> str:
    lines = ["# J-Quants Raw Quality Report", ""]
    lines.append("| endpoint | status | raw_schema | raw_validation | records | normalized_schema | normalized_validation | normalized_records | missing | empty | duplicates | storage_mismatch |")
    lines.append("| --- | --- | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |")
    for report in reports:
        normalized = report.normalized or {}
        normalized_validation = (normalized.get("validation") or {}).get("status", "(none)")
        lines.append(
            f"| {report.endpoint_name} | {report.status} | {report.schema_version} | {report.validation.get('status')} | {report.record_count} | "
            f"{normalized.get('schema_version', '(none)')} | {normalized_validation} | {normalized.get('record_count', 0)} | "
            f"{len(report.missing_dates)} | {len(report.empty_dates)} | {report.duplicate_key_count} | {report.storage_count_mismatch} |"
        )
    lines.append("")
    for report in reports:
        lines.append(f"## {report.endpoint_name}")
        lines.append(f"- expected_dates: {', '.join(report.expected_dates) or '(none)'}")
        lines.append(f"- fetched_dates: {', '.join(report.fetched_dates) or '(none)'}")
        lines.append(f"- missing_dates: {', '.join(report.missing_dates) or '(none)'}")
        lines.append(f"- empty_dates: {', '.join(report.empty_dates) or '(none)'}")
        lines.append(f"- validation_status: {report.validation.get('status')}")
        lines.append(f"- validation_messages: {', '.join(report.validation.get('messages', [])) or '(none)'}")
        lines.append(f"- schema_version: {report.schema_version}")
        if report.normalized:
            normalized_validation = report.normalized.get("validation") or {}
            lines.append(f"- normalized_schema_version: {report.normalized.get('schema_version')}")
            lines.append(f"- normalized_validation_status: {normalized_validation.get('status', '(none)')}")
            lines.append(f"- normalized_record_count: {report.normalized.get('record_count')}")
            lines.append(f"- normalized_storage_format: {report.normalized.get('storage_format')}")
        lines.append(f"- latest_manifest_storage_format: {(report.latest_manifest or {}).get('storage_format', '(none)')}")
        lines.append("")
    return "\n".join(lines)
