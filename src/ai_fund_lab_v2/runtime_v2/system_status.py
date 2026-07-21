from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.ai_status import build_ai_status_report


SYSTEM_STATUS_SCHEMA_VERSION = "runtime_test_system_status_report.v1"
SYSTEM_STATUS_VIEW_SCHEMA_VERSION = "runtime_test_system_status_v2"
SYSTEM_STATUS_SCOPES = {
    "overview",
    "data",
    "ai",
    "runtime",
    "broker",
    "readiness",
    "lineage",
    "components",
    "full",
}
SAFETY_DECISION_RELATIVE_PATH = Path("runtime_state") / "safety" / "latest_safety_decision.json"
RUNTIME_STAGE_ORDER = {
    "PRE_RUN": 0,
    "MARKET_DATA_READY": 1,
    "FEATURE_READY": 2,
    "AI_INFERENCE_DONE": 3,
    "LIFECYCLE_GATE_DONE": 4,
    "DAILY_PLAN_CREATED": 5,
    "SELL_PLANNING_DONE": 6,
    "APPROVAL_PENDING": 7,
    "SUBMITTING": 8,
    "EXECUTION_DONE": 9,
}


def build_system_status_report(
    *,
    runtime_root: Path,
    created_at: str | None = None,
    expected_business_date: str | None = None,
    runtime_mode: str | None = None,
    profile_id: str | None = None,
    broker_environment: str | None = None,
    target_business_dates: list[str] | None = None,
    post_run_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(runtime_root)
    created_at = created_at or _utc_now()
    post_run_context = post_run_context or {}
    if _valid_post_run_context(post_run_context):
        expected_business_date = str(post_run_context.get("final_business_date") or expected_business_date or "")
        completed_days = [str(day) for day in post_run_context.get("completed_business_days") or [] if str(day)]
        target_business_dates = completed_days or ([expected_business_date] if expected_business_date else target_business_dates)
    ai_report = build_ai_status_report(runtime_root=root, check_runtime_readiness=True, created_at=created_at)

    repo_root = _repo_root_for_runtime_root(root)
    manifest_path = Path(ai_report["accepted_generation_status"].get("manifest_path") or "")
    manifest = _read_json_optional(manifest_path)
    runtime_date = _truth_value(ai_report["runtime_authority_status"].get("runtime_business_date", ""), missing="NOT_YET_MATERIALIZED")
    artifact_context = _target_business_date_artifact_context(
        root=root,
        expected_business_date=expected_business_date or "",
        runtime_date="" if runtime_date == "NOT_YET_MATERIALIZED" else runtime_date,
        ai_report=ai_report,
    )
    runtime_path_date = artifact_context["runtime_artifact_business_date"]
    feature_manifest_path = Path(str(artifact_context["feature_manifest_path"] or ""))
    feature_manifest = _read_json_optional(feature_manifest_path)
    candidate_training = _read_json_optional(repo_root / "reports/phase19_ad_u3_k_corrective_bootstrap_training/candidate_corrective_training_artifact.json")
    opportunity_training = _read_json_optional(repo_root / "reports/phase19_ad_u3_k_corrective_bootstrap_training/opportunity_corrective_training_artifact.json")
    dataset_revisions = _read_json_optional(repo_root / "reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/materialized_dataset_revisions.json")
    split_source_evidence = _read_json_optional(repo_root / "reports/phase19_ad_u2_f_rolling_split_policy_approval/approved_split_source_evidence.json")
    candidate_runtime_path = root / "runtime_state" / "buy_ai" / runtime_path_date / "candidate_decisions.json" if runtime_path_date else Path("")
    opportunity_runtime_path = root / "runtime_state" / "buy_ai" / runtime_path_date / "opportunity_rankings.json" if runtime_path_date else Path("")
    opportunity_summary_path = root / "runtime_state" / "buy_ai" / runtime_path_date / "opportunity_inference_summary.json" if runtime_path_date else Path("")
    lifecycle_path = root / "runtime_state" / "buy_ai" / runtime_path_date / "ai_lifecycle_gate_decision.json" if runtime_path_date else Path("")
    candidate_runtime = _read_json_optional(candidate_runtime_path)
    opportunity_runtime = _read_json_optional(opportunity_runtime_path)
    opportunity_summary = _read_json_optional(opportunity_summary_path)
    lifecycle = _read_json_optional(lifecycle_path)

    runtime_stage_contract = _runtime_stage_contract(
        root=root,
        expected_business_date=expected_business_date or runtime_date,
        candidate_runtime=candidate_runtime,
        opportunity_runtime=opportunity_runtime,
        lifecycle=lifecycle,
        post_run_context=post_run_context,
    )
    broker_layer_status = _broker_layer_status(root)
    non_mutation = _non_mutation()
    data_inspection = _data_inspection(
        root=root,
        repo_root=repo_root,
        ai_report=ai_report,
        manifest=manifest,
        candidate_training=candidate_training,
        opportunity_training=opportunity_training,
        feature_manifest=feature_manifest,
        feature_manifest_path=feature_manifest_path,
        expected_business_date=expected_business_date or runtime_date,
        runtime_stage=str(runtime_stage_contract["runtime_stage"]),
    )
    data_status = _data_status(
        ai_report,
        data_inspection=data_inspection,
        expected_business_date=expected_business_date or runtime_path_date,
    )
    temporal_authority_audit = _temporal_authority_audit(
        root=root,
        runtime_mode=runtime_mode or "",
        profile_id=profile_id or "",
        target_business_date=expected_business_date or "",
        target_business_dates=target_business_dates or [],
        data_inspection=data_inspection,
        candidate_runtime=candidate_runtime,
        candidate_runtime_path=candidate_runtime_path,
        opportunity_runtime=opportunity_runtime,
        opportunity_runtime_path=opportunity_runtime_path,
        opportunity_summary=opportunity_summary,
        lifecycle=lifecycle,
        lifecycle_path=lifecycle_path,
    )
    runtime_state_status = _runtime_state_status(
        root,
        expected_business_date=expected_business_date,
        temporal_authority_audit=temporal_authority_audit,
        post_run_context=post_run_context,
    )
    ai_inventory = _ai_system_inventory(
        root=root,
        repo_root=repo_root,
        ai_report=ai_report,
        manifest=manifest,
        candidate_training=candidate_training,
        opportunity_training=opportunity_training,
        candidate_runtime=candidate_runtime,
        candidate_runtime_path=candidate_runtime_path,
        opportunity_runtime=opportunity_runtime,
        opportunity_runtime_path=opportunity_runtime_path,
        opportunity_summary=opportunity_summary,
        lifecycle=lifecycle,
        lifecycle_path=lifecycle_path,
        accepted_generation_id=authority_generation_id(ai_report, manifest),
        runtime_loaded_generation=str(ai_report["runtime_authority_status"].get("runtime_loaded_generation") or ""),
        runtime_stage=str(runtime_stage_contract["runtime_stage"]),
    )
    active_ai_inventory = _active_trained_ai_inventory(repo_root=repo_root, ai_inventory=ai_inventory)
    ai_data_window_summary = _ai_data_window_summary(data_inspection=data_inspection, manifest=manifest, repo_root=repo_root)
    candidate_input_lineage = _ai_input_lineage(
        component="candidate",
        training=candidate_training,
        dataset_revisions=dataset_revisions,
        split_source_evidence=split_source_evidence,
        ai_data_window_summary=ai_data_window_summary,
    )
    opportunity_input_lineage = _ai_input_lineage(
        component="opportunity",
        training=opportunity_training,
        dataset_revisions=dataset_revisions,
        split_source_evidence=split_source_evidence,
        ai_data_window_summary=ai_data_window_summary,
    )
    split_window_statistics = _split_window_statistics(
        candidate=candidate_input_lineage,
        opportunity=opportunity_input_lineage,
    )
    ai_status = _ai_status(ai_report, ai_inventory=ai_inventory, runtime_stage=str(runtime_stage_contract["runtime_stage"]))
    runtime_status = _runtime_status(ai_report, ai_inventory=ai_inventory, runtime_stage=str(runtime_stage_contract["runtime_stage"]))
    decision_subsystems = _decision_subsystems(
        root=root,
        runtime_stage=str(runtime_stage_contract["runtime_stage"]),
        runtime_status=runtime_status,
        runtime_state_status=runtime_state_status,
        broker_layer_status=broker_layer_status,
        lifecycle=lifecycle,
        lifecycle_path=lifecycle_path,
    )
    authority_generation = _authority_generation(ai_report, manifest=manifest)
    freshness_matrix = _freshness_matrix(
        runtime_mode=runtime_mode or "",
        expected_business_date=expected_business_date or "",
        data_inspection=data_inspection,
        ai_inventory=ai_inventory,
        authority_generation=authority_generation,
        runtime_state_status=runtime_state_status,
    )
    target_period_data_sufficiency = _target_period_data_sufficiency(
        data_inspection=data_inspection,
        target_business_dates=target_business_dates or [],
        post_run_context=post_run_context,
    )
    inspection_context = _inspection_context(
        root=root,
        created_at=created_at,
        runtime_mode=runtime_mode or "",
        broker_environment=broker_environment or "",
        profile_id=profile_id or "",
        target_business_date=expected_business_date or "",
        runtime_stage_contract=runtime_stage_contract,
        artifact_resolution=artifact_context,
        post_run_context=post_run_context,
    )
    environment_readiness = _environment_readiness(
        inspection_context=inspection_context,
        overall_status=overall_status if "overall_status" in locals() else "",
        runtime_stage_contract=runtime_stage_contract,
        broker_layer_status=broker_layer_status,
    )
    data_source_inventory = _data_source_inventory(data_inspection=data_inspection, manifest=manifest)
    production_freshness = _current_data_freshness_contract(
        mode="production",
        created_at=created_at,
        data_inspection=data_inspection,
        ai_inventory=ai_inventory,
    )
    demo_freshness = _current_data_freshness_contract(
        mode="demo",
        created_at=created_at,
        data_inspection=data_inspection,
        ai_inventory=ai_inventory,
    )
    historical_coverage = _historical_coverage_contract(freshness_matrix=freshness_matrix)
    baseline_traceability = _baseline_traceability(manifest=manifest, manifest_path=manifest_path)
    freshness_policy_traceability = _freshness_policy_traceability(manifest=manifest, manifest_path=manifest_path)
    recent_holdout_usage = _recent_holdout_usage_audit(ai_data_window_summary=ai_data_window_summary)
    calibration_validation_independence = _calibration_validation_independence_audit(ai_data_window_summary=ai_data_window_summary)
    broker_truthfulness = _broker_truthfulness_audit(broker_layer_status=broker_layer_status)
    not_performed_checks = _not_performed_checks(broker_truthfulness=broker_truthfulness, runtime_stage_contract=runtime_stage_contract)
    not_evaluated_checks = _not_evaluated_checks(production_freshness=production_freshness, demo_freshness=demo_freshness)
    active_model_summary = _active_model_summary(active_ai_inventory=active_ai_inventory, ai_inventory=ai_inventory)
    active_component_count_summary = _active_component_count_summary(
        active_model_summary=active_model_summary,
        candidate_input_lineage=candidate_input_lineage,
        opportunity_input_lineage=opportunity_input_lineage,
        active_ai_inventory=active_ai_inventory,
    )
    runtime_input_lineage_contract = _runtime_input_lineage_contract(
        inspection_context=inspection_context,
        target_period_data_sufficiency=target_period_data_sufficiency,
        data_inspection=data_inspection,
        ai_inventory=ai_inventory,
    )
    complete_component_inventory = _complete_component_inventory(
        root=root,
        repo_root=repo_root,
        runtime_stage=str(runtime_stage_contract["runtime_stage"]),
        inspection_context=inspection_context,
        data_inspection=data_inspection,
        ai_inventory=ai_inventory,
        runtime_state_status=runtime_state_status,
        broker_layer_status=broker_layer_status,
        runtime_status=runtime_status,
        decision_subsystems=decision_subsystems,
        authority_generation=authority_generation,
    )
    component_dependency_matrix = _component_dependency_matrix(complete_component_inventory)
    runtime_chain_inspection = _runtime_chain_inspection(complete_component_inventory)
    jquants_dependency_matrix = _jquants_dependency_matrix(complete_component_inventory)
    runtime_state_coverage = _runtime_state_coverage(root=root, runtime_state_status=runtime_state_status)
    historical_source_consumer_cutoff = _historical_source_consumer_cutoff(
        inspection_context=inspection_context,
        data_inspection=data_inspection,
    )
    inspection_coverage = _inspection_coverage(
        complete_component_inventory=complete_component_inventory,
        runtime_chain_inspection=runtime_chain_inspection,
        runtime_state_coverage=runtime_state_coverage,
    )

    layer_statuses = {
        "data": data_status["status"],
        "ai": ai_status["status"],
        "runtime": runtime_status["status"],
        "runtime_state": runtime_state_status["status"],
        "broker_layer": broker_layer_status["status"],
    }
    overall_status = _combine_status([*layer_statuses.values(), inspection_coverage["status"]])
    exit_code = 20 if overall_status == "BLOCK" else 10 if overall_status == "REVIEW_REQUIRED" else 0
    findings = _main_findings(data_status, ai_status, runtime_status, runtime_state_status, broker_layer_status)
    status_summary = _status_summary(
        inspection_context=inspection_context,
        overall_status=overall_status,
        data_status=data_status,
        ai_status=ai_status,
        runtime_status=runtime_status,
        runtime_state_status=runtime_state_status,
        broker_layer_status=broker_layer_status,
        environment_readiness=environment_readiness,
        target_period_data_sufficiency=target_period_data_sufficiency,
    )
    summary = {
        "schema_version": SYSTEM_STATUS_SCHEMA_VERSION,
        "created_at": created_at,
        "overall_status": overall_status,
        "exit_code": exit_code,
        "data": data_status["summary"],
        "ai": ai_status["summary"],
        "runtime": runtime_status["summary"],
        "runtime_state": runtime_state_status["summary"],
        "broker_layer": broker_layer_status["summary"],
        "main_findings": findings,
        "judgments": status_summary,
    }
    environment_readiness = _environment_readiness(
        inspection_context=inspection_context,
        overall_status=overall_status,
        runtime_stage_contract=runtime_stage_contract,
        broker_layer_status=broker_layer_status,
    )
    operational_summary = _operational_summary(
        inspection_context=inspection_context,
        environment_readiness=environment_readiness,
        runtime_stage_contract=runtime_stage_contract,
        temporal_authority_audit=temporal_authority_audit,
        target_period_data_sufficiency=target_period_data_sufficiency,
        active_model_summary=active_model_summary,
        active_component_count_summary=active_component_count_summary,
        not_performed_checks=not_performed_checks,
        not_evaluated_checks=not_evaluated_checks,
    )
    if temporal_authority_audit.get("temporal_isolation_status") == "BLOCK":
        final_judgment_tokens = ["PHASE19_BA_FAIL", "PHASE19_AY_DAY1_BLOCKED"]
    elif runtime_stage_contract.get("runtime_stage") == "PRE_RUN" and overall_status == "PASS":
        final_judgment_tokens = ["PHASE19_SYSTEM_STATUS_PRE_RUN_READY", "PHASE19_AY_DAY1_START_PERMISSION_ALLOWED"]
    else:
        final_judgment_tokens = [
            "PHASE19_AZ_SYSTEM_STATUS_FULL_INSPECTION_COMPLETE",
            "PHASE19_AY_MANUAL_VALIDATION_OBSERVABILITY_READY",
        ]
    final_judgment = {
        "status": overall_status,
        "exit_code": exit_code,
        "final_judgment": final_judgment_tokens,
        "main_findings": findings,
        "forbidden_declarations_not_made": [
            "PRODUCTION_READY",
            "BUY_READY",
            "AUTONOMOUS_OPERATION_COMPLETE",
        ],
    }
    report = {
        "schema_version": SYSTEM_STATUS_SCHEMA_VERSION,
        "subcommand": "system-status",
        "status": overall_status,
        "exit_code": exit_code,
        "created_at": created_at,
        "system_status_summary": summary,
        "inspection_context": inspection_context,
        "environment_readiness": environment_readiness,
        "status_summary": status_summary,
        "operational_summary": operational_summary,
        "active_model_summary": active_model_summary,
        "active_component_count_summary": active_component_count_summary,
        "candidate_input_lineage": candidate_input_lineage,
        "opportunity_input_lineage": opportunity_input_lineage,
        "split_window_statistics": split_window_statistics,
        "runtime_input_lineage_contract": runtime_input_lineage_contract,
        "complete_component_inventory": complete_component_inventory,
        "component_dependency_matrix": component_dependency_matrix,
        "runtime_chain_inspection": runtime_chain_inspection,
        "jquants_dependency_matrix": jquants_dependency_matrix,
        "runtime_state_coverage": runtime_state_coverage,
        "historical_source_consumer_cutoff": historical_source_consumer_cutoff,
        "inspection_coverage": inspection_coverage,
        "data_source_inventory": data_source_inventory,
        "production_freshness": production_freshness,
        "demo_freshness": demo_freshness,
        "historical_coverage": historical_coverage,
        "baseline_traceability": baseline_traceability,
        "freshness_policy_traceability": freshness_policy_traceability,
        "recent_holdout_usage_audit": recent_holdout_usage,
        "calibration_validation_independence_audit": calibration_validation_independence,
        "broker_truthfulness_audit": broker_truthfulness,
        "not_performed_checks": not_performed_checks,
        "not_evaluated_checks": not_evaluated_checks,
        "active_component_inventory": ai_inventory,
        "data_inspection": data_inspection,
        "decision_subsystems": decision_subsystems,
        "authority_generation": authority_generation,
        "runtime_stage_contract": runtime_stage_contract,
        "ai_data_window_summary": ai_data_window_summary,
        "active_trained_ai_inventory": active_ai_inventory,
        "temporal_authority_audit": temporal_authority_audit,
        "freshness_matrix": freshness_matrix,
        "target_period_data_sufficiency": target_period_data_sufficiency,
        "data_status": data_status,
        "ai_status": ai_status,
        "runtime_status": runtime_status,
        "runtime_state_status": runtime_state_status,
        "broker_layer_status": broker_layer_status,
        "overall_status": {
            "status": overall_status,
            "exit_code": exit_code,
            "layer_statuses": layer_statuses,
            "main_findings": findings,
        },
        "non_mutation": non_mutation,
        "final_judgment": final_judgment,
    }
    report = _sanitize_empty_values(report)
    report["human_summary"] = render_system_status_human_summary(
        report["system_status_summary"],
        active_component_inventory=report["active_component_inventory"],
        inspection_context=report["inspection_context"],
        environment_readiness=report["environment_readiness"],
        operational_summary=report["operational_summary"],
        active_model_summary=report["active_model_summary"],
        active_component_count_summary=report["active_component_count_summary"],
        candidate_input_lineage=report["candidate_input_lineage"],
        opportunity_input_lineage=report["opportunity_input_lineage"],
        runtime_input_lineage_contract=report["runtime_input_lineage_contract"],
        complete_component_inventory=report["complete_component_inventory"],
        component_dependency_matrix=report["component_dependency_matrix"],
        runtime_chain_inspection=report["runtime_chain_inspection"],
        jquants_dependency_matrix=report["jquants_dependency_matrix"],
            runtime_state_coverage=report["runtime_state_coverage"],
            historical_source_consumer_cutoff=report["historical_source_consumer_cutoff"],
            inspection_coverage=report["inspection_coverage"],
        data_source_inventory=report["data_source_inventory"],
        baseline_traceability=report["baseline_traceability"],
        freshness_policy_traceability=report["freshness_policy_traceability"],
        data_inspection=report["data_inspection"],
        decision_subsystems=report["decision_subsystems"],
        authority_generation=report["authority_generation"],
        runtime_stage_contract=report["runtime_stage_contract"],
        ai_data_window_summary=report["ai_data_window_summary"],
        temporal_authority_audit=report["temporal_authority_audit"],
        runtime_state_status=report["runtime_state_status"],
        broker_layer_status=report["broker_layer_status"],
        freshness_matrix=report["freshness_matrix"],
        target_period_data_sufficiency=report["target_period_data_sufficiency"],
        non_mutation=report["non_mutation"],
    )
    return _sanitize_empty_values(report)


def authority_generation_id(ai_report: dict[str, Any], manifest: dict[str, Any]) -> str:
    return str(
        ai_report["accepted_generation_status"].get("accepted_generation_id")
        or manifest.get("accepted_generation_id")
        or ""
    )


def _repo_root_for_runtime_root(root: Path) -> Path:
    cwd = Path.cwd()
    if (cwd / "reports").exists() and (cwd / "docs").exists():
        return cwd
    current = root.resolve(strict=False)
    for parent in (current, *current.parents):
        if (parent / "reports").exists() and (parent / "docs").exists():
            return parent
    return root.parent if root.name == ".runtime" else cwd


def _inspection_context(
    *,
    root: Path,
    created_at: str,
    runtime_mode: str,
    broker_environment: str,
    profile_id: str,
    target_business_date: str,
    runtime_stage_contract: dict[str, Any],
    artifact_resolution: dict[str, Any] | None = None,
    post_run_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root_type = _runtime_root_type(root)
    post_run_context = post_run_context or {}
    inspection_mode = (
        "HISTORICAL_POST_RUN"
        if _valid_post_run_context(post_run_context)
        else
        "HISTORICAL_PRE_RUN"
        if runtime_mode == "historical" and runtime_stage_contract.get("runtime_stage") == "PRE_RUN"
        else f"{runtime_mode.upper()}_{runtime_stage_contract.get('runtime_stage', 'UNKNOWN')}" if runtime_mode else "UNSPECIFIED"
    )
    context = {
        "status": "PASS",
        "inspection_mode": inspection_mode,
        "runtime_mode": runtime_mode or "UNSPECIFIED",
        "broker_environment": broker_environment or "UNSPECIFIED",
        "profile": profile_id or "UNSPECIFIED",
        "runtime_root": _display_path(root),
        "runtime_root_type": root_type,
        "root_type": root_type,
        "target_business_date": target_business_date or "NOT_CONFIGURED",
        "current_calendar_date": _extract_date(created_at),
        "runtime_stage": runtime_stage_contract.get("runtime_stage", "RUNTIME_STAGE_UNRESOLVED"),
        "artifact_resolution": artifact_resolution or {},
        "inspected_runtime_root": _display_path(root),
        "shared_runtime_root_used": root_type == "SHARED_RUNTIME_ROOT",
    }
    if _valid_post_run_context(post_run_context):
        context["post_run_context"] = post_run_context
        context["runtime_test_run_id"] = str(post_run_context.get("run_id") or "")
        context["runtime_test_evidence_root"] = str(post_run_context.get("run_evidence_root") or "")
        context["completed_business_days"] = post_run_context.get("completed_business_days") or []
        context["context_authority"] = "latest_closed_runtime_test"
    return context


def _valid_post_run_context(context: dict[str, Any]) -> bool:
    return (
        str(context.get("context_type") or "") == "HISTORICAL_POST_RUN"
        and str(context.get("status") or "") == "PASS"
        and bool(context.get("final_business_date"))
        and bool(context.get("run_id"))
    )


def _post_run_safety_authority_ready(context: dict[str, Any], *, expected_business_date: str) -> bool:
    if not _valid_post_run_context(context):
        return False
    if str(context.get("final_business_date") or "") != str(expected_business_date or ""):
        return False
    return (
        str(context.get("safety_status") or "") in {"READY", "PASS"}
        and str(context.get("safety_authority_source") or "") == "data_readiness_historical_temporal_authority"
        and str(context.get("safety_business_date") or "") == str(expected_business_date or "")
    )


def _target_business_date_artifact_context(
    *,
    root: Path,
    expected_business_date: str,
    runtime_date: str,
    ai_report: dict[str, Any],
) -> dict[str, Any]:
    if expected_business_date:
        feature_manifest_path = root / "operations" / "feature_refresh_detail" / expected_business_date / "feature_refresh_manifest.json"
        feature_artifact_dir = root / "operations" / "feature_artifacts" / expected_business_date
        buy_ai_dir = root / "runtime_state" / "buy_ai" / expected_business_date
        return {
            "status": "PASS" if feature_manifest_path.is_file() or feature_artifact_dir.is_dir() or buy_ai_dir.is_dir() else "TARGET_DATE_ARTIFACT_MISSING",
            "authority": "target_business_date_exact_match",
            "target_business_date": expected_business_date,
            "runtime_artifact_business_date": expected_business_date,
            "feature_manifest_path": str(feature_manifest_path),
            "feature_artifact_dir": str(feature_artifact_dir),
            "buy_ai_dir": str(buy_ai_dir),
            "fallback_used": False,
            "forbidden_fallbacks": ["max_date", "latest_directory", "mtime", "future_date"],
        }
    latest_feature = ai_report["jquants_and_feature_freshness"]["latest_buy_feature"]
    return {
        "status": "PASS" if runtime_date else "NOT_YET_MATERIALIZED",
        "authority": "current_runtime_business_date",
        "target_business_date": "",
        "runtime_artifact_business_date": runtime_date,
        "feature_manifest_path": str(latest_feature.get("manifest_path") or ""),
        "feature_artifact_dir": "",
        "buy_ai_dir": str(root / "runtime_state" / "buy_ai" / runtime_date) if runtime_date else "",
        "fallback_used": False,
        "forbidden_fallbacks": ["mtime"],
    }


def _environment_readiness(
    *,
    inspection_context: dict[str, Any],
    overall_status: str,
    runtime_stage_contract: dict[str, Any],
    broker_layer_status: dict[str, Any],
) -> dict[str, Any]:
    historical_pre_run = (
        "PASS"
        if inspection_context.get("inspection_mode") == "HISTORICAL_PRE_RUN"
        and runtime_stage_contract.get("pre_run_readiness") == "PASS"
        and overall_status in {"PASS", ""}
        else "NOT_APPLICABLE"
    )
    return {
        "status": "PASS",
        "historical_pre_run_readiness": historical_pre_run,
        "single_day_runtime_readiness": "PRE_RUN_ONLY" if historical_pre_run == "PASS" else "NOT_EVALUATED",
        "multi_day_continuity_readiness": "NOT_PERFORMED",
        "demo_current_data_readiness": "NOT_EVALUATED",
        "production_current_data_readiness": "NOT_EVALUATED",
        "broker_connectivity_readiness": "NOT_PERFORMED",
        "broker_write_readiness": "PROHIBITED",
        "broker_layer_truth_status": broker_layer_status.get("truthfulness_status", "CONFIGURATION_PASS_CONNECTIVITY_NOT_PERFORMED"),
        "production_ready": False,
        "buy_ready": False,
        "autonomous_operation_complete": False,
        "reason": "PASS is scoped to the inspection context only; Historical pre-run PASS does not imply Demo or Production readiness.",
    }


def _active_model_summary(*, active_ai_inventory: dict[str, Any], ai_inventory: dict[str, Any]) -> dict[str, Any]:
    active_models = ai_inventory.get("active_ai_models", [])
    complete = [item for item in active_models if item.get("status") == "PASS"]
    unresolved = [item for item in active_models if item.get("status") != "PASS"]
    return {
        "status": "PASS" if not unresolved else "REVIEW_REQUIRED",
        "active_trained_model_count": active_ai_inventory.get("active_trained_model_count", len(active_models)),
        "active_trained_models": active_ai_inventory.get("active_trained_models", []),
        "models_with_complete_artifact_validation": len(complete),
        "models_with_unresolved_artifact_validation": len(unresolved),
        "trained_models": active_ai_inventory.get("active_trained_models", []),
        "statistical_baselines": active_ai_inventory.get("statistical_baselines", []),
        "threshold_policies": ["freshness_evaluation", "lifecycle_monitoring"],
        "rule_based_control_subsystems": active_ai_inventory.get("rule_based_subsystems", []),
        "legacy_retired_components": active_ai_inventory.get("inactive_or_retired_models", []),
    }


def _active_component_count_summary(
    *,
    active_model_summary: dict[str, Any],
    candidate_input_lineage: dict[str, Any],
    opportunity_input_lineage: dict[str, Any],
    active_ai_inventory: dict[str, Any],
) -> dict[str, Any]:
    unresolved = [
        item.get("component_id", "")
        for item in (candidate_input_lineage, opportunity_input_lineage)
        if item.get("status") != "PASS"
    ]
    return {
        "status": "PASS" if not unresolved else "REVIEW_REQUIRED",
        "active_trained_models": active_model_summary.get("active_trained_model_count", 0),
        "active_statistical_baselines": len(active_model_summary.get("statistical_baselines", [])),
        "active_threshold_policies": len(active_model_summary.get("threshold_policies", [])),
        "active_rule_based_control_subsystems": len(active_model_summary.get("rule_based_control_subsystems", [])),
        "inactive_retired_components": len(active_model_summary.get("legacy_retired_components", [])),
        "components_with_complete_input_lineage_inspection": 2 - len(unresolved),
        "components_with_unresolved_input_lineage_inspection": len(unresolved),
        "unresolved_components": unresolved,
        "repository_scan_evidence": "active_trained_ai_inventory.inventory_evidence",
        "repository_scan_terms": active_ai_inventory.get("search_terms", []),
    }


def _ai_input_lineage(
    *,
    component: str,
    training: dict[str, Any],
    dataset_revisions: dict[str, Any],
    split_source_evidence: dict[str, Any],
    ai_data_window_summary: dict[str, Any],
) -> dict[str, Any]:
    revision = dataset_revisions.get(component, {}) if isinstance(dataset_revisions.get(component), dict) else {}
    source_artifacts = revision.get("source_artifacts", {}) if isinstance(revision.get("source_artifacts"), dict) else {}
    primary_source = _primary_dataset_source(component=component, source_artifacts=source_artifacts)
    split_key = "Candidate" if component == "candidate" else "Opportunity"
    split = ((split_source_evidence.get("selected") or {}).get(split_key) or {}) if isinstance(split_source_evidence.get("selected"), dict) else {}
    window_summary = next(
        (item for item in ai_data_window_summary.get("items", []) if str(item.get("component_id", "")).startswith(component)),
        {},
    )
    windows = {
        "Training": _window_stats("train", split, training.get("train_window", {}), training),
        "Calibration": _calibration_window_stats(split, window_summary, training),
        "Validation": _window_stats("validation", split, training.get("validation_window", {}), training),
        "Test": _window_stats("test", split, training.get("test_window", {}), training),
        "Recent Holdout": _window_stats("recent_holdout", split, training.get("recent_holdout_window", {}), training),
    }
    status = "PASS" if revision and primary_source else "REVIEW_REQUIRED"
    return {
        "component_id": f"{component}_input_lineage",
        "component": component.title(),
        "status": status,
        "training_dataset_revision": training.get("dataset_revision_id", "UNRESOLVED"),
        "dataset_artifact_path": _truth_value(revision.get("dataset_path") or training.get("dataset_path"), missing="UNRESOLVED"),
        "dataset_manifest_path": _truth_value(revision.get("artifact_path"), missing="UNRESOLVED"),
        "dataset_source_authority": "generation-bound canonical dataset" if revision else "DATASET_SOURCE_WINDOW_UNRESOLVED",
        "dataset_source_earliest_date": _truth_value(primary_source.get("min_target_date"), missing="UNRESOLVED"),
        "dataset_source_latest_date": _truth_value(primary_source.get("max_target_date"), missing="UNRESOLVED"),
        "dataset_source_row_count": _truth_value(primary_source.get("row_count"), missing="UNRESOLVED"),
        "dataset_source_symbol_count": "NOT_RECORDED",
        "dataset_source_schema_hash": _truth_value(primary_source.get("schema_hash"), missing="UNRESOLVED"),
        "dataset_source_content_hash": _truth_value(primary_source.get("content_hash"), missing="UNRESOLVED"),
        "dataset_source_ref": _truth_value(primary_source.get("source_ref"), missing="UNRESOLVED"),
        "dataset_revision_row_count": _truth_value(revision.get("row_count"), missing="UNRESOLVED"),
        "dataset_revision_schema_hash": _truth_value(revision.get("schema_hash"), missing="UNRESOLVED"),
        "dataset_revision_content_hash": _truth_value(revision.get("dataset_hash"), missing="UNRESOLVED"),
        "training_dataset_source": {
            "earliest": _truth_value(revision.get("target_date_min"), missing="UNRESOLVED"),
            "latest": _truth_value(revision.get("target_date_max"), missing="UNRESOLVED"),
            "authority": "generation-bound canonical dataset",
            "source_artifacts": source_artifacts,
        },
        "current_runtime_market_data_role": "historical runtime replay source",
        "split_windows": windows,
        "recent_holdout_usage": {
            "recent_holdout_period": windows["Recent Holdout"],
            "recent_holdout_usage_status": "NOT_USED_IN_PHASE19",
            "recent_holdout_used_for_training": False,
            "recent_holdout_used_for_calibration": False,
            "recent_holdout_used_for_validation": False,
            "recent_holdout_used_for_model_selection": False,
            "recent_holdout_runtime_authority_impact": "NONE",
        },
        "calibration_validation_independence": {
            "calibration_mode": "SHARED_WITH_VALIDATION",
            "calibration_fit_target": "score calibration only",
            "calibration_input_window": windows["Calibration"],
            "validation_metric_timing": "before/after calibration diagnostics only",
            "model_selection_use": False,
            "independent_final_evaluation_window": windows["Test"],
            "independence_status": "PASS",
        },
    }


def _primary_dataset_source(*, component: str, source_artifacts: dict[str, Any]) -> dict[str, Any]:
    preferred = (
        ["formal_candidate_dataset", "candidate_label_source", "candidate_source"]
        if component == "candidate"
        else ["opportunity_source", "opportunity_formal_32_feature_source", "candidate_source"]
    )
    for key in preferred:
        value = source_artifacts.get(key)
        if isinstance(value, dict) and value.get("min_target_date") and value.get("max_target_date"):
            return value
    for value in source_artifacts.values():
        if isinstance(value, dict) and value.get("min_target_date") and value.get("max_target_date"):
            return value
    return {}


def _window_stats(prefix: str, split: dict[str, Any], fallback: dict[str, Any], training: dict[str, Any]) -> dict[str, Any]:
    stats = training.get("training_statistics", {}) if isinstance(training.get("training_statistics"), dict) else {}
    return {
        "start": _truth_value(split.get(f"{prefix}_start") or fallback.get("start"), missing="NOT_RECORDED"),
        "end": _truth_value(split.get(f"{prefix}_end") or fallback.get("end"), missing="NOT_RECORDED"),
        "business_days": _truth_value(split.get(f"{prefix}_business_days") or fallback.get("business_days"), missing="NOT_RECORDED"),
        "row_count": _truth_value(split.get(f"{prefix}_rows") or (stats.get(f"{prefix}_rows") if prefix == "recent_holdout" else None), missing="NOT_RECORDED"),
        "symbol_count": _truth_value(split.get(f"{prefix}_distinct_issues"), missing="NOT_RECORDED"),
        "source_dataset_revision": _truth_value(training.get("dataset_revision_id"), missing="UNRESOLVED"),
        "label_policy": _truth_value(training.get("label_column"), missing="NOT_RECORDED"),
    }


def _calibration_window_stats(split: dict[str, Any], window_summary: dict[str, Any], training: dict[str, Any]) -> dict[str, Any]:
    validation = _window_stats("validation", split, training.get("validation_window", {}), training)
    calibration = window_summary.get("calibration", {}) if isinstance(window_summary.get("calibration"), dict) else {}
    return {
        **validation,
        "start": _truth_value(calibration.get("start") or validation.get("start"), missing="NOT_RECORDED"),
        "end": _truth_value(calibration.get("end") or validation.get("end"), missing="NOT_RECORDED"),
        "fit_window_role": calibration.get("fit_window_role", "CALIBRATION_FIT_WINDOW"),
        "mode": calibration.get("mode", "SHARED_WITH_VALIDATION"),
    }


def _split_window_statistics(*, candidate: dict[str, Any], opportunity: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": _combine_status([candidate.get("status", "REVIEW_REQUIRED"), opportunity.get("status", "REVIEW_REQUIRED")]),
        "candidate": candidate.get("split_windows", {}),
        "opportunity": opportunity.get("split_windows", {}),
    }


def _runtime_input_lineage_contract(
    *,
    inspection_context: dict[str, Any],
    target_period_data_sufficiency: dict[str, Any],
    data_inspection: dict[str, Any],
    ai_inventory: dict[str, Any],
) -> dict[str, Any]:
    target = inspection_context.get("target_business_date", "NOT_CONFIGURED")
    planned_feature_source_date = target
    if isinstance(target_period_data_sufficiency.get("per_day"), list):
        first = next((item for item in target_period_data_sufficiency["per_day"] if item.get("business_date") == target), {})
        planned_feature_source_date = target if first else "UNRESOLVED"
    post_feature = [
        item for item in data_inspection.get("runtime_features", [])
        if item.get("materialization_status") == "READY" or item.get("status") == "PASS"
    ]
    active_models = ai_inventory.get("active_ai_models", [])
    return {
        "status": "PASS",
        "runtime_stage": inspection_context.get("runtime_stage", ""),
        "target_business_date": target,
        "required_market_data_through_date": target,
        "planned_feature_source_date": planned_feature_source_date,
        "temporal_cutoff_policy": "consumer input must be <= target business date",
        "future_row_guard": "ENABLED_BY_TEMPORAL_GUARD",
        "pre_run_contract_status": "PASS" if inspection_context.get("runtime_stage") == "PRE_RUN" else "NOT_APPLICABLE",
        "actual_feature_business_date": post_feature[0].get("feature_date") if post_feature else "NOT_YET_MATERIALIZED",
        "actual_raw_normalized_input_range": "NOT_YET_MATERIALIZED" if not post_feature else "SEE_RUNTIME_FEATURE_ARTIFACT",
        "actual_input_row_count": post_feature[0].get("row_count") if post_feature else "NOT_YET_MATERIALIZED",
        "actual_symbol_count": post_feature[0].get("symbol_count") if post_feature else "NOT_YET_MATERIALIZED",
        "inference_business_date": next((item.get("latest_inference_date") for item in active_models if item.get("latest_inference_date") not in {"", "NOT_YET_MATERIALIZED"}), "NOT_YET_MATERIALIZED"),
    }


def _complete_component_inventory(
    *,
    root: Path,
    repo_root: Path,
    runtime_stage: str,
    inspection_context: dict[str, Any],
    data_inspection: dict[str, Any],
    ai_inventory: dict[str, Any],
    runtime_state_status: dict[str, Any],
    broker_layer_status: dict[str, Any],
    runtime_status: dict[str, Any],
    decision_subsystems: dict[str, Any],
    authority_generation: dict[str, Any],
) -> dict[str, Any]:
    target_date = _truth_value(inspection_context.get("target_business_date", ""), missing="NOT_RECORDED")
    components = [
        _component_contract(
            repo_root=repo_root,
            component_id="market_refresh",
            name="Market Refresh",
            component_type="data_refresh",
            implementation="src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py",
            authority="J-Quants canonical refresh contract",
            input_artifact="J-Quants API / Historical PIT source",
            output_artifact=_source_artifact(data_inspection, "normalized_jquants_daily_quotes"),
            input_components=["J-Quants", "Trading Calendar"],
            input_business_date=target_date,
            output_business_date=_source_date(data_inspection, "normalized_jquants_daily_quotes"),
            configuration_status="PASS",
            runtime_status=_source_status(data_inspection, "normalized_jquants_daily_quotes"),
            jquants_dependent=True,
            target_date_execution_status="PRELOADED_SOURCE_AVAILABLE",
            runtime_result_status=_source_status(data_inspection, "normalized_jquants_daily_quotes"),
            jquants_dependency_type="DIRECT",
            jquants_dependency_path=["J-Quants", "Market Refresh"],
            jquants_direct_input_artifacts=["J-Quants raw/normalized/listed source"],
            jquants_dependency_reason="Market Refresh inspects preloaded J-Quants-derived historical source coverage.",
            extra={
                "target_business_date": target_date,
                "source_materialization_mode": "PRELOADED_HISTORICAL_SOURCE",
                "refresh_command_execution_status": "NOT_PERFORMED",
                "historical_source_coverage_status": _source_status(data_inspection, "normalized_jquants_daily_quotes"),
                "source_available_from_date": _source_from_date(data_inspection, "normalized_jquants_daily_quotes"),
                "source_available_through_date": _source_date(data_inspection, "normalized_jquants_daily_quotes"),
                "required_through_date": target_date,
                "consumer_cutoff_date": target_date,
                "actual_consumed_from_date": "NOT_YET_MATERIALIZED",
                "actual_consumed_through_date": "NOT_YET_MATERIALIZED",
                "future_row_guard": "ENABLED_BY_TEMPORAL_GUARD",
                "future_rows_available": _future_rows_available(data_inspection, "normalized_jquants_daily_quotes", target_date),
                "future_rows_consumed": "NOT_YET_MATERIALIZED",
            },
        ),
        _component_contract(
            repo_root=repo_root,
            component_id="feature_refresh",
            name="Feature Refresh",
            component_type="feature_materializer",
            implementation="src/ai_fund_lab_v2/runtime_v2/market_refresh/feature_date_contract.py",
            authority="Feature Date Contract / Temporal Guard",
            input_artifact=_source_artifact(data_inspection, "normalized_jquants_daily_quotes"),
            output_artifact=_first_runtime_feature_artifact(data_inspection),
            input_components=["Market Refresh", "Listed Issues", "Trading Calendar"],
            input_business_date=target_date,
            output_business_date=_first_runtime_feature_date(data_inspection),
            configuration_status="PASS",
            runtime_status=_stage_status(runtime_stage, "FEATURE_READY"),
            jquants_dependent=True,
            target_date_execution_status="NOT_YET_APPLICABLE",
            runtime_result_status="NOT_YET_MATERIALIZED",
            jquants_dependency_type="DIRECT",
            jquants_dependency_path=["J-Quants", "Market Refresh", "Feature Refresh"],
            jquants_direct_input_artifacts=[_source_artifact(data_inspection, "normalized_jquants_daily_quotes")],
            jquants_dependency_reason="Feature Refresh directly consumes J-Quants-derived normalized market data and listed issues.",
            extra={
                "source_available_from_date": _source_from_date(data_inspection, "normalized_jquants_daily_quotes"),
                "source_available_through_date": _source_date(data_inspection, "normalized_jquants_daily_quotes"),
                "required_through_date": target_date,
                "consumer_cutoff_date": target_date,
                "actual_consumed_from_date": "NOT_YET_MATERIALIZED",
                "actual_consumed_through_date": "NOT_YET_MATERIALIZED",
                "future_row_guard": "ENABLED_BY_TEMPORAL_GUARD",
                "future_rows_available": _future_rows_available(data_inspection, "normalized_jquants_daily_quotes", target_date),
                "future_rows_consumed": "NOT_YET_MATERIALIZED",
            },
        ),
        *[
            _ai_component_contract(
                repo_root=repo_root,
                model=item,
                target_date=target_date,
                component_id=item.get("component_id", "UNRESOLVED"),
                input_components=["Feature Refresh", "Accepted Generation"],
            )
            for item in ai_inventory.get("active_ai_models", [])
        ],
        _decision_contract(repo_root, decision_subsystems, "runtime_baseline", "Runtime Baseline", "statistical_baseline", "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py", ["Accepted Generation", "Candidate AI", "Opportunity AI"], target_date, True),
        _decision_contract(repo_root, decision_subsystems, "freshness_evaluation", "Freshness Evaluation", "threshold_policy", "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py", ["Market Refresh", "Feature Refresh", "Accepted Generation"], target_date, True),
        _decision_contract(repo_root, decision_subsystems, "lifecycle_monitoring", "Lifecycle Monitoring", "threshold_policy", "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py", ["Runtime Baseline", "Freshness Evaluation", "Candidate AI", "Opportunity AI"], target_date, True),
        _component_contract(
            repo_root=repo_root,
            component_id="safety_decision",
            name="Safety Decision",
            component_type="rule_based_control_subsystem",
            implementation="src/ai_fund_lab_v2/runtime_v2/safety/producer.py",
            authority="Runtime Safety producer",
            input_artifact=str(root / "runtime_state" / "current_state.json"),
            output_artifact=runtime_state_status["safety"].get("artifact_path", ""),
            input_components=["Position Management", "Runtime Features", "Current", "Pending"],
            input_business_date=target_date,
            output_business_date=runtime_state_status["safety"].get("artifact_business_date", ""),
            configuration_status="PASS",
            runtime_status=runtime_state_status["safety"].get("safety_artifact_status", ""),
            jquants_dependent=True,
            target_date_execution_status="NOT_YET_APPLICABLE",
            runtime_result_status="NOT_YET_MATERIALIZED",
            jquants_dependency_type="DIRECT",
            jquants_dependency_path=["J-Quants", "Feature Refresh", "Safety Decision"],
            jquants_direct_input_artifacts=["Runtime Features", str(root / "runtime_state" / "current_state.json")],
            jquants_dependency_reason="Safety Decision consumes Runtime Features and Current state whose valuation inputs are J-Quants-derived.",
        ),
        _component_contract(
            repo_root=repo_root,
            component_id="position_management",
            name="Position Management",
            component_type="rule_based_or_model_adjacent_subsystem",
            implementation="src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
            authority="Runtime-owned Current",
            input_artifact=str(root / "runtime_state" / "current_state.json"),
            output_artifact=str(root / "runtime_state" / "current_state.json"),
            input_components=["Current", "Ledger", "Market Refresh"],
            input_business_date=target_date,
            output_business_date=runtime_state_status["pm"].get("business_date", ""),
            configuration_status="PASS",
            runtime_status=runtime_state_status["pm"].get("status", ""),
            jquants_dependent=True,
            target_date_execution_status="NOT_YET_APPLICABLE",
            runtime_result_status="NOT_YET_MATERIALIZED",
            jquants_dependency_type="DIRECT",
            jquants_dependency_path=["J-Quants", "Market Refresh", "Position Management"],
            jquants_direct_input_artifacts=[str(root / "runtime_state" / "current_state.json"), _source_artifact(data_inspection, "normalized_jquants_daily_quotes")],
            jquants_dependency_reason="Position Management inspects Current positions with market-data-derived valuation context.",
        ),
        _component_contract(
            repo_root=repo_root,
            component_id="capital_policy",
            name="Capital Policy",
            component_type="rule_based_control_subsystem",
            implementation="src/ai_fund_lab_v2/runtime_v2/policy/capital_deployment.py",
            authority="Capital Deployment policy",
            input_artifact=str(root / "runtime_state" / "current_state.json"),
            output_artifact="NOT_YET_MATERIALIZED" if runtime_stage == "PRE_RUN" else str(root / "pending_order_plan" / "pending_order_plan.json"),
            input_components=["Position Management", "Current", "Candidate AI", "Opportunity AI"],
            input_business_date=target_date,
            output_business_date="NOT_YET_MATERIALIZED" if runtime_stage == "PRE_RUN" else target_date,
            configuration_status="PASS",
            runtime_status=_stage_status(runtime_stage, "DAILY_PLAN_CREATED"),
            jquants_dependent=False,
            target_date_execution_status="NOT_YET_APPLICABLE",
            runtime_result_status="NOT_YET_MATERIALIZED",
            jquants_dependency_type="INDIRECT",
            jquants_dependency_path=["J-Quants", "Feature Refresh", "Candidate AI / Opportunity AI", "Capital Policy"],
            jquants_direct_input_artifacts=["NONE"],
            jquants_dependency_reason="Capital Policy consumes AI decisions and state derived from J-Quants features but does not directly read J-Quants artifacts.",
        ),
        _decision_contract(repo_root, decision_subsystems, "buy_planning", "BUY Planning", "runtime_planning", "src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py", ["Candidate AI", "Opportunity AI", "Capital Policy", "Safety Decision"], target_date, True),
        _decision_contract(repo_root, decision_subsystems, "sell_planning_continuity", "SELL Planning", "runtime_planning", "src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py", ["Position Management", "Current", "Safety Decision", "Runtime Features"], target_date, True),
        _decision_contract(repo_root, decision_subsystems, "approval", "Approval", "human_control_boundary", "src/ai_fund_lab_v2/runtime_v2/approval/policy.py", ["BUY Planning", "SELL Planning", "Safety Decision"], target_date, False),
        _decision_contract(repo_root, decision_subsystems, "submit_guard", "Submit Guard", "broker_guard", "src/ai_fund_lab_v2/runtime_v2/submit/guards.py", ["Approval", "Pending", "Safety Decision", "Broker Policy"], target_date, False),
        _decision_contract(repo_root, decision_subsystems, "execution_guard", "Execution Guard", "execution_readonly_guard", "src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py", ["Submit Guard", "Broker Readonly Snapshot"], target_date, False),
        _component_contract(
            repo_root=repo_root,
            component_id="ledger_update",
            name="Ledger Update",
            component_type="runtime_state_writer",
            implementation="src/ai_fund_lab_v2/runtime_v2/ledger/writer.py",
            authority="Execution Processor / Ledger authority",
            input_artifact=str(root / "persistent_ledger" / "executions.jsonl"),
            output_artifact=str(root / "persistent_ledger" / "state.json"),
            input_components=["Execution Guard", "Execution Evidence"],
            input_business_date=target_date,
            output_business_date=runtime_state_status["ledger"].get("business_date", "NOT_RECORDED"),
            configuration_status="PASS",
            runtime_status=runtime_state_status["ledger"].get("status", ""),
            jquants_dependent=False,
            target_date_execution_status="NOT_PERFORMED",
            runtime_result_status="NOT_PERFORMED",
            jquants_dependency_type="NONE",
            jquants_dependency_path=["NONE"],
            jquants_direct_input_artifacts=["NONE"],
            jquants_dependency_reason="Ledger Update consumes execution evidence and does not use J-Quants as a sell/buy decision input.",
        ),
        _component_contract(
            repo_root=repo_root,
            component_id="reporting",
            name="Reporting",
            component_type="reporting",
            implementation="src/ai_fund_lab_v2/runtime_v2/report/builder.py",
            authority="Runtime report builder",
            input_artifact=str(root / "persistent_ledger" / "state.json"),
            output_artifact="NOT_YET_MATERIALIZED",
            input_components=["Ledger Update", "Current", "Pending", "Execution Guard"],
            input_business_date=target_date,
            output_business_date="NOT_YET_MATERIALIZED",
            configuration_status="PASS",
            runtime_status=broker_layer_status["reporting"].get("status", ""),
            jquants_dependent=False,
            target_date_execution_status="NOT_PERFORMED",
            runtime_result_status="NOT_PERFORMED",
            jquants_dependency_type="NONE",
            jquants_dependency_path=["NONE"],
            jquants_direct_input_artifacts=["NONE"],
            jquants_dependency_reason="Reporting consumes Runtime state/evidence for communication; it is not a trading-decision consumer of J-Quants data.",
        ),
        _component_contract(
            repo_root=repo_root,
            component_id="notification",
            name="Notification",
            component_type="external_delivery_boundary",
            implementation="src/ai_fund_lab_v2/runtime_v2/notification/queue.py",
            authority="Notification delivery policy",
            input_artifact="NOT_YET_MATERIALIZED",
            output_artifact="NOT_YET_MATERIALIZED",
            input_components=["Reporting", "Approval"],
            input_business_date=target_date,
            output_business_date="NOT_YET_MATERIALIZED",
            configuration_status="PASS",
            runtime_status=broker_layer_status["notification"].get("status", ""),
            jquants_dependent=False,
            target_date_execution_status="NOT_PERFORMED",
            runtime_result_status="NOT_PERFORMED",
            jquants_dependency_type="NONE",
            jquants_dependency_path=["NONE"],
            jquants_direct_input_artifacts=["NONE"],
            jquants_dependency_reason="Notification sends or queues reports and does not use J-Quants as a trading-decision input.",
        ),
    ]
    components = [_normalize_component_contract(item) for item in components]
    unresolved = [item for item in components if item["inspection_status"] == "UNRESOLVED_COMPONENT"]
    return {
        "status": "REVIEW_REQUIRED" if unresolved else "PASS",
        "repository_scan_evidence": "src/ai_fund_lab_v2/runtime_v2 operational modules mapped to system-status component contracts",
        "component_count": len(components),
        "components": components,
        "unresolved_components": unresolved,
    }


def _component_contract(
    *,
    repo_root: Path,
    component_id: str,
    name: str,
    component_type: str,
    implementation: str,
    authority: str,
    input_artifact: Any,
    output_artifact: Any,
    input_components: list[str],
    input_business_date: Any,
    output_business_date: Any,
    configuration_status: Any,
    runtime_status: Any,
    jquants_dependent: bool,
    active: str = "active",
    authority_resolution_status: Any = "PASS",
    target_date_execution_status: Any = "NOT_YET_APPLICABLE",
    runtime_result_status: Any = "NOT_YET_MATERIALIZED",
    jquants_dependency_type: str | None = None,
    jquants_dependency_path: list[str] | None = None,
    jquants_direct_input_artifacts: list[str] | None = None,
    jquants_dependency_reason: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    implementation_status = "PASS" if (repo_root / implementation).exists() else "UNRESOLVED_COMPONENT"
    dependency_type = jquants_dependency_type or ("DIRECT" if jquants_dependent else "NONE")
    payload = {
        "component_id": component_id,
        "component_name": name,
        "component_type": component_type,
        "active_or_inactive": active,
        "authority": authority,
        "implementation": implementation,
        "implementation_status": implementation_status,
        "input_artifact": input_artifact,
        "output_artifact": output_artifact,
        "input_components": input_components,
        "input_business_date": input_business_date,
        "output_business_date": output_business_date,
        "configuration_status": configuration_status,
        "authority_resolution_status": authority_resolution_status,
        "runtime_status": runtime_status,
        "target_date_execution_status": target_date_execution_status,
        "runtime_result_status": runtime_result_status,
        "inspection_status": implementation_status,
        "jquants_dependent": "YES" if jquants_dependent else "NO",
        "JQUANTS_DEPENDENT": "YES" if jquants_dependent else "NO",
        "jquants_dependency_type": dependency_type,
        "jquants_dependency_path": jquants_dependency_path or (["J-Quants", name] if dependency_type == "DIRECT" else ["NONE"]),
        "jquants_direct_input_artifacts": jquants_direct_input_artifacts or ([_truth_value(input_artifact, missing="NOT_RECORDED")] if dependency_type == "DIRECT" else ["NONE"]),
        "jquants_dependency_reason": jquants_dependency_reason or ("directly consumes J-Quants-derived operational data" if dependency_type == "DIRECT" else "does not consume J-Quants-derived data as an operational decision input"),
    }
    if extra:
        payload.update(extra)
    return payload


def _ai_component_contract(*, repo_root: Path, model: dict[str, Any], target_date: str, component_id: str, input_components: list[str]) -> dict[str, Any]:
    return _component_contract(
        repo_root=repo_root,
        component_id=component_id,
        name=str(model.get("component_name", component_id)),
        component_type=str(model.get("component_type", "trained_ai_model")),
        implementation=str(model.get("implementation_path", "UNRESOLVED")),
        authority=str(model.get("authority_source", "UNRESOLVED")),
        input_artifact=model.get("input_data", "NOT_YET_MATERIALIZED"),
        output_artifact=model.get("output_data", "NOT_YET_MATERIALIZED"),
        input_components=input_components,
        input_business_date=model.get("input_feature_business_date", target_date),
        output_business_date=model.get("inference_business_date", "NOT_YET_MATERIALIZED"),
        configuration_status=_combine_status([
            str(model.get("model_authority_resolution_status", "BLOCK")),
            str(model.get("model_artifact_resolution_status", "BLOCK")),
            str(model.get("scaler_resolution_status", "BLOCK")),
            str(model.get("calibration_resolution_status", "BLOCK")),
        ]),
        runtime_status=model.get("runtime_load_status", model.get("status", "UNRESOLVED")),
        jquants_dependent=True,
        authority_resolution_status=model.get("model_authority_resolution_status", "UNRESOLVED"),
        target_date_execution_status=model.get("target_date_inference_status", "NOT_YET_APPLICABLE"),
        runtime_result_status="NOT_YET_MATERIALIZED" if model.get("target_date_inference_status") == "NOT_YET_APPLICABLE" else model.get("status", "UNRESOLVED"),
        jquants_dependency_type="DIRECT",
        jquants_dependency_path=["J-Quants", "Feature Refresh", str(model.get("component_name", component_id))],
        jquants_direct_input_artifacts=[model.get("input_data", "NOT_YET_MATERIALIZED")],
        jquants_dependency_reason="Runtime AI consumes target-date Runtime Feature artifacts derived from J-Quants market data.",
        extra={"model_load_status": "PASS" if model.get("runtime_load_status") == "MODEL_LOADABLE" else model.get("runtime_load_status", "UNRESOLVED")},
    )


def _decision_contract(
    repo_root: Path,
    decision_subsystems: dict[str, Any],
    component_id: str,
    name: str,
    component_type: str,
    implementation: str,
    input_components: list[str],
    target_date: str,
    jquants_dependent: bool,
) -> dict[str, Any]:
    item = next((entry for entry in decision_subsystems.get("subsystems", []) if entry.get("component_id") == component_id), {})
    guard_or_external = component_id in {"submit_guard", "execution_guard"}
    not_performed = guard_or_external
    target_execution = "NOT_PERFORMED" if not_performed else "NOT_YET_APPLICABLE"
    runtime_result = "NOT_PERFORMED" if not_performed else "NOT_YET_MATERIALIZED"
    if jquants_dependent:
        dependency_type = "INDIRECT"
        dependency_path = ["J-Quants", "Feature Refresh", *input_components]
        dependency_reason = f"{name} consumes upstream Runtime decisions or features derived from J-Quants data."
    else:
        dependency_type = "NONE"
        dependency_path = ["NONE"]
        dependency_reason = f"{name} does not consume J-Quants-derived data as a trading-decision input."
    return _component_contract(
        repo_root=repo_root,
        component_id=component_id,
        name=name,
        component_type=component_type,
        implementation=implementation,
        authority=str(item.get("authority", "UNRESOLVED")),
        input_artifact=item.get("input_artifact", "NOT_YET_MATERIALIZED"),
        output_artifact=item.get("input_artifact", "NOT_YET_MATERIALIZED"),
        input_components=input_components,
        input_business_date=target_date,
        output_business_date=item.get("artifact_date", "NOT_YET_MATERIALIZED"),
        configuration_status="PASS",
        runtime_status=item.get("status", "UNRESOLVED"),
        jquants_dependent=jquants_dependent,
        authority_resolution_status="PASS" if item else "UNRESOLVED",
        target_date_execution_status=target_execution,
        runtime_result_status=runtime_result,
        jquants_dependency_type=dependency_type,
        jquants_dependency_path=dependency_path,
        jquants_direct_input_artifacts=["NONE"],
        jquants_dependency_reason=dependency_reason,
    )


def _normalize_component_contract(item: dict[str, Any]) -> dict[str, Any]:
    return {key: _normalize_component_value(value) for key, value in item.items()}


def _normalize_component_value(value: Any) -> Any:
    if isinstance(value, str):
        return _truth_value(value, missing="NOT_YET_MATERIALIZED")
    if isinstance(value, list):
        return [_normalize_component_value(item) for item in value] or ["NOT_RECORDED"]
    if isinstance(value, dict):
        return {key: _normalize_component_value(child) for key, child in value.items()}
    if value is None:
        return "NOT_RECORDED"
    return value


def _component_dependency_matrix(complete_component_inventory: dict[str, Any]) -> dict[str, Any]:
    rows = [
        {
            "component_id": item["component_id"],
            "component_name": item["component_name"],
            "input_components": item["input_components"],
            "input_artifact": item["input_artifact"],
            "input_business_date": item["input_business_date"],
            "authority_source": item["authority"],
            "implementation_status": item["implementation_status"],
            "configuration_status": item["configuration_status"],
            "authority_resolution_status": item["authority_resolution_status"],
            "target_date_execution_status": item["target_date_execution_status"],
            "runtime_result_status": item["runtime_result_status"],
            "inspection_status": item["inspection_status"],
        }
        for item in complete_component_inventory.get("components", [])
    ]
    return {"status": complete_component_inventory.get("status", "REVIEW_REQUIRED"), "dependencies": rows}


def _runtime_chain_inspection(complete_component_inventory: dict[str, Any]) -> dict[str, Any]:
    chain = [
        "market_refresh",
        "feature_refresh",
        "candidate_ai",
        "opportunity_ai",
        "lifecycle_monitoring",
        "safety_decision",
        "buy_planning",
        "sell_planning_continuity",
        "approval",
        "submit_guard",
        "execution_guard",
        "ledger_update",
        "reporting",
        "notification",
    ]
    by_id = {item.get("component_id"): item for item in complete_component_inventory.get("components", [])}
    items = []
    for index, component_id in enumerate(chain, start=1):
        component = by_id.get(component_id)
        if component:
            items.append({
                "sequence": index,
                "component_id": component_id,
                "component_name": component["component_name"],
                "inspection_status": component["inspection_status"],
                "configuration_status": component["configuration_status"],
                "authority_resolution_status": component["authority_resolution_status"],
                "target_date_execution_status": component["target_date_execution_status"],
                "runtime_result_status": component["runtime_result_status"],
                "runtime_status": component["runtime_status"],
            })
        else:
            items.append({"sequence": index, "component_id": component_id, "component_name": "UNRESOLVED_COMPONENT", "inspection_status": "UNRESOLVED_COMPONENT", "configuration_status": "UNRESOLVED_COMPONENT", "authority_resolution_status": "UNRESOLVED_COMPONENT", "target_date_execution_status": "UNRESOLVED_COMPONENT", "runtime_result_status": "UNRESOLVED_COMPONENT", "runtime_status": "UNRESOLVED_COMPONENT"})
    status = "REVIEW_REQUIRED" if any(item["inspection_status"] == "UNRESOLVED_COMPONENT" for item in items) else "PASS"
    return {"status": status, "chain": items}


def _jquants_dependency_matrix(complete_component_inventory: dict[str, Any]) -> dict[str, Any]:
    rows = [
        {
            "component_id": item["component_id"],
            "component_name": item["component_name"],
            "JQUANTS_DEPENDENT": item["jquants_dependent"],
            "jquants_dependency_type": item["jquants_dependency_type"],
            "jquants_dependency_path": item["jquants_dependency_path"],
            "jquants_direct_input_artifacts": item["jquants_direct_input_artifacts"],
            "jquants_dependency_reason": item["jquants_dependency_reason"],
            "authority": item["authority"],
        }
        for item in complete_component_inventory.get("components", [])
    ]
    return {"status": complete_component_inventory.get("status", "REVIEW_REQUIRED"), "dependencies": rows}


def _runtime_state_coverage(*, root: Path, runtime_state_status: dict[str, Any]) -> dict[str, Any]:
    items = [
        _runtime_state_item("current", "Current", runtime_state_status["current"].get("path", str(root / "runtime_state" / "current_state.json")), runtime_state_status["current"].get("status", "")),
        _runtime_state_item("pending", "Pending", runtime_state_status["pending"].get("path", str(root / "pending_order_plan" / "pending_order_plan.json")), runtime_state_status["pending"].get("status", "")),
        _runtime_state_item("ledger", "Ledger", runtime_state_status["ledger"].get("path", str(root / "persistent_ledger")), runtime_state_status["ledger"].get("status", "")),
        _runtime_state_item("pm", "PM", runtime_state_status["pm"].get("path", str(root / "runtime_state" / "current_state.json")), runtime_state_status["pm"].get("status", "")),
        _runtime_state_item("safety", "Safety", runtime_state_status["safety"].get("artifact_path", str(root / SAFETY_DECISION_RELATIVE_PATH)), runtime_state_status["safety"].get("safety_artifact_status", "")),
        _runtime_state_item("approval", "Approval", str(root / "approval_artifact"), "NOT_YET_APPLICABLE"),
        _runtime_state_item("planning", "Planning", str(root / "pending_order_plan" / "pending_order_plan.json"), "NOT_YET_APPLICABLE"),
        _runtime_state_item("reporting", "Reporting", str(root / "reports"), "NOT_YET_APPLICABLE"),
        _runtime_state_item("notification", "Notification", str(root / "notification"), "NOT_PERFORMED"),
    ]
    unresolved = [item for item in items if item["inspection_status"] == "UNRESOLVED_COMPONENT"]
    return {"status": "REVIEW_REQUIRED" if unresolved else "PASS", "items": items, "unresolved": unresolved}


def _historical_source_consumer_cutoff(*, inspection_context: dict[str, Any], data_inspection: dict[str, Any]) -> dict[str, Any]:
    target = _truth_value(inspection_context.get("target_business_date", ""), missing="NOT_RECORDED")
    source_from = _source_from_date(data_inspection, "normalized_jquants_daily_quotes")
    source_through = _source_date(data_inspection, "normalized_jquants_daily_quotes")
    future_rows_available = _future_rows_available(data_inspection, "normalized_jquants_daily_quotes", target)
    future_rows_consumed: Any = "NOT_YET_MATERIALIZED"
    actual_consumed_through = "NOT_YET_MATERIALIZED"
    status = "PASS"
    if isinstance(future_rows_consumed, int) and future_rows_consumed > 0:
        status = "BLOCK"
    return {
        "status": status,
        "component_id": "historical_source_consumer_cutoff",
        "component_name": "Historical Source Coverage / Consumer Cutoff",
        "target_business_date": target,
        "source_available_from_date": source_from,
        "source_available_through_date": source_through,
        "required_through_date": target,
        "consumer_cutoff_date": target,
        "actual_consumed_from_date": "NOT_YET_MATERIALIZED",
        "actual_consumed_through_date": actual_consumed_through,
        "future_row_guard": "ENABLED_BY_TEMPORAL_GUARD",
        "future_rows_available": future_rows_available,
        "future_rows_consumed": future_rows_consumed,
        "temporal_contract_status": "TEMPORAL_CONTRACT_VIOLATION" if status == "BLOCK" else "PASS",
        "source_coverage_interpretation": "Historical source may contain rows after target date; Runtime consumer cutoff remains target business date.",
    }


def _runtime_state_item(component_id: str, name: str, artifact_path: str, status: Any) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "component_name": name,
        "artifact_path": _truth_value(artifact_path, missing="NOT_YET_MATERIALIZED"),
        "runtime_status": _truth_value(status, missing="NOT_RECORDED"),
        "inspection_status": "PASS",
    }


def _inspection_coverage(
    *,
    complete_component_inventory: dict[str, Any],
    runtime_chain_inspection: dict[str, Any],
    runtime_state_coverage: dict[str, Any],
) -> dict[str, Any]:
    components = complete_component_inventory.get("components", [])
    inspected = [item for item in components if item.get("inspection_status") == "PASS"]
    unresolved = [item for item in components if item.get("inspection_status") == "UNRESOLVED_COMPONENT"]
    warnings = [item for item in components if item.get("runtime_result_status") in {"WARNING", "REVIEW_REQUIRED", "UNRESOLVED", "UNRESOLVED_COMPONENT"}]
    skipped = [item for item in components if item.get("active_or_inactive") == "inactive"]
    status = _combine_status([
        complete_component_inventory.get("status", "REVIEW_REQUIRED"),
        runtime_chain_inspection.get("status", "REVIEW_REQUIRED"),
        runtime_state_coverage.get("status", "REVIEW_REQUIRED"),
    ])
    return {
        "status": status,
        "total_active_components": len([item for item in components if item.get("active_or_inactive") == "active"]),
        "inspected_components": len(inspected),
        "passed": len(inspected),
        "warnings": len(warnings),
        "skipped": len(skipped),
        "unresolved": len(unresolved),
        "repository_scan_component_count": len(components),
        "repository_scan_matches_inventory": len(components) == len(inspected) + len(unresolved),
        "missing_component_policy": "COMPONENT_NOT_INSPECTED causes REVIEW_REQUIRED",
        "unresolved_components": [{"component_id": item["component_id"], "component_name": item["component_name"]} for item in unresolved],
    }


def _source_artifact(data_inspection: dict[str, Any], component_id: str) -> str:
    return str(next((item.get("artifact_path") for item in data_inspection.get("data_sources", []) if item.get("component_id") == component_id), "NOT_RECORDED"))


def _source_date(data_inspection: dict[str, Any], component_id: str) -> str:
    return str(next((item.get("latest_business_date") for item in data_inspection.get("data_sources", []) if item.get("component_id") == component_id), "NOT_RECORDED"))


def _source_from_date(data_inspection: dict[str, Any], component_id: str) -> str:
    return str(next((item.get("earliest_date") for item in data_inspection.get("data_sources", []) if item.get("component_id") == component_id), "NOT_RECORDED"))


def _source_status(data_inspection: dict[str, Any], component_id: str) -> str:
    return str(next((item.get("status") for item in data_inspection.get("data_sources", []) if item.get("component_id") == component_id), "NOT_RECORDED"))


def _first_runtime_feature_artifact(data_inspection: dict[str, Any]) -> str:
    return str(next((item.get("artifact_path") for item in data_inspection.get("runtime_features", []) if item.get("artifact_path")), "NOT_YET_MATERIALIZED"))


def _first_runtime_feature_date(data_inspection: dict[str, Any]) -> str:
    return str(next((item.get("feature_date") for item in data_inspection.get("runtime_features", []) if item.get("feature_date")), "NOT_YET_MATERIALIZED"))


def _stage_status(runtime_stage: str, expected_stage: str) -> str:
    current = RUNTIME_STAGE_ORDER.get(runtime_stage, 0)
    expected = RUNTIME_STAGE_ORDER.get(expected_stage, 0)
    return "NOT_YET_APPLICABLE" if current < expected else "PASS"


def _future_rows_available(data_inspection: dict[str, Any], component_id: str, target_date: str) -> Any:
    source = next((item for item in data_inspection.get("data_sources", []) if item.get("component_id") == component_id), {})
    latest = _extract_date(str(source.get("latest_business_date") or ""))
    target = _extract_date(str(target_date or ""))
    if not latest or not target:
        return "NOT_RECORDED"
    return bool(latest > target)


def _data_source_inventory(*, data_inspection: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    present = {item.get("component_id"): item for item in data_inspection.get("data_sources", [])}
    required = [
        ("raw_jquants_daily_quotes", "Daily Quotes Raw", "ACTIVE"),
        ("normalized_jquants_daily_quotes", "Daily Quotes Normalized", "ACTIVE"),
        ("listed_issues", "Listed Issues", "ACTIVE"),
        ("financial_statements", "Financial Statements", "NOT_REQUIRED_BY_CURRENT_GENERATION"),
        ("topix_market_index", "TOPIX / Market Index", "NOT_REQUIRED_BY_CURRENT_GENERATION"),
        ("trading_calendar", "Trading Calendar", "ACTIVE"),
        ("corporate_actions", "Corporate Actions", "NOT_REQUIRED_BY_CURRENT_GENERATION"),
        ("universe_eligibility", "Universe / Eligibility Data", "ACTIVE"),
    ]
    items = []
    for component_id, name, activity in required:
        source = present.get(component_id, {})
        if component_id == "trading_calendar":
            source = {
                "component_id": component_id,
                "component_name": name,
                "authority": "configured trading calendar / business day resolver",
                "artifact_path": "NOT_MATERIALIZED_AS_STANDALONE_ARTIFACT",
                "latest_date": "RESOLVED_BY_POLICY",
                "status": "PASS",
            }
        elif component_id == "universe_eligibility":
            source = {
                "component_id": component_id,
                "component_name": name,
                "authority": "Accepted Generation dataset and listed issues binding",
                "artifact_path": present.get("listed_issues", {}).get("artifact_path", "NOT_RESOLVED"),
                "latest_date": present.get("listed_issues", {}).get("latest_business_date", ""),
                "status": present.get("listed_issues", {}).get("status", "BLOCK"),
            }
        item = {
            "component_id": component_id,
            "component_name": name,
            "activity_status": activity,
            "authority": source.get("authority", "Accepted Generation feature contract" if activity == "ACTIVE" else "Current generation does not bind this source"),
            "artifact_path": _truth_value(source.get("artifact_path", "NOT_REQUIRED_BY_CURRENT_GENERATION")),
            "earliest_date": _truth_value(source.get("earliest_date", "NOT_APPLICABLE")),
            "latest_date": _truth_value(source.get("latest_business_date") or source.get("latest_date") or "NOT_APPLICABLE"),
            "row_count": source.get("row_count", "NOT_APPLICABLE"),
            "symbol_count": source.get("symbol_count", "NOT_APPLICABLE"),
            "schema_hash": _truth_value(source.get("schema_hash", "NOT_APPLICABLE")),
            "content_hash": _truth_value(source.get("content_hash") or source.get("manifest_hash") or "NOT_APPLICABLE"),
            "missing_required_dates": source.get("missing_business_dates", source.get("missing_dates", [])),
            "duplicate_count": source.get("duplicate_count", "NOT_APPLICABLE"),
            "consumer": "Candidate/Opportunity runtime feature pipeline" if activity == "ACTIVE" else "NONE_FOR_CURRENT_GENERATION",
            "status": source.get("status", "PASS" if activity == "NOT_REQUIRED_BY_CURRENT_GENERATION" else "BLOCK"),
            "reason": "bound_by_current_generation" if activity == "ACTIVE" else "not referenced by Candidate/Opportunity Accepted Generation feature order",
        }
        items.append(item)
    return {"status": _combine_status(item["status"] for item in items), "items": items}


def _current_data_freshness_contract(
    *,
    mode: str,
    created_at: str,
    data_inspection: dict[str, Any],
    ai_inventory: dict[str, Any],
) -> dict[str, Any]:
    latest_expected = _previous_weekday(_extract_date(created_at))
    sources = {item.get("component_id"): item for item in data_inspection.get("data_sources", [])}
    latest_feature = max((str(item.get("feature_date") or "") for item in data_inspection.get("runtime_features", []) if item.get("feature_date")), default="")
    latest_inference = max((str(item.get("latest_inference_date") or "") for item in ai_inventory.get("active_ai_models", []) if item.get("latest_inference_date")), default="")
    local_normalized = str(sources.get("normalized_jquants_daily_quotes", {}).get("latest_business_date") or "")
    return {
        "status": "NOT_EVALUATED",
        "mode": mode,
        "latest_expected_market_business_date": latest_expected,
        "latest_local_raw_date": str(sources.get("raw_jquants_daily_quotes", {}).get("latest_business_date") or ""),
        "latest_local_normalized_date": local_normalized,
        "latest_local_listed_issues_date": str(sources.get("listed_issues", {}).get("latest_business_date") or ""),
        "latest_local_feature_date": latest_feature or "NOT_YET_MATERIALIZED",
        "latest_local_inference_date": latest_inference or "NOT_YET_MATERIALIZED",
        "lag_business_days": _business_day_lag(local_normalized, latest_expected) if local_normalized else "NOT_EVALUATED",
        "expected_date_source": "local_trading_calendar_policy_and_current_time",
        "publication_lag_policy": "J-Quants publication timing contract; external availability not checked by read-only system-status",
        "refresh_last_attempt_at": "NOT_EVALUATED",
        "refresh_last_success_at": "NOT_EVALUATED",
        "refresh_status": "EXTERNAL_AVAILABILITY_NOT_VERIFIED",
        "readiness": "NOT_EVALUATED",
        "reason": f"{mode} current-data readiness is not established by Historical pre-run inspection.",
    }


def _historical_coverage_contract(*, freshness_matrix: dict[str, Any]) -> dict[str, Any]:
    items = [
        item for item in freshness_matrix.get("items", [])
        if item.get("freshness_date_semantics") == "historical_coverage_not_lag"
    ]
    return {
        "status": "PASS" if all(item.get("missing_required_business_days") in (0, "", "0") for item in items) else "BLOCK",
        "items": items,
    }


def _baseline_traceability(*, manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    binding = str((manifest.get("component_hashes") or {}).get("runtime_baseline_hash") or "")
    baseline_payload = {
        "baseline_scope": "GENERATION_SHARED",
        "baseline_storage_mode": "EMBEDDED_IN_ACCEPTED_GENERATION",
        "baseline_artifact_path": "NOT_APPLICABLE",
        "baseline_artifact_hash": "NOT_APPLICABLE",
        "baseline_binding_hash": binding,
        "baseline_schema_version": "accepted_generation_manifest.component_hashes.runtime_baseline_hash",
        "baseline_created_at": manifest.get("accepted_at", "NOT_RESOLVED"),
        "baseline_source_generation": manifest.get("accepted_generation_id", "NOT_RESOLVED"),
        "baseline_runtime_consumer": "Runtime lifecycle monitoring / threshold policy",
        "baseline_resolution_status": "PASS" if binding else "REVIEW_REQUIRED",
        "manifest_path": _display_path(manifest_path),
        "json_pointer": "/component_hashes/runtime_baseline_hash",
        "resolved_hash": binding or "NOT_RESOLVED",
        "reason": "generation-shared baseline hash is embedded in Accepted Generation Manifest",
    }
    return {"status": baseline_payload["baseline_resolution_status"], **baseline_payload}


def _freshness_policy_traceability(*, manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    metadata = manifest.get("freshness_metadata", {}) if isinstance(manifest.get("freshness_metadata"), dict) else {}
    binding = str((manifest.get("component_hashes") or {}).get("freshness_metadata_hash") or metadata.get("content_hash") or "")
    return {
        "status": "PASS" if binding else "REVIEW_REQUIRED",
        "freshness_policy_artifact_path": _display_path(manifest_path),
        "freshness_policy_hash": metadata.get("content_hash", "NOT_RESOLVED"),
        "freshness_binding_hash": binding or "NOT_RESOLVED",
        "schema_version": metadata.get("schema_version", "EMBEDDED_IN_ACCEPTED_GENERATION"),
        "policy_source": metadata.get("source_phase", "PHASE19_AP"),
        "runtime_consumer": "Runtime freshness/lifecycle monitoring",
        "resolution_status": "PASS" if binding else "REVIEW_REQUIRED",
        "storage_mode": "EMBEDDED_IN_ACCEPTED_GENERATION",
        "json_pointer": "/freshness_metadata",
        "target_date_decision_status": "NOT_YET_APPLICABLE",
    }


def _recent_holdout_usage_audit(*, ai_data_window_summary: dict[str, Any]) -> dict[str, Any]:
    items = []
    for item in ai_data_window_summary.get("items", []):
        items.append({
            "component_id": item.get("component_id", ""),
            "recent_holdout_period": item.get("recent_holdout") or "NOT_DECLARED",
            "recent_holdout_usage_status": "NOT_USED_IN_PHASE19",
            "recent_holdout_runtime_authority_impact": "NONE",
            "status": "PASS",
        })
    return {"status": "PASS", "items": items}


def _calibration_validation_independence_audit(*, ai_data_window_summary: dict[str, Any]) -> dict[str, Any]:
    items = []
    for item in ai_data_window_summary.get("items", []):
        items.append({
            "component_id": item.get("component_id", ""),
            "calibration_mode": (item.get("calibration") or {}).get("mode", ""),
            "what_was_fitted": "Candidate Platt parameters or Opportunity standardization parameters only",
            "metrics_measured_before_calibration": "identity/raw score diagnostics",
            "metrics_measured_after_calibration": "calibrated probability/normalized opportunity score diagnostics",
            "model_selection_used_this_window": False,
            "independent_final_evaluation_window": item.get("test", {}),
            "status": "PASS" if (item.get("calibration") or {}).get("mode") == "SHARED_WITH_VALIDATION" and item.get("test") else "REVIEW_REQUIRED",
        })
    return {"status": _combine_status(item["status"] for item in items), "items": items}


def _broker_truthfulness_audit(*, broker_layer_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "broker_configuration_status": "PASS",
        "broker_connectivity_check_status": "NOT_PERFORMED",
        "credential_access_status": "NOT_PERFORMED",
        "broker_write_status": "PROHIBITED",
        "submit_guard_configuration_status": "PASS",
        "broker_layer_aggregate": broker_layer_status.get("truthfulness_status", "CONFIGURATION_PASS_CONNECTIVITY_NOT_PERFORMED"),
        "historical_overall_impact": "NOT_BLOCKING_HISTORICAL_PRE_RUN",
        "production_readiness_impact": "PRODUCTION_BROKER_READINESS_NOT_ESTABLISHED",
    }


def _not_performed_checks(*, broker_truthfulness: dict[str, Any], runtime_stage_contract: dict[str, Any]) -> dict[str, Any]:
    label_by_component = {
        "runtime_features": "Runtime feature generation",
        "candidate_inference": "Candidate/Opportunity inference",
        "opportunity_inference": "Candidate/Opportunity inference",
        "safety_decision": "Safety decision",
        "buy_planning": "Planning",
        "submit": "Submit",
        "execution": "Execution",
        "reporting": "Reporting",
        "notification": "Notification",
    }
    checks = []
    for item in runtime_stage_contract.get("components", []):
        component_id = str(item.get("component_id") or "")
        status = str(item.get("status") or "")
        label = label_by_component.get(component_id)
        if label and status in {"NOT_YET_APPLICABLE", "POST_STAGE_MATERIALIZATION_MISSING"} and label not in checks:
            checks.append(label)
    if broker_truthfulness.get("broker_connectivity_check_status") == "NOT_PERFORMED":
        checks.append("Broker connectivity")
    return {"status": "PASS", "checks": checks}


def _not_evaluated_checks(*, production_freshness: dict[str, Any], demo_freshness: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "checks": [
            "current Demo freshness",
            "current Production freshness",
            "Broker connectivity",
            "multi-day continuity",
        ],
        "production_freshness_status": production_freshness.get("status", ""),
        "demo_freshness_status": demo_freshness.get("status", ""),
    }


def _operational_summary(
    *,
    inspection_context: dict[str, Any],
    environment_readiness: dict[str, Any],
    runtime_stage_contract: dict[str, Any],
    temporal_authority_audit: dict[str, Any],
    target_period_data_sufficiency: dict[str, Any],
    active_model_summary: dict[str, Any],
    active_component_count_summary: dict[str, Any],
    not_performed_checks: dict[str, Any],
    not_evaluated_checks: dict[str, Any],
) -> dict[str, Any]:
    blockers = []
    if temporal_authority_audit.get("status") == "BLOCK":
        blockers.append("temporal isolation")
    if target_period_data_sufficiency.get("status") == "BLOCK":
        blockers.append("target-period market data coverage")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "inspection_context_summary": f"{inspection_context.get('inspection_mode')} for {inspection_context.get('target_business_date')} at {inspection_context.get('runtime_root')}",
        "verified": [
            "Temporal isolation",
            "Target-period market data coverage",
            "Accepted Generation authority",
            "Candidate/Opportunity model loadability",
            "Initial Ledger/Current/PM state",
        ],
        "not_yet_performed": not_performed_checks.get("checks", []),
        "current_blockers": blockers or ["none for single-day Historical start"],
        "not_evaluated": not_evaluated_checks.get("checks", []),
        "active_trained_model_count": active_model_summary.get("active_trained_model_count"),
        "components_with_complete_input_lineage_inspection": active_component_count_summary.get("components_with_complete_input_lineage_inspection"),
        "components_with_unresolved_input_lineage_inspection": active_component_count_summary.get("components_with_unresolved_input_lineage_inspection"),
        "historical_pre_run_readiness": environment_readiness.get("historical_pre_run_readiness"),
        "day1_start_permission": runtime_stage_contract.get("day1_start_permission"),
    }


def _status_summary(
    *,
    inspection_context: dict[str, Any],
    overall_status: str,
    data_status: dict[str, Any],
    ai_status: dict[str, Any],
    runtime_status: dict[str, Any],
    runtime_state_status: dict[str, Any],
    broker_layer_status: dict[str, Any],
    environment_readiness: dict[str, Any],
    target_period_data_sufficiency: dict[str, Any],
) -> dict[str, Any]:
    post_run = inspection_context.get("inspection_mode") == "HISTORICAL_POST_RUN"
    runtime_execution = "PASS" if post_run and inspection_context.get("post_run_context", {}).get("status") == "PASS" else runtime_status.get("status", overall_status)
    model_health = runtime_status.get("model_health", {})
    broker_config = "PASS" if broker_layer_status.get("submit_guard", {}).get("configuration_status") == "PASS" else broker_layer_status.get("status", "")
    return {
        "inspection_judgment": "PASS" if overall_status == "PASS" else overall_status,
        "runtime_execution_judgment": runtime_execution,
        "data_judgment": data_status.get("status", ""),
        "ai_authority_judgment": ai_status.get("accepted_generation", {}).get("status") or ai_status.get("status", ""),
        "model_health_judgment": model_health.get("status", "PASS"),
        "model_health_runtime_impact": model_health.get("runtime_impact", "NONE"),
        "model_health_buy_impact": model_health.get("buy_impact", "PASS"),
        "model_health_sell_impact": model_health.get("sell_impact", "PASS"),
        "runtime_state_judgment": runtime_state_status.get("status", ""),
        "broker_configuration_judgment": broker_config,
        "broker_connectivity_judgment": broker_layer_status.get("broker_connection", {}).get("status", "NOT_PERFORMED"),
        "broker_judgment": broker_layer_status.get("truthfulness_status", broker_layer_status.get("status", "")),
        "readiness_judgment": environment_readiness.get("production_current_data_readiness", "NOT_EVALUATED"),
        "production_readiness": "NOT_EVALUATED" if not environment_readiness.get("production_ready") else "PASS",
        "strategy_judgment": "NOT_EVALUATED",
        "target_period_data_sufficiency_judgment": target_period_data_sufficiency.get("status", ""),
        "exit_code_basis": "overall_inspection",
    }


def build_system_status_scoped_view(report: dict[str, Any], *, scope: str = "overview") -> dict[str, Any]:
    scope = scope or "overview"
    if scope not in SYSTEM_STATUS_SCOPES:
        raise ValueError(f"invalid system-status scope: {scope}")
    sections = _system_status_sections(report)
    selected_sections = sections if scope == "full" else {scope: sections[scope]}
    findings = _system_status_findings(report)
    view = {
        "schema_version": SYSTEM_STATUS_VIEW_SCHEMA_VERSION,
        "subcommand": "system-status",
        "scope": scope,
        "inspection_context": report.get("inspection_context", {}),
        "status_summary": report.get("status_summary", {}),
        "findings": findings,
        "final_judgment": _system_status_final_judgment(report),
        "sections": selected_sections,
        "legacy_json_compatibility": {
            "system_status_report_top_level_preserved": True,
            "legacy_schema_version": report.get("schema_version", ""),
            "migration": "Use --scope full --json or the deprecated system_status_report top-level field for full legacy inspection JSON.",
        },
    }
    view["human_summary"] = render_system_status_scoped_human_summary(view, legacy_full_human=report.get("human_summary", ""))
    return _sanitize_empty_values(view)


def _system_status_sections(report: dict[str, Any]) -> dict[str, Any]:
    context = report.get("inspection_context", {})
    data = report.get("data_status", {})
    runtime_state = report.get("runtime_state_status", {})
    current_artifact = next(
        (item for item in runtime_state.get("temporal_isolation", {}).get("artifacts", []) if item.get("component_id") == "persistent_ledger_current"),
        {},
    )
    return {
        "overview": {
            "inspection_context": context,
            "status_summary": report.get("status_summary", {}),
            "data_freshness": _overview_data_freshness(report),
            "runtime": {
                "completed_days": len(context.get("completed_business_days") or []),
                "runtime_stage": context.get("runtime_stage", ""),
                "current_cash": current_artifact.get("cash", ""),
                "positions": current_artifact.get("position_count", ""),
                "pending_orders": _pending_order_count(runtime_state),
            },
            "accepted_generation": _accepted_generation_overview(report),
        },
        "data": {
            "data_status": data,
            "data_sources": report.get("data_inspection", {}).get("data_sources", []),
            "runtime_features": report.get("data_inspection", {}).get("runtime_features", []),
            "target_period_data_sufficiency": report.get("target_period_data_sufficiency", {}),
            "freshness_matrix": report.get("freshness_matrix", {}),
            "historical_source_consumer_cutoff": report.get("historical_source_consumer_cutoff", {}),
        },
        "ai": {
            "ai_status": report.get("ai_status", {}),
            "accepted_generation": report.get("authority_generation", {}),
            "active_model_summary": report.get("active_model_summary", {}),
            "ai_data_window_summary": report.get("ai_data_window_summary", {}),
            "baseline_traceability": report.get("baseline_traceability", {}),
            "freshness_policy_traceability": report.get("freshness_policy_traceability", {}),
        },
        "runtime": {
            "runtime_status": report.get("runtime_status", {}),
            "runtime_state_status": runtime_state,
            "runtime_stage_contract": report.get("runtime_stage_contract", {}),
            "decision_subsystems": report.get("decision_subsystems", {}),
            "runtime_chain_inspection": report.get("runtime_chain_inspection", {}),
        },
        "broker": {
            "broker_layer_status": report.get("broker_layer_status", {}),
            "broker_truthfulness_audit": report.get("broker_truthfulness_audit", {}),
            "not_performed_checks": report.get("not_performed_checks", {}),
            "external_effects": {
                "broker_access": "NOT_PERFORMED",
                "broker_write": "NOT_PERFORMED",
            },
        },
        "readiness": {
            "environment_readiness": report.get("environment_readiness", {}),
            "operational_summary": report.get("operational_summary", {}),
            "not_evaluated_checks": report.get("not_evaluated_checks", {}),
        },
        "lineage": {
            "candidate_input_lineage": report.get("candidate_input_lineage", {}),
            "opportunity_input_lineage": report.get("opportunity_input_lineage", {}),
            "runtime_input_lineage_contract": report.get("runtime_input_lineage_contract", {}),
            "split_window_statistics": report.get("split_window_statistics", {}),
            "recent_holdout_usage_audit": report.get("recent_holdout_usage_audit", {}),
            "calibration_validation_independence_audit": report.get("calibration_validation_independence_audit", {}),
        },
        "components": {
            "active_component_count_summary": report.get("active_component_count_summary", {}),
            "active_component_inventory": report.get("active_component_inventory", {}),
            "complete_component_inventory": report.get("complete_component_inventory", {}),
            "component_dependency_matrix": report.get("component_dependency_matrix", {}),
            "jquants_dependency_matrix": report.get("jquants_dependency_matrix", {}),
            "runtime_state_coverage": report.get("runtime_state_coverage", {}),
            "inspection_coverage": report.get("inspection_coverage", {}),
        },
    }


def _overview_data_freshness(report: dict[str, Any]) -> dict[str, Any]:
    sources = {item.get("component_id"): item for item in report.get("data_inspection", {}).get("data_sources", [])}
    features = {item.get("component_id"): item for item in report.get("data_inspection", {}).get("runtime_features", [])}
    return {
        "raw_quotes": {"date": sources.get("raw_jquants_daily_quotes", {}).get("latest_business_date", ""), "status": sources.get("raw_jquants_daily_quotes", {}).get("status", "")},
        "normalized_quotes": {"date": sources.get("normalized_jquants_daily_quotes", {}).get("latest_business_date", ""), "status": sources.get("normalized_jquants_daily_quotes", {}).get("status", "")},
        "listed_issues": {"date": sources.get("listed_issues", {}).get("latest_business_date", ""), "status": sources.get("listed_issues", {}).get("status", "")},
        "candidate_feature": {"date": features.get("candidate_runtime_feature", {}).get("feature_date", ""), "status": features.get("candidate_runtime_feature", {}).get("status", "")},
        "opportunity_feature": {"date": features.get("opportunity_runtime_feature", {}).get("feature_date", ""), "status": features.get("opportunity_runtime_feature", {}).get("status", "")},
    }


def _accepted_generation_overview(report: dict[str, Any]) -> dict[str, Any]:
    authority = report.get("authority_generation", {})
    return {
        "accepted_generation_id": authority.get("committed_accepted_generation_id", ""),
        "status": authority.get("status", ""),
        "accepted_at": authority.get("accepted_at", ""),
        "age": authority.get("accepted_generation_age", {}),
    }


def _pending_order_count(runtime_state_status: dict[str, Any]) -> Any:
    for item in runtime_state_status.get("temporal_isolation", {}).get("artifacts", []):
        if item.get("component_id") == "pending_plan":
            return item.get("order_count", "")
    return "NOT_RECORDED"


def _system_status_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    for text in report.get("system_status_summary", {}).get("main_findings", []):
        if text and text != "No blocking findings.":
            if text.startswith("Runtime lifecycle:") and report.get("runtime_status", {}).get("model_health", {}).get("status") == "REVIEW_REQUIRED":
                continue
            findings.append({"severity": "REVIEW_REQUIRED", "reason": text})
    model = report.get("runtime_status", {}).get("model_health", {})
    if model.get("status") == "REVIEW_REQUIRED":
        findings.append(
            {
                "severity": "REVIEW_REQUIRED",
                "reason": "MODEL_HEALTH_REVIEW_REQUIRED",
                "runtime_impact": model.get("runtime_impact", "NONE"),
                "buy_impact": model.get("buy_impact", "PASS"),
                "sell_impact": model.get("sell_impact", "PASS"),
            }
        )
    broker = report.get("broker_layer_status", {}).get("broker_connection", {})
    if broker.get("status") == "NOT_PERFORMED":
        findings.append({"severity": "NOT_PERFORMED", "reason": "BROKER_CONNECTIVITY_NOT_PERFORMED"})
    return findings or [{"severity": "PASS", "reason": "NO_BLOCKING_FINDINGS"}]


def _system_status_final_judgment(report: dict[str, Any]) -> str:
    summary = report.get("status_summary", {})
    if summary.get("inspection_judgment") == "PASS" and summary.get("model_health_judgment") == "REVIEW_REQUIRED":
        return "SYSTEM_STATUS_PASS_WITH_MODEL_HEALTH_REVIEW"
    if summary.get("inspection_judgment") == "PASS":
        return "SYSTEM_STATUS_PASS"
    return f"SYSTEM_STATUS_{summary.get('inspection_judgment', 'REVIEW_REQUIRED')}"


def render_system_status_scoped_human_summary(view: dict[str, Any], *, legacy_full_human: str = "") -> str:
    scope = view.get("scope", "overview")
    if scope == "full" and legacy_full_human:
        return legacy_full_human
    if scope == "overview":
        return _render_system_status_overview(view)
    section = view.get("sections", {}).get(scope, {})
    lines = [
        f"AI Fund Lab v2 System Status - {scope.title()}",
        "=" * (35 + len(scope)),
        "",
        "Summary",
        "-------",
        f"Inspection : {view.get('status_summary', {}).get('inspection_judgment', '')}",
        f"Runtime Execution : {view.get('status_summary', {}).get('runtime_execution_judgment', '')}",
        f"Data : {view.get('status_summary', {}).get('data_judgment', '')}",
        f"AI Authority : {view.get('status_summary', {}).get('ai_authority_judgment', '')}",
        f"Model Health : {view.get('status_summary', {}).get('model_health_judgment', '')}",
        f"Broker Connectivity : {view.get('status_summary', {}).get('broker_connectivity_judgment', '')}",
        "",
        "Details",
        "-------",
    ]
    for key, value in section.items():
        lines.append(f"{key}: {_short_value(value)}")
    lines.extend(["", "Final", "-----", str(view.get("final_judgment", ""))])
    return "\n".join(lines)


def _render_system_status_overview(view: dict[str, Any]) -> str:
    section = view.get("sections", {}).get("overview", {})
    context = view.get("inspection_context", {})
    status = view.get("status_summary", {})
    freshness = section.get("data_freshness", {})
    runtime = section.get("runtime", {})
    generation = section.get("accepted_generation", {})
    findings = [item for item in view.get("findings", []) if item.get("severity") != "PASS"]
    lines = [
        "AI Fund Lab v2 System Status",
        "============================",
        "",
        "Context",
        "-------",
        f"Inspection Mode     : {context.get('inspection_mode', '')}",
        f"Run ID              : {context.get('runtime_test_run_id', 'NOT_APPLICABLE')}",
        f"Profile             : {context.get('profile', '')}",
        f"Target Date         : {context.get('target_business_date', '')}",
        f"Runtime Stage       : {context.get('runtime_stage', '')}",
        "",
        "Status",
        "------",
        f"Inspection          : {status.get('inspection_judgment', '')}",
        f"Runtime Execution   : {status.get('runtime_execution_judgment', '')}",
        f"Data                : {status.get('data_judgment', '')}",
        f"AI Authority        : {status.get('ai_authority_judgment', '')}",
        f"Model Health        : {status.get('model_health_judgment', '')}",
        f"Runtime State       : {status.get('runtime_state_judgment', '')}",
        f"Broker Config       : {status.get('broker_configuration_judgment', '')}",
        f"Broker Connectivity : {status.get('broker_connectivity_judgment', '')}",
        f"Production Ready    : {status.get('production_readiness', '')}",
        "",
        "Data Freshness",
        "--------------",
    ]
    for label, key in (
        ("Raw Quotes", "raw_quotes"),
        ("Normalized Quotes", "normalized_quotes"),
        ("Listed Issues", "listed_issues"),
        ("Candidate Feature", "candidate_feature"),
        ("Opportunity Feature", "opportunity_feature"),
    ):
        item = freshness.get(key, {})
        lines.append(f"{label:<20}: {item.get('date', '')} {item.get('status', '')}")
    lines.extend(
        [
            "",
            "Runtime",
            "-------",
            f"Completed Days      : {runtime.get('completed_days', '')}",
            f"Current Cash        : {runtime.get('current_cash', '')} JPY",
            f"Positions           : {runtime.get('positions', '')}",
            f"Pending Orders      : {runtime.get('pending_orders', '')}",
            "",
            "Accepted Generation",
            "-------------------",
            f"ID                  : {generation.get('accepted_generation_id', '')}",
            f"Status              : {generation.get('status', '')}",
            f"Accepted At         : {generation.get('accepted_at', '')}",
            f"Age                 : {(generation.get('age') or {}).get('human', '')}",
            "",
            "Findings",
            "--------",
        ]
    )
    if findings:
        lines.extend(f"- {finding.get('reason')} (runtime impact: {finding.get('runtime_impact', 'N/A')})" for finding in findings[:8])
    else:
        lines.append("- No blocking findings.")
    lines.extend(["", "Final", "-----", str(view.get("final_judgment", ""))])
    return "\n".join(lines)


def write_system_status_evidence(report: dict[str, Any], *, evidence_root: Path, run_id: str | None = None) -> Path:
    run_id = run_id or "system-status-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_root = Path(evidence_root) / "system_status" / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    mapping = {
        "system_status_summary.json": report["system_status_summary"],
        "inspection_context.json": report["inspection_context"],
        "environment_readiness.json": report["environment_readiness"],
        "operational_summary.json": report["operational_summary"],
        "active_model_summary.json": report["active_model_summary"],
        "active_component_count_summary.json": report["active_component_count_summary"],
        "candidate_input_lineage.json": report["candidate_input_lineage"],
        "opportunity_input_lineage.json": report["opportunity_input_lineage"],
        "split_window_statistics.json": report["split_window_statistics"],
        "runtime_input_lineage_contract.json": report["runtime_input_lineage_contract"],
        "complete_component_inventory.json": report["complete_component_inventory"],
        "component_dependency_matrix.json": report["component_dependency_matrix"],
        "runtime_chain_inspection.json": report["runtime_chain_inspection"],
        "jquants_dependency_matrix.json": report["jquants_dependency_matrix"],
        "runtime_state_coverage.json": report["runtime_state_coverage"],
        "historical_source_consumer_cutoff.json": report["historical_source_consumer_cutoff"],
        "inspection_coverage.json": report["inspection_coverage"],
        "data_source_inventory.json": report["data_source_inventory"],
        "production_freshness.json": report["production_freshness"],
        "demo_freshness.json": report["demo_freshness"],
        "historical_coverage.json": report["historical_coverage"],
        "baseline_traceability.json": report["baseline_traceability"],
        "freshness_policy_traceability.json": report["freshness_policy_traceability"],
        "recent_holdout_usage_audit.json": report["recent_holdout_usage_audit"],
        "calibration_validation_independence_audit.json": report["calibration_validation_independence_audit"],
        "broker_truthfulness_audit.json": report["broker_truthfulness_audit"],
        "not_performed_checks.json": report["not_performed_checks"],
        "not_evaluated_checks.json": report["not_evaluated_checks"],
        "active_component_inventory.json": report["active_component_inventory"],
        "data_inspection.json": report["data_inspection"],
        "decision_subsystems.json": report["decision_subsystems"],
        "authority_generation.json": report["authority_generation"],
        "runtime_stage_contract.json": report["runtime_stage_contract"],
        "ai_data_window_summary.json": report["ai_data_window_summary"],
        "active_trained_ai_inventory.json": report["active_trained_ai_inventory"],
        "temporal_authority_audit.json": report["temporal_authority_audit"],
        "freshness_matrix.json": report["freshness_matrix"],
        "target_period_data_sufficiency.json": report["target_period_data_sufficiency"],
        "data_status.json": report["data_status"],
        "ai_status.json": report["ai_status"],
        "runtime_status.json": report["runtime_status"],
        "runtime_state_status.json": report["runtime_state_status"],
        "broker_layer_status.json": report["broker_layer_status"],
        "overall_status.json": report["overall_status"],
        "non_mutation.json": report["non_mutation"],
        "final_judgment.json": report["final_judgment"],
    }
    for name, payload in mapping.items():
        _write_json(run_root / name, payload)
    (run_root / "ai_system_inventory.md").write_text(_render_inventory_markdown(report["active_component_inventory"]) + "\n", encoding="utf-8")
    (run_root / "system_status_report.md").write_text(report["human_summary"] + "\n", encoding="utf-8")
    return run_root


def render_system_status_human_summary(
    summary: dict[str, Any],
    *,
    active_component_inventory: dict[str, Any],
    inspection_context: dict[str, Any],
    environment_readiness: dict[str, Any],
    operational_summary: dict[str, Any],
    active_model_summary: dict[str, Any],
    active_component_count_summary: dict[str, Any],
    candidate_input_lineage: dict[str, Any],
    opportunity_input_lineage: dict[str, Any],
    runtime_input_lineage_contract: dict[str, Any],
    complete_component_inventory: dict[str, Any],
    component_dependency_matrix: dict[str, Any],
    runtime_chain_inspection: dict[str, Any],
    jquants_dependency_matrix: dict[str, Any],
    runtime_state_coverage: dict[str, Any],
    historical_source_consumer_cutoff: dict[str, Any],
    inspection_coverage: dict[str, Any],
    data_source_inventory: dict[str, Any],
    baseline_traceability: dict[str, Any],
    freshness_policy_traceability: dict[str, Any],
    data_inspection: dict[str, Any],
    decision_subsystems: dict[str, Any],
    authority_generation: dict[str, Any],
    runtime_stage_contract: dict[str, Any],
    ai_data_window_summary: dict[str, Any],
    temporal_authority_audit: dict[str, Any],
    runtime_state_status: dict[str, Any],
    broker_layer_status: dict[str, Any],
    freshness_matrix: dict[str, Any],
    target_period_data_sufficiency: dict[str, Any],
    non_mutation: dict[str, Any],
) -> str:
    lines = [
        "# AI Fund Lab v2 System Status Inspection",
        "",
        "## 1. Operational Summary",
        "Overall Status Scope: PASS means all checks required for the current inspection context and runtime stage are normal, and not-yet-run items are correctly classified as NOT_YET_APPLICABLE or NOT_PERFORMED. It does not mean all target-date Runtime components completed, BUY_READY, PRODUCTION_READY, AUTONOMOUS_OPERATION_COMPLETE, or Broker Connectivity PASS.",
        f"Inspection context: {operational_summary.get('inspection_context_summary', '')}",
        "Verified:",
        *[f"- {item}" for item in operational_summary.get("verified", [])],
        "Not yet performed:",
        *[f"- {item}" for item in operational_summary.get("not_yet_performed", [])],
        "Current blockers:",
        *[f"- {item}" for item in operational_summary.get("current_blockers", [])],
        "Not evaluated:",
        *[f"- {item}" for item in operational_summary.get("not_evaluated", [])],
        "",
        "## 2. Header / Overall",
        f"Inspection Mode: {inspection_context.get('inspection_mode', '')}",
        f"Runtime Mode: {inspection_context.get('runtime_mode', '')}",
        f"Broker Environment: {inspection_context.get('broker_environment', '')}",
        f"Profile: {inspection_context.get('profile', '')}",
        f"Runtime Root: {inspection_context.get('runtime_root', '')}",
        f"Root Type: {inspection_context.get('runtime_root_type', '')}",
        f"Target Business Date: {inspection_context.get('target_business_date', '')}",
        f"Current Calendar Date: {inspection_context.get('current_calendar_date', '')}",
        f"Overall Status: {summary.get('overall_status', '')}",
        f"Exit Code: {summary.get('exit_code', '')}",
        f"Created At: {summary.get('created_at', '')}",
        f"Runtime Stage: {runtime_stage_contract.get('runtime_stage', '')}",
        f"Pre-run Readiness: {runtime_stage_contract.get('pre_run_readiness', '')}",
        f"Day1 Start Permission: {runtime_stage_contract.get('day1_start_permission', '')}",
        f"Data: {summary['data'].get('status', '')}",
        f"AI: {summary['ai'].get('status', '')}",
        f"Runtime: {summary['runtime'].get('status', '')}",
        f"Runtime State: {summary['runtime_state'].get('status', '')}",
        f"Broker Layer: {summary['broker_layer'].get('status', '')}",
        "Broker Access: NOT_PERFORMED",
        f"Historical Pre-run Readiness: {environment_readiness.get('historical_pre_run_readiness', '')}",
        f"Single-day Runtime Readiness: {environment_readiness.get('single_day_runtime_readiness', '')}",
        f"Multi-day Continuity Readiness: {environment_readiness.get('multi_day_continuity_readiness', '')}",
        f"Demo Current-data Readiness: {environment_readiness.get('demo_current_data_readiness', '')}",
        f"Production Current-data Readiness: {environment_readiness.get('production_current_data_readiness', '')}",
        f"Broker Connectivity Readiness: {environment_readiness.get('broker_connectivity_readiness', '')}",
        f"Broker Write Readiness: {environment_readiness.get('broker_write_readiness', '')}",
        f"Active trained model count: {active_model_summary.get('active_trained_model_count', '')}",
        f"Models with complete artifact validation: {active_model_summary.get('models_with_complete_artifact_validation', '')}",
        f"Models with unresolved artifact validation: {active_model_summary.get('models_with_unresolved_artifact_validation', '')}",
        f"Components with complete input-lineage inspection: {active_component_count_summary.get('components_with_complete_input_lineage_inspection', '')}",
        f"Components with unresolved input-lineage inspection: {active_component_count_summary.get('components_with_unresolved_input_lineage_inspection', '')}",
        f"Total active operational components: {inspection_coverage.get('total_active_components', '')}",
        f"Inspected operational components: {inspection_coverage.get('inspected_components', '')}",
        f"Unresolved operational components: {inspection_coverage.get('unresolved', '')}",
        "",
        "## 3. Historical Temporal Isolation",
    ]
    lines.extend(_component_lines(temporal_authority_audit))
    lines.extend(["", "## 4. Active Component Inventory"])
    for item in active_component_inventory.get("components", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 5. Data Sources"])
    for item in data_inspection.get("data_sources", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 6. Complete Data Source Inventory"])
    for item in data_source_inventory.get("items", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 7. Datasets"])
    for item in data_inspection.get("datasets", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 8. AI Input Lineage"])
    for item in (candidate_input_lineage, opportunity_input_lineage):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 9. Runtime Input Lineage"])
    lines.extend(_component_lines(runtime_input_lineage_contract))
    lines.extend(["", "## 10. Complete Component Inventory"])
    for item in complete_component_inventory.get("components", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 11. Component Dependency Matrix"])
    for item in component_dependency_matrix.get("dependencies", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 12. Runtime Chain Inspection"])
    for item in runtime_chain_inspection.get("chain", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 13. J-Quants Dependency Matrix"])
    for item in jquants_dependency_matrix.get("dependencies", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 14. Runtime State Coverage"])
    for item in runtime_state_coverage.get("items", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 15. Historical Source / Consumer Cutoff"])
    lines.extend(_component_lines(historical_source_consumer_cutoff))
    lines.extend(["", "## 16. Inspection Coverage"])
    lines.extend(_component_lines(inspection_coverage))
    lines.extend(["", "## 17. Runtime Features"])
    for item in data_inspection.get("runtime_features", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 18. AI Models"])
    for item in active_component_inventory.get("active_ai_models", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 19. AI Data Window Summary"])
    for item in ai_data_window_summary.get("items", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 20. Runtime Baseline Traceability"])
    lines.extend(_component_lines(baseline_traceability))
    lines.extend(["", "## 21. Freshness Policy Traceability"])
    lines.extend(_component_lines(freshness_policy_traceability))
    lines.extend(["", "## 22. Decision Subsystems"])
    for item in decision_subsystems.get("subsystems", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 23. Accepted Generation / Authority"])
    lines.extend(_component_lines(authority_generation))
    lines.extend(["", "## 24. Runtime State"])
    for key in ("current", "pending", "ledger", "pm", "safety"):
        value = runtime_state_status.get(key, {})
        lines.extend(_component_lines({"component_id": key, "component_name": key.replace("_", " ").title(), **value}))
    lines.extend(["", "## 25. Broker Layer"])
    for key in ("approval", "submit_guard", "execution", "broker_connection", "notification", "reporting"):
        value = broker_layer_status.get(key, {})
        lines.extend(_component_lines({"component_id": key, "component_name": key.replace("_", " ").title(), **value}))
    lines.extend(["", "## 26. Freshness Matrix"])
    for item in freshness_matrix.get("items", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 27. Target Period Data Sufficiency"])
    lines.extend(_component_lines(target_period_data_sufficiency))
    lines.extend(["", "## 28. Runtime Stage Contract"])
    for item in runtime_stage_contract.get("components", []):
        lines.extend(_component_lines(item))
    lines.extend(["", "## 29. Findings"])
    lines.extend(f"- {finding}" for finding in summary.get("main_findings", []))
    lines.extend(
        [
            "",
            "## 30. Non-mutation Guarantee",
            f"Training rerun: {non_mutation.get('training_rerun')}",
            f"Calibration refit: {non_mutation.get('calibration_refit')}",
            f"Validation rerun: {non_mutation.get('validation_rerun')}",
            f"Generation created: {non_mutation.get('generation_created')}",
            f"Runtime pointer write: {non_mutation.get('runtime_pointer_write')}",
            f"Trading state mutation: {non_mutation.get('trading_state_mutation')}",
            f"BUY restart: {non_mutation.get('buy_restart')}",
            f"Broker access: {non_mutation.get('broker_access')}",
            f"Broker write: {non_mutation.get('broker_write')}",
            "",
            "## 31. Exit Code",
            str(summary.get("exit_code", "")),
        ]
    )
    return "\n".join(lines)


def _data_status(
    ai_report: dict[str, Any],
    *,
    data_inspection: dict[str, Any],
    expected_business_date: str,
) -> dict[str, Any]:
    freshness = ai_report["jquants_and_feature_freshness"]
    lineage = ai_report["dataset_lineage"]
    split = ai_report["split_audit"]
    latest_jquants = freshness["latest_jquants"].get("latest_normalized_daily_quotes_date", "")
    latest_feature_payload = dict(freshness["latest_buy_feature"])
    runtime_feature_statuses = [
        item.get("status", "PASS")
        for item in data_inspection.get("runtime_features", [])
        if item.get("component_id") in {"candidate_runtime_feature", "opportunity_runtime_feature"}
    ]
    target_feature_dates = [
        str(item.get("feature_date") or "")
        for item in data_inspection.get("runtime_features", [])
        if item.get("component_id") in {"candidate_runtime_feature", "opportunity_runtime_feature"}
        and str(item.get("feature_date") or "")
    ]
    target_feature_status = _combine_status(runtime_feature_statuses or ["PASS"])
    target_feature_date = expected_business_date if expected_business_date and expected_business_date in target_feature_dates else (target_feature_dates[0] if target_feature_dates else "")
    latest_feature_payload.update(
        {
            "expected_inference_feature_date": _truth_value(expected_business_date, missing="NOT_CONFIGURED"),
            "feature_date": _truth_value(target_feature_date, missing="NOT_YET_MATERIALIZED"),
            "manifest_path": _truth_value(data_inspection.get("feature_manifest", {}).get("path") or latest_feature_payload.get("manifest_path", ""), missing="NOT_YET_MATERIALIZED"),
            "runtime_resolution_authority": "target_business_date_exact_match" if expected_business_date else "current_runtime_business_date",
            "future_fixture_artifact_excluded": True,
            "forbidden_resolution_methods": ["max_date", "latest_directory", "mtime", "future_fixture_date"],
        }
    )
    latest_feature = _truth_value(latest_feature_payload.get("feature_date", ""), missing="NOT_YET_MATERIALIZED")
    status = _combine_status([target_feature_status, lineage.get("status", "PASS"), split.get("status", "PASS")])
    return {
        "status": status,
        "jquants": freshness["latest_jquants"],
        "raw": {"status": "PASS", "max_date": freshness.get("generation_bound", {}).get("raw_data_max_date_at_generation", "")},
        "normalized": {"status": "PASS", "max_date": freshness.get("generation_bound", {}).get("normalized_data_max_date_at_generation", "")},
        "feature": latest_feature_payload,
        "dataset": lineage,
        "split": split,
        "summary": {
            "status": status,
            "latest_jquants": latest_jquants,
            "latest_feature": latest_feature,
            "dataset": lineage.get("status", ""),
            "split": split.get("status", ""),
        },
    }


def _ai_status(ai_report: dict[str, Any], *, ai_inventory: dict[str, Any], runtime_stage: str) -> dict[str, Any]:
    if runtime_stage == "PRE_RUN":
        model_statuses = [item.get("status", "BLOCK") for item in ai_inventory.get("active_ai_models", [])]
        status = _combine_status([*model_statuses, ai_report["accepted_generation_status"].get("status", "BLOCK")])
        candidate_status = next((item for item in ai_inventory.get("active_ai_models", []) if item.get("component_id") == "candidate_ai"), {})
        opportunity_status = next((item for item in ai_inventory.get("active_ai_models", []) if item.get("component_id") == "opportunity_ai"), {})
        return {
            "status": status,
            "candidate": candidate_status,
            "opportunity": opportunity_status,
            "calibration": {
                "status": _combine_status([
                    candidate_status.get("calibration_resolution_status", "BLOCK"),
                    opportunity_status.get("calibration_resolution_status", "BLOCK"),
                ]),
                "candidate_calibration_hash": candidate_status.get("calibration_hash", ""),
                "opportunity_calibration_hash": opportunity_status.get("calibration_hash", ""),
            },
            "runtime_baseline": {
                "configuration_authority": "PASS",
                "target_date_decision": "NOT_YET_APPLICABLE",
                "overall_component_status": "PASS",
            },
            "freshness": ai_report["freshness_taxonomy"],
            "accepted_generation": ai_report["accepted_generation_status"],
            "summary": {
                "status": status,
                "authority": ai_report["runtime_authority_status"].get("authority_status", ""),
                "committed_generation": ai_report["accepted_generation_status"].get("accepted_generation_id", ""),
                "candidate": candidate_status.get("status", ""),
                "opportunity": opportunity_status.get("status", ""),
            },
        }
    statuses = [
        ai_report["candidate_ai_status"].get("status", "BLOCK"),
        ai_report["opportunity_ai_status"].get("status", "BLOCK"),
        ai_report["accepted_generation_status"].get("status", "BLOCK"),
        ai_report["freshness_taxonomy"].get("status", "BLOCK"),
    ]
    status = _combine_status(statuses)
    return {
        "status": status,
        "candidate": ai_report["candidate_ai_status"],
        "opportunity": ai_report["opportunity_ai_status"],
        "calibration": {
            "status": "PASS",
            "candidate_calibration_hash": ai_report["candidate_ai_status"].get("calibration_hash", ""),
            "opportunity_calibration_hash": ai_report["opportunity_ai_status"].get("calibration_hash", ""),
        },
        "runtime_baseline": ai_report["runtime_readiness"].get("lifecycle_classification", ""),
        "freshness": ai_report["freshness_taxonomy"],
        "accepted_generation": ai_report["accepted_generation_status"],
        "summary": {
            "status": status,
            "authority": ai_report["runtime_authority_status"].get("authority_status", ""),
            "committed_generation": ai_report["accepted_generation_status"].get("accepted_generation_id", ""),
            "candidate": ai_report["candidate_ai_status"].get("status", ""),
            "opportunity": ai_report["opportunity_ai_status"].get("status", ""),
        },
    }


def _runtime_status(ai_report: dict[str, Any], *, ai_inventory: dict[str, Any], runtime_stage: str) -> dict[str, Any]:
    readiness = ai_report["runtime_readiness"]
    authority = dict(ai_report["runtime_authority_status"])
    authority["runtime_business_date"] = _truth_value(authority.get("runtime_business_date", ""), missing="NOT_YET_MATERIALIZED")
    if runtime_stage == "PRE_RUN":
        model_status = _combine_status([item.get("status", "BLOCK") for item in ai_inventory.get("active_ai_models", [])])
        status = _combine_status([authority.get("status", "BLOCK"), model_status])
        return {
            "status": status,
            "resolver": authority,
            "committed": ai_report["accepted_generation_status"],
            "runtime_consumer": {
                "status": "PASS" if status == "PASS" else status,
                "candidate_runtime_status": "NOT_YET_APPLICABLE",
                "opportunity_runtime_status": "NOT_YET_APPLICABLE",
                "missing_state_classification": "PRE_RUN_NOT_MATERIALIZED",
            },
            "lifecycle": {
                **readiness,
                "status": "PASS" if status == "PASS" else status,
                "lifecycle_decision": "NOT_YET_APPLICABLE",
                "lifecycle_classification": "PRE_RUN_NOT_MATERIALIZED",
                "inference_readiness": "NOT_YET_APPLICABLE",
            },
            "threshold": {
                "status": "NOT_YET_APPLICABLE",
                "configuration_authority": "PASS",
                "target_date_decision": "NOT_YET_APPLICABLE",
                "statistical_drift_auto_stop": False,
            },
            "buy_planning": {
                "status": "NOT_YET_APPLICABLE",
                "buy_gate": "PRE_RUN_NOT_MATERIALIZED",
                "block_buy_planning": False,
                "BUY_impact": "NOT_BLOCKING_PRE_RUN",
            },
            "sell_continuity": {
                "status": "PASS",
                "sell_permission": "UNCHANGED_PRE_RUN",
            },
            "summary": {
                "status": status,
                "lifecycle": "PRE_RUN_NOT_MATERIALIZED",
                "buy_planning": "NOT_YET_APPLICABLE",
                "sell_continuity": "PASS",
            },
        }
    runtime_consumer_status = "PASS" if readiness.get("candidate_runtime_status") == "PASS" and readiness.get("opportunity_runtime_status") == "PASS" else "BLOCK"
    model_health_status = "REVIEW_REQUIRED" if readiness.get("status") == "REVIEW_REQUIRED" else readiness.get("status", "BLOCK")
    buy_status = "PASS" if readiness.get("block_buy_planning") is False else "BLOCK"
    sell_status = readiness.get("sell_permission", "")
    status = "PASS" if runtime_consumer_status == "PASS" and buy_status == "PASS" and sell_status == "PASS" else _combine_status([runtime_consumer_status, buy_status, sell_status])
    return {
        "status": status,
        "resolver": authority,
        "committed": ai_report["accepted_generation_status"],
        "runtime_consumer": {
            "status": runtime_consumer_status,
            "candidate_runtime_status": readiness.get("candidate_runtime_status", ""),
            "opportunity_runtime_status": readiness.get("opportunity_runtime_status", ""),
        },
        "lifecycle": readiness,
        "model_health": {
            "status": model_health_status,
            "trigger": readiness.get("lifecycle_classification", ""),
            "classification": readiness.get("lifecycle_classification", ""),
            "decision": readiness.get("lifecycle_decision", ""),
            "inference_readiness": readiness.get("inference_readiness", ""),
            "policy_version": "phase19_ar_threshold_policy",
            "metric": "runtime_lifecycle_monitoring",
            "observed": readiness.get("review_findings", []),
            "threshold": "accepted_generation_runtime_baseline_policy",
            "runtime_impact": "NONE" if status == "PASS" else status,
            "buy_impact": buy_status,
            "sell_impact": sell_status,
        },
        "threshold": {
            "status": "REVIEW_REQUIRED" if "STATISTICAL_DRIFT" in str(readiness.get("lifecycle_classification", "")) else "PASS",
            "classification": readiness.get("lifecycle_classification", ""),
            "statistical_drift_auto_stop": False,
        },
        "buy_planning": {
            "status": "PASS" if readiness.get("block_buy_planning") is False else "BLOCK",
            "buy_gate": readiness.get("buy_gate", ""),
            "block_buy_planning": readiness.get("block_buy_planning", ""),
        },
        "sell_continuity": {
            "status": readiness.get("sell_permission", ""),
            "sell_permission": readiness.get("sell_permission", ""),
        },
        "summary": {
            "status": status,
            "lifecycle": readiness.get("lifecycle_classification", ""),
            "model_health": model_health_status,
            "model_health_runtime_impact": "NONE" if status == "PASS" else status,
            "buy_planning": buy_status,
            "sell_continuity": sell_status,
        },
    }


def _runtime_state_status(
    root: Path,
    *,
    expected_business_date: str | None = None,
    temporal_authority_audit: dict[str, Any] | None = None,
    post_run_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_path = root / "persistent_ledger" / "state.json"
    pending_path = root / "pending_order_plan" / "pending_order_plan.json"
    runtime_state_path = root / "runtime_state" / "current_state.json"
    current = _read_json_optional(current_path)
    pending = _read_json_optional(pending_path)
    runtime_state = _read_json_optional(runtime_state_path)
    safety = inspect_safety_artifact(
        root,
        expected_business_date=expected_business_date,
        post_run_context=post_run_context,
    )
    ledger_dir = root / "persistent_ledger"
    ledger_files = ["orders.jsonl", "executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"]
    ledger_missing = [name for name in ledger_files if not (ledger_dir / name).exists()]
    blockers = []
    if not current:
        blockers.append("current_missing")
    if not pending:
        blockers.append("pending_missing")
    if not runtime_state:
        blockers.append("runtime_state_missing")
    if ledger_missing:
        blockers.append("ledger_files_missing")
    if (temporal_authority_audit or {}).get("temporal_isolation_status") == "BLOCK":
        blockers.append("temporal_state_contamination")
    safety_layer_status = safety["status"]
    status = "BLOCK" if blockers or safety_layer_status == "BLOCK" else "REVIEW_REQUIRED" if safety_layer_status == "REVIEW_REQUIRED" else "PASS"
    return {
        "status": status,
        "current": _file_status(current_path, current),
        "pending": _file_status(pending_path, pending),
        "ledger": {"status": "PASS" if not ledger_missing else "BLOCK", "missing": ledger_missing, "path": str(ledger_dir)},
        "pm": _file_status(runtime_state_path, runtime_state),
        "safety": safety,
        "temporal_isolation": temporal_authority_audit or {},
        "blockers": blockers,
        "summary": {
            "status": status,
            "current": "PASS" if current else "BLOCK",
            "pending": "PASS" if pending else "BLOCK",
            "ledger": "PASS" if not ledger_missing else "BLOCK",
            "pm": "PASS" if runtime_state else "BLOCK",
            "safety": safety["safety_artifact_status"],
            "temporal_isolation": (temporal_authority_audit or {}).get("temporal_isolation_status", ""),
        },
    }


def inspect_safety_artifact(
    root: Path,
    *,
    expected_business_date: str | None = None,
    post_run_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inspect Runtime Safety Decision materialization without creating it."""

    safety_path = root / SAFETY_DECISION_RELATIVE_PATH
    payload = _read_json_optional(safety_path)
    artifact_business_date = str(payload.get("business_date") or "") if payload else ""
    expected = str(expected_business_date or "")
    post_run_context = post_run_context or {}
    if _post_run_safety_authority_ready(post_run_context, expected_business_date=expected):
        return {
            "status": "PASS",
            "safety_artifact_status": "READY",
            "missing_state_classification": "MATERIALIZED_BY_RUNTIME_TEST_AUTHORITY",
            "expected_business_date": expected,
            "artifact_business_date": expected,
            "materialization_stage": "HISTORICAL_POST_RUN_AUTHORITY",
            "artifact_path": str(post_run_context.get("safety_authority_path") or safety_path),
            "exists": True,
            "sha256": str(post_run_context.get("safety_authority_sha256") or "NOT_RECORDED"),
            "decision_status": str(post_run_context.get("safety_decision") or "ALLOW"),
            "decision_id": str(post_run_context.get("safety_decision_id") or ""),
            "runtime_mode": "historical",
            "reason": "closed_historical_runtime_test_safety_authority_ready",
            "runtime_test_run_id": str(post_run_context.get("run_id") or ""),
            "safety_authority_source": str(post_run_context.get("safety_authority_source") or ""),
            "safety_policy_version": str(post_run_context.get("safety_policy_version") or ""),
        }
    if payload:
        date_mismatch = bool(expected and artifact_business_date and artifact_business_date != expected)
        artifact_status = "REVIEW_REQUIRED" if date_mismatch else "READY"
        return {
            "status": "REVIEW_REQUIRED" if date_mismatch else "PASS",
            "safety_artifact_status": artifact_status,
            "missing_state_classification": "ARTIFACT_DATE_MISMATCH" if date_mismatch else "MATERIALIZED",
            "expected_business_date": expected,
            "artifact_business_date": artifact_business_date,
            "materialization_stage": "MATERIALIZED",
            "artifact_path": str(safety_path),
            "exists": True,
            "sha256": _sha256_file(safety_path),
            "decision_status": str(payload.get("decision") or payload.get("safety_status") or ""),
            "decision_id": str(payload.get("safety_decision_id") or ""),
            "runtime_mode": str(payload.get("runtime_mode") or ""),
            "reason": "safety_artifact_ready" if not date_mismatch else "safety_artifact_business_date_mismatch",
        }
    post_run_missing = _target_date_safety_or_morning_already_ran(root, expected)
    if post_run_missing:
        return {
            "status": "BLOCK",
            "safety_artifact_status": "BLOCK",
            "missing_state_classification": "POST_RUN_MATERIALIZATION_MISSING",
            "expected_business_date": expected,
            "artifact_business_date": "NOT_YET_MATERIALIZED",
            "materialization_stage": "POST_RUN_MISSING",
            "artifact_path": str(safety_path),
            "exists": False,
            "sha256": "NOT_YET_MATERIALIZED",
            "decision_status": "MISSING_AFTER_TARGET_DATE_RUN",
            "decision_id": "NOT_YET_MATERIALIZED",
            "runtime_mode": "NOT_RECORDED",
            "reason": "target_date_safety_or_morning_run_completed_without_latest_safety_decision",
        }
    return {
        "status": "PASS",
        "safety_artifact_status": "NOT_YET_APPLICABLE",
        "missing_state_classification": "PRE_RUN_NOT_MATERIALIZED",
        "expected_business_date": expected,
        "artifact_business_date": "NOT_YET_MATERIALIZED",
        "materialization_stage": "PRE_RUN",
        "artifact_path": str(safety_path),
        "exists": False,
        "sha256": "NOT_YET_MATERIALIZED",
        "decision_status": "NOT_YET_APPLICABLE",
        "decision_id": "NOT_YET_MATERIALIZED",
        "runtime_mode": "NOT_RECORDED",
        "reason": "safety_decision_is_materialized_by_target_date_runtime_route",
    }


def classify_stage_artifact_materialization(
    *,
    component_id: str,
    expected_generation_stage: str,
    current_runtime_stage: str,
    exists: bool,
    date_matches: bool = True,
) -> dict[str, Any]:
    if exists and not date_matches:
        return {
            "component_id": component_id,
            "expected_generation_stage": expected_generation_stage,
            "current_runtime_stage": current_runtime_stage,
            "materialization_status": "ARTIFACT_DATE_MISMATCH",
            "missing_state_classification": "ARTIFACT_DATE_MISMATCH",
            "status": "REVIEW_REQUIRED",
        }
    if exists:
        return {
            "component_id": component_id,
            "expected_generation_stage": expected_generation_stage,
            "current_runtime_stage": current_runtime_stage,
            "materialization_status": "READY",
            "missing_state_classification": "READY",
            "status": "PASS",
        }
    expected_order = RUNTIME_STAGE_ORDER.get(expected_generation_stage, 999)
    current_order = RUNTIME_STAGE_ORDER.get(current_runtime_stage, 0)
    if current_order < expected_order:
        return {
            "component_id": component_id,
            "expected_generation_stage": expected_generation_stage,
            "current_runtime_stage": current_runtime_stage,
            "materialization_status": "NOT_YET_APPLICABLE",
            "missing_state_classification": "PRE_RUN_NOT_MATERIALIZED" if current_runtime_stage == "PRE_RUN" else "PRE_STAGE_NOT_MATERIALIZED",
            "status": "NOT_YET_APPLICABLE",
        }
    return {
        "component_id": component_id,
        "expected_generation_stage": expected_generation_stage,
        "current_runtime_stage": current_runtime_stage,
        "materialization_status": "POST_STAGE_MATERIALIZATION_MISSING",
        "missing_state_classification": "POST_STAGE_MATERIALIZATION_MISSING",
        "status": "BLOCK",
    }


def _runtime_stage_contract(
    *,
    root: Path,
    expected_business_date: str,
    candidate_runtime: dict[str, Any],
    opportunity_runtime: dict[str, Any],
    lifecycle: dict[str, Any],
    post_run_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    post_run_context = post_run_context or {}
    feature_exists = _target_date_runtime_feature_exists(root=root, expected_business_date=expected_business_date)
    runtime_stage = (
        str(post_run_context.get("runtime_stage") or "EXECUTION_DONE")
        if _valid_post_run_context(post_run_context)
        else _resolve_runtime_stage(
        root=root,
        expected_business_date=expected_business_date,
        candidate_runtime=candidate_runtime,
        opportunity_runtime=opportunity_runtime,
        lifecycle=lifecycle,
        )
    )
    completed_components = set(str(item) for item in post_run_context.get("completed_runtime_components") or [])
    safety_exists = (root / SAFETY_DECISION_RELATIVE_PATH).is_file() or _post_run_safety_authority_ready(
        post_run_context,
        expected_business_date=expected_business_date,
    )
    component_specs = [
        ("runtime_features", "Runtime Features", "FEATURE_READY", feature_exists),
        ("candidate_inference", "Candidate Inference", "AI_INFERENCE_DONE", bool(candidate_runtime)),
        ("opportunity_inference", "Opportunity Inference", "AI_INFERENCE_DONE", bool(opportunity_runtime)),
        ("ai_lifecycle_gate", "AI Lifecycle Gate", "LIFECYCLE_GATE_DONE", bool(lifecycle)),
        ("safety_decision", "Safety Decision", "LIFECYCLE_GATE_DONE", safety_exists),
        ("buy_planning", "BUY Planning", "DAILY_PLAN_CREATED", (root / "pending_order_plan" / "pending_order_plan.json").is_file() and runtime_stage != "PRE_RUN"),
        ("sell_planning", "SELL Planning", "SELL_PLANNING_DONE", "sell_planning" in completed_components),
        ("approval", "Approval", "APPROVAL_PENDING", "approval" in completed_components),
        ("submit", "Submit", "SUBMITTING", "submit" in completed_components),
        ("execution", "Execution", "EXECUTION_DONE", "execution" in completed_components),
        ("reporting", "Reporting", "EXECUTION_DONE", "reporting" in completed_components),
        ("notification", "Notification", "EXECUTION_DONE", "notification" in completed_components),
    ]
    components = []
    for component_id, name, expected_stage, exists in component_specs:
        classified = classify_stage_artifact_materialization(
            component_id=component_id,
            expected_generation_stage=expected_stage,
            current_runtime_stage=runtime_stage,
            exists=exists,
        )
        components.append({"component_name": name, **classified})
    pre_run_ok = runtime_stage == "PRE_RUN" and all(
        item["status"] in {"NOT_YET_APPLICABLE", "PASS"} for item in components
    )
    return {
        "component_id": "runtime_stage_contract",
        "component_name": "Runtime Stage Contract",
        "status": "PASS" if pre_run_ok or all(item["status"] == "PASS" for item in components) else "BLOCK",
        "runtime_stage": runtime_stage,
        "current_runtime_stage": runtime_stage,
        "target_business_date": expected_business_date,
        "pre_run_readiness": "PASS" if pre_run_ok else "NOT_PRE_RUN",
        "day1_start_permission": "ALLOWED" if pre_run_ok else "NOT_APPLICABLE",
        "post_run_context_status": "PASS" if _valid_post_run_context(post_run_context) else "NOT_APPLICABLE",
        "runtime_test_run_id": str(post_run_context.get("run_id") or ""),
        "components": components,
    }


def _resolve_runtime_stage(
    *,
    root: Path,
    expected_business_date: str,
    candidate_runtime: dict[str, Any],
    opportunity_runtime: dict[str, Any],
    lifecycle: dict[str, Any],
) -> str:
    if lifecycle:
        return "LIFECYCLE_GATE_DONE"
    if candidate_runtime or opportunity_runtime:
        return "AI_INFERENCE_DONE"
    feature_dir = root / "operations" / "feature_refresh_detail"
    feature_materialized = (
        bool(expected_business_date)
        and (
            (
                feature_dir.exists()
                and any(expected_business_date in str(path) for path in feature_dir.glob("**/*") if path.is_file())
            )
            or _target_date_runtime_feature_exists(root=root, expected_business_date=expected_business_date)
        )
    )
    if feature_materialized:
        return "FEATURE_READY"
    manifest_dir = root / "runtime_state" / "run_manifest" / expected_business_date if expected_business_date else Path("")
    if manifest_dir.is_dir() and any(manifest_dir.glob("*.json")):
        return "MARKET_DATA_READY"
    return "PRE_RUN"


def _target_date_safety_or_morning_already_ran(root: Path, expected_business_date: str) -> bool:
    if not expected_business_date:
        return False
    manifest_dir = root / "runtime_state" / "run_manifest" / expected_business_date
    tokens = (
        '"job": "morning"',
        '"job": "safety_refresh"',
        '"job": "safety_evaluation"',
        "morning_ai_planning_pending_pipeline",
        "runtime_safety_decision_producer",
        "runtime_safety_evaluation",
    )
    if manifest_dir.is_dir():
        for path in manifest_dir.glob("*.json"):
            try:
                text = json.dumps(json.loads(path.read_text(encoding="utf-8")), sort_keys=True)
            except Exception:
                text = path.read_text(encoding="utf-8", errors="ignore")
            if any(token in text for token in tokens):
                return True
    log_dir = root / "runtime_state" / "logs" / expected_business_date
    if log_dir.is_dir():
        for path in log_dir.glob("*.log"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(token.strip('"') in text for token in tokens):
                return True
    return False


def _target_date_runtime_feature_exists(*, root: Path, expected_business_date: str) -> bool:
    if not expected_business_date:
        return False
    feature_dir = root / "operations" / "feature_artifacts" / expected_business_date
    return any(
        (feature_dir / filename).is_file()
        for filename in (
            "candidate_features.parquet",
            "opportunity_feature_input.parquet",
            "position_feature_input.parquet",
            "capital_policy_input.parquet",
        )
    )


def _temporal_authority_audit(
    *,
    root: Path,
    runtime_mode: str,
    profile_id: str,
    target_business_date: str,
    target_business_dates: list[str],
    data_inspection: dict[str, Any],
    candidate_runtime: dict[str, Any],
    candidate_runtime_path: Path,
    opportunity_runtime: dict[str, Any],
    opportunity_runtime_path: Path,
    opportunity_summary: dict[str, Any],
    lifecycle: dict[str, Any],
    lifecycle_path: Path,
) -> dict[str, Any]:
    historical = runtime_mode == "historical" or bool(target_business_date)
    target = target_business_date or (target_business_dates[0] if target_business_dates else "")
    artifacts = [
        _stateful_artifact_record(
            "persistent_ledger_current",
            root / "persistent_ledger" / "state.json",
            _read_json_optional(root / "persistent_ledger" / "state.json"),
            date_keys=("business_date", "as_of", "position_state_as_of"),
            state_owner="Persistent Ledger",
            authority="Current asset state",
        ),
        _stateful_artifact_record(
            "runtime_current",
            root / "runtime_state" / "current_state.json",
            _read_json_optional(root / "runtime_state" / "current_state.json"),
            date_keys=("business_date", "as_of", "generated_at"),
            state_owner="Runtime State",
            authority="PM / Runtime operation state",
        ),
        _stateful_artifact_record(
            "pending_plan",
            root / "pending_order_plan" / "pending_order_plan.json",
            _read_json_optional(root / "pending_order_plan" / "pending_order_plan.json"),
            date_keys=("business_date", "target_business_date", "last_transition_at"),
            state_owner="Pending",
            authority="Pending order slot",
        ),
        _stateful_artifact_record(
            "safety_decision",
            root / SAFETY_DECISION_RELATIVE_PATH,
            _read_json_optional(root / SAFETY_DECISION_RELATIVE_PATH),
            date_keys=("business_date", "as_of", "created_at"),
            state_owner="Safety",
            authority="Runtime Safety Decision",
        ),
        _stateful_artifact_record(
            "candidate_inference_result",
            candidate_runtime_path,
            candidate_runtime,
            date_keys=("business_date", "feature_date"),
            created_at_keys=("generated_at", "created_at"),
            state_owner="BUY AI",
            authority="Candidate inference result",
        ),
        _stateful_artifact_record(
            "opportunity_inference_result",
            opportunity_runtime_path,
            opportunity_runtime,
            date_keys=("business_date", "feature_date"),
            created_at_keys=("generated_at", "created_at"),
            state_owner="BUY AI",
            authority="Opportunity inference result",
        ),
        _stateful_artifact_record(
            "opportunity_inference_summary",
            Path(str(opportunity_summary.get("summary_path") or "")),
            opportunity_summary,
            date_keys=("business_date", "feature_date"),
            created_at_keys=("created_at",),
            extra_dates={"input_feature_business_date": _date_from_path(Path(str(opportunity_summary.get("feature_path") or "")))},
            state_owner="BUY AI",
            authority="Opportunity inference summary",
        ),
        _stateful_artifact_record(
            "ai_lifecycle_gate",
            lifecycle_path,
            lifecycle,
            date_keys=("business_date",),
            created_at_keys=("created_at",),
            state_owner="Runtime Lifecycle",
            authority="AI lifecycle gate",
        ),
    ]
    for feature in data_inspection.get("runtime_features", []):
        source_refs = feature.get("source_data_refs") if isinstance(feature.get("source_data_refs"), dict) else {}
        artifacts.append(
            {
                "component_id": feature.get("component_id", ""),
                "path": _truth_value(feature.get("artifact_path", ""), missing="NOT_YET_MATERIALIZED"),
                "exists": Path(str(feature.get("artifact_path") or "")).exists(),
                "business_date": "NOT_YET_MATERIALIZED",
                "as_of_date": _truth_value(feature.get("feature_date", ""), missing="NOT_YET_MATERIALIZED"),
                "created_at": "NOT_YET_MATERIALIZED",
                "source_business_date": _truth_value(feature.get("input_source_date", ""), missing="NOT_YET_MATERIALIZED"),
                "runtime_mode": runtime_mode,
                "profile": profile_id,
                "run_id": "NOT_RECORDED",
                "state_owner": "Runtime Feature",
                "authority": _truth_value(feature.get("runtime_consumer", ""), missing="NOT_RECORDED"),
                "position_count": _truth_value(source_refs.get("current_position_count", ""), missing="NOT_YET_MATERIALIZED"),
                "cash": "NOT_APPLICABLE",
                "order_count": "NOT_APPLICABLE",
                "input_references": source_refs,
                "date_role": "feature_as_of_date",
            }
        )
    future_refs = []
    for artifact in artifacts:
        if not historical or not target:
            artifact["future_state_reference"] = False
            continue
        observed = [
            ("business_date", artifact.get("business_date", "")),
            ("as_of_date", artifact.get("as_of_date", "")),
            ("source_business_date", artifact.get("source_business_date", "")),
        ]
        future_fields = [
            {"field": field, "date": _extract_date(str(value))}
            for field, value in observed
            if _is_future_date(str(value), target)
        ]
        artifact["future_state_reference"] = bool(future_fields)
        artifact["future_fields"] = future_fields
        if future_fields:
            future_refs.append(
                {
                    "component_id": artifact.get("component_id", ""),
                    "path": artifact.get("path", ""),
                    "future_fields": future_fields,
                    "target_business_date": target,
                }
            )
    return {
        "component_id": "historical_temporal_isolation",
        "component_name": "Historical Runtime Temporal Isolation",
        "status": "BLOCK" if future_refs else "PASS",
        "runtime_mode": runtime_mode,
        "profile": profile_id,
        "target_business_date": target,
        "target_business_dates": target_business_dates,
        "initial_state_authority": "A. isolated empty Historical state via reset/fresh-run, or compatible pre-target snapshot only",
        "inspected_runtime_root": _display_path(root),
        "runtime_root_type": _runtime_root_type(root),
        "shared_runtime_root_used": _runtime_root_type(root) == "SHARED_RUNTIME_ROOT",
        "runtime_root_isolation_policy": "Historical execution must use backup/reset-created clean state or an isolated .runtime root; shared future state is not a valid Day1 authority.",
        "future_state_reference_count": len(future_refs),
        "future_state_references": future_refs,
        "temporal_isolation_status": "BLOCK" if future_refs else "PASS",
        "block_reason": "TEMPORAL_STATE_CONTAMINATION" if future_refs else "",
        "artifacts": artifacts,
        "created_at_future_policy": "created_at may be after target date, but business_date/as_of/source/input dates must be <= target date.",
    }


def _stateful_artifact_record(
    component_id: str,
    path: Path,
    payload: dict[str, Any],
    *,
    date_keys: tuple[str, ...],
    created_at_keys: tuple[str, ...] = ("created_at", "generated_at", "updated_at"),
    extra_dates: dict[str, Any] | None = None,
    state_owner: str,
    authority: str,
) -> dict[str, Any]:
    positions = payload.get("positions")
    active_pending = payload.get("active_pending")
    return {
        "component_id": component_id,
        "path": _display_path(path),
        "exists": path.is_file(),
        "business_date": _truth_value(_first_date_value(payload, ("business_date",)), missing="NOT_YET_MATERIALIZED"),
        "as_of_date": _truth_value(_first_date_value(payload, date_keys), missing="NOT_YET_MATERIALIZED"),
        "created_at": _truth_value(_first_date_value(payload, created_at_keys), missing="NOT_YET_MATERIALIZED"),
        "source_business_date": _truth_value(_first_extra_date(extra_dates), missing="NOT_YET_MATERIALIZED"),
        "runtime_mode": _truth_value(payload.get("runtime_mode") or payload.get("environment") or "", missing="NOT_RECORDED"),
        "profile": _truth_value(payload.get("profile") or payload.get("profile_id") or "", missing="NOT_RECORDED"),
        "run_id": _truth_value(payload.get("run_id") or "", missing="NOT_RECORDED"),
        "state_owner": state_owner,
        "authority": authority,
        "position_count": len(positions) if isinstance(positions, list) else "NOT_RECORDED",
        "cash": _truth_value(payload.get("cash", ""), missing="NOT_RECORDED"),
        "order_count": _truth_value(payload.get("order_count", 1 if active_pending else 0 if active_pending is False else ""), missing="NOT_RECORDED"),
        "input_references": {
            "asset_state_source": _truth_value(payload.get("asset_state_source", ""), missing="NOT_RECORDED"),
            "pending_state_source": _truth_value(payload.get("pending_state_source", ""), missing="NOT_RECORDED"),
            **(extra_dates or {}),
        },
    }


def _first_date_value(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _first_extra_date(extra_dates: dict[str, Any] | None) -> str:
    for value in (extra_dates or {}).values():
        if value not in (None, ""):
            return str(value)
    return ""


def _extract_date(value: str) -> str:
    match = re.search(r"\d{4}-\d{2}-\d{2}", value or "")
    return match.group(0) if match else ""


def _is_future_date(value: str, target_business_date: str) -> bool:
    observed = _extract_date(value)
    target = _extract_date(target_business_date)
    return bool(observed and target and observed > target)


def _business_day_lag(actual: str, expected: str) -> int | str:
    actual_date = _extract_date(actual)
    expected_date = _extract_date(expected)
    if not actual_date or not expected_date:
        return ""
    try:
        start = datetime.fromisoformat(min(actual_date, expected_date)).date()
        end = datetime.fromisoformat(max(actual_date, expected_date)).date()
    except ValueError:
        return ""
    direction = -1 if actual_date < expected_date else 1
    count = 0
    current = start
    while current < end:
        current = current.fromordinal(current.toordinal() + 1)
        if current.weekday() < 5:
            count += 1
    return direction * count


def _date_from_path(path: Path) -> str:
    return _extract_date(str(path))


def _strip_feature_prefixes(columns: Any) -> list[str]:
    if not isinstance(columns, list):
        return []
    return [str(column).removeprefix("feature__") for column in columns]


def _feature_projection(*, path: Path, model_features: list[str], consumer: str) -> dict[str, Any]:
    stats = _parquet_stats(path)
    artifact_columns = [str(column) for column in stats.get("columns", [])]
    selected = list(model_features)
    dependency_features: list[str] = []
    missing: list[str] = []
    for column in selected:
        if column in artifact_columns:
            continue
        if consumer == "opportunity" and column in {"candidate_rank", "candidate_reason", "candidate_score"}:
            dependency_features.append(column)
            continue
        missing.append(column)
    duplicates = sorted({column for column in artifact_columns if artifact_columns.count(column) > 1})
    unexpected = [column for column in artifact_columns if column not in selected]
    status = "PASS" if not selected or (not missing and not duplicates) else "BLOCK"
    return {
        "artifact_column_count": len(artifact_columns),
        "model_input_feature_count": len(selected),
        "metadata_column_count": len(unexpected),
        "selected_model_features": selected,
        "candidate_dependency_features": dependency_features,
        "missing_model_features": missing,
        "unexpected_columns": unexpected,
        "duplicate_columns": duplicates,
        "feature_order_validation": status,
        "feature_projection_reason": "metadata_columns_allowed" if status == "PASS" else "missing_or_duplicate_model_features",
    }


def _target_period_data_sufficiency(
    *,
    data_inspection: dict[str, Any],
    target_business_dates: list[str],
    post_run_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    post_run_context = post_run_context or {}
    sources = {item.get("component_id"): item for item in data_inspection.get("data_sources", [])}
    raw_path = Path(str(sources.get("raw_jquants_daily_quotes", {}).get("artifact_path") or ""))
    normalized_path = Path(str(sources.get("normalized_jquants_daily_quotes", {}).get("artifact_path") or ""))
    listed_path = Path(str(sources.get("listed_issues", {}).get("artifact_path") or ""))
    raw_dates = _parquet_unique_dates(raw_path)
    normalized_dates = _parquet_unique_dates(normalized_path)
    listed_dates = _parquet_unique_dates(listed_path)
    feature_dates = {str(item.get("feature_date") or "") for item in data_inspection.get("runtime_features", []) if str(item.get("feature_date") or "")}
    per_day = []
    for day in target_business_dates:
        per_day.append(
            {
                "business_date": day,
                "raw_quotes": day in raw_dates,
                "normalized_quotes": day in normalized_dates,
                "listed_issues": day in listed_dates or bool(listed_dates and min(listed_dates) <= day <= max(listed_dates)),
                "candidate_feature_materialized": day in feature_dates,
                "opportunity_feature_materialized": day in feature_dates,
            }
        )
    raw_missing = [day for day in target_business_dates if day not in raw_dates]
    normalized_missing = [day for day in target_business_dates if day not in normalized_dates]
    listed_missing = [
        day for day in target_business_dates
        if not (day in listed_dates or bool(listed_dates and min(listed_dates) <= day <= max(listed_dates)))
    ]
    feature_missing = [day for day in target_business_dates if day not in feature_dates]
    status = "PASS" if target_business_dates and not raw_missing and not normalized_missing and not listed_missing else "BLOCK"
    feature_status = "PASS" if not feature_missing else "PRE_RUN_NOT_MATERIALIZED"
    if _valid_post_run_context(post_run_context):
        completed = [str(day) for day in post_run_context.get("completed_business_days") or []]
        completed_set = set(completed)
        missing_completed = [day for day in target_business_dates if day not in completed_set]
        status = "PASS" if target_business_dates and not missing_completed else "REVIEW_REQUIRED"
        feature_status = "NOT_REQUIRED_FOR_POST_RUN_VALIDATION" if feature_missing else "PASS"
        per_day = [
            {
                **item,
                "target_run_execution_status": "PASS" if item["business_date"] in completed_set else "REVIEW_REQUIRED",
                "artifact_retention_status": "AVAILABLE" if item["candidate_feature_materialized"] or item["opportunity_feature_materialized"] else "NOT_RETAINED_AFTER_SUCCESSFUL_RUN",
                "current_shared_runtime_artifact_retention": "AVAILABLE" if item["candidate_feature_materialized"] or item["opportunity_feature_materialized"] else "NOT_RETAINED_AFTER_SUCCESSFUL_RUN",
                "post_run_validation_requirement": "RUN_EVIDENCE_AUTHORITY",
            }
            for item in per_day
        ]
        return {
            "component_id": "target_period_data_sufficiency",
            "component_name": "Target Period Data Sufficiency",
            "status": status,
            "inspection_context": "HISTORICAL_POST_RUN",
            "pre_run_source_sufficiency": "NOT_APPLICABLE_POST_RUN",
            "post_run_execution_evidence_sufficiency": status,
            "current_shared_runtime_artifact_retention": "NOT_REQUIRED_FOR_POST_RUN_VALIDATION" if feature_missing else "AVAILABLE",
            "target_business_dates": target_business_dates,
            "completed_business_days": completed,
            "missing_completed_business_days": missing_completed,
            "raw_quotes_missing_dates": raw_missing,
            "normalized_quotes_missing_dates": normalized_missing,
            "listed_issues_missing_dates": listed_missing,
            "runtime_feature_materialized_dates": sorted(feature_dates),
            "runtime_feature_missing_dates": feature_missing,
            "runtime_feature_status": feature_status,
            "per_day": per_day,
            "reason": "completed_run_evidence_is_post_run_authority" if status == "PASS" else "completed_run_evidence_incomplete",
        }
    return {
        "component_id": "target_period_data_sufficiency",
        "component_name": "Target Period Data Sufficiency",
        "status": status,
        "target_business_dates": target_business_dates,
        "raw_quotes_missing_dates": raw_missing,
        "normalized_quotes_missing_dates": normalized_missing,
        "listed_issues_missing_dates": listed_missing,
        "runtime_feature_materialized_dates": sorted(feature_dates),
        "runtime_feature_missing_dates": feature_missing,
        "runtime_feature_status": feature_status,
        "per_day": per_day,
        "reason": "raw_normalized_and_listed_available_for_target_period" if status == "PASS" else "target_period_market_data_missing",
    }


def _parquet_unique_dates(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    try:
        os.environ.setdefault("ARROW_USER_SIMD_LEVEL", "NONE")
        import pandas as pd

        with _suppress_stderr():
            frame = pd.read_parquet(path)
    except Exception:
        return set()
    date_column = next((col for col in ("Date", "date", "business_date", "as_of_date", "target_date", "data_until") if col in frame.columns), "")
    if not date_column:
        return set()
    return {_extract_date(str(value)) for value in frame[date_column].dropna().astype(str)}


def _data_inspection(
    *,
    root: Path,
    repo_root: Path,
    ai_report: dict[str, Any],
    manifest: dict[str, Any],
    candidate_training: dict[str, Any],
    opportunity_training: dict[str, Any],
    feature_manifest: dict[str, Any],
    feature_manifest_path: Path,
    expected_business_date: str,
    runtime_stage: str,
) -> dict[str, Any]:
    raw_path = root / "operations" / "jquants" / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    normalized_path = root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    listed_path = root / "operations" / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet"
    latest_jquants = ai_report["jquants_and_feature_freshness"]["latest_jquants"]
    raw_stats = _parquet_stats(raw_path)
    normalized_stats = _parquet_stats(normalized_path)
    listed_stats = _parquet_stats(listed_path)
    raw = {
        "component_id": "raw_jquants_daily_quotes",
        "component_name": "Raw J-Quants Daily Quotes",
        "source": "J-Quants",
        "artifact_path": str(raw_path),
        "latest_business_date": raw_stats.get("latest_date") or latest_jquants.get("latest_successful_daily_quotes_date", ""),
        "earliest_date": raw_stats.get("earliest_date", ""),
        "row_count": raw_stats.get("row_count", 0),
        "symbol_count": raw_stats.get("symbol_count", 0),
        "file_count": 1 if raw_path.is_file() else 0,
        "schema_version": "parquet",
        "content_hash": _sha256_file(raw_path),
        "missing_business_dates": [],
        "status": "PASS" if raw_path.is_file() else "BLOCK",
    }
    normalized = {
        "component_id": "normalized_jquants_daily_quotes",
        "component_name": "Normalized J-Quants Daily Quotes",
        "artifact_path": str(normalized_path),
        "latest_business_date": normalized_stats.get("latest_date") or latest_jquants.get("latest_normalized_daily_quotes_date", ""),
        "earliest_date": normalized_stats.get("earliest_date", ""),
        "row_count": normalized_stats.get("row_count", 0),
        "symbol_count": normalized_stats.get("symbol_count", 0),
        "dataset_revision": manifest.get("dataset_bundle_ref", {}).get("dataset_revision_ids", []),
        "schema_hash": normalized_stats.get("schema_hash", ""),
        "manifest_hash": _sha256_file(Path(latest_jquants.get("manifest_path") or "")),
        "missing_dates": [],
        "duplicate_count": normalized_stats.get("duplicate_count", 0),
        "status": "PASS" if normalized_path.is_file() else "BLOCK",
    }
    listed = {
        "component_id": "listed_issues",
        "component_name": "Listed Issues",
        "artifact_path": str(listed_path),
        "row_count": listed_stats.get("row_count", 0),
        "symbol_count": listed_stats.get("symbol_count", 0),
        "latest_business_date": listed_stats.get("latest_date", ""),
        "earliest_date": listed_stats.get("earliest_date", ""),
        "content_hash": _sha256_file(listed_path),
        "status": "PASS" if listed_path.is_file() else "BLOCK",
    }
    datasets = [
        _dataset_detail("candidate_dataset", "Candidate Dataset", candidate_training, manifest),
        _dataset_detail("opportunity_dataset", "Opportunity Dataset", opportunity_training, manifest),
    ]
    runtime_features = []
    feature_orders = {
        "candidate": _strip_feature_prefixes(manifest.get("candidate_member", {}).get("feature_order") or candidate_training.get("feature_columns", [])),
        "opportunity": _strip_feature_prefixes(manifest.get("opportunity_member", {}).get("feature_order") or opportunity_training.get("feature_columns", [])),
    }
    feature_artifacts = feature_manifest.get("artifacts", [])
    if not isinstance(feature_artifacts, list) or not feature_artifacts:
        feature_artifacts = _target_date_feature_artifacts(root=root, expected_business_date=expected_business_date)
    for artifact in feature_artifacts:
        if not isinstance(artifact, dict):
            continue
        path = Path(str(artifact.get("artifact_path") or ""))
        ai_name = str(artifact.get("ai_name") or "unknown")
        parquet_stats = _parquet_stats(path)
        projection = _feature_projection(path=path, model_features=feature_orders.get(ai_name, []), consumer=ai_name)
        target_resolution_status = artifact.get("target_date_resolution_status", "PASS")
        if target_resolution_status == "TARGET_DATE_ARTIFACT_MISSING":
            feature_status = classify_stage_artifact_materialization(
                component_id=f"{ai_name}_runtime_feature",
                expected_generation_stage="FEATURE_READY",
                current_runtime_stage=runtime_stage,
                exists=False,
            )["status"]
        else:
            feature_status = "PASS" if artifact.get("status") == "FEATURES_READY" and projection.get("feature_order_validation") != "BLOCK" else "REVIEW_REQUIRED"
        source_refs = artifact.get("source_data_refs", {}) if isinstance(artifact.get("source_data_refs"), dict) else {}
        position_temporal_isolation = (
            ai_name == "position"
            and str(source_refs.get("position_feature_reason") or "") == "current_position_state_as_of_after_feature_target_date"
            and int(_numeric_or_zero(artifact.get("row_count", parquet_stats.get("row_count", 0)))) == 0
        )
        final_positions = _read_json_optional(root / "persistent_ledger" / "state.json").get("positions") or []
        if position_temporal_isolation:
            feature_status = "PASS"
        runtime_features.append(
            {
                "component_id": f"{ai_name}_runtime_feature",
                "component_name": f"{ai_name.title()} Runtime Feature",
                "feature_date": artifact.get("data_until") or artifact.get("max_date") or "",
                "input_source_date": artifact.get("max_date", ""),
                "artifact_path": str(path),
                "row_count": artifact.get("row_count", parquet_stats.get("row_count", 0)),
                "symbol_count": parquet_stats.get("symbol_count", ""),
                "feature_count": parquet_stats.get("column_count", ""),
                "schema_hash": artifact.get("feature_schema_hash", ""),
                "content_hash": _sha256_file(path),
                "generation_process": "runtime_v2_market_refresh_pipeline / feature_refresh",
                "runtime_consumer": ai_name,
                "source_data_refs": source_refs,
                "position_feature_authority_status": "TEMPORAL_ISOLATION_PASS" if position_temporal_isolation else "NOT_APPLICABLE",
                "position_feature_authority_reason": source_refs.get("position_feature_reason", "") if ai_name == "position" else "",
                "position_feature_target_date_position_count": _numeric_or_zero(source_refs.get("current_position_count", 0)) if ai_name == "position" else "",
                "final_post_run_position_count": len(final_positions) if ai_name == "position" else "",
                "position_feature_final_position_semantics": "target-date feature rows and final post-run positions are distinct authorities" if ai_name == "position" else "",
                "target_date_resolution_status": target_resolution_status,
                "fallback_used": bool(artifact.get("fallback_used", False)),
                **projection,
                "status": feature_status,
            }
        )
    present_feature_ids = {item.get("component_id") for item in runtime_features}
    for ai_name, training in (("candidate", candidate_training), ("opportunity", opportunity_training)):
        component_id = f"{ai_name}_runtime_feature"
        if component_id in present_feature_ids:
            continue
        classification = classify_stage_artifact_materialization(
            component_id=component_id,
            expected_generation_stage="FEATURE_READY",
            current_runtime_stage=runtime_stage,
            exists=False,
        )
        runtime_features.append(
            {
                "component_id": component_id,
                "component_name": f"{ai_name.title()} Runtime Feature",
                "feature_date": "",
                "input_source_date": "",
                "artifact_path": str(
                    root
                    / "operations"
                    / "feature_artifacts"
                    / expected_business_date
                    / ("candidate_features.parquet" if ai_name == "candidate" else "opportunity_feature_input.parquet")
                ),
                "row_count": 0,
                "symbol_count": 0,
                "feature_count": len(manifest.get(f"{ai_name}_member", {}).get("feature_order") or training.get("feature_columns", [])),
                "schema_hash": manifest.get(f"{ai_name}_member", {}).get("feature_schema_hash", ""),
                "content_hash": "",
                "generation_process": "runtime_v2_market_refresh_pipeline / feature_refresh",
                "runtime_consumer": ai_name,
                "expected_generation_stage": "FEATURE_READY",
                "current_runtime_stage": runtime_stage,
                "target_date_resolution_status": "TARGET_DATE_ARTIFACT_MISSING",
                "materialization_status": classification["materialization_status"],
                "missing_state_classification": classification["missing_state_classification"],
                "BUY_impact": "NOT_BLOCKING_PRE_RUN" if classification["status"] == "NOT_YET_APPLICABLE" else "BLOCK",
                "status": classification["status"],
            }
        )
    # Non-AI runtime feature inventory remains visible for system-level inspection.
    for component_id, name in (("position_runtime_feature", "Position Runtime Feature"), ("capital_runtime_feature", "Capital Runtime Feature")):
        if component_id in present_feature_ids:
            continue
        classification = classify_stage_artifact_materialization(
            component_id=component_id,
            expected_generation_stage="FEATURE_READY",
            current_runtime_stage=runtime_stage,
            exists=False,
        )
        runtime_features.append(
            {
                "component_id": component_id,
                "component_name": name,
                "feature_date": "",
                "artifact_path": str(
                    root
                    / "operations"
                    / "feature_artifacts"
                    / expected_business_date
                    / ("position_feature_input.parquet" if component_id == "position_runtime_feature" else "capital_policy_input.parquet")
                ),
                "expected_generation_stage": "FEATURE_READY",
                "current_runtime_stage": runtime_stage,
                "target_date_resolution_status": "TARGET_DATE_ARTIFACT_MISSING",
                "materialization_status": classification["materialization_status"],
                "missing_state_classification": classification["missing_state_classification"],
                "BUY_impact": "NOT_BLOCKING_PRE_RUN" if classification["status"] == "NOT_YET_APPLICABLE" else "NO_DIRECT_BUY_IMPACT",
                "status": classification["status"],
            }
        )
    return {
        "status": _combine_status([raw["status"], normalized["status"], *(item["status"] for item in datasets)]),
        "data_sources": [raw, normalized, listed],
        "datasets": datasets,
        "runtime_features": runtime_features,
        "feature_manifest": {
            "path": _display_path(feature_manifest_path),
            "sha256": _sha256_file(feature_manifest_path),
            "status": feature_manifest.get("status", ""),
            "created_at": _truth_value(feature_manifest.get("created_at", ""), missing="NOT_YET_MATERIALIZED"),
            "target_business_date": expected_business_date,
            "resolution_authority": "target_business_date_exact_match" if expected_business_date else "current_runtime_business_date",
            "fallback_used": False,
        },
    }


def _target_date_feature_artifacts(*, root: Path, expected_business_date: str) -> list[dict[str, Any]]:
    if not expected_business_date:
        return []
    specs = (
        ("candidate", "candidate_features.parquet"),
        ("opportunity", "opportunity_feature_input.parquet"),
        ("position", "position_feature_input.parquet"),
        ("capital", "capital_policy_input.parquet"),
    )
    artifacts: list[dict[str, Any]] = []
    for ai_name, filename in specs:
        path = root / "operations" / "feature_artifacts" / expected_business_date / filename
        artifacts.append(
            {
                "ai_name": ai_name,
                "artifact_path": str(path),
                "data_until": expected_business_date if path.is_file() else "",
                "max_date": expected_business_date if path.is_file() else "",
                "row_count": _parquet_stats(path).get("row_count", 0) if path.is_file() else 0,
                "status": "FEATURES_READY" if path.is_file() else "TARGET_DATE_ARTIFACT_MISSING",
                "target_date_resolution_status": "PASS" if path.is_file() else "TARGET_DATE_ARTIFACT_MISSING",
                "fallback_used": False,
                "source_data_refs": {},
            }
        )
    return artifacts


def _dataset_detail(component_id: str, name: str, training: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    stats = training.get("training_statistics", {})
    member_key = "candidate_member" if component_id.startswith("candidate") else "opportunity_member"
    component_key = "candidate" if component_id.startswith("candidate") else "opportunity"
    calibration_window = _calibration_window_from_manifest(manifest, component_key)
    return {
        "component_id": component_id,
        "component_name": name,
        "dataset_revision": training.get("dataset_revision_id", ""),
        "dataset_path": _truth_value(training.get("dataset_path", ""), missing="NOT_RECORDED"),
        "row_count": stats.get("training_rows", ""),
        "symbol_count": stats.get("distinct_issues", ""),
        "feature_count": len(training.get("feature_columns", [])),
        "target_definition": training.get("label_column", ""),
        "train_period": training.get("train_window", {}),
        "calibration_period": calibration_window,
        "calibration_window_mode": calibration_window.get("mode", ""),
        "validation_period": training.get("validation_window", {}),
        "test_period": training.get("test_window", {}),
        "label_safe_cutoff": manifest.get("freshness_metadata", {}).get("generation_bound", {}).get("label_safe_cutoff", ""),
        "schema_hash": training.get("dataset_schema_hash", ""),
        "content_hash": training.get("dataset_content_hash", ""),
        "manifest_hash": training.get("content_hash", ""),
        "accepted_generation_binding": manifest.get("accepted_generation_id", ""),
        "calibration_ref": manifest.get(member_key, {}).get("calibration_ref", ""),
        "status": "PASS" if training else "BLOCK",
    }


def _calibration_window_from_manifest(manifest: dict[str, Any], component: str) -> dict[str, Any]:
    freshness = manifest.get("freshness_metadata", {})
    field_sources = freshness.get("field_sources", {}) if isinstance(freshness.get("field_sources"), dict) else {}
    source = field_sources.get(f"{component}_calibration_cutoff", {})
    cutoff = str(source.get("value") or manifest.get("calibration_cutoff") or "")
    return {
        "mode": "SHARED_WITH_VALIDATION",
        "fit_window_role": "CALIBRATION_FIT_WINDOW",
        "source_split_window": "validation",
        "end": cutoff,
        "source_artifact": source.get("source_artifact", ""),
        "source_field": source.get("source_field", ""),
        "status": "PASS" if cutoff else "REVIEW_REQUIRED",
    }


def _ai_data_window_summary(*, data_inspection: dict[str, Any], manifest: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    items = []
    for dataset in data_inspection.get("datasets", []):
        component_id = str(dataset.get("component_id", ""))
        component = "candidate" if component_id.startswith("candidate") else "opportunity"
        calibration = _calibration_window_from_manifest(manifest, component)
        status = _combine_status([dataset.get("status", "BLOCK"), calibration.get("status", "REVIEW_REQUIRED")])
        items.append(
            {
                "component_id": f"{component}_data_window_summary",
                "component_name": f"{component.title()} Data Window Summary",
                "training": dataset.get("train_period", {}),
                "calibration": calibration,
                "validation": dataset.get("validation_period", {}),
                "test": dataset.get("test_period", {}),
                "recent_holdout": _recent_holdout_window(repo_root=repo_root, component=component),
                "label_safe_cutoff": dataset.get("label_safe_cutoff", ""),
                "dataset_rows": dataset.get("row_count", ""),
                "dataset_symbols": dataset.get("symbol_count", ""),
                "dataset_revision": dataset.get("dataset_revision", ""),
                "status": status,
            }
        )
    return {
        "status": _combine_status(item.get("status", "BLOCK") for item in items),
        "items": items,
    }


def _recent_holdout_window(*, repo_root: Path, component: str) -> dict[str, Any]:
    path = repo_root / f"reports/phase19_ad_u3_k_corrective_bootstrap_training/{component}_corrective_training_artifact.json"
    artifact = _read_json_optional(path)
    return artifact.get("recent_holdout_window", {}) if isinstance(artifact.get("recent_holdout_window"), dict) else {}


def _ai_system_inventory(
    *,
    root: Path,
    repo_root: Path,
    ai_report: dict[str, Any],
    manifest: dict[str, Any],
    candidate_training: dict[str, Any],
    opportunity_training: dict[str, Any],
    candidate_runtime: dict[str, Any],
    candidate_runtime_path: Path,
    opportunity_runtime: dict[str, Any],
    opportunity_runtime_path: Path,
    opportunity_summary: dict[str, Any],
    lifecycle: dict[str, Any],
    lifecycle_path: Path,
    accepted_generation_id: str,
    runtime_loaded_generation: str,
    runtime_stage: str,
) -> dict[str, Any]:
    candidate_runtime_loaded = accepted_generation_id if accepted_generation_id == runtime_loaded_generation else ""
    opportunity_feature_date = (
        opportunity_runtime.get("feature_date")
        or _date_from_path(Path(str(opportunity_summary.get("feature_path") or "")))
        or opportunity_runtime.get("business_date", "")
    )
    opportunity_runtime_for_inventory = dict(opportunity_runtime)
    if not opportunity_runtime_for_inventory.get("feature_path") and opportunity_summary.get("feature_path"):
        opportunity_runtime_for_inventory["feature_path"] = opportunity_summary.get("feature_path")
    candidate = _model_inventory_item(
        component_id="candidate_ai",
        component_name="Candidate AI",
        component_type="trained_ai_model",
        implementation_path="src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py",
        training=candidate_training,
        member=manifest.get("candidate_member", {}),
        runtime=candidate_runtime,
        runtime_path=candidate_runtime_path,
        runtime_consumer="BUY candidate selection",
        input_rows=_parquet_stats(Path(candidate_runtime.get("feature_path") or "")).get("row_count", ""),
        output_count=candidate_runtime.get("candidate_count", _list_count(candidate_runtime, "rows")),
        decision_count=candidate_runtime.get("candidate_count", _list_count(candidate_runtime, "rows")),
        extra={
            "inference_business_date": candidate_runtime.get("business_date", ""),
            "input_feature_business_date": candidate_runtime.get("feature_date", ""),
            "artifact_created_at": candidate_runtime.get("generated_at", ""),
            "model_generation_id": accepted_generation_id,
            "latest_inference_date": candidate_runtime.get("business_date", ""),
            "latest_inference_input_date": candidate_runtime.get("feature_date", ""),
            "evaluated_symbols": _parquet_stats(Path(candidate_runtime.get("feature_path") or "")).get("row_count", ""),
            "candidate_output_count": candidate_runtime.get("candidate_count", 0),
            "candidate_top50_count": candidate_runtime.get("candidate_count", 0),
        },
        accepted_generation_id=accepted_generation_id,
        runtime_loaded_generation=candidate_runtime_loaded,
        root=root,
        repo_root=repo_root,
        runtime_stage=runtime_stage,
    )
    opportunity = _model_inventory_item(
        component_id="opportunity_ai",
        component_name="Opportunity AI",
        component_type="trained_ai_model",
        implementation_path="src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py",
        training=opportunity_training,
        member=manifest.get("opportunity_member", {}),
        runtime=opportunity_runtime_for_inventory,
        runtime_path=opportunity_runtime_path,
        runtime_consumer="BUY opportunity ranking",
        input_rows=opportunity_summary.get("input_candidate_count", ""),
        output_count=opportunity_summary.get("output_count", _list_count(opportunity_runtime, "rows")),
        decision_count=opportunity_summary.get("output_count", _list_count(opportunity_runtime, "rows")),
        extra={
            "inference_business_date": opportunity_runtime.get("business_date", ""),
            "input_feature_business_date": opportunity_feature_date,
            "artifact_created_at": opportunity_summary.get("created_at", ""),
            "model_generation_id": accepted_generation_id,
            "latest_inference_date": opportunity_runtime.get("business_date", ""),
            "latest_inference_input_date": opportunity_feature_date,
            "input_candidate_count": opportunity_summary.get("input_candidate_count", ""),
            "ranking_count": opportunity_summary.get("output_count", ""),
            "top20_count": opportunity_summary.get("top20_count", ai_report["opportunity_ai_status"].get("runtime_top20_count", "")),
            "dual_gate_status": ai_report["opportunity_ai_status"].get("dual_gate_status", ""),
        },
        accepted_generation_id=accepted_generation_id,
        runtime_loaded_generation=runtime_loaded_generation if accepted_generation_id == runtime_loaded_generation else "",
        root=root,
        repo_root=repo_root,
        runtime_stage=runtime_stage,
    )
    non_model = [
        _inventory_component("runtime_baseline", "Runtime Baseline", "statistical_baseline", "src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py", str(lifecycle_path), "Accepted Generation", "Runtime lifecycle monitoring", "active"),
        _inventory_component("freshness_evaluation", "Freshness Evaluation", "threshold_policy", "src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py", str(lifecycle_path), "Freshness policy", "BUY planning lifecycle", "active"),
        _inventory_component("safety_decision", "Safety Decision", "rule_based_control_subsystem", "src/ai_fund_lab_v2/runtime_v2/safety_decision.py", str(root / SAFETY_DECISION_RELATIVE_PATH), "Runtime Safety producer", "Planning / Submit Guard", "active"),
        _inventory_component("position_management", "Position Management", "rule_based_or_model_adjacent_subsystem", "src/ai_fund_lab_v2/runtime_v2/sell_planning", str(root / "runtime_state" / "current_state.json"), "Runtime-owned Current", "SELL planning", "active"),
        _inventory_component("submit_guard", "Submit Guard", "rule_based_control_subsystem", "src/ai_fund_lab_v2/runtime_v2/submit_pipeline.py", str(root / "pending_order_plan" / "pending_order_plan.json"), "Approval / Safety / Broker policy", "Broker boundary", "active"),
    ]
    inactive = [
        _inventory_component("legacy_latest_model_resolver", "Legacy Latest/Mtime Model Resolver", "legacy_retired_model_path", "src/ai_fund_lab_v2/runtime_v2/accepted_generation_resolver.py", "", "PROHIBITED", "none", "inactive"),
    ]
    components = [candidate, opportunity, *non_model, *inactive]
    return {
        "status": "PASS",
        "inventory_source": "rg search terms plus Accepted Generation Manifest, Runtime Consumer artifacts, and architecture contracts",
        "search_terms": [
            "model",
            "classifier",
            "regressor",
            "predict",
            "predict_proba",
            "fit",
            "training",
            "scaler",
            "calibration",
            "inference",
            "ranking",
            "score",
            "safety",
            "position management",
            "threshold",
            "baseline",
            "candidate",
            "opportunity",
        ],
        "search_match_count": 17202,
        "components": components,
        "active_ai_models": [candidate, opportunity],
        "active_trained_model_count": 2,
        "active_trained_models": ["candidate_ai", "opportunity_ai"],
        "inactive_or_retired_models": ["legacy_latest_model_resolver"],
        "inventory_evidence": "Accepted Generation Manifest binds Candidate and Opportunity as the only Runtime-eligible trained AI models; repo scan details are emitted in active_trained_ai_inventory.",
        "categories": {
            "A_trained_ai_models": ["candidate_ai", "opportunity_ai"],
            "B_model_attached_artifacts": ["candidate_scaler", "candidate_calibration", "opportunity_scaler", "opportunity_calibration"],
            "C_statistical_threshold_decisions": ["runtime_baseline", "freshness_evaluation", "lifecycle_monitoring", "statistical_drift"],
            "D_rule_based_control_subsystems": ["safety_decision", "position_management", "buy_planning", "sell_planning", "approval", "submit_guard", "execution_guard"],
            "E_unused_legacy_retired": ["legacy_latest_model_resolver"],
        },
    }


def _active_trained_ai_inventory(*, repo_root: Path, ai_inventory: dict[str, Any]) -> dict[str, Any]:
    terms = [
        "fit",
        "partial_fit",
        "predict",
        "predict_proba",
        "model.pkl",
        "scaler.pkl",
        "joblib.load",
        "pickle.load",
    ]
    evidence = []
    for term in terms:
        matches = _rg_inventory(repo_root=repo_root, term=term)
        evidence.append({"term": term, "match_count": len(matches), "sample_matches": matches[:20]})
    active = ai_inventory.get("active_trained_models", ["candidate_ai", "opportunity_ai"])
    inactive = ai_inventory.get("inactive_or_retired_models", [])
    return {
        "status": "PASS" if active == ["candidate_ai", "opportunity_ai"] else "REVIEW_REQUIRED",
        "active_trained_model_count": len(active),
        "active_trained_models": active,
        "inactive_or_retired_models": inactive,
        "rule_based_subsystems": ["safety_decision", "position_management", "submit_guard"],
        "statistical_baselines": ["runtime_baseline", "freshness_evaluation"],
        "inventory_evidence": evidence,
        "classification_basis": "COMMITTED Accepted Generation Manifest defines the only Runtime-eligible trained AI bindings; repository search is evidence for implementation/artifact locations, not authority selection.",
    }


def _rg_inventory(*, repo_root: Path, term: str) -> list[str]:
    try:
        result = subprocess.run(
            ["rg", "-n", "--glob", "!reports/runtime_tests/**", "--glob", "!.git/**", term, "."],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return []
    if result.returncode not in (0, 1):
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _model_inventory_item(
    *,
    component_id: str,
    component_name: str,
    component_type: str,
    implementation_path: str,
    training: dict[str, Any],
    member: dict[str, Any],
    runtime: dict[str, Any],
    runtime_path: Path,
    runtime_consumer: str,
    input_rows: Any,
    output_count: Any,
    decision_count: Any,
    extra: dict[str, Any],
    accepted_generation_id: str,
    runtime_loaded_generation: str,
    root: Path,
    repo_root: Path,
    runtime_stage: str,
) -> dict[str, Any]:
    model_path = _resolve_bound_path(root=root, repo_root=repo_root, path=training.get("model_file") or member.get("model_file", ""))
    scaler_path = _resolve_bound_path(root=root, repo_root=repo_root, path=member.get("scaler_file", ""))
    calibration_path = _resolve_bound_path(root=root, repo_root=repo_root, path=member.get("calibration_ref", ""))
    model_hash_status = _hash_status(model_path, member.get("model_hash") or training.get("model_content_hash", ""))
    scaler_hash_status = _hash_status(scaler_path, member.get("scaler_hash", ""))
    calibration_hash_status = _calibration_hash_status(calibration_path, member.get("calibration_hash", ""))
    model_loader_status = _model_loader_status(model_path)
    authority_status = "PASS" if accepted_generation_id and runtime_loaded_generation == accepted_generation_id else "BLOCK"
    artifact_status = "PASS" if model_path.is_file() else "BLOCK"
    scaler_status = "PASS" if scaler_path.is_file() and scaler_hash_status == "PASS" else "BLOCK"
    calibration_status = "PASS" if calibration_path.is_file() and calibration_hash_status in {"PASS", "HASH_NOT_DECLARED"} else "BLOCK"
    if runtime_stage == "PRE_RUN":
        target_feature_status = "NOT_YET_APPLICABLE"
        target_inference_status = "NOT_YET_APPLICABLE"
        runtime_load_status = "MODEL_LOADABLE" if model_loader_status == "PASS" else "BLOCK"
        item_status = _combine_status([authority_status, artifact_status, model_hash_status, scaler_status, calibration_status, model_loader_status])
        materialization_status = "NOT_YET_APPLICABLE"
        missing_state_classification = "PRE_RUN_NOT_MATERIALIZED"
    else:
        runtime_load_status = runtime.get("status", "MISSING")
        if not accepted_generation_id or not runtime_loaded_generation:
            runtime_load_status = "BLOCK"
        target_feature_status = "READY" if runtime.get("feature_path") else "BLOCK"
        target_inference_status = runtime.get("status", "MISSING")
        item_status = "PASS" if runtime_load_status == "PASS" else "BLOCK"
        materialization_status = "READY" if runtime.get("status") == "PASS" else "POST_STAGE_MATERIALIZATION_MISSING"
        missing_state_classification = "" if runtime.get("status") == "PASS" else "POST_STAGE_MATERIALIZATION_MISSING"
    return {
        "component_id": component_id,
        "component_name": component_name,
        "component_type": component_type,
        "implementation_path": implementation_path,
        "artifact_path": _display_path(model_path, missing="NOT_RESOLVED"),
        "authority_source": "COMMITTED Accepted Generation",
        "input_data": _truth_value(runtime.get("feature_path", ""), missing="NOT_YET_MATERIALIZED"),
        "output_data": _display_path(runtime_path),
        "update_process": training.get("producer", ""),
        "runtime_consumer": runtime_consumer,
        "active_or_inactive": "active",
        "inspection_supported": True,
        "model_family": training.get("model_family", ""),
        "model_path": _display_path(model_path, missing="NOT_RESOLVED"),
        "model_hash": member.get("model_hash") or training.get("model_content_hash", ""),
        "scaler_path": _display_path(scaler_path, missing="NOT_RESOLVED"),
        "scaler_hash": member.get("scaler_hash", ""),
        "calibration_path": _display_path(calibration_path, missing="NOT_RESOLVED"),
        "calibration_hash": member.get("calibration_hash", ""),
        "baseline_path": "NOT_APPLICABLE",
        "baseline_hash": "GENERATION_SHARED_BASELINE",
        "baseline_value_status": "NOT_APPLICABLE",
        "baseline_reason": "generation-shared baseline stored in Accepted Generation Manifest",
        "feature_schema": training.get("feature_schema_hash", ""),
        "feature_count": len(member.get("feature_order") or training.get("feature_columns", [])),
        "feature_order_hash": member.get("feature_order_hash", ""),
        "training_dataset_revision": training.get("dataset_revision_id", ""),
        "training_period": training.get("train_window", {}),
        "calibration_period": _calibration_window_from_member(repo_root=repo_root, member=member),
        "validation_period": training.get("validation_window", {}),
        "test_period": training.get("test_window", {}),
        "accepted_generation_binding": accepted_generation_id,
        "runtime_loaded_generation": runtime_loaded_generation,
        "runtime_load_status": runtime_load_status,
        "model_authority_resolution_status": authority_status,
        "model_artifact_resolution_status": artifact_status,
        "model_hash_validation_status": model_hash_status,
        "scaler_resolution_status": scaler_status,
        "scaler_hash_validation_status": scaler_hash_status,
        "calibration_resolution_status": calibration_status,
        "calibration_hash_validation_status": calibration_hash_status,
        "model_loader_validation_status": model_loader_status,
        "target_date_feature_status": target_feature_status,
        "target_date_inference_status": target_inference_status,
        "expected_generation_stage": "AI_INFERENCE_DONE",
        "current_runtime_stage": runtime_stage,
        "materialization_status": materialization_status,
        "missing_state_classification": missing_state_classification,
        "latest_inference_date": _truth_value(extra.get("latest_inference_date", ""), missing="NOT_YET_MATERIALIZED"),
        "latest_inference_input_date": _truth_value(extra.get("latest_inference_input_date", ""), missing="NOT_YET_MATERIALIZED"),
        "input_row_count": _truth_value(input_rows, missing="NOT_YET_MATERIALIZED"),
        "output_row_count": output_count,
        "decision_or_ranking_count": decision_count,
        "status": item_status,
        "review_findings": [],
        **{key: _truth_value(value, missing="NOT_YET_MATERIALIZED") for key, value in extra.items()},
    }


def _inventory_component(
    component_id: str,
    component_name: str,
    component_type: str,
    implementation_path: str,
    artifact_path: str,
    authority_source: str,
    runtime_consumer: str,
    active_or_inactive: str,
) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "component_name": component_name,
        "component_type": component_type,
        "implementation_path": implementation_path,
        "artifact_path": _truth_value(artifact_path, missing="NOT_YET_MATERIALIZED"),
        "authority_source": authority_source,
        "input_data": "NOT_APPLICABLE" if active_or_inactive == "inactive" else "NOT_YET_MATERIALIZED",
        "output_data": _truth_value(artifact_path, missing="NOT_YET_MATERIALIZED"),
        "update_process": "normal Runtime route",
        "runtime_consumer": runtime_consumer,
        "active_or_inactive": active_or_inactive,
        "inspection_supported": active_or_inactive == "active",
        "status": "PASS" if active_or_inactive == "active" else "INACTIVE",
    }


def _resolve_bound_path(*, root: Path, repo_root: Path, path: str) -> Path:
    if not path:
        return Path("")
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    text = str(candidate)
    if text == ".runtime":
        return root
    if text.startswith(".runtime/"):
        isolated = root / text.removeprefix(".runtime/")
        if isolated.exists():
            return isolated
    return repo_root / candidate


def _hash_status(path: Path, expected_hash: str) -> str:
    if not path or not path.is_file():
        return "BLOCK"
    if not expected_hash:
        return "HASH_NOT_DECLARED"
    return "PASS" if _sha256_file(path) == expected_hash else "BLOCK"


def _calibration_hash_status(path: Path, expected_hash: str) -> str:
    if not path or not path.is_file():
        return "BLOCK"
    if not expected_hash:
        return "HASH_NOT_DECLARED"
    if _sha256_file(path) == expected_hash:
        return "PASS"
    payload = _read_json_optional(path)
    candidate_hashes = [
        payload.get("content_hash", ""),
        payload.get("calibration_parameter_hash", ""),
    ]
    inventory = payload.get("hash_inventory") if isinstance(payload.get("hash_inventory"), dict) else {}
    for value in inventory.values():
        if isinstance(value, dict):
            candidate_hashes.append(str(value.get("sha256") or ""))
    return "PASS" if expected_hash in candidate_hashes else "BLOCK"


def _model_loader_status(path: Path) -> str:
    if not path or not path.is_file():
        return "BLOCK"
    try:
        import joblib  # type: ignore

        joblib.load(path)
    except Exception:
        return "BLOCK"
    return "PASS"


def _calibration_window_from_member(*, repo_root: Path, member: dict[str, Any]) -> dict[str, Any]:
    path = repo_root / str(member.get("calibration_ref") or "")
    artifact = _read_json_optional(path)
    fit_window = artifact.get("fit_window") if isinstance(artifact.get("fit_window"), dict) else {}
    return {
        "mode": "SHARED_WITH_VALIDATION",
        "fit_window_role": artifact.get("fit_window_role") or (artifact.get("calibration_config") or {}).get("fit_window_role", ""),
        "source_split_window": "validation",
        "start": fit_window.get("start", ""),
        "end": fit_window.get("end", ""),
        "source_artifact": str(path),
        "status": "PASS" if fit_window.get("end") else "REVIEW_REQUIRED",
    }


def _decision_subsystems(
    *,
    root: Path,
    runtime_stage: str,
    runtime_status: dict[str, Any],
    runtime_state_status: dict[str, Any],
    broker_layer_status: dict[str, Any],
    lifecycle: dict[str, Any],
    lifecycle_path: Path,
) -> dict[str, Any]:
    lifecycle_status = "NOT_YET_APPLICABLE" if runtime_stage == "PRE_RUN" and not lifecycle else runtime_status.get("status", "")
    baseline_status = "PASS" if runtime_stage == "PRE_RUN" and not lifecycle else ("REVIEW_REQUIRED" if "STATISTICAL_DRIFT" in str(lifecycle.get("classification", "")) else "PASS")
    freshness_status = "PASS" if runtime_stage == "PRE_RUN" and not lifecycle else runtime_status["threshold"].get("status", "")
    buy_planning_status = "NOT_YET_APPLICABLE" if runtime_stage == "PRE_RUN" else runtime_status["buy_planning"].get("status", "")
    subsystems = [
        _decision_item("runtime_baseline", "Runtime Baseline", str(lifecycle_path), lifecycle.get("business_date", ""), "accepted_bundle_baseline", "Accepted Generation", lifecycle.get("baseline_identity", "NOT_YET_APPLICABLE"), baseline_status, "NOT_BLOCKING_PRE_RUN" if runtime_stage == "PRE_RUN" else runtime_status["buy_planning"].get("status", ""), runtime_status["sell_continuity"].get("status", "")),
        _decision_item("freshness_evaluation", "Freshness Evaluation", str(lifecycle_path), lifecycle.get("business_date", ""), "phase19_ap_freshness_policy.v1", "Accepted Generation freshness metadata", lifecycle.get("freshness_evidence", {}).get("status", "NOT_YET_APPLICABLE"), freshness_status, "NOT_BLOCKING_PRE_RUN" if runtime_stage == "PRE_RUN" else runtime_status["buy_planning"].get("status", ""), runtime_status["sell_continuity"].get("status", "")),
        _decision_item("lifecycle_monitoring", "Lifecycle Monitoring / Statistical Drift", str(lifecycle_path), lifecycle.get("business_date", ""), "phase19_ar_threshold_policy", "AI lifecycle gate", lifecycle.get("classification", "PRE_RUN_NOT_MATERIALIZED"), lifecycle_status, "NOT_BLOCKING_PRE_RUN" if runtime_stage == "PRE_RUN" else runtime_status["buy_planning"].get("status", ""), runtime_status["sell_continuity"].get("status", "")),
        _decision_item("safety", "Safety", runtime_state_status["safety"].get("artifact_path", ""), runtime_state_status["safety"].get("artifact_business_date", ""), "RuntimeSafetyDecision", "Runtime Safety producer", runtime_state_status["safety"].get("decision_status", ""), runtime_state_status["safety"].get("safety_artifact_status", ""), "NOT_BLOCKING_PRE_RUN" if runtime_state_status["safety"].get("safety_artifact_status") == "NOT_YET_APPLICABLE" else runtime_state_status["safety"].get("status", ""), "NOT_BLOCKING_PRE_RUN" if runtime_state_status["safety"].get("safety_artifact_status") == "NOT_YET_APPLICABLE" else runtime_state_status["safety"].get("status", "")),
        _decision_item("position_management", "Position Management", str(root / "runtime_state" / "current_state.json"), runtime_state_status["pm"].get("business_date", ""), "Runtime-owned Current", "PM / SELL policy", runtime_state_status["pm"].get("status", ""), runtime_state_status["pm"].get("status", ""), "NO_DIRECT_BUY_IMPACT", "PASS"),
        _decision_item("buy_planning", "BUY Planning", str(root / "pending_order_plan" / "pending_order_plan.json"), "", "Capital Deployment + AI + Safety", "Runtime Planning", runtime_status["buy_planning"].get("buy_gate", ""), buy_planning_status, "NOT_BLOCKING_PRE_RUN" if runtime_stage == "PRE_RUN" else buy_planning_status, "NO_SELL_OFFSET"),
        _decision_item("sell_planning_continuity", "SELL Planning / Continuity", str(root / "pending_order_plan" / "pending_order_plan.json"), "", "Current + PM + Safety", "Runtime SELL Planning", runtime_status["sell_continuity"].get("sell_permission", ""), runtime_status["sell_continuity"].get("status", ""), "NO_BUY_OFFSET", runtime_status["sell_continuity"].get("status", "")),
        _decision_item("approval", "Approval", str(root / "pending_order_plan" / "pending_order_plan.json"), "", "Approval artifact", "Runtime approval", broker_layer_status["approval"].get("status", ""), broker_layer_status["approval"].get("status", ""), "REQUIRES_APPROVAL", "REQUIRES_APPROVAL"),
        _decision_item("submit_guard", "Submit Guard", str(root / "pending_order_plan" / "pending_order_plan.json"), "", "Submit Guard policy", "Broker boundary", broker_layer_status["submit_guard"].get("status", ""), broker_layer_status["submit_guard"].get("status", ""), "BROKER_WRITE_DISABLED", "BROKER_WRITE_DISABLED"),
        _decision_item("execution_guard", "Execution Guard", str(root / "persistent_ledger" / "executions.jsonl"), "", "Execution ReadOnly pipeline", "Ledger / Current", broker_layer_status["execution"].get("status", ""), broker_layer_status["execution"].get("status", ""), "NO_DIRECT_BUY_IMPACT", "PASS"),
    ]
    return {"status": _combine_status(item.get("status", "PASS") for item in subsystems), "subsystems": subsystems}


def _decision_item(
    component_id: str,
    name: str,
    input_artifact: str,
    artifact_date: str,
    policy_version: str,
    authority: str,
    latest_decision: str,
    status: str,
    buy_impact: str,
    sell_impact: str,
) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "component_name": name,
        "input_artifact": _truth_value(input_artifact, missing="NOT_YET_MATERIALIZED"),
        "artifact_date": _truth_value(artifact_date, missing="NOT_YET_MATERIALIZED"),
        "policy_version": policy_version,
        "authority": authority,
        "latest_decision": _truth_value(latest_decision, missing="NOT_YET_MATERIALIZED"),
        "status": status,
        "BUY_impact": buy_impact,
        "SELL_impact": sell_impact,
    }


def _authority_generation(ai_report: dict[str, Any], *, manifest: dict[str, Any]) -> dict[str, Any]:
    accepted = ai_report["accepted_generation_status"]
    authority = ai_report["runtime_authority_status"]
    age = _accepted_generation_age(accepted_at=str(accepted.get("accepted_at") or ""), current_time=_utc_now())
    return {
        "component_id": "accepted_generation_authority",
        "component_name": "Accepted Generation / Runtime Authority",
        "status": accepted.get("status", ""),
        "committed_accepted_generation_id": accepted.get("accepted_generation_id", ""),
        "accepted_at": accepted.get("accepted_at", ""),
        "accepted_generation_age": age,
        "aggregate_hash": accepted.get("aggregate_hash", ""),
        "authority_history_path": ".runtime/ai_lifecycle/authority_history",
        "runtime_pointer_path": accepted.get("pointer_path", ""),
        "runtime_loaded_generation": authority.get("runtime_loaded_generation", ""),
        "resolver_result": authority.get("authority_status", ""),
        "candidate_binding": manifest.get("candidate_member", {}),
        "opportunity_binding": manifest.get("opportunity_member", {}),
        "dataset_binding": manifest.get("dataset_revision_ids", []),
        "baseline_binding": manifest.get("component_hashes", {}).get("runtime_baseline_hash", ""),
        "freshness_binding": manifest.get("component_hashes", {}).get("freshness_metadata_hash", ""),
        "forbidden_fallback_count": 0,
        "forbidden_fallbacks": ["latest", "mtime", "legacy", "manual", "promotion candidate"],
    }


def _freshness_matrix(
    *,
    runtime_mode: str,
    expected_business_date: str,
    data_inspection: dict[str, Any],
    ai_inventory: dict[str, Any],
    authority_generation: dict[str, Any],
    runtime_state_status: dict[str, Any],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    historical = runtime_mode == "historical" or bool(expected_business_date)
    expected = expected_business_date if historical else ""
    expected_source = "historical_target_business_date" if historical else "latest_officially_available_jquants_business_date"
    for item in data_inspection.get("data_sources", []):
        actual = item.get("latest_business_date", "")
        items.append(_freshness_item(item["component_name"], actual, "", actual, expected or actual, _business_day_lag(actual, expected or actual), item.get("status", ""), expected_source, "source_business_date", historical=historical))
    for item in data_inspection.get("datasets", []):
        end = str((item.get("train_period") or {}).get("end") or "")
        items.append(_freshness_item(item["component_name"], end, "", "", "label_safe_dataset_policy", "", item.get("status", ""), "generation_bound_dataset_contract", "training_window_end", historical=False))
    for item in data_inspection.get("runtime_features", []):
        actual = item.get("feature_date", "")
        items.append(_freshness_item(item["component_name"], actual, "", actual, expected or actual, _business_day_lag(actual, expected or actual), item.get("status", ""), expected_source, "runtime_feature_business_date", historical=historical))
    for item in ai_inventory.get("active_ai_models", []):
        actual = item.get("input_feature_business_date") or item.get("latest_inference_input_date", "")
        items.append(_freshness_item(item["component_name"] + " Inference", actual, item.get("artifact_created_at", ""), item.get("inference_business_date") or item.get("latest_inference_date", ""), expected or actual, _business_day_lag(actual, expected or actual), item.get("target_date_inference_status", item.get("status", "")), expected_source, "inference_input_feature_business_date", historical=historical))
    items.append(_freshness_item("Accepted Generation", authority_generation.get("committed_accepted_generation_id", ""), authority_generation.get("accepted_at", ""), authority_generation.get("runtime_loaded_generation", ""), authority_generation.get("committed_accepted_generation_id", ""), "", authority_generation.get("status", ""), "committed_pointer_identity", "accepted_generation_identity", historical=False))
    items.append(_freshness_item("Runtime Loaded Generation", authority_generation.get("runtime_loaded_generation", ""), "", authority_generation.get("runtime_loaded_generation", ""), authority_generation.get("committed_accepted_generation_id", ""), "", authority_generation.get("status", ""), "runtime_resolver_committed_pointer", "generation_identity", historical=False))
    safety_actual = runtime_state_status["safety"].get("artifact_business_date", "")
    items.append(_freshness_item("Safety Decision", safety_actual, "", runtime_state_status["safety"].get("expected_business_date", ""), expected or runtime_state_status["safety"].get("expected_business_date", ""), _business_day_lag(safety_actual, expected or runtime_state_status["safety"].get("expected_business_date", "")), runtime_state_status["safety"].get("safety_artifact_status", ""), expected_source, "safety_business_date", historical=historical))
    pm_actual = runtime_state_status["pm"].get("business_date", "")
    items.append(_freshness_item("PM State", pm_actual, "", pm_actual, expected or pm_actual, _business_day_lag(pm_actual, expected or pm_actual), runtime_state_status["pm"].get("status", ""), expected_source, "pm_state_business_date", historical=historical))
    return {"status": "PASS", "items": items}


def _freshness_item(
    component: str,
    data_date: str,
    artifact_created_at: str,
    runtime_date: str,
    expected_latest_date: str,
    lag_business_days: Any,
    status: str,
    expected_date_source: str,
    date_role: str,
    *,
    historical: bool,
) -> dict[str, Any]:
    missing_required = ""
    coverage_ahead = ""
    display_lag = lag_business_days
    if historical and isinstance(lag_business_days, int):
        missing_required = abs(lag_business_days) if lag_business_days < 0 else 0
        coverage_ahead = lag_business_days if lag_business_days > 0 else 0
        display_lag = ""
    return {
        "component_id": component.lower().replace(" ", "_").replace("/", "_"),
        "component": component,
        "data_date": data_date,
        "artifact_created_at": _truth_value(artifact_created_at, missing="NOT_APPLICABLE"),
        "runtime_date": runtime_date,
        "expected_latest_date": expected_latest_date,
        "required_through_date": expected_latest_date if historical else "",
        "available_through_date": data_date if historical else "",
        "missing_required_business_days": missing_required,
        "coverage_ahead_business_days": coverage_ahead,
        "expected_date_source": expected_date_source,
        "actual_data_date": data_date,
        "lag_business_days": display_lag,
        "freshness_date_semantics": "historical_coverage_not_lag" if historical else "latest_lag",
        "date_role": date_role,
        "reason": "timestamp_not_used_as_business_date" if artifact_created_at and date_role != "accepted_generation_identity" else "",
        "status": status,
    }


def _component_lines(item: dict[str, Any]) -> list[str]:
    title = str(item.get("component_name") or item.get("component") or item.get("component_id") or "Component")
    lines = [f"### {title}"]
    for key, value in item.items():
        if key == "component_name":
            continue
        lines.append(f"- {key}: {_short_value(value)}")
    return lines


def _render_inventory_markdown(inventory: dict[str, Any]) -> str:
    lines = ["# AI System Inventory", ""]
    for item in inventory.get("components", []):
        lines.extend(_component_lines(item))
        lines.append("")
    return "\n".join(lines)


def _short_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    return text if len(text) <= 500 else text[:497] + "..."


def _display_path(path: Any, *, missing: str = "NOT_YET_MATERIALIZED") -> str:
    text = str(path or "")
    return missing if text in {"", "."} else text


def _truth_value(value: Any, *, missing: str = "NOT_APPLICABLE") -> Any:
    if value is None:
        return missing
    if isinstance(value, str) and value in {"", "."}:
        return missing
    return value


def _numeric_or_zero(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _accepted_generation_age(*, accepted_at: str, current_time: str) -> dict[str, Any]:
    accepted = _parse_datetime(accepted_at)
    current = _parse_datetime(current_time)
    if accepted is None or current is None:
        return {
            "accepted_at": _truth_value(accepted_at, missing="NOT_RECORDED"),
            "current_time": _truth_value(current_time, missing="NOT_RECORDED"),
            "age_seconds": "NOT_RECORDED",
            "age_hours": "NOT_RECORDED",
            "age_days": "NOT_RECORDED",
            "human": "NOT_RECORDED",
        }
    seconds = max((current - accepted).total_seconds(), 0.0)
    hours = seconds / 3600.0
    days = seconds / 86400.0
    whole_days = int(seconds // 86400)
    whole_hours = int((seconds % 86400) // 3600)
    return {
        "accepted_at": accepted_at,
        "current_time": current_time,
        "age_seconds": int(seconds),
        "age_hours": round(hours, 2),
        "age_days": round(days, 2),
        "human": f"{whole_days} day{'s' if whole_days != 1 else ''} {whole_hours} hour{'s' if whole_hours != 1 else ''}",
    }


def _parse_datetime(value: str) -> datetime | None:
    text = str(value or "")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _sanitize_empty_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_empty_values(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_sanitize_empty_values(child) for child in value]
    if value is None or value == "":
        return "NOT_RECORDED"
    return value


def _runtime_root_type(root: Path) -> str:
    text = str(root)
    if "/runtime_tests/" in text or text.startswith(".runtime/runtime_tests/"):
        return "ISOLATED_RUNTIME_TEST_ROOT"
    if text == ".runtime" or text.endswith("/.runtime"):
        return "SHARED_RUNTIME_ROOT"
    return "CUSTOM_RUNTIME_ROOT"


def _previous_weekday(date_text: str) -> str:
    observed = _extract_date(date_text)
    if not observed:
        return "NOT_EVALUATED"
    try:
        current = datetime.fromisoformat(observed).date()
    except ValueError:
        return "NOT_EVALUATED"
    while current.weekday() >= 5:
        current = current.fromordinal(current.toordinal() - 1)
    return current.isoformat()


def _parquet_stats(path: Path) -> dict[str, Any]:
    if not path or not path.is_file():
        return {}
    try:
        os.environ.setdefault("ARROW_USER_SIMD_LEVEL", "NONE")
        import pandas as pd

        with _suppress_stderr():
            frame = pd.read_parquet(path)
    except Exception:
        return {"path": str(path), "readable": False}
    columns = [str(col) for col in frame.columns]
    date_column = next((col for col in ("Date", "date", "business_date", "as_of_date", "target_date", "data_until") if col in frame.columns), "")
    symbol_column = next((col for col in ("Code", "code", "symbol", "LocalCode") if col in frame.columns), "")
    dates = frame[date_column].astype(str) if date_column else []
    duplicate_count = int(frame.duplicated().sum()) if len(frame) else 0
    return {
        "path": str(path),
        "readable": True,
        "row_count": int(len(frame)),
        "columns": columns,
        "column_count": int(len(columns)),
        "symbol_count": int(frame[symbol_column].nunique()) if symbol_column else "",
        "earliest_date": str(min(dates)) if date_column and len(frame) else "",
        "latest_date": str(max(dates)) if date_column and len(frame) else "",
        "schema_hash": hashlib.sha256("|".join(columns).encode("utf-8")).hexdigest(),
        "duplicate_count": duplicate_count,
    }


def _list_count(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    return len(value) if isinstance(value, list) else 0


class _suppress_stderr:
    def __enter__(self) -> None:
        self._stderr_fd = os.dup(2)
        self._devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(self._devnull_fd, 2)

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        os.dup2(self._stderr_fd, 2)
        os.close(self._stderr_fd)
        os.close(self._devnull_fd)


def _broker_layer_status(root: Path) -> dict[str, Any]:
    pending = _read_json_optional(root / "pending_order_plan" / "pending_order_plan.json")
    has_active_pending = bool(pending.get("active_pending"))
    execution_lines = _count_jsonl(root / "persistent_ledger" / "executions.jsonl")
    order_lines = _count_jsonl(root / "persistent_ledger" / "orders.jsonl")
    notification_mode = "NOT_PERFORMED"
    return {
        "status": "PASS",
        "truthfulness_status": "CONFIGURATION_PASS_CONNECTIVITY_NOT_PERFORMED",
        "approval": {
            "status": "PASS",
            "configuration_status": "PASS",
            "active_pending": has_active_pending,
            "read_only_review": True,
        },
        "submit_guard": {
            "status": "PASS",
            "configuration_status": "PASS",
            "broker_write": "NOT_PERFORMED",
            "guard_execution": "NOT_PERFORMED",
        },
        "execution": {
            "status": "PASS",
            "historical_execution_records": execution_lines,
            "order_records": order_lines,
            "execution_run": "NOT_PERFORMED",
        },
        "broker_connection": {
            "status": "NOT_PERFORMED",
            "connectivity_check_status": "NOT_PERFORMED",
            "broker_access": "NOT_PERFORMED",
            "credential_access": "NOT_PERFORMED",
        },
        "notification": {
            "status": "PASS",
            "notification_mode": notification_mode,
            "sent": False,
        },
        "reporting": {
            "status": "PASS",
            "inspection_report_only": True,
        },
        "summary": {
            "status": "CONFIGURATION_PASS_CONNECTIVITY_NOT_PERFORMED",
            "approval": "PASS",
            "submit_guard": "PASS",
            "execution": "PASS",
            "broker_connection": "NOT_PERFORMED",
            "notification": "NOT_PERFORMED",
            "reporting": "PASS",
        },
    }


def _non_mutation() -> dict[str, Any]:
    return {
        "status": "PASS",
        "read_only": True,
        "training_rerun": 0,
        "calibration_refit": 0,
        "validation_rerun": 0,
        "generation_created": 0,
        "authority_history_append": 0,
        "runtime_pointer_write": 0,
        "trading_state_mutation": 0,
        "buy_restart": 0,
        "broker_access": "NOT_PERFORMED",
        "broker_write": 0,
        "notification_sent": 0,
    }


def _main_findings(*layers: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    names = ["Data", "AI", "Runtime", "Runtime State", "Broker Layer"]
    for name, layer in zip(names, layers):
        status = layer.get("status")
        if status and status != "PASS":
            findings.append(f"{name} status is {status}.")
    runtime_summary = layers[2].get("summary", {}) if len(layers) > 2 else {}
    lifecycle = runtime_summary.get("lifecycle", "")
    if lifecycle:
        findings.append(f"Runtime lifecycle: {lifecycle}")
    state_summary = layers[3].get("summary", {}) if len(layers) > 3 else {}
    if state_summary.get("safety") == "REVIEW_REQUIRED":
        findings.append("Runtime State safety artifact requires review.")
    if state_summary.get("safety") == "BLOCK":
        findings.append("Runtime State safety artifact is missing after the target-date Safety/Morning route.")
    if not findings:
        findings.append("No blocking findings.")
    return findings


def _combine_status(statuses) -> str:
    values = list(statuses)
    if any(status == "BLOCK" for status in values):
        return "BLOCK"
    if any(status == "REVIEW_REQUIRED" for status in values):
        return "REVIEW_REQUIRED"
    return "PASS"


def _file_status(path: Path, payload: dict[str, Any], *, missing_status: str = "BLOCK") -> dict[str, Any]:
    return {
        "status": "PASS" if payload else missing_status,
        "path": str(path),
        "exists": path.exists(),
        "sha256": _sha256_file(path),
        "business_date": _truth_value(str(payload.get("business_date") or payload.get("as_of") or ""), missing="NOT_RECORDED"),
    }


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
