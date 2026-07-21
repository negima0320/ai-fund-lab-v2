from __future__ import annotations

import pickle
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import file_hash, read_json, stable_json_hash, validate_artifact_against_schema, write_json
from ai_fund_lab_v2.ai_lifecycle.candidate_validator import validate_candidate_primary
from ai_fund_lab_v2.ai_lifecycle.calibration_hash_inventory import validate_hash_inventory
from ai_fund_lab_v2.ai_lifecycle.opportunity_validator import validate_opportunity_primary
from ai_fund_lab_v2.ai_lifecycle.temporal_robustness_validator import review_recent_holdout
from ai_fund_lab_v2.ai_lifecycle.training_pipeline import transform_features
from ai_fund_lab_v2.ai_lifecycle.validation_artifact_writer import build_hash_inventory, write_validation_artifact


ValidationMode = Literal["FORMAL_VALIDATION", "FIXTURE_SMOKE"]
CREATED_AT = "2026-07-20T00:00:00+09:00"
VALIDATION_RUN_ID = "phase19_ad_u5_formal_validation_7b36f4d2a95e1c6b"
DEFAULT_REPORT_DIR = Path("reports/phase19_ad_u5_formal_validation")
DEFAULT_OUTPUT_DIR = Path(".runtime/ai_lifecycle/validation_outputs") / VALIDATION_RUN_ID
DEFAULT_SCHEMA_DIR = Path("schemas/ai_lifecycle")
POLICY_PATH = Path(".runtime/ai_lifecycle/policies/model_quality/phase19_ad_u3_d_model_quality_policy/model_quality_policy.json")
U4A_DIR = Path("reports/phase19_ad_u4_a_calibration_human_decision_and_hash_reconciliation")
U4D_DIR = Path("reports/phase19_ad_u4_d_formal_calibration_execution")
CALIBRATION_OUTPUT_DIR = Path(".runtime/ai_lifecycle/calibration_outputs/phase19_ad_u4_d_formal_calibration_0d5fdc96b879d5f1")

COMPONENTS = {
    "candidate": {
        "component": "Candidate",
        "resolved": Path("reports/phase19_ad_u3_a_contract_only_dataset_input_resolver/candidate_resolved_training_input.json"),
        "training_artifact": Path("reports/phase19_ad_u3_k_corrective_bootstrap_training/candidate_corrective_training_artifact.json"),
        "scaler_artifact": Path("reports/phase19_ad_u3_k_corrective_bootstrap_training/candidate_scaler_artifact.json"),
        "calibration_artifact": CALIBRATION_OUTPUT_DIR / "candidate/candidate_calibration_artifact.json",
        "model_file": Path(".runtime/ai_lifecycle/training_outputs/phase19_ad_u3_k_corrective_bootstrap_7cc6dfbfbf7899fa/candidate/model.pkl"),
        "scaler_file": Path(".runtime/ai_lifecycle/training_outputs/phase19_ad_u3_k_corrective_bootstrap_7cc6dfbfbf7899fa/candidate/scaler.pkl"),
        "requirements": "candidate_requirements",
    },
    "opportunity": {
        "component": "Opportunity",
        "resolved": Path("reports/phase19_ad_u3_a_contract_only_dataset_input_resolver/opportunity_resolved_training_input.json"),
        "training_artifact": Path("reports/phase19_ad_u3_k_corrective_bootstrap_training/opportunity_corrective_training_artifact.json"),
        "scaler_artifact": Path("reports/phase19_ad_u3_k_corrective_bootstrap_training/opportunity_scaler_artifact.json"),
        "calibration_artifact": CALIBRATION_OUTPUT_DIR / "opportunity/opportunity_calibration_artifact.json",
        "model_file": Path(".runtime/ai_lifecycle/training_outputs/phase19_ad_u3_k_corrective_bootstrap_7cc6dfbfbf7899fa/opportunity/model.pkl"),
        "scaler_file": Path(".runtime/ai_lifecycle/training_outputs/phase19_ad_u3_k_corrective_bootstrap_7cc6dfbfbf7899fa/opportunity/scaler.pkl"),
        "requirements": "opportunity_requirements",
    },
}


