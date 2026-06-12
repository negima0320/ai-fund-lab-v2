#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    build_first_controlled_batch_summary,
    build_full_range_chunk_plan,
    check_resume_restart,
    resolve_full_range_paths,
)
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402


SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4t_post_batch_integrity_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4t_post_batch_integrity_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4t_post_batch_integrity_audit.md")

READY = "READY_FOR_CONTROLLED_BATCH_EXPANSION"
BLOCKED_MISSING_OUTPUT = "BLOCKED_BY_MISSING_OUTPUT"
BLOCKED_MANIFEST_MISMATCH = "BLOCKED_BY_MANIFEST_MISMATCH"
BLOCKED_AUDIT_FAILURE = "BLOCKED_BY_AUDIT_FAILURE"
BLOCKED_RESUME_STATE = "BLOCKED_BY_RESUME_STATE"
BLOCKED_ORPHAN_ARTIFACT = "BLOCKED_BY_ORPHAN_ARTIFACT"
SKIPPED_NO_BATCH_OUTPUT = "SKIPPED_NO_BATCH_OUTPUT"


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
    source_run_id = f"phase4t_post_batch_source_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    phase4s_summary = build_first_controlled_batch_summary(run_id=source_run_id)
    integrity = build_post_batch_integrity_summary(phase4s_summary)
    _write_json(summary_path, integrity)
    checks = {
        "phase4s_summary_exists": bool(phase4s_summary),
        "post_batch_integrity_summary_exists": summary_path.is_file(),
        "final_output_exists": integrity.get("final_output_exists_count") == integrity.get("checked_chunk_count") and integrity.get("checked_chunk_count", 0) > 0,
        "chunk_manifest_exists": integrity.get("chunk_manifest_count") == integrity.get("checked_chunk_count") and integrity.get("checked_chunk_count", 0) > 0,
        "chunk_audit_exists": integrity.get("chunk_audit_count") == integrity.get("checked_chunk_count") and integrity.get("checked_chunk_count", 0) > 0,
        "run_manifest_exists": bool(integrity.get("run_manifest_exists")),
        "row_count_consistency_checked": integrity.get("row_count_match") is True,
        "eligible_excluded_consistency_checked": integrity.get("eligible_excluded_count_match") is True,
        "schema_leakage_ok_checked": integrity.get("schema_validation_all_ok") is True and integrity.get("leakage_audit_all_ok") is True,
        "resume_success_skip_checked": integrity.get("resume_success_skip_ready") is True,
        "duplicate_orphan_detection_exists": "duplicate_output_count" in integrity
        and "duplicate_manifest_count" in integrity
        and "orphan_output_count" in integrity
        and "orphan_manifest_count" in integrity,
        "integrity_status_produced": integrity.get("integrity_status") in {
            READY,
            BLOCKED_MISSING_OUTPUT,
            BLOCKED_MANIFEST_MISMATCH,
            BLOCKED_AUDIT_FAILURE,
            BLOCKED_RESUME_STATE,
            BLOCKED_ORPHAN_ARTIFACT,
            SKIPPED_NO_BATCH_OUTPUT,
        },
        "ready_or_clear_blocked_or_skipped_status_produced": integrity.get("status") in {"READY", "BLOCKED", "SKIPPED"},
        "full_range_generation_not_executed": integrity.get("full_range_generation_executed") is False,
        "label_generation_not_implemented": integrity.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_implemented": integrity.get("training_executed") is False
        and integrity.get("inference_executed") is False
        and integrity.get("backtest_executed") is False
        and integrity.get("trading_executed") is False,
        "no_secret_terms_in_reports": _no_secret_terms(integrity),
    }
    result = {
        "phase": "Phase4-T",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "integrity_status": integrity.get("integrity_status"),
        "checked_chunk_count": integrity.get("checked_chunk_count"),
        "recommended_next_action": integrity.get("recommended_next_action"),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4t_post_batch_integrity.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result, integrity)
    return result


