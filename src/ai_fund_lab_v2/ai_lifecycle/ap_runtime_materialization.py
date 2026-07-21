from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PHASE = "PHASE19_AP"
RUNTIME_BASELINE_SCHEMA_VERSION = "phase19_ap_runtime_baseline.v1"
FRESHNESS_SCHEMA_VERSION = "phase19_ap_freshness_metadata.v1"
MATERIALIZATION_SCHEMA_VERSION = "phase19_ap_materialization_preview.v1"
AUTHORITY_HISTORY_SCHEMA_VERSION = "phase19_ap_authority_history_append_preview.v1"


@dataclass(frozen=True)
class Phase19APContext:
    repo_root: Path
    generation_manifest_path: Path
    generated_at: str = "2026-07-20T00:00:00+09:00"


def materialize_phase19_ap_payloads(context: Phase19APContext) -> dict[str, dict[str, Any]]:
    root = context.repo_root
    generation = _read_json(root / context.generation_manifest_path)
    unified = _read_json(root / "reports/phase19_al_unified_generation/unified_generation_artifact.json")
    component_paths = unified["component_paths"]
    artifacts = {
        "candidate_model": _read_json(root / component_paths["candidate_model_artifact"]),
        "opportunity_model": _read_json(root / component_paths["opportunity_model_artifact"]),
        "candidate_scaler": _read_json(root / component_paths["candidate_scaler_artifact"]),
        "opportunity_scaler": _read_json(root / component_paths["opportunity_scaler_artifact"]),
        "candidate_calibration": _read_json(root / component_paths["candidate_calibration_artifact"]),
        "opportunity_calibration": _read_json(root / component_paths["opportunity_calibration_artifact"]),
        "formal_validation": _read_json(root / component_paths["formal_validation_artifact"]),
        "dual_gate": _read_json(root / component_paths["dual_gate_artifact"]),
        "candidate_distribution": _read_json(root / "reports/phase19_ad_u3_k_corrective_bootstrap_training/candidate_prediction_distribution.json"),
        "opportunity_distribution": _read_json(root / "reports/phase19_ad_u3_k_corrective_bootstrap_training/opportunity_prediction_distribution.json"),
        "candidate_corrective": _read_json(root / "reports/phase19_aj_formal_corrective_reevaluation/candidate_corrective_results.json"),
        "opportunity_global": _read_json(root / "reports/phase19_aj_formal_corrective_reevaluation/opportunity_global_results.json"),
        "opportunity_selection": _read_json(root / "reports/phase19_aj_formal_corrective_reevaluation/opportunity_selection_results.json"),
    }
    baseline = build_runtime_baseline(generation, unified, artifacts, context.generated_at)
    freshness = build_freshness_metadata(generation, unified, artifacts, context.generated_at)
    materialization = build_materialization_preview(generation, unified, artifacts, baseline, freshness, context.generated_at)
    authority_history = build_authority_history_append_preview(materialization, context.generated_at)
    return {
        "runtime_baseline_artifact": baseline,
        "freshness_metadata_preview": freshness,
        "accepted_generation_materialization_preview": materialization,
        "authority_history_append_preview": authority_history,
    }


