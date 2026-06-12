#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    FORBIDDEN_FEATURE_TERMS,
    OPTIONAL_FEATURE_METADATA_COLUMNS,
    REQUIRED_FEATURE_COLUMNS,
    audit_feature_table,
    build_full_range_chunk_plan,
    check_resume_restart,
    resolve_full_range_paths,
    validate_feature_table,
)
from ai_fund_lab_v2.candidate_ai.normalized_data_reader import discover_daily_quotes_normalized  # noqa: E402
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from scripts.build_candidate_features_controlled_batch_expansion import (  # noqa: E402
    SUMMARY_PATH as PHASE4U_SUMMARY_PATH,
    build_controlled_batch_expansion_summary,
)

SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4v_post_expansion_readiness_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4v_post_expansion_readiness_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4v_post_expansion_readiness_audit.md")

READY_LARGER = "READY_FOR_LARGER_CONTROLLED_BATCH"
READY_FULL = "READY_FOR_FULL_CONTROLLED_FEATURE_GENERATION"
BLOCKED_ARTIFACT = "BLOCKED_BY_ARTIFACT_INTEGRITY"
BLOCKED_SCHEMA = "BLOCKED_BY_SCHEMA"
BLOCKED_LEAKAGE = "BLOCKED_BY_LEAKAGE"
BLOCKED_STORAGE = "BLOCKED_BY_STORAGE"
BLOCKED_RESUME = "BLOCKED_BY_RESUME_STATE"
SKIPPED_NO_OUTPUT = "SKIPPED_NO_OUTPUT"


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    phase4u = _ensure_phase4u_summary()
    summary = build_post_expansion_readiness_summary(phase4u_summary=phase4u)
    _write_json(summary_path, summary)
    checks = {
        "phase4u_summary_exists": PHASE4U_SUMMARY_PATH.is_file(),
        "post_expansion_readiness_summary_exists": summary_path.is_file(),
        "artifact_integrity_checked": "artifact_integrity" in summary and "final_output_count" in summary["artifact_integrity"],
        "feature_output_stats_produced": summary.get("total_feature_rows", 0) > 0
        and isinstance(summary.get("null_count_by_feature"), dict),
        "schema_leakage_reaudit_checked": "schema_validation_all_ok" in summary
        and "leakage_audit_all_ok" in summary,
        "storage_guard_checked": "runtime_free_space_bytes" in summary
        and "runtime_free_space_sufficient" in summary,
        "resume_readiness_checked": "resume_ready" in summary and "manifest_consistent" in summary,
        "readiness_status_produced": summary.get("readiness_status")
        in {
            READY_LARGER,
            READY_FULL,
            BLOCKED_ARTIFACT,
            BLOCKED_SCHEMA,
            BLOCKED_LEAKAGE,
            BLOCKED_STORAGE,
            BLOCKED_RESUME,
            SKIPPED_NO_OUTPUT,
        },
        "ready_or_clear_blocked_or_skipped_status_produced": summary.get("status") in {"READY", "BLOCKED", "SKIPPED"},
        "data_source_type_recorded": bool(summary.get("data_source_type")),
        "label_generation_not_implemented": summary.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_implemented": summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "no_secret_terms_in_reports": _no_secret_terms(summary),
    }
    result = {
        "phase": "Phase4-V",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4v_post_expansion_readiness.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def build_post_expansion_readiness_summary(
    *,
    phase4u_summary: dict[str, Any],
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
) -> dict[str, Any]:
    run_id = str(phase4u_summary.get("run_id") or "")
    paths = resolve_full_range_paths(runtime_dir=runtime_dir, report_dir=report_dir)
    if not run_id:
        return _skipped_summary("missing Phase4-U run_id")
    manifests = _read_chunk_manifests(paths.manifest_dir, run_id)
    if not manifests:
        return _skipped_summary("no Phase4-U chunk manifests found")
    run_manifest_path = paths.manifest_dir / f"{run_id}_run_manifest.json"
    run_manifest = _read_json_optional(run_manifest_path)
    rows = _read_feature_rows(manifests)
    feature_stats = _feature_stats(rows)
    validation = validate_feature_table(rows) if rows else None
    leakage = audit_feature_table(rows) if rows else None
    artifact = _artifact_integrity(paths, run_id, manifests, run_manifest)
    resume = _resume_readiness(paths, run_id, manifests)
    storage = _storage_guard(paths.runtime_dir, manifests)
    schema_validation_all_ok = (
        bool(rows)
        and validation is not None
        and validation.is_valid
        and all(str(manifest.get("schema_validation_status") or "") == "OK" for manifest in manifests)
    )
    leakage_audit_all_ok = (
        bool(rows)
        and leakage is not None
        and leakage.status == "OK"
        and all(str(manifest.get("leakage_audit_status") or "") == "OK" for manifest in manifests)
    )
    forbidden_feature_detected = bool((validation and validation.forbidden_columns) or (leakage and leakage.forbidden_feature_detected))
    columns = set().union(*(set(row.keys()) for row in rows)) if rows else set()
    future_column_detected = bool(leakage.future_column_detected if leakage else False) or any(
        str(column).startswith("future_") for column in columns
    )
    label_column_detected = bool(leakage.label_column_detected if leakage else False) or any(
        "label" in str(column).lower() for column in columns
    )
    data_source_type = _consistent_value([run_manifest.get("data_source_type")] + [manifest.get("data_source_type") for manifest in manifests]) or str(
        phase4u_summary.get("runner_summary", {}).get("data_source_type") or phase4u_summary.get("data_source_type") or "mock"
    )
    artifact_integrity_ok = artifact["artifact_integrity_ok"]
    manifest_consistent = resume["manifest_consistent"]
    resume_ready = resume["resume_ready"]
    readiness_status = _readiness_status(
        has_rows=bool(rows),
        artifact_integrity_ok=artifact_integrity_ok,
        schema_validation_all_ok=schema_validation_all_ok,
        leakage_audit_all_ok=leakage_audit_all_ok and not forbidden_feature_detected and not future_column_detected and not label_column_detected,
        runtime_free_space_sufficient=storage["runtime_free_space_sufficient"],
        resume_ready=resume_ready,
        planned_chunk_count=int(phase4u_summary.get("planned_chunk_count") or artifact["success_manifest_count"]),
        completed_chunk_count=artifact["success_manifest_count"],
        data_source_type=data_source_type,
    )
    summary = {
        "status": "READY" if readiness_status in {READY_LARGER, READY_FULL} else ("SKIPPED" if readiness_status == SKIPPED_NO_OUTPUT else "BLOCKED"),
        "readiness_status": readiness_status,
        "run_id": run_id,
        "data_source_type": data_source_type,
        "completed_chunk_count": artifact["success_manifest_count"],
        "failed_chunk_count": artifact["failed_manifest_count"],
        "remaining_missing_chunk_count": max(0, int(phase4u_summary.get("planned_chunk_count") or 0) - artifact["success_manifest_count"] - artifact["failed_manifest_count"]),
        "final_output_count": artifact["final_output_count"],
        "chunk_manifest_count": artifact["chunk_manifest_count"],
        "chunk_audit_count": artifact["chunk_audit_count"],
        "run_manifest_completed_count": artifact["run_manifest_completed_count"],
        "tmp_leftover_count": artifact["tmp_leftover_count"],
        "duplicate_output_count": artifact["duplicate_output_count"],
        "duplicate_manifest_count": artifact["duplicate_manifest_count"],
        "orphan_output_count": artifact["orphan_output_count"],
        "orphan_manifest_count": artifact["orphan_manifest_count"],
        **feature_stats,
        "schema_validation_all_ok": schema_validation_all_ok,
        "leakage_audit_all_ok": leakage_audit_all_ok,
        "forbidden_feature_detected": forbidden_feature_detected,
        "future_column_detected": future_column_detected,
        "label_column_detected": label_column_detected,
        "runtime_free_space_bytes": storage["runtime_free_space_bytes"],
        "estimated_next_batch_size_bytes": storage["estimated_next_batch_size_bytes"],
        "runtime_free_space_sufficient": storage["runtime_free_space_sufficient"],
        "resume_ready": resume_ready,
        "manifest_consistent": manifest_consistent,
        "artifact_integrity_ok": artifact_integrity_ok,
        "artifact_integrity": artifact,
        "resume_readiness": resume,
        "storage_guard": storage,
        "validation_messages": list(validation.messages) if validation else [],
        "leakage_messages": list(leakage.messages) if leakage else [],
        "recommended_next_action": _recommended_action(readiness_status, data_source_type),
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(SUMMARY_PATH),
    }
    return summary


def _ensure_phase4u_summary() -> dict[str, Any]:
    summary = _read_json_optional(PHASE4U_SUMMARY_PATH)
    if summary and _phase4u_artifacts_exist(summary):
        return summary
    return build_controlled_batch_expansion_summary()


def _phase4u_artifacts_exist(summary: dict[str, Any]) -> bool:
    run_id = str(summary.get("run_id") or "")
    if not run_id:
        return False
    paths = resolve_full_range_paths()
    manifest_path = paths.manifest_dir / f"{run_id}_run_manifest.json"
    feature_dir = paths.feature_dir / run_id
    return manifest_path.is_file() and feature_dir.exists() and any(feature_dir.glob("*.json"))


def _read_chunk_manifests(manifest_dir: Path, run_id: str) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(manifest_dir.glob(f"{run_id}_*manifest.json")):
        if path.name.endswith("_run_manifest.json"):
            continue
        payload = _read_json_optional(path)
        if payload:
            payload.setdefault("manifest_path", str(path))
            manifests.append(payload)
    return manifests


def _read_feature_rows(manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for manifest in manifests:
        output_path = Path(str(manifest.get("output_path") or ""))
        if not output_path.is_file():
            continue
        payload = _read_json_optional(output_path)
        rows.extend(dict(row) for row in payload.get("rows", []) if isinstance(row, dict))
    return rows


def _feature_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    columns = sorted({column for row in rows for column in row})
    feature_columns = [
        column
        for column in columns
        if column not in REQUIRED_FEATURE_COLUMNS and column not in OPTIONAL_FEATURE_METADATA_COLUMNS
    ]
    null_counts: dict[str, int] = {}
    for column in feature_columns:
        null_counts[column] = sum(1 for row in rows if row.get(column) is None or row.get(column) == "")
    dates = sorted({str(row.get("as_of_date") or row.get("target_date") or "") for row in rows if row.get("as_of_date") or row.get("target_date")})
    codes = sorted({str(row.get("code") or "") for row in rows if row.get("code")})
    excluded_reasons = Counter(str(row.get("excluded_reason") or "") for row in rows)
    eligible_count = sum(1 for row in rows if row.get("universe_eligible") is True)
    return {
        "total_feature_rows": len(rows),
        "eligible_count": eligible_count,
        "excluded_count": len(rows) - eligible_count,
        "code_count": len(codes),
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "feature_columns": feature_columns,
        "null_count_by_feature": null_counts,
        "excluded_reason_counts": dict(sorted(excluded_reasons.items())),
    }


def _artifact_integrity(paths, run_id: str, manifests: list[dict[str, Any]], run_manifest: dict[str, Any]) -> dict[str, Any]:
    output_paths = [Path(str(manifest.get("output_path") or "")) for manifest in manifests if manifest.get("output_path")]
    audit_paths = [Path(str(manifest.get("audit_path") or "")) for manifest in manifests if manifest.get("audit_path")]
    chunk_ids = [str(manifest.get("chunk_id") or "") for manifest in manifests]
    feature_run_dir = paths.feature_dir / run_id
    all_outputs = sorted(feature_run_dir.glob("*.json")) if feature_run_dir.exists() else []
    referenced_outputs = {str(path) for path in output_paths}
    tmp_run_dir = paths.tmp_dir / run_id
    tmp_leftovers = sorted(str(path) for path in tmp_run_dir.rglob("*") if path.is_file()) if tmp_run_dir.exists() else []
    success_count = sum(1 for manifest in manifests if manifest.get("status") == "SUCCESS")
    failed_count = sum(1 for manifest in manifests if manifest.get("status") == "FAILED")
    final_output_count = sum(1 for path in output_paths if path.is_file())
    chunk_audit_count = sum(1 for path in audit_paths if path.is_file())
    run_completed = int(run_manifest.get("completed_chunk_count") or 0)
    run_failed = int(run_manifest.get("failed_chunk_count") or 0)
    duplicate_output_count = len(output_paths) - len({str(path) for path in output_paths})
    duplicate_manifest_count = len(chunk_ids) - len(set(chunk_ids))
    orphan_output_count = sum(1 for path in all_outputs if str(path) not in referenced_outputs)
    orphan_manifest_count = 0
    ok = (
        success_count > 0
        and failed_count == 0
        and final_output_count == success_count
        and len(manifests) == success_count
        and chunk_audit_count == success_count
        and run_completed == success_count
        and run_failed == 0
        and not tmp_leftovers
        and duplicate_output_count == 0
        and duplicate_manifest_count == 0
        and orphan_output_count == 0
        and orphan_manifest_count == 0
    )
    return {
        "artifact_integrity_ok": ok,
        "final_output_count": final_output_count,
        "chunk_manifest_count": len(manifests),
        "chunk_audit_count": chunk_audit_count,
        "success_manifest_count": success_count,
        "failed_manifest_count": failed_count,
        "run_manifest_completed_count": run_completed,
        "run_manifest_failed_count": run_failed,
        "tmp_leftover_count": len(tmp_leftovers),
        "tmp_leftover_paths": tmp_leftovers,
        "duplicate_output_count": duplicate_output_count,
        "duplicate_manifest_count": duplicate_manifest_count,
        "orphan_output_count": orphan_output_count,
        "orphan_manifest_count": orphan_manifest_count,
    }


def _resume_readiness(paths, run_id: str, manifests: list[dict[str, Any]]) -> dict[str, Any]:
    discovery = discover_daily_quotes_normalized(paths.runtime_dir)
    resume_payload: dict[str, Any] = {
        "completed_chunk_ids": [],
        "failed_chunk_ids": [],
        "missing_chunk_ids": [],
        "partial_tmp_paths": [],
        "manifest_inconsistencies": [],
    }
    if discovery.status == "FOUND" and discovery.path and discovery.storage_format:
        try:
            records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
            max_codes = max((int(manifest.get("code_count") or 1) for manifest in manifests), default=1)
            data_source_type = _consistent_value([manifest.get("data_source_type") for manifest in manifests]) or "mock"
            plans = build_full_range_chunk_plan(records, run_id=run_id, data_source_type=data_source_type, max_codes_per_chunk=max_codes)
            resume = check_resume_restart(plans, manifest_dir=paths.manifest_dir, tmp_dir=paths.tmp_dir)
            resume_payload = resume.to_dict()
        except Exception as exc:  # pragma: no cover - defensive audit path
            resume_payload["manifest_inconsistencies"] = [f"resume_check_failed:{type(exc).__name__}"]
    manifest_consistent = not resume_payload.get("manifest_inconsistencies")
    partial_tmp_absent = not resume_payload.get("partial_tmp_paths")
    resume_ready = manifest_consistent and partial_tmp_absent
    return {
        "resume_ready": resume_ready,
        "manifest_consistent": manifest_consistent,
        "success_chunk_skip_possible": bool(resume_payload.get("completed_chunk_ids")),
        "failed_chunk_rerun_possible": True,
        "missing_chunk_run_possible": True,
        "partial_tmp_absent": partial_tmp_absent,
        "resume_restart_summary": resume_payload,
    }


def _storage_guard(runtime_dir: Path, manifests: list[dict[str, Any]]) -> dict[str, Any]:
    output_size = 0
    for manifest in manifests:
        output_path = Path(str(manifest.get("output_path") or ""))
        if output_path.is_file():
            output_size += output_path.stat().st_size
    estimated_next = max(output_size, 1)
    try:
        usage = shutil.disk_usage(runtime_dir)
        free_bytes = usage.free
        sufficient = free_bytes > estimated_next * 2
    except OSError:
        free_bytes = 0
        sufficient = True
    return {
        "runtime_free_space_bytes": free_bytes,
        "estimated_next_batch_size_bytes": estimated_next,
        "runtime_free_space_sufficient": sufficient,
    }


def _readiness_status(
    *,
    has_rows: bool,
    artifact_integrity_ok: bool,
    schema_validation_all_ok: bool,
    leakage_audit_all_ok: bool,
    runtime_free_space_sufficient: bool,
    resume_ready: bool,
    planned_chunk_count: int,
    completed_chunk_count: int,
    data_source_type: str,
) -> str:
    if not has_rows:
        return SKIPPED_NO_OUTPUT
    if not artifact_integrity_ok:
        return BLOCKED_ARTIFACT
    if not schema_validation_all_ok:
        return BLOCKED_SCHEMA
    if not leakage_audit_all_ok:
        return BLOCKED_LEAKAGE
    if not runtime_free_space_sufficient:
        return BLOCKED_STORAGE
    if not resume_ready:
        return BLOCKED_RESUME
    if completed_chunk_count >= planned_chunk_count and data_source_type == "mock":
        return READY_FULL
    return READY_LARGER


def _recommended_action(readiness_status: str, data_source_type: str) -> str:
    if readiness_status == READY_FULL:
        return f"ready for full controlled feature generation gate; data_source_type={data_source_type}, so validate real_runtime separately before production use"
    if readiness_status == READY_LARGER:
        return "ready for a larger controlled batch with the same stop-on-first-failure guard"
    if readiness_status == SKIPPED_NO_OUTPUT:
        return "run Phase4-U controlled batch expansion before readiness audit"
    if readiness_status == BLOCKED_ARTIFACT:
        return "fix output, manifest, audit, tmp, duplicate, or orphan artifact integrity before continuing"
    if readiness_status == BLOCKED_SCHEMA:
        return "fix schema validation failures before continuing"
    if readiness_status == BLOCKED_LEAKAGE:
        return "fix leakage or forbidden feature detections before continuing"
    if readiness_status == BLOCKED_STORAGE:
        return "free runtime storage or reduce next batch size before continuing"
    return "fix resume/restart state before continuing"


def _skipped_summary(reason: str) -> dict[str, Any]:
    return {
        "status": "SKIPPED",
        "readiness_status": SKIPPED_NO_OUTPUT,
        "data_source_type": "skipped",
        "completed_chunk_count": 0,
        "failed_chunk_count": 0,
        "remaining_missing_chunk_count": 0,
        "total_feature_rows": 0,
        "eligible_count": 0,
        "excluded_count": 0,
        "code_count": 0,
        "date_min": None,
        "date_max": None,
        "schema_validation_all_ok": False,
        "leakage_audit_all_ok": False,
        "forbidden_feature_detected": False,
        "future_column_detected": False,
        "label_column_detected": False,
        "runtime_free_space_bytes": 0,
        "estimated_next_batch_size_bytes": 0,
        "runtime_free_space_sufficient": True,
        "resume_ready": False,
        "manifest_consistent": False,
        "artifact_integrity_ok": False,
        "recommended_next_action": reason,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(SUMMARY_PATH),
    }


def _consistent_value(values: list[Any]) -> str | None:
    normalized = {str(value) for value in values if value}
    if len(normalized) == 1:
        return next(iter(normalized))
    return None


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "data_source_type",
        "completed_chunk_count",
        "failed_chunk_count",
        "remaining_missing_chunk_count",
        "total_feature_rows",
        "eligible_count",
        "excluded_count",
        "code_count",
        "date_min",
        "date_max",
        "schema_validation_all_ok",
        "leakage_audit_all_ok",
        "runtime_free_space_sufficient",
        "resume_ready",
        "artifact_integrity_ok",
    )
    return {key: summary.get(key) for key in keys}


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-V Post-expansion Readiness Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- readiness_status: `{result.get('readiness_status')}`",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Checks", ""])
    for name, value in result["checks"].items():
        mark = "OK" if value else "NG"
        lines.append(f"- {mark}: `{name}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- Phase4-V audits the four-chunk controlled expansion outputs.",
            "- It does not generate labels, build datasets, train, infer, backtest, call broker APIs, place orders, trade, or update Portfolio state.",
            "- `data_source_type=mock` readiness does not imply real J-Quants runtime readiness.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "password", "cookie", "token", "http://", "https://")
    return not any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