def build_post_batch_integrity_summary(phase4s_summary: dict[str, Any]) -> dict[str, Any]:
    run_id = str(phase4s_summary.get("run_id") or "")
    executions = list(phase4s_summary.get("runner_summary", {}).get("executions", []))
    run_manifest_path = Path(str(phase4s_summary.get("run_manifest_path") or ""))
    if not executions:
        return _base_integrity_summary(phase4s_summary, SKIPPED_NO_BATCH_OUTPUT)

    chunk_manifests: list[dict[str, Any]] = []
    output_paths: list[Path] = []
    manifest_paths: list[Path] = []
    audit_paths: list[Path] = []
    tmp_leftovers: list[str] = []
    row_matches: list[bool] = []
    eligible_matches: list[bool] = []
    schema_ok: list[bool] = []
    leakage_ok: list[bool] = []
    feature_versions: set[str] = set()
    schema_versions: set[str] = set()
    data_source_types: set[str] = set()

    for item in executions:
        manifest_path = Path(str(item.get("chunk_manifest_path") or ""))
        manifest_paths.append(manifest_path)
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        chunk_manifests.append(manifest)
        output_path = Path(str(manifest.get("output_path") or ""))
        audit_path = Path(str(manifest.get("audit_path") or ""))
        output_paths.append(output_path)
        audit_paths.append(audit_path)
        tmp_path = Path(str(item.get("tmp_output_path") or ""))
        if tmp_path and tmp_path.is_file():
            tmp_leftovers.append(str(tmp_path))
        rows = _read_output_rows(output_path)
        audit = _read_json_optional(audit_path)
        row_matches.append(output_path.is_file() and len(rows) == _int_field(manifest, "row_count", -1))
        eligible_count = sum(1 for row in rows if row.get("universe_eligible") is True)
        excluded_count = len(rows) - eligible_count
        eligible_matches.append(
            output_path.is_file()
            and eligible_count == _int_field(manifest, "eligible_count", -1)
            and excluded_count == _int_field(manifest, "excluded_count", -1)
        )
        schema_ok.append(manifest.get("schema_validation_status") == "OK" and audit.get("status") == "OK")
        leakage_ok.append(manifest.get("leakage_audit_status") == "OK" and audit.get("status") == "OK")
        if audit.get("feature_version"):
            feature_versions.add(str(audit["feature_version"]))
        for row in rows:
            if row.get("feature_version"):
                feature_versions.add(str(row["feature_version"]))

    run_manifest = _read_json_optional(run_manifest_path)
    if run_manifest.get("data_source_type"):
        data_source_types.add(str(run_manifest["data_source_type"]))
    if run_manifest.get("feature_version"):
        feature_versions.add(str(run_manifest["feature_version"]))
    if run_manifest.get("schema_version"):
        schema_versions.add(str(run_manifest["schema_version"]))
    readiness = phase4s_summary.get("readiness_summary", {})
    if readiness.get("data_source_type"):
        data_source_types.add(str(readiness["data_source_type"]))
    distribution = readiness.get("distribution_audit", {})
    data_source_type_consistent = len(data_source_types) <= 1 and bool(data_source_types)
    feature_version_consistent = len(feature_versions) <= 1 and bool(feature_versions)
    schema_version_consistent = bool(schema_versions) and distribution.get("schema_version_consistent") is True

    final_output_exists_count = sum(1 for path in output_paths if path.is_file())
    chunk_manifest_count = sum(1 for path in manifest_paths if path.is_file())
    chunk_audit_count = sum(1 for path in audit_paths if path.is_file())
    success_manifest_count = sum(1 for manifest in chunk_manifests if manifest.get("status") == "SUCCESS")
    failed_manifest_count = sum(1 for manifest in chunk_manifests if manifest.get("status") == "FAILED")
    run_completed = int(run_manifest.get("completed_chunk_count") or 0)
    run_failed = int(run_manifest.get("failed_chunk_count") or 0)
    duplicate_output_count = len(output_paths) - len({str(path) for path in output_paths})
    duplicate_manifest_count = len(manifest_paths) - len({str(path) for path in manifest_paths})
    orphan_output_count, orphan_manifest_count = _orphan_counts(run_id, output_paths, manifest_paths)
    resume_success_skip_ready = _resume_success_skip_ready(phase4s_summary)

    checked_chunk_count = len(executions)
    row_count_match = bool(row_matches) and all(row_matches)
    eligible_excluded_count_match = bool(eligible_matches) and all(eligible_matches)
    schema_validation_all_ok = bool(schema_ok) and all(schema_ok)
    leakage_audit_all_ok = bool(leakage_ok) and all(leakage_ok)
    integrity_status = _integrity_status(
        checked_chunk_count=checked_chunk_count,
        final_output_exists_count=final_output_exists_count,
        tmp_leftover_count=len(tmp_leftovers),
        chunk_manifest_count=chunk_manifest_count,
        chunk_audit_count=chunk_audit_count,
        row_count_match=row_count_match,
        eligible_excluded_count_match=eligible_excluded_count_match,
        schema_validation_all_ok=schema_validation_all_ok,
        leakage_audit_all_ok=leakage_audit_all_ok,
        resume_success_skip_ready=resume_success_skip_ready,
        duplicate_output_count=duplicate_output_count,
        duplicate_manifest_count=duplicate_manifest_count,
        orphan_output_count=orphan_output_count,
        orphan_manifest_count=orphan_manifest_count,
        data_source_type_consistent=data_source_type_consistent,
        feature_version_consistent=feature_version_consistent,
        schema_version_consistent=schema_version_consistent,
    )
    return {
        "status": "READY" if integrity_status == READY else "BLOCKED",
        "integrity_status": integrity_status,
        "run_id": run_id,
        "checked_chunk_count": checked_chunk_count,
        "final_output_exists_count": final_output_exists_count,
        "tmp_leftover_count": len(tmp_leftovers),
        "chunk_manifest_count": chunk_manifest_count,
        "chunk_audit_count": chunk_audit_count,
        "success_manifest_count": success_manifest_count,
        "failed_manifest_count": failed_manifest_count,
        "run_manifest_exists": run_manifest_path.is_file(),
        "run_manifest_completed_chunk_count": run_completed,
        "run_manifest_failed_chunk_count": run_failed,
        "row_count_match": row_count_match,
        "eligible_excluded_count_match": eligible_excluded_count_match,
        "schema_validation_all_ok": schema_validation_all_ok,
        "leakage_audit_all_ok": leakage_audit_all_ok,
        "resume_success_skip_ready": resume_success_skip_ready,
        "duplicate_output_count": duplicate_output_count,
        "duplicate_manifest_count": duplicate_manifest_count,
        "orphan_output_count": orphan_output_count,
        "orphan_manifest_count": orphan_manifest_count,
        "data_source_type_consistent": data_source_type_consistent,
        "feature_version_consistent": feature_version_consistent,
        "schema_version_consistent": schema_version_consistent,
        "tmp_leftover_paths": tmp_leftovers,
        "recommended_next_action": _recommended_action(integrity_status),
        "full_range_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(SUMMARY_PATH),
    }


