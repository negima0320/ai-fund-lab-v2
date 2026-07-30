from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RawSchema:
    endpoint_name: str
    schema_version: int
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...]
    key_fields: tuple[str, ...]
    date_field: str
    code_field: str | None
    allowed_empty_policy: str
    field_mapping: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class ValidationResult:
    endpoint: str
    schema_version: int
    status: str
    record_count: int
    missing_required_fields: dict[str, int]
    missing_key_count: int
    duplicate_key_count: int
    type_warning_count: int
    messages: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


RAW_SCHEMAS: dict[str, RawSchema] = {
    "daily_quotes": RawSchema(
        endpoint_name="daily_quotes",
        schema_version=1,
        required_fields=("Date", "Code", "O", "H", "L", "C", "Vo"),
        optional_fields=("AdjO", "AdjH", "AdjL", "AdjC", "AdjVo"),
        key_fields=("Date", "Code"),
        date_field="Date",
        code_field="Code",
        allowed_empty_policy="business_day_warning_non_business_day_ok",
        field_mapping={
            "Date": ("Date",),
            "Code": ("Code",),
            "O": ("O", "Open", "AdjustmentOpen", "AdjO"),
            "H": ("H", "High", "AdjustmentHigh", "AdjH"),
            "L": ("L", "Low", "AdjustmentLow", "AdjL"),
            "C": ("C", "Close", "AdjustmentClose", "AdjC"),
            "Vo": ("Vo", "Volume", "AdjustmentVolume", "AdjVo"),
            "AdjO": ("AdjO", "AdjustmentOpen"),
            "AdjH": ("AdjH", "AdjustmentHigh"),
            "AdjL": ("AdjL", "AdjustmentLow"),
            "AdjC": ("AdjC", "AdjustmentClose"),
            "AdjVo": ("AdjVo", "AdjustmentVolume"),
        },
    ),
    "listed_issues": RawSchema(
        endpoint_name="listed_issues",
        schema_version=1,
        required_fields=("Date", "Code", "CoName", "Mkt"),
        optional_fields=("CoNameEn", "MktNm", "S17", "S33"),
        key_fields=("Date", "Code"),
        date_field="Date",
        code_field="Code",
        allowed_empty_policy="snapshot_warning",
        field_mapping={
            "Date": ("Date",),
            "Code": ("Code",),
            "CoName": ("CoName", "CompanyName", "CompanyNameJapanese"),
            "Mkt": ("Mkt", "MarketCode"),
        },
    ),
    "earnings_calendar": RawSchema(
        endpoint_name="earnings_calendar",
        schema_version=1,
        required_fields=("Date", "Code"),
        optional_fields=(
            "CoName",
            "FY",
            "FQ",
            "Section",
            "SectorNm",
            "PublicationDate",
            "ScheduledDate",
            "TimePredicted",
            "SessionPredicted",
            "PublicationType",
        ),
        key_fields=("Date", "Code"),
        date_field="Date",
        code_field="Code",
        allowed_empty_policy="snapshot_warning",
        field_mapping={
            "Date": ("Date", "ScheduledDate", "scheduled_date"),
            "Code": ("Code", "LocalCode", "code"),
            "CoName": ("CoName", "CompanyName", "company_name"),
        },
    ),
    "trading_calendar": RawSchema(
        endpoint_name="trading_calendar",
        schema_version=1,
        required_fields=("Date", "HolDiv"),
        optional_fields=(),
        key_fields=("Date",),
        date_field="Date",
        code_field=None,
        allowed_empty_policy="range_warning",
        field_mapping={"Date": ("Date",), "HolDiv": ("HolDiv", "HolidayDivision")},
    ),
    "fins_summary": RawSchema(
        endpoint_name="fins_summary",
        schema_version=1,
        required_fields=("DiscDate", "Code"),
        optional_fields=("DiscNo", "DiscTime", "DocType", "TypeOfDocument", "CurPerType", "CurPerEn", "CurrentPeriodEndDate", "ForecastProfit"),
        key_fields=("DiscDate", "Code", "DiscNo"),
        date_field="DiscDate",
        code_field="Code",
        allowed_empty_policy="empty_ok",
        field_mapping={"DiscDate": ("DiscDate", "DisclosedDate"), "Code": ("Code", "LocalCode"), "DiscNo": ("DiscNo",)},
    ),
}

