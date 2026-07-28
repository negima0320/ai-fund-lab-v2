"""Historical logical source identity helpers.

The Historical runtime must bind submit to the logical inputs materialized for
the current run. Physical parquet metadata, path, or an older manifest hash must
not become the submit authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

SOURCE_IDENTITY_VERSION = "historical_source_identity_v1"


def build_source_identity(
    path: Path | str,
    *,
    logical_source_id: str,
    business_date: str,
    feature_date: str = "",
    as_of_date: str = "",
    materialization_id: str = "",
    source_manifest_path: Path | str = "",
) -> dict[str, Any]:
    source_path = Path(path)
    manifest_path = Path(source_manifest_path) if str(source_manifest_path) else Path()
    manifest_hash = _sha256_file(manifest_path) if str(manifest_path) else ""
    identity = _build_source_identity_cached(
        str(source_path),
        logical_source_id,
        business_date,
        feature_date,
        as_of_date,
        materialization_id,
        str(manifest_path) if str(manifest_path) else "",
        manifest_hash,
        _sha256_file(source_path),
    )
    return dict(identity)


def build_identity_from_logical_manifest(
    manifest_path: Path | str,
    *,
    logical_source_id: str,
    business_date: str,
) -> dict[str, Any]:
    manifest = _read_json(Path(manifest_path))
    source_identities = manifest.get("source_identities")
    if isinstance(source_identities, dict) and isinstance(source_identities.get(logical_source_id), dict):
        return dict(source_identities[logical_source_id])
    feature_date = str(manifest.get("feature_date") or manifest.get("business_date") or "")
    as_of_date = str(manifest.get("as_of_date") or manifest.get("business_date") or "")
    materialization_id = str(
        manifest.get("materialization_id")
        or manifest.get("logical_materialization_id")
        or f"historical_asof:{business_date}"
    )
    logical_paths = manifest.get("logical_paths") if isinstance(manifest.get("logical_paths"), dict) else {}
    path = str(logical_paths.get(logical_source_id) or "")
    return build_source_identity(
        path,
        logical_source_id=logical_source_id,
        business_date=business_date,
        feature_date=feature_date,
        as_of_date=as_of_date,
        materialization_id=materialization_id,
        source_manifest_path=manifest_path,
    )


def validate_bound_source_identity(
    *,
    expected_identity: dict[str, Any],
    actual_path: Path | str,
    logical_source_id: str,
    business_date: str,
    source_manifest_path: Path | str = "",
) -> dict[str, Any]:
    actual_identity = build_source_identity(
        actual_path,
        logical_source_id=logical_source_id,
        business_date=business_date,
        feature_date=str(expected_identity.get("feature_date") or ""),
        as_of_date=str(expected_identity.get("as_of_date") or ""),
        materialization_id=str(expected_identity.get("materialization_id") or ""),
        source_manifest_path=source_manifest_path,
    )
    result = {
        "status": "PASS",
        "reason": "historical source identity verified",
        "source_identity_contract_version": SOURCE_IDENTITY_VERSION,
        "logical_source_id": logical_source_id,
        "expected_source_path": str(expected_identity.get("physical_source_path") or ""),
        "actual_source_path": str(actual_identity.get("physical_source_path") or ""),
        "expected_materialization_id": str(expected_identity.get("materialization_id") or ""),
        "actual_materialization_id": str(actual_identity.get("materialization_id") or ""),
        "expected_content_hash": str(expected_identity.get("content_hash") or ""),
        "actual_content_hash": str(actual_identity.get("content_hash") or ""),
        "expected_physical_file_hash": str(expected_identity.get("physical_file_hash") or ""),
        "actual_physical_file_hash": str(actual_identity.get("physical_file_hash") or ""),
        "expected_manifest_hash": str(expected_identity.get("source_manifest_hash") or ""),
        "actual_manifest_hash": str(actual_identity.get("source_manifest_hash") or ""),
        "expected_schema_hash": str(expected_identity.get("schema_hash") or ""),
        "actual_schema_hash": str(actual_identity.get("schema_hash") or ""),
        "expected_hash": str(expected_identity.get("content_hash") or ""),
        "source_hash": str(actual_identity.get("content_hash") or ""),
        "expected_source_identity": expected_identity,
        "actual_source_identity": actual_identity,
        "physical_path_differs": str(expected_identity.get("physical_source_path") or "")
        != str(actual_identity.get("physical_source_path") or ""),
        "recommended_action": "",
    }
    mismatch_class = _mismatch_class(expected_identity, actual_identity, business_date)
    if mismatch_class:
        result.update(
            {
                "status": "HALT",
                "reason": "historical source identity mismatch",
                "mismatch_class": mismatch_class,
                "root_reason_code": mismatch_class,
                "recommended_action": _recommended_action(mismatch_class),
            }
        )
        return result
    result["mismatch_class"] = "NONE"
    return result


def logical_input_manifest_path_from_asof_view(asof_view_path: Path | str, business_date: str) -> Path:
    path = Path(asof_view_path)
    return path.parent / "inputs" / "historical_asof" / business_date / "logical_input_manifest.json"


def _mismatch_class(expected: dict[str, Any], actual: dict[str, Any], business_date: str) -> str:
    if str(expected.get("business_date") or "") != business_date or str(actual.get("business_date") or "") != business_date:
        return "BUSINESS_DATE_MISMATCH"
    if not str(expected.get("physical_source_path") or ""):
        return "BOUND_SOURCE_PATH_MISSING"
    if not Path(str(expected.get("physical_source_path") or "")).is_file():
        return "BOUND_SOURCE_FILE_MISSING"
    if not Path(str(actual.get("physical_source_path") or "")).is_file():
        return "ACTUAL_SOURCE_FILE_MISSING"
    expected_run = _runtime_test_run_id(str(expected.get("physical_source_path") or ""))
    actual_run = _runtime_test_run_id(str(actual.get("physical_source_path") or ""))
    if expected_run and actual_run and expected_run != actual_run:
        return "CROSS_RUN_SOURCE_REJECTION"
    if str(expected.get("logical_source_id") or "") != str(actual.get("logical_source_id") or ""):
        return "LOGICAL_SOURCE_ID_MISMATCH"
    if str(expected.get("schema_hash") or "") != str(actual.get("schema_hash") or ""):
        return "SCHEMA_HASH_MISMATCH"
    if str(expected.get("content_hash") or "") != str(actual.get("content_hash") or ""):
        actual_path = str(actual.get("physical_source_path") or "")
        expected_path = str(expected.get("physical_source_path") or "")
        if "/raw/" in actual_path and "/raw_normalized/" in expected_path:
            return "RAW_VS_NORMALIZED_MISMATCH"
        if expected_run and not actual_run:
            return "RUN_SCOPED_VS_GLOBAL_SOURCE_MISMATCH"
        return "CONTENT_HASH_MISMATCH"
    return ""


def _recommended_action(mismatch_class: str) -> str:
    if mismatch_class in {"CROSS_RUN_SOURCE_REJECTION", "RUN_SCOPED_VS_GLOBAL_SOURCE_MISMATCH"}:
        return "Use the Morning/Pending-bound run-scoped logical input manifest for this run."
    if mismatch_class == "RAW_VS_NORMALIZED_MISMATCH":
        return "Bind Submit to normalized_ohlcv; do not mix raw OHLCV with normalized OHLCV."
    if mismatch_class == "BUSINESS_DATE_MISMATCH":
        return "Regenerate the runtime day with matching business_date and feature_date authority."
    return "Regenerate or inspect the historical logical source materialization before submit."


@lru_cache(maxsize=64)
def _build_source_identity_cached(
    path: str,
    logical_source_id: str,
    business_date: str,
    feature_date: str,
    as_of_date: str,
    materialization_id: str,
    source_manifest_path: str,
    source_manifest_hash: str,
    physical_file_hash: str,
) -> dict[str, Any]:
    source_path = Path(path)
    stats = _dataset_stats(source_path)
    base = {
        "source_identity_version": SOURCE_IDENTITY_VERSION,
        "logical_source_id": logical_source_id,
        "materialization_id": materialization_id,
        "business_date": business_date,
        "feature_date": feature_date,
        "as_of_date": as_of_date,
        "physical_source_path": str(source_path),
        "source_manifest_path": source_manifest_path,
        "source_manifest_hash": source_manifest_hash,
        "physical_file_hash": physical_file_hash,
        "logical_dataset_hash": stats["logical_dataset_hash"],
        "content_hash": stats["logical_dataset_hash"],
        "schema_hash": stats["schema_hash"],
        "row_count": stats["row_count"],
        "min_date": stats["min_date"],
        "max_date": stats["max_date"],
        "symbol_count": stats["symbol_count"],
    }
    base["source_identity_hash"] = _semantic_hash(
        {
            key: base[key]
            for key in (
                "source_identity_version",
                "logical_source_id",
                "materialization_id",
                "business_date",
                "feature_date",
                "as_of_date",
                "content_hash",
                "schema_hash",
                "row_count",
                "min_date",
                "max_date",
                "symbol_count",
            )
        }
    )
    return base


def _dataset_stats(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {
            "logical_dataset_hash": "",
            "schema_hash": "",
            "row_count": 0,
            "min_date": "",
            "max_date": "",
            "symbol_count": 0,
        }
    try:
        import pandas as pd

        frame = pd.read_parquet(path)
    except Exception:
        return {
            "logical_dataset_hash": _sha256_file(path),
            "schema_hash": "",
            "row_count": 0,
            "min_date": "",
            "max_date": "",
            "symbol_count": 0,
        }
    columns = [str(col) for col in frame.columns]
    schema = [{"name": str(col), "dtype": str(dtype)} for col, dtype in zip(frame.columns, frame.dtypes)]
    schema_hash = _semantic_hash(sorted(schema, key=lambda item: item["name"]))
    normalized = frame.copy()
    normalized.columns = columns
    normalized = normalized.reindex(sorted(columns), axis=1)
    normalized = normalized.astype("string").fillna("<NA>")
    sort_columns = list(normalized.columns)
    if sort_columns:
        normalized = normalized.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)
    logical_hash = hashlib.sha256(normalized.to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()
    date_column = _first_present(columns, ("Date", "date", "business_date", "BusinessDate"))
    code_column = _first_present(columns, ("Code", "code", "LocalCode", "local_code", "symbol", "Symbol"))
    min_date = ""
    max_date = ""
    symbol_count = 0
    if date_column:
        dates = frame[date_column].astype("string").dropna()
        if len(dates):
            min_date = str(dates.min())
            max_date = str(dates.max())
    if code_column:
        symbol_count = int(frame[code_column].astype("string").dropna().nunique())
    return {
        "logical_dataset_hash": logical_hash,
        "schema_hash": schema_hash,
        "row_count": int(len(frame)),
        "min_date": min_date,
        "max_date": max_date,
        "symbol_count": symbol_count,
    }


def _first_present(values: list[str], candidates: tuple[str, ...]) -> str:
    present = set(values)
    for candidate in candidates:
        if candidate in present:
            return candidate
    return ""


def _runtime_test_run_id(path: str) -> str:
    match = re.search(r"reports/runtime_tests/runs/([^/]+)/", path)
    return match.group(1) if match else ""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _semantic_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
