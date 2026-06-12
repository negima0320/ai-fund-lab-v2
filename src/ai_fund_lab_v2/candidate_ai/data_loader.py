from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping


LOADER_VERSION = "candidate_real_data_loader_contract_v1"
LOADER_SCHEMA_VERSION = "daily_quotes_normalized_to_candidate_input_v1"

STANDARD_INPUT_COLUMNS = ("date", "code", "open", "high", "low", "close", "volume")

DAILY_QUOTES_NORMALIZED_COLUMN_MAPPING = {
    "Date": "date",
    "Code": "code",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
}


@dataclass(frozen=True)
class CandidateLoaderValidationResult:
    is_valid: bool
    missing_required_fields: dict[str, int] = field(default_factory=dict)
    invalid_code_count: int = 0
    missing_close_count: int = 0
    missing_volume_count: int = 0
    non_numeric_value_count: int = 0
    future_row_count: int = 0
    messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateRealDataLoaderAudit:
    status: str
    as_of_date: str
    source_snapshot_id: str
    input_source_path: str | None
    input_manifest_path: str | None
    input_row_count: int
    filtered_row_count: int
    dropped_future_row_count: int
    invalid_row_count: int
    input_hash_optional: str | None
    schema_version: str
    loader_version: str
    validation: CandidateLoaderValidationResult
    messages: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "as_of_date": self.as_of_date,
            "source_snapshot_id": self.source_snapshot_id,
            "input_source_path": self.input_source_path,
            "input_manifest_path": self.input_manifest_path,
            "input_row_count": self.input_row_count,
            "filtered_row_count": self.filtered_row_count,
            "dropped_future_row_count": self.dropped_future_row_count,
            "invalid_row_count": self.invalid_row_count,
            "input_hash_optional": self.input_hash_optional,
            "schema_version": self.schema_version,
            "loader_version": self.loader_version,
            "validation": {
                "is_valid": self.validation.is_valid,
                "missing_required_fields": dict(self.validation.missing_required_fields),
                "invalid_code_count": self.validation.invalid_code_count,
                "missing_close_count": self.validation.missing_close_count,
                "missing_volume_count": self.validation.missing_volume_count,
                "non_numeric_value_count": self.validation.non_numeric_value_count,
                "future_row_count": self.validation.future_row_count,
                "messages": list(self.validation.messages),
            },
            "messages": list(self.messages),
        }


@dataclass(frozen=True)
class CandidateRealDataLoaderResult:
    rows: list[dict[str, Any]]
    audit: CandidateRealDataLoaderAudit


def adapt_daily_quotes_normalized(
    records: Iterable[Mapping[str, Any]],
    *,
    as_of_date: str,
    lookback_rows: int = 80,
    source_snapshot_id: str | None = None,
    input_source_path: Path | str | None = None,
    input_manifest_path: Path | str | None = None,
    input_hash_optional: str | None = None,
) -> CandidateRealDataLoaderResult:
    materialized_records = [dict(record) for record in records]
    validation = validate_daily_quotes_normalized_input(materialized_records, as_of_date=as_of_date)
    valid_visible_rows: list[dict[str, Any]] = []
    dropped_future_row_count = 0
    invalid_row_count = 0

    for record in materialized_records:
        row_date = str(record.get("Date") or "")
        if row_date > as_of_date:
            dropped_future_row_count += 1
            continue
        if not _input_record_is_valid(record):
            invalid_row_count += 1
            continue
        valid_visible_rows.append(_map_record(record))

    rows = _tail_by_code(valid_visible_rows, lookback_rows=lookback_rows)
    audit = CandidateRealDataLoaderAudit(
        status="OK" if validation.is_valid and dropped_future_row_count == 0 else "WARNING",
        as_of_date=as_of_date,
        source_snapshot_id=source_snapshot_id or build_source_snapshot_id(materialized_records, as_of_date=as_of_date),
        input_source_path=str(input_source_path) if input_source_path is not None else None,
        input_manifest_path=str(input_manifest_path) if input_manifest_path is not None else None,
        input_row_count=len(materialized_records),
        filtered_row_count=len(rows),
        dropped_future_row_count=dropped_future_row_count,
        invalid_row_count=invalid_row_count,
        input_hash_optional=input_hash_optional or hash_records_optional(materialized_records),
        schema_version=LOADER_SCHEMA_VERSION,
        loader_version=LOADER_VERSION,
        validation=validation,
        messages=_audit_messages(validation, dropped_future_row_count=dropped_future_row_count),
    )
    return CandidateRealDataLoaderResult(rows=rows, audit=audit)


