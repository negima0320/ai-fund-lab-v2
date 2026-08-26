from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import corporate_event, market_context, portfolio_policy as pp
from ai_fund_lab_v2.strategy.candidate_opportunity_compatibility import ArtifactCompatibilityResult
from ai_fund_lab_v2.strategy.portfolio_policy import (
    PortfolioPolicyConfig,
    PortfolioPolicyConsumerError,
    PortfolioPolicyInputSummary,
    PortfolioPolicySchemaError,
    build_portfolio_policy_payload,
    default_runtime_artifact_path,
    load_portfolio_policy_fixture,
    portfolio_policy_hash,
    produce_portfolio_policy_artifact,
    stable_payload_hash,
    validate_portfolio_policy_artifact,
    verify_source_hashes,
)


def test_phase22_c_produces_draft_review_required_not_eligible_artifact(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["artifact_lifecycle_status"] == "DRAFT"
    assert result.payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert result.payload["concrete_values_decided"] is False
    assert result.payload["risk_posture"] == "BALANCED"
    assert result.payload["entry_posture"] == "MAINTAIN"
    assert result.payload["upstream_artifacts"]["market_context"]["shadow_read_allowed"] is True
    assert result.payload["upstream_artifacts"]["corporate_event"]["shadow_read_allowed"] is True
    assert Path(result.artifact_path).is_file()
    assert validate_portfolio_policy_artifact(result.payload)["status"] == "PASS"


def test_phase22_c_schema_rejects_missing_field_invalid_taxonomy_status_and_confidence(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    for mutation in (
        lambda item: item.pop("risk_posture"),
        lambda item: item.update({"cash_posture": "TWENTY_PERCENT"}),
        lambda item: item.update({"runtime_consumer_eligibility": "ELIGIBLE"}),
        lambda item: item.update({"confidence": 2.0}),
        lambda item: item.update({"schema_version": "portfolio_policy.v999"}),
    ):
        mutated = dict(payload)
        mutation(mutated)
        with pytest.raises(PortfolioPolicySchemaError):
            validate_portfolio_policy_artifact(mutated)


def test_phase22_c_upstream_review_required_and_not_eligible_propagates(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    reasons = set(result.payload["reason_codes"])
    assert result.payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "upstream_review_required:SOURCE_REVIEW_REQUIRED" in reasons
    assert "upstream_review_required:SOURCE_NOT_ELIGIBLE" not in reasons
    assert result.payload["downstream_calculation_eligibility"] == "CALCULATION_ALLOWED_WITH_REVIEW"
    assert result.payload["consumer_eligibility_reason_codes"] == ["SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE"]
    with pytest.raises(PortfolioPolicyConsumerError):
        load_portfolio_policy_fixture(result.artifact_path, for_production=True)


def test_phase22_c_upstream_block_schema_date_and_hash_propagate_to_block(tmp_path: Path) -> None:
    schema_bad_market = _write_market_context(tmp_path, schema_version="strategy_market_context.v999")
    date_bad_corporate = _write_corporate_event(tmp_path, business_date="2026-07-14", feature_date="2026-07-14")
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=schema_bad_market,
        corporate_event_artifact_path=date_bad_corporate,
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={"position_count": 0},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        policy_config=_config(tmp_path),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert any(reason.startswith("upstream_block:") for reason in payload["reason_codes"])

    hash_bad = _write_market_context(tmp_path)
    mutated = json.loads(hash_bad.read_text(encoding="utf-8"))
    mutated["trend_strength"] = 0.5
    _write_json(hash_bad, mutated)
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=hash_bad,
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={"position_count": 0},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        policy_config=_config(tmp_path),
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert "upstream_block:INCOMPATIBLE_HASH" in payload["reason_codes"]


def test_phase22_c_date_pit_rejects_candidate_opportunity_future_and_cross_date(tmp_path: Path) -> None:
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        candidate_summary=_summary(tmp_path, "candidate", business_date="2026-07-14", feature_date="2026-07-14"),
        opportunity_summary=_summary(tmp_path, "opportunity", feature_date="2026-07-16"),
        current_portfolio_summary={},
        current_cash_summary={},
        current_exposure_summary={},
        policy_config=_config(tmp_path),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert "candidate_summary_date_mismatch" in payload["reason_codes"]
    assert "opportunity_summary_date_mismatch" in payload["reason_codes"]
    assert "future_feature_date_detected" in payload["reason_codes"]


def test_phase22_c_hash_lineage_config_hash_and_source_hash_validation(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    assert verify_source_hashes(result.payload)["status"] == "PASS"

    bad_config = _config(tmp_path)
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={},
        current_cash_summary={},
        current_exposure_summary={},
        policy_config=bad_config,
        expected_policy_config_hash="sha256:deadbeef",
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert "policy_config_hash_mismatch" in payload["reason_codes"]

    source_hashes = list(result.payload["source_hashes"])
    source_hashes[0] = {**source_hashes[0], "sha256": "deadbeef"}
    changed = {**result.payload, "source_hashes": source_hashes}
    assert verify_source_hashes(changed)["status"] == "BLOCK"


def test_phase22_c_bootstrap_missing_inputs_review_required_no_fixed_fallback(tmp_path: Path) -> None:
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=None,
        corporate_event_artifact_path=None,
        candidate_summary=_summary(tmp_path, "candidate", status="REVIEW_REQUIRED"),
        opportunity_summary=_summary(tmp_path, "opportunity", status="REVIEW_REQUIRED"),
        current_portfolio_summary={},
        current_cash_summary={},
        current_exposure_summary={},
        policy_config=None,
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert payload["risk_posture"] == "UNRESOLVED"
    assert payload["temporal_safety"]["previous_day_policy_copied"] is False
    assert payload["temporal_safety"]["implicit_latest_fallback_used"] is False
    assert "policy_config_required" in payload["reason_codes"]


def test_phase22_c_intent_taxonomy_is_axis_separated_and_concrete_values_forbidden(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload

    assert {
        "risk_posture",
        "entry_posture",
        "position_count_posture",
        "cash_posture",
        "exposure_posture",
        "position_management_bias",
    }.issubset(payload)
    assert payload["concrete_values_decided"] is False
    assert "target_positions" not in payload
    payload["target_cash_ratio"] = 0.2
    with pytest.raises(PortfolioPolicySchemaError):
        validate_portfolio_policy_artifact(payload)


def test_phase22_c_fixture_shadow_consumer_reads_draft_and_rejects_production(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    fixture = load_portfolio_policy_fixture(result.artifact_path)

    assert fixture["schema_version"] == "portfolio_policy.v1"
    assert fixture["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    with pytest.raises(PortfolioPolicyConsumerError):
        load_portfolio_policy_fixture(result.artifact_path, for_production=True)


def test_phase22_c_artifact_hash_is_stable_and_detects_mismatch(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    payload = dict(result.payload)
    assert payload["artifact_hash"] == portfolio_policy_hash(payload)
    payload["cash_posture"] = "RAISE"
    assert payload["artifact_hash"] != portfolio_policy_hash(payload)


def test_phase31_g28_risk_pacing_authoritative_maps_market_quality(tmp_path: Path) -> None:
    cases = [
        ("HEALTHY_EXPANSION", "COMPLETE", "NORMAL_DEPLOYMENT", ["RISK_PACING_NORMAL"]),
        ("RECOVERY_CONFIRMATION_INCOMPLETE", "COMPLETE", "GRADUAL_REDEPLOYMENT", ["RISK_PACING_GRADUAL_REDEPLOYMENT"]),
        ("SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH", "COMPLETE", "CAUTIOUS_DEPLOYMENT", ["RISK_PACING_CAUTIOUS"]),
        ("CONFLICTED_MARKET_STRUCTURE", "PARTIAL", "CAUTIOUS_DEPLOYMENT", ["RISK_PACING_CAUTIOUS"]),
        ("INSUFFICIENT_EVIDENCE", "INSUFFICIENT", "PRESERVE_OPTIONALITY", ["RISK_PACING_INSUFFICIENT_MARKET_QUALITY", "RISK_PACING_PRESERVE_OPTIONALITY"]),
    ]
    for quality, completeness, expected_intent, expected_reasons in cases:
        payload, _ = build_portfolio_policy_payload(
            business_date="2026-07-15",
            market_context_artifact_path=_write_market_context(
                tmp_path / quality,
                accepted=True,
                market_quality_state=quality,
                market_quality_evidence_completeness=completeness,
            ),
            corporate_event_artifact_path=_write_corporate_event(tmp_path / quality, accepted=True),
            candidate_summary=_summary(tmp_path / quality, "candidate"),
            opportunity_summary=_summary(tmp_path / quality, "opportunity"),
            current_portfolio_summary={"position_count": 0},
            current_cash_summary={"cash_available": 1000000},
            current_exposure_summary={"gross_exposure": 0},
            policy_config=_config(tmp_path / quality),
        )
        assert payload["risk_pacing_intent"] == expected_intent
        assert payload["risk_pacing_reason_codes"] == expected_reasons
        assert payload["risk_pacing_authority"]["owner"] == "PORTFOLIO_POLICY"
        assert payload["risk_pacing_authority"]["authoritative_consumer"] == "PORTFOLIO_CONSTRUCTION"
        assert payload["risk_pacing_authority"]["authoritative_consumer_count"] == 1
        assert payload["risk_pacing_authority"]["shadow_path_removed"] is True
        assert payload["risk_pacing_mode"] == "AUTHORITATIVE"
        assert payload["risk_pacing_as_of"] == "2026-07-15"
        assert payload["risk_pacing_component_evidence"]["future_information_used"] is False
        assert payload["risk_pacing_component_evidence"]["historical_outcome_used"] is False
        assert payload["risk_pacing_component_evidence"]["evidence_feedback_used"] is False
        assert "target_exposure_ratio" not in payload
        assert "target_positions" not in payload
        assert validate_portfolio_policy_artifact(payload)["status"] == "PASS"


def test_phase31_g23_risk_pacing_missing_quality_fails_closed_and_is_deterministic(tmp_path: Path) -> None:
    kwargs = dict(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path, accepted=True),
        corporate_event_artifact_path=_write_corporate_event(tmp_path, accepted=True),
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={"position_count": 0},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        policy_config=_config(tmp_path),
    )
    first, _ = build_portfolio_policy_payload(**kwargs)
    second, _ = build_portfolio_policy_payload(**kwargs)

    assert first["risk_pacing_intent"] == "PRESERVE_OPTIONALITY"
    assert first["risk_pacing_reason_codes"] == ["RISK_PACING_INSUFFICIENT_MARKET_QUALITY"]
    assert first["risk_pacing_evidence_completeness"] == "INSUFFICIENT"
    assert first["risk_pacing_intent"] == second["risk_pacing_intent"]
    assert first["risk_pacing_reason_codes"] == second["risk_pacing_reason_codes"]
    assert first["risk_posture"] == second["risk_posture"] == "BALANCED"
    assert first["entry_posture"] == second["entry_posture"] == "MAINTAIN"
    assert first["target_position_count"] == second["target_position_count"]
    assert first["target_gross_exposure_ratio"] == second["target_gross_exposure_ratio"]
    assert first["risk_pacing_mode"] == "AUTHORITATIVE"
    assert first["risk_pacing_authority"]["authoritative_consumer_count"] == 1


def test_phase31_g23_risk_pacing_temporal_invalid_quality_is_not_normal(tmp_path: Path) -> None:
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(
            tmp_path,
            accepted=True,
            market_quality_state="HEALTHY_EXPANSION",
            market_quality_evidence_completeness="COMPLETE",
            market_quality_as_of="2026-07-16",
        ),
        corporate_event_artifact_path=_write_corporate_event(tmp_path, accepted=True),
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={"position_count": 0},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        policy_config=_config(tmp_path),
    )

    assert payload["risk_pacing_intent"] == "PRESERVE_OPTIONALITY"
    assert "RISK_PACING_TEMPORAL_AUTHORITY_INVALID" in payload["risk_pacing_reason_codes"]
    assert payload["risk_pacing_as_of"] == "2026-07-15"


def test_phase29_j1_portfolio_policy_routes_dpc_capacity_to_dce_without_low_capacity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pp, "validate_market_context_compatibility", lambda *args, **kwargs: _compatible_result("market_context"))
    monkeypatch.setattr(pp, "validate_corporate_event_compatibility", lambda *args, **kwargs: _compatible_result("corporate_event"))
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path, accepted=True),
        corporate_event_artifact_path=_write_corporate_event(tmp_path, accepted=True),
        candidate_summary=_summary(tmp_path, "candidate_j1", summary={"consumer_eligible_rows": 50}),
        opportunity_summary=_summary(
            tmp_path,
            "opportunity_j1",
            summary={"consumer_eligible_rows": 50, "buy_eligible_opportunity_count": 50, "meaningful_allocation_position_count": 50},
        ),
        current_portfolio_summary={"position_count": 0},
        current_cash_summary={"cash_available": 200000},
        current_exposure_summary={"gross_exposure": 800000},
        policy_config=_config(tmp_path),
        safety_limit_summary={"minimum_cash_ratio": 0.0, "maximum_gross_exposure_ratio": 1.0, "concentration": {"maximum_position_weight": 0.25}},
    )
    dce_internal = payload["upstream_artifacts"]["internal_policy_resolvers"]["dynamic_cash_exposure_internal"]

    assert payload["resolved_opportunity_capacity"] == 50
    assert payload["meaningful_allocation_position_count"] == 50
    assert dce_internal["opportunity_capacity_authority"]["resolved_value"] == 50
    assert dce_internal["opportunity_capacity_authority"]["source"] == "dynamic_position_count.resolved_opportunity_capacity"
    assert "internal_dynamic_cash_exposure:low_opportunity_capacity" not in payload["reason_codes"]
    assert dce_internal["target_gross_exposure_ratio"] == 1.0
    assert dce_internal["target_gross_exposure_ratio"] > 0.90


def test_phase31_g56_capital_budget_envelope_schema_is_authoritative_without_trading_consumer(tmp_path: Path) -> None:
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(
            tmp_path,
            accepted=True,
            market_quality_state="SHORT_TERM_BREADTH_BREAKDOWN",
            market_quality_evidence_completeness="COMPLETE",
        ),
        corporate_event_artifact_path=_write_corporate_event(tmp_path, accepted=True),
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={"position_count": 0},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        pending_reservation_summary={"pending_reserved_cash": 0},
        policy_config=_config(tmp_path),
    )

    envelope = payload["incremental_capital_budget_envelope"]

    assert envelope["schema_version"] == "incremental_capital_budget_envelope.v1"
    assert envelope["owner"] == "PORTFOLIO_POLICY"
    assert envelope["authority_status"] == "AUTHORITATIVE"
    assert envelope["planned_authoritative_consumer"] == "PORTFOLIO_CONSTRUCTION"
    assert envelope["planned_authoritative_consumer_count"] == 1
    assert envelope["authoritative_consumer_count"] == 0
    assert envelope["trading_consumer_connected"] is False
    assert envelope["portfolio_construction_decision_change_count"] == 0
    assert envelope["position_sizing_decision_change_count"] == 0
    assert envelope["runtime_order_intent_change_count"] == 0
    assert envelope["profit_engine_preservation_evidence"]["deployment_intensity_is_not_security_admission"] is True
    assert envelope["profit_engine_preservation_evidence"]["market_quality_hard_buy_gate_created"] is False
    assert envelope["exploration_participation_semantic"]["reduced_risk_participation_possible"] is True
    assert envelope["exploration_participation_semantic"]["no_buy_created_by_envelope"] is True
    assert envelope["historical_outcome_used"] is False
    assert envelope["paper_ledger_input_used"] is False
    assert envelope["mfe_mae_input_used"] is False
    assert envelope["test_result_input_used"] is False
    assert envelope["audit_result_input_used"] is False
    assert validate_portfolio_policy_artifact(payload)["status"] == "PASS"


def test_phase31_g56_capital_budget_semantic_states_are_reachable(tmp_path: Path) -> None:
    cases = [
        ("healthy_bootstrap", "HEALTHY_EXPANSION", "COMPLETE", {"position_count": 0}, {"gross_exposure": 0}, "FULL_DEPLOYMENT_CAPACITY"),
        ("healthy_invested", "HEALTHY_EXPANSION", "COMPLETE", {"position_count": 3}, {"gross_exposure": 500000}, "ELEVATED_DEPLOYMENT_CAPACITY"),
        ("gradual", "RECOVERY_CONFIRMATION_INCOMPLETE", "COMPLETE", {"position_count": 2}, {"gross_exposure": 300000}, "SELECTIVE_DEPLOYMENT_CAPACITY"),
        ("cautious_invested", "CONFLICTED_MARKET_STRUCTURE", "COMPLETE", {"position_count": 2}, {"gross_exposure": 300000}, "DEFENSIVE_DEPLOYMENT_CAPACITY"),
        ("missing_quality", None, None, {"position_count": 0}, {"gross_exposure": 0}, "PRESERVE_MOST_OPTIONALITY"),
    ]
    observed = set()
    for name, quality, completeness, portfolio, exposure, expected in cases:
        case_dir = tmp_path / name
        payload, _ = build_portfolio_policy_payload(
            business_date="2026-07-15",
            market_context_artifact_path=_write_market_context(
                case_dir,
                accepted=True,
                market_quality_state=quality,
                market_quality_evidence_completeness=completeness,
            ),
            corporate_event_artifact_path=_write_corporate_event(case_dir, accepted=True),
            candidate_summary=_summary(case_dir, "candidate"),
            opportunity_summary=_summary(case_dir, "opportunity"),
            current_portfolio_summary=portfolio,
            current_cash_summary={"cash_available": 1000000},
            current_exposure_summary=exposure,
            pending_reservation_summary={"pending_reserved_cash": 0},
            policy_config=_config(case_dir),
        )
        capacity = payload["incremental_capital_budget_envelope"]["deployment_capacity_semantic"]
        observed.add(capacity)
        assert capacity == expected

    assert observed == {
        "FULL_DEPLOYMENT_CAPACITY",
        "ELEVATED_DEPLOYMENT_CAPACITY",
        "SELECTIVE_DEPLOYMENT_CAPACITY",
        "DEFENSIVE_DEPLOYMENT_CAPACITY",
        "PRESERVE_MOST_OPTIONALITY",
    }


def test_phase31_g56_bootstrap_residual_and_missing_evidence_semantics(tmp_path: Path) -> None:
    bootstrap, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(
            tmp_path / "bootstrap",
            accepted=True,
            market_quality_state="SHORT_TERM_BREADTH_BREAKDOWN",
            market_quality_evidence_completeness="COMPLETE",
        ),
        corporate_event_artifact_path=_write_corporate_event(tmp_path / "bootstrap", accepted=True),
        candidate_summary=_summary(tmp_path / "bootstrap", "candidate"),
        opportunity_summary=_summary(tmp_path / "bootstrap", "opportunity"),
        current_portfolio_summary={"position_count": 0},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        pending_reservation_summary={"pending_reserved_cash": 0},
        policy_config=_config(tmp_path / "bootstrap"),
    )
    residual, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(
            tmp_path / "residual",
            accepted=True,
            market_quality_state="SHORT_TERM_BREADTH_BREAKDOWN",
            market_quality_evidence_completeness="COMPLETE",
        ),
        corporate_event_artifact_path=_write_corporate_event(tmp_path / "residual", accepted=True),
        candidate_summary=_summary(tmp_path / "residual", "candidate"),
        opportunity_summary=_summary(tmp_path / "residual", "opportunity"),
        current_portfolio_summary={"position_count": 1},
        current_cash_summary={"cash_available": 250000},
        current_exposure_summary={"gross_exposure": 750000},
        pending_reservation_summary={"pending_reserved_cash": 0},
        policy_config=_config(tmp_path / "residual"),
    )
    missing, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path / "missing", accepted=True),
        corporate_event_artifact_path=_write_corporate_event(tmp_path / "missing", accepted=True),
        candidate_summary=_summary(tmp_path / "missing", "candidate"),
        opportunity_summary=_summary(tmp_path / "missing", "opportunity"),
        current_portfolio_summary={"position_count": 0},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        pending_reservation_summary={"pending_reserved_cash": 0},
        policy_config=_config(tmp_path / "missing"),
    )

    bootstrap_envelope = bootstrap["incremental_capital_budget_envelope"]
    residual_envelope = residual["incremental_capital_budget_envelope"]
    missing_envelope = missing["incremental_capital_budget_envelope"]

    assert bootstrap_envelope["bootstrap_or_residual_cash_state"] == "EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP"
    assert residual_envelope["bootstrap_or_residual_cash_state"] == "RESIDUAL_OPTIONALITY_CASH"
    assert bootstrap_envelope["deployment_capacity_semantic"] == "SELECTIVE_DEPLOYMENT_CAPACITY"
    assert bootstrap_envelope["exploration_participation_semantic"]["bootstrap_automatic_full_deployment"] is False
    assert bootstrap_envelope["exploration_participation_semantic"]["bootstrap_automatic_preserve_most_optionality"] is False
    assert missing_envelope["evidence_completeness"] == "INSUFFICIENT"
    assert missing_envelope["deployment_capacity_semantic"] == "PRESERVE_MOST_OPTIONALITY"
    assert missing_envelope["deployment_capacity_semantic"] != "FULL_DEPLOYMENT_CAPACITY"


