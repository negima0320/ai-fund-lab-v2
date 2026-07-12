"""Current Temporal Schema migration utilities for Runtime v2."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.temporal import (
    CurrentTemporalState,
    FreshnessStatus,
    evaluate_current_position_freshness,
    evaluate_current_valuation_freshness,
    resolve_temporal_context,
)


CURRENT_TEMPORAL_SCHEMA_VERSION = "runtime_v2_current_temporal_v1"
CURRENT_MIGRATION_SCHEMA_VERSION = "runtime_v2_current_temporal_migration_v1"


@dataclass(frozen=True)
class CurrentTemporalMetadata:
    source_schema_version: str
    target_schema_version: str
    migration_status: str
    legacy_as_of_used: bool
    position_state_as_of: str
    valuation_as_of: str
    source_market_date: str
    last_execution_date: str
    last_reconciled_at: str
    warnings: tuple[str, ...]
    review_required: bool
    production_equivalent: bool

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        return payload


@dataclass(frozen=True)
class CurrentMigrationResult:
    status: str
    reason: str
    artifact_path: str
    source_current_path: str
    source_schema_version: str
    target_schema_version: str
    migration_status: str
    apply_requested: bool
    apply_executed: bool
    backup_path: str
    legacy_as_of_used: bool
    missing_evidence: tuple[str, ...]
    warnings: tuple[str, ...]
    review_required: bool
    candidate_current: dict[str, Any]

    @property
    def manifest_fields(self) -> dict[str, Any]:
        return {
            "current_temporal_migration_status": self.status,
            "current_temporal_migration_reason": self.reason,
            "current_temporal_migration_artifact_path": self.artifact_path,
            "current_temporal_source_current_path": self.source_current_path,
            "current_temporal_source_schema_version": self.source_schema_version,
            "current_temporal_target_schema_version": self.target_schema_version,
            "current_temporal_apply_requested": self.apply_requested,
            "current_temporal_apply_executed": self.apply_executed,
            "current_temporal_backup_path": self.backup_path,
            "current_temporal_legacy_as_of_used": self.legacy_as_of_used,
            "current_temporal_missing_evidence": list(self.missing_evidence),
            "current_temporal_warnings": list(self.warnings),
            "current_temporal_review_required": self.review_required,
            "current_position_status": self.candidate_current.get("current_position_status") or "",
            "current_valuation_status": self.candidate_current.get("current_valuation_status") or "",
            "position_state_as_of": self.candidate_current.get("position_state_as_of") or "",
            "valuation_as_of": self.candidate_current.get("valuation_as_of") or "",
            "source_market_date": self.candidate_current.get("source_market_date") or "",
        }


def read_current_temporal(
    *,
    runtime_root: Path | str,
    business_date: str,
    now: datetime | None = None,
) -> tuple[dict[str, Any], CurrentTemporalMetadata]:
    current_path = Path(runtime_root) / "persistent_ledger" / "state.json"
    payload = _read_json(current_path)
    candidate, metadata, _, _ = build_current_temporal_candidate(
        runtime_root=runtime_root,
        business_date=business_date,
        current_payload=payload,
        now=now,
    )
    return candidate, metadata


def build_current_temporal_candidate(
    *,
    runtime_root: Path | str,
    business_date: str,
    current_payload: dict[str, Any],
    now: datetime | None = None,
) -> tuple[dict[str, Any], CurrentTemporalMetadata, tuple[str, ...], tuple[str, ...]]:
    root = Path(runtime_root)
    warnings: list[str] = []
    missing: list[str] = []
    source_schema = str(current_payload.get("temporal_schema_version") or current_payload.get("schema_version") or "legacy_current")
    explicit_temporal = _has_explicit_temporal_fields(current_payload)
    legacy_as_of = str(current_payload.get("as_of") or "")
    legacy_as_of_used = not explicit_temporal
    positions = list(current_payload.get("positions") or [])
    last_execution_date = str(current_payload.get("last_execution_date") or "")
    position_state_as_of = str(current_payload.get("position_state_as_of") or "")
    valuation_as_of = str(current_payload.get("valuation_as_of") or "")
    source_market_date = str(current_payload.get("source_market_date") or "")
    last_reconciled_at = str(current_payload.get("last_reconciled_at") or current_payload.get("updated_at") or "")

    ledger_execution_date = _latest_runtime_owned_execution_date(root / "persistent_ledger" / "executions.jsonl")
    if ledger_execution_date:
        last_execution_date = last_execution_date or ledger_execution_date
        position_state_as_of = position_state_as_of or ledger_execution_date
    elif positions and not position_state_as_of:
        warnings.append("position_state_derived_from_legacy_as_of_without_execution_evidence")
        missing.append("runtime_owned_execution_ledger")
        position_state_as_of = legacy_as_of
    elif not positions and not position_state_as_of:
        position_state_as_of = legacy_as_of or business_date

    market_date = _latest_market_evidence_date(root)
    if market_date:
        valuation_as_of = valuation_as_of or market_date
        source_market_date = source_market_date or market_date
    elif not valuation_as_of:
        warnings.append("valuation_state_derived_from_legacy_as_of_without_market_evidence")
        missing.append("market_evidence")
        valuation_as_of = legacy_as_of
        source_market_date = legacy_as_of

    if not last_execution_date:
        last_execution_date = position_state_as_of
    if not last_reconciled_at:
        warnings.append("last_reconciled_at_missing")
        missing.append("last_reconciled_at")

    temporal_state = CurrentTemporalState(
        position_state_as_of=position_state_as_of,
        valuation_as_of=valuation_as_of,
        last_execution_date=last_execution_date,
        last_reconciled_at=last_reconciled_at,
        source_market_date=source_market_date,
    )
    context = resolve_temporal_context(
        runtime_business_date=business_date,
        latest_available_market_date=source_market_date or None,
        now=now,
        root=_base_dir_for_runtime_root(root),
    )
    position_evidence = evaluate_current_position_freshness(context=context, current=temporal_state)
    valuation_evidence = evaluate_current_valuation_freshness(context=context, current=temporal_state, now=now)
    review_required = bool(missing) or legacy_as_of_used
    production_equivalent = not legacy_as_of_used and not review_required
    candidate = dict(current_payload)
    candidate.update(
        {
            "temporal_schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "business_date": business_date,
            "position_state_as_of": position_state_as_of,
            "valuation_as_of": valuation_as_of,
            "source_market_date": source_market_date,
            "last_execution_date": last_execution_date,
            "last_reconciled_at": last_reconciled_at,
            "updated_at": str(current_payload.get("updated_at") or current_payload.get("created_at") or ""),
            "temporal_status": "REVIEW_REQUIRED" if review_required else "READY",
            "position_state_source": "runtime_owned_execution_ledger" if ledger_execution_date else "legacy_current",
            "valuation_source": "market_evidence" if market_date else "legacy_current",
            "valuation_generated_at": str(current_payload.get("valuation_generated_at") or ""),
            "no_fill": bool(positions and position_state_as_of != business_date and valuation_as_of == business_date),
            "legacy_as_of_used": legacy_as_of_used,
            "legacy_migration_status": "LEGACY_DERIVED" if legacy_as_of_used else "NATIVE_TEMPORAL",
            "derived_position_state_as_of": position_state_as_of if legacy_as_of_used else "",
            "derived_valuation_as_of": valuation_as_of if legacy_as_of_used else "",
            "production_equivalent": production_equivalent,
            "current_position_status": position_evidence.status.value,
            "current_valuation_status": valuation_evidence.status.value,
            "current_position_temporal_evidence": position_evidence.to_payload(),
            "current_valuation_temporal_evidence": valuation_evidence.to_payload(),
        }
    )
    metadata = CurrentTemporalMetadata(
        source_schema_version=source_schema,
        target_schema_version=CURRENT_TEMPORAL_SCHEMA_VERSION,
        migration_status="LEGACY_DERIVED" if legacy_as_of_used else "READY",
        legacy_as_of_used=legacy_as_of_used,
        position_state_as_of=position_state_as_of,
        valuation_as_of=valuation_as_of,
        source_market_date=source_market_date,
        last_execution_date=last_execution_date,
        last_reconciled_at=last_reconciled_at,
        warnings=tuple(sorted(set(warnings))),
        review_required=review_required,
        production_equivalent=production_equivalent,
    )
    return candidate, metadata, tuple(sorted(set(missing))), tuple(sorted(set(warnings)))


def run_current_temporal_migration(
    *,
    runtime_root: Path | str,
    business_date: str,
    apply_current_migration: bool = False,
    now: datetime | None = None,
) -> CurrentMigrationResult:
    root = Path(runtime_root)
    generated_at = (now or datetime.now(timezone.utc)).isoformat()
    source_path = root / "persistent_ledger" / "state.json"
    artifact_path = root / "runtime_state" / "current_migration" / business_date / "current_temporal_migration.json"
    try:
        current = _read_json(source_path)
    except ValueError as exc:
        payload = _migration_payload(
            business_date=business_date,
            generated_at=generated_at,
            source_current_path=str(source_path),
            source_schema_version="UNKNOWN",
            migration_status="HALT",
            apply_requested=apply_current_migration,
            apply_executed=False,
            legacy_as_of_used=False,
            candidate_current={},
            missing_evidence=("current",),
            warnings=(str(exc),),
            review_required=True,
            backup_path="",
        )
        _write_json(artifact_path, payload)
        return _result_from_payload(payload, artifact_path=artifact_path, reason=str(exc))

    candidate, metadata, missing, warnings = build_current_temporal_candidate(
        runtime_root=root,
        business_date=business_date,
        current_payload=current,
        now=now,
    )
    safe_legacy_apply = _safe_legacy_temporal_metadata_apply(
        source=current,
        candidate=candidate,
        missing=missing,
        metadata=metadata,
    )
    review_required = metadata.review_required and not safe_legacy_apply
    if safe_legacy_apply:
        candidate = dict(candidate)
        candidate.update(
            {
                "temporal_status": "READY",
                "production_equivalent": False,
                "legacy_migration_status": "LEGACY_TEMPORAL_METADATA_APPLIED",
            }
        )
    apply_executed = False
    backup_path = ""
    if apply_current_migration and not review_required:
        backup_path = str(_atomic_write_current(root=root, source_path=source_path, payload=candidate, now=now))
        apply_executed = True
    payload = _migration_payload(
        business_date=business_date,
        generated_at=generated_at,
        source_current_path=str(source_path),
        source_schema_version=metadata.source_schema_version,
        migration_status=metadata.migration_status,
        apply_requested=apply_current_migration,
        apply_executed=apply_executed,
        legacy_as_of_used=metadata.legacy_as_of_used,
        candidate_current=candidate,
        missing_evidence=missing,
        warnings=warnings,
        review_required=review_required,
        backup_path=backup_path,
    )
    _write_json(artifact_path, payload)
    return _result_from_payload(
        payload,
        artifact_path=artifact_path,
        reason="current_temporal_migration_review_required" if review_required else "current_temporal_migration_ready",
    )


def _safe_legacy_temporal_metadata_apply(
    *,
    source: dict[str, Any],
    candidate: dict[str, Any],
    missing: tuple[str, ...],
    metadata: CurrentTemporalMetadata,
) -> bool:
    if not metadata.legacy_as_of_used or missing:
        return False
    if candidate.get("current_position_status") != FreshnessStatus.READY.value:
        return False
    if candidate.get("current_valuation_status") != FreshnessStatus.READY.value:
        return False
    for field in ("cash", "buying_power", "market_value", "total_equity"):
        if source.get(field) != candidate.get(field):
            return False
    source_positions = list(source.get("positions") or [])
    candidate_positions = list(candidate.get("positions") or [])
    if len(source_positions) != len(candidate_positions):
        return False
    for before, after in zip(source_positions, candidate_positions):
        for field in ("symbol", "quantity", "average_price", "cost_basis"):
            if before.get(field) != after.get(field):
                return False
    return True


def write_current_temporal_state(path: Path, payload: dict[str, Any]) -> Path:
    required = (
        "position_state_as_of",
        "valuation_as_of",
        "source_market_date",
        "last_execution_date",
        "last_reconciled_at",
        "updated_at",
    )
    missing = [field for field in required if not payload.get(field)]
    if missing:
        raise ValueError("missing Current temporal fields: " + ",".join(missing))
    if payload.get("temporal_schema_version") != CURRENT_TEMPORAL_SCHEMA_VERSION:
        raise ValueError("temporal_schema_version must be " + CURRENT_TEMPORAL_SCHEMA_VERSION)
    _write_json(path, payload)
    return path


def _migration_payload(
    *,
    business_date: str,
    generated_at: str,
    source_current_path: str,
    source_schema_version: str,
    migration_status: str,
    apply_requested: bool,
    apply_executed: bool,
    legacy_as_of_used: bool,
    candidate_current: dict[str, Any],
    missing_evidence: tuple[str, ...],
    warnings: tuple[str, ...],
    review_required: bool,
    backup_path: str,
) -> dict[str, Any]:
    return {
        "schema_version": CURRENT_MIGRATION_SCHEMA_VERSION,
        "business_date": business_date,
        "generated_at": generated_at,
        "source_current_path": source_current_path,
        "source_schema_version": source_schema_version,
        "target_schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
        "migration_status": migration_status,
        "apply_requested": apply_requested,
        "apply_executed": apply_executed,
        "legacy_as_of_used": legacy_as_of_used,
        "derived_fields": {
            "position_state_as_of": candidate_current.get("position_state_as_of") or "",
            "valuation_as_of": candidate_current.get("valuation_as_of") or "",
            "source_market_date": candidate_current.get("source_market_date") or "",
            "last_execution_date": candidate_current.get("last_execution_date") or "",
            "last_reconciled_at": candidate_current.get("last_reconciled_at") or "",
        },
        "missing_evidence": list(missing_evidence),
        "warnings": list(warnings),
        "review_required": review_required,
        "backup_path": backup_path,
        "candidate_current": candidate_current,
        "next_operator_action": "review missing evidence before apply" if review_required else "apply may be requested explicitly",
    }


def _result_from_payload(payload: dict[str, Any], *, artifact_path: Path, reason: str) -> CurrentMigrationResult:
    status = "REVIEW_REQUIRED" if payload.get("review_required") else "READY"
    if payload.get("migration_status") == "HALT":
        status = "HALT"
    return CurrentMigrationResult(
        status=status,
        reason=reason,
        artifact_path=str(artifact_path),
        source_current_path=str(payload.get("source_current_path") or ""),
        source_schema_version=str(payload.get("source_schema_version") or ""),
        target_schema_version=str(payload.get("target_schema_version") or ""),
        migration_status=str(payload.get("migration_status") or ""),
        apply_requested=bool(payload.get("apply_requested")),
        apply_executed=bool(payload.get("apply_executed")),
        backup_path=str(payload.get("backup_path") or ""),
        legacy_as_of_used=bool(payload.get("legacy_as_of_used")),
        missing_evidence=tuple(payload.get("missing_evidence") or ()),
        warnings=tuple(payload.get("warnings") or ()),
        review_required=bool(payload.get("review_required")),
        candidate_current=dict(payload.get("candidate_current") or {}),
    )


def _atomic_write_current(*, root: Path, source_path: Path, payload: dict[str, Any], now: datetime | None) -> Path:
    timestamp = (now or datetime.now(timezone.utc)).isoformat().replace(":", "").replace("+", "")
    backup_path = root / "persistent_ledger" / "history" / "current" / f"{timestamp}.json"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.exists():
        shutil.copy2(source_path, backup_path)
    temp_path = source_path.with_suffix(".json.tmp")
    write_current_temporal_state(temp_path, payload)
    os.replace(temp_path, source_path)
    _read_json(source_path)
    return backup_path


def _latest_runtime_owned_execution_date(path: Path) -> str:
    if not path.is_file():
        return ""
    dates: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("broker_only") is True:
            continue
        if str(record.get("runtime_owned") or "true").lower() == "false":
            continue
        value = str(
            record.get("business_date")
            or record.get("execution_date")
            or record.get("filled_at")
            or record.get("as_of")
            or record.get("generated_at")
            or ""
        )
        if value:
            dates.append(value[:10])
    return max(dates) if dates else ""


def _latest_market_evidence_date(root: Path) -> str:
    latest = root / "runtime_state" / "market" / "latest.json"
    if latest.is_file():
        try:
            payload = _read_json(latest)
            artifact = Path(str(payload.get("artifact_path") or ""))
            if artifact.is_file():
                market = _read_json(artifact)
                return str(market.get("market_date") or market.get("latest_available_market_date") or "")
        except ValueError:
            return ""
    market_root = root / "runtime_state" / "market"
    candidates = sorted(market_root.glob("*/market_evidence.json"))
    dates = []
    for path in candidates:
        try:
            payload = _read_json(path)
        except ValueError:
            continue
        value = str(payload.get("market_date") or payload.get("latest_available_market_date") or "")
        if value:
            dates.append(value)
    return max(dates) if dates else ""


def _has_explicit_temporal_fields(payload: dict[str, Any]) -> bool:
    return all(
        payload.get(field)
        for field in (
            "position_state_as_of",
            "valuation_as_of",
            "source_market_date",
            "last_execution_date",
            "last_reconciled_at",
        )
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{path} missing") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} invalid json: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must be a JSON object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _base_dir_for_runtime_root(runtime_root: Path) -> Path:
    return runtime_root.parent if runtime_root.name == ".runtime" else Path(".")