def validate_daily_quotes_normalized_input(
    records: Iterable[Mapping[str, Any]],
    *,
    as_of_date: str,
) -> CandidateLoaderValidationResult:
    rows = [dict(record) for record in records]
    missing_required = {field: 0 for field in DAILY_QUOTES_NORMALIZED_COLUMN_MAPPING}
    invalid_code_count = 0
    missing_close_count = 0
    missing_volume_count = 0
    non_numeric_value_count = 0
    future_row_count = 0

    for record in rows:
        for field in DAILY_QUOTES_NORMALIZED_COLUMN_MAPPING:
            if record.get(field) in (None, ""):
                missing_required[field] += 1
        if str(record.get("Date") or "") > as_of_date:
            future_row_count += 1
            continue
        if not str(record.get("Code") or "").strip():
            invalid_code_count += 1
        if record.get("Close") in (None, ""):
            missing_close_count += 1
        if record.get("Volume") in (None, ""):
            missing_volume_count += 1
        for field in ("Open", "High", "Low", "Close", "Volume"):
            if record.get(field) in (None, ""):
                continue
            if not _is_numeric(record.get(field)):
                non_numeric_value_count += 1

    missing_required = {field: count for field, count in missing_required.items() if count}
    is_valid = not (
        missing_required
        or invalid_code_count
        or missing_close_count
        or missing_volume_count
        or non_numeric_value_count
    )
    return CandidateLoaderValidationResult(
        is_valid=is_valid,
        missing_required_fields=missing_required,
        invalid_code_count=invalid_code_count,
        missing_close_count=missing_close_count,
        missing_volume_count=missing_volume_count,
        non_numeric_value_count=non_numeric_value_count,
        future_row_count=future_row_count,
        messages=_validation_messages(
            missing_required=missing_required,
            invalid_code_count=invalid_code_count,
            missing_close_count=missing_close_count,
            missing_volume_count=missing_volume_count,
            non_numeric_value_count=non_numeric_value_count,
            future_row_count=future_row_count,
        ),
    )


def build_source_snapshot_id(records: Iterable[Mapping[str, Any]], *, as_of_date: str) -> str:
    digest = hash_records_optional(records) or "empty"
    return f"daily_quotes_normalized:{as_of_date}:{digest[:12]}"


def hash_records_optional(records: Iterable[Mapping[str, Any]]) -> str | None:
    rows = [dict(record) for record in records]
    if not rows:
        return None
    encoded = json.dumps(rows, ensure_ascii=True, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _map_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "date": str(record["Date"]),
        "code": str(record["Code"]),
        "open": float(record["Open"]),
        "high": float(record["High"]),
        "low": float(record["Low"]),
        "close": float(record["Close"]),
        "volume": float(record["Volume"]),
    }


def _tail_by_code(rows: list[dict[str, Any]], *, lookback_rows: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(rows, key=lambda item: (str(item["code"]), str(item["date"]))):
        grouped[str(row["code"])].append(row)
    output: list[dict[str, Any]] = []
    for code in sorted(grouped):
        output.extend(grouped[code][-lookback_rows:])
    return output


def _input_record_is_valid(record: Mapping[str, Any]) -> bool:
    if any(record.get(field) in (None, "") for field in DAILY_QUOTES_NORMALIZED_COLUMN_MAPPING):
        return False
    if not str(record.get("Code") or "").strip():
        return False
    return all(_is_numeric(record.get(field)) for field in ("Open", "High", "Low", "Close", "Volume"))


def _is_numeric(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _validation_messages(
    *,
    missing_required: dict[str, int],
    invalid_code_count: int,
    missing_close_count: int,
    missing_volume_count: int,
    non_numeric_value_count: int,
    future_row_count: int,
) -> tuple[str, ...]:
    messages: list[str] = []
    if missing_required:
        messages.append(f"missing required fields: {missing_required}")
    if invalid_code_count:
        messages.append(f"invalid code rows: {invalid_code_count}")
    if missing_close_count:
        messages.append(f"missing close rows: {missing_close_count}")
    if missing_volume_count:
        messages.append(f"missing volume rows: {missing_volume_count}")
    if non_numeric_value_count:
        messages.append(f"non numeric price/volume values: {non_numeric_value_count}")
    if future_row_count:
        messages.append(f"future rows will be dropped: {future_row_count}")
    return tuple(messages)


def _audit_messages(validation: CandidateLoaderValidationResult, *, dropped_future_row_count: int) -> tuple[str, ...]:
    messages = list(validation.messages)
    if dropped_future_row_count:
        messages.append(f"dropped future rows: {dropped_future_row_count}")
    if not messages:
        messages.append("daily_quotes_normalized adapter contract passed")
    return tuple(messages)