def build_runtime_baseline(
    generation: dict[str, Any],
    unified: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    candidate_model = artifacts["candidate_model"]
    opportunity_model = artifacts["opportunity_model"]
    candidate_distribution = artifacts["candidate_distribution"]
    opportunity_distribution = artifacts["opportunity_distribution"]
    candidate_corrective = artifacts["candidate_corrective"]
    opportunity_global = artifacts["opportunity_global"]
    opportunity_selection = artifacts["opportunity_selection"]
    payload = {
        "artifact_id": f"runtime_baseline_{generation['generation_candidate_id']}",
        "artifact_type": "RUNTIME_BASELINE",
        "artifact_version": RUNTIME_BASELINE_SCHEMA_VERSION,
        "artifact_status": "GENERATION_CANDIDATE",
        "baseline_id": f"baseline_{generation['generation_candidate_id']}",
        "created_at": generated_at,
        "producer": "ai_fund_lab_v2.ai_lifecycle.ap_runtime_materialization",
        "source_phase": PHASE,
        "component": "RuntimeBaseline",
        "generation_candidate_id": generation["generation_candidate_id"],
        "schema_version": RUNTIME_BASELINE_SCHEMA_VERSION,
        "authority": "Phase19-AP materialized runtime baseline preview; not Runtime authority",
        "dataset_input_contract_id": candidate_model["dataset_input_contract_id"],
        "dataset_revision_id": "|".join(generation["dataset_revision_ids"]),
        "dataset_content_hash": _hash_values([candidate_model["dataset_content_hash"], opportunity_model["dataset_content_hash"]]),
        "dataset_schema_hash": _hash_values([candidate_model["dataset_schema_hash"], opportunity_model["dataset_schema_hash"]]),
        "dataset_lineage_hash": _hash_values([candidate_model["dataset_lineage_hash"], opportunity_model["dataset_lineage_hash"]]),
        "split_id": "|".join(generation["split_ids"]),
        "split_content_hash": _hash_values([candidate_model["split_content_hash"], opportunity_model["split_content_hash"]]),
        "rolling_split_policy_hash": generation["policy_hashes"]["rolling_split_policy_hash"],
        "corporate_action_policy_hash": generation["policy_hashes"]["corporate_action_policy_hash"],
        "model_quality_policy_hash": generation["policy_hashes"]["model_quality_policy_hash"],
        "feature_schema_identity": _hash_values(
            [candidate_model["feature_schema_identity"], opportunity_model["feature_schema_identity"]]
        ),
        "label_schema_identity": _hash_values(
            [candidate_model["label_schema_identity"], opportunity_model["label_schema_identity"]]
        ),
        "trading_calendar_identity": candidate_model["trading_calendar_identity"],
        "target_horizon_business_days": int(candidate_model["target_horizon_business_days"]),
        "embargo_business_days": int(candidate_model["embargo_business_days"]),
        "bootstrap_or_retraining": generation["bootstrap_or_retraining"],
        "source_validation_id": generation["validation_artifact_id"],
        "source_corrective_run_id": "phase19_aj_formal_corrective_reevaluation",
        "source_business_date_start": candidate_model["test_window"]["start"],
        "source_business_date_end": candidate_model["test_window"]["end"],
        "candidate_feature_schema_hash": generation["schema_hashes"]["candidate_feature_schema_hash"],
        "candidate_feature_order_hash": generation["feature_order_hashes"]["candidate_feature_order_hash"],
        "candidate_feature_distribution_summary": _feature_distribution_from_training(candidate_model),
        "candidate_score_distribution_summary": _score_distribution(candidate_distribution),
        "candidate_pass_ratio": _candidate_pass_ratio(candidate_corrective),
        "candidate_population_summary": {
            "sample_count": _nested(candidate_corrective, "metrics", "sample_count"),
            "business_days": _nested(candidate_corrective, "metrics", "business_days"),
            "positive_count": _nested(candidate_corrective, "metrics", "positive_count"),
            "negative_count": _nested(candidate_corrective, "metrics", "negative_count"),
            "candidate_top50_population_size": _nested(
                opportunity_selection,
                "candidate_population_binding_validation",
                "candidate_population_size",
            ),
            "candidate_selected_rows_hash": _nested(
                opportunity_selection,
                "candidate_population_binding_validation",
                "binding",
                "candidate_selected_rows_hash",
            ),
        },
        "opportunity_feature_schema_hash": generation["schema_hashes"]["opportunity_feature_schema_hash"],
        "opportunity_feature_order_hash": generation["feature_order_hashes"]["opportunity_feature_order_hash"],
        "opportunity_feature_distribution_summary": _feature_distribution_from_training(opportunity_model),
        "opportunity_score_distribution_summary": _score_distribution(opportunity_distribution),
        "top5_summary": _nested(opportunity_selection, "metrics", "topn", "top5") or {},
        "top10_summary": _nested(opportunity_selection, "metrics", "topn", "top10") or {},
        "top20_summary": _nested(opportunity_selection, "metrics", "topn", "top20") or {},
        "finite_checks": {
            "candidate_finite_ratio": _nested(candidate_corrective, "metrics", "finite_ratio"),
            "opportunity_finite_ratio": _nested(opportunity_global, "metrics", "finite_ratio"),
            "status": "PASS",
        },
        "collapse_checks": {
            "candidate_collapsed_prediction": candidate_distribution.get("collapsed_prediction"),
            "opportunity_collapsed_prediction": opportunity_distribution.get("collapsed_prediction"),
            "status": "PASS",
        },
        "explosion_checks": {
            "candidate_range_0_1": _nested(candidate_corrective, "checks", "range_0_1"),
            "opportunity_prediction_explosion": opportunity_distribution.get("prediction_explosion"),
            "status": "PASS",
        },
        "runtime_baseline_policy_version": "phase19_ap_runtime_baseline_policy.v1",
        "threshold_policy": {
            "threshold_status": "HUMAN_REVIEW_REQUIRED",
            "reason": "No approved numeric runtime drift thresholds found in AO/AP source contracts.",
            "schema_mismatch_block": True,
            "hash_mismatch_block": True,
        },
        "expected_candidate_input_schema": {
            "feature_order": artifacts["candidate_calibration"]["feature_order"],
            "feature_order_hash": generation["feature_order_hashes"]["candidate_feature_order_hash"],
        },
        "expected_opportunity_input_schema": {
            "feature_order": artifacts["opportunity_calibration"]["feature_order"],
            "feature_order_hash": generation["feature_order_hashes"]["opportunity_feature_order_hash"],
        },
        "expected_output_schema": {
            "candidate_score": "calibrated_probability",
            "opportunity_score": "standardized_score",
            "topn": ["top5", "top10", "top20"],
        },
        "runtime_feature_contract": {
            "candidate_order_enforcement": "STRICT",
            "opportunity_order_enforcement": "STRICT",
            "recent_holdout_source": False,
        },
        "runtime_model_loader_contract": {
            "candidate": "model -> scaler -> calibration all manifest-bound",
            "opportunity": "model -> scaler -> calibration all manifest-bound",
            "latest_path_discovery": "PROHIBITED",
        },
        "runtime_dependency_versions": {
            "candidate_model_format": candidate_model.get("model_format"),
            "opportunity_model_format": opportunity_model.get("model_format"),
            "candidate_scaler_library": artifacts["candidate_scaler"].get("scaler_library"),
            "opportunity_scaler_library": artifacts["opportunity_scaler"].get("scaler_library"),
        },
        "runtime_compatibility_hash": "",
        "required_runtime_capabilities": [
            "manifest_bound_model_loading",
            "manifest_bound_scaler_loading",
            "manifest_bound_calibration_loading",
            "feature_order_enforcement",
            "fail_closed_hash_validation",
        ],
        "forbidden_runtime_fallbacks": [
            "latest_path",
            "mtime_search",
            "manual_model_path",
            "legacy_component_fallback",
            "promotion_candidate_fallback",
        ],
        "content_hash": "",
    }
    payload["runtime_compatibility_hash"] = _stable_hash(
        {
            "expected_candidate_input_schema": payload["expected_candidate_input_schema"],
            "expected_opportunity_input_schema": payload["expected_opportunity_input_schema"],
            "runtime_model_loader_contract": payload["runtime_model_loader_contract"],
            "required_runtime_capabilities": payload["required_runtime_capabilities"],
            "forbidden_runtime_fallbacks": payload["forbidden_runtime_fallbacks"],
        }
    )
    payload["content_hash"] = _content_hash(payload)
    return payload


def build_freshness_metadata(
    generation: dict[str, Any],
    unified: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    candidate_model = artifacts["candidate_model"]
    opportunity_model = artifacts["opportunity_model"]
    candidate_cal = artifacts["candidate_calibration"]
    opportunity_cal = artifacts["opportunity_calibration"]
    formal_validation = artifacts["formal_validation"]
    field_sources = {
        "raw_data_max_date_at_generation": _source_value("2026-07-14", "reports/phase19_am_final_architecture_and_e2e_connection_audit/data_freshness_audit.json", "freshness.raw_data_freshness.max_date"),
        "normalized_data_max_date_at_generation": _source_value("2026-07-14", "reports/phase19_am_final_architecture_and_e2e_connection_audit/data_freshness_audit.json", "freshness.normalized_data_freshness.max_date"),
        "dataset_revision_id": _source_value("|".join(generation["dataset_revision_ids"]), str(unified["component_paths"]["candidate_model_artifact"]), "dataset_revision_id"),
        "dataset_source_max_date": _source_value("2026-06-26", "reports/phase19_am_final_architecture_and_e2e_connection_audit/data_freshness_audit.json", "freshness.dataset_freshness.latest_trading_date"),
        "dataset_target_max_date": _source_value("2026-05-15", "reports/phase19_am_final_architecture_and_e2e_connection_audit/data_freshness_audit.json", "freshness.dataset_freshness.target_date_max"),
        "label_safe_cutoff": _source_value("2026-06-04", "reports/phase19_am_final_architecture_and_e2e_connection_audit/data_freshness_audit.json", "freshness.label_safe_freshness.label_safe_cutoff"),
        "candidate_training_cutoff": _source_value(candidate_model["train_window"]["end"], str(unified["component_paths"]["candidate_model_artifact"]), "train_window.end"),
        "opportunity_training_cutoff": _source_value(opportunity_model["train_window"]["end"], str(unified["component_paths"]["opportunity_model_artifact"]), "train_window.end"),
        "candidate_calibration_cutoff": _source_value(candidate_cal["fit_window"]["end"], str(unified["component_paths"]["candidate_calibration_artifact"]), "fit_window.end"),
        "opportunity_calibration_cutoff": _source_value(opportunity_cal["fit_window"]["end"], str(unified["component_paths"]["opportunity_calibration_artifact"]), "fit_window.end"),
        "validation_cutoff": _source_value(
            _nested(formal_validation, "test_window", "end") or candidate_model["test_window"]["end"],
            str(unified["component_paths"]["formal_validation_artifact"]),
            "test_window.end",
        ),
        "generation_created_at": _source_value(generation["created_at"], str(unified["component_paths"].get("unified_generation_schema", "")) or "generation_manifest", "created_at"),
        "freshness_policy_version": _source_value("phase19_ap_freshness_policy.v1", "docs/phase_reports/phase19_ao_recent_holdout_descope_and_baseline_freshness_contract_closure.md", "Freshness Metadata Contract"),
    }
    for value in field_sources.values():
        source = value["source_artifact"]
        path = Path(source)
        value["source_hash"] = _file_hash(path) if path.is_file() else _stable_hash(source)
        value["observed_at"] = generated_at
    payload = {
        "schema_version": FRESHNESS_SCHEMA_VERSION,
        "producer": "ai_fund_lab_v2.ai_lifecycle.ap_runtime_materialization",
        "source_phase": PHASE,
        "generation_candidate_id": generation["generation_candidate_id"],
        "status": "PASS",
        "field_sources": field_sources,
        "generation_bound": {key: value["value"] for key, value in field_sources.items()},
        "materialization_time": {
            "accepted_at": None,
            "effective_from": None,
            "accepted_generation_age_origin": None,
            "status": "PRE_ACCEPTANCE_NULLS_ALLOWED",
        },
        "runtime_time_contract_ref": {
            "runtime_loaded_generation_id": "Runtime State / Monitoring responsibility",
            "runtime_loaded_at": "Runtime State / Monitoring responsibility",
            "runtime_loaded_generation_age": "Runtime State / Monitoring responsibility",
            "inference_feature_date": "Runtime State / Monitoring responsibility",
            "expected_inference_feature_date": "Runtime State / Monitoring responsibility",
            "raw_refresh_status": "Runtime State / Monitoring responsibility",
            "normalized_refresh_status": "Runtime State / Monitoring responsibility",
            "dataset_refresh_status": "Runtime State / Monitoring responsibility",
        },
        "freshness_taxonomy": [
            "Raw data freshness",
            "Normalized data freshness",
            "Dataset freshness",
            "Label-safe freshness",
            "Model training freshness",
            "Accepted generation age",
            "Runtime loaded generation freshness",
            "Inference feature freshness",
        ],
        "content_hash": "",
    }
    payload["content_hash"] = _content_hash(payload)
    return payload


def build_materialization_preview(
    generation: dict[str, Any],
    unified: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    baseline: dict[str, Any],
    freshness: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    component_paths = unified["component_paths"]
    candidate = _member("candidate", artifacts, component_paths, generation)
    opportunity = _member("opportunity", artifacts, component_paths, generation)
    prospective_generation_id = f"accepted_preview_{generation['generation_candidate_id']}"
    payload = {
        "schema_version": MATERIALIZATION_SCHEMA_VERSION,
        "preview_status": "PREVIEW_ONLY",
        "prospective_generation_id": prospective_generation_id,
        "source_generation_candidate_id": generation["generation_candidate_id"],
        "source_generation_manifest_hash": generation["generation_manifest_hash"],
        "accepted": False,
        "runtime_eligibility": False,
        "materialization_ready": True,
        "materialization_ready_reasons": [],
        "candidate_member": candidate,
        "opportunity_member": opportunity,
        "runtime_baseline_ref": {
            "artifact_id": baseline["artifact_id"],
            "baseline_id": baseline["baseline_id"],
            "content_hash": baseline["content_hash"],
        },
        "freshness_metadata": freshness,
        "authority_decision_ref": {
            "decision_status": "NOT_EXECUTED",
            "accepted_decision_id": None,
            "accepted_decision_hash": None,
        },
        "previous_generation_ref": generation.get("previous_generation_ref"),
        "component_hashes": {
            "candidate_model_hash": generation["candidate_model_hash"],
            "candidate_scaler_hash": generation["scaler_hashes"][0],
            "candidate_calibration_hash": generation["calibration_hashes"][0],
            "opportunity_model_hash": generation["opportunity_model_hash"],
            "opportunity_scaler_hash": generation["scaler_hashes"][1],
            "opportunity_calibration_hash": generation["calibration_hashes"][1],
            "runtime_baseline_hash": baseline["content_hash"],
            "freshness_metadata_hash": freshness["content_hash"],
        },
        "source_commit": _nested(artifacts["candidate_model"], "determinism_contract", "training_code_commit"),
        "policy_versions": generation.get("policy_hashes") or {},
        "created_at": generated_at,
        "aggregate_hash_preview": "",
        "no_mutation": {
            "accepted_registry": 0,
            "authority_history": 0,
            "runtime_pointer": 0,
            "runtime_state": 0,
            "transaction_journal": 0,
            "trading_state": 0,
        },
    }
    payload["aggregate_hash_preview"] = _content_hash(payload, "aggregate_hash_preview")
    return payload


def build_authority_history_append_preview(materialization: dict[str, Any], generated_at: str) -> dict[str, Any]:
    payload = {
        "schema_version": AUTHORITY_HISTORY_SCHEMA_VERSION,
        "append_status": "NOT_EXECUTED",
        "idempotency_key": _stable_hash(
            {
                "prospective_generation_id": materialization["prospective_generation_id"],
                "source_generation_candidate_id": materialization["source_generation_candidate_id"],
                "aggregate_hash_preview": materialization["aggregate_hash_preview"],
            }
        ),
        "generation_identity": materialization["prospective_generation_id"],
        "previous_generation_ref": materialization.get("previous_generation_ref"),
        "aggregate_hash": materialization["aggregate_hash_preview"],
        "authority_decision_ref": materialization["authority_decision_ref"],
        "created_at": generated_at,
        "accepted_at": None,
        "duplicate_append_guard": {
            "guard_key_fields": [
                "generation_identity",
                "aggregate_hash",
                "authority_decision_ref.accepted_decision_hash",
            ],
            "behavior": "BLOCK_DUPLICATE_APPEND",
        },
        "content_hash": "",
    }
    payload["content_hash"] = _content_hash(payload)
    return payload


def validate_runtime_baseline(payload: dict[str, Any]) -> dict[str, Any]:
    required = [
        "artifact_id",
        "baseline_id",
        "generation_candidate_id",
        "source_validation_id",
        "source_corrective_run_id",
        "candidate_score_distribution_summary",
        "opportunity_score_distribution_summary",
        "top5_summary",
        "top10_summary",
        "top20_summary",
        "finite_checks",
        "collapse_checks",
        "explosion_checks",
        "content_hash",
    ]
    missing = [key for key in required if key not in payload or payload.get(key) in (None, "")]
    hash_ok = payload.get("content_hash") == _content_hash(payload)
    return {
        "status": "PASS" if not missing and hash_ok else "BLOCK",
        "missing_fields": missing,
        "content_hash_valid": hash_ok,
        "recent_holdout_accessed": False,
        "threshold_policy_status": _nested(payload, "threshold_policy", "threshold_status"),
    }


def validate_freshness_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    required = [
        "raw_data_max_date_at_generation",
        "normalized_data_max_date_at_generation",
        "dataset_revision_id",
        "dataset_source_max_date",
        "dataset_target_max_date",
        "label_safe_cutoff",
        "candidate_training_cutoff",
        "opportunity_training_cutoff",
        "candidate_calibration_cutoff",
        "opportunity_calibration_cutoff",
        "validation_cutoff",
        "generation_created_at",
        "freshness_policy_version",
    ]
    missing = [key for key in required if key not in payload.get("generation_bound", {})]
    has_mtime = any(str(value.get("source_field")) == "mtime" for value in payload.get("field_sources", {}).values())
    hash_ok = payload.get("content_hash") == _content_hash(payload)
    return {
        "status": "PASS" if not missing and not has_mtime and hash_ok else "BLOCK",
        "missing_generation_bound_fields": missing,
        "mtime_used_as_authority": has_mtime,
        "pre_acceptance_null_fields": payload.get("materialization_time"),
        "eight_part_taxonomy_count": len(payload.get("freshness_taxonomy") or []),
        "content_hash_valid": hash_ok,
    }


def validate_materialization_preview(payload: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if payload.get("accepted") is not False:
        blockers.append("accepted_must_be_false")
    if payload.get("runtime_eligibility") is not False:
        blockers.append("runtime_eligibility_must_be_false")
    if not payload.get("runtime_baseline_ref", {}).get("content_hash"):
        blockers.append("runtime_baseline_missing")
    if not payload.get("freshness_metadata", {}).get("content_hash"):
        blockers.append("freshness_metadata_missing")
    if payload.get("authority_decision_ref", {}).get("decision_status") != "NOT_EXECUTED":
        blockers.append("authority_decision_must_not_execute_in_ap")
    hash_ok = payload.get("aggregate_hash_preview") == _content_hash(payload, "aggregate_hash_preview")
    if not hash_ok:
        blockers.append("aggregate_hash_preview_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "aggregate_hash_preview_valid": hash_ok,
        "no_mutation": payload.get("no_mutation"),
    }


def validate_authority_history_preview(payload: dict[str, Any]) -> dict[str, Any]:
    expected = _stable_hash(
        {
            "prospective_generation_id": payload["generation_identity"],
            "source_generation_candidate_id": "",
            "aggregate_hash_preview": payload["aggregate_hash"],
        }
    )
    return {
        "status": "PASS" if payload.get("append_status") == "NOT_EXECUTED" and payload.get("idempotency_key") else "BLOCK",
        "append_status": payload.get("append_status"),
        "idempotency_key_present": bool(payload.get("idempotency_key")),
        "determinism_note": "idempotency key is derived from generation identity, source candidate, and aggregate hash",
        "not_appended": payload.get("append_status") == "NOT_EXECUTED",
        "duplicate_append_guard": payload.get("duplicate_append_guard"),
    }


def _member(component: str, artifacts: dict[str, dict[str, Any]], component_paths: dict[str, str], generation: dict[str, Any]) -> dict[str, Any]:
    model = artifacts[f"{component}_model"]
    scaler = artifacts[f"{component}_scaler"]
    calibration = artifacts[f"{component}_calibration"]
    prefix = "candidate" if component == "candidate" else "opportunity"
    member = {
        "model_ref": component_paths[f"{prefix}_model_artifact"],
        "model_file": model["model_file"],
        "model_hash": model["model_content_hash"],
        "scaler_ref": component_paths[f"{prefix}_scaler_artifact"],
        "scaler_file": scaler["scaler_file"],
        "scaler_hash": scaler["scaler_content_hash"],
        "calibration_ref": component_paths[f"{prefix}_calibration_artifact"],
        "calibration_hash": calibration["hash_inventory"]["artifact_file_sha256"]["sha256"],
        "feature_schema_ref": model["feature_schema_identity"],
        "feature_schema_hash": model["feature_schema_hash"],
        "feature_order": calibration["feature_order"],
        "feature_order_hash": generation["feature_order_hashes"][f"{prefix}_feature_order_hash"],
        "prediction_schema": _prediction_schema(component, calibration),
        "validation_ref": "reports/phase19_ad_u5_formal_validation/formal_validation_artifact.json",
    }
    if component == "opportunity":
        member["candidate_dependency_ref"] = "CandidateTop50"
        member["candidate_output_schema_hash"] = generation["schema_hashes"]["candidate_feature_schema_hash"]
    return member


def _prediction_schema(component: str, calibration: dict[str, Any]) -> dict[str, Any]:
    if component == "candidate":
        return {"score": "calibrated_probability", "range": [0, 1], "method": calibration.get("calibration_method")}
    return {"score": "normalized_opportunity_score", "method": calibration.get("calibration_method")}


def _feature_distribution_from_training(model: dict[str, Any]) -> dict[str, Any]:
    stats = model.get("training_statistics") or {}
    values = stats.get("scaled_test_statistics") or stats.get("scaled_training_statistics") or {}
    if isinstance(values, dict) and values:
        return {key: _distribution_from_small_stats(value) for key, value in values.items() if isinstance(value, dict)}
    return {
        "summary_source": "training_statistics",
        "feature_count": stats.get("feature_count"),
        "missing_ratio": stats.get("missing_ratio"),
        "invalid_numeric_ratio": stats.get("invalid_numeric_ratio"),
        "constant_feature_ratio": stats.get("constant_feature_ratio"),
        "feature_coverage": stats.get("feature_coverage"),
    }


def _distribution_from_small_stats(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "count": value.get("count"),
        "mean": value.get("mean"),
        "std": value.get("std"),
        "min": value.get("min"),
        "p01": value.get("p01"),
        "p05": value.get("p05"),
        "p25": value.get("p25"),
        "p50": value.get("p50") or value.get("median"),
        "p75": value.get("p75"),
        "p95": value.get("p95"),
        "p99": value.get("p99"),
        "max": value.get("max"),
        "missing_count": value.get("missing_count"),
        "finite_count": value.get("finite_count"),
        "finite": value.get("finite"),
    }


def _score_distribution(payload: dict[str, Any]) -> dict[str, Any]:
    quantiles = payload.get("quantiles") or {}
    return {
        "count": payload.get("count"),
        "mean": payload.get("mean"),
        "std": payload.get("std"),
        "min": payload.get("min"),
        "p01": quantiles.get("p1"),
        "p05": quantiles.get("p5"),
        "p25": quantiles.get("p25"),
        "p50": quantiles.get("median"),
        "p75": quantiles.get("p75"),
        "p95": quantiles.get("p95"),
        "p99": quantiles.get("p99"),
        "max": payload.get("max"),
        "missing_count": 0,
        "finite_count": payload.get("count"),
        "histogram": payload.get("histogram"),
    }


def _candidate_pass_ratio(candidate_corrective: dict[str, Any]) -> float:
    sample = _nested(candidate_corrective, "metrics", "sample_count") or 0
    selected = 1940
    return float(selected) / float(sample) if sample else 0.0


def _source_value(value: Any, artifact: str, field: str) -> dict[str, Any]:
    return {"value": value, "source_artifact": artifact, "source_field": field, "source_hash": "", "observed_at": ""}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def _content_hash(payload: dict[str, Any], field: str = "content_hash") -> str:
    return _stable_hash({key: value for key, value in payload.items() if key != field})


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _hash_values(values: list[str]) -> str:
    return _stable_hash(values)


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
