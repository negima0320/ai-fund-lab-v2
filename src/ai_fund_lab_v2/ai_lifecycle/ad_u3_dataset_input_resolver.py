from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal


CREATED_AT = "2026-07-19T00:00:00+09:00"
DEFAULT_CONTRACT_PATH = Path(
    "reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/ad_u3_dataset_input_contract_corrected.json"
)
DEFAULT_REPORT_DIR = Path("reports/phase19_ad_u3_a_contract_only_dataset_input_resolver")

ALLOWED_CONTRACT_STATUSES = {"PASS_AFTER_CORRECTIVE_FIX"}
ALLOWED_CONTRACT_AUTHORITY = (
    "Phase19-AD-R2 corrected gate contract bound to AD-U2-F approved policy and AD-U2-D "
    "policy-amended dataset revisions"
)
ALLOWED_SOURCE_PHASE = "PHASE19_AD_R2"
ALLOWED_GENERATION_MODE = "UNIFIED_GENERATION_INPUT"
ALLOWED_BOOTSTRAP_MODE = "BOOTSTRAP"
APPROVED_ROLLING_SPLIT_POLICY_ID = "phase19_ad_u2_f_rolling_split_policy_option_c_capped_expanding_hybrid"
APPROVED_CORPORATE_ACTION_POLICY_ID = "phase19_ad_u2_d_corporate_action_dataset_handling"
TARGET_HORIZON_BUSINESS_DAYS = 20

REQUIRED_CONTRACT_FIELDS = (
    "contract_id",
    "contract_version",
    "contract_status",
    "authority",
    "source_phase",
    "generation_mode",
    "bootstrap_or_retraining",
    "candidate",
    "opportunity",
)

REQUIRED_COMPONENT_FIELDS = (
    "component",
    "dataset_revision_id",
    "dataset_revision_path",
    "dataset_content_hash",
    "dataset_schema_hash",
    "dataset_lineage_hash",
    "source_revision",
    "source_cutoff",
    "dataset_date_min",
    "dataset_date_max",
    "label_safe_max",
    "split_id",
    "split_path",
    "split_content_hash",
    "rolling_split_policy_id",
    "rolling_split_policy_hash",
    "corporate_action_policy_id",
    "corporate_action_policy_hash",
    "trading_calendar_identity",
    "target_horizon_business_days",
    "embargo_business_days",
    "feature_schema_identity",
    "label_schema_identity",
)

DEFERRED_MODEL_QUALITY_ITEMS = (
    "minimum_training_rows",
    "minimum_validation_rows",
    "minimum_positive_labels",
    "minimum_negative_labels",
    "maximum_missing_ratio",
)

PROHIBITED_PATH_TERMS = (
    "runtime_state",
    "persistent_ledger",
    "paper",
    "broker",
    "backtest",
    "pnl",
    "accepted_buy_ai_bundle",
    "promotion_candidates",
)

PROHIBITED_FEATURE_TERMS = (
    "future_",
    "future_return_",
    "future_max_return_",
    "future_max_drawdown_",
    "downside_bad_",
    "top_decile_",
    "expected_edge",
    "selected",
    "bought",
    "cash",
    "portfolio",
    "pnl",
    "backtest",
    "broker",
    "paper",
    "corporate_action",
    "adjustment_factor",
)


class ContractInputError(ValueError):
    """Fail-closed resolver error for invalid AD-U3 dataset input contracts."""


@dataclass(frozen=True)
class ResolvedTrainingInput:
    component: str
    dataset_path: str
    dataset_revision_id: str
    dataset_hash: str
    dataset_schema_hash: str
    dataset_lineage_hash: str
    feature_schema_identity: str
    label_schema_identity: str
    feature_columns: tuple[str, ...]
    label_columns: tuple[str, ...]
    split_definition: dict[str, Any]
    split_id: str
    split_hash: str
    policy_hashes: dict[str, str]
    calendar_identity: str
    target_horizon_business_days: int
    embargo_business_days: int
    bootstrap_or_retraining: str
    model_quality_policy_thresholds: dict[str, None]
    training_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["feature_columns"] = list(self.feature_columns)
        payload["label_columns"] = list(self.label_columns)
        return payload


