from __future__ import annotations

from collections import Counter
import math
from dataclasses import asdict, dataclass, field
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
    row_classification_summary: dict[str, Any] = field(default_factory=dict)

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
    if endpoint_name == "daily_quotes":
        return _validate_daily_quotes(records, schema)

    missing_required = {field: 0 for field in schema.required_fields}
    missing_key_count = 0
    type_warning_count = 0
    keys: list[tuple[str, ...]] = []

    for record in records:
        for field in schema.required_fields:
            if _is_missing_value(record.get(field)):
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


def _validate_daily_quotes(records: list[dict[str, Any]], schema: RawSchema) -> ValidationResult:
    raw_fields = ("O", "H", "L", "C", "Vo")
    adjusted_fields = ("AdjO", "AdjH", "AdjL", "AdjC", "AdjVo")
    price_fields = raw_fields + adjusted_fields
    row_classes = {
        "VALID_PRICE_ROW": 0,
        "VALID_NO_PRICE_ROW": 0,
        "PARTIAL_OHLCV_CORRUPTION": 0,
        "INVALID_NUMERIC_ROW": 0,
        "SCHEMA_CORRUPTION": 0,
    }
    missing_required = {field: 0 for field in schema.required_fields}
    missing_key_count = 0
    type_warning_count = 0
    keys: list[tuple[str, ...]] = []
    affected_dates: set[str] = set()
    affected_codes: set[str] = set()
    reason_counts: Counter[str] = Counter()

    for record in records:
        key_values = _schema_key_values("daily_quotes", schema, record)
        date_value = str(record.get("Date") or "")
        code_value = str(record.get("Code") or "")
        if date_value:
            affected_dates.add(date_value)
        if code_value:
            affected_codes.add(code_value)
        identity_missing = any(not value for value in key_values)
        if identity_missing:
            missing_key_count += 1
            reason_counts["identity_fields_missing"] += 1
        else:
            keys.append(key_values)
        type_warning_count += _type_warnings(schema, record)

        classification, reasons = _classify_daily_quote_price_row(record)
        if identity_missing:
            classification = "SCHEMA_CORRUPTION"
        row_classes[classification] += 1
        reason_counts.update(reasons)

        if classification in {"PARTIAL_OHLCV_CORRUPTION", "SCHEMA_CORRUPTION"}:
            for field in schema.required_fields:
                if _is_missing_value(record.get(field)):
                    missing_required[field] += 1
        elif classification == "INVALID_NUMERIC_ROW":
            # Keep identity fields strict while reporting price/value defects through the row classification.
            for field in ("Date", "Code"):
                if _is_missing_value(record.get(field)):
                    missing_required[field] += 1

    missing_required = {field: count for field, count in missing_required.items() if count}
    duplicate_key_count = sum(count - 1 for count in Counter(keys).values() if count > 1)
    invalid_count = (
        row_classes["PARTIAL_OHLCV_CORRUPTION"]
        + row_classes["INVALID_NUMERIC_ROW"]
        + row_classes["SCHEMA_CORRUPTION"]
    )
    messages: list[str] = []
    if missing_required:
        messages.append("required fields are missing")
    if missing_key_count:
        messages.append("business key fields are missing")
    if duplicate_key_count:
        messages.append("duplicate business keys detected")
    if row_classes["VALID_NO_PRICE_ROW"]:
        messages.append("source-valid no-price rows present")
    if row_classes["PARTIAL_OHLCV_CORRUPTION"]:
        messages.append("partial OHLCV corruption detected")
    if row_classes["INVALID_NUMERIC_ROW"]:
        messages.append("invalid OHLCV numeric values detected")
    if row_classes["SCHEMA_CORRUPTION"]:
        messages.append("schema corruption detected")
    if type_warning_count:
        messages.append("type normalization warnings detected")

    status = "OK"
    if invalid_count or missing_key_count:
        status = "ERROR"
    elif duplicate_key_count or type_warning_count or row_classes["VALID_NO_PRICE_ROW"]:
        status = "WARNING"

    classification_summary = {
        "valid_price_row_count": row_classes["VALID_PRICE_ROW"],
        "valid_no_price_row_count": row_classes["VALID_NO_PRICE_ROW"],
        "partial_ohlcv_corruption_count": row_classes["PARTIAL_OHLCV_CORRUPTION"],
        "invalid_numeric_row_count": row_classes["INVALID_NUMERIC_ROW"],
        "schema_corruption_count": row_classes["SCHEMA_CORRUPTION"],
        "affected_dates": sorted(affected_dates),
        "affected_codes": sorted(affected_codes),
        "source_null_policy": "raw_source_faithful_valid_no_price_rows_are_not_canonical_price_rows",
        "endpoint_validation_status": status,
        "reason_counts": dict(sorted(reason_counts.items())),
        "price_field_groups": {
            "raw": list(raw_fields),
            "adjusted": list(adjusted_fields),
        },
    }
    return ValidationResult(
        endpoint="daily_quotes",
        schema_version=schema.schema_version,
        status=status,
        record_count=len(records),
        missing_required_fields=missing_required,
        missing_key_count=missing_key_count,
        duplicate_key_count=duplicate_key_count,
        type_warning_count=type_warning_count,
        messages=messages,
        row_classification_summary=classification_summary,
    )


