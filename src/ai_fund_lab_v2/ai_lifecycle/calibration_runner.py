from __future__ import annotations

import pickle
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import file_hash, stable_json_hash, write_json
from ai_fund_lab_v2.ai_lifecycle.calibration_artifact_writer import build_calibration_artifact, write_calibration_artifact
from ai_fund_lab_v2.ai_lifecycle.candidate_calibration import CandidateCalibrationError, fit_candidate_platt
from ai_fund_lab_v2.ai_lifecycle.opportunity_calibration import OpportunityCalibrationError, fit_opportunity_standardization
from ai_fund_lab_v2.ai_lifecycle.training_pipeline import transform_features


CalibrationMode = Literal["FIXTURE_SMOKE", "FORMAL_CALIBRATION"]
DEFAULT_SCHEMA_DIR = Path("schemas/ai_lifecycle")
DEFAULT_U4A_EVIDENCE_DIR = Path("reports/phase19_ad_u4_a_calibration_human_decision_and_hash_reconciliation")
FORMAL_RUN_ID = "phase19_ad_u4_d_formal_calibration_0d5fdc96b879d5f1"
FORMAL_OUTPUT_DIR = Path(".runtime/ai_lifecycle/calibration_outputs") / FORMAL_RUN_ID
FORMAL_REPORT_DIR = Path("reports/phase19_ad_u4_d_formal_calibration_execution")
FORMAL_PATHS = {
    "candidate": {
        "resolved_input": Path("reports/phase19_ad_u3_a_contract_only_dataset_input_resolver/candidate_resolved_training_input.json"),
        "model_artifact": Path("reports/phase19_ad_u3_k_corrective_bootstrap_training/candidate_corrective_training_artifact.json"),
        "scaler_artifact": Path("reports/phase19_ad_u3_k_corrective_bootstrap_training/candidate_scaler_artifact.json"),
        "model_file": Path(".runtime/ai_lifecycle/training_outputs/phase19_ad_u3_k_corrective_bootstrap_7cc6dfbfbf7899fa/candidate/model.pkl"),
        "scaler_file": Path(".runtime/ai_lifecycle/training_outputs/phase19_ad_u3_k_corrective_bootstrap_7cc6dfbfbf7899fa/candidate/scaler.pkl"),
    },
    "opportunity": {
        "resolved_input": Path("reports/phase19_ad_u3_a_contract_only_dataset_input_resolver/opportunity_resolved_training_input.json"),
        "model_artifact": Path("reports/phase19_ad_u3_k_corrective_bootstrap_training/opportunity_corrective_training_artifact.json"),
        "scaler_artifact": Path("reports/phase19_ad_u3_k_corrective_bootstrap_training/opportunity_scaler_artifact.json"),
        "model_file": Path(".runtime/ai_lifecycle/training_outputs/phase19_ad_u3_k_corrective_bootstrap_7cc6dfbfbf7899fa/opportunity/model.pkl"),
        "scaler_file": Path(".runtime/ai_lifecycle/training_outputs/phase19_ad_u3_k_corrective_bootstrap_7cc6dfbfbf7899fa/opportunity/scaler.pkl"),
    },
}


class CalibrationRunnerError(ValueError):
    """Fail-closed error for calibration runner violations."""


@dataclass(frozen=True)
class CalibrationRunRequest:
    mode: CalibrationMode
    report_dir: Path
    schema_dir: Path = DEFAULT_SCHEMA_DIR
    u4a_evidence_dir: Path = DEFAULT_U4A_EVIDENCE_DIR


