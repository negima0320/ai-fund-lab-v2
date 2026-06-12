from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from ai_fund_lab_v2.data_store.schema import ValidationResult, validate_records
from ai_fund_lab_v2.data_store.storage_backends import StorageBackend, create_storage_backend
from ai_fund_lab_v2.runtime.paths import RuntimePaths


class DataLayer(str, Enum):
    RAW = "raw"
    FEATURES = "features"
    LABELS = "labels"


@dataclass(frozen=True)
class DiffSummary:
    record_count_before: int
    record_count_after: int
    inserted_count: int
    updated_count: int
    unchanged_count: int
    deleted_or_missing_count: int
    duplicate_key_count: int
    changed_keys_sample: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_count_before": self.record_count_before,
            "record_count_after": self.record_count_after,
            "inserted_count": self.inserted_count,
            "updated_count": self.updated_count,
            "unchanged_count": self.unchanged_count,
            "deleted_or_missing_count": self.deleted_or_missing_count,
            "duplicate_key_count": self.duplicate_key_count,
            "changed_keys_sample": self.changed_keys_sample,
        }


@dataclass(frozen=True)
class SaveResult:
    path: Path
    storage_format: str
    diff_summary: DiffSummary
    validation_result: ValidationResult | None


@dataclass(frozen=True)
class MarketDataStore:
    """Local file store for Phase1 data.

    Upsert policy:
    records are unique by (target_date, business_key, endpoint). For stock data,
    business_key defaults to code. For code-less data, callers should provide a
    business_key or rely on target_date replacement.
    """

    paths: RuntimePaths
    raw_storage_format: str = "jsonl"
    backend: StorageBackend | None = None

    def save_raw(
        self,
        records: Iterable[dict[str, Any]],
        endpoint: str,
        source: str = "jquants",
        collection: str | None = None,
        default_target_date: str | None = None,
    ) -> Path:
        return self.save_raw_with_result(
            records,
            endpoint=endpoint,
            source=source,
            collection=collection,
            default_target_date=default_target_date,
        ).path

    def save_raw_with_result(
        self,
        records: Iterable[dict[str, Any]],
        endpoint: str,
        source: str = "jquants",
        collection: str | None = None,
        default_target_date: str | None = None,
        endpoint_name: str | None = None,
    ) -> SaveResult:
        return self.upsert(
            DataLayer.RAW,
            records,
            endpoint=endpoint,
            source=source,
            collection=collection,
            default_target_date=default_target_date,
            endpoint_name=endpoint_name,
        )

    def save_features(self, records: Iterable[dict[str, Any]], endpoint: str, source: str = "feature_builder") -> Path:
        return self.upsert(DataLayer.FEATURES, records, endpoint=endpoint, source=source).path

    def save_labels(self, records: Iterable[dict[str, Any]], endpoint: str, source: str = "label_builder") -> Path:
        return self.upsert(DataLayer.LABELS, records, endpoint=endpoint, source=source).path

    def upsert(
        self,
        layer: DataLayer,
        records: Iterable[dict[str, Any]],
        *,
        endpoint: str,
        source: str,
        collection: str | None = None,
        default_target_date: str | None = None,
        endpoint_name: str | None = None,
    ) -> SaveResult:
        output_path = self._path_for(layer, endpoint, collection=collection)
        existing = self._backend_for(layer).read_records(output_path)
        merged = {self._key(record): record for record in existing}

        fetched_at = datetime.now(timezone.utc).isoformat()
        normalized_records: list[dict[str, Any]] = []
        for record in records:
            normalized = self._normalize_record(
                record,
                endpoint=endpoint,
                source=source,
                fetched_at=fetched_at,
                default_target_date=default_target_date,
            )
            normalized_records.append(normalized)
            merged[self._key(normalized)] = normalized

        written = sorted(merged.values(), key=lambda item: self._key(item))
        self._backend_for(layer).write_records(output_path, written)
        validation = validate_records(endpoint_name, normalized_records) if endpoint_name else None
        return SaveResult(
            path=output_path,
            storage_format=self._backend_for(layer).format_name,
            diff_summary=self._diff(existing, normalized_records, written),
            validation_result=validation,
        )

    def read_layer(self, layer: DataLayer, endpoint: str) -> list[dict[str, Any]]:
        return self._backend_for(layer).read_records(self._path_for(layer, endpoint))

    def read_raw_collection(self, collection: str) -> list[dict[str, Any]]:
        return self._backend_for(DataLayer.RAW).read_records(self._path_for(DataLayer.RAW, "", collection=collection))

    def _path_for(self, layer: DataLayer, endpoint: str, collection: str | None = None) -> Path:
        safe_endpoint = endpoint.strip("/").replace("/", "__") or "unknown"
        base = {
            DataLayer.RAW: self.paths.raw_data,
            DataLayer.FEATURES: self.paths.feature_data,
            DataLayer.LABELS: self.paths.label_data,
        }[layer]
        if collection:
            return self._backend_for(layer).path_for(base / collection / "data")
        return self._backend_for(layer).path_for(base / safe_endpoint)

    def _normalize_record(
        self,
        record: dict[str, Any],
        *,
        endpoint: str,
        source: str,
        fetched_at: str,
        default_target_date: str | None,
    ) -> dict[str, Any]:
        normalized = dict(record)
        normalized["fetched_at"] = normalized.get("fetched_at") or fetched_at
        normalized["target_date"] = (
            normalized.get("target_date")
            or normalized.get("Date")
            or normalized.get("date")
            or normalized.get("DisclosedDate")
            or normalized.get("DiscDate")
            or default_target_date
        )
        normalized["code"] = str(normalized.get("code") or normalized.get("Code") or normalized.get("LocalCode") or "")
        normalized["business_key"] = str(
            normalized.get("business_key")
            or normalized.get("code")
            or normalized.get("Code")
            or normalized.get("LocalCode")
            or normalized.get("Date")
            or normalized.get("date")
            or normalized.get("DisclosedDate")
            or normalized.get("DiscDate")
            or normalized.get("target_date")
            or ""
        )
        normalized["source"] = normalized.get("source") or source
        normalized["endpoint"] = normalized.get("endpoint") or endpoint

        missing = [name for name in ("target_date", "business_key", "source", "endpoint") if not normalized.get(name)]
        if missing:
            raise ValueError(f"Market data record is missing required metadata: {', '.join(missing)}")
        return normalized

    def _key(self, record: dict[str, Any]) -> tuple[str, str, str]:
        return (str(record["target_date"]), str(record["business_key"]), str(record["endpoint"]))

    def _backend_for(self, layer: DataLayer) -> StorageBackend:
        if layer == DataLayer.RAW:
            return self.backend or create_storage_backend(self.raw_storage_format)
        return create_storage_backend("jsonl")

    def _diff(self, existing: list[dict[str, Any]], incoming: list[dict[str, Any]], written: list[dict[str, Any]]) -> DiffSummary:
        before = {self._key(record): record for record in existing}
        after = {self._key(record): record for record in written}
        incoming_keys = [self._key(record) for record in incoming]
        inserted = [key for key in incoming_keys if key not in before]
        updated = [key for key in incoming_keys if key in before and before[key] != after.get(key)]
        unchanged = [key for key in incoming_keys if key in before and before[key] == after.get(key)]
        deleted_or_missing = [key for key in before if key not in after]
        duplicate_key_count = max(0, len(incoming_keys) - len(set(incoming_keys)))
        changed_keys = inserted + updated + deleted_or_missing
        return DiffSummary(
            record_count_before=len(existing),
            record_count_after=len(written),
            inserted_count=len(inserted),
            updated_count=len(updated),
            unchanged_count=len(unchanged),
            deleted_or_missing_count=len(deleted_or_missing),
            duplicate_key_count=duplicate_key_count,
            changed_keys_sample=["|".join(key) for key in changed_keys[:10]],
        )
