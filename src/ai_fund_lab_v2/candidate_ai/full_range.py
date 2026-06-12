from __future__ import annotations

import json
import shutil
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from ai_fund_lab_v2.candidate_ai.normalized_data_reader import discover_daily_quotes_normalized
from ai_fund_lab_v2.candidate_ai.data_loader import adapt_daily_quotes_normalized, validate_daily_quotes_normalized_input
from ai_fund_lab_v2.candidate_ai.feature_builder import build_candidate_features_mock_with_audit
from ai_fund_lab_v2.candidate_ai.leakage_audit import audit_feature_table
from ai_fund_lab_v2.data_store import StorageBackendError, create_storage_backend
from ai_fund_lab_v2.runtime import RuntimePaths


DEFAULT_FULL_RANGE_FEATURE_VERSION = "candidate_features_full_range_dry_run_v1"
DEFAULT_FULL_RANGE_SCHEMA_VERSION = "candidate_feature_table_v1"
DEFAULT_MAX_CODES_PER_CHUNK = 500
DEFAULT_READINESS_STATUS = "PLAN_READY_FOR_FULL_RANGE_DRY_RUN"
NO_WRITE_GATE_READY = "READY_FOR_FULL_RANGE_EXECUTION"
NO_WRITE_GATE_BLOCKED_BY_CHUNK_PLAN = "BLOCKED_BY_CHUNK_PLAN"
NO_WRITE_GATE_BLOCKED_BY_RESUME_STATE = "BLOCKED_BY_RESUME_STATE"
NO_WRITE_GATE_BLOCKED_BY_NO_WRITE_VALIDATION = "BLOCKED_BY_NO_WRITE_VALIDATION"
NO_WRITE_GATE_BLOCKED_BY_SCHEMA = "BLOCKED_BY_SCHEMA"
NO_WRITE_GATE_BLOCKED_BY_LEAKAGE = "BLOCKED_BY_LEAKAGE"
NO_WRITE_GATE_SKIPPED_NO_DATA = "SKIPPED_NO_DATA"
CONTROLLED_EXECUTION_READY = "CONTROLLED_EXECUTION_COMPLETED"
CONTROLLED_EXECUTION_BLOCKED = "CONTROLLED_EXECUTION_BLOCKED"
CONTROLLED_EXECUTION_FAILED = "CONTROLLED_EXECUTION_FAILED"
RESUME_CONTROLLED_READY = "RESUME_AWARE_CONTROLLED_COMPLETED"
RESUME_CONTROLLED_BLOCKED = "RESUME_AWARE_CONTROLLED_BLOCKED"
RESUME_CONTROLLED_SKIPPED = "RESUME_AWARE_CONTROLLED_SKIPPED"
BATCH_READINESS_READY = "READY_FOR_CONTROLLED_BATCH_EXECUTION"
BATCH_READINESS_BLOCKED_BY_CHUNK_PLAN = "BLOCKED_BY_CHUNK_PLAN"
BATCH_READINESS_BLOCKED_BY_RESUME_STATE = "BLOCKED_BY_RESUME_STATE"
BATCH_READINESS_BLOCKED_BY_MANIFEST_INCONSISTENCY = "BLOCKED_BY_MANIFEST_INCONSISTENCY"
BATCH_READINESS_BLOCKED_BY_STORAGE = "BLOCKED_BY_STORAGE"
BATCH_READINESS_BLOCKED_BY_SCHEMA = "BLOCKED_BY_SCHEMA"
BATCH_READINESS_BLOCKED_BY_LEAKAGE = "BLOCKED_BY_LEAKAGE"
BATCH_READINESS_SKIPPED_NO_DATA = "SKIPPED_NO_DATA"


@dataclass(frozen=True)
class FullRangePaths:
    runtime_dir: Path
    feature_dir: Path
    manifest_dir: Path
    audit_dir: Path
    tmp_dir: Path
    report_dir: Path

    def ensure_dirs(self) -> None:
        for path in (self.feature_dir, self.manifest_dir, self.audit_dir, self.tmp_dir, self.report_dir):
            path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class FullRangeChunkPlan:
    run_id: str
    chunk_id: str
    date_start: str
    date_end: str
    code_start: str | None
    code_end: str | None
    codes: tuple[str, ...]
    code_count: int
    expected_input_rows_optional: int | None
    status: str
    data_source_type: str
    feature_version: str
    schema_version: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["codes"] = list(self.codes)
        return payload


@dataclass(frozen=True)
class FullRangeRunManifest:
    run_id: str
    created_at: str
    data_source_type: str
    feature_version: str
    schema_version: str
    date_min: str | None
    date_max: str | None
    code_count: int
    chunk_count: int
    completed_chunk_count: int
    failed_chunk_count: int
    skipped_chunk_count: int
    readiness_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FullRangeChunkManifest:
    run_id: str
    chunk_id: str
    status: str
    date_start: str
    date_end: str
    code_count: int
    row_count: int
    eligible_count: int
    excluded_count: int
    schema_validation_status: str
    leakage_audit_status: str
    output_path: str | None
    manifest_path: str | None
    audit_path: str | None
    error_message: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResumeRestartSummary:
    completed_chunk_ids: tuple[str, ...]
    failed_chunk_ids: tuple[str, ...]
    missing_chunk_ids: tuple[str, ...]
    partial_tmp_paths: tuple[str, ...]
    manifest_inconsistencies: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "completed_chunk_ids": list(self.completed_chunk_ids),
            "failed_chunk_ids": list(self.failed_chunk_ids),
            "missing_chunk_ids": list(self.missing_chunk_ids),
            "partial_tmp_paths": list(self.partial_tmp_paths),
            "manifest_inconsistencies": list(self.manifest_inconsistencies),
        }


@dataclass(frozen=True)
class ChunkPlanDistributionAudit:
    status: str
    chunk_count: int
    date_chunk_count: int
    code_chunk_count: int
    date_start: str | None
    date_end: str | None
    code_count_min: int
    code_count_max: int
    expected_row_count_min: int
    expected_row_count_max: int
    empty_chunk_ids: tuple[str, ...]
    overlap_count: int
    gap_count: int
    duplicate_chunk_id_count: int
    data_source_type_consistent: bool
    feature_version_consistent: bool
    schema_version_consistent: bool
    messages: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["empty_chunk_ids"] = list(self.empty_chunk_ids)
        payload["messages"] = list(self.messages)
        return payload


@dataclass(frozen=True)
class NoWriteChunkValidationResult:
    status: str
    checked_chunk_count: int
    chunks_with_input_rows: int
    chunks_with_empty_inputs: int
    schema_validation_status: str
    leakage_audit_status: str
    output_paths_resolved: bool
    tmp_final_paths_separated: bool
    feature_output_written: bool
    messages: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["messages"] = list(self.messages)
        return payload


@dataclass(frozen=True)
class ControlledChunkExecutionResult:
    status: str
    run_id: str
    chunk_id: str | None
    executed_chunk_count: int
    max_chunks_to_execute: int
    row_count: int
    eligible_count: int
    excluded_count: int
    schema_validation_status: str
    leakage_audit_status: str
    tmp_output_path: str | None
    final_output_path: str | None
    chunk_manifest_path: str | None
    chunk_audit_path: str | None
    run_manifest_path: str | None
    error_message: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledExecutionFailureInjection:
    force_schema_validation_failure: bool = False
    force_leakage_audit_failure: bool = False
    force_write_failure: bool = False
    force_atomic_move_failure: bool = False

    @property
    def enabled(self) -> bool:
        return any(
            (
                self.force_schema_validation_failure,
                self.force_leakage_audit_failure,
                self.force_write_failure,
                self.force_atomic_move_failure,
            )
        )

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


def resolve_full_range_paths(
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
) -> FullRangePaths:
    root = Path(runtime_dir) / "candidate_ai"
    return FullRangePaths(
        runtime_dir=Path(runtime_dir),
        feature_dir=root / "features" / "full_range",
        manifest_dir=root / "manifests" / "full_range",
        audit_dir=root / "audit" / "full_range",
        tmp_dir=root / "tmp" / "full_range",
        report_dir=Path(report_dir),
    )