class FormalValidationRunnerError(ValueError):
    """Fail-closed error for formal validation boundary violations."""


@dataclass(frozen=True)
class FormalValidationRequest:
    mode: ValidationMode
    report_dir: Path = DEFAULT_REPORT_DIR
    output_dir: Path = DEFAULT_OUTPUT_DIR
    schema_dir: Path = DEFAULT_SCHEMA_DIR


def _load_pickle(path: Path) -> Any:
    with path.open("rb") as handle:
        return pickle.load(handle)


def _window_frame(resolved: dict[str, Any], window_name: str) -> pd.DataFrame:
    dataset = pd.read_parquet(resolved["dataset_path"])
    target_date = dataset["target_date"].astype(str)
    window = resolved["split_definition"][window_name]
    return dataset[(target_date >= str(window["start"])) & (target_date <= str(window["end"]))].copy()


def _matrix(frame: pd.DataFrame, feature_order: list[str], model_payload: dict[str, Any], scaler_payload: dict[str, Any]) -> np.ndarray:
    raw = transform_features(frame, feature_order, model_payload["preprocessing"])
    result = np.array(raw, dtype=np.float64, copy=True)
    index_by_feature = {feature: idx for idx, feature in enumerate(scaler_payload["input_feature_columns"])}
    scaled_indices = [index_by_feature[column] for column in scaler_payload["scaled_feature_columns"]]
    if scaled_indices:
        result[:, scaled_indices] = scaler_payload["scaler"].transform(result[:, scaled_indices])
    return result


def _preflight_component(key: str, policy: dict[str, Any]) -> dict[str, Any]:
    info = COMPONENTS[key]
    resolved = read_json(info["resolved"])
    training_artifact = read_json(info["training_artifact"])
    scaler_artifact = read_json(info["scaler_artifact"])
    calibration_artifact = read_json(info["calibration_artifact"])
    reasons: list[str] = []
    if training_artifact.get("artifact_status") != "TRAINING_OUTPUT":
        reasons.append("training_artifact_not_training_output")
    if training_artifact.get("runtime_eligibility") is not False or training_artifact.get("accepted") is not False:
        reasons.append("training_artifact_runtime_or_accepted")
    if file_hash(info["model_file"]) != calibration_artifact.get("source_model_hash"):
        reasons.append("source_model_raw_sha256_mismatch")
    if file_hash(info["scaler_file"]) != calibration_artifact.get("source_scaler_hash"):
        reasons.append("source_scaler_raw_sha256_mismatch")
    if list(training_artifact.get("feature_columns", [])) != list(calibration_artifact.get("feature_order", [])):
        reasons.append("feature_order_mismatch")
    if resolved.get("dataset_revision_id") != training_artifact.get("dataset_revision_id"):
        reasons.append("dataset_revision_mismatch")
    if resolved.get("split_id") != training_artifact.get("split_id"):
        reasons.append("split_id_mismatch")
    if calibration_artifact.get("dataset_usage_contract_hash") != read_json(U4A_DIR / "calibration_dataset_usage_contract.json").get("contract_hash"):
        reasons.append("dataset_usage_contract_mismatch")
    schema_validation = validate_artifact_against_schema(calibration_artifact, DEFAULT_SCHEMA_DIR / "calibration_artifact.schema.json")
    hash_validation = validate_hash_inventory(
        artifact=calibration_artifact,
        artifact_path=info["calibration_artifact"],
        source_model_file=info["model_file"],
        source_scaler_file=info["scaler_file"],
    )
    if schema_validation["status"] != "PASS":
        reasons.append("calibration_artifact_schema_mismatch")
    if hash_validation["status"] != "PASS":
        reasons.append("calibration_hash_inventory_mismatch")
    return {
        "status": "PASS" if not reasons else "BLOCK",
        "reason_codes": reasons,
        "resolved": resolved,
        "training_artifact": training_artifact,
        "scaler_artifact": scaler_artifact,
        "calibration_artifact": calibration_artifact,
        "schema_validation": schema_validation,
        "hash_validation": hash_validation,
        "source_hashes": {
            "model_raw_sha256": file_hash(info["model_file"]),
            "scaler_raw_sha256": file_hash(info["scaler_file"]),
            "calibration_artifact_sha256": file_hash(info["calibration_artifact"]),
        },
        "policy_requirements": policy[info["requirements"]],
    }


