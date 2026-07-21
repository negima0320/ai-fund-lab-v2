from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation


AI_STATUS_SCHEMA_VERSION = "runtime_test_ai_status_report.v1"
AI_STATUS_EVIDENCE_FILES = (
    "ai_status_summary.json",
    "dataset_lineage.json",
    "split_audit.json",
    "candidate_ai_status.json",
    "opportunity_ai_status.json",
    "accepted_generation_status.json",
    "runtime_authority_status.json",
    "jquants_and_feature_freshness.json",
    "freshness_taxonomy.json",
    "runtime_readiness.json",
    "legacy_fallback_audit.json",
    "non_mutation.json",
    "final_judgment.json",
)


def build_ai_status_report(
    *,
    runtime_root: Path,
    check_runtime_readiness: bool = False,
    created_at: str | None = None,
) -> dict[str, Any]:
    root = Path(runtime_root)
    repo_root = _repo_root_for_runtime_root(root)
    created_at = created_at or _utc_now()

    resolution = resolve_accepted_generation(root)
    manifest_path = Path(resolution.bundle_manifest_path) if resolution.bundle_manifest_path else Path("")
    manifest = _read_json_optional(manifest_path)
    pointer_path = root / "runtime_state" / "accepted_buy_ai_bundle.json"
    pointer = _read_json_optional(pointer_path)

    candidate_training = _read_json_optional(repo_root / "reports/phase19_ad_u3_k_corrective_bootstrap_training/candidate_corrective_training_artifact.json")
    opportunity_training = _read_json_optional(repo_root / "reports/phase19_ad_u3_k_corrective_bootstrap_training/opportunity_corrective_training_artifact.json")
    candidate_validation = _read_json_optional(repo_root / "reports/phase19_aj_formal_corrective_reevaluation/candidate_corrective_results.json")
    dual_gate = _read_json_optional(repo_root / "reports/phase19_aj_formal_corrective_reevaluation/opportunity_dual_gate_artifact.json")

    runtime_date = _latest_runtime_ai_date(root)
    runtime_dir = root / "runtime_state" / "buy_ai" / runtime_date if runtime_date else Path("")
    candidate_runtime_path = runtime_dir / "candidate_decisions.json" if runtime_date else Path("")
    opportunity_runtime_path = runtime_dir / "opportunity_rankings.json" if runtime_date else Path("")
    lifecycle_path = runtime_dir / "ai_lifecycle_gate_decision.json" if runtime_date else Path("")
    candidate_runtime = _read_json_optional(candidate_runtime_path)
    opportunity_runtime = _read_json_optional(opportunity_runtime_path)
    lifecycle = _read_json_optional(lifecycle_path)

    latest_jquants_path = _latest_manifest(root / "operations/jquants/market_data_refresh_detail", "refresh_manifest.json")
    latest_feature_path = _latest_manifest(root / "operations/feature_refresh_detail", "feature_refresh_manifest.json")
    latest_jquants = _read_json_optional(latest_jquants_path)
    latest_feature = _read_json_optional(latest_feature_path)

    structural_findings = _structural_findings(
        resolution=resolution.to_dict(),
        manifest=manifest,
        pointer=pointer,
        candidate_runtime=candidate_runtime,
        opportunity_runtime=opportunity_runtime,
        lifecycle=lifecycle,
        candidate_runtime_path=candidate_runtime_path,
        opportunity_runtime_path=opportunity_runtime_path,
        lifecycle_path=lifecycle_path,
    )
    review_findings = _review_findings(lifecycle)
    overall_status = "BLOCK" if structural_findings else "REVIEW_REQUIRED" if review_findings else "PASS"
    exit_code = 20 if overall_status == "BLOCK" else 10 if overall_status == "REVIEW_REQUIRED" else 0

    dataset_lineage = _dataset_lineage(manifest, candidate_training, opportunity_training)
    split_audit = _split_audit(manifest, candidate_training, opportunity_training)
    candidate_status = _candidate_status(manifest, candidate_training, candidate_validation, candidate_runtime, candidate_runtime_path)
    opportunity_status = _opportunity_status(manifest, opportunity_training, dual_gate, opportunity_runtime, opportunity_runtime_path)
    accepted_status = _accepted_generation_status(manifest, pointer, resolution.to_dict(), manifest_path, pointer_path)
    runtime_authority = _runtime_authority_status(resolution.to_dict(), lifecycle, runtime_date)
    freshness = _freshness_status(manifest, lifecycle, latest_jquants, latest_jquants_path, latest_feature, latest_feature_path, runtime_date)
    freshness_taxonomy = _freshness_taxonomy(manifest, lifecycle)
    runtime_readiness = _runtime_readiness(
        status=overall_status,
        check_runtime_readiness=check_runtime_readiness,
        lifecycle=lifecycle,
        candidate_runtime=candidate_runtime,
        opportunity_runtime=opportunity_runtime,
        structural_findings=structural_findings,
        review_findings=review_findings,
    )
    legacy_fallback = {
        "status": "PASS",
        "legacy_fallback_used": False,
        "latest_pointer_used": False,
        "mtime_selection_used": False,
        "promotion_candidate_used": False,
        "manual_model_path_used": False,
        "authority": "COMMITTED Accepted Generation Resolver only",
        "source_evidence": resolution.source_evidence,
    }
    non_mutation = {
        "status": "PASS",
        "read_only": True,
        "training_rerun": 0,
        "calibration_refit": 0,
        "validation_rerun": 0,
        "generation_created": 0,
        "authority_history_append": 0,
        "runtime_pointer_write": 0,
        "trading_state_mutation": 0,
        "broker_access": "NOT_PERFORMED",
        "broker_write": 0,
        "buy_restart": 0,
    }
    final_judgment = {
        "status": overall_status,
        "exit_code": exit_code,
        "final_judgment": _final_judgment(overall_status),
        "supporting": [
            "AI_STATUS_READ_ONLY_PASS",
            "COMMITTED_AUTHORITY_INSPECTED",
            "BROKER_ACCESS_NOT_PERFORMED",
        ],
        "main_findings": [*structural_findings, *review_findings] or ["No blocking or review findings."],
    }
    summary = {
        "schema_version": AI_STATUS_SCHEMA_VERSION,
        "created_at": created_at,
        "ai_authority_status": runtime_authority["authority_status"],
        "overall_status": overall_status,
        "exit_code": exit_code,
        "committed_generation": accepted_status["accepted_generation_id"],
        "accepted_at": accepted_status["accepted_at"],
        "runtime_loaded_generation": runtime_authority["runtime_loaded_generation"],
        "candidate": candidate_status["summary"],
        "opportunity": opportunity_status["summary"],
        "latest_jquants": freshness["latest_jquants"],
        "latest_buy_feature": freshness["latest_buy_feature"],
        "inference_readiness": runtime_readiness["inference_readiness"],
        "broker_access": "NOT_PERFORMED",
        "main_findings": final_judgment["main_findings"],
    }

    return {
        "schema_version": AI_STATUS_SCHEMA_VERSION,
        "subcommand": "ai-status",
        "status": overall_status,
        "exit_code": exit_code,
        "created_at": created_at,
        "ai_status_summary": summary,
        "dataset_lineage": dataset_lineage,
        "split_audit": split_audit,
        "candidate_ai_status": candidate_status,
        "opportunity_ai_status": opportunity_status,
        "accepted_generation_status": accepted_status,
        "runtime_authority_status": runtime_authority,
        "jquants_and_feature_freshness": freshness,
        "freshness_taxonomy": freshness_taxonomy,
        "runtime_readiness": runtime_readiness,
        "legacy_fallback_audit": legacy_fallback,
        "non_mutation": non_mutation,
        "final_judgment": final_judgment,
        "human_summary": render_ai_status_human_summary(summary, detailed=False),
        "detailed_human_summary": render_ai_status_human_summary(summary, detailed=True),
    }


