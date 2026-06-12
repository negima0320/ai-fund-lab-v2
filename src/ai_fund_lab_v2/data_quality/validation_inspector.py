from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import RAW_COLLECTIONS
from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.data_store.schema import RAW_SCHEMAS, validate_records


@dataclass(frozen=True)
class ValidationInspection:
    endpoint_name: str
    schema_version: int
    validation_status: str
    record_count: int
    missing_required_fields: dict[str, int]
    missing_key_count: int
    duplicate_key_count: int
    type_warning_count: int
    problem_record_sample: list[dict[str, Any]]
    affected_dates: list[str]
    affected_codes: list[str]
    field_mapping: dict[str, tuple[str, ...]]
    mapping_hints: dict[str, dict[str, Any]]
    suggested_fix: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint_name,
            "schema_version": self.schema_version,
            "validation_status": self.validation_status,
            "record_count": self.record_count,
            "missing_required_fields": self.missing_required_fields,
            "missing_key_count": self.missing_key_count,
            "duplicate_key_count": self.duplicate_key_count,
            "type_warning_count": self.type_warning_count,
            "problem_record_sample": self.problem_record_sample,
            "affected_dates": self.affected_dates,
            "affected_codes": self.affected_codes,
            "field_mapping": {key: list(value) for key, value in self.field_mapping.items()},
            "mapping_hints": self.mapping_hints,
            "suggested_fix": self.suggested_fix,
        }


def inspect_validation(store: MarketDataStore, endpoint_name: str, *, limit: int = 20, target_date: str | None = None) -> ValidationInspection:
    schema = RAW_SCHEMAS[endpoint_name]
    records = store.read_raw_collection(RAW_COLLECTIONS[endpoint_name])
    if target_date:
        records = [record for record in records if str(record.get("target_date") or record.get(schema.date_field)) == target_date]
    validation = validate_records(endpoint_name, records)

    sample: list[dict[str, Any]] = []
    affected_dates = set()
    affected_codes = set()
    for record in records:
        missing_required = [field for field in schema.required_fields if record.get(field) in (None, "")]
        missing_key = any(record.get(field) in (None, "") for field in schema.key_fields)
        if not missing_required and not missing_key:
            continue
        affected_dates.add(str(record.get("target_date") or record.get(schema.date_field) or ""))
        if schema.code_field:
            affected_codes.add(str(record.get("code") or record.get(schema.code_field) or ""))
        if len(sample) < limit:
            sample.append(redact_record(record))

    mapping_hints = build_mapping_hints(records, endpoint_name)
    return ValidationInspection(
        endpoint_name=endpoint_name,
        schema_version=schema.schema_version,
        validation_status=validation.status,
        record_count=validation.record_count,
        missing_required_fields=validation.missing_required_fields,
        missing_key_count=validation.missing_key_count,
        duplicate_key_count=validation.duplicate_key_count,
        type_warning_count=validation.type_warning_count,
        problem_record_sample=sample,
        affected_dates=sorted(day for day in affected_dates if day),
        affected_codes=sorted(code for code in affected_codes if code)[:limit],
        field_mapping=schema.field_mapping,
        mapping_hints=mapping_hints,
        suggested_fix=suggested_fix(endpoint_name, validation.missing_required_fields, mapping_hints),
    )


def build_mapping_hints(records: list[dict[str, Any]], endpoint_name: str) -> dict[str, dict[str, Any]]:
    schema = RAW_SCHEMAS[endpoint_name]
    hints: dict[str, dict[str, Any]] = {}
    for required, candidates in schema.field_mapping.items():
        candidate_counts = {candidate: sum(1 for record in records if record.get(candidate) not in (None, "")) for candidate in candidates}
        hints[required] = {"candidates": list(candidates), "non_empty_counts": candidate_counts}
    return hints


def suggested_fix(endpoint_name: str, missing_required_fields: dict[str, int], mapping_hints: dict[str, dict[str, Any]]) -> str:
    if not missing_required_fields:
        return "No schema fix needed."
    usable_alternatives = []
    for field in missing_required_fields:
        counts = mapping_hints.get(field, {}).get("non_empty_counts", {})
        usable = [name for name, count in counts.items() if name != field and count > 0]
        if usable:
            usable_alternatives.append(f"{field}: consider mapping from {', '.join(usable)}")
    if usable_alternatives:
        return "; ".join(usable_alternatives)
    if endpoint_name == "daily_quotes":
        return "Daily quotes contain null required OHLCV values; keep schema strict and refetch or inspect upstream missing values."
    return "Inspect upstream raw records and decide whether schema_version should be incremented."


def redact_record(record: dict[str, Any]) -> dict[str, Any]:
    blocked = {"api_key", "token", "authorization", "x-api-key", "password", "id_token", "refresh_token"}
    return {key: value for key, value in record.items() if key.lower() not in blocked}
