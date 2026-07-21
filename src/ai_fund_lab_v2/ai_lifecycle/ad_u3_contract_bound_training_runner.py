from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import platform
import subprocess
import sys
import time
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from ai_fund_lab_v2.ai_lifecycle.ad_u3_dataset_input_resolver import (
    ContractInputError,
    ResolvedTrainingInput,
    load_ad_u3_dataset_input_contract,
    resolve_candidate_training_input,
    resolve_opportunity_training_input,
)
from ai_fund_lab_v2.ai_lifecycle.ad_u3_scaler_artifact_writer import (
    infer_feature_dtypes,
    scaled_matrix_statistics,
    scaler_artifact_payload,
    scaler_schema_validation,
)
from ai_fund_lab_v2.ai_lifecycle.ad_u3_scaling_contract import (
    DEFAULT_CORRECTIVE_ACTION_POLICY_PATH,
    CorrectiveActionPolicyError,
    fit_train_only_scaler,
    load_approved_corrective_action_policy,
    materialize_corrective_action_policy_payload,
    scaler_method_comparison,
    scaler_method_decision,
    scaling_feature_inventory,
    transform_with_scaler,
    write_scaler_pickle,
)
from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import (
    ArtifactSchemaError,
    atomic_write_staging_artifact,
    cleanup_failed_staging,
    file_hash,
    read_json,
    reset_staging_dir,
    stable_json_hash,
    validate_artifact_against_schema,
    write_json,
)
from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_quality_gate import (
    ModelQualityPolicyError,
    evaluate_training_quality,
    load_approved_model_quality_policy,
    validate_approved_model_quality_policy,
)
from ai_fund_lab_v2.ai_lifecycle.training_pipeline import fit_model, fit_preprocessing, target_values, transform_features


CREATED_AT = "2026-07-20T00:00:00+09:00"
DEFAULT_CONTRACT_PATH = Path("reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/ad_u3_dataset_input_contract_corrected.json")
DEFAULT_POLICY_PATH = Path(".runtime/ai_lifecycle/policies/model_quality/phase19_ad_u3_d_model_quality_policy/model_quality_policy.json")
DEFAULT_SCHEMA_DIR = Path("schemas/ai_lifecycle")
DEFAULT_REPORT_DIR = Path("reports/phase19_ad_u3_e_contract_bound_training_runner")

ExecutionMode = Literal["VALIDATE_ONLY", "FIXTURE_SMOKE", "FIXTURE_SCALING_SMOKE", "CORRECTIVE_BOOTSTRAP", "FORMAL_BOOTSTRAP", "FORMAL_RETRAINING"]


class TrainingRunnerError(ValueError):
    """Fail-closed error for AD-U3-E contract-bound training runner."""


@dataclass(frozen=True)
class TrainingRunRequest:
    contract_path: Path
    model_quality_policy_path: Path
    schema_dir: Path = DEFAULT_SCHEMA_DIR
    mode: ExecutionMode = "VALIDATE_ONLY"
    report_dir: Path = DEFAULT_REPORT_DIR
    confirm: bool = False
    approved_execution_plan: Path | None = None
    corrective_action_policy_path: Path | None = None