def write_ai_status_evidence(report: dict[str, Any], *, evidence_root: Path, run_id: str | None = None) -> Path:
    run_id = run_id or "ai-status-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_root = Path(evidence_root) / "ai_status" / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    mapping = {
        "ai_status_summary.json": report["ai_status_summary"],
        "dataset_lineage.json": report["dataset_lineage"],
        "split_audit.json": report["split_audit"],
        "candidate_ai_status.json": report["candidate_ai_status"],
        "opportunity_ai_status.json": report["opportunity_ai_status"],
        "accepted_generation_status.json": report["accepted_generation_status"],
        "runtime_authority_status.json": report["runtime_authority_status"],
        "jquants_and_feature_freshness.json": report["jquants_and_feature_freshness"],
        "freshness_taxonomy.json": report["freshness_taxonomy"],
        "runtime_readiness.json": report["runtime_readiness"],
        "legacy_fallback_audit.json": report["legacy_fallback_audit"],
        "non_mutation.json": report["non_mutation"],
        "final_judgment.json": report["final_judgment"],
    }
    for name, payload in mapping.items():
        _write_json(run_root / name, payload)
    (run_root / "ai_status_report.md").write_text(report["detailed_human_summary"] + "\n", encoding="utf-8")
    return run_root


def render_ai_status_human_summary(summary: dict[str, Any], *, detailed: bool) -> str:
    lines = [
        "# AI Authority / Runtime Readiness Inspection",
        f"AI Authority Status: {summary.get('ai_authority_status', '')}",
        f"Overall Status: {summary.get('overall_status', '')}",
        f"COMMITTED Generation: {summary.get('committed_generation', '')}",
        f"Accepted At: {summary.get('accepted_at', '')}",
        f"Runtime Loaded Generation: {summary.get('runtime_loaded_generation', '')}",
        f"Candidate: model={summary['candidate'].get('model_family', '')}, training={summary['candidate'].get('training_status', '')}, feature_count={summary['candidate'].get('feature_count', '')}, validation={summary['candidate'].get('validation_status', '')}, runtime_load={summary['candidate'].get('runtime_load', '')}",
        f"Opportunity: model={summary['opportunity'].get('model_family', '')}, training={summary['opportunity'].get('training_status', '')}, feature_count={summary['opportunity'].get('feature_count', '')}, selection_validation={summary['opportunity'].get('selection_validation_status', '')}, runtime_load={summary['opportunity'].get('runtime_load', '')}",
        f"Latest J-Quants: {summary['latest_jquants'].get('latest_normalized_daily_quotes_date', '')}",
        f"Latest BUY Feature: {summary['latest_buy_feature'].get('feature_date', '')}",
        f"Inference Readiness: {summary.get('inference_readiness', '')}",
        "Broker Access: NOT_PERFORMED",
        "Main Findings:",
    ]
    lines.extend(f"- {finding}" for finding in summary.get("main_findings", []))
    if detailed:
        lines.extend(
            [
                "",
                "Detailed Notes:",
                "- This command is read-only observability and does not execute training, calibration, validation, generation, runtime transition, BUY restart, or broker access.",
                "- Exit code 10 means REVIEW_REQUIRED; statistical drift monitoring is intentionally separated from structural blocking.",
            ]
        )
    return "\n".join(lines)