def _base_integrity_summary(phase4s_summary: dict[str, Any], integrity_status: str) -> dict[str, Any]:
    return {
        "status": "SKIPPED",
        "integrity_status": integrity_status,
        "run_id": phase4s_summary.get("run_id"),
        "checked_chunk_count": 0,
        "final_output_exists_count": 0,
        "tmp_leftover_count": 0,
        "chunk_manifest_count": 0,
        "chunk_audit_count": 0,
        "success_manifest_count": 0,
        "failed_manifest_count": 0,
        "run_manifest_completed_chunk_count": 0,
        "run_manifest_failed_chunk_count": 0,
        "row_count_match": False,
        "eligible_excluded_count_match": False,
        "schema_validation_all_ok": False,
        "leakage_audit_all_ok": False,
        "resume_success_skip_ready": False,
        "duplicate_output_count": 0,
        "duplicate_manifest_count": 0,
        "orphan_output_count": 0,
        "orphan_manifest_count": 0,
        "data_source_type_consistent": False,
        "feature_version_consistent": False,
        "schema_version_consistent": False,
        "recommended_next_action": _recommended_action(integrity_status),
        "full_range_generation_executed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(SUMMARY_PATH),
    }


def _read_output_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    return [dict(row) for row in rows if isinstance(row, dict)]


def _int_field(payload: dict[str, Any], key: str, default: int) -> int:
    value = payload.get(key)
    if value is None:
        return default
    return int(value)


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _orphan_counts(run_id: str, output_paths: list[Path], manifest_paths: list[Path]) -> tuple[int, int]:
    referenced_outputs = {str(path) for path in output_paths}
    referenced_manifests = {str(path) for path in manifest_paths}
    output_parent = output_paths[0].parent if output_paths else Path()
    manifest_parent = manifest_paths[0].parent if manifest_paths else Path()
    orphan_outputs = [
        path
        for path in output_parent.glob("*.json")
        if str(path) not in referenced_outputs
    ] if output_parent.exists() else []
    orphan_manifests = [
        path
        for path in manifest_parent.glob(f"{run_id}_*manifest.json")
        if not path.name.endswith("_run_manifest.json") and str(path) not in referenced_manifests
    ] if manifest_parent.exists() else []
    return len(orphan_outputs), len(orphan_manifests)


def _resume_success_skip_ready(phase4s_summary: dict[str, Any]) -> bool:
    run_id = str(phase4s_summary.get("run_id") or "")
    readiness = phase4s_summary.get("readiness_summary", {})
    input_path = Path(str(readiness.get("input_path") or ""))
    storage_format = str(readiness.get("storage_format") or "")
    if not run_id or not input_path.is_file() or not storage_format:
        return False
    try:
        records = create_storage_backend(storage_format).read_records(input_path)
    except Exception:
        return False
    max_codes = int(readiness.get("distribution_audit", {}).get("code_count_max") or 1)
    plans = build_full_range_chunk_plan(records, run_id=run_id, data_source_type=str(readiness.get("data_source_type") or "mock"), max_codes_per_chunk=max_codes)
    paths = resolve_full_range_paths(runtime_dir=Path(input_path).parents[4], report_dir=Path(phase4s_summary.get("summary_path", ".")).parent)
    resume = check_resume_restart(plans, manifest_dir=paths.manifest_dir, tmp_dir=paths.tmp_dir)
    executed_ids = set(phase4s_summary.get("runner_summary", {}).get("executed_chunk_ids", []))
    return executed_ids.issubset(set(resume.completed_chunk_ids)) and not resume.manifest_inconsistencies