def test_phase31_g56_envelope_is_deterministic_and_behavior_additive(tmp_path: Path) -> None:
    kwargs = dict(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(
            tmp_path,
            accepted=True,
            market_quality_state="HEALTHY_EXPANSION",
            market_quality_evidence_completeness="COMPLETE",
        ),
        corporate_event_artifact_path=_write_corporate_event(tmp_path, accepted=True),
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={"position_count": 0},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        pending_reservation_summary={"pending_reserved_cash": 0},
        policy_config=_config(tmp_path),
    )
    first, _ = build_portfolio_policy_payload(**kwargs)
    second, _ = build_portfolio_policy_payload(**kwargs)
    first_without_envelope = {key: value for key, value in first.items() if key != "incremental_capital_budget_envelope"}
    second_without_envelope = {key: value for key, value in second.items() if key != "incremental_capital_budget_envelope"}

    assert first["incremental_capital_budget_envelope"] == second["incremental_capital_budget_envelope"]
    assert first_without_envelope == second_without_envelope
    assert first["risk_pacing_intent"] == "NORMAL_DEPLOYMENT"
    assert first["target_gross_exposure_ratio"] == second["target_gross_exposure_ratio"]
    assert first["target_position_count"] == second["target_position_count"]
    assert first["incremental_capital_budget_envelope"]["authoritative_consumer_count"] == 0