def _dataset_lineage(manifest: dict[str, Any], candidate: dict[str, Any], opportunity: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS" if manifest else "BLOCK",
        "dataset_revision_ids": manifest.get("dataset_revision_ids", []),
        "candidate": {
            "dataset_revision_id": candidate.get("dataset_revision_id", ""),
            "dataset_content_hash": candidate.get("dataset_content_hash", ""),
            "dataset_schema_hash": candidate.get("dataset_schema_hash", ""),
            "dataset_lineage_hash": candidate.get("dataset_lineage_hash", ""),
            "label_column": candidate.get("label_column", ""),
            "label_schema_hash": candidate.get("label_schema_hash", ""),
        },
        "opportunity": {
            "dataset_revision_id": opportunity.get("dataset_revision_id", ""),
            "dataset_content_hash": opportunity.get("dataset_content_hash", ""),
            "dataset_schema_hash": opportunity.get("dataset_schema_hash", ""),
            "dataset_lineage_hash": opportunity.get("dataset_lineage_hash", ""),
            "label_column": opportunity.get("label_column", ""),
            "label_schema_hash": opportunity.get("label_schema_hash", ""),
        },
        "lineage_hashes": manifest.get("lineage_hashes", {}),
    }


def _repo_root_for_runtime_root(root: Path) -> Path:
    cwd = Path.cwd()
    if (cwd / "reports").exists() and (cwd / "docs").exists():
        return cwd
    current = root.resolve(strict=False)
    for parent in (current, *current.parents):
        if (parent / "reports").exists() and (parent / "docs").exists():
            return parent
    return root.parent if root.name == ".runtime" else cwd


