"""Historical market-data as-of resolution for Runtime v2.

The resolver never rewrites canonical data.  It proves the logical consumer
view that a Historical run may use for a business date.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ASOF_SCHEMA_VERSION = "runtime_historical_asof_view_v1"
LEGACY_ASOF_SCHEMA_VERSIONS = {"phase17_l_historical_asof_view_v1"}
SUPPORTED_ASOF_SCHEMA_VERSIONS = {ASOF_SCHEMA_VERSION, *LEGACY_ASOF_SCHEMA_VERSIONS}
HISTORICAL_LOGICAL_INPUT_SCHEMA_VERSION = "runtime_historical_logical_input_v1"
HISTORICAL_LOGICAL_INPUT_MANIFEST_SCHEMA_VERSION = "runtime_historical_logical_input_manifest_v1"
DATE_COLUMNS = ("target_date", "date", "Date", "market_date")


@dataclass(frozen=True)
class HistoricalAsOfAuthority:
    authority: str
    status: str
    reason: str
    business_date: str
    physical_source_path: str
    physical_source_hash: str
    physical_row_count: int
    physical_max_date: str
    logical_cutoff: str
    logical_row_count: int
    logical_max_date: str
    future_rows_excluded_count: int
    manifest_path: str = ""
    manifest_hash: str = ""
    expected_source_hash: str = ""
    expected_manifest_hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HistoricalAsOfResolution:
    status: str
    reason: str
    business_date: str
    logical_identity: str
    authorities: tuple[HistoricalAsOfAuthority, ...]

    @property
    def latest_available_market_date(self) -> str:
        daily = next((item for item in self.authorities if item.authority == "normalized_ohlcv"), None)
        return daily.logical_max_date if daily else self.business_date

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": ASOF_SCHEMA_VERSION,
            "status": self.status,
            "reason": self.reason,
            "business_date": self.business_date,
            "logical_identity": self.logical_identity,
            "latest_available_market_date": self.latest_available_market_date,
            "authorities": [authority.to_payload() for authority in self.authorities],
            "future_rows_excluded_from_consumer": all(
                authority.status == "PASS" and authority.logical_max_date <= authority.logical_cutoff
                for authority in self.authorities
            ),
            "physical_data_unchanged": True,
        }


@dataclass(frozen=True)
class HistoricalLogicalInput:
    status: str
    reason: str
    business_date: str
    input_root: str
    raw_root: str
    normalized_root: str
    manifest_path: str
    manifest_hash: str
    resolution: HistoricalAsOfResolution
    logical_paths: dict[str, str]

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": HISTORICAL_LOGICAL_INPUT_SCHEMA_VERSION,
            "status": self.status,
            "reason": self.reason,
            "business_date": self.business_date,
            "input_root": self.input_root,
            "raw_root": self.raw_root,
            "normalized_root": self.normalized_root,
            "manifest_path": self.manifest_path,
            "manifest_hash": self.manifest_hash,
            "logical_paths": dict(self.logical_paths),
            "resolution": self.resolution.to_payload(),
            "verified_derived_test_input": True,
            "authority_is_physical_source_hash_plus_cutoff": True,
        }


def resolve_historical_market_data_asof(
    *,
    operations_root: Path | str,
    business_date: str,
    expected_hashes: dict[str, str] | None = None,
    manifest_refs: dict[str, str] | None = None,
    expected_manifest_hashes: dict[str, str] | None = None,
) -> HistoricalAsOfResolution:
    root = Path(operations_root)
    expected = expected_hashes or {}
    manifests = manifest_refs or {}
    expected_manifests = expected_manifest_hashes or {}
    authority_paths = {
        "normalized_ohlcv": root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet",
        "raw_ohlcv": root / "jquants" / "raw" / "jquants" / "equities_bars_daily" / "data.parquet",
        "trading_calendar": root / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet",
        "listed_issues": root / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet",
    }
    authorities = tuple(
        _resolve_authority(
            authority=name,
            source_path=path,
            business_date=business_date,
            expected_source_hash=expected.get(name, ""),
            manifest_path=manifests.get(name, ""),
            expected_manifest_hash=expected_manifests.get(name, ""),
        )
        for name, path in authority_paths.items()
    )
    failed = [item for item in authorities if item.status != "PASS"]
    status = "PASS" if not failed else "HALT"
    reason = "historical_asof_view_ready" if status == "PASS" else "historical_asof_authority_invalid"
    return HistoricalAsOfResolution(
        status=status,
        reason=reason,
        business_date=business_date,
        logical_identity=f"historical-asof:{business_date}",
        authorities=authorities,
    )


def write_historical_asof_evidence(
    *,
    evidence_root: Path | str,
    business_date: str,
    resolution: HistoricalAsOfResolution,
) -> Path:
    path = Path(evidence_root) / "historical_asof_view.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = resolution.to_payload()
    payload["artifact_path"] = str(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def materialize_historical_logical_inputs(
    *,
    operations_root: Path | str,
    business_date: str,
    evidence_root: Path | str,
    runtime_test_context: dict[str, Any] | None = None,
) -> HistoricalLogicalInput:
    resolution = resolve_historical_market_data_asof(
        operations_root=operations_root,
        business_date=business_date,
    )
    input_root = Path(evidence_root) / "inputs" / "historical_asof" / business_date
    raw_root = input_root / "raw"
    normalized_root = input_root / "raw_normalized"
    logical_paths = {
        "normalized_ohlcv": str(normalized_root / "jquants" / "equities_bars_daily" / "data.parquet"),
        "raw_ohlcv": str(raw_root / "jquants" / "equities_bars_daily" / "data.parquet"),
        "trading_calendar": str(raw_root / "jquants" / "trading_calendar" / "data.parquet"),
        "listed_issues": str(raw_root / "jquants" / "listed_issues" / "data.parquet"),
    }
    if resolution.status == "PASS":
        for authority in resolution.authorities:
            target = logical_paths.get(authority.authority)
            if not target:
                continue
            _write_filtered_parquet(
                source_path=Path(authority.physical_source_path),
                output_path=Path(target),
                cutoff=business_date,
            )
    manifest_path = input_root / "logical_input_manifest.json"
    payload = {
        "schema_version": HISTORICAL_LOGICAL_INPUT_MANIFEST_SCHEMA_VERSION,
        "status": resolution.status,
        "reason": resolution.reason,
        "business_date": business_date,
        "input_root": str(input_root),
        "raw_root": str(raw_root),
        "normalized_root": str(normalized_root),
        "logical_paths": logical_paths,
        "runtime_test_identity": dict(runtime_test_context or {}),
        "resolution": resolution.to_payload(),
        "verified_derived_test_input": True,
        "canonical_physical_data_unchanged": True,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return HistoricalLogicalInput(
        status=resolution.status,
        reason=resolution.reason,
        business_date=business_date,
        input_root=str(input_root),
        raw_root=str(raw_root),
        normalized_root=str(normalized_root),
        manifest_path=str(manifest_path),
        manifest_hash=_file_hash(manifest_path),
        resolution=resolution,
        logical_paths=logical_paths,
    )


def _resolve_authority(
    *,
    authority: str,
    source_path: Path,
    business_date: str,
    expected_source_hash: str,
    manifest_path: str,
    expected_manifest_hash: str,
) -> HistoricalAsOfAuthority:
    manifest_hash = _file_hash(Path(manifest_path)) if manifest_path else ""
    if expected_manifest_hash and manifest_hash != expected_manifest_hash:
        return HistoricalAsOfAuthority(
            authority=authority,
            status="HALT",
            reason="manifest_hash_mismatch",
            business_date=business_date,
            physical_source_path=str(source_path),
            physical_source_hash=_file_hash(source_path) if source_path.is_file() else "",
            physical_row_count=0,
            physical_max_date="",
            logical_cutoff=business_date,
            logical_row_count=0,
            logical_max_date="",
            future_rows_excluded_count=0,
            manifest_path=manifest_path,
            manifest_hash=manifest_hash,
            expected_source_hash=expected_source_hash,
            expected_manifest_hash=expected_manifest_hash,
        )
    if not source_path.is_file():
        return HistoricalAsOfAuthority(
            authority=authority,
            status="HALT",
            reason="physical_source_missing",
            business_date=business_date,
            physical_source_path=str(source_path),
            physical_source_hash="",
            physical_row_count=0,
            physical_max_date="",
            logical_cutoff=business_date,
            logical_row_count=0,
            logical_max_date="",
            future_rows_excluded_count=0,
            manifest_path=manifest_path,
            manifest_hash=manifest_hash,
            expected_source_hash=expected_source_hash,
            expected_manifest_hash=expected_manifest_hash,
        )
    source_hash = _file_hash(source_path)
    if expected_source_hash and source_hash != expected_source_hash:
        return HistoricalAsOfAuthority(
            authority=authority,
            status="HALT",
            reason="source_hash_mismatch",
            business_date=business_date,
            physical_source_path=str(source_path),
            physical_source_hash=source_hash,
            physical_row_count=0,
            physical_max_date="",
            logical_cutoff=business_date,
            logical_row_count=0,
            logical_max_date="",
            future_rows_excluded_count=0,
            manifest_path=manifest_path,
            manifest_hash=manifest_hash,
            expected_source_hash=expected_source_hash,
            expected_manifest_hash=expected_manifest_hash,
        )
    try:
        import pandas as pd

        frame = pd.read_parquet(source_path)
    except Exception as exc:  # noqa: BLE001 - fail closed authority evidence.
        return HistoricalAsOfAuthority(
            authority=authority,
            status="HALT",
            reason=f"source_unreadable:{type(exc).__name__}",
            business_date=business_date,
            physical_source_path=str(source_path),
            physical_source_hash=source_hash,
            physical_row_count=0,
            physical_max_date="",
            logical_cutoff=business_date,
            logical_row_count=0,
            logical_max_date="",
            future_rows_excluded_count=0,
            manifest_path=manifest_path,
            manifest_hash=manifest_hash,
            expected_source_hash=expected_source_hash,
            expected_manifest_hash=expected_manifest_hash,
        )
    date_column = _date_column(tuple(str(column) for column in frame.columns))
    if not date_column:
        return HistoricalAsOfAuthority(
            authority=authority,
            status="HALT",
            reason="date_column_missing",
            business_date=business_date,
            physical_source_path=str(source_path),
            physical_source_hash=source_hash,
            physical_row_count=int(len(frame)),
            physical_max_date="",
            logical_cutoff=business_date,
            logical_row_count=0,
            logical_max_date="",
            future_rows_excluded_count=0,
            manifest_path=manifest_path,
            manifest_hash=manifest_hash,
            expected_source_hash=expected_source_hash,
            expected_manifest_hash=expected_manifest_hash,
        )
    dates = frame[date_column].astype(str)
    physical_max = str(dates.max()) if len(frame) else ""
    logical = frame[dates <= business_date]
    logical_dates = logical[date_column].astype(str) if len(logical) else []
    logical_max = str(logical_dates.max()) if len(logical) else ""
    future_count = int((dates > business_date).sum())
    status = "PASS"
    reason = "historical_asof_authority_ready"
    if len(logical) == 0:
        status = "HALT"
        reason = "logical_view_empty"
    elif logical_max > business_date:
        status = "HALT"
        reason = "future_row_in_logical_view"
    return HistoricalAsOfAuthority(
        authority=authority,
        status=status,
        reason=reason,
        business_date=business_date,
        physical_source_path=str(source_path),
        physical_source_hash=source_hash,
        physical_row_count=int(len(frame)),
        physical_max_date=physical_max,
        logical_cutoff=business_date,
        logical_row_count=int(len(logical)),
        logical_max_date=logical_max,
        future_rows_excluded_count=future_count,
        manifest_path=manifest_path,
        manifest_hash=manifest_hash,
        expected_source_hash=expected_source_hash,
        expected_manifest_hash=expected_manifest_hash,
    )


def _date_column(columns: tuple[str, ...]) -> str:
    return next((column for column in DATE_COLUMNS if column in columns), "")


def _write_filtered_parquet(*, source_path: Path, output_path: Path, cutoff: str) -> None:
    import pandas as pd

    frame = pd.read_parquet(source_path)
    date_column = _date_column(tuple(str(column) for column in frame.columns))
    if not date_column:
        raise ValueError(f"date column missing for historical logical input: {source_path}")
    logical = frame[frame[date_column].astype(str) <= cutoff].copy()
    if len(logical) and str(logical[date_column].astype(str).max()) > cutoff:
        raise ValueError("future_row_detected")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logical.to_parquet(output_path, index=False)


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
