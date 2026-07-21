from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.ai_lifecycle.ad_u3_dataset_input_resolver import (
    ALLOWED_CONTRACT_AUTHORITY,
    ContractInputError,
    dry_validate_contract,
    load_ad_u3_dataset_input_contract,
    prohibited_input_guard,
    resolve_candidate_training_input,
    resolve_feature_label_schema,
    resolve_opportunity_training_input,
    resolve_training_input,
    resolve_versioned_split,
    validate_bootstrap_mode,
    validate_component_artifact_binding,
    validate_contract,
)


def test_contract_load_success(tmp_path: Path) -> None:
    contract_path = _fixture_contract(tmp_path)

    contract = load_ad_u3_dataset_input_contract(contract_path)

    assert contract["contract_status"] == "PASS_AFTER_CORRECTIVE_FIX"


def test_contract_missing_field_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    del contract["authority"]

    result = validate_contract(contract)

    assert result["status"] == "BLOCK"
    assert "missing_contract_field:authority" in result["reason_codes"]


def test_unknown_status_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["contract_status"] = "DRAFT"

    result = validate_contract(contract)

    assert result["status"] == "BLOCK"
    assert "unknown_or_unapproved_contract_status" in result["reason_codes"]


def test_wrong_authority_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["authority"] = "wrong"

    result = validate_contract(contract)

    assert result["status"] == "BLOCK"
    assert "wrong_contract_authority" in result["reason_codes"]


def test_candidate_and_opportunity_resolve_without_training(tmp_path: Path) -> None:
    contract = load_ad_u3_dataset_input_contract(_fixture_contract(tmp_path))

    candidate = resolve_candidate_training_input(contract)
    opportunity = resolve_opportunity_training_input(contract)

    assert candidate.component == "Candidate"
    assert opportunity.component == "Opportunity"
    assert candidate.training_executed is False
    assert candidate.split_definition["split_recomputed"] is False
    assert candidate.model_quality_policy_thresholds["minimum_training_rows"] is None


def test_dataset_hash_mismatch_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["candidate"]["dataset_content_hash"] = "bad"

    with pytest.raises(ContractInputError, match="dataset_hash_match"):
        resolve_candidate_training_input(contract)


def test_schema_hash_mismatch_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["candidate"]["dataset_schema_hash"] = "bad"

    with pytest.raises(ContractInputError, match="dataset_schema_hash_match"):
        resolve_candidate_training_input(contract)


def test_lineage_hash_mismatch_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["candidate"]["dataset_lineage_hash"] = "bad"

    with pytest.raises(ContractInputError, match="dataset_lineage_hash_match"):
        resolve_candidate_training_input(contract)


def test_split_hash_mismatch_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["candidate"]["split_content_hash"] = "bad"

    with pytest.raises(ContractInputError, match="split_hash_match"):
        resolve_candidate_training_input(contract)


def test_policy_hash_mismatch_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["candidate"]["rolling_split_policy_hash"] = "bad"

    with pytest.raises(ContractInputError, match="candidate_rolling_split_policy_hash_mismatch"):
        resolve_candidate_training_input(contract)


def test_corporate_action_policy_hash_mismatch_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["candidate"]["corporate_action_policy_hash"] = "bad"

    result = validate_contract(contract)

    assert result["status"] == "BLOCK"
    assert "candidate_corporate_action_policy_hash_mismatch" in result["reason_codes"]


def test_calendar_identity_missing_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["candidate"]["trading_calendar_identity"] = ""

    result = validate_contract(contract)

    assert result["status"] == "BLOCK"
    assert "candidate_missing_component_field:trading_calendar_identity" in result["reason_codes"]


def test_embargo_mismatch_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["candidate"]["embargo_business_days"] = 10

    result = validate_contract(contract)

    assert result["status"] == "BLOCK"
    assert "candidate_embargo_mismatch" in result["reason_codes"]


def test_label_safe_overflow_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["candidate"]["label_safe_max"] = "2020-01-01"

    result = validate_contract(contract)

    assert result["status"] == "BLOCK"
    assert "candidate_label_safe_overflow" in result["reason_codes"]


def test_future_feature_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    feature_path = Path(contract["candidate"]["feature_schema_path"])
    feature_schema = _read_json(feature_path)
    feature_schema["columns"].append({"name": "feature__future_return_20d"})
    _write_json(feature_path, feature_schema)

    result = resolve_feature_label_schema(contract["candidate"])

    assert result["status"] == "BLOCK"
    assert "future_feature_column_detected" in result["reason_codes"]