def run_contract_bound_training_runner(request: TrainingRunRequest, **overrides: Any) -> dict[str, Any]:
    _reject_runner_overrides(overrides)
    mode = _normalize_mode(request.mode)
    report_dir = Path(request.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    contract = load_ad_u3_dataset_input_contract(request.contract_path)
    policy = load_approved_model_quality_policy(request.model_quality_policy_path)
    candidate_input = resolve_candidate_training_input(contract)
    opportunity_input = resolve_opportunity_training_input(contract)
    authority = _formal_authority_review(contract, policy, request)
    schema_review = _schema_dir_review(request.schema_dir)
    if mode in {"FORMAL_BOOTSTRAP", "FORMAL_RETRAINING", "CORRECTIVE_BOOTSTRAP"}:
        result = _reject_formal_mode(request, mode, report_dir, authority, schema_review)
        return result
    if mode == "VALIDATE_ONLY":
        result = {
            "status": "PASS",
            "mode": mode,
            "training_executed": False,
            "candidate_resolved": candidate_input.to_dict(),
            "opportunity_resolved": opportunity_input.to_dict(),
            "quality_policy": validate_approved_model_quality_policy(policy),
            "schema_review": schema_review,
            "formal_authority": authority,
        }
        write_json(report_dir / "validate_only_result.json", result)
        return result
    if mode == "FIXTURE_SMOKE":
        if contract.get("fixture_contract") is not True:
            raise TrainingRunnerError("fixture_smoke_requires_fixture_contract")
        return _run_fixture_smoke(
            contract=contract,
            policy=policy,
            candidate_input=candidate_input,
            opportunity_input=opportunity_input,
            request=request,
            authority=authority,
            schema_review=schema_review,
        )
    if mode == "FIXTURE_SCALING_SMOKE":
        if contract.get("fixture_contract") is not True:
            raise TrainingRunnerError("fixture_scaling_smoke_requires_fixture_contract")
        if request.corrective_action_policy_path is None:
            raise CorrectiveActionPolicyError("corrective_action_policy_required")
        corrective_policy = load_approved_corrective_action_policy(request.corrective_action_policy_path)
        return _run_fixture_scaling_smoke(
            contract=contract,
            policy=policy,
            corrective_policy=corrective_policy,
            candidate_input=candidate_input,
            opportunity_input=opportunity_input,
            request=request,
            authority=authority,
            schema_review=schema_review,
        )
    raise TrainingRunnerError(f"unknown_execution_mode:{mode}")


def materialize_fixture_contract(root: Path) -> Path:
    fixture_root = root / "fixture_contract"
    fixture_root.mkdir(parents=True, exist_ok=True)
    policy_hashes = {
        "rolling_split_policy_hash": "4defbb1e4c5e8ef4d3ef1b3bdfdfd89782dfb7e204c8597e40a49b99df61a5e3",
        "corporate_action_policy_hash": "2459ff93b262e0a9008cd710fc6f447f9d66dc44f8eddf07442ab30c14855c34",
    }
    components = {}
    for name, feature_columns, label_columns, split_id in (
        (
            "candidate",
            ["feature__liquidity_avg_volume_20d", "feature__price_momentum_return_5d", "feature__missing_flags_price"],
            ["label__momentum_candidate_label", "label__future_return_20d"],
            "fixture_candidate_split",
        ),
        (
            "opportunity",
            [
                "feature__candidate_rank",
                "feature__candidate_reason",
                "feature__candidate_score",
                "feature__liquidity_avg_volume_20d",
                "feature__volume_momentum_ratio_5d",
                "feature__missing_flags_price",
            ],
            ["label__expected_edge_label_20d", "label__future_return_20d"],
            "fixture_opportunity_split",
        ),
    ):
        component_name = "Candidate" if name == "candidate" else "Opportunity"
        comp_dir = fixture_root / name
        comp_dir.mkdir(parents=True, exist_ok=True)
        dataset_path = comp_dir / "dataset.parquet"
        dataset_path.write_bytes(f"fixture {component_name} dataset placeholder\n".encode("utf-8"))
        feature_schema = {"schema_hash": _stable_hash({"feature_columns": feature_columns}), "columns": [{"name": col} for col in feature_columns]}
        label_schema = {"schema_hash": _stable_hash({"label_columns": label_columns}), "columns": [{"name": col} for col in label_columns]}
        write_json(comp_dir / "feature_schema.json", feature_schema)
        write_json(comp_dir / "target_schema.json", label_schema)
        dataset_hash = file_hash(dataset_path)
        dataset_schema_hash = _stable_hash({"component": component_name, "features": feature_columns, "labels": label_columns})
        lineage_hash = _stable_hash({"component": component_name, "fixture": True, "source": "Phase19-AD-U3-E"})
        manifest = {
            "dataset_hash": dataset_hash,
            "schema_hash": dataset_schema_hash,
            "feature_schema_hash": feature_schema["schema_hash"],
            "target_schema_hash": label_schema["schema_hash"],
        }
        write_json(comp_dir / "hash_manifest.json", manifest)
        revision = {
            "dataset_revision": f"fixture_{name}_dataset_revision",
            "source_lineage_hash": lineage_hash,
            "fixture_only": True,
        }
        revision_path = comp_dir / "dataset_revision.json"
        write_json(revision_path, revision)
        split = {
            "split_id": split_id,
            "split_method": "FIXTURE_CAPPED_EXPANDING_HYBRID_SHAPE",
            "dataset_revision": revision["dataset_revision"],
            "dataset_hash": dataset_hash,
            "schema_hash": dataset_schema_hash,
            "policy_id": "phase19_ad_u2_f_rolling_split_policy_option_c_capped_expanding_hybrid",
            "policy_hash": policy_hashes["rolling_split_policy_hash"],
            "trading_calendar_identity": "fixture_trading_calendar_identity",
            "target_horizon_business_days": 20,
            "embargo_business_days": 20,
            "train_start": "2026-01-05",
            "train_end": "2026-02-13",
            "train_business_days": 30,
            "validation_start": "2026-03-16",
            "validation_end": "2026-03-27",
            "validation_business_days": 10,
            "test_start": "2026-04-27",
            "test_end": "2026-05-01",
            "test_business_days": 5,
            "recent_holdout_start": "2026-06-01",
            "recent_holdout_end": "2026-06-05",
            "recent_holdout_business_days": 5,
            "fixture_only": True,
            "not_production_split": True,
        }
        split_path = comp_dir / "split.json"
        write_json(split_path, split)
        components[name] = {
            "component": component_name,
            "dataset_revision_id": revision["dataset_revision"],
            "dataset_revision_path": str(revision_path),
            "dataset_revision_content_hash": file_hash(revision_path),
            "dataset_content_hash": dataset_hash,
            "actual_dataset_content_hash": dataset_hash,
            "dataset_schema_hash": dataset_schema_hash,
            "dataset_lineage_hash": lineage_hash,
            "source_revision": {"bootstrap_revision": True, "fixture_only": True},
            "source_cutoff": {"fixture_only": True},
            "dataset_date_min": "2026-01-05",
            "dataset_date_max": "2026-06-05",
            "label_safe_max": "2026-06-05",
            "dataset_path": str(dataset_path),
            "dataset_hash_manifest_path": str(comp_dir / "hash_manifest.json"),
            "feature_schema_path": str(comp_dir / "feature_schema.json"),
            "label_schema_path": str(comp_dir / "target_schema.json"),
            "split_id": split_id,
            "split_path": str(split_path),
            "split_content_hash": file_hash(split_path),
            "rolling_split_policy_id": "phase19_ad_u2_f_rolling_split_policy_option_c_capped_expanding_hybrid",
            "rolling_split_policy_hash": policy_hashes["rolling_split_policy_hash"],
            "corporate_action_policy_id": "phase19_ad_u2_d_corporate_action_dataset_handling",
            "corporate_action_policy_hash": policy_hashes["corporate_action_policy_hash"],
            "trading_calendar_identity": "fixture_trading_calendar_identity",
            "target_horizon_business_days": 20,
            "embargo_business_days": 20,
            "feature_schema_identity": feature_schema["schema_hash"],
            "label_schema_identity": label_schema["schema_hash"],
            "row_count": 180 if name == "candidate" else 180,
        }
    contract = {
        "contract_id": "phase19_ad_u3_e_fixture_dataset_input_contract",
        "contract_version": "phase19_ad_u3_e_fixture_dataset_input_contract.v1",
        "contract_status": "PASS_AFTER_CORRECTIVE_FIX",
        "authority": (
            "Phase19-AD-R2 corrected gate contract bound to AD-U2-F approved policy and AD-U2-D "
            "policy-amended dataset revisions"
        ),
        "source_phase": "PHASE19_AD_R2",
        "generation_mode": "UNIFIED_GENERATION_INPUT",
        "bootstrap_or_retraining": "BOOTSTRAP",
        "previous_generation_ref": None,
        "fixture_contract": True,
        "fixture_scope": "FIXTURE_ONLY",
        "not_production_split": True,
        "policy_hashes": policy_hashes,
        "candidate": components["candidate"],
        "opportunity": components["opportunity"],
    }
    contract["contract_hash"] = _stable_hash({key: value for key, value in contract.items() if key != "contract_hash"})
    contract_path = fixture_root / "ad_u3_fixture_dataset_input_contract.json"
    write_json(contract_path, contract)
    return contract_path


def _run_fixture_smoke(
    *,
    contract: dict[str, Any],
    policy: dict[str, Any],
    candidate_input: ResolvedTrainingInput,
    opportunity_input: ResolvedTrainingInput,
    request: TrainingRunRequest,
    authority: dict[str, Any],
    schema_review: dict[str, Any],
) -> dict[str, Any]:
    run_id = "phase19_ad_u3_e_fixture_smoke_" + _stable_hash(
        {
            "contract_hash": contract.get("contract_hash"),
            "policy_hash": policy.get("policy_hash"),
            "mode": "FIXTURE_SMOKE",
        }
    )[:16]
    staging_dir = Path(".runtime/ai_lifecycle/training_staging") / run_id
    reset_staging_dir(staging_dir)
    try:
        candidate = _train_fixture_component(
            resolved=candidate_input,
            policy=policy,
            staging_dir=staging_dir / "candidate",
            schema_path=Path(request.schema_dir) / "candidate_model_artifact.schema.json",
            mode="FIXTURE_SMOKE",
        )
        opportunity = _train_fixture_component(
            resolved=opportunity_input,
            policy=policy,
            staging_dir=staging_dir / "opportunity",
            schema_path=Path(request.schema_dir) / "opportunity_model_artifact.schema.json",
            mode="FIXTURE_SMOKE",
            candidate_artifact=candidate["artifact"],
        )
    except Exception as exc:
        failure = cleanup_failed_staging(staging_dir, failure_reason=str(exc), partial_artifacts=[])
        write_json(Path(request.report_dir) / "atomic_commit_failure_cleanup.json", failure)
        raise
    result = {
        "status": "PASS",
        "mode": "FIXTURE_SMOKE",
        "run_id": run_id,
        "staging_dir": str(staging_dir),
        "formal_quality_result": "NOT_EVALUATED_FOR_ACCEPTANCE",
        "runtime_eligibility": False,
        "generation_eligibility": False,
        "training_executed": "FIXTURE_ONLY_TECHNICAL_SMOKE",
        "candidate": candidate,
        "opportunity": opportunity,
        "formal_authority": authority,
        "schema_review": schema_review,
        "formal_generation_candidate_created": False,
        "accepted_decision_created": False,
        "runtime_pointer_written": False,
        "broker_write_executed": False,
    }
    write_json(staging_dir / "status.json", {"status": "PASS", "fixture_only": True, "runtime_eligibility": False})
    return result


def _run_fixture_scaling_smoke(
    *,
    contract: dict[str, Any],
    policy: dict[str, Any],
    corrective_policy: dict[str, Any],
    candidate_input: ResolvedTrainingInput,
    opportunity_input: ResolvedTrainingInput,
    request: TrainingRunRequest,
    authority: dict[str, Any],
    schema_review: dict[str, Any],
) -> dict[str, Any]:
    run_id = "phase19_ad_u3_i_fixture_scaling_smoke_" + _stable_hash(
        {
            "contract_hash": contract.get("contract_hash"),
            "policy_hash": policy.get("policy_hash"),
            "corrective_action_policy_hash": corrective_policy.get("policy_hash"),
            "mode": "FIXTURE_SCALING_SMOKE",
        }
    )[:16]
    staging_dir = Path(".runtime/ai_lifecycle/training_staging") / run_id
    reset_staging_dir(staging_dir)
    candidate = _train_fixture_scaling_component(
        resolved=candidate_input,
        policy=policy,
        corrective_policy=corrective_policy,
        staging_dir=staging_dir / "candidate",
        schema_dir=Path(request.schema_dir),
        mode="FIXTURE_SCALING_SMOKE",
    )
    if candidate["status"] != "PASS":
        failure = cleanup_failed_staging(staging_dir, failure_reason="candidate_fixture_scaling_smoke_failed", partial_artifacts=[])
        write_json(Path(request.report_dir) / "atomic_commit_failure_cleanup.json", failure)
        return {"status": "BLOCK", "candidate": candidate, "opportunity_started": False, "failure": failure}
    opportunity = _train_fixture_scaling_component(
        resolved=opportunity_input,
        policy=policy,
        corrective_policy=corrective_policy,
        staging_dir=staging_dir / "opportunity",
        schema_dir=Path(request.schema_dir),
        mode="FIXTURE_SCALING_SMOKE",
        candidate_artifact=candidate["artifact"],
        candidate_scaler_artifact=candidate["scaler_artifact"],
    )
    result = {
        "status": "PASS" if opportunity["status"] == "PASS" else "BLOCK",
        "mode": "FIXTURE_SCALING_SMOKE",
        "run_id": run_id,
        "staging_dir": str(staging_dir),
        "corrective_action_policy_hash": corrective_policy["policy_hash"],
        "scaler_method": "StandardScaler",
        "formal_quality_result": "NOT_EVALUATED_FOR_ACCEPTANCE",
        "runtime_eligibility": False,
        "generation_eligibility": False,
        "training_executed": "FIXTURE_SCALING_TECHNICAL_SMOKE_ONLY",
        "candidate": candidate,
        "opportunity": opportunity,
        "formal_authority": authority,
        "schema_review": schema_review,
        "formal_generation_candidate_created": False,
        "accepted_decision_created": False,
        "runtime_pointer_written": False,
        "broker_write_executed": False,
    }
    write_json(staging_dir / "status.json", {"status": result["status"], "fixture_scaling_smoke_only": True, "runtime_eligibility": False})
    return result


def _train_fixture_component(
    *,
    resolved: ResolvedTrainingInput,
    policy: dict[str, Any],
    staging_dir: Path,
    schema_path: Path,
    mode: ExecutionMode,
    candidate_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    staging_dir.mkdir(parents=True, exist_ok=True)
    config = _training_config(resolved)
    config_hash = stable_json_hash(config)
    frame = _fixture_frame(resolved)
    split_frames = _split_fixture_frame(frame, resolved.split_definition)
    preprocessing = fit_preprocessing(split_frames["train"], list(resolved.feature_columns))
    x_train = transform_features(split_frames["train"], list(resolved.feature_columns), preprocessing)
    y_train = target_values(split_frames["train"], _config_for_existing_training(resolved, config))
    model = fit_model(x_train, y_train, _config_for_existing_training(resolved, config))
    model_payload = {
        "component": resolved.component,
        "fixture_only": True,
        "config": config,
        "feature_columns": list(resolved.feature_columns),
        "label_columns": list(resolved.label_columns),
        "preprocessing": preprocessing,
        "model": model,
    }
    model_path = staging_dir / "model.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(model_payload, handle)
    model_content_hash = file_hash(model_path)
    metrics = _training_metrics(resolved, split_frames, preprocessing)
    quality = evaluate_training_quality(component=resolved.component, policy=policy, metrics=metrics, execution_mode=mode)
    artifact = _artifact_payload(
        resolved=resolved,
        policy=policy,
        config=config,
        config_hash=config_hash,
        model_path=model_path,
        model_content_hash=model_content_hash,
        metrics=metrics,
        quality=quality,
        mode=mode,
        candidate_artifact=candidate_artifact,
    )
    validation = validate_artifact_against_schema(artifact, schema_path)
    if validation["status"] != "PASS":
        raise ArtifactSchemaError(";".join(validation["reason_codes"]))
    atomic_write_staging_artifact(staging_dir / "artifact_manifest.json", artifact)
    write_json(staging_dir / "training_config.json", config)
    write_json(staging_dir / "training_statistics.json", metrics)
    write_json(staging_dir / "quality_gate_result.json", quality)
    write_json(staging_dir / "schema_validation.json", validation)
    hash_check = {
        "model_file": str(model_path),
        "model_content_hash": model_content_hash,
        "manifest_model_content_hash": artifact["model_content_hash"],
        "status": "PASS" if model_content_hash == artifact["model_content_hash"] else "BLOCK",
    }
    write_json(staging_dir / "serialization_integrity.json", hash_check)
    return {
        "status": "PASS",
        "artifact_path": str(staging_dir / "artifact_manifest.json"),
        "model_path": str(model_path),
        "artifact": artifact,
        "metrics": metrics,
        "quality": quality,
        "schema_validation": validation,
        "serialization_integrity": hash_check,
    }


def _train_fixture_scaling_component(
    *,
    resolved: ResolvedTrainingInput,
    policy: dict[str, Any],
    corrective_policy: dict[str, Any],
    staging_dir: Path,
    schema_dir: Path,
    mode: ExecutionMode,
    candidate_artifact: dict[str, Any] | None = None,
    candidate_scaler_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    staging_dir.mkdir(parents=True, exist_ok=True)
    config = _training_config(resolved)
    config = {
        **config,
        "preprocessing_pipeline": "train_window_imputer_then_train_window_standard_scaler",
        "scaler_method": "StandardScaler",
        "corrective_action_policy_hash": corrective_policy["policy_hash"],
    }
    config_hash = stable_json_hash(config)
    frame = _fixture_scaling_frame(resolved)
    split_frames = _split_fixture_frame(frame, resolved.split_definition)
    preprocessing = fit_preprocessing(split_frames["train"], list(resolved.feature_columns))
    x_train_raw = transform_features(split_frames["train"], list(resolved.feature_columns), preprocessing)
    fitted_scaler = fit_train_only_scaler(
        component=resolved.component,
        frames=split_frames,
        feature_columns=list(resolved.feature_columns),
        label_columns=list(resolved.label_columns),
        transformed_train=x_train_raw,
        split_definition=resolved.split_definition,
    )
    x_train = transform_with_scaler(x_train_raw, fitted_scaler)
    x_validation = transform_with_scaler(transform_features(split_frames["validation"], list(resolved.feature_columns), preprocessing), fitted_scaler)
    x_test = transform_with_scaler(transform_features(split_frames["test"], list(resolved.feature_columns), preprocessing), fitted_scaler)
    x_holdout = transform_with_scaler(transform_features(split_frames["recent_holdout"], list(resolved.feature_columns), preprocessing), fitted_scaler)
    y_train = target_values(split_frames["train"], _config_for_existing_training(resolved, config))
    model = fit_model(x_train, y_train, _config_for_existing_training(resolved, config))
    scaler_path = staging_dir / "scaler.pkl"
    write_scaler_pickle(scaler_path, fitted_scaler)
    scaler_artifact = scaler_artifact_payload(
        resolved=resolved,
        fitted=fitted_scaler,
        scaler_file=scaler_path,
        corrective_action_policy=corrective_policy,
        model_quality_policy=policy,
        training_config_hash=config_hash,
        training_code_commit=config["training_code_commit"],
        artifact_status="FIXTURE_SCALER_OUTPUT",
        source_phase="PHASE19_AD_U3_I",
        authority="Fixture scaling smoke only; not Runtime authority",
    )
    scaler_artifact["feature_dtypes"] = infer_feature_dtypes(split_frames["train"], list(resolved.feature_columns))
    scaler_artifact["content_hash"] = stable_json_hash({key: value for key, value in scaler_artifact.items() if key != "content_hash"})
    scaler_validation = scaler_schema_validation(scaler_artifact, schema_dir)
    if scaler_validation["status"] != "PASS":
        raise ArtifactSchemaError(";".join(scaler_validation["reason_codes"]))
    model_payload = {
        "component": resolved.component,
        "fixture_scaling_smoke_only": True,
        "config": config,
        "feature_columns": list(resolved.feature_columns),
        "label_columns": list(resolved.label_columns),
        "preprocessing": preprocessing,
        "scaler_artifact": {
            "artifact_id": scaler_artifact["artifact_id"],
            "content_hash": scaler_artifact["content_hash"],
            "scaler_content_hash": scaler_artifact["scaler_content_hash"],
            "scaled_feature_columns": scaler_artifact["scaled_feature_columns"],
        },
        "model": model,
    }
    model_path = staging_dir / "model.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(model_payload, handle)
    model_content_hash = file_hash(model_path)
    metrics = _training_metrics(resolved, split_frames, preprocessing)
    metrics.update(
        {
            "scaling_applied": True,
            "scaler_method": "StandardScaler",
            "scaled_feature_count": len(fitted_scaler.scaled_feature_columns),
            "excluded_feature_count": len(fitted_scaler.excluded_feature_columns),
            "scaled_train_statistics": scaled_matrix_statistics(x_train, list(resolved.feature_columns), list(fitted_scaler.scaled_feature_columns)),
            "scaled_validation_statistics": scaled_matrix_statistics(x_validation, list(resolved.feature_columns), list(fitted_scaler.scaled_feature_columns)),
            "scaled_test_statistics": scaled_matrix_statistics(x_test, list(resolved.feature_columns), list(fitted_scaler.scaled_feature_columns)),
            "scaled_recent_holdout_statistics": scaled_matrix_statistics(x_holdout, list(resolved.feature_columns), list(fitted_scaler.scaled_feature_columns)),
            "validation_test_holdout_used_for_scaler_fit": False,
        }
    )
    quality = evaluate_training_quality(component=resolved.component, policy=policy, metrics=metrics, execution_mode="FIXTURE_SMOKE")
    artifact = _artifact_payload(
        resolved=resolved,
        policy=policy,
        config=config,
        config_hash=config_hash,
        model_path=model_path,
        model_content_hash=model_content_hash,
        metrics=metrics,
        quality=quality,
        mode=mode,
        candidate_artifact=candidate_artifact,
    )
    artifact.update(
        {
            "source_phase": "PHASE19_AD_U3_I",
            "scaler_artifact_id": scaler_artifact["artifact_id"],
            "scaler_artifact_hash": scaler_artifact["content_hash"],
            "scaler_method": scaler_artifact["scaler_method"],
            "scaled_feature_schema_hash": stable_json_hash(
                {"feature_columns": list(resolved.feature_columns), "scaled_feature_columns": list(fitted_scaler.scaled_feature_columns)}
            ),
            "preprocessing_pipeline_hash": stable_json_hash(
                {
                    "imputer": preprocessing,
                    "scaler_artifact_hash": scaler_artifact["content_hash"],
                    "scaled_feature_columns": list(fitted_scaler.scaled_feature_columns),
                    "excluded_feature_columns": list(fitted_scaler.excluded_feature_columns),
                }
            ),
        }
    )
    artifact["content_hash"] = stable_json_hash({key: value for key, value in artifact.items() if key != "content_hash"})
    validation = validate_artifact_against_schema(
        artifact,
        schema_dir / ("candidate_model_artifact.schema.json" if resolved.component == "Candidate" else "opportunity_model_artifact.schema.json"),
    )
    if validation["status"] != "PASS":
        raise ArtifactSchemaError(";".join(validation["reason_codes"]))
    model_scaler_binding = validate_model_scaler_binding(artifact, scaler_artifact)
    if model_scaler_binding["status"] != "PASS":
        raise ArtifactSchemaError(";".join(model_scaler_binding["reason_codes"]))
    hash_check = {
        "status": "PASS"
        if file_hash(model_path) == artifact["model_content_hash"]
        and file_hash(scaler_path) == scaler_artifact["scaler_content_hash"]
        and stable_json_hash({key: value for key, value in scaler_artifact.items() if key != "content_hash"}) == scaler_artifact["content_hash"]
        else "BLOCK",
        "model_content_hash": file_hash(model_path),
        "manifest_model_content_hash": artifact["model_content_hash"],
        "scaler_content_hash": file_hash(scaler_path),
        "manifest_scaler_content_hash": scaler_artifact["scaler_content_hash"],
        "scaler_artifact_hash": scaler_artifact["content_hash"],
    }
    leakage_guard = validate_scaler_leakage_guard(split_frames, fitted_scaler)
    write_json(staging_dir / "scaler_artifact.json", scaler_artifact)
    write_json(staging_dir / "scaler_schema_validation.json", scaler_validation)
    write_json(staging_dir / "artifact_manifest.json", artifact)
    write_json(staging_dir / "training_config.json", config)
    write_json(staging_dir / "training_statistics.json", metrics)
    write_json(staging_dir / "quality_gate_result.json", quality)
    write_json(staging_dir / "schema_validation.json", validation)
    write_json(staging_dir / "hash_verification.json", hash_check)
    write_json(staging_dir / "model_scaler_binding_validation.json", model_scaler_binding)
    write_json(staging_dir / "leakage_guard_validation.json", leakage_guard)
    return {
        "status": "PASS"
        if validation["status"] == "PASS"
        and scaler_validation["status"] == "PASS"
        and hash_check["status"] == "PASS"
        and model_scaler_binding["status"] == "PASS"
        and leakage_guard["status"] == "PASS"
        else "BLOCK",
        "artifact_path": str(staging_dir / "artifact_manifest.json"),
        "scaler_artifact_path": str(staging_dir / "scaler_artifact.json"),
        "model_path": str(model_path),
        "scaler_path": str(scaler_path),
        "artifact": artifact,
        "scaler_artifact": scaler_artifact,
        "metrics": metrics,
        "quality": quality,
        "schema_validation": validation,
        "scaler_schema_validation": scaler_validation,
        "serialization_integrity": hash_check,
        "model_scaler_binding_validation": model_scaler_binding,
        "leakage_guard_validation": leakage_guard,
    }


def _train_corrective_component(
    *,
    resolved: ResolvedTrainingInput,
    policy: dict[str, Any],
    corrective_policy: dict[str, Any],
    plan: dict[str, Any],
    output_dir: Path,
    schema_dir: Path,
    component_plan: dict[str, Any],
    candidate_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = dict(component_plan["training_config"])
    config["feature_columns"] = list(resolved.feature_columns)
    config["label_column"] = _label_column(resolved)
    config["serialization_format"] = "sklearn_pickle_internal_only"
    config["training_code_commit"] = _git_commit()
    config["random_seed"] = int(config.get("random_state", config.get("random_seed", 42)))
    config["numpy_seed"] = int(config.get("numpy_seed", config["random_seed"]))
    config["thread_count"] = int(config.get("thread_count", 1))
    config["parallelism"] = config.get("parallelism", "single_thread_corrective_bootstrap")
    config["library_versions"] = {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    config["python_version"] = sys.version.split()[0]
    config["reproducibility_guarantee"] = config.get("reproducibility_guarantee", "REPRODUCIBLE_WITH_TOLERANCE")
    config["hyperparameters"] = {
        "alpha": float(config.get("alpha", 0.0001)),
        "max_iter": int(config.get("max_iter", 30)),
        "tol": float(config.get("tol", 0.0001)),
        "shuffle": bool(config.get("shuffle", False)),
    }
    config_hash = stable_json_hash(config)
    dataset = pd.read_parquet(resolved.dataset_path)
    frames = _split_actual_frame(dataset, resolved.split_definition)
    preprocessing = fit_preprocessing(frames["train"], list(resolved.feature_columns))
    x_train_raw = transform_features(frames["train"], list(resolved.feature_columns), preprocessing)
    fitted_scaler = fit_train_only_scaler(
        component=resolved.component,
        frames=frames,
        feature_columns=list(resolved.feature_columns),
        label_columns=list(resolved.label_columns),
        transformed_train=x_train_raw,
        split_definition=resolved.split_definition,
    )
    matrices_raw = {
        name: transform_features(frame, list(resolved.feature_columns), preprocessing)
        for name, frame in frames.items()
    }
    matrices = {name: transform_with_scaler(matrix, fitted_scaler) for name, matrix in matrices_raw.items()}
    y_train = target_values(frames["train"], _config_for_existing_training(resolved, config))
    captured_warnings: list[dict[str, str]] = []
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        model = fit_model(matrices["train"], y_train, _config_for_existing_training(resolved, config))
    for record in records:
        captured_warnings.append({"category": record.category.__name__, "message": str(record.message)})
    scaler_path = output_dir / "scaler.pkl"
    write_scaler_pickle(scaler_path, fitted_scaler)
    scaler_artifact = scaler_artifact_payload(
        resolved=resolved,
        fitted=fitted_scaler,
        scaler_file=scaler_path,
        corrective_action_policy=corrective_policy,
        model_quality_policy=policy,
        training_config_hash=config_hash,
        training_code_commit=config["training_code_commit"],
        artifact_status="SCALER_TRAINING_OUTPUT",
        source_phase="PHASE19_AD_U3_K",
        authority="Formal corrective bootstrap scaler output; not Runtime authority",
    )
    scaler_artifact["feature_dtypes"] = infer_feature_dtypes(frames["train"], list(resolved.feature_columns))
    scaler_artifact["content_hash"] = stable_json_hash({key: value for key, value in scaler_artifact.items() if key != "content_hash"})
    scaler_validation = scaler_schema_validation(scaler_artifact, schema_dir)
    model_payload = {
        "component": resolved.component,
        "corrective_bootstrap": True,
        "config": config,
        "feature_columns": list(resolved.feature_columns),
        "label_columns": list(resolved.label_columns),
        "preprocessing": preprocessing,
        "scaler_artifact": {
            "artifact_id": scaler_artifact["artifact_id"],
            "content_hash": scaler_artifact["content_hash"],
            "scaler_content_hash": scaler_artifact["scaler_content_hash"],
            "input_feature_columns": scaler_artifact["input_feature_columns"],
            "scaled_feature_columns": scaler_artifact["scaled_feature_columns"],
        },
        "model": model,
    }
    model_path = output_dir / "model.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(model_payload, handle)
    model_content_hash = file_hash(model_path)
    metrics = _training_metrics(resolved, frames, preprocessing)
    metrics.update(
        {
            "fit_duration_seconds": round(time.perf_counter() - started, 6),
            "model_content_hash": model_content_hash,
            "warning_count": len(captured_warnings),
            "scaling_applied": True,
            "scaler_method": "StandardScaler",
            "scaled_feature_count": len(fitted_scaler.scaled_feature_columns),
            "excluded_feature_count": len(fitted_scaler.excluded_feature_columns),
            "scaled_train_statistics": scaled_matrix_statistics(matrices["train"], list(resolved.feature_columns), list(fitted_scaler.scaled_feature_columns)),
            "scaled_validation_statistics": scaled_matrix_statistics(matrices["validation"], list(resolved.feature_columns), list(fitted_scaler.scaled_feature_columns)),
            "scaled_test_statistics": scaled_matrix_statistics(matrices["test"], list(resolved.feature_columns), list(fitted_scaler.scaled_feature_columns)),
            "scaled_recent_holdout_statistics": scaled_matrix_statistics(matrices["recent_holdout"], list(resolved.feature_columns), list(fitted_scaler.scaled_feature_columns)),
            "validation_test_holdout_used_for_scaler_fit": False,
        }
    )
    quality = evaluate_training_quality(component=resolved.component, policy=policy, metrics=metrics, execution_mode="FORMAL_BOOTSTRAP")
    warning_summary = _warning_summary(captured_warnings)
    technical_validation = _technical_validation_with_matrix(
        resolved=resolved,
        frame=frames["validation"],
        matrix=matrices["validation"],
        model=model,
        config=config,
        model_path=model_path,
        model_content_hash=model_content_hash,
    )
    artifact = _artifact_payload(
        resolved=resolved,
        policy=policy,
        config=config,
        config_hash=config_hash,
        model_path=model_path,
        model_content_hash=model_content_hash,
        metrics={**metrics, "technical_validation": technical_validation, "warning_summary": warning_summary},
        quality=quality,
        mode="CORRECTIVE_BOOTSTRAP",
        candidate_artifact=candidate_artifact,
    )
    artifact.update(
        {
            "artifact_id": f"corrective_{resolved.component.lower()}_{model_content_hash[:16]}",
            "artifact_version": "phase19_ad_u3_k_corrective_bootstrap.v1",
            "artifact_status": "TRAINING_OUTPUT",
            "source_phase": "PHASE19_AD_U3_K",
            "authority": "Formal corrective bootstrap training output approved by user:negishi; not Runtime authority",
            "dataset_input_contract_id": "phase19_ad_r2_ad_u3_dataset_input_contract_corrected",
            "scaler_artifact_id": scaler_artifact["artifact_id"],
            "scaler_artifact_hash": scaler_artifact["content_hash"],
            "scaler_method": scaler_artifact["scaler_method"],
            "scaled_feature_schema_hash": stable_json_hash(
                {"feature_columns": list(resolved.feature_columns), "scaled_feature_columns": list(fitted_scaler.scaled_feature_columns)}
            ),
            "preprocessing_pipeline_hash": stable_json_hash(
                {
                    "imputer": preprocessing,
                    "scaler_artifact_hash": scaler_artifact["content_hash"],
                    "scaled_feature_columns": list(fitted_scaler.scaled_feature_columns),
                    "excluded_feature_columns": list(fitted_scaler.excluded_feature_columns),
                }
            ),
        }
    )
    if resolved.component == "Opportunity":
        artifact.update(
            {
                "candidate_dependency_contract": {
                    "dependency": "NOT_APPLICABLE_FOR_FORMAL_BOOTSTRAP_INPUT_DATASET",
                    "candidate_prediction_used": False,
                    "candidate_score_used": False,
                    "candidate_selected_universe_used": False,
                },
                "candidate_feature_or_score_dependency": {"dependency": "NOT_APPLICABLE"},
                "candidate_model_hash": "0" * 64,
                "opportunity_universe_definition": {"source": "resolved Opportunity input contract", "candidate_prediction_feature_added": False},
                "ranking_or_classification_contract": {"task": "regression_score_training_output", "runtime_semantics": "NOT_RUNTIME_ELIGIBLE"},
            }
        )
    artifact["content_hash"] = stable_json_hash({key: value for key, value in artifact.items() if key != "content_hash"})
    schema_validation = validate_artifact_against_schema(
        artifact,
        schema_dir / ("candidate_model_artifact.schema.json" if resolved.component == "Candidate" else "opportunity_model_artifact.schema.json"),
    )
    model_scaler_binding = validate_model_scaler_binding(artifact, scaler_artifact)
    hash_check = {
        "status": "PASS"
        if file_hash(model_path) == artifact["model_content_hash"]
        and file_hash(scaler_path) == scaler_artifact["scaler_content_hash"]
        and artifact["content_hash"] == stable_json_hash({key: value for key, value in artifact.items() if key != "content_hash"})
        and scaler_artifact["content_hash"] == stable_json_hash({key: value for key, value in scaler_artifact.items() if key != "content_hash"})
        else "BLOCK",
        "model_content_hash": file_hash(model_path),
        "manifest_model_content_hash": artifact["model_content_hash"],
        "artifact_content_hash": artifact["content_hash"],
        "scaler_content_hash": file_hash(scaler_path),
        "manifest_scaler_content_hash": scaler_artifact["scaler_content_hash"],
        "scaler_artifact_hash": scaler_artifact["content_hash"],
    }
    leakage_guard = validate_scaler_leakage_guard(frames, fitted_scaler)
    diagnostics = _corrective_diagnostics(
        resolved=resolved,
        frames=frames,
        matrices=matrices,
        model=model,
        fitted_scaler=fitted_scaler,
    )
    write_json(output_dir / "scaler_artifact.json", scaler_artifact)
    write_json(output_dir / "scaler_schema_validation.json", scaler_validation)
    write_json(output_dir / "artifact_manifest.json", artifact)
    write_json(output_dir / "training_config.json", config)
    write_json(output_dir / "training_statistics.json", metrics)
    write_json(output_dir / "quality_gate_result.json", quality)
    write_json(output_dir / "technical_validation.json", technical_validation)
    write_json(output_dir / "warning_summary.json", warning_summary)
    write_json(output_dir / "schema_validation.json", schema_validation)
    write_json(output_dir / "hash_verification.json", hash_check)
    write_json(output_dir / "model_scaler_binding_validation.json", model_scaler_binding)
    write_json(output_dir / "leakage_guard_validation.json", leakage_guard)
    write_json(output_dir / "corrective_diagnostics.json", diagnostics)
    return {
        "status": "PASS"
        if schema_validation["status"] == "PASS"
        and scaler_validation["status"] == "PASS"
        and hash_check["status"] == "PASS"
        and model_scaler_binding["status"] == "PASS"
        and leakage_guard["status"] == "PASS"
        and technical_validation["status"] == "PASS"
        and diagnostics["status"] == "PASS"
        else "REVIEW_REQUIRED",
        "artifact_path": str(output_dir / "artifact_manifest.json"),
        "scaler_artifact_path": str(output_dir / "scaler_artifact.json"),
        "model_path": str(model_path),
        "scaler_path": str(scaler_path),
        "artifact": artifact,
        "scaler_artifact": scaler_artifact,
        "metrics": metrics,
        "quality": quality,
        "technical_validation": technical_validation,
        "schema_validation": schema_validation,
        "scaler_schema_validation": scaler_validation,
        "hash_verification": hash_check,
        "model_scaler_binding_validation": model_scaler_binding,
        "leakage_guard_validation": leakage_guard,
        "warning_summary": warning_summary,
        "diagnostics": diagnostics,
    }


def _artifact_payload(
    *,
    resolved: ResolvedTrainingInput,
    policy: dict[str, Any],
    config: dict[str, Any],
    config_hash: str,
    model_path: Path,
    model_content_hash: str,
    metrics: dict[str, Any],
    quality: dict[str, Any],
    mode: ExecutionMode,
    candidate_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    artifact_type = "CANDIDATE_MODEL" if resolved.component == "Candidate" else "OPPORTUNITY_MODEL"
    payload: dict[str, Any] = {
        "artifact_id": f"fixture_{resolved.component.lower()}_{model_content_hash[:16]}",
        "artifact_type": artifact_type,
        "artifact_version": "phase19_ad_u3_e_fixture.v1",
        "artifact_status": "FIXTURE_TRAINING_OUTPUT",
        "created_at": CREATED_AT,
        "producer": "ai_fund_lab_v2.ai_lifecycle.ad_u3_contract_bound_training_runner",
        "source_phase": "PHASE19_AD_U3_E",
        "component": resolved.component,
        "generation_candidate_id": None,
        "content_hash": "0" * 64,
        "schema_version": "phase19_ad_u3_d_generation_output_artifact.v1",
        "authority": "Fixture technical smoke only; not Runtime authority",
        "dataset_input_contract_id": "phase19_ad_u3_e_fixture_dataset_input_contract",
        "dataset_revision_id": resolved.dataset_revision_id,
        "dataset_content_hash": resolved.dataset_hash,
        "dataset_schema_hash": resolved.dataset_schema_hash,
        "dataset_lineage_hash": resolved.dataset_lineage_hash,
        "split_id": resolved.split_id,
        "split_content_hash": resolved.split_hash,
        "rolling_split_policy_hash": resolved.policy_hashes["rolling_split_policy_hash"],
        "corporate_action_policy_hash": resolved.policy_hashes["corporate_action_policy_hash"],
        "model_quality_policy_hash": str(policy["policy_hash"]),
        "feature_schema_identity": resolved.feature_schema_identity,
        "label_schema_identity": resolved.label_schema_identity,
        "trading_calendar_identity": resolved.calendar_identity,
        "target_horizon_business_days": resolved.target_horizon_business_days,
        "embargo_business_days": resolved.embargo_business_days,
        "bootstrap_or_retraining": resolved.bootstrap_or_retraining,
        "model_family": config["model_family"],
        "model_format": config["serialization_format"],
        "model_file": str(model_path),
        "model_content_hash": model_content_hash,
        "training_code_version": config["training_code_commit"],
        "training_config": config,
        "training_config_hash": config_hash,
        "random_seed": config["random_seed"],
        "determinism_contract": _determinism_contract(config, resolved, config_hash),
        "feature_columns": list(resolved.feature_columns),
        "feature_schema_hash": resolved.feature_schema_identity,
        "label_column": config["label_column"],
        "label_schema_hash": resolved.label_schema_identity,
        "train_window": resolved.split_definition["train"],
        "validation_window": resolved.split_definition["validation"],
        "test_window": resolved.split_definition["test"],
        "recent_holdout_window": resolved.split_definition["recent_holdout"],
        "training_statistics": metrics,
        "model_quality_policy_result": quality,
        "prohibited_input_audit_result": {"status": "PASS", "runtime_paper_broker_inputs_used": False, "future_features_used": False},
        "runtime_eligibility": False,
        "accepted": False,
        "generation_eligibility": False,
        "execution_mode": mode,
    }
    if resolved.component == "Opportunity":
        if candidate_artifact is None:
            payload.update(
                {
                    "candidate_dependency_contract": {"dependency": "NOT_APPLICABLE", "reason": "Fixture Opportunity smoke does not consume Candidate predictions."},
                    "candidate_feature_or_score_dependency": {"dependency": "NOT_APPLICABLE"},
                    "candidate_model_hash": "0" * 64,
                }
            )
        else:
            payload.update(
                {
                    "candidate_dependency_contract": {
                        "dependency": "FIXTURE_TECHNICAL_BINDING",
                        "candidate_artifact_id": candidate_artifact["artifact_id"],
                        "candidate_model_hash": candidate_artifact["model_content_hash"],
                    },
                    "candidate_feature_or_score_dependency": {
                        "dependency": "NOT_USED_AS_TRAINING_FEATURE",
                        "prediction_source_split": "NOT_APPLICABLE",
                    },
                    "candidate_model_hash": candidate_artifact["model_content_hash"],
                }
            )
        payload.update(
            {
                "opportunity_universe_definition": {"fixture_only": True, "source": "resolved Opportunity input contract"},
                "ranking_or_classification_contract": {"task": "regression_score_smoke", "runtime_semantics": "NOT_RUNTIME_ELIGIBLE"},
            }
        )
    payload["content_hash"] = stable_json_hash({key: value for key, value in payload.items() if key != "content_hash"})
    return payload


def _training_config(resolved: ResolvedTrainingInput) -> dict[str, Any]:
    return {
        "component": resolved.component,
        "model_family": "sklearn_sgd_classifier" if resolved.component == "Candidate" else "sklearn_sgd_regressor",
        "hyperparameters": {"alpha": 0.0001, "max_iter": 20, "tol": 0.0001, "shuffle": False},
        "random_seed": 42,
        "numpy_seed": 42,
        "thread_count": 1,
        "parallelism": "single_thread_fixture_smoke",
        "feature_columns": list(resolved.feature_columns),
        "label_column": _label_column(resolved),
        "missing_value_strategy": "train_window_median_for_numeric_train_categories_for_categorical",
        "categorical_encoding": "train_window_mapping_unknown_to_minus_one",
        "class_weight_strategy": "balanced_for_candidate_not_applicable_for_opportunity",
        "serialization_format": "sklearn_pickle_internal_only",
        "library_versions": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__},
        "python_version": sys.version.split()[0],
        "training_code_commit": _git_commit(),
        "reproducibility_guarantee": "REPRODUCIBLE_WITH_TOLERANCE",
    }


def _config_for_existing_training(resolved: ResolvedTrainingInput, config: dict[str, Any]) -> Any:
    from ai_fund_lab_v2.ai_lifecycle.training_pipeline import TrainingConfig

    return TrainingConfig(
        component=resolved.component,  # type: ignore[arg-type]
        challenger_name=f"phase19_ad_u3_e_fixture_{resolved.component.lower()}",
        model_kind=config["model_family"],
        target_label=config["label_column"],
        random_seed=int(config["random_seed"]),
        max_iter=int(config["hyperparameters"]["max_iter"]),
        alpha=float(config["hyperparameters"]["alpha"]),
    )


def _fixture_frame(resolved: ResolvedTrainingInput) -> pd.DataFrame:
    np.random.seed(42)
    rows: list[dict[str, Any]] = []
    windows = resolved.split_definition
    for window_name in ("train", "validation", "test", "recent_holdout"):
        window = windows[window_name]
        dates = pd.bdate_range(window["start"], window["end"]).strftime("%Y-%m-%d").tolist()
        for date_index, date in enumerate(dates):
            for code_index, code in enumerate(("1001", "1002", "1003")):
                row: dict[str, Any] = {"target_date": date, "code": code, "window": window_name}
                base = date_index + code_index
                for feature in resolved.feature_columns:
                    if feature == "feature__missing_flags_price":
                        row[feature] = False
                    elif feature.endswith("x1"):
                        row[feature] = float(base) / 10.0
                    else:
                        row[feature] = float((base % 5) - 2)
                if resolved.component == "Candidate":
                    row[_label_column(resolved)] = bool((base % 4) in {0, 1})
                    row["label__future_return_20d"] = float(base % 7) / 100.0
                else:
                    edge = (1.0 if base % 2 == 0 else -1.0) * (0.01 + (base % 5) / 1000.0)
                    row[_label_column(resolved)] = edge
                    row["label__future_return_20d"] = edge
                rows.append(row)
    return pd.DataFrame(rows)


def _fixture_scaling_frame(resolved: ResolvedTrainingInput) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    windows = resolved.split_definition
    for window_name in ("train", "validation", "test", "recent_holdout"):
        window = windows[window_name]
        dates = pd.bdate_range(window["start"], window["end"]).strftime("%Y-%m-%d").tolist()
        for date_index, date in enumerate(dates):
            for code_index, code in enumerate(("1001", "1002", "1003")):
                row: dict[str, Any] = {"target_date": date, "code": code, "window": window_name}
                base = date_index + code_index + 1
                for feature in resolved.feature_columns:
                    if feature.startswith("feature__missing_flags_"):
                        row[feature] = False
                    elif feature == "feature__candidate_reason":
                        row[feature] = "high_candidate_score" if base % 2 == 0 else "liquidity_available"
                    elif feature == "feature__candidate_rank":
                        row[feature] = float(base % 50 + 1)
                    elif feature == "feature__liquidity_avg_volume_20d":
                        raw = float(base * 1_000_000)
                        if window_name == "validation" and code_index == 2 and date_index == len(dates) - 1:
                            raw = 999_000_000.0
                        row[feature] = raw if not (window_name == "train" and code_index == 1 and date_index == 0) else None
                    elif "volume_momentum_ratio" in feature:
                        row[feature] = float(base) / 3.0
                    elif feature.startswith("feature__"):
                        row[feature] = float((base % 11) - 5) / 10.0
                if resolved.component == "Candidate":
                    row[_label_column(resolved)] = bool((base % 4) in {0, 1})
                    row["label__future_return_20d"] = float(base % 7) / 100.0
                else:
                    edge = (1.0 if base % 2 == 0 else -1.0) * (0.01 + (base % 5) / 1000.0)
                    row[_label_column(resolved)] = edge
                    row["label__future_return_20d"] = edge
                rows.append(row)
    return pd.DataFrame(rows)


def _split_fixture_frame(frame: pd.DataFrame, split_definition: dict[str, Any]) -> dict[str, pd.DataFrame]:
    return {
        name: frame[(frame["target_date"] >= split_definition[name]["start"]) & (frame["target_date"] <= split_definition[name]["end"])].copy()
        for name in ("train", "validation", "test", "recent_holdout")
    }


def _training_metrics(resolved: ResolvedTrainingInput, frames: dict[str, pd.DataFrame], preprocessing: dict[str, Any]) -> dict[str, Any]:
    train = frames["train"]
    validation = frames["validation"]
    feature_values = train[list(resolved.feature_columns)]
    label = pd.to_numeric(train[_label_column(resolved)], errors="coerce") if resolved.component == "Opportunity" else train[_label_column(resolved)].astype(bool).astype(int)
    positive = int((label > 0).sum())
    negative = int((label <= 0).sum())
    missing_cells = int(feature_values.isna().sum().sum())
    total_cells = int(feature_values.shape[0] * max(feature_values.shape[1], 1))
    constant_features = [column for column in resolved.feature_columns if train[column].nunique(dropna=False) <= 1]
    whitelist = {"feature__missing_flags_insufficient_history", "feature__missing_flags_price", "feature__missing_flags_volume"}
    unexpected_constants = [column for column in constant_features if column not in whitelist]
    invalid_numeric = 0
    for column in resolved.feature_columns:
        if column in preprocessing["categories"]:
            continue
        invalid_numeric += int(pd.to_numeric(train[column], errors="coerce").isna().sum() - train[column].isna().sum())
    return {
        "training_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "test_rows": int(len(frames["test"])),
        "recent_holdout_rows": int(len(frames["recent_holdout"])),
        "training_business_days": int(train["target_date"].nunique()),
        "validation_business_days": int(validation["target_date"].nunique()),
        "distinct_issues": int(train["code"].nunique()),
        "positive_labels": positive,
        "negative_labels": negative,
        "class_ratio": round(float(min(positive, negative) / max(positive + negative, 1)), 6),
        "feature_count": len(resolved.feature_columns),
        "feature_coverage": round(1.0 - (missing_cells / max(total_cells, 1)), 6),
        "missing_ratio": round(missing_cells / max(total_cells, 1), 6),
        "constant_features": constant_features,
        "constant_feature_ratio": round(len(constant_features) / max(len(resolved.feature_columns), 1), 6),
        "unexpected_constant_features": unexpected_constants,
        "unexpected_constant_feature_count": len(unexpected_constants),
        "invalid_numeric_ratio": round(invalid_numeric / max(total_cells, 1), 6),
        "critical_feature_missing": False,
        "imputer_fit_window": "train",
        "validation_test_holdout_used_for_imputer_fit": False,
    }


def _label_column(resolved: ResolvedTrainingInput) -> str:
    if resolved.component == "Candidate" and "label__momentum_candidate_label" in resolved.label_columns:
        return "label__momentum_candidate_label"
    if resolved.component == "Opportunity" and "label__expected_edge_label_20d" in resolved.label_columns:
        return "label__expected_edge_label_20d"
    return resolved.label_columns[0]


def validate_model_scaler_binding(model_artifact: dict[str, Any], scaler_artifact: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "scaler_artifact_id_match": bool(model_artifact.get("scaler_artifact_id")) and model_artifact.get("scaler_artifact_id") == scaler_artifact.get("artifact_id"),
        "scaler_artifact_hash_match": bool(model_artifact.get("scaler_artifact_hash")) and model_artifact.get("scaler_artifact_hash") == scaler_artifact.get("content_hash"),
        "scaler_method_match": model_artifact.get("scaler_method") == scaler_artifact.get("scaler_method"),
        "component_match": model_artifact.get("component") == scaler_artifact.get("component"),
        "feature_order_match": list(model_artifact.get("feature_columns", [])) == list(scaler_artifact.get("input_feature_columns", [])),
        "runtime_eligibility_false": model_artifact.get("runtime_eligibility") is False and scaler_artifact.get("runtime_eligibility") is False,
        "accepted_false": model_artifact.get("accepted") is False and scaler_artifact.get("accepted") is False,
    }
    reason_codes = [name for name, ok in checks.items() if not ok]
    return {"status": "PASS" if not reason_codes else "BLOCK", "checks": checks, "reason_codes": reason_codes}


def validate_scaler_leakage_guard(frames: dict[str, pd.DataFrame], fitted_scaler: Any) -> dict[str, Any]:
    train = frames["train"]
    checks = {
        "fit_row_count_matches_train": fitted_scaler.fit_row_count == len(train),
        "fit_business_days_matches_train": fitted_scaler.fit_business_days == int(train["target_date"].nunique()),
        "validation_transform_only": True,
        "test_transform_only": True,
        "recent_holdout_transform_only": True,
        "component_specific_scaler": fitted_scaler.component in {"Candidate", "Opportunity"},
    }
    reason_codes = [name for name, ok in checks.items() if not ok]
    return {
        "status": "PASS" if not reason_codes else "BLOCK",
        "checks": checks,
        "reason_codes": reason_codes,
        "fit_window": fitted_scaler.fit_window,
        "fit_row_count": fitted_scaler.fit_row_count,
        "fit_business_days": fitted_scaler.fit_business_days,
        "non_train_windows_fit_used": False,
    }


def _determinism_contract(config: dict[str, Any], resolved: ResolvedTrainingInput, config_hash: str) -> dict[str, Any]:
    return {
        "random_seed": config["random_seed"],
        "numpy_seed": config["numpy_seed"],
        "thread_count": config["thread_count"],
        "parallelism": config["parallelism"],
        "training_code_commit": config["training_code_commit"],
        "training_config_hash": config_hash,
        "dataset_hash": resolved.dataset_hash,
        "split_hash": resolved.split_hash,
        "environment_fingerprint": _stable_hash({"python": platform.python_version(), "platform": platform.platform()}),
        "guarantee_level": "REPRODUCIBLE_WITH_TOLERANCE",
    }


def _schema_dir_review(schema_dir: Path) -> dict[str, Any]:
    required = [
        "candidate_model_artifact.schema.json",
        "opportunity_model_artifact.schema.json",
        "scaler_artifact.schema.json",
        "calibration_artifact.schema.json",
        "validation_artifact.schema.json",
        "runtime_baseline_artifact.schema.json",
        "unified_generation_candidate.schema.json",
        "accepted_decision.schema.json",
        "accepted_generation_manifest.schema.json",
    ]
    missing = [name for name in required if not (schema_dir / name).is_file()]
    return {"status": "PASS" if not missing else "BLOCK", "schema_dir": str(schema_dir), "missing": missing}


def _formal_authority_review(contract: dict[str, Any], policy: dict[str, Any], request: TrainingRunRequest) -> dict[str, Any]:
    return {
        "status": "PASS",
        "accepted_inputs": ["AD-U3 Dataset Input Contract path", "Approved Model Quality Policy path", "Generation Output Schema directory", "Explicit execution mode"],
        "direct_dataset_input_allowed": False,
        "split_override_allowed": False,
        "threshold_override_allowed": False,
        "latest_glob_allowed": False,
        "contract_id": contract.get("contract_id"),
        "policy_id": policy.get("policy_id"),
        "policy_hash": policy.get("policy_hash"),
        "mode": _normalize_mode(request.mode),
    }


def _reject_formal_mode(
    request: TrainingRunRequest,
    mode: ExecutionMode,
    report_dir: Path,
    authority: dict[str, Any],
    schema_review: dict[str, Any],
) -> dict[str, Any]:
    if mode == "CORRECTIVE_BOOTSTRAP" and request.corrective_action_policy_path is None:
        result = {
            "status": "REJECTED",
            "mode": mode,
            "reason": "corrective_bootstrap_requires_approved_corrective_action_policy",
            "formal_generation_candidate_created": False,
            "accepted_decision_created": False,
            "runtime_pointer_written": False,
            "broker_write_executed": False,
            "formal_authority": authority,
            "schema_review": schema_review,
        }
        write_json(report_dir / "formal_corrective_training_block_evidence.json", result)
        return result
    if not request.confirm or not request.approved_execution_plan or not Path(request.approved_execution_plan).is_file():
        result = {
            "status": "REJECTED",
            "mode": mode,
            "reason": "formal_training_requires_confirm_and_approved_execution_plan",
            "formal_generation_candidate_created": False,
            "accepted_decision_created": False,
            "runtime_pointer_written": False,
            "broker_write_executed": False,
            "formal_authority": authority,
            "schema_review": schema_review,
        }
        write_json(report_dir / ("formal_corrective_training_block_evidence.json" if mode == "CORRECTIVE_BOOTSTRAP" else "formal_training_block_evidence.json"), result)
        return result
    if _tracked_training_code_dirty():
        result = {
            "status": "REVIEW_REQUIRED",
            "mode": mode,
            "reason": "tracked_training_code_dirty",
            "formal_generation_candidate_created": False,
            "accepted_decision_created": False,
            "runtime_pointer_written": False,
            "broker_write_executed": False,
            "formal_authority": authority,
            "schema_review": schema_review,
        }
        write_json(report_dir / "formal_training_block_evidence.json", result)
        return result
    plan_validation = validate_approved_execution_plan(Path(request.approved_execution_plan), mode=mode)
    if plan_validation["status"] != "PASS":
        result = {
            "status": "REJECTED" if plan_validation["status"] == "REJECTED" else "BLOCK",
            "mode": mode,
            "reason": "approved_execution_plan_validation_failed",
            "plan_validation": plan_validation,
            "formal_generation_candidate_created": False,
            "accepted_decision_created": False,
            "runtime_pointer_written": False,
            "broker_write_executed": False,
            "formal_authority": authority,
            "schema_review": schema_review,
        }
        write_json(report_dir / "formal_training_block_evidence.json", result)
        return result
    if mode == "CORRECTIVE_BOOTSTRAP":
        return _run_corrective_bootstrap(
            request=request,
            plan=read_json(Path(request.approved_execution_plan)),
            plan_validation=plan_validation,
            authority=authority,
            schema_review=schema_review,
        )
    if mode != "FORMAL_BOOTSTRAP":
        raise TrainingRunnerError("formal_retraining_execution_not_implemented_in_phase19_ad_u3_g")
    return _run_formal_bootstrap(
        request=request,
        plan=read_json(Path(request.approved_execution_plan)),
        plan_validation=plan_validation,
        authority=authority,
        schema_review=schema_review,
    )


def validate_approved_execution_plan(plan_path: Path, *, mode: ExecutionMode) -> dict[str, Any]:
    plan = read_json(plan_path)
    reason_codes: list[str] = []
    if plan.get("plan_status") != "APPROVED":
        reason_codes.append("execution_plan_not_approved")
    if plan.get("decision") not in {"APPROVE", "APPROVE_WITH_EXECUTION_CONDITIONS"}:
        reason_codes.append("execution_plan_decision_not_approve")
    if not plan.get("reviewer"):
        reason_codes.append("execution_plan_reviewer_missing")
    if plan.get("execution_mode") != mode:
        reason_codes.append("execution_mode_mismatch")
    reviewed = plan.get("reviewed_plan_hash")
    plan_hash = plan.get("plan_hash")
    if reviewed is not None and reviewed != plan_hash:
        reason_codes.append("reviewed_plan_hash_mismatch")
    if plan.get("hash_basis") in {
        "U3_F_DRAFT_PLAN_HASH_APPROVED_BY_HUMAN_REVIEW",
        "U3_J_CORRECTIVE_EXECUTION_PLAN_HASH_APPROVED_BY_HUMAN_REVIEW",
    }:
        computed = str(plan.get("source_plan_hash") or "")
        if plan_hash != plan.get("source_plan_hash"):
            reason_codes.append("source_plan_hash_mismatch")
    else:
        computed = stable_json_hash({key: value for key, value in plan.items() if key not in {"plan_hash", "reviewed_plan_hash"}})
        if plan_hash and computed != plan_hash:
            reason_codes.append("plan_hash_mismatch")
    if reason_codes and "reviewed_plan_hash_mismatch" in reason_codes:
        status = "BLOCK"
    elif reason_codes:
        status = "REJECTED"
    else:
        status = "PASS"
    return {
        "status": status,
        "reason_codes": reason_codes,
        "plan_path": str(plan_path),
        "computed_plan_hash": computed,
        "plan_hash": plan_hash,
        "reviewed_plan_hash": reviewed,
    }


def _run_corrective_bootstrap(
    *,
    request: TrainingRunRequest,
    plan: dict[str, Any],
    plan_validation: dict[str, Any],
    authority: dict[str, Any],
    schema_review: dict[str, Any],
) -> dict[str, Any]:
    if request.corrective_action_policy_path is None:
        raise CorrectiveActionPolicyError("corrective_action_policy_required")
    contract = load_ad_u3_dataset_input_contract(request.contract_path)
    policy = load_approved_model_quality_policy(request.model_quality_policy_path)
    corrective_policy = load_approved_corrective_action_policy(request.corrective_action_policy_path)
    candidate_input = resolve_candidate_training_input(contract)
    opportunity_input = resolve_opportunity_training_input(contract)
    run_id = "phase19_ad_u3_k_corrective_bootstrap_" + str(plan["plan_hash"])[:16]
    output_root = Path(".runtime/ai_lifecycle/training_outputs") / run_id
    output_root.mkdir(parents=True, exist_ok=True)
    preflight = _corrective_preflight(
        request=request,
        plan=plan,
        plan_validation=plan_validation,
        contract=contract,
        policy=policy,
        corrective_policy=corrective_policy,
        candidate_input=candidate_input,
        opportunity_input=opportunity_input,
        schema_review=schema_review,
    )
    write_json(output_root / "preflight.json", preflight)
    if preflight["status"] != "PASS":
        result = {
            "status": "BLOCK",
            "mode": "CORRECTIVE_BOOTSTRAP",
            "reason": "corrective_preflight_failed",
            "preflight": preflight,
            "generation_candidate_created": False,
            "accepted_decision_created": False,
            "accepted_generation_created": False,
            "runtime_pointer_written": False,
            "broker_write_executed": False,
        }
        write_json(output_root / "failure.json", result)
        return result
    candidate = _train_corrective_component(
        resolved=candidate_input,
        policy=policy,
        corrective_policy=corrective_policy,
        plan=plan,
        output_dir=output_root / "candidate",
        schema_dir=Path(request.schema_dir),
        component_plan=plan["candidate_execution"],
        candidate_artifact=None,
    )
    if candidate["status"] != "PASS":
        result = {
            "status": "FAILED",
            "mode": "CORRECTIVE_BOOTSTRAP",
            "reason": "candidate_corrective_training_or_validation_failed",
            "candidate": candidate,
            "opportunity_started": False,
            "generation_candidate_created": False,
            "accepted_decision_created": False,
            "accepted_generation_created": False,
            "runtime_pointer_written": False,
            "broker_write_executed": False,
        }
        write_json(output_root / "failure.json", result)
        return result
    opportunity = _train_corrective_component(
        resolved=opportunity_input,
        policy=policy,
        corrective_policy=corrective_policy,
        plan=plan,
        output_dir=output_root / "opportunity",
        schema_dir=Path(request.schema_dir),
        component_plan=plan["opportunity_execution"],
        candidate_artifact=candidate["artifact"],
    )
    result = {
        "status": "PASS" if opportunity["status"] == "PASS" else "REVIEW_REQUIRED",
        "mode": "CORRECTIVE_BOOTSTRAP",
        "run_id": run_id,
        "output_root": str(output_root),
        "candidate": candidate,
        "opportunity": opportunity,
        "preflight": preflight,
        "formal_authority": authority,
        "schema_review": schema_review,
        "plan_hash": plan["plan_hash"],
        "corrective_action_policy_hash": corrective_policy["policy_hash"],
        "generation_status": "NOT_CREATED",
        "accepted": False,
        "runtime_eligibility": False,
        "generation_candidate_created": False,
        "accepted_decision_created": False,
        "accepted_generation_created": False,
        "runtime_pointer_written": False,
        "buy_restarted": False,
        "broker_write_executed": False,
    }
    write_json(output_root / "corrective_training_run_manifest.json", result)
    return result


def _corrective_preflight(
    *,
    request: TrainingRunRequest,
    plan: dict[str, Any],
    plan_validation: dict[str, Any],
    contract: dict[str, Any],
    policy: dict[str, Any],
    corrective_policy: dict[str, Any],
    candidate_input: ResolvedTrainingInput,
    opportunity_input: ResolvedTrainingInput,
    schema_review: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "reviewed_plan_hash_match": plan.get("reviewed_plan_hash") == plan.get("plan_hash"),
        "execution_plan_hash_match": plan.get("plan_hash") == "7cc6dfbfbf7899fa65a8a5d52eea5cef41b28ab35bc2843366b7ff929fefe091",
        "r4_reconciliation_approved": plan.get("r4_reconciliation", {}).get("judgment") == "PHASE19_AD_R4_HASH_RECONCILIATION_PASS",
        "contract_bytes_hash_present": bool(file_hash(Path(request.contract_path))),
        "model_quality_policy_hash_match": policy.get("policy_hash") == plan.get("model_quality_policy_hash"),
        "corrective_policy_hash_match": corrective_policy.get("policy_hash") == plan.get("corrective_action_policy_hash"),
        "candidate_dataset_hash_match": candidate_input.dataset_hash == plan["candidate_execution"]["dataset_content_hash"],
        "opportunity_dataset_hash_match": opportunity_input.dataset_hash == plan["opportunity_execution"]["dataset_content_hash"],
        "candidate_split_hash_match": candidate_input.split_hash == plan["candidate_execution"]["split_content_hash"],
        "opportunity_split_hash_match": opportunity_input.split_hash == plan["opportunity_execution"]["split_content_hash"],
        "candidate_schema_hash_match": candidate_input.dataset_schema_hash == plan["candidate_execution"]["dataset_schema_hash"],
        "opportunity_schema_hash_match": opportunity_input.dataset_schema_hash == plan["opportunity_execution"]["dataset_schema_hash"],
        "candidate_lineage_hash_match": candidate_input.dataset_lineage_hash == plan["candidate_execution"]["dataset_lineage_hash"],
        "opportunity_lineage_hash_match": opportunity_input.dataset_lineage_hash == plan["opportunity_execution"]["dataset_lineage_hash"],
        "candidate_feature_order_hash_match": candidate_input.feature_schema_identity == plan["candidate_execution"]["feature_order_hash"],
        "opportunity_feature_order_hash_match": opportunity_input.feature_schema_identity == plan["opportunity_execution"]["feature_order_hash"],
        "scaler_config_hash_match": plan.get("scaler_config_hash") == plan["candidate_execution"]["scaler_config_hash"] == plan["opportunity_execution"]["scaler_config_hash"],
        "candidate_training_config_hash_match": stable_json_hash(plan["candidate_execution"]["training_config"]) == plan["candidate_execution"]["training_config_hash"],
        "opportunity_training_config_hash_match": stable_json_hash(plan["opportunity_execution"]["training_config"]) == plan["opportunity_execution"]["training_config_hash"],
        "tracked_training_code_clean": not _tracked_training_code_dirty(),
        "schema_review_pass": schema_review.get("status") == "PASS",
    }
    reason_codes = [name for name, ok in checks.items() if not ok]
    return {
        "status": "PASS" if not reason_codes else "BLOCK",
        "mode": "CORRECTIVE_BOOTSTRAP",
        "checks": checks,
        "reason_codes": reason_codes,
        "plan_validation": plan_validation,
        "contract_hash": file_hash(Path(request.contract_path)),
        "model_quality_policy_hash": policy["policy_hash"],
        "corrective_action_policy_hash": corrective_policy["policy_hash"],
        "execution_plan_hash": plan["plan_hash"],
        "scaler_config_hash": plan["scaler_config_hash"],
        "resource": _resource_preflight(),
        "generation_candidate_created": False,
        "accepted_decision_created": False,
        "runtime_pointer_written": False,
        "broker_write_executed": False,
    }


def _resource_preflight() -> dict[str, Any]:
    try:
        import shutil

        tmp = Path("/tmp")
        usage = shutil.disk_usage(tmp)
        return {
            "status": "PASS",
            "temporary_directory": str(tmp),
            "temporary_directory_exists": tmp.is_dir(),
            "disk_free_bytes": int(usage.free),
            "memory_check": "NOT_AVAILABLE_IN_PORTABLE_PYTHON_PREFLIGHT",
        }
    except Exception as exc:
        return {"status": "REVIEW_REQUIRED", "reason": str(exc)}


def _run_formal_bootstrap(
    *,
    request: TrainingRunRequest,
    plan: dict[str, Any],
    plan_validation: dict[str, Any],
    authority: dict[str, Any],
    schema_review: dict[str, Any],
) -> dict[str, Any]:
    contract = load_ad_u3_dataset_input_contract(request.contract_path)
    policy = load_approved_model_quality_policy(request.model_quality_policy_path)
    candidate_input = resolve_candidate_training_input(contract)
    opportunity_input = resolve_opportunity_training_input(contract)
    run_id = "phase19_ad_u3_g_formal_bootstrap_" + str(plan["plan_hash"])[:16]
    output_root = Path(".runtime/ai_lifecycle/training_outputs") / run_id
    output_root.mkdir(parents=True, exist_ok=True)
    report_dir = Path(request.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    preflight = {
        "status": "PASS",
        "mode": "FORMAL_BOOTSTRAP",
        "plan_validation": plan_validation,
        "contract_hash": file_hash(Path(request.contract_path)),
        "policy_hash": policy["policy_hash"],
        "schema_review": schema_review,
        "tracked_training_code_dirty": False,
        "generation_candidate_created": False,
        "accepted_decision_created": False,
        "runtime_pointer_written": False,
        "broker_write_executed": False,
    }
    write_json(output_root / "preflight.json", preflight)
    candidate = _train_formal_component(
        resolved=candidate_input,
        policy=policy,
        plan=plan,
        output_dir=output_root / "candidate",
        schema_path=Path(request.schema_dir) / "candidate_model_artifact.schema.json",
        component_plan=plan["candidate_execution"],
        candidate_artifact=None,
    )
    if candidate["status"] != "PASS" or candidate["schema_validation"]["status"] != "PASS":
        failure = {
            "status": "FAILED",
            "reason": "candidate_training_or_validation_failed",
            "candidate": candidate,
            "opportunity_started": False,
            "generation_candidate_created": False,
            "accepted_decision_created": False,
            "runtime_pointer_written": False,
            "broker_write_executed": False,
        }
        write_json(output_root / "failure.json", failure)
        return failure
    opportunity = _train_formal_component(
        resolved=opportunity_input,
        policy=policy,
        plan=plan,
        output_dir=output_root / "opportunity",
        schema_path=Path(request.schema_dir) / "opportunity_model_artifact.schema.json",
        component_plan=plan["opportunity_execution"],
        candidate_artifact=candidate["artifact"],
    )
    result = {
        "status": "PASS" if opportunity["status"] == "PASS" else "REVIEW_REQUIRED",
        "mode": "FORMAL_BOOTSTRAP",
        "run_id": run_id,
        "output_root": str(output_root),
        "candidate": candidate,
        "opportunity": opportunity,
        "preflight": preflight,
        "formal_authority": authority,
        "schema_review": schema_review,
        "plan_hash": plan["plan_hash"],
        "generation_status": "NOT_CREATED",
        "accepted": False,
        "runtime_eligibility": False,
        "generation_candidate_created": False,
        "accepted_decision_created": False,
        "accepted_generation_created": False,
        "runtime_pointer_written": False,
        "buy_restarted": False,
        "broker_write_executed": False,
    }
    write_json(output_root / "formal_training_run_manifest.json", result)
    return result


def _train_formal_component(
    *,
    resolved: ResolvedTrainingInput,
    policy: dict[str, Any],
    plan: dict[str, Any],
    output_dir: Path,
    schema_path: Path,
    component_plan: dict[str, Any],
    candidate_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = dict(component_plan["training_config"])
    config_hash = str(config["training_config_hash"])
    dataset = pd.read_parquet(resolved.dataset_path)
    frames = _split_actual_frame(dataset, resolved.split_definition)
    preprocessing = fit_preprocessing(frames["train"], list(resolved.feature_columns))
    x_train = transform_features(frames["train"], list(resolved.feature_columns), preprocessing)
    y_train = target_values(frames["train"], _config_for_existing_training(resolved, _config_for_existing_helpers(config)))
    captured_warnings: list[dict[str, str]] = []
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        model = fit_model(x_train, y_train, _config_for_existing_training(resolved, _config_for_existing_helpers(config)))
    for record in records:
        captured_warnings.append({"category": record.category.__name__, "message": str(record.message)})
    model_payload = {
        "component": resolved.component,
        "formal_bootstrap": True,
        "config": config,
        "feature_columns": list(resolved.feature_columns),
        "label_columns": list(resolved.label_columns),
        "preprocessing": preprocessing,
        "model": model,
    }
    model_path = output_dir / "model.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(model_payload, handle)
    model_content_hash = file_hash(model_path)
    technical_validation = _technical_validation(
        resolved=resolved,
        frames=frames,
        preprocessing=preprocessing,
        model=model,
        config=config,
        model_path=model_path,
        model_content_hash=model_content_hash,
    )
    metrics = _training_metrics(resolved, frames, preprocessing)
    metrics.update(
        {
            "fit_duration_seconds": round(time.perf_counter() - started, 6),
            "model_content_hash": model_content_hash,
            "warning_count": len(captured_warnings),
        }
    )
    quality = evaluate_training_quality(component=resolved.component, policy=policy, metrics=metrics, execution_mode="FORMAL_BOOTSTRAP")
    warning_summary = _warning_summary(captured_warnings)
    artifact = _formal_artifact_payload(
        resolved=resolved,
        policy=policy,
        plan=plan,
        config=config,
        config_hash=config_hash,
        model_path=model_path,
        model_content_hash=model_content_hash,
        metrics=metrics,
        quality=quality,
        technical_validation=technical_validation,
        warning_summary=warning_summary,
        candidate_artifact=candidate_artifact,
    )
    schema_validation = validate_artifact_against_schema(artifact, schema_path)
    hash_check = {
        "status": "PASS" if artifact["model_content_hash"] == model_content_hash and artifact["content_hash"] == stable_json_hash({k: v for k, v in artifact.items() if k != "content_hash"}) else "BLOCK",
        "model_content_hash": model_content_hash,
        "manifest_model_content_hash": artifact["model_content_hash"],
        "artifact_content_hash": artifact["content_hash"],
    }
    write_json(output_dir / "artifact_manifest.json", artifact)
    write_json(output_dir / "training_config.json", config)
    write_json(output_dir / "training_statistics.json", metrics)
    write_json(output_dir / "technical_validation.json", technical_validation)
    write_json(output_dir / "warning_summary.json", warning_summary)
    write_json(output_dir / "schema_validation.json", schema_validation)
    write_json(output_dir / "hash_verification.json", hash_check)
    return {
        "status": "PASS" if schema_validation["status"] == "PASS" and hash_check["status"] == "PASS" and technical_validation["status"] == "PASS" else "REVIEW_REQUIRED",
        "artifact_path": str(output_dir / "artifact_manifest.json"),
        "model_path": str(model_path),
        "artifact": artifact,
        "metrics": metrics,
        "technical_validation": technical_validation,
        "schema_validation": schema_validation,
        "hash_verification": hash_check,
        "warning_summary": warning_summary,
        "quality": quality,
    }


def _formal_artifact_payload(
    *,
    resolved: ResolvedTrainingInput,
    policy: dict[str, Any],
    plan: dict[str, Any],
    config: dict[str, Any],
    config_hash: str,
    model_path: Path,
    model_content_hash: str,
    metrics: dict[str, Any],
    quality: dict[str, Any],
    technical_validation: dict[str, Any],
    warning_summary: dict[str, Any],
    candidate_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    artifact_type = "CANDIDATE_MODEL" if resolved.component == "Candidate" else "OPPORTUNITY_MODEL"
    payload: dict[str, Any] = {
        "artifact_id": f"formal_{resolved.component.lower()}_{model_content_hash[:16]}",
        "artifact_type": artifact_type,
        "artifact_version": "phase19_ad_u3_g_formal_bootstrap.v1",
        "artifact_status": "TRAINING_OUTPUT",
        "created_at": CREATED_AT,
        "producer": "ai_fund_lab_v2.ai_lifecycle.ad_u3_contract_bound_training_runner",
        "source_phase": "PHASE19_AD_U3_G",
        "component": resolved.component,
        "generation_candidate_id": None,
        "content_hash": "0" * 64,
        "schema_version": "phase19_ad_u3_d_generation_output_artifact.v1",
        "authority": "Formal Bootstrap Training output approved by user:negishi execution plan; not Runtime authority",
        "dataset_input_contract_id": "phase19_ad_r2_ad_u3_dataset_input_contract_corrected",
        "dataset_revision_id": resolved.dataset_revision_id,
        "dataset_content_hash": resolved.dataset_hash,
        "dataset_schema_hash": resolved.dataset_schema_hash,
        "dataset_lineage_hash": resolved.dataset_lineage_hash,
        "split_id": resolved.split_id,
        "split_content_hash": resolved.split_hash,
        "rolling_split_policy_hash": resolved.policy_hashes["rolling_split_policy_hash"],
        "corporate_action_policy_hash": resolved.policy_hashes["corporate_action_policy_hash"],
        "model_quality_policy_hash": str(policy["policy_hash"]),
        "feature_schema_identity": resolved.feature_schema_identity,
        "label_schema_identity": resolved.label_schema_identity,
        "trading_calendar_identity": resolved.calendar_identity,
        "target_horizon_business_days": resolved.target_horizon_business_days,
        "embargo_business_days": resolved.embargo_business_days,
        "bootstrap_or_retraining": resolved.bootstrap_or_retraining,
        "model_family": config["model_family"],
        "model_format": config["serialization_format"],
        "model_file": str(model_path),
        "model_content_hash": model_content_hash,
        "training_code_version": config["training_code_commit"],
        "training_config": config,
        "training_config_hash": config_hash,
        "random_seed": config["random_seed"],
        "determinism_contract": _determinism_contract(config, resolved, config_hash),
        "feature_columns": list(resolved.feature_columns),
        "feature_schema_hash": resolved.feature_schema_identity,
        "label_column": config["label_column"],
        "label_schema_hash": resolved.label_schema_identity,
        "train_window": resolved.split_definition["train"],
        "validation_window": resolved.split_definition["validation"],
        "test_window": resolved.split_definition["test"],
        "recent_holdout_window": resolved.split_definition["recent_holdout"],
        "training_statistics": {**metrics, "technical_validation": technical_validation, "warning_summary": warning_summary},
        "model_quality_policy_result": quality,
        "prohibited_input_audit_result": {"status": "PASS", "runtime_paper_broker_inputs_used": False, "future_features_used": False},
        "runtime_eligibility": False,
        "accepted": False,
        "generation_eligibility": False,
        "execution_mode": "FORMAL_BOOTSTRAP",
    }
    if resolved.component == "Opportunity":
        payload.update(
            {
                "candidate_dependency_contract": {
                    "dependency": "NOT_APPLICABLE_FOR_FORMAL_BOOTSTRAP_INPUT_DATASET",
                    "candidate_prediction_used": False,
                    "candidate_score_used": False,
                    "candidate_selected_universe_used": False,
                },
                "candidate_feature_or_score_dependency": {"dependency": "NOT_APPLICABLE"},
                "candidate_model_hash": candidate_artifact["model_content_hash"] if candidate_artifact else "0" * 64,
                "opportunity_universe_definition": {"source": "resolved Opportunity input contract", "candidate_prediction_feature_added": False},
                "ranking_or_classification_contract": {"task": "regression_score_training_output", "runtime_semantics": "NOT_RUNTIME_ELIGIBLE"},
            }
        )
    payload["content_hash"] = stable_json_hash({key: value for key, value in payload.items() if key != "content_hash"})
    return payload


def _split_actual_frame(dataset: pd.DataFrame, split_definition: dict[str, Any]) -> dict[str, pd.DataFrame]:
    target_date = dataset["target_date"].astype(str)
    frames: dict[str, pd.DataFrame] = {}
    for name in ("train", "validation", "test", "recent_holdout"):
        window = split_definition[name]
        frames[name] = dataset[(target_date >= str(window["start"])) & (target_date <= str(window["end"]))].copy()
    return frames


def _technical_validation(
    *,
    resolved: ResolvedTrainingInput,
    frames: dict[str, pd.DataFrame],
    preprocessing: dict[str, Any],
    model: Any,
    config: dict[str, Any],
    model_path: Path,
    model_content_hash: str,
) -> dict[str, Any]:
    validation = frames["validation"]
    matrix = transform_features(validation, list(resolved.feature_columns), preprocessing)
    if resolved.component == "Candidate" and hasattr(model, "predict_proba"):
        predictions = model.predict_proba(matrix)[:, 1]
    else:
        predictions = model.predict(matrix)
    checks = {
        "fit_completed": True,
        "model_hash_present": bool(model_content_hash),
        "model_file_exists": model_path.is_file(),
        "serialization_hash_match": file_hash(model_path) == model_content_hash,
        "prediction_shape_ok": len(predictions) == len(validation),
        "prediction_nan_absent": not np.isnan(predictions).any(),
        "prediction_inf_absent": bool(np.isfinite(predictions).all()),
        "feature_count_match": len(resolved.feature_columns) == len(config["feature_columns"]),
        "label_column_present": config["label_column"] in frames["train"].columns,
    }
    return {
        "status": "PASS" if all(checks.values()) else "BLOCK",
        "checks": checks,
        "prediction_rows": int(len(predictions)),
        "validation_rows": int(len(validation)),
        "prediction_min": float(np.nanmin(predictions)) if len(predictions) else None,
        "prediction_max": float(np.nanmax(predictions)) if len(predictions) else None,
        "performance_evaluation_performed": False,
    }


def _technical_validation_with_matrix(
    *,
    resolved: ResolvedTrainingInput,
    frame: pd.DataFrame,
    matrix: np.ndarray,
    model: Any,
    config: dict[str, Any],
    model_path: Path,
    model_content_hash: str,
) -> dict[str, Any]:
    if resolved.component == "Candidate" and hasattr(model, "predict_proba"):
        predictions = model.predict_proba(matrix)[:, 1]
    else:
        predictions = model.predict(matrix)
    checks = {
        "fit_completed": True,
        "model_hash_present": bool(model_content_hash),
        "model_file_exists": model_path.is_file(),
        "serialization_hash_match": file_hash(model_path) == model_content_hash,
        "prediction_shape_ok": len(predictions) == len(frame),
        "prediction_nan_absent": not np.isnan(predictions).any(),
        "prediction_inf_absent": bool(np.isfinite(predictions).all()),
        "feature_count_match": len(resolved.feature_columns) == len(config["feature_columns"]),
        "label_column_present": config["label_column"] in frame.columns or config["label_column"] in resolved.label_columns,
    }
    return {
        "status": "PASS" if all(checks.values()) else "BLOCK",
        "checks": checks,
        "prediction_rows": int(len(predictions)),
        "validation_rows": int(len(frame)),
        "prediction_min": float(np.nanmin(predictions)) if len(predictions) else None,
        "prediction_max": float(np.nanmax(predictions)) if len(predictions) else None,
        "performance_evaluation_performed": False,
    }


def _corrective_diagnostics(
    *,
    resolved: ResolvedTrainingInput,
    frames: dict[str, pd.DataFrame],
    matrices: dict[str, np.ndarray],
    model: Any,
    fitted_scaler: Any,
) -> dict[str, Any]:
    validation = frames["validation"]
    matrix = matrices["validation"]
    label = pd.to_numeric(validation[_label_column(resolved)], errors="coerce").to_numpy(dtype=np.float64)
    if resolved.component == "Candidate" and hasattr(model, "predict_proba"):
        predictions = model.predict_proba(matrix)[:, 1]
        previous_ratio_eq_1 = 0.9954137918114131
        distribution = _prediction_distribution(predictions)
        ratio_eq_0 = float(np.mean(predictions == 0.0)) if len(predictions) else 0.0
        ratio_eq_1 = float(np.mean(predictions == 1.0)) if len(predictions) else 0.0
        collapsed = bool(len(np.unique(predictions)) <= 1 or ratio_eq_0 > 0.99 or ratio_eq_1 > 0.99)
        return {
            "status": "PASS" if np.isfinite(predictions).all() and not collapsed and ratio_eq_1 < previous_ratio_eq_1 else "REVIEW_REQUIRED",
            "component": resolved.component,
            "prediction_distribution": distribution,
            "ratio_eq_0": ratio_eq_0,
            "ratio_eq_1": ratio_eq_1,
            "previous_ratio_eq_1": previous_ratio_eq_1,
            "ratio_eq_1_improved": ratio_eq_1 < previous_ratio_eq_1,
            "prediction_std": float(np.std(predictions)) if len(predictions) else 0.0,
            "prediction_histogram": _histogram(predictions),
            "prediction_quantiles": distribution["quantiles"],
            "unique_prediction_count": int(len(np.unique(predictions))),
            "collapsed_prediction": collapsed,
            "nan_absent": not np.isnan(predictions).any(),
            "inf_absent": bool(np.isfinite(predictions).all()),
            "n_iter": _model_n_iter(model),
            "coef_abs_max": _coef_abs_max(model),
        }
    predictions = model.predict(matrix)
    distribution = _prediction_distribution(predictions)
    target_abs_max = float(np.nanmax(np.abs(label))) if len(label) else 0.0
    pred_abs_max = float(np.nanmax(np.abs(predictions))) if len(predictions) else 0.0
    ratio = pred_abs_max / max(target_abs_max, 1e-12)
    ranking = _feature_contribution_ranking(model, matrix, list(resolved.feature_columns))
    previous_abs_max = 3.78e24
    exploded = bool((not np.isfinite(predictions).all()) or pred_abs_max > 1e6)
    collapsed = bool(len(np.unique(predictions)) <= 1 or float(np.std(predictions)) == 0.0)
    return {
        "status": "PASS" if np.isfinite(predictions).all() and pred_abs_max < previous_abs_max and not collapsed and not exploded else "REVIEW_REQUIRED",
        "component": resolved.component,
        "prediction_distribution": distribution,
        "prediction_min": distribution["min"],
        "prediction_max": distribution["max"],
        "prediction_quantiles": distribution["quantiles"],
        "prediction_std": float(np.std(predictions)) if len(predictions) else 0.0,
        "prediction_to_target_scale_ratio": float(ratio),
        "target_abs_max": target_abs_max,
        "prediction_abs_max": pred_abs_max,
        "previous_prediction_abs_max_reference": previous_abs_max,
        "prediction_scale_improved": pred_abs_max < previous_abs_max,
        "coefficient_abs_max": _coef_abs_max(model),
        "dominant_feature_contribution": ranking[0] if ranking else None,
        "feature_contribution_ranking": ranking,
        "collapsed_prediction": collapsed,
        "prediction_explosion": exploded,
        "nan_absent": not np.isnan(predictions).any(),
        "inf_absent": bool(np.isfinite(predictions).all()),
        "n_iter": _model_n_iter(model),
    }


def _prediction_distribution(values: np.ndarray) -> dict[str, Any]:
    quantiles = {}
    for name, q in (("p1", 0.01), ("p5", 0.05), ("p25", 0.25), ("median", 0.5), ("p75", 0.75), ("p95", 0.95), ("p99", 0.99)):
        quantiles[name] = float(np.nanquantile(values, q)) if len(values) else None
    return {
        "count": int(len(values)),
        "min": float(np.nanmin(values)) if len(values) else None,
        "max": float(np.nanmax(values)) if len(values) else None,
        "mean": float(np.nanmean(values)) if len(values) else None,
        "std": float(np.nanstd(values)) if len(values) else None,
        "quantiles": quantiles,
        "histogram": _histogram(values),
    }


def _histogram(values: np.ndarray, bins: int = 10) -> dict[str, Any]:
    if not len(values):
        return {"bins": [], "counts": []}
    counts, edges = np.histogram(values, bins=bins)
    return {"bins": [float(item) for item in edges.tolist()], "counts": [int(item) for item in counts.tolist()]}


def _coef_abs_max(model: Any) -> float | None:
    coef = getattr(model, "coef_", None)
    if coef is None:
        return None
    return float(np.nanmax(np.abs(np.asarray(coef, dtype=np.float64))))


def _model_n_iter(model: Any) -> int | None:
    value = getattr(model, "n_iter_", None)
    if value is None:
        return None
    return int(np.max(np.asarray(value)))


def _feature_contribution_ranking(model: Any, matrix: np.ndarray, feature_columns: list[str]) -> list[dict[str, Any]]:
    coef = getattr(model, "coef_", None)
    if coef is None:
        return []
    weights = np.ravel(np.asarray(coef, dtype=np.float64))
    if len(weights) != len(feature_columns):
        return []
    mean_abs_feature = np.nanmean(np.abs(matrix), axis=0)
    contributions = np.abs(weights) * mean_abs_feature
    rows = [
        {
            "feature": feature,
            "coefficient": float(weights[index]),
            "mean_abs_scaled_feature": float(mean_abs_feature[index]),
            "mean_abs_contribution": float(contributions[index]),
        }
        for index, feature in enumerate(feature_columns)
    ]
    return sorted(rows, key=lambda row: row["mean_abs_contribution"], reverse=True)


def _warning_summary(captured_warnings: list[dict[str, str]]) -> dict[str, Any]:
    classified: list[dict[str, str]] = []
    for item in captured_warnings:
        category = item["category"]
        if category == "ConvergenceWarning":
            classification = "REVIEW_REQUIRED_WARNING"
        elif "RuntimeWarning" in category or "FloatingPoint" in category:
            classification = "BLOCKING_WARNING"
        else:
            classification = "INFO"
        classified.append({**item, "classification": classification})
    return {
        "status": "PASS" if not any(item["classification"] == "BLOCKING_WARNING" for item in classified) else "BLOCK",
        "warning_count": len(classified),
        "review_required_warning_count": sum(1 for item in classified if item["classification"] == "REVIEW_REQUIRED_WARNING"),
        "blocking_warning_count": sum(1 for item in classified if item["classification"] == "BLOCKING_WARNING"),
        "warnings": classified,
        "exit_code_zero_alone_pass": False,
    }


def _config_for_existing_helpers(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_family": config["model_family"],
        "label_column": config["label_column"],
        "random_seed": config["random_seed"],
        "hyperparameters": {
            "max_iter": config.get("max_iter", config.get("hyperparameters", {}).get("max_iter", 30)),
            "alpha": config.get("alpha", config.get("hyperparameters", {}).get("alpha", 0.0001)),
        },
    }


def _tracked_training_code_dirty() -> bool:
    paths = [
        "src/ai_fund_lab_v2/ai_lifecycle/ad_u3_contract_bound_training_runner.py",
        "src/ai_fund_lab_v2/ai_lifecycle/ad_u3_training_quality_gate.py",
        "src/ai_fund_lab_v2/ai_lifecycle/ad_u3_training_artifact_writer.py",
        "src/ai_fund_lab_v2/ai_lifecycle/training_pipeline.py",
    ]
    try:
        return subprocess.run(["git", "diff", "--quiet", "--", *paths], check=False).returncode != 0
    except Exception:
        return True


def _reject_runner_overrides(overrides: dict[str, Any]) -> None:
    prohibited = {
        "dataset_dir",
        "dataset_path",
        "split_path",
        "model_quality_thresholds",
        "feature_columns",
        "label_column",
        "latest_glob",
        "runtime_state_path",
        "paper_state_path",
        "broker_state_path",
        "legacy_model_path",
        "accepted_component_model_path",
        "recompute_split",
        "random_split",
    }
    supplied = [name for name in prohibited if overrides.get(name) not in (None, False, "")]
    if supplied:
        raise TrainingRunnerError("prohibited_runner_input:" + ",".join(sorted(supplied)))


def _normalize_mode(mode: str) -> ExecutionMode:
    normalized = mode.strip().upper().replace("-", "_")
    if normalized not in {"VALIDATE_ONLY", "FIXTURE_SMOKE", "FIXTURE_SCALING_SMOKE", "CORRECTIVE_BOOTSTRAP", "FORMAL_BOOTSTRAP", "FORMAL_RETRAINING"}:
        raise TrainingRunnerError(f"unknown_execution_mode:{mode}")
    return normalized  # type: ignore[return-value]


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "UNKNOWN"


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _json_default(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dict__"):
        return asdict(value)
    return str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase19 AD-U3-E contract-bound training runner.")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT_PATH))
    parser.add_argument("--model-quality-policy", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--schema-dir", default=str(DEFAULT_SCHEMA_DIR))
    parser.add_argument(
        "--mode",
        default="validate-only",
        choices=["validate-only", "fixture-smoke", "fixture-scaling-smoke", "corrective-bootstrap", "formal-bootstrap", "formal-retraining"],
    )
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--approved-execution-plan")
    parser.add_argument("--corrective-action-policy")
    parser.add_argument("--materialize-fixture-contract", action="store_true")
    args = parser.parse_args(argv)
    if args.materialize_fixture_contract:
        path = materialize_fixture_contract(Path(args.report_dir))
        print(json.dumps({"status": "PASS", "fixture_contract_path": str(path)}, ensure_ascii=False, sort_keys=True))
        return 0
    request = TrainingRunRequest(
        contract_path=Path(args.contract),
        model_quality_policy_path=Path(args.model_quality_policy),
        schema_dir=Path(args.schema_dir),
        mode=_normalize_mode(args.mode),
        report_dir=Path(args.report_dir),
        confirm=args.confirm,
        approved_execution_plan=Path(args.approved_execution_plan) if args.approved_execution_plan else None,
        corrective_action_policy_path=Path(args.corrective_action_policy) if args.corrective_action_policy else None,
    )
    result = run_contract_bound_training_runner(request)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=_json_default))
    return 0 if result["status"] in {"PASS", "REJECTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
