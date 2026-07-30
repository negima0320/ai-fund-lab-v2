from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import corporate_event, market_context, portfolio_policy
from ai_fund_lab_v2.strategy.position_management import (
    PMAcceptedGenerationReference,
    PMSourceSummary,
    PositionManagementConsumerError,
    PositionManagementSchemaError,
    build_position_management_payload,
    default_runtime_artifact_path,
    load_position_management_fixture,
    position_management_hash,
    produce_position_management_artifact,
    validate_generation_binding,
    validate_position_management_artifact,
    verify_source_hashes,
)
from ai_fund_lab_v2.strategy.portfolio_policy import PortfolioPolicyConfig, PortfolioPolicyInputSummary


def test_phase22_d_produces_draft_review_required_not_eligible_artifact(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["artifact_lifecycle_status"] == "DRAFT"
    assert result.payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert result.payload["quantity_decided"] is False
    assert result.payload["minimum_holding_decided"] is False
    assert result.payload["cooldown_decided"] is False
    assert [item["action"] for item in result.payload["positions"]] == ["HOLD", "ADD", "REDUCE", "EXIT"]
    assert validate_position_management_artifact(result.payload)["status"] == "PASS"


def test_phase22_d_schema_rejects_invalid_action_intensity_missing_identity_status_and_quantity(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    mutations = (
        lambda item: item["positions"][0].update({"action": "SELL"}),
        lambda item: item["positions"][0].update({"intensity": "HIGH"}),
        lambda item: item["positions"][0].pop("position_id"),
        lambda item: item["positions"][0].pop("security_code"),
        lambda item: item.update({"schema_version": "position_management.v999"}),
        lambda item: item.update({"runtime_consumer_eligibility": "ELIGIBLE"}),
        lambda item: item["positions"][0].update({"runtime_sell_quantity": 100}),
    )
    for mutation in mutations:
        mutated = json.loads(json.dumps(payload))
        mutation(mutated)
        with pytest.raises(PositionManagementSchemaError):
            validate_position_management_artifact(mutated)


def test_phase22_d_upstream_review_required_and_not_eligible_propagates(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "upstream_review_required:SOURCE_REVIEW_REQUIRED" in result.payload["reason_codes"]
    assert "upstream_review_required:SOURCE_NOT_ELIGIBLE" not in result.payload["reason_codes"]
    assert result.payload["downstream_calculation_eligibility"] == "CALCULATION_ALLOWED_WITH_REVIEW"
    assert result.payload["upstream_artifacts"]["market_context"]["shadow_read_allowed"] is True
    assert result.payload["upstream_artifacts"]["corporate_event"]["shadow_read_allowed"] is True
    assert result.payload["upstream_artifacts"]["portfolio_policy"]["shadow_read_allowed"] is True
    with pytest.raises(PositionManagementConsumerError):
        load_position_management_fixture(result.artifact_path, for_production=True)


def test_phase22_d_upstream_block_schema_date_hash_propagates_to_block(tmp_path: Path) -> None:
    market_bad = _write_market_context(tmp_path, schema_version="strategy_market_context.v999")
    portfolio_path = _write_portfolio_policy(tmp_path)
    payload, _ = build_position_management_payload(
        business_date="2026-07-15",
        market_context_artifact_path=market_bad,
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=portfolio_path,
        existing_pm_decisions=_pm_decisions(),
        position_lifecycle_summary=_summary(tmp_path, "lifecycle"),
        technical_feature_summary=_summary(tmp_path, "features"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        accepted_generation_reference=_generation(tmp_path),
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert any(reason.startswith("upstream_block:") for reason in payload["reason_codes"])

    hash_bad = _write_portfolio_policy(tmp_path)
    mutated = json.loads(hash_bad.read_text(encoding="utf-8"))
    mutated["risk_posture"] = "DEFENSIVE"
    _write_json(hash_bad, mutated)
    payload, _ = build_position_management_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=hash_bad,
        existing_pm_decisions=_pm_decisions(),
        position_lifecycle_summary=_summary(tmp_path, "lifecycle"),
        technical_feature_summary=_summary(tmp_path, "features"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        accepted_generation_reference=_generation(tmp_path),
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert "upstream_block:INCOMPATIBLE_HASH" in payload["reason_codes"]


def test_phase22_d_date_pit_rejects_cross_date_and_future_lifecycle(tmp_path: Path) -> None:
    payload, _ = build_position_management_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        existing_pm_decisions=_pm_decisions(),
        position_lifecycle_summary=_summary(tmp_path, "lifecycle", business_date="2026-07-14", feature_date="2026-07-16"),
        technical_feature_summary=_summary(tmp_path, "features"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        accepted_generation_reference=_generation(tmp_path),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert "position_lifecycle_date_mismatch" in payload["reason_codes"]
    assert "future_feature_or_lifecycle_date_detected" in payload["reason_codes"]
    assert payload["temporal_safety"]["implicit_latest_fallback_used"] is False


def test_phase22_d_generation_model_scaler_binding_blocks_mismatch_hash_and_unscaled_fallback(tmp_path: Path) -> None:
    assert validate_generation_binding(_generation(tmp_path))["status"] == "PASS"
    assert validate_generation_binding(_generation(tmp_path, scaler_generation_id="other-generation"))["status"] == "BLOCK"
    assert "scaler_generation_mismatch" in validate_generation_binding(_generation(tmp_path, scaler_generation_id="other-generation"))["reason_codes"]
    assert "model_hash_mismatch" in validate_generation_binding(_generation(tmp_path, model_hash="deadbeef"))["reason_codes"]
    assert "unscaled_fallback_forbidden" in validate_generation_binding(_generation(tmp_path, scaler_reference=""))["reason_codes"]


def test_phase22_d_action_and_intensity_are_separated_and_quantity_not_generated(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    reduce = next(item for item in payload["positions"] if item["action"] == "REDUCE")
    exit_item = next(item for item in payload["positions"] if item["action"] == "EXIT")

    assert reduce["intensity"] == "MEDIUM"
    assert exit_item["intensity"] == "NONE"
    for position in payload["positions"]:
        assert not ({"quantity", "runtime_sell_quantity", "broker_quantity", "reduce_quantity", "exit_quantity"} & set(position))


def test_phase22_d_bootstrap_missing_inputs_does_not_emit_fixed_hold_pass(tmp_path: Path) -> None:
    payload, _ = build_position_management_payload(
        business_date="2026-07-15",
        market_context_artifact_path=None,
        corporate_event_artifact_path=None,
        portfolio_policy_artifact_path=None,
        existing_pm_decisions=[],
        position_lifecycle_summary=_summary(tmp_path, "lifecycle", status="REVIEW_REQUIRED"),
        technical_feature_summary=_summary(tmp_path, "features", status="REVIEW_REQUIRED"),
        opportunity_summary=_summary(tmp_path, "opportunity", status="REVIEW_REQUIRED"),
        accepted_generation_reference=_generation(tmp_path),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert payload["positions"] == []
    assert "position_management_shadow_positions_required" in payload["reason_codes"]
    assert payload["temporal_safety"]["previous_day_pm_artifact_copied"] is False


def test_phase22_d_existing_pm_behavior_preservation_from_shadow_rows(tmp_path: Path) -> None:
    decisions = _pm_decisions()
    payload = _produce(tmp_path, decisions=decisions).payload

    assert [row["action"] for row in payload["positions"]] == [row["decision"] for row in decisions]
    assert [row["intensity"] for row in payload["positions"]] == ["NONE", "UNRESOLVED", "MEDIUM", "NONE"]
    assert [row["confidence"] for row in payload["positions"]] == [row["confidence"] for row in decisions]
    assert payload["accepted_generation_reference"]["generation_id"] == "pm-generation-fixture"
    assert payload["model_reference"]["path"].endswith("pm_model.pkl")
    assert payload["scaler_reference"]["path"].endswith("pm_scaler.pkl")


def test_phase23_e_runtime_current_positions_feed_strategy_pm_without_fixed_empty_or_hold(tmp_path: Path) -> None:
    payload, _ = build_position_management_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        existing_pm_decisions=[],
        runtime_current_positions=[
            {
                "position_id": "runtime-pos-7203",
                "symbol": "7203",
                "quantity": 100,
                "average_price": 1000,
                "acquired_at": "2026-07-10T00:00:00+00:00",
                "position_state_as_of": "2026-07-15",
                "valuation_as_of": "2026-07-15",
                "position_lifecycle_id": "lifecycle-7203",
            }
        ],
        position_lifecycle_summary=_summary(tmp_path, "lifecycle"),
        technical_feature_summary=_summary(tmp_path, "features"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        accepted_generation_reference=_generation(tmp_path),
    )

    assert payload["positions"]
    assert "position_management_shadow_positions_required" not in payload["reason_codes"]
    assert payload["runtime_current_position_adapter"]["status"] == "PASS"
    assert payload["runtime_current_position_adapter"]["direct_position_copy_used"] is False
    assert payload["runtime_current_position_adapter"]["fixed_empty_positions_used"] is False
    position = payload["positions"][0]
    assert position["position_id"] == "runtime-pos-7203"
    assert position["security_code"] == "7203"
    assert position["action"] == "UNRESOLVED"
    assert "runtime_current_position_requires_strategy_pm_evaluation" in position["reason_codes"]
    assert not ({"quantity", "runtime_sell_quantity", "broker_quantity", "reduce_quantity", "exit_quantity"} & set(position))
    contract = position["adapter_source_contract"]
    assert contract["quantity"] == 100
    assert contract["average_price"] == 1000
    assert contract["valuation_date"] == "2026-07-15"
    assert contract["position_lifecycle_id"] == "lifecycle-7203"
    assert contract["accepted_generation_id"] == "pm-generation-fixture"
    assert contract["technical_features_join_key"] == {"code": "7203", "target_date": "2026-07-15"}
    assert payload["accepted_generation_reference"]["generation_binding_validation"]["status"] == "PASS"
    assert validate_position_management_artifact(payload)["status"] == "PASS"


def test_phase23_k_authoritative_empty_runtime_current_is_safe_zero_action(tmp_path: Path) -> None:
    payload, _ = build_position_management_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        existing_pm_decisions=[],
        runtime_current_positions=[],
        position_lifecycle_summary=PMSourceSummary(
            status="REVIEW_REQUIRED",
            business_date="2026-07-15",
            feature_date="2026-07-15",
            source_ref="",
            source_hash="",
            summary={},
        ),
        technical_feature_summary=PMSourceSummary(
            status="REVIEW_REQUIRED",
            business_date="2026-07-15",
            feature_date="2026-07-15",
            source_ref="",
            source_hash="",
            summary={},
        ),
        opportunity_summary=PMSourceSummary(
            status="REVIEW_REQUIRED",
            business_date="2026-07-15",
            feature_date="2026-07-15",
            source_ref="",
            source_hash="",
            summary={},
        ),
        accepted_generation_reference=_generation(tmp_path),
    )

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["positions"] == []
    assert payload["runtime_current_position_adapter"]["status"] == "EMPTY_PORTFOLIO"
    assert payload["runtime_current_position_adapter"]["runtime_current_connected"] is True
    assert payload["runtime_current_position_adapter"]["authoritative_empty_portfolio"] is True
    assert "position_management_shadow_positions_required" not in payload["reason_codes"]
    assert "technical_features_review_required" not in payload["reason_codes"]
    assert "source_lineage_hash_required" not in payload["reason_codes"]
    assert payload["accepted_generation_reference"]["generation_binding_validation"]["status"] == "PASS"
    assert validate_position_management_artifact(payload)["status"] == "PASS"


def test_phase22_d_hash_lineage_and_artifact_hash_validation(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    assert verify_source_hashes(result.payload)["status"] == "PASS"
    assert result.payload["artifact_hash"] == position_management_hash(result.payload)

    changed = json.loads(json.dumps(result.payload))
    changed["source_hashes"][0]["sha256"] = "deadbeef"
    assert verify_source_hashes(changed)["status"] == "BLOCK"
    changed = json.loads(json.dumps(result.payload))
    changed["positions"][0]["action"] = "EXIT"
    assert changed["artifact_hash"] != position_management_hash(changed)


def test_phase22_d_fixture_shadow_reads_draft_and_rejects_production(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    payload = load_position_management_fixture(result.artifact_path)

    assert payload["schema_version"] == "position_management.v1"
    with pytest.raises(PositionManagementConsumerError):
        load_position_management_fixture(result.artifact_path, for_production=True)


def _produce(tmp_path: Path, *, decisions: list[dict[str, object]] | None = None):
    return produce_position_management_artifact(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        existing_pm_decisions=decisions or _pm_decisions(),
        position_lifecycle_summary=_summary(tmp_path, "lifecycle"),
        technical_feature_summary=_summary(tmp_path, "features"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        accepted_generation_reference=_generation(tmp_path),
        output_path=default_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _pm_decisions() -> list[dict[str, object]]:
    return [
        {"decision_id": "pm-1", "symbol": "7203", "decision": "HOLD", "confidence": 0.8, "decision_reason_codes": ["HOLD_BY_STRONG_CONTINUATION"], "feature_vector_hash": "fv-hold"},
        {"decision_id": "pm-2", "symbol": "6758", "decision": "ADD", "confidence": 0.7, "decision_reason_codes": ["ADD_BY_STRONG_TREND_AND_RANK"], "feature_vector_hash": "fv-add"},
        {"decision_id": "pm-3", "symbol": "9984", "decision": "REDUCE", "reduce_intensity": "MEDIUM", "confidence": 0.6, "decision_reason_codes": ["REDUCE_BY_PEAK_DRAWDOWN_WARNING"], "feature_vector_hash": "fv-reduce"},
        {"decision_id": "pm-4", "symbol": "8306", "decision": "EXIT", "confidence": 0.9, "decision_reason_codes": ["EXIT_BY_HARD_STOP"], "feature_vector_hash": "fv-exit"},
    ]


def _generation(
    tmp_path: Path,
    *,
    model_generation_id: str = "pm-generation-fixture",
    scaler_generation_id: str = "pm-generation-fixture",
    model_hash: str | None = None,
    scaler_reference: str | None = None,
) -> PMAcceptedGenerationReference:
    model = tmp_path / "pm_model.pkl"
    scaler = tmp_path / "pm_scaler.pkl"
    model.write_bytes(b"pm-model")
    scaler.write_bytes(b"pm-scaler")
    return PMAcceptedGenerationReference(
        generation_id="pm-generation-fixture",
        generation_status="RESOLVED_COMMITTED",
        model_reference=str(model),
        scaler_reference=str(scaler) if scaler_reference is None else scaler_reference,
        model_generation_id=model_generation_id,
        scaler_generation_id=scaler_generation_id,
        model_hash=_sha256_file(model) if model_hash is None else model_hash,
        scaler_hash=_sha256_file(scaler),
        feature_schema_hash="pm-feature-schema-hash",
        accepted_generation_hash="accepted-generation-hash",
    )


def _summary(
    tmp_path: Path,
    kind: str,
    *,
    status: str = "PASS",
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
) -> PMSourceSummary:
    path = tmp_path / f"{kind}_summary.json"
    payload = {"kind": kind, "business_date": business_date, "feature_date": feature_date, "status": status}
    _write_json(path, payload)
    return PMSourceSummary(
        status=status,
        business_date=business_date,
        feature_date=feature_date,
        source_ref=str(path),
        source_hash=_sha256_file(path),
        summary=payload,
    )


def _write_portfolio_policy(tmp_path: Path) -> Path:
    market_path = _write_market_context(tmp_path)
    corporate_path = _write_corporate_event(tmp_path)
    candidate = _pp_summary(tmp_path, "candidate")
    opportunity = _pp_summary(tmp_path, "opportunity")
    config_path = tmp_path / "portfolio_policy_config.json"
    config_payload = {
        "intent_policy": {
            "risk_posture": "BALANCED",
            "entry_posture": "MAINTAIN",
            "position_count_posture": "MAINTAIN",
            "cash_posture": "MAINTAIN",
            "exposure_posture": "MAINTAIN",
            "position_management_bias": "NEUTRAL",
        },
        "single_name_weight_cap": 0.18,
    }
    _write_json(config_path, config_payload)
    result = portfolio_policy.produce_portfolio_policy_artifact(
        business_date="2026-07-15",
        market_context_artifact_path=market_path,
        corporate_event_artifact_path=corporate_path,
        candidate_summary=candidate,
        opportunity_summary=opportunity,
        current_portfolio_summary={},
        current_cash_summary={},
        current_exposure_summary={},
        policy_config=PortfolioPolicyConfig(
            config_version="phase22_d_fixture_policy_config.v1",
            config_source=str(config_path),
            intent_policy=config_payload["intent_policy"],
            single_name_weight_cap=0.18,
            single_name_weight_cap_source=f"{config_path}#single_name_weight_cap",
        ),
        output_path=tmp_path / "portfolio_policy.json",
    )
    return Path(result.artifact_path)


def _pp_summary(tmp_path: Path, kind: str) -> PortfolioPolicyInputSummary:
    path = tmp_path / f"pp_{kind}_summary.json"
    payload = {"kind": kind, "business_date": "2026-07-15", "feature_date": "2026-07-15"}
    _write_json(path, payload)
    return PortfolioPolicyInputSummary("PASS", "2026-07-15", "2026-07-15", payload, str(path), _sha256_file(path))


def _write_market_context(
    tmp_path: Path,
    *,
    schema_version: str = market_context.SCHEMA_VERSION,
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
) -> Path:
    source = tmp_path / "market_source.parquet"
    source.write_text("market-source", encoding="utf-8")
    payload = {
        "schema_version": schema_version,
        "producer_version": "phase22_a_market_context_producer.v1",
        "business_date": business_date,
        "as_of": f"{business_date}T00:00:00+00:00",
        "feature_date": feature_date,
        "trend_regime": "RANGE",
        "trend_strength": 0.0,
        "market_breadth": "NEUTRAL",
        "volatility_regime": "NORMAL",
        "sector_dispersion": "MODERATE",
        "confidence": 0.0,
        "uncertainty": "THRESHOLD_OR_SOURCE_REVIEW_REQUIRED",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "reason_codes": ["market_context_threshold_config_required"],
        "source_artifacts": [{"role": "jquants_daily_quotes", "path": str(source), "required": True, "exists": True}],
        "source_hashes": [{"role": "jquants_daily_quotes", "path": str(source), "sha256": market_context.sha256_file(source)}],
        "temporal_safety": {"point_in_time": feature_date <= business_date, "future_leakage_used": feature_date > business_date, "feature_date_lte_business_date": feature_date <= business_date},
        "metrics": {},
        "threshold_policy": {"status": "CONFIG_REQUIRED", "source": "", "values": None},
    }
    payload["artifact_hash"] = market_context.market_context_hash(payload)
    path = tmp_path / f"market_context_{business_date}_{feature_date}_{schema_version}.json"
    _write_json(path, payload)
    return path


def _write_corporate_event(tmp_path: Path, *, business_date: str = "2026-07-15", feature_date: str = "2026-07-15") -> Path:
    source = tmp_path / "corporate_source.parquet"
    source.write_text("corporate-source", encoding="utf-8")
    payload = {
        "schema_version": corporate_event.SCHEMA_VERSION,
        "producer_version": "phase22_aa_corporate_event_producer.v1",
        "business_date": business_date,
        "as_of": f"{business_date}T00:00:00+00:00",
        "feature_date": feature_date,
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "coverage_status": "PARTIAL",
        "events": [],
        "source_artifacts": [{"role": "jquants_listed_issues", "path": str(source), "required": True, "exists": True}],
        "source_hashes": [{"role": "jquants_listed_issues", "path": str(source), "sha256": corporate_event.sha256_file(source)}],
        "temporal_safety": {"point_in_time": feature_date <= business_date, "future_leakage_used": feature_date > business_date, "feature_date_lte_business_date": feature_date <= business_date},
    }
    payload["artifact_hash"] = corporate_event.corporate_event_hash(payload)
    path = tmp_path / f"corporate_event_{business_date}_{feature_date}.json"
    _write_json(path, payload)
    return path


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