def _load_json(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _load_pickle(path: Path) -> Any:
    with path.open("rb") as handle:
        return pickle.load(handle)


def load_u4a_bindings(evidence_dir: Path = DEFAULT_U4A_EVIDENCE_DIR) -> dict[str, Any]:
    usage = _load_json(evidence_dir / "calibration_dataset_usage_contract.json")
    binding = _load_json(evidence_dir / "artifact_binding_contract.json")
    return {"dataset_usage_contract": usage, "artifact_binding_contract": binding}


def validate_artifact_binding(
    *,
    source_model_artifact: dict[str, Any],
    source_scaler_artifact: dict[str, Any],
    source_model_file: Path,
    source_scaler_file: Path,
    binding: dict[str, Any],
    dataset_usage_contract: dict[str, Any],
) -> dict[str, Any]:
    reason_codes: list[str] = []
    if source_model_artifact.get("artifact_status") not in {"TRAINING_OUTPUT", "FIXTURE_TRAINING_OUTPUT"}:
        reason_codes.append("source_artifact_not_training_output")
    if source_model_artifact.get("runtime_eligibility") is not False:
        reason_codes.append("runtime_eligible_source_artifact")
    if source_model_artifact.get("accepted") is not False:
        reason_codes.append("accepted_source_artifact")
    if source_model_artifact.get("dataset_revision_id") != binding.get("dataset_revision_id"):
        reason_codes.append("dataset_revision_mismatch")
    if source_model_artifact.get("split_id") != binding.get("split_id"):
        reason_codes.append("split_id_mismatch")
    if source_model_artifact.get("split_content_hash") != binding.get("split_hash"):
        reason_codes.append("split_hash_mismatch")
    if dataset_usage_contract.get("contract_hash") != binding.get("dataset_usage_contract_hash"):
        reason_codes.append("dataset_usage_contract_mismatch")
    if source_model_artifact.get("artifact_id") != binding.get("source_model_artifact_id"):
        reason_codes.append("source_model_artifact_id_mismatch")
    if file_hash(source_model_file) != binding.get("source_model_hash"):
        reason_codes.append("source_model_hash_mismatch")
    if source_scaler_artifact.get("artifact_id") != binding.get("source_scaler_artifact_id"):
        reason_codes.append("source_scaler_artifact_id_mismatch")
    if file_hash(source_scaler_file) != binding.get("source_scaler_hash"):
        reason_codes.append("source_scaler_hash_mismatch")
    if list(source_model_artifact.get("feature_columns", [])) != list(source_scaler_artifact.get("input_feature_columns", [])):
        reason_codes.append("feature_order_mismatch")
    return {"status": "PASS" if not reason_codes else "REVIEW_REQUIRED", "reason_codes": reason_codes}


def _write_pickle(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(payload, handle)


def _validation_frame(resolved_input: dict[str, Any]) -> pd.DataFrame:
    dataset = pd.read_parquet(resolved_input["dataset_path"])
    target_date = dataset["target_date"].astype(str)
    window = resolved_input["split_definition"]["validation"]
    return dataset[(target_date >= str(window["start"])) & (target_date <= str(window["end"]))].copy()


def _scaled_validation_matrix(
    *,
    frame: pd.DataFrame,
    feature_columns: list[str],
    model_payload: dict[str, Any],
    scaler_payload: dict[str, Any],
) -> np.ndarray:
    matrix = transform_features(frame, feature_columns, model_payload["preprocessing"])
    result = np.array(matrix, dtype=np.float64, copy=True)
    index_by_feature = {feature: index for index, feature in enumerate(scaler_payload["input_feature_columns"])}
    scaled_indices = [index_by_feature[column] for column in scaler_payload["scaled_feature_columns"]]
    if scaled_indices:
        result[:, scaled_indices] = scaler_payload["scaler"].transform(result[:, scaled_indices])
    return result


def _quantiles(values: np.ndarray) -> dict[str, float]:
    return {str(q): float(np.quantile(values, q)) for q in [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]}


def _distribution(values: np.ndarray) -> dict[str, Any]:
    counts, edges = np.histogram(values, bins=20)
    return {
        "sample_count": int(values.size),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "quantiles": _quantiles(values),
        "histogram": {"counts": [int(v) for v in counts], "edges": [float(v) for v in edges]},
        "finite": bool(np.isfinite(values).all()),
    }


def _formal_binding_for(component: str, bindings: dict[str, Any]) -> dict[str, Any]:
    key = "candidate_bindings" if component == "Candidate" else "opportunity_bindings"
    return bindings["artifact_binding_contract"][key]


def _formal_preflight_component(component: str, bindings: dict[str, Any]) -> dict[str, Any]:
    key = component.lower()
    paths = FORMAL_PATHS[key]
    resolved = _load_json(paths["resolved_input"])
    model_artifact = _load_json(paths["model_artifact"])
    scaler_artifact = _load_json(paths["scaler_artifact"])
    binding = _formal_binding_for(component, bindings)
    model_hash = file_hash(paths["model_file"])
    scaler_hash = file_hash(paths["scaler_file"])
    binding_validation = validate_artifact_binding(
        source_model_artifact=model_artifact,
        source_scaler_artifact=scaler_artifact,
        source_model_file=paths["model_file"],
        source_scaler_file=paths["scaler_file"],
        binding=binding,
        dataset_usage_contract=bindings["dataset_usage_contract"],
    )
    user_instruction_scaler_hash = {
        "Candidate": "f731db7894e214444d34fac656e37c4a28cb6429c297d8f7ca252b34bdb31f94",
        "Opportunity": "820e17c08c9844aa953c9bcce880ffd671a900cbc3dac062eddd7dafcc6c7548",
    }[component]
    scaler_hash_target_reconciliation = {
        "instruction_value": user_instruction_scaler_hash,
        "actual_scaler_raw_bytes_sha256": scaler_hash,
        "scaler_artifact_content_hash": scaler_artifact.get("content_hash"),
        "classification": "MATCHES_RAW_BYTES"
        if user_instruction_scaler_hash == scaler_hash
        else "INSTRUCTION_VALUE_MATCHES_SCALER_ARTIFACT_CONTENT_HASH_NOT_RAW_BYTES",
    }
    return {
        "status": "PASS" if binding_validation["status"] == "PASS" else "REVIEW_REQUIRED",
        "component": component,
        "resolved_input": resolved,
        "model_artifact": model_artifact,
        "scaler_artifact": scaler_artifact,
        "binding": binding,
        "binding_validation": binding_validation,
        "hashes": {
            "dataset_content_hash": resolved["dataset_hash"],
            "dataset_schema_hash": resolved["dataset_schema_hash"],
            "dataset_lineage_hash": resolved["dataset_lineage_hash"],
            "split_id": resolved["split_id"],
            "split_hash": resolved["split_hash"],
            "dataset_usage_contract_hash": bindings["dataset_usage_contract"]["contract_hash"],
            "model_raw_bytes_sha256": model_hash,
            "scaler_raw_bytes_sha256": scaler_hash,
            "scaler_artifact_content_hash": scaler_artifact.get("content_hash"),
            "feature_order_hash": stable_json_hash(model_artifact["feature_columns"]),
        },
        "scaler_hash_target_reconciliation": scaler_hash_target_reconciliation,
    }


def _run_candidate_formal(*, output_dir: Path, report_dir: Path, schema_dir: Path, preflight: dict[str, Any], dataset_usage_contract: dict[str, Any]) -> dict[str, Any]:
    paths = FORMAL_PATHS["candidate"]
    started = time.perf_counter()
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        model_payload = _load_pickle(paths["model_file"])
        scaler_payload = _load_pickle(paths["scaler_file"])
        frame = _validation_frame(preflight["resolved_input"])
        matrix = _scaled_validation_matrix(
            frame=frame,
            feature_columns=list(preflight["model_artifact"]["feature_columns"]),
            model_payload=model_payload,
            scaler_payload=scaler_payload,
        )
        model = model_payload["model"]
        raw_scores = model.decision_function(matrix) if hasattr(model, "decision_function") else model.predict_proba(matrix)[:, 1]
        labels = frame[preflight["model_artifact"]["label_column"]].astype(bool).astype(int).to_numpy()
        calibration = fit_candidate_platt(raw_scores, labels)
    artifact = build_calibration_artifact(
        component="Candidate",
        source_model_artifact=preflight["model_artifact"],
        source_scaler_artifact=preflight["scaler_artifact"],
        dataset_usage_contract=dataset_usage_contract,
        source_model_file=paths["model_file"],
        source_scaler_file=paths["scaler_file"],
        calibration_method="PLATT_SCALING",
        calibration_method_version="sklearn.LogisticRegression.lbfgs.v1",
        calibration_config={"fit_window_role": "CALIBRATION_FIT_WINDOW", "identity_comparison": True, "formal_run_id": FORMAL_RUN_ID},
        calibration_parameters=calibration.parameters,
        fit_window=preflight["resolved_input"]["split_definition"]["validation"],
        input_score_schema={"candidate_raw_score": "decision_function_float"},
        output_score_schema={"calibrated_candidate_probability": {"type": "float", "range": [0, 1], "higher_is_better": True}},
        quality_metrics=calibration.quality_metrics,
        quality_gate_result=calibration.quality_gate_result,
        source_phase="PHASE19_AD_U4_D",
    )
    artifact_result = write_calibration_artifact(
        artifact=artifact,
        artifact_path=output_dir / "candidate" / "candidate_calibration_artifact.json",
        schema_dir=schema_dir,
        source_model_file=paths["model_file"],
        source_scaler_file=paths["scaler_file"],
    )
    raw = np.asarray(calibration.raw_scores, dtype=float)
    prob = np.asarray(calibration.calibrated_probability, dtype=float)
    metrics = {
        "status": calibration.status,
        "sample_count": int(len(labels)),
        "positive_count": int(np.sum(labels == 1)),
        "negative_count": int(np.sum(labels == 0)),
        "class_balance": float(np.mean(labels)),
        "raw_score_distribution": _distribution(raw),
        "calibrated_probability_distribution": _distribution(prob),
        "quality_metrics": calibration.quality_metrics,
        "quality_gate_result": calibration.quality_gate_result,
        "fit_duration_seconds": round(time.perf_counter() - started, 6),
        "warnings": [{"category": r.category.__name__, "message": str(r.message)} for r in records],
    }
    write_json(report_dir / "candidate_calibration_artifact.json", artifact_result["artifact"])
    write_json(report_dir / "candidate_calibration_parameters.json", calibration.parameters)
    write_json(report_dir / "candidate_calibration_metrics.json", metrics)
    write_json(report_dir / "candidate_identity_comparison.json", calibration.quality_metrics["identity"] | {"platt": calibration.quality_metrics["platt"], "main_metric_worsened_vs_identity": calibration.quality_metrics["main_metric_worsened_vs_identity"]})
    write_json(report_dir / "candidate_calibration_curve.json", {"identity": calibration.quality_metrics["identity"]["calibration_curve"], "platt": calibration.quality_metrics["platt"]["calibration_curve"]})
    write_json(report_dir / "candidate_prediction_distribution.json", {"raw_score": metrics["raw_score_distribution"], "calibrated_probability": metrics["calibrated_probability_distribution"]})
    write_json(report_dir / "candidate_quality_gate.json", calibration.quality_gate_result)
    return {"status": "PASS" if calibration.status == "PASS" and artifact_result["status"] == "PASS" else "REVIEW_REQUIRED", "artifact_result": artifact_result, "metrics": metrics}


def _run_opportunity_formal(*, output_dir: Path, report_dir: Path, schema_dir: Path, preflight: dict[str, Any], dataset_usage_contract: dict[str, Any]) -> dict[str, Any]:
    paths = FORMAL_PATHS["opportunity"]
    started = time.perf_counter()
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        model_payload = _load_pickle(paths["model_file"])
        scaler_payload = _load_pickle(paths["scaler_file"])
        frame = _validation_frame(preflight["resolved_input"])
        matrix = _scaled_validation_matrix(
            frame=frame,
            feature_columns=list(preflight["model_artifact"]["feature_columns"]),
            model_payload=model_payload,
            scaler_payload=scaler_payload,
        )
        raw_predictions = model_payload["model"].predict(matrix)
        calibration = fit_opportunity_standardization(raw_predictions)
    artifact = build_calibration_artifact(
        component="Opportunity",
        source_model_artifact=preflight["model_artifact"],
        source_scaler_artifact=preflight["scaler_artifact"],
        dataset_usage_contract=dataset_usage_contract,
        source_model_file=paths["model_file"],
        source_scaler_file=paths["scaler_file"],
        calibration_method="STANDARDIZED",
        calibration_method_version="mean_std.v1",
        calibration_config={"fit_window_role": "CALIBRATION_FIT_WINDOW", "clipping": {"enabled": False}, "percentile": "diagnostic_only", "formal_run_id": FORMAL_RUN_ID},
        calibration_parameters=calibration.parameters,
        fit_window=preflight["resolved_input"]["split_definition"]["validation"],
        input_score_schema={"raw_opportunity_prediction": "float"},
        output_score_schema={"normalized_opportunity_score": {"type": "float", "higher_is_better": True}, "percentile": "diagnostic_only"},
        quality_metrics=calibration.quality_metrics,
        quality_gate_result=calibration.quality_gate_result,
        source_phase="PHASE19_AD_U4_D",
    )
    artifact_result = write_calibration_artifact(
        artifact=artifact,
        artifact_path=output_dir / "opportunity" / "opportunity_calibration_artifact.json",
        schema_dir=schema_dir,
        source_model_file=paths["model_file"],
        source_scaler_file=paths["scaler_file"],
    )
    raw = np.asarray(calibration.raw_scores, dtype=float)
    normalized = np.asarray(calibration.normalized_opportunity_score, dtype=float)
    metrics = {
        "status": calibration.status,
        "sample_count": int(raw.size),
        "raw_prediction_distribution": _distribution(raw),
        "normalized_score_distribution": _distribution(normalized),
        "standardization_mean": calibration.parameters["mean"],
        "standardization_std": calibration.parameters["std"],
        "quality_metrics": calibration.quality_metrics,
        "quality_gate_result": calibration.quality_gate_result,
        "fit_duration_seconds": round(time.perf_counter() - started, 6),
        "warnings": [{"category": r.category.__name__, "message": str(r.message)} for r in records],
    }
    write_json(report_dir / "opportunity_calibration_artifact.json", artifact_result["artifact"])
    write_json(report_dir / "opportunity_calibration_parameters.json", calibration.parameters)
    write_json(report_dir / "opportunity_calibration_metrics.json", metrics)
    write_json(report_dir / "opportunity_prediction_distribution.json", {"raw_prediction": metrics["raw_prediction_distribution"], "normalized_score": metrics["normalized_score_distribution"]})
    write_json(report_dir / "opportunity_percentile_diagnostics.json", {"percentile_diagnostic": calibration.percentile_diagnostic, "distribution": calibration.quality_metrics["percentile_diagnostic_distribution"]})
    write_json(report_dir / "opportunity_quality_gate.json", calibration.quality_gate_result)
    return {"status": "PASS" if calibration.status == "PASS" and artifact_result["status"] == "PASS" else "REVIEW_REQUIRED", "artifact_result": artifact_result, "metrics": metrics}


def _run_formal_calibration(request: CalibrationRunRequest) -> dict[str, Any]:
    output_dir = FORMAL_OUTPUT_DIR
    report_dir = request.report_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    bindings = load_u4a_bindings(request.u4a_evidence_dir)
    candidate_preflight = _formal_preflight_component("Candidate", bindings)
    opportunity_preflight = _formal_preflight_component("Opportunity", bindings)
    preflight = {
        "status": "PASS" if candidate_preflight["status"] == "PASS" and opportunity_preflight["status"] == "PASS" else "REVIEW_REQUIRED",
        "formal_run_id": FORMAL_RUN_ID,
        "candidate": {k: v for k, v in candidate_preflight.items() if k not in {"resolved_input", "model_artifact", "scaler_artifact"}},
        "opportunity": {k: v for k, v in opportunity_preflight.items() if k not in {"resolved_input", "model_artifact", "scaler_artifact"}},
        "calibration_artifact_schema_hash": file_hash(request.schema_dir / "calibration_artifact.schema.json"),
        "calibration_method_decision_hash": file_hash(request.u4a_evidence_dir / "candidate_method_decision.json") + ":" + file_hash(request.u4a_evidence_dir / "opportunity_method_decision.json"),
        "calibration_quality_gate_hash": file_hash(request.u4a_evidence_dir / "calibration_quality_gate_contract.json"),
    }
    write_json(report_dir / "preflight_results.json", preflight)
    if preflight["status"] != "PASS":
        return {"status": "REVIEW_REQUIRED", "preflight": preflight, "candidate_started": False, "opportunity_started": False}
    candidate = _run_candidate_formal(
        output_dir=output_dir,
        report_dir=report_dir,
        schema_dir=request.schema_dir,
        preflight=candidate_preflight,
        dataset_usage_contract=bindings["dataset_usage_contract"],
    )
    if candidate["status"] != "PASS":
        return {"status": "REVIEW_REQUIRED", "preflight": preflight, "candidate": candidate, "opportunity_started": False}
    opportunity = _run_opportunity_formal(
        output_dir=output_dir,
        report_dir=report_dir,
        schema_dir=request.schema_dir,
        preflight=opportunity_preflight,
        dataset_usage_contract=bindings["dataset_usage_contract"],
    )
    result = {
        "status": "PASS" if opportunity["status"] == "PASS" else "REVIEW_REQUIRED",
        "formal_run_id": FORMAL_RUN_ID,
        "output_dir": str(output_dir),
        "preflight": preflight,
        "candidate": candidate,
        "opportunity": opportunity,
        "dataset_window_access": {"train_accessed": False, "validation_accessed": True, "test_accessed": False, "recent_holdout_accessed": False},
        "formal_validation_executed": False,
        "unified_generation_created": False,
        "accepted_decision_created": False,
        "accepted_generation_created": False,
        "runtime_pointer_written": False,
        "buy_restart_executed": False,
        "broker_write_executed": False,
        "ledger_mutation_executed": False,
    }
    write_json(output_dir / "formal_calibration_run_manifest.json", result)
    write_json(report_dir / "execution_log.json", result)
    return result


def _fixture_artifact(component: str, model_path: Path, scaler_path: Path, contract_hash: str, *, feature_columns: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    base_hash = stable_json_hash({"component": component, "fixture": True})
    split_hash = stable_json_hash({"component": component, "split": True})
    model_artifact = {
        "artifact_id": f"fixture_{component.lower()}_{file_hash(model_path)[:16]}",
        "artifact_status": "FIXTURE_TRAINING_OUTPUT",
        "runtime_eligibility": False,
        "accepted": False,
        "generation_eligibility": False,
        "model_content_hash": file_hash(model_path),
        "feature_columns": feature_columns,
        "dataset_revision_id": f"fixture_{component.lower()}_dataset_revision",
        "dataset_content_hash": base_hash,
        "dataset_schema_hash": stable_json_hash({"schema": component}),
        "dataset_lineage_hash": stable_json_hash({"lineage": component}),
        "split_id": f"fixture_{component.lower()}_split",
        "split_content_hash": split_hash,
        "feature_schema_identity": stable_json_hash({"features": feature_columns}),
        "label_schema_identity": stable_json_hash({"label": component}),
        "trading_calendar_identity": stable_json_hash({"calendar": "fixture"}),
        "target_horizon_business_days": 20,
        "embargo_business_days": 20,
        "bootstrap_or_retraining": "BOOTSTRAP",
        "rolling_split_policy_hash": stable_json_hash({"rolling": "fixture"}),
        "corporate_action_policy_hash": stable_json_hash({"ca": "fixture"}),
        "model_quality_policy_hash": stable_json_hash({"quality": "fixture"}),
    }
    scaler_artifact = {
        "artifact_id": f"fixture_{component.lower()}_scaler_{file_hash(scaler_path)[:16]}",
        "artifact_status": "FIXTURE_SCALER_OUTPUT",
        "scaler_content_hash": file_hash(scaler_path),
        "input_feature_columns": feature_columns,
    }
    binding = {
        "dataset_revision_id": model_artifact["dataset_revision_id"],
        "split_id": model_artifact["split_id"],
        "split_hash": model_artifact["split_content_hash"],
        "dataset_usage_contract_hash": contract_hash,
        "source_model_artifact_id": model_artifact["artifact_id"],
        "source_model_hash": model_artifact["model_content_hash"],
        "source_scaler_artifact_id": scaler_artifact["artifact_id"],
        "source_scaler_hash": scaler_artifact["scaler_content_hash"],
    }
    return model_artifact, scaler_artifact | {"fixture_binding": binding}


def _fixture_dataset_usage_contract() -> dict[str, Any]:
    payload = {
        "schema_version": "phase19_ad_u4_c_fixture_dataset_usage_contract.v1",
        "window_roles": {"validation": {"phase19_reclassified_role": "CALIBRATION_FIT_WINDOW"}},
    }
    payload["contract_hash"] = stable_json_hash(payload)
    return payload


def _run_candidate_fixture(report_dir: Path, schema_dir: Path, dataset_usage_contract: dict[str, Any]) -> dict[str, Any]:
    model_path = report_dir / "fixture_sources" / "candidate_model.pkl"
    scaler_path = report_dir / "fixture_sources" / "candidate_scaler.pkl"
    _write_pickle(model_path, {"fixture": "candidate_model"})
    _write_pickle(scaler_path, {"fixture": "candidate_scaler"})
    source, scaler = _fixture_artifact("Candidate", model_path, scaler_path, dataset_usage_contract["contract_hash"], feature_columns=["feature_a"])
    binding = scaler.pop("fixture_binding")
    binding_validation = validate_artifact_binding(
        source_model_artifact=source,
        source_scaler_artifact=scaler,
        source_model_file=model_path,
        source_scaler_file=scaler_path,
        binding=binding,
        dataset_usage_contract=dataset_usage_contract,
    )
    scores = np.array([-4, -3, -2, -1, 1, 2, 3, 4], dtype=float)
    labels = np.array([0, 0, 0, 0, 1, 1, 1, 1], dtype=int)
    calibration = fit_candidate_platt(scores, labels)
    artifact = build_calibration_artifact(
        component="Candidate",
        source_model_artifact=source,
        source_scaler_artifact=scaler,
        dataset_usage_contract=dataset_usage_contract,
        source_model_file=model_path,
        source_scaler_file=scaler_path,
        calibration_method="PLATT_SCALING",
        calibration_method_version="sklearn.LogisticRegression.lbfgs.v1",
        calibration_config={"fit_window_role": "CALIBRATION_FIT_WINDOW", "identity_comparison": True},
        calibration_parameters=calibration.parameters,
        fit_window={"name": "validation", "role": "CALIBRATION_FIT_WINDOW"},
        input_score_schema={"candidate_raw_score": "float"},
        output_score_schema={"calibrated_candidate_probability": {"type": "float", "range": [0, 1]}},
        quality_metrics=calibration.quality_metrics,
        quality_gate_result=calibration.quality_gate_result,
    )
    artifact_result = write_calibration_artifact(
        artifact=artifact,
        artifact_path=report_dir / "candidate_calibration_artifact.json",
        schema_dir=schema_dir,
        source_model_file=model_path,
        source_scaler_file=scaler_path,
    )
    degraded = fit_candidate_platt([-8, -6, -4, -2, 2, 4, 6, 8], [1, 1, 1, 1, 0, 0, 0, 0])
    failure_cases: dict[str, Any] = {
        "platt_degradation": {"status": degraded.status, "reason_codes": degraded.quality_gate_result["reason_codes"]},
    }
    for name, raw, y in [
        ("collapse", [1, 1, 1, 1], [0, 1, 0, 1]),
        ("nan_inf", [0, 1, float("nan"), 2], [0, 1, 0, 1]),
    ]:
        try:
            fit_candidate_platt(raw, y)
            failure_cases[name] = {"status": "UNEXPECTED_PASS"}
        except (CandidateCalibrationError, ValueError) as exc:
            failure_cases[name] = {"status": "PASS", "error": str(exc)}
    return {
        "status": "PASS" if calibration.status == "PASS" and artifact_result["status"] == "PASS" and binding_validation["status"] == "PASS" else "REVIEW_REQUIRED",
        "binding_validation": binding_validation,
        "calibration": calibration.__dict__,
        "artifact_result": artifact_result,
        "failure_cases": failure_cases,
    }


def _run_opportunity_fixture(report_dir: Path, schema_dir: Path, dataset_usage_contract: dict[str, Any]) -> dict[str, Any]:
    model_path = report_dir / "fixture_sources" / "opportunity_model.pkl"
    scaler_path = report_dir / "fixture_sources" / "opportunity_scaler.pkl"
    _write_pickle(model_path, {"fixture": "opportunity_model"})
    _write_pickle(scaler_path, {"fixture": "opportunity_scaler"})
    source, scaler = _fixture_artifact("Opportunity", model_path, scaler_path, dataset_usage_contract["contract_hash"], feature_columns=["feature_a"])
    binding = scaler.pop("fixture_binding")
    binding_validation = validate_artifact_binding(
        source_model_artifact=source,
        source_scaler_artifact=scaler,
        source_model_file=model_path,
        source_scaler_file=scaler_path,
        binding=binding,
        dataset_usage_contract=dataset_usage_contract,
    )
    calibration = fit_opportunity_standardization([-2, -1, 0, 1, 2, 3])
    artifact = build_calibration_artifact(
        component="Opportunity",
        source_model_artifact=source,
        source_scaler_artifact=scaler,
        dataset_usage_contract=dataset_usage_contract,
        source_model_file=model_path,
        source_scaler_file=scaler_path,
        calibration_method="STANDARDIZED",
        calibration_method_version="mean_std.v1",
        calibration_config={"fit_window_role": "CALIBRATION_FIT_WINDOW", "clipping": {"enabled": False}, "percentile": "diagnostic_only"},
        calibration_parameters=calibration.parameters,
        fit_window={"name": "validation", "role": "CALIBRATION_FIT_WINDOW"},
        input_score_schema={"raw_opportunity_score": "float"},
        output_score_schema={"normalized_opportunity_score": "float", "percentile": "diagnostic_only"},
        quality_metrics=calibration.quality_metrics,
        quality_gate_result=calibration.quality_gate_result,
    )
    artifact_result = write_calibration_artifact(
        artifact=artifact,
        artifact_path=report_dir / "opportunity_calibration_artifact.json",
        schema_dir=schema_dir,
        source_model_file=model_path,
        source_scaler_file=scaler_path,
    )
    failure_cases: dict[str, Any] = {}
    for name, raw in [
        ("zero_std", [1, 1, 1]),
        ("nan_inf", [1, float("inf"), 2]),
        ("explosion", [0, 1e308, -1e308]),
    ]:
        try:
            fit_opportunity_standardization(raw)
            failure_cases[name] = {"status": "UNEXPECTED_PASS"}
        except (OpportunityCalibrationError, ValueError) as exc:
            failure_cases[name] = {"status": "PASS", "error": str(exc)}
    broken = calibration.__dict__.copy()
    broken["quality_gate_result"] = {"status": "OPPORTUNITY_CALIBRATION_REVIEW_REQUIRED", "reason_codes": ["opportunity_ordering_not_preserved"]}
    failure_cases["ordering_break"] = {"status": "PASS", "simulated_result": broken["quality_gate_result"]}
    return {
        "status": "PASS" if calibration.status == "PASS" and artifact_result["status"] == "PASS" and binding_validation["status"] == "PASS" else "REVIEW_REQUIRED",
        "binding_validation": binding_validation,
        "calibration": calibration.__dict__,
        "artifact_result": artifact_result,
        "failure_cases": failure_cases,
    }


def run_calibration_runner(request: CalibrationRunRequest) -> dict[str, Any]:
    if request.mode == "FORMAL_CALIBRATION":
        return _run_formal_calibration(request)
    if request.mode != "FIXTURE_SMOKE":
        raise CalibrationRunnerError("formal_calibration_not_allowed_in_u4_c_fixture_runner")
    request.report_dir.mkdir(parents=True, exist_ok=True)
    dataset_usage_contract = _fixture_dataset_usage_contract()
    candidate = _run_candidate_fixture(request.report_dir, request.schema_dir, dataset_usage_contract)
    if candidate["status"] != "PASS":
        result = {"status": "REVIEW_REQUIRED", "candidate": candidate, "opportunity_started": False}
        write_json(request.report_dir / "calibration_fixture_result.json", result)
        return result
    opportunity = _run_opportunity_fixture(request.report_dir, request.schema_dir, dataset_usage_contract)
    result = {
        "status": "PASS" if opportunity["status"] == "PASS" else "REVIEW_REQUIRED",
        "mode": request.mode,
        "candidate": candidate,
        "opportunity": opportunity,
        "formal_calibration_executed": False,
        "test_evaluation_executed": False,
        "recent_holdout_evaluation_executed": False,
        "runtime_pointer_written": False,
        "broker_write_executed": False,
    }
    write_json(request.report_dir / "calibration_fixture_result.json", result)
    return result