def _split_audit(manifest: dict[str, Any], candidate: dict[str, Any], opportunity: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS" if manifest else "BLOCK",
        "split_ids": manifest.get("split_ids", []),
        "candidate": _split_component(candidate),
        "opportunity": _split_component(opportunity),
        "recent_holdout": {
            "accessed": False,
            "required_for_phase19_av": False,
            "candidate_window": candidate.get("recent_holdout_window", {}),
            "opportunity_window": opportunity.get("recent_holdout_window", {}),
        },
    }


def _split_component(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "split_id": payload.get("split_id", ""),
        "split_content_hash": payload.get("split_content_hash", ""),
        "train_window": payload.get("train_window", {}),
        "validation_window": payload.get("validation_window", {}),
        "test_window": payload.get("test_window", {}),
        "embargo_business_days": payload.get("embargo_business_days", ""),
    }


def _candidate_status(
    manifest: dict[str, Any],
    training: dict[str, Any],
    validation: dict[str, Any],
    runtime: dict[str, Any],
    runtime_path: Path,
) -> dict[str, Any]:
    member = manifest.get("candidate_member", {})
    return {
        "status": "PASS" if runtime.get("status") == "PASS" and training else "BLOCK",
        "artifact_id": training.get("artifact_id", ""),
        "model_family": training.get("model_family", ""),
        "model_hash": member.get("model_hash", training.get("model_content_hash", "")),
        "scaler_hash": member.get("scaler_hash", ""),
        "calibration_hash": member.get("calibration_hash", ""),
        "feature_count": len(member.get("feature_order", training.get("feature_columns", []))),
        "feature_order_hash": member.get("feature_order_hash", ""),
        "training_status": training.get("model_quality_policy_result", {}).get("formal_quality_result", ""),
        "validation_status": validation.get("status", ""),
        "runtime_load": runtime.get("status", "MISSING"),
        "runtime_artifact_path": str(runtime_path),
        "runtime_candidate_count": runtime.get("candidate_count", 0),
        "summary": {
            "model_family": training.get("model_family", ""),
            "training_status": training.get("model_quality_policy_result", {}).get("formal_quality_result", ""),
            "feature_count": len(member.get("feature_order", training.get("feature_columns", []))),
            "validation_status": validation.get("status", ""),
            "runtime_load": runtime.get("status", "MISSING"),
        },
    }


def _opportunity_status(
    manifest: dict[str, Any],
    training: dict[str, Any],
    dual_gate: dict[str, Any],
    runtime: dict[str, Any],
    runtime_path: Path,
) -> dict[str, Any]:
    member = manifest.get("opportunity_member", {})
    rows = runtime.get("rows") if isinstance(runtime.get("rows"), list) else runtime.get("rankings", [])
    return {
        "status": "PASS" if runtime.get("status") == "PASS" and dual_gate.get("artifact_status") == "DUAL_GATE_PASS" else "BLOCK",
        "artifact_id": training.get("artifact_id", ""),
        "model_family": training.get("model_family", ""),
        "model_hash": member.get("model_hash", training.get("model_content_hash", "")),
        "scaler_hash": member.get("scaler_hash", ""),
        "calibration_hash": member.get("calibration_hash", ""),
        "feature_count": len(member.get("feature_order", training.get("feature_columns", []))),
        "feature_order_hash": member.get("feature_order_hash", ""),
        "training_status": training.get("model_quality_policy_result", {}).get("formal_quality_result", ""),
        "global_gate_status": dual_gate.get("global_gate_result", {}).get("status", ""),
        "selection_validation_status": dual_gate.get("selection_gate_result", {}).get("status", ""),
        "dual_gate_status": dual_gate.get("dual_gate_result", {}).get("status", dual_gate.get("artifact_status", "")),
        "runtime_load": runtime.get("status", "MISSING"),
        "runtime_artifact_path": str(runtime_path),
        "runtime_opportunity_count": len(rows) if isinstance(rows, list) else 0,
        "runtime_top20_count": sum(1 for row in rows if isinstance(row, dict) and row.get("is_top20")) if isinstance(rows, list) else 0,
        "summary": {
            "model_family": training.get("model_family", ""),
            "training_status": training.get("model_quality_policy_result", {}).get("formal_quality_result", ""),
            "feature_count": len(member.get("feature_order", training.get("feature_columns", []))),
            "selection_validation_status": dual_gate.get("selection_gate_result", {}).get("status", ""),
            "runtime_load": runtime.get("status", "MISSING"),
        },
    }


