from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import capital_deployment, portfolio_construction, portfolio_policy, position_management
from ai_fund_lab_v2.strategy.capital_deployment import (
    CapitalDeploymentConsumerError,
    CapitalDeploymentSchemaError,
    CapitalDeploymentSourceSummary,
    build_capital_deployment_payload,
    default_runtime_artifact_path,
    load_capital_deployment_fixture,
    validate_capital_deployment_artifact,
    verify_source_hashes,
)


def test_phase22_f_produces_draft_review_required_not_eligible_artifact(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["artifact_lifecycle_status"] == "DRAFT"
    assert result.payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert result.payload["capital_constraint_status"] == "CAPITAL_SUFFICIENT"
    assert result.payload["allocation_decided"] is False
    assert result.payload["quantity_decided"] is False
    assert result.payload["lot_rounding_decided"] is False
    assert validate_capital_deployment_artifact(result.payload)["status"] == "PASS"


def test_phase22_f_schema_rejects_invalid_posture_status_and_concrete_fields(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    mutations = (
        lambda item: item.update({"portfolio_capital_posture": "BALANCED"}),
        lambda item: item["members"][0].update({"allocation_posture": "BUY"}),
        lambda item: item["members"][0].pop("security_code"),
        lambda item: item.update({"schema_version": "capital_deployment.v999"}),
        lambda item: item.update({"runtime_consumer_eligibility": "ELIGIBLE"}),
        lambda item: item.update({"target_cash_ratio": 0.2}),
        lambda item: item.update({"target_exposure_ratio": 0.8}),
        lambda item: item["members"][0].update({"allocation_jpy": 100000}),
        lambda item: item["members"][0].update({"quantity": 100}),
        lambda item: item["members"][0].update({"lot_rounding_result": "100"}),
    )
    for mutation in mutations:
        mutated = json.loads(json.dumps(payload))
        mutation(mutated)
        with pytest.raises(CapitalDeploymentSchemaError):
            validate_capital_deployment_artifact(mutated)


def test_phase22_f_upstream_review_required_propagates_and_rejects_production(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "upstream_review_required:SOURCE_REVIEW_REQUIRED" in result.payload["reason_codes"]
    assert "upstream_review_required:SOURCE_NOT_ELIGIBLE" not in result.payload["reason_codes"]
    assert result.payload["downstream_calculation_eligibility"] == "CALCULATION_ALLOWED_WITH_REVIEW"
    assert result.payload["upstream_artifacts"]["portfolio_construction"]["shadow_read_allowed"] is True
    assert result.payload["upstream_artifacts"]["portfolio_policy"]["shadow_read_allowed"] is True
    assert result.payload["upstream_artifacts"]["position_management"]["shadow_read_allowed"] is True
    with pytest.raises(CapitalDeploymentConsumerError):
        load_capital_deployment_fixture(result.artifact_path, for_production=True)


def test_phase22_f_upstream_block_schema_date_hash_propagates(tmp_path: Path) -> None:
    construction_bad = _write_portfolio_construction(tmp_path)
    mutated = json.loads(construction_bad.read_text(encoding="utf-8"))
    mutated["portfolio_members"][0]["membership_intent"] = "EXCLUDE"
    _write_json(construction_bad, mutated)
    payload, _ = build_capital_deployment_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=construction_bad,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_exposure_summary=_summary(tmp_path, "exposure"),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        pending_reservation_summary=_summary(tmp_path, "pending"),
        policy_config_summary=_summary(tmp_path, "policy_config"),
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert "upstream_block:INCOMPATIBLE_HASH" in payload["reason_codes"]


def test_phase22_f_constraint_statuses_are_separate_without_quantity_or_lot_calculation(tmp_path: Path) -> None:
    cases = [
        (_summary(tmp_path, "cash", summary={"capital_constraint_status": "CONSTRAINED"}), _summary(tmp_path, "exposure"), _summary(tmp_path, "pending"), "CAPITAL_CONSTRAINED", "CONSERVE"),
        (_summary(tmp_path, "cash", summary={"cash_constraint_status": "CONFLICT"}), _summary(tmp_path, "exposure"), _summary(tmp_path, "pending"), "CASH_RESERVE_CONFLICT", "CONSERVE"),
        (_summary(tmp_path, "cash"), _summary(tmp_path, "exposure", summary={"exposure_constraint_status": "CONFLICT"}), _summary(tmp_path, "pending"), "EXPOSURE_CONFLICT", "WITHHOLD"),
        (_summary(tmp_path, "cash"), _summary(tmp_path, "exposure"), _summary(tmp_path, "pending", summary={"reservation_status": "CONFLICT"}), "PENDING_RESERVATION_CONFLICT", "WITHHOLD"),
    ]
    for cash, exposure, pending, status, posture in cases:
        payload, _ = build_capital_deployment_payload(
            business_date="2026-07-15",
            portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path),
            portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
            position_management_artifact_path=_write_position_management(tmp_path),
            current_cash_summary=cash,
            current_exposure_summary=exposure,
            current_portfolio_summary=_summary(tmp_path, "portfolio"),
            pending_reservation_summary=pending,
            policy_config_summary=_summary(tmp_path, "policy_config"),
        )
        assert payload["capital_constraint_status"] == status
        assert payload["portfolio_capital_posture"] == posture
        assert payload["quantity_decided"] is False
        assert payload["lot_rounding_decided"] is False


def test_phase22_f_date_pit_blocks_future_cash_exposure_and_pending(tmp_path: Path) -> None:
    payload, _ = build_capital_deployment_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        current_cash_summary=_summary(tmp_path, "cash", feature_date="2026-07-16"),
        current_exposure_summary=_summary(tmp_path, "exposure"),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        pending_reservation_summary=_summary(tmp_path, "pending"),
        policy_config_summary=_summary(tmp_path, "policy_config"),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert "current_cash_date_mismatch" in payload["reason_codes"]
    assert "future_cash_exposure_or_pending_date_detected" in payload["reason_codes"]
    assert payload["temporal_safety"]["implicit_latest_fallback_used"] is False


def test_phase22_f_hash_lineage_and_artifact_hash_validation(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert verify_source_hashes(result.payload)["status"] == "PASS"
    assert result.payload["artifact_hash"] == capital_deployment.capital_deployment_hash(result.payload)
    changed = json.loads(json.dumps(result.payload))
    changed["source_hashes"][0]["sha256"] = "deadbeef"
    assert verify_source_hashes(changed)["status"] == "BLOCK"


def test_phase22_f_bootstrap_missing_inputs_does_not_use_fixed_fallbacks(tmp_path: Path) -> None:
    payload, _ = build_capital_deployment_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=None,
        portfolio_policy_artifact_path=None,
        position_management_artifact_path=None,
        current_cash_summary=_summary(tmp_path, "cash", status="REVIEW_REQUIRED"),
        current_exposure_summary=_summary(tmp_path, "exposure", status="REVIEW_REQUIRED"),
        current_portfolio_summary=_summary(tmp_path, "portfolio", status="REVIEW_REQUIRED"),
        pending_reservation_summary=_summary(tmp_path, "pending", status="REVIEW_REQUIRED"),
        policy_config_summary=_summary(tmp_path, "policy_config", status="REVIEW_REQUIRED"),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert payload["capital_constraint_status"] == "SOURCE_UNAVAILABLE"
    assert payload["members"] == []
    assert payload["temporal_safety"]["previous_day_capital_deployment_copied"] is False
    assert payload["cash_ratio_decided"] is False
    assert payload["exposure_decided"] is False


def test_phase22_f_existing_authorities_preserved(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload

    assert payload["position_count_decided"] is False
    assert payload["cash_ratio_decided"] is False
    assert payload["exposure_decided"] is False
    assert payload["position_sizing_decided"] is False
    assert payload["allocation_decided"] is False
    assert payload["quantity_decided"] is False
    assert payload["lot_rounding_decided"] is False
    assert payload["production_consumer_connected"] is False
    assert payload["runtime_switch_performed"] is False
    assert payload["legacy_authority_active"] is True
    assert payload["existing_capital_deployment_authority_active"] is True


def test_phase22_f_fixture_shadow_reads_draft_and_rejects_production(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    payload = load_capital_deployment_fixture(result.artifact_path)

    assert payload["schema_version"] == "capital_deployment.v1"
    with pytest.raises(CapitalDeploymentConsumerError):
        load_capital_deployment_fixture(result.artifact_path, for_production=True)


def _produce(tmp_path: Path):
    return capital_deployment.produce_capital_deployment_artifact(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_exposure_summary=_summary(tmp_path, "exposure"),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        pending_reservation_summary=_summary(tmp_path, "pending"),
        policy_config_summary=_summary(tmp_path, "policy_config"),
        output_path=default_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _summary(
    tmp_path: Path,
    kind: str,
    *,
    status: str = "PASS",
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
    summary: dict[str, object] | None = None,
) -> CapitalDeploymentSourceSummary:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / f"{kind}_summary.json"
    payload = {"kind": kind, "business_date": business_date, "feature_date": feature_date, "status": status, "summary": summary or {}}
    _write_json(path, payload)
    return CapitalDeploymentSourceSummary(status, business_date, feature_date, str(path), _sha256_file(path), payload["summary"])


def _write_portfolio_construction(tmp_path: Path) -> Path:
    source = tmp_path / "portfolio_construction_source.json"
    _write_json(source, {"source": "pc"})
    payload = {
        "schema_version": portfolio_construction.SCHEMA_VERSION,
        "producer_version": "phase22_e_portfolio_construction_producer.v1",
        "business_date": "2026-07-15",
        "as_of": "2026-07-15T00:00:00+00:00",
        "feature_date": "2026-07-15",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "portfolio_members": [
            _pc_member("7203", "RETAIN", True, 1, "MAINTAIN", "pm-7203", target_weight=0.2),
            _pc_member("6098", "ADD_CANDIDATE", False, 2, "INCREASE", "", target_weight=0.2, candidate_ref="candidate-6098", opportunity_ref="opportunity-6098"),
            _pc_member("8306", "REMOVE_CANDIDATE", True, 3, "REMOVE", "pm-8306", target_weight=0.0),
        ],
        "member_count": 3,
        "membership_intent_taxonomy": sorted(portfolio_construction.MEMBERSHIP_INTENTS),
        "weight_intent_taxonomy": sorted(portfolio_construction.WEIGHT_INTENTS),
        "position_count_policy_reference": "policy",
        "cash_policy_reference": "policy",
        "exposure_policy_reference": "policy",
        "concrete_values_decided": False,
        "position_count_decided": False,
        "cash_ratio_decided": False,
        "exposure_decided": False,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "reason_codes": ["upstream_review_required:SOURCE_NOT_ELIGIBLE"],
        "upstream_artifacts": {},
        "source_artifacts": [{"role": "pc", "path": str(source), "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "pc", "path": str(source), "sha256": _sha256_file(source)}],
        "temporal_safety": {"point_in_time": True, "future_leakage_used": False, "feature_date_lte_business_date": True, "implicit_latest_fallback_used": False, "previous_day_portfolio_construction_copied": False},
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    payload["artifact_hash"] = portfolio_construction.portfolio_construction_hash(payload)
    path = tmp_path / "portfolio_construction.json"
    _write_json(path, payload)
    return path


def _write_portfolio_policy(tmp_path: Path) -> Path:
    source = tmp_path / "portfolio_policy_source.json"
    _write_json(source, {"source": "policy"})
    payload = {
        "schema_version": portfolio_policy.SCHEMA_VERSION,
        "producer_version": "phase22_c_portfolio_policy_producer.v1",
        "business_date": "2026-07-15",
        "as_of": "2026-07-15T00:00:00+00:00",
        "feature_date": "2026-07-15",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "risk_posture": "BALANCED",
        "entry_posture": "MAINTAIN",
        "position_count_posture": "MAINTAIN",
        "cash_posture": "MAINTAIN",
        "exposure_posture": "MAINTAIN",
        "position_management_bias": "NEUTRAL",
        "target_position_count_resolution": {"status": "PASS", "source": "fixture", "resolved_value": 3},
        "target_position_count": 3,
        "target_gross_exposure_ratio_resolution": {"status": "PASS", "source": "fixture", "resolved_value": 0.6},
        "target_gross_exposure_ratio": 0.6,
        "target_gross_exposure": 0.6,
        "cash_reserve_ratio_resolution": {"status": "PASS", "source": "fixture", "resolved_value": 0.4},
        "cash_reserve_ratio": 0.4,
        "cash_reserve": 0.4,
        "single_name_weight_cap": 0.2,
        "single_name_weight_cap_source": "fixture#single_name_weight_cap",
        "single_name_weight_cap_authority": {"status": "PASS", "source": "fixture#single_name_weight_cap", "single_name_weight_cap": 0.2},
        "deployment_posture": "MAINTAIN",
        "confidence": 0.0,
        "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
        "reason_codes": ["upstream_review_required:SOURCE_NOT_ELIGIBLE"],
        "deferred_concrete_values": [],
        "concrete_values_decided": False,
        "upstream_artifacts": {},
        "source_artifacts": [{"role": "policy", "path": str(source), "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "policy", "path": str(source), "sha256": _sha256_file(source)}],
        "temporal_safety": {"point_in_time": True, "future_leakage_used": False, "feature_date_lte_business_date": True, "implicit_latest_fallback_used": False, "previous_day_policy_copied": False},
    }
    payload["artifact_hash"] = portfolio_policy.portfolio_policy_hash(payload)
    path = tmp_path / "portfolio_policy.json"
    _write_json(path, payload)
    return path


def _write_position_management(tmp_path: Path) -> Path:
    source = tmp_path / "pm_source.json"
    _write_json(source, {"source": "pm"})
    payload = {
        "schema_version": position_management.SCHEMA_VERSION,
        "producer_version": "phase22_d_position_management_producer.v1",
        "business_date": "2026-07-15",
        "as_of": "2026-07-15T00:00:00+00:00",
        "feature_date": "2026-07-15",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "positions": [{"position_id": "pm-7203", "security_code": "7203", "action": "HOLD", "intensity": "NONE", "confidence": 0.8, "uncertainty": "UPSTREAM_REVIEW_REQUIRED", "reason_codes": ["fixture"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""}],
        "position_count": 1,
        "action_taxonomy": sorted(position_management.PM_ACTIONS),
        "intensity_taxonomy": sorted(position_management.PM_INTENSITIES),
        "quantity_decided": False,
        "minimum_holding_decided": False,
        "cooldown_decided": False,
        "reason_codes": ["upstream_review_required:SOURCE_NOT_ELIGIBLE"],
        "upstream_artifacts": {},
        "accepted_generation_reference": {},
        "model_reference": {},
        "scaler_reference": {},
        "source_artifacts": [{"role": "pm", "path": str(source), "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "pm", "path": str(source), "sha256": _sha256_file(source)}],
        "temporal_safety": {"point_in_time": True, "future_leakage_used": False, "feature_date_lte_business_date": True, "implicit_latest_fallback_used": False, "previous_day_pm_artifact_copied": False},
        "production_consumer_connected": False,
        "existing_pm_authority_active": True,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    payload["artifact_hash"] = position_management.position_management_hash(payload)
    path = tmp_path / "position_management.json"
    _write_json(path, payload)
    return path


def _pc_member(
    security_code: str,
    membership_intent: str,
    current_position: bool,
    priority: int,
    weight_intent: str,
    pm_ref: str,
    *,
    target_weight: float,
    candidate_ref: str = "",
    opportunity_ref: str = "",
) -> dict[str, object]:
    target_membership = membership_intent in {"RETAIN", "ADD_CANDIDATE"}
    resolution = {
        "status": "PASS",
        "resolved_weight": target_weight,
        "reason": "fixture_target_weight",
    }
    if target_weight == 0.0:
        resolution["zero_weight_reason"] = "fixture_zero_weight"
    return {
        "member_id": f"pc-{security_code}",
        "security_code": security_code,
        "symbol": security_code,
        "current_position": current_position,
        "membership_intent": membership_intent,
        "target_membership": target_membership,
        "target_weight": target_weight,
        "target_weight_authority": {
            "authority": "portfolio_construction_fixture",
            "canonical_field": "target_weight",
            "schema_version": portfolio_construction.SCHEMA_VERSION,
        },
        "target_weight_resolution": resolution,
        "construction_priority": priority,
        "weight_intent": weight_intent,
        "candidate_reference": candidate_ref,
        "opportunity_reference": opportunity_ref,
        "position_management_reference": pm_ref,
        "portfolio_policy_reference": "policy",
        "membership_reason": "fixture_membership",
        "weight_reason": "fixture_weight",
        "confidence": 0.8,
        "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
        "reason_codes": ["fixture"],
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