def test_prohibited_path_rejects_runtime_path() -> None:
    result = prohibited_input_guard(
        component={
            "dataset_path": ".runtime/runtime_state/current_state.json",
            "feature_schema_path": "feature_schema.json",
            "label_schema_path": "target_schema.json",
        },
        feature_columns=["feature__price_momentum_return_20d"],
    )

    assert result["status"] == "BLOCK"
    assert "prohibited_path:dataset_path" in result["reason_codes"]


def test_direct_dataset_bypass_rejects(tmp_path: Path) -> None:
    contract = load_ad_u3_dataset_input_contract(_fixture_contract(tmp_path))

    with pytest.raises(ContractInputError, match="direct_or_prohibited_input_override"):
        resolve_candidate_training_input(contract, dataset_dir="other")


def test_split_recompute_rejects(tmp_path: Path) -> None:
    contract = load_ad_u3_dataset_input_contract(_fixture_contract(tmp_path))

    with pytest.raises(ContractInputError, match="split_recompute_rejected"):
        resolve_candidate_training_input(contract, recompute_split=True)


def test_bootstrap_mode_success(tmp_path: Path) -> None:
    contract = load_ad_u3_dataset_input_contract(_fixture_contract(tmp_path))

    result = validate_bootstrap_mode(contract)

    assert result["status"] == "PASS"


def test_retraining_fallback_rejects(tmp_path: Path) -> None:
    contract = _contract_payload(_fixture_contract(tmp_path))
    contract["bootstrap_or_retraining"] = "RETRAINING"

    with pytest.raises(ContractInputError, match="unsupported_bootstrap_or_retraining"):
        resolve_candidate_training_input(contract)


def test_deferred_threshold_remains_unset(tmp_path: Path) -> None:
    contract = load_ad_u3_dataset_input_contract(_fixture_contract(tmp_path))
    resolved = resolve_candidate_training_input(contract)

    assert set(resolved.model_quality_policy_thresholds) == {
        "minimum_training_rows",
        "minimum_validation_rows",
        "minimum_positive_labels",
        "minimum_negative_labels",
        "maximum_missing_ratio",
    }
    assert all(value is None for value in resolved.model_quality_policy_thresholds.values())


def test_deferred_threshold_autofill_rejects(tmp_path: Path) -> None:
    contract = load_ad_u3_dataset_input_contract(_fixture_contract(tmp_path))

    with pytest.raises(ContractInputError, match="deferred_model_quality_autofill_rejected"):
        resolve_candidate_training_input(contract, deferred_thresholds={"minimum_training_rows": 1})


def test_dry_validate_materializes_evidence_without_training(tmp_path: Path) -> None:
    contract_path = _fixture_contract(tmp_path)
    report_dir = tmp_path / "reports"

    result = dry_validate_contract(contract_path, report_dir)

    assert result["status"] == "PASS"
    assert result["training_executed"] is False
    assert _read_json(report_dir / "training_not_executed_evidence.json")["candidate_training_executed"] is False
    assert _read_json(report_dir / "failure_injection_results.json")["status"] == "PASS"


def test_versioned_split_resolution_does_not_recompute(tmp_path: Path) -> None:
    contract = load_ad_u3_dataset_input_contract(_fixture_contract(tmp_path))

    result = resolve_versioned_split(contract["candidate"])

    assert result["status"] == "PASS"
    assert result["split_definition"]["split_recomputed"] is False


def _fixture_contract(tmp_path: Path) -> Path:
    candidate = _component_fixture(tmp_path, "candidate", "Candidate", "split_2edb9f39d8008b10")
    opportunity = _component_fixture(tmp_path, "opportunity", "Opportunity", "split_61b5c8077880a82e")
    contract = {
        "contract_id": "phase19_ad_r2_ad_u3_dataset_input_contract_corrected",
        "contract_version": "phase19_ad_r2_ad_u3_dataset_input_contract.v1",
        "contract_status": "PASS_AFTER_CORRECTIVE_FIX",
        "authority": ALLOWED_CONTRACT_AUTHORITY,
        "source_phase": "PHASE19_AD_R2",
        "generation_mode": "UNIFIED_GENERATION_INPUT",
        "bootstrap_or_retraining": "BOOTSTRAP",
        "previous_generation_ref": None,
        "candidate": candidate,
        "opportunity": opportunity,
        "policy_hashes": {
            "rolling_split_policy_hash": "approved-rolling-policy-hash",
            "corporate_action_policy_hash": "approved-ca-policy-hash",
        },
        "deferred_model_quality_policy_items": [
            "minimum_training_rows",
            "minimum_validation_rows",
            "minimum_positive_labels",
            "minimum_negative_labels",
            "maximum_missing_ratio",
        ],
    }
    path = tmp_path / "contract.json"
    _write_json(path, contract)
    return path