def test_phase31_g56_missing_stale_and_malformed_envelope_fail_closed(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload

    missing = dict(payload)
    missing.pop("incremental_capital_budget_envelope")
    with pytest.raises(PortfolioPolicySchemaError):
        validate_portfolio_policy_artifact(missing)

    malformed = json.loads(json.dumps(payload))
    malformed["incremental_capital_budget_envelope"]["authority_status"] = "EVIDENCE_ONLY_NON_AUTHORITATIVE"
    with pytest.raises(PortfolioPolicySchemaError):
        validate_portfolio_policy_artifact(malformed)

    stale = json.loads(json.dumps(payload))
    stale["incremental_capital_budget_envelope"]["market_quality_as_of"] = "2026-07-16"
    stale["incremental_capital_budget_envelope"]["envelope_hash"] = portfolio_policy_hash({})
    with pytest.raises(PortfolioPolicySchemaError):
        validate_portfolio_policy_artifact(stale)


def _produce(tmp_path: Path):
    return produce_portfolio_policy_artifact(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={"position_count": 2},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        policy_config=_config(tmp_path),
        output_path=default_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _config(tmp_path: Path) -> PortfolioPolicyConfig:
    path = tmp_path / "portfolio_policy_config.json"
    payload = {
        "config_version": "phase22_c_fixture_intent_config.v1",
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
    _write_json(path, payload)
    return PortfolioPolicyConfig(
        config_version="phase22_c_fixture_intent_config.v1",
        config_source=str(path),
        intent_policy=payload["intent_policy"],
        single_name_weight_cap=0.18,
        single_name_weight_cap_source=f"{path}#single_name_weight_cap",
    )


def _summary(
    tmp_path: Path,
    kind: str,
    *,
    status: str = "PASS",
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
    summary: dict[str, object] | None = None,
) -> PortfolioPolicyInputSummary:
    path = tmp_path / f"{kind}_summary.json"
    payload = summary or {"kind": kind, "business_date": business_date, "feature_date": feature_date, "count": 2}
    _write_json(path, payload)
    return PortfolioPolicyInputSummary(
        status=status,
        business_date=business_date,
        feature_date=feature_date,
        summary=payload,
        source_ref=str(path),
        source_hash=_sha256_file(path),
    )


def _write_market_context(
    tmp_path: Path,
    *,
    schema_version: str = market_context.SCHEMA_VERSION,
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
    accepted: bool = False,
    market_quality_state: str | None = None,
    market_quality_evidence_completeness: str | None = None,
    market_quality_as_of: str | None = None,
) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
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
        "confidence": 0.9 if accepted else 0.0,
        "uncertainty": "LOW" if accepted else "THRESHOLD_OR_SOURCE_REVIEW_REQUIRED",
        "artifact_lifecycle_status": "ACCEPTED" if accepted else "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "PASS" if accepted else "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "ELIGIBLE" if accepted else "NOT_ELIGIBLE",
        "reason_codes": [] if accepted else ["market_context_threshold_config_required"],
        "source_artifacts": [{"role": "jquants_daily_quotes", "path": str(source), "required": True, "exists": True}],
        "source_hashes": [{"role": "jquants_daily_quotes", "path": str(source), "sha256": market_context.sha256_file(source)}],
        "temporal_safety": {
            "point_in_time": feature_date <= business_date,
            "future_leakage_used": feature_date > business_date,
            "feature_date_lte_business_date": feature_date <= business_date,
        },
        "metrics": {},
        "threshold_policy": {"status": "CONFIG_REQUIRED", "source": "", "values": None},
    }
    if market_quality_state:
        payload.update(
            {
                "market_quality_state": market_quality_state,
                "market_quality_reason_codes": ["MARKET_QUALITY_HEALTHY"] if market_quality_state.startswith("HEALTHY") else [f"TEST_{market_quality_state}"],
                "market_quality_evidence_completeness": market_quality_evidence_completeness or "COMPLETE",
                "market_quality_component_evidence": {
                    "schema_version": "market_quality_component_evidence.v1",
                    "future_information_used": False,
                    "historical_outcome_used": False,
                    "evidence_feedback_used": False,
                },
                "market_quality_as_of": market_quality_as_of or feature_date,
            }
        )
    payload["artifact_hash"] = market_context.market_context_hash(payload)
    path = tmp_path / f"market_context_{business_date}_{feature_date}_{schema_version}.json"
    _write_json(path, payload)
    return path


def _write_corporate_event(
    tmp_path: Path,
    *,
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
    accepted: bool = False,
) -> Path:
    source = tmp_path / "corporate_source.parquet"
    source.write_text("corporate-source", encoding="utf-8")
    payload = {
        "schema_version": corporate_event.SCHEMA_VERSION,
        "producer_version": "phase22_aa_corporate_event_producer.v1",
        "business_date": business_date,
        "as_of": f"{business_date}T00:00:00+00:00",
        "feature_date": feature_date,
        "artifact_lifecycle_status": "ACCEPTED" if accepted else "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "PASS" if accepted else "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "ELIGIBLE" if accepted else "NOT_ELIGIBLE",
        "coverage_status": "FULL" if accepted else "PARTIAL",
        "events": [],
        "event_count": 0,
        "event_taxonomy": sorted(corporate_event.EVENT_TYPES),
        "event_identity": {
            "algorithm": "sha256",
            "fields": ["security_code", "event_type", "announcement_date", "effective_date", "availability_date", "source_reference", "revision_id"],
            "row_order_dependent": False,
        },
        "reason_codes": [] if accepted else ["corporate_event_source_coverage_incomplete"],
        "source_artifacts": [{"role": "jquants_listed_issues", "path": str(source), "required": True, "exists": True}],
        "source_hashes": [{"role": "jquants_listed_issues", "path": str(source), "sha256": corporate_event.sha256_file(source)}],
        "temporal_safety": {
            "point_in_time": feature_date <= business_date,
            "future_leakage_used": feature_date > business_date,
            "feature_date_lte_business_date": feature_date <= business_date,
        },
        "no_event_semantics": {
            "empty_events_meaning": "NO_EVENTS_ONLY_WHEN_SOURCE_COVERAGE_AVAILABLE_AND_PRODUCER_PASS",
            "unknown_event_state_when_source_missing": False,
        },
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


def _compatible_result(kind: str) -> ArtifactCompatibilityResult:
    return ArtifactCompatibilityResult(
        artifact_kind=kind,
        artifact_path=f"{kind}.json",
        schema_version=f"{kind}.v1",
        status="COMPATIBLE_NOT_CONNECTED",
        schema_compatible=True,
        shadow_read_allowed=True,
        production_decision_allowed=False,
        business_date="2026-07-15",
        feature_date="2026-07-15",
        business_date_aligned=True,
        feature_date_point_in_time=True,
        artifact_hash_valid=True,
        source_lineage_valid=True,
        source_hashes_valid=True,
        lifecycle_status="DRAFT",
        producer_result_status="PASS",
        runtime_consumer_eligibility="NOT_ELIGIBLE",
        reason_codes=(),
    )
