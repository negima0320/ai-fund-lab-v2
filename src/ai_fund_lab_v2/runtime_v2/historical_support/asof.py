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

from ai_fund_lab_v2.runtime_v2.historical_support.listed_issues_snapshots import (
    SELECTION_POLICY,
    resolve_listed_issues_snapshot,
)
from ai_fund_lab_v2.runtime_v2.market_data_bootstrap import (
    REQUIRED_LOOKBACK_BUSINESS_DAYS,
    build_market_data_warmup_sufficiency,
    parquet_inventory,
)


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
    selected_snapshot_date: str = ""
    selection_policy: str = ""
    snapshot_age_days: int | None = None
    content_hash_verified: bool = False

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HistoricalAsOfResolution:
    status: str
    reason: str
    business_date: str
    logical_identity: str
    authorities: tuple[HistoricalAsOfAuthority, ...]
    feature_lookback_coverage: dict[str, Any] | None = None

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
            "feature_lookback_coverage": dict(self.feature_lookback_coverage or {}),
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
    historical_listed_issues_snapshot_root: Path | str | None = None,
    require_feature_lookback: bool = False,
) -> HistoricalAsOfResolution:
    root = Path(operations_root)
    expected = expected_hashes or {}
    manifests = manifest_refs or {}
    expected_manifests = expected_manifest_hashes or {}
    listed_snapshot_root = Path(historical_listed_issues_snapshot_root) if historical_listed_issues_snapshot_root else (
        root / "jquants" / "historical_snapshots" / "listed_issues"
    )
    source_resolution = _resolve_historical_ohlcv_source_paths(
        operations_root=root,
        business_date=business_date,
        require_feature_lookback=require_feature_lookback,
    )
    authority_paths = {
        "normalized_ohlcv": root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet",
        "raw_ohlcv": root / "jquants" / "raw" / "jquants" / "equities_bars_daily" / "data.parquet",
        "trading_calendar": root / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet",
    }
    authority_paths.update(source_resolution["authority_paths"])
    authorities_list = [
        _resolve_authority(
            authority=name,
            source_path=path,
            business_date=business_date,
            expected_source_hash=expected.get(name, ""),
            manifest_path=manifests.get(name, ""),
            expected_manifest_hash=expected_manifests.get(name, ""),
        )
        for name, path in authority_paths.items()
    ]
    if (listed_snapshot_root / "index.json").is_file():
        authorities_list.append(_resolve_listed_issues_snapshot_authority(listed_snapshot_root, business_date))
    else:
        authorities_list.append(
            _resolve_authority(
                authority="listed_issues",
                source_path=root / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet",
                business_date=business_date,
                expected_source_hash=expected.get("listed_issues", ""),
                manifest_path=manifests.get("listed_issues", ""),
                expected_manifest_hash=expected_manifests.get("listed_issues", ""),
            )
        )
    authorities = tuple(authorities_list)
    failed = [item for item in authorities if item.status != "PASS"]
    lookback_status = str(source_resolution["coverage"].get("status") or "PASS")
    status = "PASS" if not failed and lookback_status == "PASS" else "HALT"
    if failed:
        reason = "historical_asof_authority_invalid"
    elif lookback_status != "PASS":
        reason = "historical_feature_lookback_insufficient"
    else:
        reason = "historical_asof_view_ready"
    return HistoricalAsOfResolution(
        status=status,
        reason=reason,
        business_date=business_date,
        logical_identity=f"historical-asof:{business_date}",
        authorities=authorities,
        feature_lookback_coverage=source_resolution["coverage"],
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
    historical_listed_issues_snapshot_root: Path | str | None = None,
    require_feature_lookback: bool = False,
) -> HistoricalLogicalInput:
    resolution = resolve_historical_market_data_asof(
        operations_root=operations_root,
        business_date=business_date,
        historical_listed_issues_snapshot_root=historical_listed_issues_snapshot_root,
        require_feature_lookback=require_feature_lookback,
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
        "feature_lookback_coverage": dict(resolution.feature_lookback_coverage or {}),
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


def _resolve_historical_ohlcv_source_paths(
    *,
    operations_root: Path,
    business_date: str,
    require_feature_lookback: bool,
) -> dict[str, Any]:
    default_normalized = operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    default_raw = operations_root / "jquants" / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    default_calendar = operations_root / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet"
    if not require_feature_lookback:
        return {
            "authority_paths": {},
            "coverage": {
                "schema_version": "runtime_historical_feature_lookback_coverage_v1",
                "status": "PASS",
                "reason": "feature_lookback_check_not_required",
                "business_date": business_date,
                "required_lookback_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
                "selected_source_role": "operations_canonical",
                "selected_normalized_ohlcv_path": str(default_normalized),
            },
        }

    candidates = [
        _lookback_candidate(
            role="operations_canonical",
            normalized_path=default_normalized,
            raw_path=default_raw,
            trading_calendar_path=default_calendar,
            business_date=business_date,
            runtime_root=_runtime_root_for_operations(operations_root),
        )
    ]
    for normalized_path in _discover_acquisition_normalized_sources(_runtime_root_for_operations(operations_root)):
        run_root = normalized_path.parents[3]
        candidates.append(
            _lookback_candidate(
                role="acquisition_staging",
                normalized_path=normalized_path,
                raw_path=run_root / "raw" / "jquants" / "equities_bars_daily" / "data.parquet",
                trading_calendar_path=run_root / "raw" / "jquants" / "trading_calendar" / "data.parquet",
                business_date=business_date,
                runtime_root=_runtime_root_for_operations(operations_root),
            )
        )

    selected = next((candidate for candidate in candidates if candidate["status"] == "PASS"), candidates[0])
    coverage = {
        "schema_version": "runtime_historical_feature_lookback_coverage_v1",
        "status": selected["status"],
        "reason": selected["reason"],
        "business_date": business_date,
        "required_lookback_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
        "selected_source_role": selected["role"],
        "selected_normalized_ohlcv_path": selected["normalized_path"],
        "selected_raw_ohlcv_path": selected["raw_path"] if Path(str(selected["raw_path"])).is_file() else str(default_raw),
        "selected_trading_calendar_path": selected["trading_calendar_path"] if Path(str(selected["trading_calendar_path"])).is_file() else str(default_calendar),
        "candidate_sources": candidates,
        "future_leakage_policy": "logical consumer input is materialized with rows Date <= business_date only",
        "runtime_market_data_mutated": False,
    }
    authority_paths: dict[str, Path] = {}
    if selected["role"] != "operations_canonical" or selected["normalized_path"] != str(default_normalized):
        authority_paths["normalized_ohlcv"] = Path(str(selected["normalized_path"]))
        raw_path = Path(str(selected["raw_path"]))
        if raw_path.is_file():
            authority_paths["raw_ohlcv"] = raw_path
        trading_calendar_path = Path(str(selected["trading_calendar_path"]))
        if trading_calendar_path.is_file():
            authority_paths["trading_calendar"] = trading_calendar_path
    return {"authority_paths": authority_paths, "coverage": coverage}


def _lookback_candidate(
    *,
    role: str,
    normalized_path: Path,
    raw_path: Path,
    trading_calendar_path: Path,
    business_date: str,
    runtime_root: Path,
) -> dict[str, Any]:
    warmup = build_market_data_warmup_sufficiency(
        runtime_root=runtime_root,
        target_start_date=business_date,
        target_end_date=business_date,
        maximum_required_warmup_business_days=REQUIRED_LOOKBACK_BUSINESS_DAYS,
        source_path=normalized_path,
    )
    inventory = parquet_inventory(normalized_path)
    calendar_coverage = _calendar_lookback_coverage(
        trading_calendar_path=trading_calendar_path,
        normalized_path=normalized_path,
        business_date=business_date,
    )
    blocked: list[str] = []
    if inventory.get("status") != "PASS":
        blocked.append("normalized_ohlcv_source_not_ready")
    if inventory.get("duplicate_key_count"):
        blocked.append("normalized_ohlcv_duplicate_keys")
    if inventory.get("jquants_lineage_status") != "PASS":
        blocked.append("normalized_ohlcv_lineage_not_pass")
    if inventory.get("future_or_training_columns_detected"):
        blocked.append("training_or_future_columns_detected")
    if warmup.get("warmup_sufficiency_judgment") != "PASS":
        blocked.append("feature_lookback_insufficient")
    if calendar_coverage.get("status") != "PASS":
        blocked.append(str(calendar_coverage.get("reason") or "trading_calendar_lookback_not_ready"))
    status = "PASS" if not blocked else "BLOCK"
    return {
        "role": role,
        "status": status,
        "reason": "FEATURE_LOOKBACK_SOURCE_READY" if status == "PASS" else "FEATURE_LOOKBACK_SOURCE_BLOCKED",
        "normalized_path": str(normalized_path),
        "raw_path": str(raw_path),
        "trading_calendar_path": str(trading_calendar_path),
        "warmup_sufficiency": warmup,
        "trading_calendar_lookback": calendar_coverage,
        "inventory": {
            key: inventory.get(key)
            for key in (
                "exists",
                "row_count",
                "earliest_date",
                "latest_date",
                "unique_business_days",
                "symbol_count",
                "duplicate_key_count",
                "jquants_lineage_status",
                "future_or_training_columns_detected",
                "status",
            )
        },
        "blocked_reasons": blocked,
    }


def _calendar_lookback_coverage(
    *,
    trading_calendar_path: Path,
    normalized_path: Path,
    business_date: str,
) -> dict[str, Any]:
    if not trading_calendar_path.is_file():
        return {
            "status": "BLOCK",
            "reason": "trading_calendar_authority_missing",
            "trading_calendar_path": str(trading_calendar_path),
            "required_lookback_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
        }
    try:
        import pandas as pd

        calendar = pd.read_parquet(trading_calendar_path)
        quotes = pd.read_parquet(normalized_path, columns=["Date"])
    except Exception as exc:  # noqa: BLE001 - fail closed evidence.
        return {
            "status": "BLOCK",
            "reason": f"lookback_authority_unreadable:{type(exc).__name__}",
            "trading_calendar_path": str(trading_calendar_path),
            "required_lookback_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
        }
    date_column = _date_column(tuple(str(column) for column in calendar.columns))
    if not date_column:
        return {
            "status": "BLOCK",
            "reason": "trading_calendar_date_column_missing",
            "trading_calendar_path": str(trading_calendar_path),
            "required_lookback_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
        }
    frame = calendar.copy()
    if "HolDiv" in frame.columns:
        frame = frame[frame["HolDiv"].astype(str) == "1"].copy()
    elif "holiday_division" in frame.columns:
        frame = frame[frame["holiday_division"].astype(str) == "1"].copy()
    calendar_dates = sorted({str(value) for value in frame[date_column].dropna().astype(str) if str(value) <= business_date})
    required_start = calendar_dates[-REQUIRED_LOOKBACK_BUSINESS_DAYS] if len(calendar_dates) >= REQUIRED_LOOKBACK_BUSINESS_DAYS else ""
    quote_dates = sorted({str(value) for value in quotes["Date"].dropna().astype(str) if str(value) <= business_date})
    available_count = len([day for day in quote_dates if required_start and required_start <= day <= business_date])
    status = "PASS" if required_start and available_count >= REQUIRED_LOOKBACK_BUSINESS_DAYS else "BLOCK"
    return {
        "status": status,
        "reason": "TRADING_CALENDAR_LOOKBACK_READY" if status == "PASS" else "TRADING_CALENDAR_LOOKBACK_INSUFFICIENT",
        "trading_calendar_path": str(trading_calendar_path),
        "lookback_authority": "jquants_trading_calendar",
        "target_date": business_date,
        "required_lookback_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
        "required_history_start_date": required_start,
        "actual_history_start_date": quote_dates[0] if quote_dates else "",
        "actual_history_end_date": quote_dates[-1] if quote_dates else "",
        "available_business_day_count": available_count,
    }


def _discover_acquisition_normalized_sources(runtime_root: Path) -> list[Path]:
    runs_root = runtime_root / "market_data_acquisition" / "runs"
    if not runs_root.is_dir():
        return []
    candidates = [
        path
        for path in runs_root.glob("*/raw_normalized/jquants/equities_bars_daily/data.parquet")
        if path.is_file()
    ]
    return sorted(candidates, key=lambda path: (path.stat().st_mtime, str(path)), reverse=True)


def _runtime_root_for_operations(operations_root: Path) -> Path:
    return operations_root.parent if operations_root.name == "operations" else operations_root.parent / ".runtime"


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


def _resolve_listed_issues_snapshot_authority(snapshot_root: Path, business_date: str) -> HistoricalAsOfAuthority:
    resolution = resolve_listed_issues_snapshot(
        snapshot_root=snapshot_root,
        business_date=business_date,
        mode="historical",
    )
    if resolution.status != "PASS":
        return HistoricalAsOfAuthority(
            authority="listed_issues",
            status="HALT",
            reason=resolution.reason,
            business_date=business_date,
            physical_source_path=resolution.selected_snapshot_path,
            physical_source_hash="",
            physical_row_count=0,
            physical_max_date="",
            logical_cutoff=business_date,
            logical_row_count=0,
            logical_max_date="",
            future_rows_excluded_count=0,
            manifest_path=resolution.selected_manifest_path,
            manifest_hash="",
            selected_snapshot_date=resolution.selected_snapshot_date,
            selection_policy=SELECTION_POLICY,
            snapshot_age_days=resolution.snapshot_age_days,
        )
    source_path = Path(resolution.selected_snapshot_path)
    try:
        import pandas as pd

        frame = pd.read_parquet(source_path)
        date_column = _date_column(tuple(str(column) for column in frame.columns))
        dates = frame[date_column].astype(str) if date_column else []
        physical_max = str(dates.max()) if len(frame) and date_column else resolution.selected_snapshot_date
    except Exception:
        frame = []
        physical_max = resolution.selected_snapshot_date
    return HistoricalAsOfAuthority(
        authority="listed_issues",
        status="PASS",
        reason="historical_listed_issues_snapshot_authority_ready",
        business_date=business_date,
        physical_source_path=resolution.selected_snapshot_path,
        physical_source_hash=resolution.selected_content_hash,
        physical_row_count=int(len(frame)),
        physical_max_date=physical_max,
        logical_cutoff=business_date,
        logical_row_count=int(len(frame)),
        logical_max_date=resolution.selected_snapshot_date,
        future_rows_excluded_count=0,
        manifest_path=resolution.selected_manifest_path,
        manifest_hash=_file_hash(Path(resolution.selected_manifest_path)),
        selected_snapshot_date=resolution.selected_snapshot_date,
        selection_policy=SELECTION_POLICY,
        snapshot_age_days=resolution.snapshot_age_days,
        content_hash_verified=resolution.content_hash_verified,
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
