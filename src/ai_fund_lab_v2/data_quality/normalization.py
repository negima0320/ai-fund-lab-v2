from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import RAW_COLLECTIONS
from ai_fund_lab_v2.data_store import create_storage_backend, validate_records
from ai_fund_lab_v2.runtime import RuntimePaths

DAILY_QUOTES_ENDPOINT = "/v2/equities/bars/daily"
DAILY_QUOTES_NORMALIZED_ENDPOINT = "daily_quotes_normalized"
DAILY_QUOTES_NORMALIZED_COLLECTION = "jquants/equities_bars_daily"
RAW_SCHEMA_VERSION = 1
NORMALIZED_SCHEMA_VERSION = 2

ADJUSTED_FIELDS = ("AdjO", "AdjH", "AdjL", "AdjC", "AdjVo")
UNADJUSTED_FIELDS = ("O", "H", "L", "C", "Vo")
NORMALIZED_FIELDS = ("Open", "High", "Low", "Close", "Volume")


@dataclass(frozen=True)
class NormalizationReport:
    endpoint_name: str
    input_record_count: int
    output_record_count: int
    adjusted_count: int
    unadjusted_count: int
    error_count: int
    warning_count: int
    duplicate_key_count: int
    status: str
    affected_dates: list[str]
    affected_codes: list[str]
    sample_errors: list[str]
    sample_warnings: list[str]
    field_mapping: dict[str, str]
    validation_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_daily_quotes(records: list[dict[str, Any]], limit_errors: int = 20) -> tuple[list[dict[str, Any]], NormalizationReport]:
    normalized_records: list[dict[str, Any]] = []
    adjusted_count = 0
    unadjusted_count = 0
    warning_count = 0
    sample_errors: list[str] = []
    sample_warnings: list[str] = []

    for index, record in enumerate(records):
        source_fields: tuple[str, ...] | None = None
        price_source = ""
        if _has_all(record, ADJUSTED_FIELDS):
            source_fields = ADJUSTED_FIELDS
            price_source = "adjusted"
        elif _has_all(record, UNADJUSTED_FIELDS):
            source_fields = UNADJUSTED_FIELDS
            price_source = "unadjusted"

        date = str(record.get("Date") or record.get("target_date") or "")
        code = str(record.get("Code") or record.get("code") or "")
        if not source_fields or not date or not code:
            if len(sample_errors) < limit_errors:
                missing = _missing_reason(record)
                sample_errors.append(f"record={index} date={date or '(missing)'} code={code or '(missing)'} {missing}")
            continue
        if price_source == "adjusted":
            adjusted_count += 1
        else:
            unadjusted_count += 1

        normalized = {
            "Date": date,
            "Code": code,
            "Open": record.get(source_fields[0]),
            "High": record.get(source_fields[1]),
            "Low": record.get(source_fields[2]),
            "Close": record.get(source_fields[3]),
            "Volume": record.get(source_fields[4]),
            "PriceSource": price_source,
            "SchemaVersion": NORMALIZED_SCHEMA_VERSION,
            "source_endpoint": DAILY_QUOTES_ENDPOINT,
            "target_date": date,
            "code": code,
            "business_key": code,
            "endpoint": DAILY_QUOTES_NORMALIZED_ENDPOINT,
            "source": "jquants",
        }
        zero_fields = _zero_fields(normalized)
        if zero_fields:
            warning_count += len(zero_fields)
            if len(sample_warnings) < limit_errors:
                sample_warnings.append(f"date={date} code={code} zero_fields={','.join(zero_fields)}")
        normalized_records.append(normalized)

    duplicate_key_count = _duplicate_key_count(normalized_records)
    validation = validate_records(DAILY_QUOTES_NORMALIZED_ENDPOINT, normalized_records)
    status = "ERROR" if len(records) != len(normalized_records) else validation.status
    report = NormalizationReport(
        endpoint_name=DAILY_QUOTES_NORMALIZED_ENDPOINT,
        input_record_count=len(records),
        output_record_count=len(normalized_records),
        adjusted_count=adjusted_count,
        unadjusted_count=unadjusted_count,
        error_count=len(records) - len(normalized_records),
        warning_count=warning_count,
        duplicate_key_count=duplicate_key_count,
        status=status,
        affected_dates=sorted({str(record.get("Date")) for record in normalized_records if record.get("Date")}),
        affected_codes=sorted({str(record.get("Code")) for record in normalized_records if record.get("Code")}),
        sample_errors=sample_errors,
        sample_warnings=sample_warnings,
        field_mapping={
            "Open": "AdjO if complete else O",
            "High": "AdjH if complete else H",
            "Low": "AdjL if complete else L",
            "Close": "AdjC if complete else C",
            "Volume": "AdjVo if complete else Vo",
            "PriceSource": "adjusted/unadjusted",
        },
        validation_status=validation.status,
    )
    return normalized_records, report


def read_daily_quotes_raw(paths: RuntimePaths, input_format: str) -> tuple[list[dict[str, Any]], str, Path]:
    storage_format = resolve_input_format(paths, input_format)
    backend = create_storage_backend(storage_format)
    path = backend.path_for(paths.raw_data / RAW_COLLECTIONS["daily_quotes"] / "data")
    return backend.read_records(path), storage_format, path


def write_daily_quotes_normalized(paths: RuntimePaths, output_format: str, records: list[dict[str, Any]]) -> Path:
    backend = create_storage_backend(output_format)
    path = normalized_output_path(paths, output_format)
    backend.write_records(path, records)
    return path


def normalized_output_path(paths: RuntimePaths, output_format: str) -> Path:
    backend = create_storage_backend(output_format)
    return backend.path_for(paths.raw_normalized_data / DAILY_QUOTES_NORMALIZED_COLLECTION / "data")


def resolve_input_format(paths: RuntimePaths, input_format: str) -> str:
    if input_format != "auto":
        return input_format
    parquet_path = create_storage_backend("parquet").path_for(paths.raw_data / RAW_COLLECTIONS["daily_quotes"] / "data")
    jsonl_path = create_storage_backend("jsonl").path_for(paths.raw_data / RAW_COLLECTIONS["daily_quotes"] / "data")
    if parquet_path.exists():
        return "parquet"
    if jsonl_path.exists():
        return "jsonl"
    return "jsonl"


def _has_all(record: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return all(record.get(field) not in (None, "") for field in fields)


def _missing_reason(record: dict[str, Any]) -> str:
    missing_adjusted = [field for field in ADJUSTED_FIELDS if record.get(field) in (None, "")]
    missing_unadjusted = [field for field in UNADJUSTED_FIELDS if record.get(field) in (None, "")]
    missing_key = [field for field in ("Date", "Code") if record.get(field) in (None, "")]
    parts = []
    if missing_key:
        parts.append(f"missing_key={','.join(missing_key)}")
    parts.append(f"missing_adjusted={','.join(missing_adjusted) or '(none)'}")
    parts.append(f"missing_unadjusted={','.join(missing_unadjusted) or '(none)'}")
    return " ".join(parts)


def _zero_fields(record: dict[str, Any]) -> list[str]:
    fields = []
    for field in NORMALIZED_FIELDS:
        try:
            if float(record.get(field)) == 0.0:
                fields.append(field)
        except (TypeError, ValueError):
            continue
    return fields


def _duplicate_key_count(records: list[dict[str, Any]]) -> int:
    keys = [(str(record.get("Date")), str(record.get("Code"))) for record in records if record.get("Date") and record.get("Code")]
    return sum(count - 1 for count in Counter(keys).values() if count > 1)