NORMALIZED_SCHEMAS: dict[str, RawSchema] = {
    "daily_quotes_normalized": RawSchema(
        endpoint_name="daily_quotes_normalized",
        schema_version=2,
        required_fields=("Date", "Code", "Open", "High", "Low", "Close", "Volume", "PriceSource", "SchemaVersion"),
        optional_fields=("source_endpoint",),
        key_fields=("Date", "Code"),
        date_field="Date",
        code_field="Code",
        allowed_empty_policy="normalized_prices_required_volume_zero_warning",
        field_mapping={
            "Date": ("Date",),
            "Code": ("Code",),
            "Open": ("AdjO", "O"),
            "High": ("AdjH", "H"),
            "Low": ("AdjL", "L"),
            "Close": ("AdjC", "C"),
            "Volume": ("AdjVo", "Vo"),
            "PriceSource": ("PriceSource",),
            "SchemaVersion": ("SchemaVersion",),
        },
    )
}


def validate_records(endpoint_name: str, records: list[dict[str, Any]]) -> ValidationResult:
    schema = RAW_SCHEMAS.get(endpoint_name) or NORMALIZED_SCHEMAS[endpoint_name]
    missing_required = {field: 0 for field in schema.required_fields}
    missing_key_count = 0
    type_warning_count = 0
    keys: list[tuple[str, ...]] = []

    for record in records:
        for field in schema.required_fields:
            if record.get(field) in (None, ""):
                missing_required[field] += 1
        key_values = _schema_key_values(endpoint_name, schema, record)
        if any(not value for value in key_values):
            missing_key_count += 1
        else:
            keys.append(key_values)
        type_warning_count += _type_warnings(schema, record)
        type_warning_count += _value_warnings(endpoint_name, record)

    missing_required = {field: count for field, count in missing_required.items() if count}
    duplicate_key_count = sum(count - 1 for count in Counter(keys).values() if count > 1)
    messages: list[str] = []
    if missing_required:
        messages.append("required fields are missing")
    if missing_key_count:
        messages.append("business key fields are missing")
    if duplicate_key_count:
        messages.append("duplicate business keys detected")
    if type_warning_count:
        messages.append("type normalization warnings detected")

    status = "OK"
    if missing_required or missing_key_count:
        status = "ERROR"
    elif duplicate_key_count or type_warning_count:
        status = "WARNING"

    return ValidationResult(
        endpoint=endpoint_name,
        schema_version=schema.schema_version,
        status=status,
        record_count=len(records),
        missing_required_fields=missing_required,
        missing_key_count=missing_key_count,
        duplicate_key_count=duplicate_key_count,
        type_warning_count=type_warning_count,
        messages=messages,
    )


def fins_summary_business_key(record: dict[str, Any]) -> str:
    key_values = _fins_summary_key_values(record)
    if any(key_values):
        return "fins_summary:" + ":".join(key_values)
    return ""


def _schema_key_values(endpoint_name: str, schema: RawSchema, record: dict[str, Any]) -> tuple[str, ...]:
    if endpoint_name == "fins_summary":
        return _fins_summary_key_values(record)
    return tuple(str(record.get(field) or "") for field in schema.key_fields)


def _fins_summary_key_values(record: dict[str, Any]) -> tuple[str, ...]:
    disc_date = str(record.get("DiscDate") or record.get("DisclosedDate") or record.get("target_date") or "")
    code = str(record.get("Code") or record.get("LocalCode") or record.get("code") or "")
    disc_no = str(record.get("DiscNo") or "")
    if disc_date and code and disc_no:
        return (disc_date, code, disc_no)

    fallback = [
        ("DiscTime", str(record.get("DiscTime") or record.get("DisclosedTime") or "")),
        ("DocType", str(record.get("DocType") or record.get("TypeOfDocument") or "")),
        ("CurPerType", str(record.get("CurPerType") or "")),
        ("CurPerSt", str(record.get("CurPerSt") or "")),
        ("CurPerEn", str(record.get("CurPerEn") or record.get("CurrentPeriodEndDate") or "")),
        ("CurFYSt", str(record.get("CurFYSt") or "")),
        ("CurFYEn", str(record.get("CurFYEn") or "")),
    ]
    fallback_values = tuple(f"{name}={value}" for name, value in fallback if value)
    if disc_date and code and fallback_values:
        return (disc_date, code, *fallback_values)
    return (disc_date, code)


def _type_warnings(schema: RawSchema, record: dict[str, Any]) -> int:
    warnings = 0
    if record.get(schema.date_field) is not None and not isinstance(record.get(schema.date_field), str):
        warnings += 1
    if schema.code_field and record.get(schema.code_field) is not None and not isinstance(record.get(schema.code_field), str):
        warnings += 1
    return warnings


def _value_warnings(endpoint_name: str, record: dict[str, Any]) -> int:
    if endpoint_name != "daily_quotes_normalized":
        return 0
    warnings = 0
    # Zero prices/volume can appear in real market data edge cases, but should be inspected before feature use.
    for field in ("Open", "High", "Low", "Close", "Volume"):
        try:
            if record.get(field) == 0 or float(record.get(field)) == 0.0:
                warnings += 1
        except (TypeError, ValueError):
            continue
    return warnings