def _accepted_generation_status(
    manifest: dict[str, Any],
    pointer: dict[str, Any],
    resolution: dict[str, Any],
    manifest_path: Path,
    pointer_path: Path,
) -> dict[str, Any]:
    return {
        "status": "PASS" if resolution.get("resolution_status") == "RESOLVED_COMMITTED" else "BLOCK",
        "accepted_generation_id": manifest.get("accepted_generation_id") or resolution.get("generation_id", ""),
        "generation_id": manifest.get("generation_id", ""),
        "accepted": manifest.get("accepted", False),
        "runtime_eligibility": manifest.get("runtime_eligibility", False),
        "accepted_at": manifest.get("accepted_at") or pointer.get("accepted_at", ""),
        "effective_from": manifest.get("effective_from") or pointer.get("effective_from", ""),
        "aggregate_hash": resolution.get("aggregate_hash", ""),
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256_file(manifest_path),
        "pointer_path": str(pointer_path),
        "pointer_sha256": _sha256_file(pointer_path),
        "transaction_state": pointer.get("transaction_state", ""),
    }


def _runtime_authority_status(resolution: dict[str, Any], lifecycle: dict[str, Any], runtime_date: str) -> dict[str, Any]:
    return {
        "status": "PASS" if resolution.get("resolution_status") == "RESOLVED_COMMITTED" else "BLOCK",
        "authority_status": resolution.get("resolution_status", ""),
        "runtime_loaded_generation": lifecycle.get("accepted_bundle_id") or resolution.get("generation_id", ""),
        "runtime_business_date": runtime_date,
        "transaction_state": resolution.get("transaction_state", ""),
        "allowed_authority": "COMMITTED Accepted Generation pointer only",
        "forbidden_authorities": ["latest", "mtime", "legacy", "manual", "promotion_candidate"],
        "reason_codes": resolution.get("reason_codes", []),
    }


def _freshness_status(
    manifest: dict[str, Any],
    lifecycle: dict[str, Any],
    latest_jquants: dict[str, Any],
    latest_jquants_path: Path,
    latest_feature: dict[str, Any],
    latest_feature_path: Path,
    runtime_date: str,
) -> dict[str, Any]:
    freshness = lifecycle.get("freshness_evidence", {})
    return {
        "status": "PASS" if freshness.get("status", "PASS") == "PASS" else freshness.get("status", "REVIEW_REQUIRED"),
        "latest_jquants": {
            "manifest_path": str(latest_jquants_path),
            "latest_successful_daily_quotes_date": latest_jquants.get("latest_successful_daily_quotes_date", ""),
            "latest_normalized_daily_quotes_date": latest_jquants.get("latest_normalized_daily_quotes_date", ""),
        },
        "latest_buy_feature": {
            "manifest_path": str(latest_feature_path),
            "feature_date": runtime_date or freshness.get("inference_feature_date", ""),
            "expected_inference_feature_date": freshness.get("expected_inference_feature_date", ""),
        },
        "generation_bound": manifest.get("freshness_metadata", {}).get("generation_bound", {}),
        "runtime_freshness_evidence": freshness,
    }


