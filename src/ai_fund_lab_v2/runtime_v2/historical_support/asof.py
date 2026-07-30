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

from ai_fund_lab_v2.runtime_v2.historical_support.source_identity import build_source_identity

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
    composed_authorities = source_resolution.get("composed_authorities") or {}
    if composed_authorities:
        authorities_list = [
            composed_authorities["normalized_ohlcv"],
            composed_authorities["raw_ohlcv"],
            composed_authorities["trading_calendar"],
        ]
    else:
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
    elif source_resolution["coverage"].get("composition_used"):
        reason = "historical_asof_composed_authority_ready"
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
    for authority in resolution.authorities:
        target = logical_paths.get(authority.authority)
        if not target or authority.status != "PASS":
            continue
        composition = _composition_for_authority(resolution.feature_lookback_coverage, authority.authority)
        if composition:
            _write_composed_parquet(
                base_path=Path(composition["base_path"]),
                overlay_path=Path(composition["overlay_path"]),
                output_path=Path(target),
                cutoff=business_date,
                key_columns=tuple(composition["key_columns"]),
            )
        else:
            _write_filtered_parquet(
                source_path=Path(authority.physical_source_path),
                output_path=Path(target),
                cutoff=business_date,
            )
    materialization_id = f"historical_asof:{business_date}"
    source_identities = {
        key: build_source_identity(
            path,
            logical_source_id=key,
            business_date=business_date,
            feature_date=business_date,
            as_of_date=business_date,
            materialization_id=materialization_id,
        )
        for key, path in logical_paths.items()
        if Path(path).is_file()
    }
    manifest_path = input_root / "logical_input_manifest.json"
    payload = {
        "schema_version": HISTORICAL_LOGICAL_INPUT_MANIFEST_SCHEMA_VERSION,
        "status": resolution.status,
        "reason": resolution.reason,
        "business_date": business_date,
        "feature_date": business_date,
        "as_of_date": business_date,
        "materialization_id": materialization_id,
        "input_root": str(input_root),
        "raw_root": str(raw_root),
        "normalized_root": str(normalized_root),
        "logical_paths": logical_paths,
        "source_identity_version": "historical_source_identity_v1",
        "source_identities": source_identities,
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

    selected = _select_lookback_candidate(candidates)
    composition = {}
    if selected["status"] != "PASS":
        composition = _select_composed_lookback_candidate(
            operations_candidate=candidates[0],
            staging_candidates=[candidate for candidate in candidates[1:] if candidate["role"] == "acquisition_staging"],
            business_date=business_date,
        )
        if composition.get("status") == "PASS":
            coverage = {
                "schema_version": "runtime_historical_feature_lookback_coverage_v1",
                "status": "PASS",
                "reason": "historical_feature_lookback_ready",
                "business_date": business_date,
                "required_lookback_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
                "selected_source_role": "composed_canonical_plus_acquisition_staging",
                "selected_normalized_ohlcv_path": composition["normalized_composition"]["logical_source_path"],
                "selected_raw_ohlcv_path": composition["raw_composition"]["logical_source_path"],
                "selected_trading_calendar_path": composition["trading_calendar_composition"]["logical_source_path"],
                "candidate_sources": candidates,
                "composition_used": True,
                "source_composition": composition,
                "future_leakage_policy": "logical consumer input is materialized with rows Date <= business_date only",
                "runtime_market_data_mutated": False,
            }
            return {
                "authority_paths": {},
                "coverage": coverage,
                "composed_authorities": {
                    "normalized_ohlcv": _composed_authority_from_summary(
                        authority="normalized_ohlcv",
                        business_date=business_date,
                        summary=composition["normalized_composition"],
                    ),
                    "raw_ohlcv": _composed_authority_from_summary(
                        authority="raw_ohlcv",
                        business_date=business_date,
                        summary=composition["raw_composition"],
                    ),
                    "trading_calendar": _composed_authority_from_summary(
                        authority="trading_calendar",
                        business_date=business_date,
                        summary=composition["trading_calendar_composition"],
                    ),
                },
            }
        if composition.get("status") == "BLOCK" and composition.get("composition_attempts"):
            first_attempt = dict(composition["composition_attempts"][0])
            if not first_attempt.get("overlay_target_date_available"):
                composition = {}
            else:
                selected = {
                    **selected,
                    "role": "composed_canonical_plus_acquisition_staging",
                    "status": "BLOCK",
                    "reason": composition.get("reason") or "SOURCE_COMPOSITION_BLOCKED",
                    "composition_attempt": composition,
                }
        if composition.get("status") == "BLOCK" and selected.get("composition_attempt"):
            selected = {
                **selected,
                "role": "composed_canonical_plus_acquisition_staging",
                "status": "BLOCK",
                "reason": composition.get("reason") or "SOURCE_COMPOSITION_BLOCKED",
                "composition_attempt": composition,
            }
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
        "composition_used": False,
        "composition_attempt": selected.get("composition_attempt", composition),
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
        blocked.append(str(warmup.get("reason") or "feature_lookback_insufficient"))
    if calendar_coverage.get("status") != "PASS":
        blocked.append(str(calendar_coverage.get("reason") or "trading_calendar_lookback_not_ready"))
    status = "PASS" if not blocked else "BLOCK"
    reason = "FEATURE_LOOKBACK_SOURCE_READY" if status == "PASS" else _primary_lookback_blocker(blocked)
    return {
        "role": role,
        "status": status,
        "reason": reason,
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


def _select_composed_lookback_candidate(
    *,
    operations_candidate: dict[str, Any],
    staging_candidates: list[dict[str, Any]],
    business_date: str,
) -> dict[str, Any]:
    attempts = []
    for staging in sorted(staging_candidates, key=_lookback_candidate_rank, reverse=True):
        attempt = _composed_lookback_candidate(
            operations_candidate=operations_candidate,
            staging_candidate=staging,
            business_date=business_date,
        )
        attempts.append(attempt)
        if attempt["status"] == "PASS":
            return attempt | {"composition_attempts": attempts}
    if attempts:
        return attempts[0] | {"composition_attempts": attempts}
    return {
        "schema_version": "historical_source_composition_v1",
        "status": "BLOCK",
        "reason": "validated_staging_source_missing",
        "business_date": business_date,
        "composition_attempts": [],
    }


def _composed_lookback_candidate(
    *,
    operations_candidate: dict[str, Any],
    staging_candidate: dict[str, Any],
    business_date: str,
) -> dict[str, Any]:
    staging_root = Path(str(staging_candidate["normalized_path"])).parents[3]
    eligibility = _validated_staging_eligibility(
        run_root=staging_root,
        normalized_path=Path(str(staging_candidate["normalized_path"])),
        raw_path=Path(str(staging_candidate["raw_path"])),
        calendar_path=Path(str(staging_candidate["trading_calendar_path"])),
    )
    if eligibility["status"] != "PASS":
        return {
            "schema_version": "historical_source_composition_v1",
            "status": "BLOCK",
            "reason": eligibility["reason"],
            "business_date": business_date,
            "overlay_target_date_available": bool(
                dict(staging_candidate.get("warmup_sufficiency") or {}).get("target_date_available")
            ),
            "staging_eligibility": eligibility,
            "base_source_role": operations_candidate["role"],
            "overlay_source_role": staging_candidate["role"],
        }
    try:
        import pandas as pd

        base_normalized = pd.read_parquet(Path(str(operations_candidate["normalized_path"])))
        overlay_normalized = pd.read_parquet(Path(str(staging_candidate["normalized_path"])))
        base_raw = pd.read_parquet(Path(str(operations_candidate["raw_path"])))
        overlay_raw = pd.read_parquet(Path(str(staging_candidate["raw_path"])))
        base_calendar = pd.read_parquet(Path(str(operations_candidate["trading_calendar_path"])))
        overlay_calendar = pd.read_parquet(Path(str(staging_candidate["trading_calendar_path"])))
    except Exception as exc:  # noqa: BLE001 - fail closed source composition.
        return {
            "schema_version": "historical_source_composition_v1",
            "status": "BLOCK",
            "reason": f"source_composition_unreadable:{type(exc).__name__}",
            "business_date": business_date,
            "staging_eligibility": eligibility,
        }

    normalized = _compose_frames(
        base_normalized,
        overlay_normalized,
        business_date=business_date,
        key_columns=("Date", "Code"),
        base_path=str(operations_candidate["normalized_path"]),
        overlay_path=str(staging_candidate["normalized_path"]),
    )
    raw = _compose_frames(
        base_raw,
        overlay_raw,
        business_date=business_date,
        key_columns=("Date", "Code"),
        base_path=str(operations_candidate["raw_path"]),
        overlay_path=str(staging_candidate["raw_path"]),
    )
    calendar = _compose_frames(
        base_calendar,
        overlay_calendar,
        business_date=business_date,
        key_columns=("Date",),
        base_path=str(operations_candidate["trading_calendar_path"]),
        overlay_path=str(staging_candidate["trading_calendar_path"]),
    )
    warmup = _frame_warmup_sufficiency(normalized["frame"], business_date)
    calendar_coverage = _calendar_lookback_coverage_from_frames(
        calendar=calendar["frame"],
        quotes=normalized["frame"],
        business_date=business_date,
    )
    raw_normalized = _raw_normalized_consistency(raw=raw["frame"], normalized=normalized["frame"], business_date=business_date)
    blocked = []
    for name, summary in (("normalized", normalized), ("raw", raw), ("trading_calendar", calendar)):
        if summary["status"] != "PASS":
            blocked.append(f"{name}:{summary['reason']}")
    if warmup["warmup_sufficiency_judgment"] != "PASS":
        blocked.append(str(warmup["reason"]))
    if calendar_coverage["status"] != "PASS":
        blocked.append(str(calendar_coverage["reason"]))
    if raw_normalized["status"] != "PASS":
        blocked.append(str(raw_normalized["reason"]))
    status = "PASS" if not blocked else "BLOCK"
    reason = "historical_canonical_base_validated_staging_composition_ready" if status == "PASS" else _primary_lookback_blocker(blocked)
    return {
        "schema_version": "historical_source_composition_v1",
        "status": status,
        "reason": reason,
        "business_date": business_date,
        "overlay_target_date_available": bool(dict(staging_candidate.get("warmup_sufficiency") or {}).get("target_date_available")),
        "base_source_role": operations_candidate["role"],
        "overlay_source_role": staging_candidate["role"],
        "staging_eligibility": eligibility,
        "normalized_composition": _summary_without_frame(normalized, "composition:normalized_ohlcv"),
        "raw_composition": _summary_without_frame(raw, "composition:raw_ohlcv"),
        "trading_calendar_composition": _summary_without_frame(calendar, "composition:trading_calendar"),
        "warmup_sufficiency": warmup,
        "trading_calendar_lookback": calendar_coverage,
        "raw_normalized_consistency": raw_normalized,
        "blocked_reasons": blocked,
        "runtime_market_data_mutated": False,
    }


def _validated_staging_eligibility(
    *,
    run_root: Path,
    normalized_path: Path,
    raw_path: Path,
    calendar_path: Path,
) -> dict[str, Any]:
    state_path = run_root / "state.json"
    plan_path = run_root / "plan.json"
    if not state_path.is_file() or not plan_path.is_file():
        return {
            "schema_version": "historical_staging_eligibility_v1",
            "status": "BLOCK",
            "reason": "STAGING_VALIDATION_ARTIFACT_MISSING",
            "run_root": str(run_root),
            "state_path": str(state_path),
            "plan_path": str(plan_path),
        }
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - fail closed.
        return {
            "schema_version": "historical_staging_eligibility_v1",
            "status": "BLOCK",
            "reason": f"STAGING_VALIDATION_ARTIFACT_UNREADABLE:{type(exc).__name__}",
            "run_root": str(run_root),
        }
    final = dict(state.get("final_validation") or {})
    inventory = dict(final.get("normalized_inventory") or {})
    schema = dict(final.get("schema_comparison") or {})
    lineage = dict(final.get("jquants_lineage") or {})
    blocked = []
    if state.get("status") != "PASS" or plan.get("status") != "PASS" or final.get("status") != "PASS":
        blocked.append("STAGING_FINAL_VALIDATION_NOT_PASS")
    if state.get("acquisition_run_id") != run_root.name or plan.get("acquisition_run_id") != run_root.name:
        blocked.append("STAGING_RUN_ID_MISMATCH")
    if not normalized_path.is_file() or not raw_path.is_file() or not calendar_path.is_file():
        blocked.append("STAGING_SOURCE_FILE_MISSING")
    if inventory.get("duplicate_key_count"):
        blocked.append("STAGING_DUPLICATE_KEYS")
    if int(final.get("future_date_count") or 0):
        blocked.append("STAGING_FUTURE_DATE_ROWS")
    if lineage.get("status") != "PASS":
        blocked.append("STAGING_JQUANTS_LINEAGE_NOT_PASS")
    if schema.get("status") != "PASS" or schema.get("runtime_merge_compatible") is not True:
        blocked.append("STAGING_SCHEMA_NOT_RUNTIME_COMPATIBLE")
    normalized_hash = _file_hash(normalized_path)
    if final.get("content_hash") and final.get("content_hash") != normalized_hash:
        blocked.append("STAGING_NORMALIZED_HASH_MISMATCH")
    return {
        "schema_version": "historical_staging_eligibility_v1",
        "status": "PASS" if not blocked else "BLOCK",
        "reason": "validated_incremental_staging_ready" if not blocked else blocked[0],
        "run_root": str(run_root),
        "acquisition_run_id": str(state.get("acquisition_run_id") or ""),
        "state_path": str(state_path),
        "plan_path": str(plan_path),
        "normalized_path": str(normalized_path),
        "raw_path": str(raw_path),
        "trading_calendar_path": str(calendar_path),
        "normalized_hash": normalized_hash,
        "expected_normalized_hash": str(final.get("content_hash") or ""),
        "coverage_start_date": str(final.get("coverage_start_date") or ""),
        "coverage_end_date": str(final.get("coverage_end_date") or ""),
        "duplicate_key_count": int(inventory.get("duplicate_key_count") or 0),
        "future_date_count": int(final.get("future_date_count") or 0),
        "lineage_status": str(lineage.get("status") or ""),
        "schema_status": str(schema.get("status") or ""),
        "runtime_merge_compatible": bool(schema.get("runtime_merge_compatible")),
        "blocked_reasons": blocked,
    }


def _compose_frames(
    base: Any,
    overlay: Any,
    *,
    business_date: str,
    key_columns: tuple[str, ...],
    base_path: str,
    overlay_path: str,
) -> dict[str, Any]:
    import pandas as pd

    missing = [column for column in key_columns if column not in base.columns or column not in overlay.columns]
    if missing:
        return {
            "status": "BLOCK",
            "reason": "SOURCE_COMPOSITION_KEY_MISSING",
            "missing_key_columns": missing,
            "base_path": base_path,
            "overlay_path": overlay_path,
            "key_columns": list(key_columns),
            "frame": pd.DataFrame(),
        }
    base_dates = base[key_columns[0]].astype(str)
    overlay_dates = overlay[key_columns[0]].astype(str)
    base_cut = base[base_dates <= business_date].copy()
    overlay_cut = overlay[overlay_dates <= business_date].copy()
    base_keyed = _with_merge_key(base_cut, key_columns)
    overlay_keyed = _with_merge_key(overlay_cut, key_columns)
    base_keys = set(base_keyed["_composition_key"])
    overlay_keys = set(overlay_keyed["_composition_key"])
    overlap_keys = base_keys & overlay_keys
    replaced_keys = _changed_overlap_keys(base_keyed, overlay_keyed, overlap_keys)
    combined = pd.concat([base_keyed, overlay_keyed], ignore_index=True)
    before_dedup = int(len(combined))
    combined = combined.drop_duplicates(subset=["_composition_key"], keep="last")
    combined = combined.drop(columns=["_composition_key"])
    combined = combined.sort_values(list(key_columns), kind="mergesort").reset_index(drop=True)
    duplicate_count = _duplicate_key_count(combined, key_columns)
    logical_dates = combined[key_columns[0]].astype(str) if len(combined) else []
    future_excluded = int((base_dates > business_date).sum()) + int((overlay_dates > business_date).sum())
    status = "PASS" if len(combined) and duplicate_count == 0 else "BLOCK"
    reason = "source_composition_ready" if status == "PASS" else ("SOURCE_COMPOSITION_DUPLICATE_KEYS" if duplicate_count else "SOURCE_COMPOSITION_EMPTY")
    return {
        "status": status,
        "reason": reason,
        "base_path": base_path,
        "overlay_path": overlay_path,
        "base_hash": _file_hash(Path(base_path)),
        "overlay_hash": _file_hash(Path(overlay_path)),
        "key_columns": list(key_columns),
        "base_row_count": int(len(base)),
        "overlay_row_count": int(len(overlay)),
        "base_logical_row_count": int(len(base_cut)),
        "overlay_logical_row_count": int(len(overlay_cut)),
        "future_rows_excluded_count": future_excluded,
        "before_dedup_row_count": before_dedup,
        "logical_row_count": int(len(combined)),
        "physical_row_count": int(len(base) + len(overlay)),
        "duplicate_key_count": duplicate_count,
        "overlay_new_key_count": len(overlay_keys - base_keys),
        "overlay_overlap_key_count": len(overlap_keys),
        "overlay_replaced_key_count": len(replaced_keys),
        "changed_overlap_key_samples": sorted(replaced_keys)[:20],
        "logical_max_date": str(max(logical_dates)) if len(combined) else "",
        "physical_max_date": str(max(list(base_dates) + list(overlay_dates))) if len(base) + len(overlay) else "",
        "frame_hash": _frame_hash(combined),
        "frame": combined,
    }


def _summary_without_frame(summary: dict[str, Any], logical_source_path: str) -> dict[str, Any]:
    return {key: value for key, value in summary.items() if key != "frame"} | {
        "logical_source_path": logical_source_path
    }


def _composed_authority_from_summary(
    *,
    authority: str,
    business_date: str,
    summary: dict[str, Any],
) -> HistoricalAsOfAuthority:
    return HistoricalAsOfAuthority(
        authority=authority,
        status="PASS" if summary["status"] == "PASS" else "HALT",
        reason="historical_composed_authority_ready" if summary["status"] == "PASS" else summary["reason"],
        business_date=business_date,
        physical_source_path=str(summary["logical_source_path"]),
        physical_source_hash=str(summary["frame_hash"]),
        physical_row_count=int(summary["physical_row_count"]),
        physical_max_date=str(summary["physical_max_date"]),
        logical_cutoff=business_date,
        logical_row_count=int(summary["logical_row_count"]),
        logical_max_date=str(summary["logical_max_date"]),
        future_rows_excluded_count=int(summary["future_rows_excluded_count"]),
        content_hash_verified=True,
    )


def _primary_lookback_blocker(blocked: list[str]) -> str:
    priority = (
        "QUOTE_TARGET_DATE_MISSING",
        "SOURCE_ROWS_EMPTY",
        "TRADING_CALENDAR_TARGET_DATE_MISSING",
        "TRADING_CALENDAR_LOOKBACK_INSUFFICIENT",
        "HISTORICAL_SOURCE_WARMUP_INSUFFICIENT",
    )
    for reason in priority:
        if reason in blocked:
            return reason
    return blocked[0] if blocked else "FEATURE_LOOKBACK_SOURCE_BLOCKED"


def _select_lookback_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    ready = next((candidate for candidate in candidates if candidate["status"] == "PASS"), None)
    if ready is not None:
        return ready
    return sorted(candidates, key=_lookback_candidate_rank, reverse=True)[0]


def _lookback_candidate_rank(candidate: dict[str, Any]) -> tuple[int, int, int, int, str]:
    warmup = dict(candidate.get("warmup_sufficiency") or {})
    calendar = dict(candidate.get("trading_calendar_lookback") or {})
    inventory = dict(candidate.get("inventory") or {})
    target_available = 1 if warmup.get("target_date_available") else 0
    calendar_target_available = 1 if calendar.get("target_date_available") else 0
    available_days = int(calendar.get("available_business_day_count") or warmup.get("available_business_dates_count") or 0)
    row_count = int(inventory.get("row_count") or 0)
    latest = str(inventory.get("latest_date") or "")
    return (target_available, calendar_target_available, available_days, row_count, latest)


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
    calendar_state_columns = [column for column in ("HolDiv", "HolidayDivision", "holiday_division") if column in frame.columns]
    if calendar_state_columns:
        open_mask = None
        for column in calendar_state_columns:
            mask = frame[column].notna() & frame[column].map(_is_trading_calendar_open_value)
            open_mask = mask if open_mask is None else open_mask | mask
        frame = frame[open_mask].copy()
    calendar_dates = sorted({str(value) for value in frame[date_column].dropna().astype(str) if str(value) <= business_date})
    required_start = calendar_dates[-REQUIRED_LOOKBACK_BUSINESS_DAYS] if len(calendar_dates) >= REQUIRED_LOOKBACK_BUSINESS_DAYS else ""
    quote_dates = sorted({str(value) for value in quotes["Date"].dropna().astype(str) if str(value) <= business_date})
    available_count = len([day for day in quote_dates if required_start and required_start <= day <= business_date])
    target_date_available = business_date in set(quote_dates)
    status = "PASS" if required_start and available_count >= REQUIRED_LOOKBACK_BUSINESS_DAYS and target_date_available else "BLOCK"
    if status == "PASS":
        reason = "TRADING_CALENDAR_LOOKBACK_READY"
    elif not quote_dates:
        reason = "SOURCE_ROWS_EMPTY"
    elif not target_date_available:
        reason = "QUOTE_TARGET_DATE_MISSING"
    else:
        reason = "TRADING_CALENDAR_LOOKBACK_INSUFFICIENT"
    return {
        "status": status,
        "reason": reason,
        "trading_calendar_path": str(trading_calendar_path),
        "lookback_authority": "jquants_trading_calendar",
        "target_date": business_date,
        "required_lookback_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
        "required_history_start_date": required_start,
        "actual_history_start_date": quote_dates[0] if quote_dates else "",
        "actual_history_end_date": quote_dates[-1] if quote_dates else "",
        "available_business_day_count": available_count,
        "target_date_available": target_date_available,
        "target_date_missing": not target_date_available,
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


def _with_merge_key(frame: Any, key_columns: tuple[str, ...]) -> Any:
    keyed = frame.copy()
    key_values = [keyed[column].astype(str) for column in key_columns]
    key = key_values[0]
    for value in key_values[1:]:
        key = key + "\0" + value
    keyed["_composition_key"] = key
    return keyed


def _changed_overlap_keys(base_keyed: Any, overlay_keyed: Any, overlap_keys: set[str]) -> set[str]:
    if not overlap_keys:
        return set()
    common_columns = [
        column
        for column in base_keyed.columns
        if column in overlay_keyed.columns and column != "_composition_key"
    ]
    base_rows = base_keyed[base_keyed["_composition_key"].isin(overlap_keys)].set_index("_composition_key")
    overlay_rows = overlay_keyed[overlay_keyed["_composition_key"].isin(overlap_keys)].set_index("_composition_key")
    changed = set()
    for key in overlap_keys:
        base_payload = json.dumps(base_rows.loc[key, common_columns].astype(str).to_dict(), sort_keys=True)
        overlay_payload = json.dumps(overlay_rows.loc[key, common_columns].astype(str).to_dict(), sort_keys=True)
        if base_payload != overlay_payload:
            changed.add(key.replace("\0", "|"))
    return changed


def _duplicate_key_count(frame: Any, key_columns: tuple[str, ...]) -> int:
    if not len(frame):
        return 0
    return int(frame.duplicated(subset=list(key_columns)).sum())


def _frame_hash(frame: Any) -> str:
    payload = frame.astype(str).to_json(orient="records", date_format="iso")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _frame_warmup_sufficiency(frame: Any, business_date: str) -> dict[str, Any]:
    date_column = _business_date_column(tuple(str(column) for column in frame.columns))
    if not date_column or not len(frame):
        return {
            "schema_version": "runtime_market_data_warmup_sufficiency_v1",
            "warmup_sufficiency_judgment": "BLOCK",
            "reason": "SOURCE_ROWS_EMPTY",
            "target_start_date": business_date,
            "target_end_date": business_date,
            "required_business_dates_count": REQUIRED_LOOKBACK_BUSINESS_DAYS,
            "available_business_dates_count": 0,
            "missing_warmup_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
            "target_date_available": False,
            "target_date_missing": True,
        }
    dates = sorted({str(value) for value in frame[date_column].dropna().astype(str) if str(value) <= business_date})
    required_window = dates[-REQUIRED_LOOKBACK_BUSINESS_DAYS:] if len(dates) >= REQUIRED_LOOKBACK_BUSINESS_DAYS else dates
    target_available = business_date in set(dates)
    available_count = len(required_window)
    missing = max(0, REQUIRED_LOOKBACK_BUSINESS_DAYS - available_count)
    status = "PASS" if missing == 0 and target_available else "BLOCK"
    if status == "PASS":
        reason = "FEATURE_LOOKBACK_SOURCE_READY"
    elif not target_available:
        reason = "QUOTE_TARGET_DATE_MISSING"
    else:
        reason = "HISTORICAL_SOURCE_WARMUP_INSUFFICIENT"
    return {
        "schema_version": "runtime_market_data_warmup_sufficiency_v1",
        "warmup_sufficiency_judgment": status,
        "reason": reason,
        "target_start_date": business_date,
        "target_end_date": business_date,
        "required_business_dates_count": REQUIRED_LOOKBACK_BUSINESS_DAYS,
        "available_business_dates_count": available_count,
        "missing_warmup_business_days": missing,
        "required_history_start_date": required_window[0] if required_window else "",
        "actual_history_start_date": dates[0] if dates else "",
        "actual_history_end_date": dates[-1] if dates else "",
        "target_date_available": target_available,
        "target_date_missing": not target_available,
    }


def _calendar_lookback_coverage_from_frames(
    *,
    calendar: Any,
    quotes: Any,
    business_date: str,
) -> dict[str, Any]:
    date_column = _business_date_column(tuple(str(column) for column in calendar.columns))
    if not date_column:
        return {
            "status": "BLOCK",
            "reason": "trading_calendar_date_column_missing",
            "required_lookback_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
        }
    frame = calendar.copy()
    calendar_state_columns = [column for column in ("HolDiv", "HolidayDivision", "holiday_division") if column in frame.columns]
    if calendar_state_columns:
        open_mask = None
        for column in calendar_state_columns:
            mask = frame[column].notna() & frame[column].map(_is_trading_calendar_open_value)
            open_mask = mask if open_mask is None else open_mask | mask
        frame = frame[open_mask].copy()
    calendar_dates = sorted({str(value) for value in frame[date_column].dropna().astype(str) if str(value) <= business_date})
    quote_date_column = _business_date_column(tuple(str(column) for column in quotes.columns))
    quote_dates = sorted({str(value) for value in quotes[quote_date_column].dropna().astype(str) if str(value) <= business_date}) if quote_date_column else []
    required_start = calendar_dates[-REQUIRED_LOOKBACK_BUSINESS_DAYS] if len(calendar_dates) >= REQUIRED_LOOKBACK_BUSINESS_DAYS else ""
    available_count = len([day for day in quote_dates if required_start and required_start <= day <= business_date])
    target_date_available = business_date in set(quote_dates)
    status = "PASS" if required_start and available_count >= REQUIRED_LOOKBACK_BUSINESS_DAYS and target_date_available else "BLOCK"
    if status == "PASS":
        reason = "historical_trading_calendar_composed_authority_ready"
    elif not quote_dates:
        reason = "SOURCE_ROWS_EMPTY"
    elif not target_date_available:
        reason = "QUOTE_TARGET_DATE_MISSING"
    else:
        reason = "TRADING_CALENDAR_LOOKBACK_INSUFFICIENT"
    return {
        "status": status,
        "reason": reason,
        "lookback_authority": "jquants_trading_calendar_composed",
        "target_date": business_date,
        "required_lookback_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
        "required_history_start_date": required_start,
        "actual_history_start_date": quote_dates[0] if quote_dates else "",
        "actual_history_end_date": quote_dates[-1] if quote_dates else "",
        "available_business_day_count": available_count,
        "target_date_available": target_date_available,
        "target_date_missing": not target_date_available,
    }


def _raw_normalized_consistency(*, raw: Any, normalized: Any, business_date: str) -> dict[str, Any]:
    raw_date_column = _business_date_column(tuple(str(column) for column in raw.columns))
    normalized_date_column = _business_date_column(tuple(str(column) for column in normalized.columns))
    raw_dates = set(raw[raw_date_column].dropna().astype(str)) if raw_date_column else set()
    normalized_dates = set(normalized[normalized_date_column].dropna().astype(str)) if normalized_date_column else set()
    raw_target = business_date in raw_dates
    normalized_target = business_date in normalized_dates
    status = "PASS" if raw_target == normalized_target and normalized_target else "BLOCK"
    return {
        "status": status,
        "reason": "raw_normalized_target_availability_consistent" if status == "PASS" else "RAW_NORMALIZED_TARGET_AVAILABILITY_MISMATCH",
        "business_date": business_date,
        "raw_target_date_available": raw_target,
        "normalized_target_date_available": normalized_target,
        "raw_latest_date": max(raw_dates) if raw_dates else "",
        "normalized_latest_date": max(normalized_dates) if normalized_dates else "",
    }


def _composition_for_authority(coverage: dict[str, Any] | None, authority: str) -> dict[str, Any] | None:
    source_composition = dict((coverage or {}).get("source_composition") or {})
    key = {
        "normalized_ohlcv": "normalized_composition",
        "raw_ohlcv": "raw_composition",
        "trading_calendar": "trading_calendar_composition",
    }.get(authority)
    if not key:
        return None
    composition = source_composition.get(key)
    return dict(composition) if isinstance(composition, dict) else None


def _write_composed_parquet(
    *,
    base_path: Path,
    overlay_path: Path,
    output_path: Path,
    cutoff: str,
    key_columns: tuple[str, ...],
) -> None:
    import pandas as pd

    base = pd.read_parquet(base_path)
    overlay = pd.read_parquet(overlay_path)
    summary = _compose_frames(
        base,
        overlay,
        business_date=cutoff,
        key_columns=key_columns,
        base_path=str(base_path),
        overlay_path=str(overlay_path),
    )
    if summary["status"] != "PASS":
        raise ValueError(str(summary["reason"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary["frame"].to_parquet(output_path, index=False)


def _date_column(columns: tuple[str, ...]) -> str:
    return next((column for column in DATE_COLUMNS if column in columns), "")


def _business_date_column(columns: tuple[str, ...]) -> str:
    return next((column for column in ("Date", "date", "target_date", "market_date") if column in columns), "")


def _is_trading_calendar_open_value(value: Any) -> bool:
    text = str(value).strip()
    return text in {"1", "1.0"}


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