def build_full_range_chunk_plan(
    records: Iterable[Mapping[str, Any]],
    *,
    run_id: str,
    data_source_type: str,
    feature_version: str = DEFAULT_FULL_RANGE_FEATURE_VERSION,
    schema_version: str = DEFAULT_FULL_RANGE_SCHEMA_VERSION,
    max_codes_per_chunk: int = DEFAULT_MAX_CODES_PER_CHUNK,
) -> list[FullRangeChunkPlan]:
    rows = [dict(record) for record in records]
    if max_codes_per_chunk <= 0:
        raise ValueError("max_codes_per_chunk must be positive")
    date_chunks = _month_date_chunks(_record_dates(rows))
    code_chunks = _code_chunks(_record_codes(rows), max_codes_per_chunk=max_codes_per_chunk)
    plans: list[FullRangeChunkPlan] = []
    row_counter = Counter((str(row.get("Date") or ""), str(row.get("Code") or "")) for row in rows)
    for date_start, date_end in date_chunks:
        for codes in code_chunks:
            chunk_id = _chunk_id(run_id, date_start, date_end, codes)
            expected_rows = sum(
                count
                for (date_value, code), count in row_counter.items()
                if date_start <= date_value <= date_end and code in codes
            )
            plans.append(
                FullRangeChunkPlan(
                    run_id=run_id,
                    chunk_id=chunk_id,
                    date_start=date_start,
                    date_end=date_end,
                    code_start=codes[0] if codes else None,
                    code_end=codes[-1] if codes else None,
                    codes=tuple(codes),
                    code_count=len(codes),
                    expected_input_rows_optional=expected_rows,
                    status="PLANNED",
                    data_source_type=data_source_type,
                    feature_version=feature_version,
                    schema_version=schema_version,
                )
            )
    return plans


def build_run_manifest(
    *,
    run_id: str,
    records: Iterable[Mapping[str, Any]],
    chunk_plans: Iterable[FullRangeChunkPlan],
    data_source_type: str,
    feature_version: str = DEFAULT_FULL_RANGE_FEATURE_VERSION,
    schema_version: str = DEFAULT_FULL_RANGE_SCHEMA_VERSION,
    readiness_status: str = DEFAULT_READINESS_STATUS,
) -> FullRangeRunManifest:
    rows = [dict(record) for record in records]
    chunks = list(chunk_plans)
    dates = _record_dates(rows)
    codes = _record_codes(rows)
    return FullRangeRunManifest(
        run_id=run_id,
        created_at=_now_utc(),
        data_source_type=data_source_type,
        feature_version=feature_version,
        schema_version=schema_version,
        date_min=dates[0] if dates else None,
        date_max=dates[-1] if dates else None,
        code_count=len(codes),
        chunk_count=len(chunks),
        completed_chunk_count=0,
        failed_chunk_count=0,
        skipped_chunk_count=0,
        readiness_status=readiness_status,
    )


def check_resume_restart(
    chunk_plans: Iterable[FullRangeChunkPlan],
    *,
    manifest_dir: Path | str,
    tmp_dir: Path | str,
) -> ResumeRestartSummary:
    plans = list(chunk_plans)
    planned_ids = {plan.chunk_id for plan in plans}
    plan_run_ids = {plan.run_id for plan in plans}
    existing = {
        chunk_id: manifest
        for chunk_id, manifest in _read_existing_chunk_manifests(Path(manifest_dir)).items()
        if chunk_id.startswith("corrupt:") or not manifest.get("run_id") or str(manifest.get("run_id") or "") in plan_run_ids
    }
    completed = sorted(chunk_id for chunk_id, manifest in existing.items() if manifest.get("status") in {"SUCCESS", "COMPLETED"})
    failed = sorted(chunk_id for chunk_id, manifest in existing.items() if manifest.get("status") in {"FAILED", "ERROR"})
    missing = sorted(planned_ids - set(existing))
    inconsistencies: list[str] = []
    for chunk_id, manifest in existing.items():
        if chunk_id.startswith("duplicate:"):
            inconsistencies.append(f"duplicate_chunk_manifest:{manifest.get('duplicate_chunk_id') or chunk_id}")
            continue
        if chunk_id not in planned_ids:
            inconsistencies.append(f"unexpected_chunk_manifest:{chunk_id}")
        status = str(manifest.get("status") or "")
        if status not in {"SUCCESS", "COMPLETED", "FAILED", "ERROR", "SKIPPED"}:
            inconsistencies.append(f"unknown_status:{chunk_id}:{status or '(missing)'}")
        for key in ("output_path", "audit_path", "manifest_path"):
            value = manifest.get(key)
            if value and not Path(str(value)).exists() and manifest.get("status") in {"SUCCESS", "COMPLETED"}:
                inconsistencies.append(f"missing_{key}:{chunk_id}")
    partial_paths = sorted(str(path) for path in Path(tmp_dir).rglob("*") if path.is_file()) if Path(tmp_dir).exists() else []
    return ResumeRestartSummary(
        completed_chunk_ids=tuple(completed),
        failed_chunk_ids=tuple(failed),
        missing_chunk_ids=tuple(missing),
        partial_tmp_paths=tuple(partial_paths),
        manifest_inconsistencies=tuple(sorted(inconsistencies)),
    )