def _classify_daily_quote_price_row(record: dict[str, Any]) -> tuple[str, list[str]]:
    raw_fields = ("O", "H", "L", "C", "Vo")
    adjusted_fields = ("AdjO", "AdjH", "AdjL", "AdjC", "AdjVo")
    raw_state = _field_group_state(record, raw_fields)
    adjusted_state = _field_group_state(record, adjusted_fields)
    if raw_state == "all_missing" and adjusted_state == "all_missing":
        return "VALID_NO_PRICE_ROW", ["source_valid_no_price_row"]
    if raw_state == "partial" or adjusted_state == "partial":
        return "PARTIAL_OHLCV_CORRUPTION", ["partial_ohlcv_field_group"]
    usable_fields: tuple[str, ...] | None = None
    source = ""
    if adjusted_state == "complete":
        usable_fields = adjusted_fields
        source = "adjusted"
    elif raw_state == "complete":
        usable_fields = raw_fields
        source = "raw"
    if not usable_fields:
        return "PARTIAL_OHLCV_CORRUPTION", ["no_complete_price_field_group"]
    numeric_reasons = _daily_quote_numeric_reasons(record, usable_fields)
    if numeric_reasons:
        return "INVALID_NUMERIC_ROW", numeric_reasons
    return "VALID_PRICE_ROW", [f"valid_{source}_price_row"]


def _field_group_state(record: dict[str, Any], fields: tuple[str, ...]) -> str:
    present = [not _is_missing_value(record.get(field)) for field in fields]
    if all(present):
        return "complete"
    if any(present):
        return "partial"
    return "all_missing"


def _daily_quote_numeric_reasons(record: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    values: dict[str, float] = {}
    reasons: list[str] = []
    for field in fields:
        value = _finite_float(record.get(field))
        if value is None:
            reasons.append(f"{field}_not_finite_numeric")
            continue
        values[field] = value
    if reasons:
        return reasons
    open_value, high_value, low_value, close_value, volume_value = (values[field] for field in fields)
    if open_value < 0 or high_value < 0 or low_value < 0 or close_value < 0:
        reasons.append("negative_price")
    if volume_value < 0:
        reasons.append("negative_volume")
    if high_value < open_value or high_value < close_value or low_value > open_value or low_value > close_value or high_value < low_value:
        reasons.append("ohlc_relationship_invalid")
    return reasons


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value == ""
    try:
        return bool(math.isnan(value))  # pandas/pyarrow nulls can arrive as float NaN.
    except TypeError:
        return False


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