def _component_fixture(tmp_path: Path, key: str, component: str, split_id: str) -> dict:
    root = tmp_path / key
    root.mkdir()
    dataset_path = root / "dataset.parquet"
    dataset_path.write_bytes(f"{key}-dataset".encode())
    dataset_hash = _sha(dataset_path)
    feature_schema = {
        "kind": "feature",
        "schema_hash": f"{key}-feature-schema-hash",
        "columns": [{"name": "feature__price_momentum_return_20d"}],
    }
    label_schema = {
        "kind": "target",
        "schema_hash": f"{key}-label-schema-hash",
        "columns": [{"name": "label__future_return_20d"}],
    }
    feature_path = root / "feature_schema.json"
    label_path = root / "target_schema.json"
    _write_json(feature_path, feature_schema)
    _write_json(label_path, label_schema)
    manifest = {
        "dataset_hash": dataset_hash,
        "schema_hash": f"{key}-dataset-schema-hash",
        "feature_schema_hash": feature_schema["schema_hash"],
        "target_schema_hash": label_schema["schema_hash"],
    }
    manifest_path = root / "hash_manifest.json"
    _write_json(manifest_path, manifest)
    revision = {
        "dataset_revision": f"{key}_dataset_revision_policy_amended_hash",
        "source_lineage_hash": f"{key}-lineage-hash",
    }
    revision_path = root / "revision.json"
    _write_json(revision_path, revision)
    split = {
        "schema_version": "phase19_ad_r2_materialized_versioned_split.v1",
        "split_id": split_id,
        "split_method": "CAPPED_EXPANDING_HYBRID",
        "dataset_revision": revision["dataset_revision"],
        "dataset_hash": dataset_hash,
        "schema_hash": manifest["schema_hash"],
        "policy_id": "phase19_ad_u2_f_rolling_split_policy_option_c_capped_expanding_hybrid",
        "policy_hash": "approved-rolling-policy-hash",
        "trading_calendar_identity": "calendar-hash",
        "target_horizon_business_days": 20,
        "embargo_business_days": 20,
        "train_start": "2021-01-01",
        "train_end": "2024-12-02",
        "train_business_days": 800,
        "validation_start": "2025-01-06",
        "validation_end": "2025-12-01",
        "validation_business_days": 222,
        "test_start": "2026-01-05",
        "test_end": "2026-03-03",
        "test_business_days": 39,
        "recent_holdout_start": "2026-04-01",
        "recent_holdout_end": "2026-05-15",
        "recent_holdout_business_days": 29,
    }
    split_path = root / "split.json"
    _write_json(split_path, split)
    return {
        "component": component,
        "dataset_revision_id": revision["dataset_revision"],
        "dataset_revision_path": str(revision_path),
        "dataset_revision_content_hash": _sha(revision_path),
        "dataset_path": str(dataset_path),
        "dataset_content_hash": dataset_hash,
        "dataset_schema_hash": manifest["schema_hash"],
        "dataset_lineage_hash": revision["source_lineage_hash"],
        "dataset_hash_manifest_path": str(manifest_path),
        "source_revision": {"bootstrap_revision": True, "previous_dataset_revision": f"{key}_previous"},
        "source_cutoff": {"computed_label_safe_cutoff": "2026-05-29"},
        "dataset_date_min": "2021-01-01",
        "dataset_date_max": "2026-05-15",
        "label_safe_max": "2026-05-15",
        "split_id": split_id,
        "split_path": str(split_path),
        "split_content_hash": _sha(split_path),
        "rolling_split_policy_id": split["policy_id"],
        "rolling_split_policy_hash": split["policy_hash"],
        "corporate_action_policy_id": "phase19_ad_u2_d_corporate_action_dataset_handling",
        "corporate_action_policy_hash": "approved-ca-policy-hash",
        "trading_calendar_identity": split["trading_calendar_identity"],
        "target_horizon_business_days": 20,
        "embargo_business_days": 20,
        "feature_schema_identity": feature_schema["schema_hash"],
        "feature_schema_path": str(feature_path),
        "label_schema_identity": label_schema["schema_hash"],
        "label_schema_path": str(label_path),
        "row_count": 100,
    }


def _contract_payload(path: Path) -> dict:
    return _read_json(path)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