def build_full_range_dry_run_summary(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "auto",
    max_codes_per_chunk: int = DEFAULT_MAX_CODES_PER_CHUNK,
    data_source_type: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    run_id = run_id or f"phase4m_full_range_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    paths.ensure_dirs()
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format=input_format)
    if discovery.status != "FOUND" or discovery.path is None or discovery.storage_format is None:
        summary = _skipped_summary(run_id=run_id, discovery_message=discovery.message, data_source_type=data_source_type or "skipped")
        summary_path = paths.report_dir / "phase4m_full_range_dry_run_summary.json"
        _write_json(summary_path, summary)
        summary["summary_path"] = str(summary_path)
        return summary
    try:
        records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    except (StorageBackendError, ImportError, RuntimeError) as exc:
        summary = _skipped_summary(run_id=run_id, discovery_message=f"could not read normalized data: {type(exc).__name__}", data_source_type=data_source_type or "skipped")
        summary_path = paths.report_dir / "phase4m_full_range_dry_run_summary.json"
        _write_json(summary_path, summary)
        summary["summary_path"] = str(summary_path)
        return summary
    source_type = data_source_type or detect_full_range_data_source_type(runtime_dir)
    chunk_plan = build_full_range_chunk_plan(records, run_id=run_id, data_source_type=source_type, max_codes_per_chunk=max_codes_per_chunk)
    run_manifest = build_run_manifest(run_id=run_id, records=records, chunk_plans=chunk_plan, data_source_type=source_type)
    resume = check_resume_restart(chunk_plan, manifest_dir=paths.manifest_dir, tmp_dir=paths.tmp_dir)
    run_manifest_path = paths.manifest_dir / f"{run_id}_run_manifest.json"
    chunk_plan_path = paths.manifest_dir / f"{run_id}_chunk_plan.json"
    summary_path = paths.report_dir / "phase4m_full_range_dry_run_summary.json"
    _write_json(run_manifest_path, run_manifest.to_dict())
    _write_json(chunk_plan_path, {"run_id": run_id, "chunks": [plan.to_dict() for plan in chunk_plan]})
    dates = _record_dates(records)
    codes = _record_codes(records)
    summary = {
        "status": "OK",
        "mode": "dry_run_only",
        "feature_generation_executed": False,
        "run_id": run_id,
        "data_source_type": source_type,
        "storage_format": discovery.storage_format,
        "input_path": str(discovery.path),
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "code_count": len(codes),
        "input_row_count": len(records),
        "chunk_count": len(chunk_plan),
        "run_manifest_path": str(run_manifest_path),
        "chunk_plan_path": str(chunk_plan_path),
        "resume_restart_summary": resume.to_dict(),
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def audit_chunk_plan_distribution(chunk_plans: Iterable[FullRangeChunkPlan]) -> ChunkPlanDistributionAudit:
    plans = list(chunk_plans)
    if not plans:
        return ChunkPlanDistributionAudit(
            status="ERROR",
            chunk_count=0,
            date_chunk_count=0,
            code_chunk_count=0,
            date_start=None,
            date_end=None,
            code_count_min=0,
            code_count_max=0,
            expected_row_count_min=0,
            expected_row_count_max=0,
            empty_chunk_ids=(),
            overlap_count=0,
            gap_count=0,
            duplicate_chunk_id_count=0,
            data_source_type_consistent=False,
            feature_version_consistent=False,
            schema_version_consistent=False,
            messages=("chunk plan is empty",),
        )
    chunk_ids = [plan.chunk_id for plan in plans]
    duplicate_count = len(chunk_ids) - len(set(chunk_ids))
    date_ranges = sorted({(plan.date_start, plan.date_end) for plan in plans})
    code_ranges = sorted({(plan.code_start or "", plan.code_end or "") for plan in plans})
    code_counts = [plan.code_count for plan in plans]
    row_counts = [int(plan.expected_input_rows_optional or 0) for plan in plans]
    empty = tuple(sorted(plan.chunk_id for plan in plans if int(plan.expected_input_rows_optional or 0) <= 0 or plan.code_count <= 0))
    overlap_count, gap_count = _date_overlap_gap_counts(date_ranges)
    data_source_type_consistent = len({plan.data_source_type for plan in plans}) == 1
    feature_version_consistent = len({plan.feature_version for plan in plans}) == 1
    schema_version_consistent = len({plan.schema_version for plan in plans}) == 1
    messages: list[str] = []
    if duplicate_count:
        messages.append("duplicate chunk_id detected")
    if empty:
        messages.append("empty chunk detected")
    if overlap_count:
        messages.append("overlap detected")
    if gap_count:
        messages.append("gap detected")
    if not data_source_type_consistent:
        messages.append("data_source_type mismatch")
    if not feature_version_consistent:
        messages.append("feature_version mismatch")
    if not schema_version_consistent:
        messages.append("schema_version mismatch")
    status = "OK" if not messages else "ERROR"
    return ChunkPlanDistributionAudit(
        status=status,
        chunk_count=len(plans),
        date_chunk_count=len(date_ranges),
        code_chunk_count=len(code_ranges),
        date_start=min(plan.date_start for plan in plans),
        date_end=max(plan.date_end for plan in plans),
        code_count_min=min(code_counts),
        code_count_max=max(code_counts),
        expected_row_count_min=min(row_counts),
        expected_row_count_max=max(row_counts),
        empty_chunk_ids=empty,
        overlap_count=overlap_count,
        gap_count=gap_count,
        duplicate_chunk_id_count=duplicate_count,
        data_source_type_consistent=data_source_type_consistent,
        feature_version_consistent=feature_version_consistent,
        schema_version_consistent=schema_version_consistent,
        messages=tuple(messages),
    )


def validate_chunks_no_write(
    records: Iterable[Mapping[str, Any]],
    chunk_plans: Iterable[FullRangeChunkPlan],
    *,
    paths: FullRangePaths,
) -> NoWriteChunkValidationResult:
    rows = [dict(record) for record in records]
    plans = list(chunk_plans)
    messages: list[str] = []
    chunks_with_input_rows = 0
    chunks_with_empty_inputs = 0
    schema_statuses: list[str] = []
    for plan in plans:
        chunk_rows = _select_chunk_records(rows, plan)
        if chunk_rows:
            chunks_with_input_rows += 1
        else:
            chunks_with_empty_inputs += 1
            messages.append(f"empty input rows for chunk: {plan.chunk_id}")
            continue
        validation = validate_daily_quotes_normalized_input(chunk_rows, as_of_date=plan.date_end)
        schema_statuses.append("OK" if validation.is_valid else "ERROR")
    leakage_status = _run_no_write_leakage_probe(plans)
    output_paths_resolved = all((paths.feature_dir, paths.manifest_dir, paths.audit_dir, paths.tmp_dir, paths.report_dir))
    tmp_final_paths_separated = paths.tmp_dir != paths.feature_dir and paths.tmp_dir != paths.manifest_dir and paths.tmp_dir != paths.audit_dir
    schema_validation_status = "OK" if schema_statuses and all(status == "OK" for status in schema_statuses) else "ERROR"
    status = "OK"
    if chunks_with_empty_inputs or schema_validation_status != "OK":
        status = "ERROR"
    if leakage_status != "OK":
        status = "ERROR"
    if not output_paths_resolved or not tmp_final_paths_separated:
        status = "ERROR"
    return NoWriteChunkValidationResult(
        status=status,
        checked_chunk_count=len(plans),
        chunks_with_input_rows=chunks_with_input_rows,
        chunks_with_empty_inputs=chunks_with_empty_inputs,
        schema_validation_status=schema_validation_status,
        leakage_audit_status=leakage_status,
        output_paths_resolved=bool(output_paths_resolved),
        tmp_final_paths_separated=tmp_final_paths_separated,
        feature_output_written=False,
        messages=tuple(messages),
    )


def evaluate_no_write_final_gate(
    *,
    distribution: ChunkPlanDistributionAudit,
    resume: ResumeRestartSummary,
    validation: NoWriteChunkValidationResult,
    data_source_type: str,
    feature_version: str,
    schema_version: str,
) -> str:
    if distribution.chunk_count == 0:
        return NO_WRITE_GATE_SKIPPED_NO_DATA
    if distribution.status != "OK":
        return NO_WRITE_GATE_BLOCKED_BY_CHUNK_PLAN
    if resume.manifest_inconsistencies or resume.partial_tmp_paths:
        return NO_WRITE_GATE_BLOCKED_BY_RESUME_STATE
    if validation.status != "OK":
        if validation.schema_validation_status != "OK":
            return NO_WRITE_GATE_BLOCKED_BY_SCHEMA
        if validation.leakage_audit_status != "OK":
            return NO_WRITE_GATE_BLOCKED_BY_LEAKAGE
        return NO_WRITE_GATE_BLOCKED_BY_NO_WRITE_VALIDATION
    if not data_source_type or not feature_version or not schema_version:
        return NO_WRITE_GATE_BLOCKED_BY_NO_WRITE_VALIDATION
    return NO_WRITE_GATE_READY


def build_full_range_no_write_summary(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "auto",
    max_codes_per_chunk: int = DEFAULT_MAX_CODES_PER_CHUNK,
    data_source_type: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    run_id = run_id or f"phase4n_no_write_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    paths.ensure_dirs()
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format=input_format)
    summary_path = paths.report_dir / "phase4n_full_range_no_write_summary.json"
    if discovery.status != "FOUND" or discovery.path is None or discovery.storage_format is None:
        summary = {
            "status": "SKIPPED",
            "gate_status": NO_WRITE_GATE_SKIPPED_NO_DATA,
            "mode": "no_write",
            "feature_generation_executed": False,
            "feature_output_written": False,
            "run_id": run_id,
            "data_source_type": data_source_type or "skipped",
            "reason": discovery.message,
            "summary_path": str(summary_path),
        }
        _write_json(summary_path, summary)
        return summary
    try:
        records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    except (StorageBackendError, ImportError, RuntimeError) as exc:
        summary = {
            "status": "SKIPPED",
            "gate_status": NO_WRITE_GATE_SKIPPED_NO_DATA,
            "mode": "no_write",
            "feature_generation_executed": False,
            "feature_output_written": False,
            "run_id": run_id,
            "data_source_type": data_source_type or "skipped",
            "reason": f"could not read normalized data: {type(exc).__name__}",
            "summary_path": str(summary_path),
        }
        _write_json(summary_path, summary)
        return summary
    source_type = data_source_type or detect_full_range_data_source_type(runtime_dir)
    plans = build_full_range_chunk_plan(records, run_id=run_id, data_source_type=source_type, max_codes_per_chunk=max_codes_per_chunk)
    distribution = audit_chunk_plan_distribution(plans)
    validation = validate_chunks_no_write(records, plans, paths=paths)
    resume = check_resume_restart(plans, manifest_dir=paths.manifest_dir, tmp_dir=paths.tmp_dir)
    feature_version = plans[0].feature_version if plans else DEFAULT_FULL_RANGE_FEATURE_VERSION
    schema_version = plans[0].schema_version if plans else DEFAULT_FULL_RANGE_SCHEMA_VERSION
    gate_status = evaluate_no_write_final_gate(
        distribution=distribution,
        resume=resume,
        validation=validation,
        data_source_type=source_type,
        feature_version=feature_version,
        schema_version=schema_version,
    )
    dates = _record_dates(records)
    codes = _record_codes(records)
    summary = {
        "status": "OK" if gate_status == NO_WRITE_GATE_READY else "BLOCKED",
        "gate_status": gate_status,
        "mode": "no_write",
        "feature_generation_executed": False,
        "feature_output_written": False,
        "run_id": run_id,
        "data_source_type": source_type,
        "storage_format": discovery.storage_format,
        "input_path": str(discovery.path),
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "code_count": len(codes),
        "input_row_count": len(records),
        "chunk_count": len(plans),
        "distribution_audit": distribution.to_dict(),
        "no_write_validation": validation.to_dict(),
        "resume_restart_summary": resume.to_dict(),
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def execute_full_range_chunk_controlled(
    records: Iterable[Mapping[str, Any]],
    chunk_plan: FullRangeChunkPlan,
    *,
    paths: FullRangePaths,
    max_chunks_to_execute: int = 1,
    failure_injection: ControlledExecutionFailureInjection | None = None,
) -> ControlledChunkExecutionResult:
    failure_injection = failure_injection or ControlledExecutionFailureInjection()
    if max_chunks_to_execute != 1:
        return ControlledChunkExecutionResult(
            status=CONTROLLED_EXECUTION_FAILED,
            run_id=chunk_plan.run_id,
            chunk_id=chunk_plan.chunk_id,
            executed_chunk_count=0,
            max_chunks_to_execute=max_chunks_to_execute,
            row_count=0,
            eligible_count=0,
            excluded_count=0,
            schema_validation_status="SKIPPED",
            leakage_audit_status="SKIPPED",
            tmp_output_path=None,
            final_output_path=None,
            chunk_manifest_path=None,
            chunk_audit_path=None,
            run_manifest_path=None,
            error_message="controlled execution requires max_chunks_to_execute=1",
        )
    paths.ensure_dirs()
    source_rows = _select_controlled_source_records([dict(record) for record in records], chunk_plan)
    if not source_rows:
        return _controlled_failed_result(chunk_plan, paths, "selected chunk has no input rows")
    try:
        loader_result = adapt_daily_quotes_normalized(
            source_rows,
            as_of_date=chunk_plan.date_end,
            lookback_rows=80,
            source_snapshot_id=f"full_range_controlled:{chunk_plan.chunk_id}",
        )
        build_result = build_candidate_features_mock_with_audit(
            loader_result.rows,
            as_of_date=chunk_plan.date_end,
            feature_version=chunk_plan.feature_version,
            source_snapshot_id=f"full_range_controlled:{chunk_plan.chunk_id}",
        )
    except Exception as exc:  # pragma: no cover - defensive manifest path
        return _controlled_failed_result(chunk_plan, paths, f"feature build failed: {type(exc).__name__}")

    safe_chunk = _safe_name(chunk_plan.chunk_id)
    tmp_output = paths.tmp_dir / chunk_plan.run_id / f"{safe_chunk}.tmp.json"
    final_output = paths.feature_dir / chunk_plan.run_id / f"{safe_chunk}.json"
    chunk_manifest_path = paths.manifest_dir / f"{chunk_plan.run_id}_{safe_chunk}_manifest.json"
    chunk_audit_path = paths.audit_dir / f"{chunk_plan.run_id}_{safe_chunk}_audit.json"
    if failure_injection.force_write_failure:
        return _controlled_failed_result(
            chunk_plan,
            paths,
            "write failure injected",
            row_count=build_result.audit.row_count,
            eligible_count=build_result.audit.eligible_count,
            excluded_count=build_result.audit.excluded_count,
            schema_validation_status="OK" if build_result.validation.is_valid else "ERROR",
            leakage_audit_status=build_result.audit.status,
        )
    _write_json(tmp_output, {"rows": build_result.rows})
    audit_payload = build_result.audit.to_dict()
    audit_payload.update(
        {
            "controlled_execution": True,
            "chunk_id": chunk_plan.chunk_id,
            "tmp_output_path": str(tmp_output),
            "final_output_path": str(final_output),
        }
    )
    _write_json(chunk_audit_path, audit_payload)
    schema_status = "OK" if build_result.validation.is_valid else "ERROR"
    leakage_status = build_result.audit.status
    error_message = "schema validation or leakage audit failed"
    if failure_injection.force_schema_validation_failure:
        schema_status = "ERROR"
        error_message = "validation failure injected"
    if failure_injection.force_leakage_audit_failure:
        leakage_status = "ERROR"
        error_message = "leakage failure injected"
    if schema_status == "OK" and leakage_status == "OK":
        if failure_injection.force_atomic_move_failure:
            manifest = FullRangeChunkManifest(
                run_id=chunk_plan.run_id,
                chunk_id=chunk_plan.chunk_id,
                status="FAILED",
                date_start=chunk_plan.date_start,
                date_end=chunk_plan.date_end,
                code_count=chunk_plan.code_count,
                row_count=build_result.audit.row_count,
                eligible_count=build_result.audit.eligible_count,
                excluded_count=build_result.audit.excluded_count,
                schema_validation_status=schema_status,
                leakage_audit_status=leakage_status,
                output_path=None,
                manifest_path=str(chunk_manifest_path),
                audit_path=str(chunk_audit_path),
                error_message="atomic move failure injected",
            )
            _write_json(chunk_manifest_path, manifest.to_dict())
            return ControlledChunkExecutionResult(
                status=CONTROLLED_EXECUTION_FAILED,
                run_id=chunk_plan.run_id,
                chunk_id=chunk_plan.chunk_id,
                executed_chunk_count=1,
                max_chunks_to_execute=max_chunks_to_execute,
                row_count=build_result.audit.row_count,
                eligible_count=build_result.audit.eligible_count,
                excluded_count=build_result.audit.excluded_count,
                schema_validation_status=schema_status,
                leakage_audit_status=leakage_status,
                tmp_output_path=str(tmp_output),
                final_output_path=None,
                chunk_manifest_path=str(chunk_manifest_path),
                chunk_audit_path=str(chunk_audit_path),
                run_manifest_path=None,
                error_message="atomic move failure injected",
            )
        promote_tmp_to_final(tmp_output, final_output)
        manifest = FullRangeChunkManifest(
            run_id=chunk_plan.run_id,
            chunk_id=chunk_plan.chunk_id,
            status="SUCCESS",
            date_start=chunk_plan.date_start,
            date_end=chunk_plan.date_end,
            code_count=chunk_plan.code_count,
            row_count=build_result.audit.row_count,
            eligible_count=build_result.audit.eligible_count,
            excluded_count=build_result.audit.excluded_count,
            schema_validation_status=schema_status,
            leakage_audit_status=leakage_status,
            output_path=str(final_output),
            manifest_path=str(chunk_manifest_path),
            audit_path=str(chunk_audit_path),
            error_message=None,
        )
        _write_json(chunk_manifest_path, manifest.to_dict())
        return ControlledChunkExecutionResult(
            status=CONTROLLED_EXECUTION_READY,
            run_id=chunk_plan.run_id,
            chunk_id=chunk_plan.chunk_id,
            executed_chunk_count=1,
            max_chunks_to_execute=max_chunks_to_execute,
            row_count=build_result.audit.row_count,
            eligible_count=build_result.audit.eligible_count,
            excluded_count=build_result.audit.excluded_count,
            schema_validation_status=schema_status,
            leakage_audit_status=leakage_status,
            tmp_output_path=str(tmp_output),
            final_output_path=str(final_output),
            chunk_manifest_path=str(chunk_manifest_path),
            chunk_audit_path=str(chunk_audit_path),
            run_manifest_path=None,
            error_message=None,
        )

    manifest = FullRangeChunkManifest(
        run_id=chunk_plan.run_id,
        chunk_id=chunk_plan.chunk_id,
        status="FAILED",
        date_start=chunk_plan.date_start,
        date_end=chunk_plan.date_end,
        code_count=chunk_plan.code_count,
        row_count=build_result.audit.row_count,
        eligible_count=build_result.audit.eligible_count,
        excluded_count=build_result.audit.excluded_count,
        schema_validation_status=schema_status,
        leakage_audit_status=leakage_status,
        output_path=None,
        manifest_path=str(chunk_manifest_path),
        audit_path=str(chunk_audit_path),
        error_message=error_message,
    )
    _write_json(chunk_manifest_path, manifest.to_dict())
    return ControlledChunkExecutionResult(
        status=CONTROLLED_EXECUTION_FAILED,
        run_id=chunk_plan.run_id,
        chunk_id=chunk_plan.chunk_id,
        executed_chunk_count=1,
        max_chunks_to_execute=max_chunks_to_execute,
        row_count=build_result.audit.row_count,
        eligible_count=build_result.audit.eligible_count,
        excluded_count=build_result.audit.excluded_count,
        schema_validation_status=schema_status,
        leakage_audit_status=leakage_status,
        tmp_output_path=str(tmp_output),
        final_output_path=None,
        chunk_manifest_path=str(chunk_manifest_path),
        chunk_audit_path=str(chunk_audit_path),
        run_manifest_path=None,
        error_message=error_message,
    )


def promote_tmp_to_final(tmp_path: Path | str, final_path: Path | str) -> Path:
    tmp = Path(tmp_path)
    final = Path(final_path)
    final.parent.mkdir(parents=True, exist_ok=True)
    tmp.replace(final)
    return final


def build_full_range_controlled_summary(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "auto",
    max_codes_per_chunk: int = 30,
    max_chunks_to_execute: int = 1,
    data_source_type: str | None = None,
    run_id: str | None = None,
    failure_injection: ControlledExecutionFailureInjection | None = None,
) -> dict[str, Any]:
    failure_injection = failure_injection or ControlledExecutionFailureInjection()
    run_id = run_id or f"phase4o_controlled_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    paths.ensure_dirs()
    no_write = build_full_range_no_write_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format=input_format,
        max_codes_per_chunk=max_codes_per_chunk,
        data_source_type=data_source_type,
        run_id=run_id,
    )
    summary_path = paths.report_dir / "phase4o_full_range_controlled_summary.json"
    if no_write.get("gate_status") != NO_WRITE_GATE_READY:
        summary = {
            "status": "BLOCKED",
            "controlled_status": CONTROLLED_EXECUTION_BLOCKED,
            "run_id": run_id,
            "max_chunks_to_execute": max_chunks_to_execute,
            "executed_chunk_count": 0,
            "no_write_gate_status": no_write.get("gate_status"),
            "feature_generation_executed": False,
            "feature_output_written": False,
            "summary_path": str(summary_path),
        }
        _write_json(summary_path, summary)
        return summary
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format=input_format)
    if discovery.status != "FOUND" or discovery.path is None or discovery.storage_format is None:
        summary = {
            "status": "SKIPPED",
            "controlled_status": CONTROLLED_EXECUTION_BLOCKED,
            "run_id": run_id,
            "max_chunks_to_execute": max_chunks_to_execute,
            "executed_chunk_count": 0,
            "reason": discovery.message,
            "feature_generation_executed": False,
            "feature_output_written": False,
            "summary_path": str(summary_path),
        }
        _write_json(summary_path, summary)
        return summary
    records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    source_type = data_source_type or detect_full_range_data_source_type(runtime_dir)
    plans = build_full_range_chunk_plan(records, run_id=run_id, data_source_type=source_type, max_codes_per_chunk=max_codes_per_chunk)
    if not plans:
        summary = {
            "status": "SKIPPED",
            "controlled_status": CONTROLLED_EXECUTION_BLOCKED,
            "run_id": run_id,
            "max_chunks_to_execute": max_chunks_to_execute,
            "executed_chunk_count": 0,
            "reason": "chunk plan is empty",
            "feature_generation_executed": False,
            "feature_output_written": False,
            "summary_path": str(summary_path),
        }
        _write_json(summary_path, summary)
        return summary
    selected_chunk = plans[0]
    execution = execute_full_range_chunk_controlled(
        records,
        selected_chunk,
        paths=paths,
        max_chunks_to_execute=max_chunks_to_execute,
        failure_injection=failure_injection,
    )
    run_manifest_path = paths.manifest_dir / f"{run_id}_run_manifest.json"
    run_manifest = build_run_manifest(
        run_id=run_id,
        records=records,
        chunk_plans=plans,
        data_source_type=source_type,
        readiness_status="CONTROLLED_EXECUTION_DONE" if execution.status == CONTROLLED_EXECUTION_READY else "CONTROLLED_EXECUTION_FAILED",
    ).to_dict()
    run_manifest.update(
        {
            "completed_chunk_count": 1 if execution.status == CONTROLLED_EXECUTION_READY else 0,
            "failed_chunk_count": 1 if execution.status == CONTROLLED_EXECUTION_FAILED else 0,
            "skipped_chunk_count": max(0, len(plans) - execution.executed_chunk_count),
            "last_updated_at": _now_utc(),
        }
    )
    _write_json(run_manifest_path, run_manifest)
    execution_payload = execution.to_dict()
    execution_payload["run_manifest_path"] = str(run_manifest_path)
    summary = {
        "status": "OK" if execution.status == CONTROLLED_EXECUTION_READY else "ERROR",
        "controlled_status": execution.status,
        "run_id": run_id,
        "data_source_type": source_type,
        "max_chunks_to_execute": max_chunks_to_execute,
        "executed_chunk_count": execution.executed_chunk_count,
        "selected_chunk_id": execution.chunk_id,
        "feature_generation_executed": execution.executed_chunk_count == 1,
        "feature_output_written": bool(execution.final_output_path),
        "tmp_to_final_atomic_move": bool(execution.final_output_path),
        "schema_validation_status": execution.schema_validation_status,
        "leakage_audit_status": execution.leakage_audit_status,
        "feature_output_path": execution.final_output_path,
        "tmp_output_path": execution.tmp_output_path,
        "chunk_manifest_path": execution.chunk_manifest_path,
        "chunk_audit_path": execution.chunk_audit_path,
        "run_manifest_path": str(run_manifest_path),
        "row_count": execution.row_count,
        "eligible_count": execution.eligible_count,
        "excluded_count": execution.excluded_count,
        "no_write_gate_status": no_write.get("gate_status"),
        "failure_injection": failure_injection.to_dict(),
        "error_message": execution.error_message,
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def build_full_range_resume_controlled_summary(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "auto",
    max_codes_per_chunk: int = 30,
    max_chunks_to_execute: int = 2,
    max_allowed_chunks: int = 2,
    data_source_type: str | None = None,
    run_id: str | None = None,
    stop_on_first_failure: bool = True,
    max_failed_chunks_allowed: int = 0,
) -> dict[str, Any]:
    run_id = run_id or f"phase4q_resume_controlled_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    paths.ensure_dirs()
    summary_path = paths.report_dir / "phase4q_resume_aware_controlled_summary.json"
    if max_chunks_to_execute < 0 or max_chunks_to_execute > max_allowed_chunks:
        summary = _resume_controlled_base_summary(
            run_id=run_id,
            runner_status=RESUME_CONTROLLED_BLOCKED,
            status="BLOCKED",
            max_chunks_to_execute=max_chunks_to_execute,
            summary_path=summary_path,
        )
        summary["reason"] = f"resume-aware controlled runner requires max_chunks_to_execute <= {max_allowed_chunks}"
        _write_json(summary_path, summary)
        return summary
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format=input_format)
    if discovery.status != "FOUND" or discovery.path is None or discovery.storage_format is None:
        summary = _resume_controlled_base_summary(
            run_id=run_id,
            runner_status=RESUME_CONTROLLED_SKIPPED,
            status="SKIPPED",
            max_chunks_to_execute=max_chunks_to_execute,
            summary_path=summary_path,
        )
        summary["reason"] = discovery.message
        _write_json(summary_path, summary)
        return summary
    try:
        records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    except (StorageBackendError, ImportError, RuntimeError) as exc:
        summary = _resume_controlled_base_summary(
            run_id=run_id,
            runner_status=RESUME_CONTROLLED_SKIPPED,
            status="SKIPPED",
            max_chunks_to_execute=max_chunks_to_execute,
            summary_path=summary_path,
        )
        summary["reason"] = f"could not read normalized data: {type(exc).__name__}"
        _write_json(summary_path, summary)
        return summary
    source_type = data_source_type or detect_full_range_data_source_type(runtime_dir)
    plans = build_full_range_chunk_plan(records, run_id=run_id, data_source_type=source_type, max_codes_per_chunk=max_codes_per_chunk)
    resume = check_resume_restart(plans, manifest_dir=paths.manifest_dir, tmp_dir=paths.tmp_dir)
    if resume.manifest_inconsistencies:
        summary = _resume_controlled_base_summary(
            run_id=run_id,
            runner_status=RESUME_CONTROLLED_BLOCKED,
            status="BLOCKED",
            max_chunks_to_execute=max_chunks_to_execute,
            summary_path=summary_path,
        )
        summary.update(
            {
                "planned_chunk_count": len(plans),
                "blocked_inconsistency_count": len(resume.manifest_inconsistencies),
                "partial_tmp_warning_count": len(resume.partial_tmp_paths),
                "resume_restart_summary": resume.to_dict(),
                "reason": "manifest inconsistency detected",
            }
        )
        _write_json(summary_path, summary)
        return summary
    plan_by_id = {plan.chunk_id: plan for plan in plans}
    completed_ids = set(resume.completed_chunk_ids)
    failed_ids = [chunk_id for chunk_id in resume.failed_chunk_ids if chunk_id in plan_by_id]
    missing_ids = [chunk_id for chunk_id in resume.missing_chunk_ids if chunk_id in plan_by_id]
    candidates = [plan_by_id[chunk_id] for chunk_id in failed_ids + missing_ids]
    selected = candidates[:max_chunks_to_execute]
    results: list[ControlledChunkExecutionResult] = []
    stopped_on_failure = False
    stop_reason: str | None = None
    for plan in selected:
        result = execute_full_range_chunk_controlled(records, plan, paths=paths, max_chunks_to_execute=1)
        results.append(result)
        current_failed_count = sum(1 for item in results if item.status == CONTROLLED_EXECUTION_FAILED)
        if current_failed_count > max_failed_chunks_allowed:
            stopped_on_failure = True
            stop_reason = "max_failed_chunks_allowed exceeded"
            if stop_on_first_failure:
                break
    success_count = sum(1 for result in results if result.status == CONTROLLED_EXECUTION_READY)
    failed_count = sum(1 for result in results if result.status == CONTROLLED_EXECUTION_FAILED)
    run_manifest_path = paths.manifest_dir / f"{run_id}_run_manifest.json"
    run_manifest = build_run_manifest(
        run_id=run_id,
        records=records,
        chunk_plans=plans,
        data_source_type=source_type,
        readiness_status=RESUME_CONTROLLED_READY if failed_count == 0 else CONTROLLED_EXECUTION_FAILED,
    ).to_dict()
    run_manifest.update(
        {
            "completed_chunk_count": len(completed_ids) + success_count,
            "failed_chunk_count": failed_count,
            "skipped_chunk_count": len(completed_ids),
            "last_updated_at": _now_utc(),
            "runner_status": RESUME_CONTROLLED_READY if failed_count == 0 else CONTROLLED_EXECUTION_FAILED,
            "executed_chunk_ids": [result.chunk_id for result in results if result.chunk_id],
            "stop_on_first_failure": stop_on_first_failure,
            "max_failed_chunks_allowed": max_failed_chunks_allowed,
            "stopped_on_failure": stopped_on_failure,
            "stop_reason": stop_reason,
        }
    )
    _write_json(run_manifest_path, run_manifest)
    summary = {
        "status": "OK" if failed_count == 0 else "ERROR",
        "runner_status": RESUME_CONTROLLED_READY if failed_count == 0 else CONTROLLED_EXECUTION_FAILED,
        "run_id": run_id,
        "data_source_type": source_type,
        "storage_format": discovery.storage_format,
        "max_chunks_to_execute": max_chunks_to_execute,
        "max_allowed_chunks": max_allowed_chunks,
        "stop_on_first_failure": stop_on_first_failure,
        "max_failed_chunks_allowed": max_failed_chunks_allowed,
        "planned_chunk_count": len(plans),
        "skipped_success_chunk_count": len(completed_ids),
        "rerun_failed_chunk_count": len(failed_ids),
        "run_missing_chunk_count": len(missing_ids),
        "executed_chunk_count": len(results),
        "blocked_inconsistency_count": 0,
        "partial_tmp_warning_count": len(resume.partial_tmp_paths),
        "completed_chunk_count": len(completed_ids) + success_count,
        "failed_chunk_count": failed_count,
        "stopped_on_failure": stopped_on_failure,
        "stop_reason": stop_reason,
        "feature_generation_executed": bool(results),
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "tmp_to_final_atomic_move": all(bool(result.final_output_path) for result in results) if results else False,
        "schema_validation_status": "OK" if all(result.schema_validation_status == "OK" for result in results) else "ERROR",
        "leakage_audit_status": "OK" if all(result.leakage_audit_status == "OK" for result in results) else "ERROR",
        "executed_chunk_ids": [result.chunk_id for result in results if result.chunk_id],
        "executions": [result.to_dict() for result in results],
        "resume_restart_summary": resume.to_dict(),
        "run_manifest_path": str(run_manifest_path),
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def build_first_controlled_batch_summary(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "auto",
    max_codes_per_chunk: int = 30,
    max_chunks_to_execute: int = 2,
    data_source_type: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    run_id = run_id or f"phase4s_first_batch_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    paths.ensure_dirs()
    summary_path = paths.report_dir / "phase4s_first_controlled_batch_summary.json"
    stop_on_first_failure = True
    max_failed_chunks_allowed = 0
    if max_chunks_to_execute != 2:
        summary = _first_batch_base_summary(
            run_id=run_id,
            status="BLOCKED",
            batch_status="FIRST_CONTROLLED_BATCH_BLOCKED",
            gate_status="BLOCKED_BY_EXECUTION_LIMIT",
            max_chunks_to_execute=max_chunks_to_execute,
            summary_path=summary_path,
        )
        summary["stop_reason"] = "Phase4-S requires max_chunks_to_execute=2"
        _write_json(summary_path, summary)
        return summary
    readiness = build_controlled_batch_readiness_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format=input_format,
        max_codes_per_chunk=max_codes_per_chunk,
        data_source_type=data_source_type,
        run_id=run_id,
    )
    gate_status = readiness.get("gate_status")
    gate_ready = (
        gate_status == BATCH_READINESS_READY
        and readiness.get("manifest_inconsistency_count") == 0
        and readiness.get("runtime_free_space_sufficient") is True
        and readiness.get("preflight_schema_validation_status") == "OK"
        and readiness.get("preflight_leakage_audit_status") == "OK"
    )
    if not gate_ready:
        summary = _first_batch_base_summary(
            run_id=run_id,
            status="BLOCKED",
            batch_status="FIRST_CONTROLLED_BATCH_BLOCKED",
            gate_status=str(gate_status or "UNKNOWN"),
            max_chunks_to_execute=max_chunks_to_execute,
            summary_path=summary_path,
        )
        summary.update(
            {
                "planned_chunk_count": readiness.get("chunk_count", 0),
                "stop_reason": "readiness gate is not READY",
                "readiness_summary": readiness,
            }
        )
        _write_json(summary_path, summary)
        return summary
    runner = build_full_range_resume_controlled_summary(
        runtime_dir=runtime_dir,
        report_dir=report_dir,
        input_format=input_format,
        max_codes_per_chunk=max_codes_per_chunk,
        max_chunks_to_execute=max_chunks_to_execute,
        data_source_type=data_source_type,
        run_id=run_id,
        stop_on_first_failure=stop_on_first_failure,
        max_failed_chunks_allowed=max_failed_chunks_allowed,
    )
    feature_output_written_count = sum(1 for item in runner.get("executions", []) if item.get("final_output_path"))
    failed_count = int(runner.get("failed_chunk_count") or 0)
    summary = {
        "status": "OK" if runner.get("status") == "OK" else "ERROR",
        "batch_status": "FIRST_CONTROLLED_BATCH_COMPLETED" if runner.get("status") == "OK" else "FIRST_CONTROLLED_BATCH_FAILED",
        "gate_status": gate_status,
        "run_id": run_id,
        "max_chunks_to_execute": max_chunks_to_execute,
        "stop_on_first_failure": stop_on_first_failure,
        "max_failed_chunks_allowed": max_failed_chunks_allowed,
        "planned_chunk_count": runner.get("planned_chunk_count", readiness.get("chunk_count", 0)),
        "executed_chunk_count": runner.get("executed_chunk_count", 0),
        "completed_chunk_count": runner.get("completed_chunk_count", 0),
        "failed_chunk_count": failed_count,
        "skipped_chunk_count": runner.get("skipped_success_chunk_count", 0),
        "feature_output_written_count": feature_output_written_count,
        "schema_validation_status": runner.get("schema_validation_status"),
        "leakage_audit_status": runner.get("leakage_audit_status"),
        "stopped_on_failure": bool(runner.get("stopped_on_failure")),
        "stop_reason": runner.get("stop_reason"),
        "tmp_to_final_atomic_move": runner.get("tmp_to_final_atomic_move"),
        "chunk_manifest_paths": [item.get("chunk_manifest_path") for item in runner.get("executions", [])],
        "run_manifest_path": runner.get("run_manifest_path"),
        "feature_generation_executed": runner.get("feature_generation_executed") is True,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "readiness_summary": readiness,
        "runner_summary": runner,
        "summary_path": str(summary_path),
    }
    if failed_count > max_failed_chunks_allowed:
        summary["status"] = "ERROR"
        summary["batch_status"] = "FIRST_CONTROLLED_BATCH_FAILED"
        summary["stopped_on_failure"] = True
        summary["stop_reason"] = summary["stop_reason"] or "max_failed_chunks_allowed exceeded"
    _write_json(summary_path, summary)
    return summary


def build_controlled_batch_readiness_summary(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "auto",
    max_codes_per_chunk: int = DEFAULT_MAX_CODES_PER_CHUNK,
    data_source_type: str | None = None,
    run_id: str | None = None,
    estimated_bytes_per_feature_row: int = 512,
) -> dict[str, Any]:
    run_id = run_id or f"phase4r_batch_readiness_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    paths.ensure_dirs()
    summary_path = paths.report_dir / "phase4r_controlled_batch_readiness_summary.json"
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format=input_format)
    if discovery.status != "FOUND" or discovery.path is None or discovery.storage_format is None:
        summary = _batch_readiness_base_summary(
            run_id=run_id,
            data_source_type=data_source_type or "skipped",
            gate_status=BATCH_READINESS_SKIPPED_NO_DATA,
            summary_path=summary_path,
        )
        summary["status"] = "SKIPPED"
        summary["recommended_next_action"] = "prepare normalized history before controlled batch execution"
        _write_json(summary_path, summary)
        return summary
    try:
        records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    except (StorageBackendError, ImportError, RuntimeError) as exc:
        summary = _batch_readiness_base_summary(
            run_id=run_id,
            data_source_type=data_source_type or "skipped",
            gate_status=BATCH_READINESS_SKIPPED_NO_DATA,
            summary_path=summary_path,
        )
        summary["status"] = "SKIPPED"
        summary["recommended_next_action"] = f"fix normalized data read error: {type(exc).__name__}"
        _write_json(summary_path, summary)
        return summary
    source_type = data_source_type or detect_full_range_data_source_type(runtime_dir)
    plans = build_full_range_chunk_plan(records, run_id=run_id, data_source_type=source_type, max_codes_per_chunk=max_codes_per_chunk)
    distribution = audit_chunk_plan_distribution(plans)
    validation = validate_chunks_no_write(records, plans, paths=paths)
    resume = check_resume_restart(plans, manifest_dir=paths.manifest_dir, tmp_dir=paths.tmp_dir)
    storage = _runtime_free_space_check(paths.runtime_dir)
    estimated_feature_rows = sum(int(plan.expected_input_rows_optional or 0) for plan in plans)
    estimated_output_size = estimated_feature_rows * max(1, estimated_bytes_per_feature_row)
    runtime_free_space_sufficient = (
        True
        if storage["status"] == "UNKNOWN"
        else bool(storage.get("free_bytes", 0) > estimated_output_size * 2)
    )
    feature_version_consistent = distribution.feature_version_consistent
    schema_version_consistent = distribution.schema_version_consistent
    data_source_type_consistent = distribution.data_source_type_consistent
    manifest_inconsistency_count = len(resume.manifest_inconsistencies)
    resume_state_consistent = manifest_inconsistency_count == 0
    gate_status = _controlled_batch_gate_status(
        chunk_count=len(plans),
        input_row_count=len(records),
        distribution_status=distribution.status,
        resume_state_consistent=resume_state_consistent,
        manifest_inconsistency_count=manifest_inconsistency_count,
        runtime_free_space_sufficient=runtime_free_space_sufficient,
        feature_version_consistent=feature_version_consistent,
        schema_version_consistent=schema_version_consistent,
        data_source_type_consistent=data_source_type_consistent,
        preflight_schema_validation_status=validation.schema_validation_status,
        preflight_leakage_audit_status=validation.leakage_audit_status,
    )
    summary = {
        "status": "READY" if gate_status == BATCH_READINESS_READY else "BLOCKED",
        "gate_status": gate_status,
        "run_id": run_id,
        "data_source_type": source_type,
        "storage_format": discovery.storage_format,
        "input_path": str(discovery.path),
        "chunk_count": len(plans),
        "date_chunk_count": distribution.date_chunk_count,
        "code_chunk_count": distribution.code_chunk_count,
        "input_row_count": len(records),
        "estimated_feature_row_count": estimated_feature_rows,
        "estimated_output_size_bytes": estimated_output_size,
        "runtime_free_space_check": storage,
        "runtime_free_space_sufficient": runtime_free_space_sufficient,
        "completed_chunk_count": len(resume.completed_chunk_ids),
        "failed_chunk_count": len(resume.failed_chunk_ids),
        "missing_chunk_count": len(resume.missing_chunk_ids),
        "partial_tmp_warning_count": len(resume.partial_tmp_paths),
        "manifest_inconsistency_count": manifest_inconsistency_count,
        "feature_version_consistent": feature_version_consistent,
        "schema_version_consistent": schema_version_consistent,
        "data_source_type_consistent": data_source_type_consistent,
        "resume_state_consistent": resume_state_consistent,
        "preflight_schema_validation_status": validation.schema_validation_status,
        "preflight_leakage_audit_status": validation.leakage_audit_status,
        "stop_on_first_failure": True,
        "max_failed_chunks_allowed": 0,
        "recommended_next_action": _controlled_batch_recommended_action(gate_status),
        "resume_restart_summary": resume.to_dict(),
        "distribution_audit": distribution.to_dict(),
        "no_write_validation": validation.to_dict(),
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def detect_full_range_data_source_type(runtime_dir: Path | str = ".runtime") -> str:
    manifest = Path(runtime_dir) / "reports" / "candidate_ai" / "phase4k_mock_normalized_history_manifest.json"
    if manifest.is_file():
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "skipped"
        if payload.get("data_source_type") == "mock":
            return "mock"
    discovery = discover_daily_quotes_normalized(runtime_dir)
    if discovery.status == "FOUND":
        return "real_runtime"
    return "skipped"


def _month_date_chunks(dates: list[str]) -> list[tuple[str, str]]:
    months: dict[str, list[str]] = {}
    for value in dates:
        months.setdefault(value[:7], []).append(value)
    return [(values[0], values[-1]) for _, values in sorted(months.items())]


def _code_chunks(codes: list[str], *, max_codes_per_chunk: int) -> list[list[str]]:
    return [codes[index : index + max_codes_per_chunk] for index in range(0, len(codes), max_codes_per_chunk)]


def _record_dates(records: Iterable[Mapping[str, Any]]) -> list[str]:
    return sorted({str(record.get("Date") or "") for record in records if record.get("Date")})


def _record_codes(records: Iterable[Mapping[str, Any]]) -> list[str]:
    return sorted({str(record.get("Code") or "") for record in records if record.get("Code")})


def _chunk_id(run_id: str, date_start: str, date_end: str, codes: list[str]) -> str:
    code_start = codes[0] if codes else "none"
    code_end = codes[-1] if codes else "none"
    return f"{run_id}__{date_start}_{date_end}__codes_{code_start}_{code_end}"


def _select_chunk_records(records: list[dict[str, Any]], plan: FullRangeChunkPlan) -> list[dict[str, Any]]:
    code_set = set(plan.codes)
    return [
        record
        for record in records
        if plan.date_start <= str(record.get("Date") or "") <= plan.date_end and str(record.get("Code") or "") in code_set
    ]


def _run_no_write_leakage_probe(plans: list[FullRangeChunkPlan]) -> str:
    if not plans:
        return "ERROR"
    rows = [
        {
            "as_of_date": plan.date_end,
            "target_date": plan.date_end,
            "code": plan.codes[0] if plan.codes else "UNKNOWN",
            "feature_version": plan.feature_version,
            "source_snapshot_id": f"no_write:{plan.chunk_id}",
            "feature_set_name": "full_range_no_write_probe",
            "created_at": _now_utc(),
            "data_start_date": plan.date_start,
            "data_end_date": plan.date_end,
            "universe_eligible": True,
            "excluded_reason": "",
        }
        for plan in plans[:5]
        if plan.codes
    ]
    if not rows:
        return "ERROR"
    return audit_feature_table(rows).status


def _select_controlled_source_records(records: list[dict[str, Any]], plan: FullRangeChunkPlan) -> list[dict[str, Any]]:
    code_set = set(plan.codes)
    return [
        record
        for record in records
        if str(record.get("Code") or "") in code_set and str(record.get("Date") or "") <= plan.date_end
    ]


def _controlled_failed_result(
    chunk_plan: FullRangeChunkPlan,
    paths: FullRangePaths,
    message: str,
    *,
    row_count: int = 0,
    eligible_count: int = 0,
    excluded_count: int = 0,
    schema_validation_status: str = "SKIPPED",
    leakage_audit_status: str = "SKIPPED",
) -> ControlledChunkExecutionResult:
    safe_chunk = _safe_name(chunk_plan.chunk_id)
    manifest_path = paths.manifest_dir / f"{chunk_plan.run_id}_{safe_chunk}_manifest.json"
    manifest = FullRangeChunkManifest(
        run_id=chunk_plan.run_id,
        chunk_id=chunk_plan.chunk_id,
        status="FAILED",
        date_start=chunk_plan.date_start,
        date_end=chunk_plan.date_end,
        code_count=chunk_plan.code_count,
        row_count=row_count,
        eligible_count=eligible_count,
        excluded_count=excluded_count,
        schema_validation_status=schema_validation_status,
        leakage_audit_status=leakage_audit_status,
        output_path=None,
        manifest_path=str(manifest_path),
        audit_path=None,
        error_message=message,
    )
    _write_json(manifest_path, manifest.to_dict())
    return ControlledChunkExecutionResult(
        status=CONTROLLED_EXECUTION_FAILED,
        run_id=chunk_plan.run_id,
        chunk_id=chunk_plan.chunk_id,
        executed_chunk_count=1,
        max_chunks_to_execute=1,
        row_count=row_count,
        eligible_count=eligible_count,
        excluded_count=excluded_count,
        schema_validation_status=schema_validation_status,
        leakage_audit_status=leakage_audit_status,
        tmp_output_path=None,
        final_output_path=None,
        chunk_manifest_path=str(manifest_path),
        chunk_audit_path=None,
        run_manifest_path=None,
        error_message=message,
    )


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)