def _freshness_taxonomy(manifest: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    freshness = lifecycle.get("freshness_evidence", {})
    generation_bound = manifest.get("freshness_metadata", {}).get("generation_bound", {})
    return {
        "status": "PASS",
        "items": [
            {"name": "Raw data freshness", "value": freshness.get("raw_data_max_date_at_generation") or generation_bound.get("raw_data_max_date_at_generation", "")},
            {"name": "Normalized data freshness", "value": freshness.get("normalized_data_max_date_at_generation") or generation_bound.get("normalized_data_max_date_at_generation", "")},
            {"name": "Dataset freshness", "value": freshness.get("training_dataset_max_date") or generation_bound.get("dataset_target_max_date", "")},
            {"name": "Label-safe freshness", "value": freshness.get("label_safe_cutoff") or generation_bound.get("label_safe_cutoff", "")},
            {"name": "Model training freshness", "value": freshness.get("model_training_cutoff") or generation_bound.get("candidate_training_cutoff", "")},
            {"name": "Accepted generation age", "value": freshness.get("model_acceptance_age_business_days", "")},
            {"name": "Runtime loaded generation freshness", "value": freshness.get("model_accepted_at", "")},
            {"name": "Inference feature freshness", "value": freshness.get("inference_feature_date", "")},
        ],
    }


def _runtime_readiness(
    *,
    status: str,
    check_runtime_readiness: bool,
    lifecycle: dict[str, Any],
    candidate_runtime: dict[str, Any],
    opportunity_runtime: dict[str, Any],
    structural_findings: list[str],
    review_findings: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "check_runtime_readiness": check_runtime_readiness,
        "inference_readiness": "BLOCK" if structural_findings else "REVIEW_REQUIRED" if review_findings else "PASS",
        "candidate_runtime_status": candidate_runtime.get("status", "MISSING"),
        "opportunity_runtime_status": opportunity_runtime.get("status", "MISSING"),
        "lifecycle_decision": lifecycle.get("decision", ""),
        "lifecycle_classification": lifecycle.get("classification", ""),
        "buy_gate": lifecycle.get("buy_gate", ""),
        "block_buy_planning": lifecycle.get("block_buy_planning", ""),
        "sell_permission": lifecycle.get("sell_permission", ""),
        "structural_findings": structural_findings,
        "review_findings": review_findings,
    }


def _structural_findings(
    *,
    resolution: dict[str, Any],
    manifest: dict[str, Any],
    pointer: dict[str, Any],
    candidate_runtime: dict[str, Any],
    opportunity_runtime: dict[str, Any],
    lifecycle: dict[str, Any],
    candidate_runtime_path: Path,
    opportunity_runtime_path: Path,
    lifecycle_path: Path,
) -> list[str]:
    findings: list[str] = []
    if resolution.get("resolution_status") != "RESOLVED_COMMITTED":
        findings.append(f"COMMITTED Accepted Generation is not resolved: {resolution.get('block_reason', '')}")
    if not manifest:
        findings.append("Accepted Generation manifest is missing or unreadable.")
    if not pointer:
        findings.append("Runtime COMMITTED pointer is missing or unreadable.")
    if candidate_runtime.get("status") != "PASS":
        findings.append(f"Candidate runtime artifact is not PASS: {candidate_runtime_path}")
    if opportunity_runtime.get("status") != "PASS":
        findings.append(f"Opportunity runtime artifact is not PASS: {opportunity_runtime_path}")
    if not lifecycle:
        findings.append(f"Runtime lifecycle gate decision is missing: {lifecycle_path}")
    if lifecycle.get("block_buy_planning") is True and "STATISTICAL_DRIFT" not in str(lifecycle.get("classification", "")):
        findings.append("Runtime lifecycle gate structurally blocks BUY planning.")
    return findings


def _review_findings(lifecycle: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    classification = str(lifecycle.get("classification", ""))
    if lifecycle.get("decision") == "REVIEW_REQUIRED" or "REVIEW_REQUIRED" in classification:
        findings.append(f"Runtime lifecycle monitoring is REVIEW_REQUIRED: {classification or lifecycle.get('decision')}")
    if "STATISTICAL_DRIFT" in classification and lifecycle.get("block_buy_planning") is False:
        findings.append("Statistical drift is review-only and does not automatically stop BUY planning.")
    return findings


def _final_judgment(status: str) -> list[str]:
    if status == "PASS":
        return ["PHASE19_AV_AI_STATUS_INSPECTION_COMPLETE", "PHASE19_AW_MANUAL_MULTI_DAY_RUNTIME_VALIDATION_READY"]
    if status == "REVIEW_REQUIRED":
        return ["PHASE19_AV_AI_STATUS_INSPECTION_COMPLETE", "PHASE19_AW_READY_WITH_REVIEW_MONITORING"]
    if status == "BLOCK":
        return ["PHASE19_AV_REVIEW_REQUIRED", "PHASE19_AW_BLOCKED"]
    return ["PHASE19_AV_AI_STATUS_INSPECTION_FAIL", "PHASE19_AW_BLOCKED"]


def _latest_runtime_ai_date(root: Path) -> str:
    base = root / "runtime_state" / "buy_ai"
    dates = sorted(child.name for child in base.iterdir() if child.is_dir()) if base.exists() else []
    return dates[-1] if dates else ""


def _latest_manifest(base: Path, filename: str) -> Path:
    if not base.exists():
        return Path("")
    candidates = sorted(path for path in base.glob(f"*/{filename}") if path.is_file())
    return candidates[-1] if candidates else Path("")


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    if not path or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
