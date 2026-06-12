from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import ENDPOINT_PATHS, RAW_COLLECTIONS
from ai_fund_lab_v2.data_store import create_storage_backend, manifest_path, read_manifest
from ai_fund_lab_v2.data_store.schema import validate_records
from ai_fund_lab_v2.runtime import RuntimePaths


@dataclass(frozen=True)
class EndpointReadiness:
    endpoint_name: str
    status: str
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParquetReadinessResult:
    status: str
    reasons: list[str]
    endpoints: list[EndpointReadiness]
    recommended_next_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reasons": self.reasons,
            "endpoints": [endpoint.to_dict() for endpoint in self.endpoints],
            "recommended_next_action": self.recommended_next_action,
        }


def check_parquet_readiness(paths: RuntimePaths) -> ParquetReadinessResult:
    global_reasons: list[str] = []
    if importlib.util.find_spec("pyarrow") is None:
        global_reasons.append("pyarrow_missing")
    if importlib.util.find_spec("pandas") is None:
        global_reasons.append("pandas_missing")

    manifest_entries = read_manifest(manifest_path(paths.raw_data))
    endpoint_results: list[EndpointReadiness] = []
    for endpoint_name in ENDPOINT_PATHS:
        reasons: list[str] = []
        base = paths.raw_data / RAW_COLLECTIONS[endpoint_name] / "data"
        jsonl_path = create_storage_backend("jsonl").path_for(base)
        parquet_path = create_storage_backend("parquet").path_for(base)
        jsonl_records = create_storage_backend("jsonl").read_records(jsonl_path)
        parquet_records = create_storage_backend("parquet").read_records(parquet_path)
        if len(jsonl_records) != len(parquet_records):
            reasons.append("jsonl_parquet_record_count_mismatch")
        if not parquet_path.exists():
            reasons.append("parquet_file_missing")
        if not str(parquet_path).startswith(str(paths.raw_data)):
            reasons.append("parquet_outside_runtime_raw")
        parquet_validation = validate_records(endpoint_name, parquet_records)
        jsonl_validation = validate_records(endpoint_name, jsonl_records)
        if parquet_validation.status != jsonl_validation.status:
            reasons.append("validation_status_mismatch")
        latest = latest_manifest(manifest_entries, ENDPOINT_PATHS[endpoint_name])
        if not latest or latest.get("storage_format") != "parquet":
            reasons.append("latest_manifest_not_parquet")
        if not any(entry.get("endpoint") == ENDPOINT_PATHS[endpoint_name] and entry.get("status") == "MIGRATED" for entry in manifest_entries):
            reasons.append("migration_event_missing")
        endpoint_results.append(EndpointReadiness(endpoint_name, "READY" if not reasons else "NOT_READY", reasons))

    all_reasons = global_reasons + [f"{endpoint.endpoint_name}:{reason}" for endpoint in endpoint_results for reason in endpoint.reasons]
    status = "READY" if not all_reasons else "NOT_READY"
    action = "Parquet can be considered as default." if status == "READY" else "Resolve NOT_READY reasons before making Parquet default."
    return ParquetReadinessResult(status, all_reasons, endpoint_results, action)


def latest_manifest(entries: list[dict], endpoint: str) -> dict | None:
    rows = [entry for entry in entries if entry.get("endpoint") == endpoint and entry.get("event_type") != "NORMALIZED"]
    return rows[-1] if rows else None