def _date_overlap_gap_counts(date_ranges: list[tuple[str, str]]) -> tuple[int, int]:
    overlap_count = 0
    gap_count = 0
    previous_end: date | None = None
    for start_text, end_text in date_ranges:
        start = date.fromisoformat(start_text)
        end = date.fromisoformat(end_text)
        if previous_end is not None:
            if start <= previous_end:
                overlap_count += 1
            elif start > previous_end + timedelta(days=4):
                # Month chunks can skip weekends/holidays. A gap larger than a long weekend is suspicious.
                gap_count += 1
        previous_end = end
    return overlap_count, gap_count


def _read_existing_chunk_manifests(manifest_dir: Path) -> dict[str, dict[str, Any]]:
    if not manifest_dir.exists():
        return {}
    output: dict[str, dict[str, Any]] = {}
    for path in manifest_dir.glob("*manifest*.json"):
        if path.name.endswith("_run_manifest.json") or path.name.endswith("_chunk_plan.json"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            output[f"corrupt:{path.name}"] = {"status": "ERROR", "error_message": "invalid json"}
            continue
        chunk_id = str(payload.get("chunk_id") or path.stem)
        if chunk_id in output:
            duplicate_key = f"duplicate:{chunk_id}:{path.name}"
            output[duplicate_key] = {
                "status": "ERROR",
                "error_message": "duplicate chunk manifest",
                "duplicate_chunk_id": chunk_id,
                "run_id": payload.get("run_id"),
                "manifest_path": str(path),
            }
            continue
        output[chunk_id] = payload
    return output


def _skipped_summary(*, run_id: str, discovery_message: str, data_source_type: str) -> dict[str, Any]:
    return {
        "status": "SKIPPED",
        "mode": "dry_run_only",
        "feature_generation_executed": False,
        "run_id": run_id,
        "data_source_type": data_source_type,
        "reason": discovery_message,
        "chunk_count": 0,
        "run_manifest_path": None,
        "chunk_plan_path": None,
        "resume_restart_summary": {
            "completed_chunk_ids": [],
            "failed_chunk_ids": [],
            "missing_chunk_ids": [],
            "partial_tmp_paths": [],
            "manifest_inconsistencies": [],
        },
    }


def _resume_controlled_base_summary(
    *,
    run_id: str,
    runner_status: str,
    status: str,
    max_chunks_to_execute: int,
    summary_path: Path,
) -> dict[str, Any]:
    return {
        "status": status,
        "runner_status": runner_status,
        "run_id": run_id,
        "max_chunks_to_execute": max_chunks_to_execute,
        "planned_chunk_count": 0,
        "skipped_success_chunk_count": 0,
        "rerun_failed_chunk_count": 0,
        "run_missing_chunk_count": 0,
        "executed_chunk_count": 0,
        "blocked_inconsistency_count": 0,
        "partial_tmp_warning_count": 0,
        "completed_chunk_count": 0,
        "failed_chunk_count": 0,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(summary_path),
    }


def _batch_readiness_base_summary(
    *,
    run_id: str,
    data_source_type: str,
    gate_status: str,
    summary_path: Path,
) -> dict[str, Any]:
    return {
        "status": "BLOCKED",
        "gate_status": gate_status,
        "run_id": run_id,
        "data_source_type": data_source_type,
        "chunk_count": 0,
        "date_chunk_count": 0,
        "code_chunk_count": 0,
        "input_row_count": 0,
        "estimated_feature_row_count": 0,
        "estimated_output_size_bytes": 0,
        "runtime_free_space_check": {"status": "UNKNOWN"},
        "runtime_free_space_sufficient": True,
        "completed_chunk_count": 0,
        "failed_chunk_count": 0,
        "missing_chunk_count": 0,
        "partial_tmp_warning_count": 0,
        "manifest_inconsistency_count": 0,
        "feature_version_consistent": False,
        "schema_version_consistent": False,
        "data_source_type_consistent": False,
        "resume_state_consistent": False,
        "preflight_schema_validation_status": "SKIPPED",
        "preflight_leakage_audit_status": "SKIPPED",
        "stop_on_first_failure": True,
        "max_failed_chunks_allowed": 0,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(summary_path),
    }


def _first_batch_base_summary(
    *,
    run_id: str,
    status: str,
    batch_status: str,
    gate_status: str,
    max_chunks_to_execute: int,
    summary_path: Path,
) -> dict[str, Any]:
    return {
        "status": status,
        "batch_status": batch_status,
        "gate_status": gate_status,
        "run_id": run_id,
        "max_chunks_to_execute": max_chunks_to_execute,
        "stop_on_first_failure": True,
        "max_failed_chunks_allowed": 0,
        "planned_chunk_count": 0,
        "executed_chunk_count": 0,
        "completed_chunk_count": 0,
        "failed_chunk_count": 0,
        "skipped_chunk_count": 0,
        "feature_output_written_count": 0,
        "schema_validation_status": "SKIPPED",
        "leakage_audit_status": "SKIPPED",
        "stopped_on_failure": False,
        "stop_reason": None,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(summary_path),
    }


def _controlled_batch_gate_status(
    *,
    chunk_count: int,
    input_row_count: int,
    distribution_status: str,
    resume_state_consistent: bool,
    manifest_inconsistency_count: int,
    runtime_free_space_sufficient: bool,
    feature_version_consistent: bool,
    schema_version_consistent: bool,
    data_source_type_consistent: bool,
    preflight_schema_validation_status: str,
    preflight_leakage_audit_status: str,
) -> str:
    if chunk_count <= 0 or input_row_count <= 0:
        return BATCH_READINESS_SKIPPED_NO_DATA
    if distribution_status != "OK" or not (feature_version_consistent and schema_version_consistent and data_source_type_consistent):
        return BATCH_READINESS_BLOCKED_BY_CHUNK_PLAN
    if manifest_inconsistency_count:
        return BATCH_READINESS_BLOCKED_BY_MANIFEST_INCONSISTENCY
    if not resume_state_consistent:
        return BATCH_READINESS_BLOCKED_BY_RESUME_STATE
    if not runtime_free_space_sufficient:
        return BATCH_READINESS_BLOCKED_BY_STORAGE
    if preflight_schema_validation_status != "OK":
        return BATCH_READINESS_BLOCKED_BY_SCHEMA
    if preflight_leakage_audit_status != "OK":
        return BATCH_READINESS_BLOCKED_BY_LEAKAGE
    return BATCH_READINESS_READY


def _controlled_batch_recommended_action(gate_status: str) -> str:
    if gate_status == BATCH_READINESS_READY:
        return "ready for small controlled batch execution with stop_on_first_failure=true"
    if gate_status == BATCH_READINESS_SKIPPED_NO_DATA:
        return "prepare or discover normalized input data before retrying readiness audit"
    if gate_status == BATCH_READINESS_BLOCKED_BY_MANIFEST_INCONSISTENCY:
        return "fix manifest inconsistency before any controlled batch execution"
    if gate_status == BATCH_READINESS_BLOCKED_BY_RESUME_STATE:
        return "review resume state and isolate partial tmp outputs before retrying"
    if gate_status == BATCH_READINESS_BLOCKED_BY_STORAGE:
        return "free runtime storage or reduce batch size before retrying"
    if gate_status == BATCH_READINESS_BLOCKED_BY_SCHEMA:
        return "fix preflight schema validation before retrying"
    if gate_status == BATCH_READINESS_BLOCKED_BY_LEAKAGE:
        return "fix leakage audit before retrying"
    return "fix chunk plan consistency before retrying"


def _runtime_free_space_check(runtime_dir: Path) -> dict[str, Any]:
    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(runtime_dir)
    except OSError as exc:
        return {
            "status": "UNKNOWN",
            "reason": type(exc).__name__,
        }
    return {
        "status": "OK",
        "path": str(runtime_dir),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