def _candidate_scores(window_name: str, preflight: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, int]:
    frame = _window_frame(preflight["resolved"], window_name)
    model_payload = _load_pickle(COMPONENTS["candidate"]["model_file"])
    scaler_payload = _load_pickle(COMPONENTS["candidate"]["scaler_file"])
    matrix = _matrix(frame, list(preflight["calibration_artifact"]["feature_order"]), model_payload, scaler_payload)
    raw_scores = model_payload["model"].decision_function(matrix)
    labels = frame[preflight["training_artifact"]["label_column"]].astype(bool).astype(int).to_numpy()
    business_days = int(frame["target_date"].nunique())
    return raw_scores, labels, business_days


def _opportunity_scores(window_name: str, preflight: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, int]:
    frame = _window_frame(preflight["resolved"], window_name)
    model_payload = _load_pickle(COMPONENTS["opportunity"]["model_file"])
    scaler_payload = _load_pickle(COMPONENTS["opportunity"]["scaler_file"])
    matrix = _matrix(frame, list(preflight["calibration_artifact"]["feature_order"]), model_payload, scaler_payload)
    raw_predictions = model_payload["model"].predict(matrix)
    target = pd.to_numeric(frame[preflight["training_artifact"]["label_column"]], errors="coerce").fillna(0.0).to_numpy(dtype=np.float64)
    business_days = int(frame["target_date"].nunique())
    return raw_predictions, target, business_days


def _formal_policy() -> dict[str, Any]:
    return {
        "schema_version": "phase19_ad_u5_formal_evaluation_policy.v1",
        "formal_cycle_number": 1,
        "test_previously_accessed": False,
        "recent_holdout_previously_accessed": False,
        "result_driven_tuning_allowed": False,
        "frozen_after_start": ["Model", "Scaler", "Calibration parameters", "Feature order", "Evaluation metric", "Quality threshold", "Decision threshold", "Dataset window", "Sample filter"],
        "rerun_policy": "execution failure rerun only; quality failure requires corrective generation review",
    }