def _integrity_status(**values: Any) -> str:
    checked = int(values["checked_chunk_count"])
    if checked <= 0:
        return SKIPPED_NO_BATCH_OUTPUT
    if values["final_output_exists_count"] != checked or values["tmp_leftover_count"] != 0:
        return BLOCKED_MISSING_OUTPUT
    if values["chunk_manifest_count"] != checked or not values["row_count_match"] or not values["eligible_excluded_count_match"]:
        return BLOCKED_MANIFEST_MISMATCH
    if values["chunk_audit_count"] != checked or not values["schema_validation_all_ok"] or not values["leakage_audit_all_ok"]:
        return BLOCKED_AUDIT_FAILURE
    if not values["resume_success_skip_ready"]:
        return BLOCKED_RESUME_STATE
    if values["duplicate_output_count"] or values["duplicate_manifest_count"] or values["orphan_output_count"] or values["orphan_manifest_count"]:
        return BLOCKED_ORPHAN_ARTIFACT
    if not (values["data_source_type_consistent"] and values["feature_version_consistent"] and values["schema_version_consistent"]):
        return BLOCKED_MANIFEST_MISMATCH
    return READY


def _recommended_action(integrity_status: str) -> str:
    if integrity_status == READY:
        return "ready for controlled batch expansion with the same stop-on-first-failure guard"
    if integrity_status == SKIPPED_NO_BATCH_OUTPUT:
        return "run Phase4-S first controlled batch before auditing integrity"
    if integrity_status == BLOCKED_MISSING_OUTPUT:
        return "inspect missing final outputs or leftover tmp files before retrying"
    if integrity_status == BLOCKED_MANIFEST_MISMATCH:
        return "fix manifest/output count mismatch before expanding controlled batch"
    if integrity_status == BLOCKED_AUDIT_FAILURE:
        return "fix schema or leakage audit failure before expanding controlled batch"
    if integrity_status == BLOCKED_RESUME_STATE:
        return "fix resume state so SUCCESS chunks become skip candidates"
    return "remove duplicate or orphan artifacts before expanding controlled batch"


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "password", "cookie", "token", "http://", "https://")
    return not any(term in text for term in terms)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any], integrity: dict[str, Any]) -> None:
    lines = [
        "# Phase4-T Post-batch Integrity Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- integrity_status: `{integrity.get('integrity_status')}`",
        f"- recommended_next_action: {integrity.get('recommended_next_action')}",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Integrity Summary",
        "",
        f"- checked_chunk_count: {integrity.get('checked_chunk_count')}",
        f"- final_output_exists_count: {integrity.get('final_output_exists_count')}",
        f"- tmp_leftover_count: {integrity.get('tmp_leftover_count')}",
        f"- chunk_manifest_count: {integrity.get('chunk_manifest_count')}",
        f"- chunk_audit_count: {integrity.get('chunk_audit_count')}",
        f"- success_manifest_count: {integrity.get('success_manifest_count')}",
        f"- failed_manifest_count: {integrity.get('failed_manifest_count')}",
        f"- row_count_match: {integrity.get('row_count_match')}",
        f"- eligible_excluded_count_match: {integrity.get('eligible_excluded_count_match')}",
        f"- schema_validation_all_ok: {integrity.get('schema_validation_all_ok')}",
        f"- leakage_audit_all_ok: {integrity.get('leakage_audit_all_ok')}",
        f"- resume_success_skip_ready: {integrity.get('resume_success_skip_ready')}",
        f"- duplicate_output_count: {integrity.get('duplicate_output_count')}",
        f"- duplicate_manifest_count: {integrity.get('duplicate_manifest_count')}",
        f"- orphan_output_count: {integrity.get('orphan_output_count')}",
        f"- orphan_manifest_count: {integrity.get('orphan_manifest_count')}",
        "",
        "## Checks",
        "",
    ]
    for name, value in result["checks"].items():
        mark = "OK" if value else "NG"
        lines.append(f"- {mark}: `{name}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- This audit only checks artifacts from a two-chunk controlled batch.",
            "- It does not implement all-chunk generation, labels, dataset building, training, inference, backtest, broker API, orders, trading, or Portfolio auto-update.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