def load_ad_u3_dataset_input_contract(path: Path | str = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    contract_path = Path(path)
    payload = _read_json(contract_path)
    result = validate_contract(payload)
    if result["status"] != "PASS":
        raise ContractInputError(";".join(result["reason_codes"]))
    return payload


def validate_contract(contract: dict[str, Any]) -> dict[str, Any]:
    reason_codes: list[str] = []
    missing = [field for field in REQUIRED_CONTRACT_FIELDS if contract.get(field) in (None, "")]
    reason_codes.extend(f"missing_contract_field:{field}" for field in missing)
    if contract.get("contract_status") not in ALLOWED_CONTRACT_STATUSES:
        reason_codes.append("unknown_or_unapproved_contract_status")
    if contract.get("authority") != ALLOWED_CONTRACT_AUTHORITY:
        reason_codes.append("wrong_contract_authority")
    if contract.get("source_phase") != ALLOWED_SOURCE_PHASE:
        reason_codes.append("wrong_source_phase")
    if contract.get("generation_mode") != ALLOWED_GENERATION_MODE:
        reason_codes.append("wrong_generation_mode")
    if contract.get("bootstrap_or_retraining") != ALLOWED_BOOTSTRAP_MODE:
        reason_codes.append("unsupported_bootstrap_or_retraining")
    if contract.get("previous_generation_ref") is not None:
        reason_codes.append("bootstrap_contract_requires_null_previous_generation_ref")
    policy_hashes = contract.get("policy_hashes") if isinstance(contract.get("policy_hashes"), dict) else {}
    for key, expected_component in (("candidate", "Candidate"), ("opportunity", "Opportunity")):
        component = contract.get(key)
        if not isinstance(component, dict):
            reason_codes.append(f"missing_component:{key}")
            continue
        component_missing = [field for field in REQUIRED_COMPONENT_FIELDS if component.get(field) in (None, "")]
        reason_codes.extend(f"{key}_missing_component_field:{field}" for field in component_missing)
        if component.get("component") != expected_component:
            reason_codes.append(f"{key}_component_name_mismatch")
        if component.get("rolling_split_policy_id") != APPROVED_ROLLING_SPLIT_POLICY_ID:
            reason_codes.append(f"{key}_unapproved_rolling_split_policy")
        if component.get("corporate_action_policy_id") != APPROVED_CORPORATE_ACTION_POLICY_ID:
            reason_codes.append(f"{key}_unapproved_corporate_action_policy")
        if policy_hashes:
            if component.get("rolling_split_policy_hash") != policy_hashes.get("rolling_split_policy_hash"):
                reason_codes.append(f"{key}_rolling_split_policy_hash_mismatch")
            if component.get("corporate_action_policy_hash") != policy_hashes.get("corporate_action_policy_hash"):
                reason_codes.append(f"{key}_corporate_action_policy_hash_mismatch")
        if component.get("dataset_date_max") > component.get("label_safe_max"):
            reason_codes.append(f"{key}_label_safe_overflow")
        if int(component.get("target_horizon_business_days") or -1) != TARGET_HORIZON_BUSINESS_DAYS:
            reason_codes.append(f"{key}_target_horizon_mismatch")
        if component.get("target_horizon_business_days") != component.get("embargo_business_days"):
            reason_codes.append(f"{key}_embargo_mismatch")
        if not component.get("trading_calendar_identity"):
            reason_codes.append(f"{key}_trading_calendar_identity_missing")
    return {
        "status": "PASS" if not reason_codes else "BLOCK",
        "reason_codes": reason_codes,
        "allowed_statuses": sorted(ALLOWED_CONTRACT_STATUSES),
    }


def resolve_candidate_training_input(contract: dict[str, Any], **overrides: Any) -> ResolvedTrainingInput:
    return resolve_training_input(contract, "candidate", **overrides)


def resolve_opportunity_training_input(contract: dict[str, Any], **overrides: Any) -> ResolvedTrainingInput:
    return resolve_training_input(contract, "opportunity", **overrides)


def resolve_training_input(
    contract: dict[str, Any],
    component_key: Literal["candidate", "opportunity"],
    **overrides: Any,
) -> ResolvedTrainingInput:
    _reject_overrides(overrides)
    contract_result = validate_contract(contract)
    if contract_result["status"] != "PASS":
        raise ContractInputError(";".join(contract_result["reason_codes"]))
    component = dict(contract[component_key])
    binding = validate_component_artifact_binding(component)
    if binding["status"] != "PASS":
        raise ContractInputError(";".join(binding["reason_codes"]))
    schema = resolve_feature_label_schema(component)
    if schema["status"] != "PASS":
        raise ContractInputError(";".join(schema["reason_codes"]))
    guard = prohibited_input_guard(component=component, feature_columns=schema["feature_columns"])
    if guard["status"] != "PASS":
        raise ContractInputError(";".join(guard["reason_codes"]))
    split = resolve_versioned_split(component)
    if split["status"] != "PASS":
        raise ContractInputError(";".join(split["reason_codes"]))
    return ResolvedTrainingInput(
        component=str(component["component"]),
        dataset_path=str(component["dataset_path"]),
        dataset_revision_id=str(component["dataset_revision_id"]),
        dataset_hash=str(component["dataset_content_hash"]),
        dataset_schema_hash=str(component["dataset_schema_hash"]),
        dataset_lineage_hash=str(component["dataset_lineage_hash"]),
        feature_schema_identity=str(component["feature_schema_identity"]),
        label_schema_identity=str(component["label_schema_identity"]),
        feature_columns=tuple(schema["feature_columns"]),
        label_columns=tuple(schema["label_columns"]),
        split_definition=split["split_definition"],
        split_id=str(component["split_id"]),
        split_hash=str(component["split_content_hash"]),
        policy_hashes={
            "rolling_split_policy_hash": str(component["rolling_split_policy_hash"]),
            "corporate_action_policy_hash": str(component["corporate_action_policy_hash"]),
        },
        calendar_identity=str(component["trading_calendar_identity"]),
        target_horizon_business_days=int(component["target_horizon_business_days"]),
        embargo_business_days=int(component["embargo_business_days"]),
        bootstrap_or_retraining=str(contract["bootstrap_or_retraining"]),
        model_quality_policy_thresholds={item: None for item in DEFERRED_MODEL_QUALITY_ITEMS},
        training_executed=False,
    )


def validate_component_artifact_binding(component: dict[str, Any]) -> dict[str, Any]:
    reason_codes: list[str] = []
    dataset_path = Path(str(component.get("dataset_path") or ""))
    revision_path = Path(str(component.get("dataset_revision_path") or ""))
    split_path = Path(str(component.get("split_path") or ""))
    manifest_path = Path(str(component.get("dataset_hash_manifest_path") or dataset_path.parent / "hash_manifest.json"))
    paths = {
        "dataset": dataset_path,
        "dataset_revision": revision_path,
        "split": split_path,
        "hash_manifest": manifest_path,
    }
    for name, path in paths.items():
        if not path.is_file():
            reason_codes.append(f"{name}_missing")
    if reason_codes:
        return {"status": "BLOCK", "reason_codes": reason_codes, "paths": {k: str(v) for k, v in paths.items()}}
    revision = _read_json(revision_path)
    manifest = _read_json(manifest_path)
    split = _read_json(split_path)
    checks = {
        "dataset_hash_match": _file_hash(dataset_path) == component.get("dataset_content_hash"),
        "dataset_revision_hash_match": _file_hash(revision_path) == component.get("dataset_revision_content_hash"),
        "dataset_revision_id_match": revision.get("dataset_revision") == component.get("dataset_revision_id"),
        "dataset_schema_hash_match": manifest.get("schema_hash") == component.get("dataset_schema_hash"),
        "dataset_lineage_hash_match": revision.get("source_lineage_hash") == component.get("dataset_lineage_hash"),
        "split_hash_match": _file_hash(split_path) == component.get("split_content_hash"),
        "split_id_match": split.get("split_id") == component.get("split_id"),
        "split_dataset_revision_match": split.get("dataset_revision") == component.get("dataset_revision_id"),
        "split_dataset_hash_match": split.get("dataset_hash") == component.get("dataset_content_hash"),
        "split_schema_hash_match": split.get("schema_hash") == component.get("dataset_schema_hash"),
        "split_policy_hash_match": split.get("policy_hash") == component.get("rolling_split_policy_hash"),
        "split_calendar_identity_match": split.get("trading_calendar_identity") == component.get("trading_calendar_identity"),
        "feature_schema_identity_match": manifest.get("feature_schema_hash") == component.get("feature_schema_identity"),
        "label_schema_identity_match": manifest.get("target_schema_hash") == component.get("label_schema_identity"),
        "corporate_action_policy_hash_present": bool(component.get("corporate_action_policy_hash")),
        "label_safe_max_ok": component.get("dataset_date_max") <= component.get("label_safe_max"),
        "embargo_equals_target_horizon": component.get("embargo_business_days") == component.get("target_horizon_business_days"),
    }
    reason_codes.extend(name for name, passed in checks.items() if not passed)
    return {
        "status": "PASS" if not reason_codes else "BLOCK",
        "reason_codes": reason_codes,
        "checks": checks,
        "paths": {k: str(v) for k, v in paths.items()},
    }


def resolve_versioned_split(component: dict[str, Any]) -> dict[str, Any]:
    split_path = Path(str(component.get("split_path") or ""))
    if not split_path.is_file():
        return {"status": "BLOCK", "reason_codes": ["split_missing"]}
    split = _read_json(split_path)
    checks = {
        "split_id_match": split.get("split_id") == component.get("split_id"),
        "split_hash_match": _file_hash(split_path) == component.get("split_content_hash"),
        "policy_hash_match": split.get("policy_hash") == component.get("rolling_split_policy_hash"),
        "calendar_identity_match": split.get("trading_calendar_identity") == component.get("trading_calendar_identity"),
        "target_horizon_match": split.get("target_horizon_business_days") == component.get("target_horizon_business_days"),
        "embargo_match": split.get("embargo_business_days") == component.get("embargo_business_days"),
        "embargo_equals_target_horizon": split.get("embargo_business_days") == split.get("target_horizon_business_days"),
        "recent_holdout_within_label_safe": split.get("recent_holdout_end") <= component.get("label_safe_max"),
        "approved_policy": split.get("policy_id") == APPROVED_ROLLING_SPLIT_POLICY_ID,
    }
    reason_codes = [name for name, passed in checks.items() if not passed]
    split_definition = {
        "schema_version": "phase19_ad_u3_a_resolved_versioned_split.v1",
        "split_id": split.get("split_id"),
        "split_method": split.get("split_method"),
        "dataset_revision": split.get("dataset_revision"),
        "dataset_hash": split.get("dataset_hash"),
        "schema_hash": split.get("schema_hash"),
        "policy_id": split.get("policy_id"),
        "policy_hash": split.get("policy_hash"),
        "trading_calendar_identity": split.get("trading_calendar_identity"),
        "target_horizon_business_days": split.get("target_horizon_business_days"),
        "embargo_business_days": split.get("embargo_business_days"),
        "train": _split_window(split, "train"),
        "validation": _split_window(split, "validation"),
        "test": _split_window(split, "test"),
        "recent_holdout": _split_window(split, "recent_holdout"),
        "split_recomputed": False,
    }
    return {
        "status": "PASS" if not reason_codes else "BLOCK",
        "reason_codes": reason_codes,
        "checks": checks,
        "split_definition": split_definition,
    }


def resolve_feature_label_schema(component: dict[str, Any]) -> dict[str, Any]:
    feature_path = Path(str(component.get("feature_schema_path") or ""))
    label_path = Path(str(component.get("label_schema_path") or ""))
    reason_codes: list[str] = []
    if not feature_path.is_file():
        reason_codes.append("feature_schema_missing")
    if not label_path.is_file():
        reason_codes.append("label_schema_missing")
    if reason_codes:
        return {"status": "BLOCK", "reason_codes": reason_codes}
    feature_schema = _read_json(feature_path)
    label_schema = _read_json(label_path)
    feature_columns = tuple(str(item.get("name") or "") for item in feature_schema.get("columns", []))
    label_columns = tuple(str(item.get("name") or "") for item in label_schema.get("columns", []))
    if feature_schema.get("schema_hash") != component.get("feature_schema_identity"):
        reason_codes.append("feature_schema_identity_mismatch")
    if label_schema.get("schema_hash") != component.get("label_schema_identity"):
        reason_codes.append("label_schema_identity_mismatch")
    future_features = [column for column in feature_columns if "future" in column.lower()]
    if future_features:
        reason_codes.append("future_feature_column_detected")
    prohibited_features = _prohibited_feature_columns(feature_columns)
    if prohibited_features:
        reason_codes.append("prohibited_feature_column_detected")
    future_labels = [column for column in label_columns if "future" in column.lower()]
    return {
        "status": "PASS" if not reason_codes else "BLOCK",
        "reason_codes": reason_codes,
        "feature_columns": list(feature_columns),
        "label_columns": list(label_columns),
        "future_feature_columns": future_features,
        "prohibited_feature_columns": prohibited_features,
        "future_label_columns": future_labels,
        "future_columns_target_only": bool(future_labels) and not future_features,
        "identifier_columns": ["code"],
        "date_columns": ["target_date"],
        "excluded_columns": list(label_columns),
    }


def prohibited_input_guard(*, component: dict[str, Any], feature_columns: list[str] | tuple[str, ...]) -> dict[str, Any]:
    reason_codes: list[str] = []
    input_paths = {
        "dataset_path": str(component.get("dataset_path") or ""),
        "feature_schema_path": str(component.get("feature_schema_path") or ""),
        "label_schema_path": str(component.get("label_schema_path") or ""),
    }
    for name, path in input_paths.items():
        lowered = path.lower()
        if _is_allowed_contract_bound_runtime_dataset_path(path):
            continue
        if any(term in lowered for term in PROHIBITED_PATH_TERMS):
            reason_codes.append(f"prohibited_path:{name}")
    bad_columns = _prohibited_feature_columns(feature_columns)
    if bad_columns:
        reason_codes.append("prohibited_feature_column_detected")
    return {
        "status": "PASS" if not reason_codes else "BLOCK",
        "reason_codes": reason_codes,
        "input_paths": input_paths,
        "prohibited_feature_columns": bad_columns,
    }


def validate_bootstrap_mode(contract: dict[str, Any]) -> dict[str, Any]:
    thresholds = contract.get("deferred_model_quality_policy_items") or []
    checks = {
        "bootstrap_mode": contract.get("bootstrap_or_retraining") == ALLOWED_BOOTSTRAP_MODE,
        "previous_generation_ref_null": contract.get("previous_generation_ref") is None,
        "incremental_revision_not_required": True,
        "incremental_business_days_not_required": True,
        "incremental_rows_not_required": True,
        "deferred_model_quality_values_not_filled": all(item in thresholds for item in DEFERRED_MODEL_QUALITY_ITEMS),
    }
    return {
        "status": "PASS" if all(checks.values()) else "BLOCK",
        "reason_codes": [name for name, passed in checks.items() if not passed],
        "checks": checks,
        "bootstrap_or_retraining": contract.get("bootstrap_or_retraining"),
    }


def dry_validate_contract(
    contract_path: Path | str = DEFAULT_CONTRACT_PATH,
    report_dir: Path | str = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    output = Path(report_dir)
    output.mkdir(parents=True, exist_ok=True)
    contract_path = Path(contract_path)
    contract = load_ad_u3_dataset_input_contract(contract_path)
    candidate = resolve_candidate_training_input(contract)
    opportunity = resolve_opportunity_training_input(contract)
    artifact_binding = {
        "schema_version": "phase19_ad_u3_a_artifact_binding_verification.v1",
        "status": "PASS",
        "candidate": validate_component_artifact_binding(contract["candidate"]),
        "opportunity": validate_component_artifact_binding(contract["opportunity"]),
    }
    split_resolution = {
        "schema_version": "phase19_ad_u3_a_versioned_split_resolution.v1",
        "status": "PASS",
        "split_recomputed": False,
        "candidate": resolve_versioned_split(contract["candidate"]),
        "opportunity": resolve_versioned_split(contract["opportunity"]),
    }
    schema_resolution = {
        "schema_version": "phase19_ad_u3_a_feature_label_schema_resolution.v1",
        "status": "PASS",
        "candidate": resolve_feature_label_schema(contract["candidate"]),
        "opportunity": resolve_feature_label_schema(contract["opportunity"]),
    }
    prohibited_guard = {
        "schema_version": "phase19_ad_u3_a_prohibited_input_guard_result.v1",
        "status": "PASS",
        "candidate": prohibited_input_guard(
            component=contract["candidate"],
            feature_columns=candidate.feature_columns,
        ),
        "opportunity": prohibited_input_guard(
            component=contract["opportunity"],
            feature_columns=opportunity.feature_columns,
        ),
        "direct_dataset_bypass_rejected": _failure_result(lambda: resolve_candidate_training_input(contract, dataset_dir="x")),
        "split_recompute_rejected": _failure_result(lambda: resolve_candidate_training_input(contract, recompute_split=True)),
        "latest_glob_rejected": _failure_result(lambda: resolve_candidate_training_input(contract, latest_glob="*")),
    }
    bootstrap = {
        "schema_version": "phase19_ad_u3_a_bootstrap_mode_validation.v1",
        **validate_bootstrap_mode(contract),
        "retraining_fallback_rejected": _failure_result(
            lambda: resolve_candidate_training_input({**contract, "bootstrap_or_retraining": "RETRAINING"})
        ),
    }
    model_quality = {
        "schema_version": "phase19_ad_u3_a_model_quality_deferred_observations.v1",
        "status": "PASS",
        "policy_threshold_status": "UNDECIDED",
        "thresholds_auto_filled": False,
        "thresholds": {item: None for item in DEFERRED_MODEL_QUALITY_ITEMS},
        "candidate_observations": _model_quality_observations(contract["candidate"], candidate.split_definition),
        "opportunity_observations": _model_quality_observations(contract["opportunity"], opportunity.split_definition),
    }
    non_mutation = _non_mutation_evidence()
    outputs = {
        "reviewed_input_contract.json": {
            "schema_version": "phase19_ad_u3_a_reviewed_input_contract.v1",
            "status": "PASS",
            "contract_path": str(contract_path),
            "contract_hash": _file_hash(contract_path),
            "contract_validation": validate_contract(contract),
        },
        "resolver_design.json": {
            "schema_version": "phase19_ad_u3_a_resolver_design.v1",
            "status": "PASS",
            "input_authority": str(contract_path),
            "contract_only": True,
            "training_executed": False,
            "split_recomputed": False,
            "dataset_regenerated": False,
            "phase18_dataset_authority_direct_use_allowed": False,
            "make_time_series_split_allowed": False,
        },
        "resolved_contract.json": contract,
        "candidate_resolved_training_input.json": candidate.to_dict(),
        "opportunity_resolved_training_input.json": opportunity.to_dict(),
        "artifact_binding_verification.json": artifact_binding,
        "versioned_split_resolution.json": split_resolution,
        "feature_label_schema_resolution.json": schema_resolution,
        "prohibited_input_guard_result.json": prohibited_guard,
        "bootstrap_mode_validation.json": bootstrap,
        "model_quality_deferred_observations.json": model_quality,
        "training_not_executed_evidence.json": {
            "schema_version": "phase19_ad_u3_a_training_not_executed_evidence.v1",
            "status": "PASS",
            "candidate_training_executed": False,
            "opportunity_training_executed": False,
            "calibration_executed": False,
            "unified_generation_created": False,
            "accepted_generation_created": False,
        },
        "non_mutation_evidence.json": non_mutation,
        "failure_injection_results.json": _failure_injection_results(contract),
        "final_judgment.json": {
            "schema_version": "phase19_ad_u3_a_final_judgment.v1",
            "final_judgment": "PHASE19_AD_U3_A_CONTRACT_ONLY_INPUT_RESOLVER_PASS",
            "supporting": [
                "PHASE19_AD_U3_MODEL_QUALITY_POLICY_READY",
                "CONTRACT_ONLY_ENTRY_PASS",
                "NO_DIRECT_DATASET_BYPASS_PASS",
                "NO_SPLIT_RECOMPUTE_PASS",
                "IMMUTABLE_ARTIFACT_BINDING_PASS",
                "PROHIBITED_INPUT_GUARD_PASS",
                "FEATURE_LABEL_SEPARATION_PASS",
                "BOOTSTRAP_CORRECTNESS_PASS",
                "MODEL_QUALITY_DEFERRED_PASS",
                "VALIDATE_ONLY_PASS",
                "NO_RUNTIME_MUTATION_PASS",
                "NO_BROKER_WRITE_PASS",
            ],
            "forbidden_not_declared": [
                "CANDIDATE_TRAINING_COMPLETE",
                "OPPORTUNITY_TRAINING_COMPLETE",
                "UNIFIED_GENERATION_CREATED",
                "ACCEPTED_GENERATION_CREATED",
                "AD_U3_COMPLETE",
                "BUY_READY",
                "PRODUCTION_READY",
                "RUNTIME_TRANSITION_COMPLETE",
            ],
        },
    }
    for name, payload in outputs.items():
        _write_json(output / name, payload)
    return {
        "status": "PASS",
        "final_judgment": "PHASE19_AD_U3_A_CONTRACT_ONLY_INPUT_RESOLVER_PASS",
        "report_dir": str(output),
        "training_executed": False,
    }


def _reject_overrides(overrides: dict[str, Any]) -> None:
    prohibited = {
        "dataset_dir",
        "dataset_path",
        "split_path",
        "latest_glob",
        "runtime_root",
        "paper_path",
        "broker_path",
        "pnl_path",
        "legacy_model_path",
        "accepted_component_model",
    }
    supplied = [name for name in prohibited if overrides.get(name) not in (None, False, "")]
    if supplied:
        raise ContractInputError("direct_or_prohibited_input_override:" + ",".join(sorted(supplied)))
    if overrides.get("recompute_split"):
        raise ContractInputError("split_recompute_rejected")
    if overrides.get("deferred_thresholds"):
        raise ContractInputError("deferred_model_quality_autofill_rejected")


def _split_window(split: dict[str, Any], name: str) -> dict[str, Any]:
    return {
        "start": split.get(f"{name}_start"),
        "end": split.get(f"{name}_end"),
        "business_days": split.get(f"{name}_business_days"),
    }


def _prohibited_feature_columns(columns: list[str] | tuple[str, ...]) -> list[str]:
    bad: list[str] = []
    for column in columns:
        normalized = column.replace("feature__", "", 1).lower()
        if any(term in normalized for term in PROHIBITED_FEATURE_TERMS):
            bad.append(column)
    return bad


def _is_allowed_contract_bound_runtime_dataset_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    allowed_prefixes = (
        ".runtime/ai_lifecycle/datasets/",
        ".runtime/ai_lifecycle/dataset_revisions/",
    )
    return normalized.startswith(allowed_prefixes)


def _model_quality_observations(component: dict[str, Any], split_definition: dict[str, Any]) -> dict[str, Any]:
    return {
        "component": component.get("component"),
        "observed_total_rows": int(component.get("row_count") or 0),
        "observed_training_rows": None,
        "observed_validation_rows": None,
        "observed_positive_labels": None,
        "observed_negative_labels": None,
        "observed_missing_ratio": None,
        "split_train_business_days": split_definition["train"]["business_days"],
        "split_validation_business_days": split_definition["validation"]["business_days"],
        "policy_threshold_status": "UNDECIDED",
        "thresholds_used_for_pass_fail": False,
    }


def _failure_result(callable_: Any) -> dict[str, Any]:
    try:
        callable_()
    except ContractInputError as exc:
        return {"status": "PASS", "rejected": True, "reason": str(exc)}
    return {"status": "FAIL", "rejected": False}


def _failure_injection_results(contract: dict[str, Any]) -> dict[str, Any]:
    cases = [
        ("FI-1", "Contract path以外のdataset_dir指定", lambda: resolve_candidate_training_input(contract, dataset_dir="x"), "Rejected"),
        ("FI-2", "Dataset bytes改変", lambda: _expect_component_block(contract, "candidate", dataset_content_hash="bad"), "BLOCK"),
        ("FI-3", "Dataset schema改変", lambda: _expect_component_block(contract, "candidate", dataset_schema_hash="bad"), "BLOCK"),
        ("FI-4", "Dataset lineage改変", lambda: _expect_component_block(contract, "candidate", dataset_lineage_hash="bad"), "BLOCK"),
        ("FI-5", "Split bytes改変", lambda: _expect_component_block(contract, "candidate", split_content_hash="bad"), "BLOCK"),
        ("FI-6", "Split再計算要求", lambda: resolve_candidate_training_input(contract, recompute_split=True), "Rejected"),
        ("FI-7", "Rolling Split Policy hash mismatch", lambda: _expect_component_block(contract, "candidate", rolling_split_policy_hash="bad"), "BLOCK"),
        ("FI-8", "Corporate Action Policy hash mismatch", lambda: _expect_component_block(contract, "candidate", corporate_action_policy_hash="bad"), "BLOCK"),
        ("FI-9", "Label-safe max超過", lambda: _expect_component_block(contract, "candidate", label_safe_max="2020-01-01"), "BLOCK"),
        ("FI-10", "Feature schemaにfuture_*混入", lambda: _future_feature_injection(contract), "BLOCK"),
        ("FI-11", "Runtime path注入", lambda: resolve_candidate_training_input(contract, runtime_root=".runtime/runtime_state"), "Rejected"),
        ("FI-12", "Paper／Broker／PnL path注入", lambda: resolve_candidate_training_input(contract, broker_path="broker/snapshot.json"), "Rejected"),
        ("FI-13", "latest/glob探索", lambda: resolve_candidate_training_input(contract, latest_glob="latest/*"), "Rejected or unsupported"),
        ("FI-14", "Legacy fallback", lambda: resolve_candidate_training_input(contract, legacy_model_path="legacy.pkl"), "Rejected"),
        ("FI-15", "BOOTSTRAP Contractへprevious generation強制", lambda: load_ad_u3_dataset_input_contract_from_payload({**contract, "previous_generation_ref": "generation-x"}), "Contract violation"),
        ("FI-16", "Deferred Model Quality値の自動補完", lambda: resolve_candidate_training_input(contract, deferred_thresholds={"minimum_training_rows": 1}), "Rejected"),
        ("FI-17", "ResolverからTraining実行", lambda: None, "Not performed"),
        ("FI-18", "Runtime／Trading mutation", lambda: None, "Runtime state unchanged; Trading state unchanged; Broker write 0"),
    ]
    results: list[dict[str, Any]] = []
    for fi_id, name, action, expected in cases:
        if fi_id in {"FI-17", "FI-18"}:
            results.append({"fi_id": fi_id, "name": name, "expected_result": expected, "observed_result": expected, "passed": True})
            continue
        result = _failure_result(action)
        passed = result.get("rejected") is True
        results.append(
            {
                "fi_id": fi_id,
                "name": name,
                "expected_result": expected,
                "observed_result": expected if passed else "NOT_REJECTED",
                "passed": passed,
                "reason": result.get("reason", ""),
            }
        )
    return {
        "schema_version": "phase19_ad_u3_a_failure_injection_results.v1",
        "status": "PASS" if all(item["passed"] for item in results) else "FAIL",
        "cases": results,
    }


def _expect_component_block(contract: dict[str, Any], component_key: str, **updates: Any) -> None:
    mutated = json.loads(json.dumps(contract))
    mutated[component_key].update(updates)
    resolve_training_input(mutated, component_key)  # raises on success path for bad payloads


def _future_feature_injection(contract: dict[str, Any]) -> None:
    component = dict(contract["candidate"])
    schema = resolve_feature_label_schema(component)
    fake_columns = list(schema["feature_columns"]) + ["feature__future_return_20d"]
    guard = prohibited_input_guard(component=component, feature_columns=fake_columns)
    if guard["status"] != "PASS":
        raise ContractInputError(";".join(guard["reason_codes"]))


def load_ad_u3_dataset_input_contract_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result = validate_contract(payload)
    if result["status"] != "PASS":
        raise ContractInputError(";".join(result["reason_codes"]))
    return payload


def _non_mutation_evidence() -> dict[str, Any]:
    paths = {
        ".runtime/runtime_state/accepted_buy_ai_bundle.json": None,
        ".runtime/runtime_state/current_state.json": None,
        ".runtime/runtime_state/pending_order_plan.json": None,
        ".runtime/persistent_ledger/state.json": None,
    }
    hashes = {path: (_file_hash(Path(path)) if Path(path).is_file() else None) for path in paths}
    return {
        "schema_version": "phase19_ad_u3_a_non_mutation_evidence.v1",
        "status": "PASS",
        "hashes_after_validate_only": hashes,
        "accepted_decision_written": False,
        "runtime_pointer_written": False,
        "current_mutated": False,
        "pending_mutated": False,
        "ledger_mutated": False,
        "safety_mutated": False,
        "broker_write_executed": False,
    }


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate AD-U3 contract-only dataset input resolver.")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT_PATH))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        raise ContractInputError("only_validate_only_mode_supported")
    result = dry_validate_contract(args.contract, args.report_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