def run_formal_validation(request: FormalValidationRequest) -> dict[str, Any]:
    if request.mode != "FORMAL_VALIDATION":
        raise FormalValidationRunnerError("unsupported_validation_mode")
    request.report_dir.mkdir(parents=True, exist_ok=True)
    request.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    policy = read_json(POLICY_PATH)
    formal_policy = _formal_policy()
    write_json(request.report_dir / "formal_evaluation_policy_materialization.json", {**formal_policy, "status": "PASS"})
    candidate_preflight = _preflight_component("candidate", policy)
    opportunity_preflight = _preflight_component("opportunity", policy)
    preflight = {
        "status": "PASS" if candidate_preflight["status"] == "PASS" and opportunity_preflight["status"] == "PASS" else "BLOCK",
        "candidate": {k: v for k, v in candidate_preflight.items() if k not in {"resolved", "training_artifact", "scaler_artifact", "calibration_artifact"}},
        "opportunity": {k: v for k, v in opportunity_preflight.items() if k not in {"resolved", "training_artifact", "scaler_artifact", "calibration_artifact"}},
        "model_quality_policy_hash": policy["policy_hash"],
        "validation_run_id": VALIDATION_RUN_ID,
    }
    write_json(request.report_dir / "preflight_results.json", preflight)
    if preflight["status"] != "PASS":
        return {"status": "BLOCK", "preflight": preflight, "test_accessed": False}

    recorded_warnings: list[dict[str, str]] = []
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        candidate_raw, candidate_labels, candidate_days = _candidate_scores("test", candidate_preflight)
        candidate = validate_candidate_primary(
            raw_scores=candidate_raw,
            labels=candidate_labels,
            calibration_parameters=candidate_preflight["calibration_artifact"]["calibration_parameters"],
            policy_requirements=policy["candidate_requirements"],
            business_days=candidate_days,
        )
        opportunity_raw, opportunity_target, opportunity_days = _opportunity_scores("test", opportunity_preflight)
        opportunity = validate_opportunity_primary(
            raw_predictions=opportunity_raw,
            target=opportunity_target,
            calibration_parameters=opportunity_preflight["calibration_artifact"]["calibration_parameters"],
            policy_requirements=policy["opportunity_requirements"],
            business_days=opportunity_days,
        )
    recorded_warnings = [{"category": record.category.__name__, "message": str(record.message)} for record in records]
    candidate_pass = candidate["status"] == "CANDIDATE_FORMAL_VALIDATION_PASS"
    opportunity_pass = opportunity["status"] == "OPPORTUNITY_FORMAL_VALIDATION_PASS"
    candidate_review = candidate["status"] == "CANDIDATE_FORMAL_VALIDATION_REVIEW_REQUIRED"
    opportunity_review = opportunity["status"] == "OPPORTUNITY_FORMAL_VALIDATION_REVIEW_REQUIRED"
    primary_pass = candidate_pass and opportunity_pass
    write_json(request.report_dir / "candidate_primary_metrics.json", candidate["metrics"])
    write_json(
        request.report_dir / "candidate_primary_quality_gate.json",
        {"status": candidate["status"], "checks": candidate["checks"], "policy_scope_resolution": candidate["policy_scope_resolution"]},
    )
    write_json(request.report_dir / "candidate_prediction_distribution.json", candidate["metrics"]["probability_distribution"])
    write_json(request.report_dir / "candidate_calibration_quality.json", {k: candidate["metrics"][k] for k in ["brier_score", "log_loss", "expected_calibration_error", "calibration_curve", "roc_auc", "pr_auc"]})
    write_json(request.report_dir / "opportunity_primary_metrics.json", opportunity["metrics"])
    write_json(
        request.report_dir / "opportunity_primary_quality_gate.json",
        {"status": opportunity["status"], "checks": opportunity["checks"], "policy_scope_resolution": opportunity["policy_scope_resolution"]},
    )
    write_json(request.report_dir / "opportunity_prediction_distribution.json", {"raw_prediction": opportunity["metrics"]["raw_prediction_distribution"], "normalized_score": opportunity["metrics"]["normalized_score_distribution"]})
    combined = {
        "status": "PRIMARY_FORMAL_VALIDATION_PASS" if primary_pass else ("PRIMARY_FORMAL_VALIDATION_REVIEW_REQUIRED" if candidate_review or opportunity_review else "PRIMARY_FORMAL_VALIDATION_FAIL"),
        "policy": policy["approved_policy"],
        "candidate_status": candidate["status"],
        "opportunity_status": opportunity["status"],
        "component_override_rule": "components evaluated independently; one component cannot hide the other",
    }
    write_json(request.report_dir / "combined_quality_gate.json", combined)

    recent_decision = {
        "status": "EXECUTED" if primary_pass else "NOT_EXECUTED",
        "reason": "Primary test gate PASS" if primary_pass else "Primary combined gate did not PASS",
        "recent_holdout_is_second_formal_validation": False,
    }
    write_json(request.report_dir / "recent_holdout_access_decision.json", recent_decision)
    candidate_recent: dict[str, Any] | None = None
    opportunity_recent: dict[str, Any] | None = None
    recent_review: dict[str, Any]
    if primary_pass:
        cand_raw_h, cand_labels_h, cand_days_h = _candidate_scores("recent_holdout", candidate_preflight)
        cand_h = validate_candidate_primary(
            raw_scores=cand_raw_h,
            labels=cand_labels_h,
            calibration_parameters=candidate_preflight["calibration_artifact"]["calibration_parameters"],
            policy_requirements={**policy["candidate_requirements"], "minimum_test_rows": policy["candidate_requirements"]["minimum_recent_holdout_rows"], "minimum_test_business_days": policy["candidate_requirements"]["minimum_recent_holdout_business_days"]},
            business_days=cand_days_h,
        )
        opp_raw_h, opp_target_h, opp_days_h = _opportunity_scores("recent_holdout", opportunity_preflight)
        opp_h = validate_opportunity_primary(
            raw_predictions=opp_raw_h,
            target=opp_target_h,
            calibration_parameters=opportunity_preflight["calibration_artifact"]["calibration_parameters"],
            policy_requirements={**policy["opportunity_requirements"], "minimum_test_rows": policy["opportunity_requirements"]["minimum_recent_holdout_rows"], "minimum_test_business_days": policy["opportunity_requirements"]["minimum_recent_holdout_business_days"]},
            business_days=opp_days_h,
        )
        candidate_recent = cand_h["metrics"]
        opportunity_recent = opp_h["metrics"]
        recent_review = review_recent_holdout(candidate_metrics=candidate_recent, opportunity_metrics=opportunity_recent, policy=policy)
    else:
        recent_review = {"status": "NOT_EXECUTED", "reason_codes": ["primary_formal_validation_not_passed"], "generation_eligibility": False}
    write_json(request.report_dir / "candidate_recent_holdout_metrics.json", candidate_recent or {"status": "NOT_EXECUTED"})
    write_json(request.report_dir / "opportunity_recent_holdout_metrics.json", opportunity_recent or {"status": "NOT_EXECUTED"})
    write_json(request.report_dir / "recent_holdout_robustness_review.json", recent_review)

    final_status = "PASS" if primary_pass and recent_review["status"] == "PASS" else ("REVIEW_REQUIRED" if (candidate_review or opportunity_review or (primary_pass and recent_review["status"] == "REVIEW_REQUIRED")) else "FAIL")
    generation_eligibility = final_status == "PASS"
    metric_payload = {"candidate": candidate["metrics"], "opportunity": opportunity["metrics"], "combined": combined, "recent_holdout": recent_review}
    artifact = {
        "artifact_id": f"formal_validation_{VALIDATION_RUN_ID[-16:]}",
        "artifact_type": "FORMAL_VALIDATION",
        "artifact_version": "phase19_ad_u5_formal_validation.v1",
        "artifact_status": "FORMAL_VALIDATION_PASS" if final_status == "PASS" else ("REVIEW_REQUIRED" if final_status == "REVIEW_REQUIRED" else "FORMAL_VALIDATION_FAIL"),
        "created_at": CREATED_AT,
        "producer": "ai_fund_lab_v2.ai_lifecycle.formal_validation_runner",
        "source_phase": "PHASE19_AD_U5",
        "component": "Validation",
        "generation_candidate_id": None,
        "schema_version": "phase19_ad_u5_formal_validation_artifact.v1",
        "authority": "Formal Validation output; not Runtime authority and not Accepted Generation",
        "validation_run_id": VALIDATION_RUN_ID,
        "formal_cycle_number": 1,
        "formal_validation_policy": formal_policy,
        "source_bindings": {
            "candidate_training_artifact": candidate_preflight["training_artifact"]["artifact_id"],
            "candidate_calibration_artifact": candidate_preflight["calibration_artifact"]["artifact_id"],
            "opportunity_training_artifact": opportunity_preflight["training_artifact"]["artifact_id"],
            "opportunity_calibration_artifact": opportunity_preflight["calibration_artifact"]["artifact_id"],
        },
        "validated_artifact_ids": [
            candidate_preflight["training_artifact"]["artifact_id"],
            candidate_preflight["calibration_artifact"]["artifact_id"],
            opportunity_preflight["training_artifact"]["artifact_id"],
            opportunity_preflight["calibration_artifact"]["artifact_id"],
        ],
        "validated_artifact_hashes": [
            candidate_preflight["training_artifact"]["content_hash"],
            candidate_preflight["calibration_artifact"]["content_hash"],
            opportunity_preflight["training_artifact"]["content_hash"],
            opportunity_preflight["calibration_artifact"]["content_hash"],
        ],
        "dataset_usage_contract_hash": candidate_preflight["calibration_artifact"]["dataset_usage_contract_hash"],
        "model_quality_policy_hash": policy["policy_hash"],
        "candidate_result": {"status": candidate["status"], "checks": candidate["checks"]},
        "opportunity_result": {"status": opportunity["status"], "checks": opportunity["checks"]},
        "combined_quality_gate": combined,
        "recent_holdout_review": recent_review,
        "window_usage": {"test_accessed": True, "recent_holdout_accessed": bool(primary_pass), "train_accessed_for_fit": False, "validation_accessed_for_fit": False},
        "runtime_eligibility": False,
        "generation_eligibility": generation_eligibility,
        "accepted": False,
        "hash_inventory": {},
        "content_hash": "0" * 64,
    }
    artifact["hash_inventory"] = build_hash_inventory(
        artifact=artifact,
        candidate_calibration_artifact_path=COMPONENTS["candidate"]["calibration_artifact"],
        opportunity_calibration_artifact_path=COMPONENTS["opportunity"]["calibration_artifact"],
        source_model_files=[COMPONENTS["candidate"]["model_file"], COMPONENTS["opportunity"]["model_file"]],
        source_scaler_files=[COMPONENTS["candidate"]["scaler_file"], COMPONENTS["opportunity"]["scaler_file"]],
        validation_policy_path=POLICY_PATH,
        metric_payload=metric_payload,
    )
    artifact_result = write_validation_artifact(artifact=artifact, path=request.output_dir / "formal_validation_artifact.json", schema_dir=request.schema_dir)
    write_json(request.report_dir / "formal_validation_artifact.json", artifact_result["artifact"])
    write_json(request.report_dir / "artifact_schema_validation.json", artifact_result["schema_validation"])
    write_json(request.report_dir / "hash_inventory_validation.json", {"status": artifact_result["status"], "hash_inventory": artifact_result["artifact"]["hash_inventory"]})
    write_json(request.report_dir / "artifact_binding_validation.json", {"status": "PASS", "preflight": preflight})
    access = {"status": "PASS", "test_accessed": True, "recent_holdout_accessed": bool(primary_pass), "recent_holdout_access_condition": "primary_pass_only", "train_fit_executed": False, "calibration_refit_executed": False}
    write_json(request.report_dir / "dataset_window_access_audit.json", access)
    non_mutation = {"status": "PASS", "training_mutation": False, "calibration_parameter_mutation": False, "unified_generation_creation": False, "accepted_decision_creation": False, "accepted_generation_creation": False, "runtime_pointer_write": False, "buy_restart": False, "broker_write": False, "ledger_mutation": False}
    write_json(request.report_dir / "non_mutation_evidence.json", non_mutation)
    result = {
        "status": final_status,
        "validation_run_id": VALIDATION_RUN_ID,
        "output_dir": str(request.output_dir),
        "candidate": {"status": candidate["status"], "metrics": candidate["metrics"]},
        "opportunity": {"status": opportunity["status"], "metrics": opportunity["metrics"]},
        "combined": combined,
        "recent_holdout_review": recent_review,
        "artifact_result": artifact_result,
        "warnings": recorded_warnings,
        "duration_seconds": round(time.perf_counter() - started, 6),
        "non_mutation": non_mutation,
    }
    write_json(request.output_dir / "formal_validation_run_manifest.json", result)
    write_json(request.report_dir / "execution_log.json", result)
    return result
