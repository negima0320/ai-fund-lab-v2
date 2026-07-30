from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import dynamic_position_count as dpc
from ai_fund_lab_v2.strategy.dynamic_position_count import (
    DynamicPositionCountConsumerError,
    DynamicPositionCountSchemaError,
    DynamicPositionCountSourceSummary,
    build_dynamic_position_count_payload,
    default_runtime_artifact_path,
    dynamic_position_count_hash,
    load_dynamic_position_count_config,
    load_dynamic_position_count_fixture,
    produce_dynamic_position_count_artifact,
    validate_dynamic_position_count_artifact,
    verify_source_hashes,
)
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy
from ai_fund_lab_v2.runtime_v2.safety.portfolio_limits import (
    PortfolioSafetyLimitsError,
    load_portfolio_safety_limits,
)


def test_phase22_h_produces_draft_not_eligible_dynamic_position_count_artifact(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.status == "PASS"
    assert result.payload["schema_version"] == "dynamic_position_count.v1"
    assert result.payload["artifact_lifecycle_status"] == "DRAFT"
    assert result.payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert result.payload["minimum_position_count"] <= result.payload["target_position_count"]
    assert result.payload["maximum_position_count"] is None
    assert result.payload["safety_hard_maximum"] is None
    assert result.payload["strategy_fixed_position_cap_used"] is False
    assert result.payload["target_position_count"] <= result.payload["available_opportunity_count"]
    assert result.payload["shadow_comparison"]["runtime_behavior_changed"] is False
    assert result.payload["legacy_active_max_positions"] == 5
    assert result.payload["strategy_maximum_position_count"] is None
    assert result.payload["ceiling_authority_status"] == "SEPARATED"
    assert Path(result.artifact_path).is_file()
    assert validate_dynamic_position_count_artifact(result.payload)["status"] == "PASS"


def test_phase22_h_schema_rejects_count_hierarchy_and_invalid_counts(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    mutations = (
        lambda item: item.update({"minimum_position_count": 4, "target_position_count": 3}),
        lambda item: item.update({"target_position_count": 6, "available_opportunity_count": 5}),
        lambda item: item.update({"minimum_position_count": -1}),
        lambda item: item.update({"target_position_count": 2.5}),
        lambda item: item.update({"schema_version": "dynamic_position_count.v999"}),
        lambda item: item.update({"strategy_fixed_position_cap_used": True}),
    )
    for mutation in mutations:
        mutated = json.loads(json.dumps(payload))
        mutation(mutated)
        with pytest.raises(DynamicPositionCountSchemaError):
            validate_dynamic_position_count_artifact(mutated)


def test_phase22_h_regime_rules_preserve_relative_risk_relationships(tmp_path: Path) -> None:
    risk_on = _produce(
        tmp_path / "risk_on",
        market={"trend_regime": "BULL", "market_breadth": "STRONG", "volatility_regime": "NORMAL", "confidence": 0.95, "uncertainty": "LOW"},
        policy={"risk_posture": "RISK_ON", "entry_posture": "EXPAND", "confidence": 0.95, "uncertainty": "LOW"},
    ).payload
    balanced = _produce(
        tmp_path / "balanced",
        market={"trend_regime": "RANGE", "market_breadth": "NEUTRAL", "volatility_regime": "NORMAL", "confidence": 0.9, "uncertainty": "LOW"},
        policy={"risk_posture": "BALANCED", "entry_posture": "MAINTAIN", "confidence": 0.9, "uncertainty": "LOW"},
    ).payload
    high_vol = _produce(
        tmp_path / "high_vol",
        market={"trend_regime": "BULL", "market_breadth": "STRONG", "volatility_regime": "HIGH", "confidence": 0.8, "uncertainty": "LOW"},
        policy={"risk_posture": "BALANCED", "entry_posture": "MAINTAIN", "confidence": 0.8, "uncertainty": "LOW"},
    ).payload
    defensive = _produce(
        tmp_path / "defensive",
        market={"trend_regime": "BEAR", "market_breadth": "WEAK", "volatility_regime": "HIGH", "confidence": 0.7, "uncertainty": "MEDIUM"},
        policy={"risk_posture": "DEFENSIVE", "entry_posture": "RESTRICT", "confidence": 0.7, "uncertainty": "MEDIUM"},
    ).payload
    unresolved = _produce(
        tmp_path / "unresolved",
        market={"trend_regime": "RANGE", "market_breadth": "NEUTRAL", "volatility_regime": "NORMAL", "confidence": 0.1, "uncertainty": "HIGH"},
        policy={"risk_posture": "UNRESOLVED", "entry_posture": "UNRESOLVED", "confidence": 0.1, "uncertainty": "HIGH"},
    ).payload

    assert risk_on["target_position_count"] >= balanced["target_position_count"]
    assert high_vol["target_position_count"] <= risk_on["target_position_count"]
    assert defensive["target_position_count"] <= balanced["target_position_count"]
    assert unresolved["capacity_constraint_status"] == "UNCERTAINTY_CONSTRAINED"


def test_phase22_h_capacity_limits_do_not_create_missing_opportunities(tmp_path: Path) -> None:
    sufficient = _produce(tmp_path / "sufficient", candidates=8, opportunities=8, current=2).payload
    exact = _produce(tmp_path / "exact", candidates=5, opportunities=5, current=5).payload
    opportunity_short = _produce(tmp_path / "op_short", candidates=8, opportunities=2, current=1).payload
    candidate_short = _produce(tmp_path / "cand_short", candidates=2, opportunities=8, current=1).payload
    current_above = _produce(tmp_path / "current_above", candidates=8, opportunities=8, current=5, policy={"risk_posture": "DEFENSIVE", "entry_posture": "RESTRICT", "confidence": 0.8, "uncertainty": "LOW"}).payload

    assert sufficient["capacity_constraint_status"] == "SUFFICIENT"
    assert exact["target_position_count"] == 5
    assert opportunity_short["target_position_count"] == 2
    assert opportunity_short["capacity_constraint_status"] in {"SUFFICIENT", "OPPORTUNITY_CONSTRAINED"}
    assert candidate_short["target_position_count"] == 2
    assert candidate_short["capacity_constraint_status"] in {"SUFFICIENT", "CANDIDATE_CONSTRAINED"}
    assert current_above["strategy_fixed_position_cap_used"] is False


def test_phase23_ai_canonical_candidate_and_opportunity_capacity_fields_resolve(tmp_path: Path) -> None:
    candidate = dpc.resolve_capacity_count(_summary(tmp_path, "candidate_canonical", summary={"candidate_capacity_count": 50}), artifact_class="candidate")
    opportunity = dpc.resolve_capacity_count(_summary(tmp_path, "opportunity_canonical", summary={"opportunity_capacity_count": 50}), artifact_class="opportunity")

    assert candidate.resolution_status == "PASS"
    assert candidate.resolved_count == 50
    assert candidate.source_field == "candidate_capacity_count"
    assert candidate.legacy_alias_used is False
    assert opportunity.resolution_status == "PASS"
    assert opportunity.resolved_count == 50
    assert opportunity.source_field == "opportunity_capacity_count"
    assert opportunity.legacy_alias_used is False


def test_phase23_ai_supported_consumer_eligible_legacy_alias_resolves(tmp_path: Path) -> None:
    candidate = dpc.resolve_capacity_count(_summary(tmp_path, "candidate_legacy", summary={"consumer_eligible_rows": 50, "row_count": 50}), artifact_class="candidate")
    opportunity = dpc.resolve_capacity_count(_summary(tmp_path, "opportunity_legacy", summary={"consumer_eligible_rows": 50, "row_count": 50}), artifact_class="opportunity")

    assert candidate.resolution_status == "PASS"
    assert candidate.resolved_count == 50
    assert candidate.source_field == "consumer_eligible_rows"
    assert candidate.legacy_alias_used is True
    assert opportunity.resolution_status == "PASS"
    assert opportunity.resolved_count == 50
    assert opportunity.source_field == "consumer_eligible_rows"
    assert opportunity.legacy_alias_used is True


def test_phase23_ai_missing_capacity_fields_review_required_without_silent_zero(tmp_path: Path) -> None:
    payload, _ = build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_missing", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy_missing", summary=_policy()),
        candidate_summary=_summary(tmp_path, "candidate_missing", summary={"raw_row_count": 50}),
        opportunity_summary=_summary(tmp_path, "opportunity_missing", summary={"raw_row_count": 50}),
        current_portfolio_summary=_summary(tmp_path, "current_missing", summary={"current_position_count": 0}),
        safety_hard_maximum=10,
        existing_active_max_positions=5,
        config=_resolved_config(),
    )

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["target_position_count"] is None
    assert payload["capacity_resolution_status"] == "REVIEW_REQUIRED"
    assert "CANDIDATE_CAPACITY_FIELD_MISSING" in payload["reason_codes"]
    assert "OPPORTUNITY_CAPACITY_FIELD_MISSING" in payload["reason_codes"]


def test_phase23_ai_conflicting_capacity_fields_review_required(tmp_path: Path) -> None:
    payload, _ = build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_conflict", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy_conflict", summary=_policy()),
        candidate_summary=_summary(tmp_path, "candidate_conflict", summary={"consumer_eligible_rows": 50, "available_candidate_count": 0, "row_count": 50}),
        opportunity_summary=_summary(tmp_path, "opportunity_conflict", summary={"consumer_eligible_rows": 50, "available_opportunity_count": 0, "row_count": 50}),
        current_portfolio_summary=_summary(tmp_path, "current_conflict", summary={"current_position_count": 0}),
        safety_hard_maximum=10,
        existing_active_max_positions=5,
        config=_resolved_config(),
    )

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["target_position_count"] is None
    assert payload["candidate_capacity_resolution"]["resolution_status"] == "REVIEW_REQUIRED"
    assert payload["opportunity_capacity_resolution"]["resolution_status"] == "REVIEW_REQUIRED"
    assert payload["candidate_capacity_resolution"]["conflict_detected"] is True
    assert payload["opportunity_capacity_resolution"]["conflict_detected"] is True
    assert "CANDIDATE_CAPACITY_FIELD_CONFLICT" in payload["reason_codes"]
    assert "OPPORTUNITY_CAPACITY_FIELD_CONFLICT" in payload["reason_codes"]


def test_phase23_ai_legitimate_zero_capacity_passes_when_rejections_are_complete(tmp_path: Path) -> None:
    candidate = dpc.resolve_capacity_count(_summary(tmp_path, "candidate_zero", summary={"consumer_eligible_rows": 0, "row_count": 50, "rejected_rows": 50}), artifact_class="candidate")
    opportunity = dpc.resolve_capacity_count(_summary(tmp_path, "opportunity_zero", summary={"consumer_eligible_rows": 0, "row_count": 50, "rejected_rows": 50}), artifact_class="opportunity")

    assert candidate.resolution_status == "PASS"
    assert candidate.resolved_count == 0
    assert candidate.resolution_reason == "LEGITIMATE_ZERO_CAPACITY"
    assert opportunity.resolution_status == "PASS"
    assert opportunity.resolved_count == 0
    assert opportunity.resolution_reason == "LEGITIMATE_ZERO_CAPACITY"


def test_phase23_ai_target_run_capacity_reproduction_uses_policy_not_silent_zero(tmp_path: Path) -> None:
    payload, _ = build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_ah", summary={"trend_regime": "BULL", "market_breadth": "STRONG", "volatility_regime": "NORMAL", "confidence": 0.95, "uncertainty": "LOW"}),
        portfolio_policy_summary=_summary(tmp_path, "policy_ah", summary={"risk_posture": "RISK_ON", "entry_posture": "EXPAND", "confidence": 0.95, "uncertainty": "LOW"}),
        candidate_summary=_summary(tmp_path, "candidate_ah", summary={"consumer_eligible_rows": 50, "row_count": 50}),
        opportunity_summary=_summary(tmp_path, "opportunity_ah", summary={"consumer_eligible_rows": 50, "row_count": 50}),
        current_portfolio_summary=_summary(tmp_path, "current_ah", summary={"current_position_count": 0}),
        safety_hard_maximum=10,
        existing_active_max_positions=5,
        config=_resolved_config(),
    )

    assert payload["producer_result_status"] == "PASS"
    assert payload["resolved_candidate_capacity"] == 50
    assert payload["resolved_opportunity_capacity"] == 50
    assert payload["target_position_count"] > 0
    assert "candidate_capacity_constrained" not in payload["reason_codes"]
    assert "opportunity_capacity_constrained" not in payload["reason_codes"]


def test_phase23_ai_no_forced_buy_when_policy_capacity_is_legitimate_zero(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "zero_policy", candidates=0, opportunities=0, current=0).payload

    assert payload["producer_result_status"] == "PASS"
    assert payload["resolved_candidate_capacity"] == 0
    assert payload["resolved_opportunity_capacity"] == 0
    assert payload["target_position_count"] == 0
    assert payload["target_position_count_resolution"] == "EXPLICIT_ZERO"


def test_phase23_ai_contradiction_guard_prevents_upstream_positive_from_resolving_zero(tmp_path: Path) -> None:
    payload, _ = build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_guard", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy_guard", summary=_policy()),
        candidate_summary=_summary(tmp_path, "candidate_guard", summary={"candidate_capacity_count": 0, "consumer_eligible_rows": 50, "row_count": 50}),
        opportunity_summary=_summary(tmp_path, "opportunity_guard", summary={"opportunity_capacity_count": 0, "consumer_eligible_rows": 50, "row_count": 50}),
        current_portfolio_summary=_summary(tmp_path, "current_guard", summary={"current_position_count": 0}),
        safety_hard_maximum=10,
        existing_active_max_positions=5,
        config=_resolved_config(),
    )

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["candidate_capacity_resolution"]["resolved_count"] == 0
    assert payload["opportunity_capacity_resolution"]["resolved_count"] == 0
    assert payload["capacity_resolution_status"] == "REVIEW_REQUIRED"
    assert payload["target_position_count"] is None


def test_phase22_h_status_propagates_review_and_blocks_without_fixed_fallback(tmp_path: Path) -> None:
    review_payload, _ = build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market", status="REVIEW_REQUIRED", summary={}),
        portfolio_policy_summary=_summary(tmp_path, "policy", summary=_policy()),
        candidate_summary=_summary(tmp_path, "candidate", summary={"available_candidate_count": 8}),
        opportunity_summary=_summary(tmp_path, "opportunity", summary={"available_opportunity_count": 8}),
        current_portfolio_summary=_summary(tmp_path, "current", summary={"current_position_count": 1}),
        safety_hard_maximum=10,
        existing_active_max_positions=5,
        config=_resolved_config(),
    )
    assert review_payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert review_payload["target_position_count"] is None
    assert review_payload["target_position_count_resolution"] == "UNRESOLVED"
    assert review_payload["downstream_calculation_eligibility"] == "CALCULATION_ALLOWED_WITH_REVIEW"
    assert review_payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert review_payload["temporal_safety"]["previous_day_target_copied"] is False

    block_payload, _ = build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_block", status="PASS", feature_date="2026-07-16", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy_block", summary=_policy()),
        candidate_summary=_summary(tmp_path, "candidate_block", summary={"available_candidate_count": 8}),
        opportunity_summary=_summary(tmp_path, "opportunity_block", summary={"available_opportunity_count": 8}),
        current_portfolio_summary=_summary(tmp_path, "current_block", summary={"current_position_count": 1}),
        safety_hard_maximum=10,
        existing_active_max_positions=5,
        config=_resolved_config(),
    )
    assert block_payload["producer_result_status"] == "BLOCK"
    assert "future_source_date_detected" in block_payload["reason_codes"]


def test_phase22_h_config_missing_invalid_and_hash_mismatch_contract(tmp_path: Path) -> None:
    payload, _ = build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy", summary=_policy()),
        candidate_summary=_summary(tmp_path, "candidate", summary={"available_candidate_count": 8}),
        opportunity_summary=_summary(tmp_path, "opportunity", summary={"available_opportunity_count": 8}),
        current_portfolio_summary=_summary(tmp_path, "current", summary={"current_position_count": 1}),
        safety_hard_maximum=10,
        existing_active_max_positions=5,
        config=None,
    )
    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "dynamic_position_count_config_required" in payload["reason_codes"]

    bad_config = tmp_path / "bad_config.json"
    _write_json(bad_config, {"schema_version": "bad"})
    with pytest.raises(dpc.DynamicPositionCountConfigError):
        load_dynamic_position_count_config(bad_config)

    mismatch, _ = build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_hash", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy_hash", summary=_policy()),
        candidate_summary=_summary(tmp_path, "candidate_hash", summary={"available_candidate_count": 8}),
        opportunity_summary=_summary(tmp_path, "opportunity_hash", summary={"available_opportunity_count": 8}),
        current_portfolio_summary=_summary(tmp_path, "current_hash", summary={"current_position_count": 1}),
        safety_hard_maximum=10,
        existing_active_max_positions=5,
        config=_resolved_config(),
        expected_config_hash="sha256:deadbeef",
    )
    assert mismatch["producer_result_status"] == "BLOCK"
    assert "dynamic_position_count_config_hash_mismatch" in mismatch["reason_codes"]


def test_phase22_h_hash_lineage_fixture_and_artifact_hash_validation(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert verify_source_hashes(result.payload)["status"] == "PASS"
    assert result.payload["artifact_hash"] == dynamic_position_count_hash(result.payload)
    changed = json.loads(json.dumps(result.payload))
    changed["source_hashes"][0]["sha256"] = "deadbeef"
    assert verify_source_hashes(changed)["status"] == "BLOCK"
    fixture = load_dynamic_position_count_fixture(result.artifact_path)
    assert fixture["schema_version"] == "dynamic_position_count.v1"
    with pytest.raises(DynamicPositionCountConsumerError):
        load_dynamic_position_count_fixture(result.artifact_path, for_production=True)


def test_phase22_h_runtime_preservation_existing_max_positions_unchanged(tmp_path: Path) -> None:
    policy = load_capital_deployment_policy("configs/runtime_v2/capital_deployment.json")
    result = _produce(tmp_path)

    assert policy.max_positions == 5
    assert result.payload["shadow_comparison"]["existing_active_max_positions"] == 5
    assert result.payload["strategy_maximum_position_count"] is None
    assert result.payload["strategy_fixed_position_cap_used"] is False
    assert result.payload["shadow_comparison"]["runtime_behavior_changed"] is False
    assert result.payload["runtime_switch_performed"] is False
    assert result.payload["existing_max_positions_authority_active"] is True
    assert result.payload["cash_ratio_decided"] is False
    assert result.payload["exposure_decided"] is False
    assert result.payload["position_sizing_decided"] is False
    assert result.payload["allocation_decided"] is False
    assert result.payload["quantity_decided"] is False
    assert result.payload["lot_rounding_decided"] is False


def test_phase22_hr_unresolved_safety_fixture_reviews_without_legacy_fallback(tmp_path: Path) -> None:
    payload, _ = build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_hr", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy_hr", summary=_policy()),
        candidate_summary=_summary(tmp_path, "candidate_hr", summary={"available_candidate_count": 10}),
        opportunity_summary=_summary(tmp_path, "opportunity_hr", summary={"available_opportunity_count": 10}),
        current_portfolio_summary=_summary(tmp_path, "current_hr", summary={"current_position_count": 2}),
        safety_hard_maximum=None,
        existing_active_max_positions=5,
        config=_unresolved_safety_config(),
    )

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["legacy_active_max_positions"] == 5
    assert payload["strategy_maximum_position_count"] is None
    assert payload["difference_from_legacy_ceiling"] is None
    assert payload["safety_hard_maximum"] is None
    assert payload["safety_hard_maximum_status"] == "REVIEW_REQUIRED"
    assert payload["ceiling_authority_status"] == "REVIEW_REQUIRED"
    assert "safety_hard_maximum_review_required" in payload["reason_codes"]


def test_phase22_hs_fixed_position_count_safety_cap_is_removed_and_shared() -> None:
    policy = load_capital_deployment_policy("configs/runtime_v2/capital_deployment.json")
    limits = load_portfolio_safety_limits("configs/safety/portfolio_limits.json", legacy_active_max_positions=policy.max_positions)

    assert limits.authority_owner == "Safety Layer"
    assert limits.safety_hard_maximum is None
    assert limits.override_allowed is False
    assert tuple(sorted(limits.effective_scope)) == ("demo", "historical", "production")
    assert _config().strategy_maximum_position_count is None
    assert _config().safety_hard_maximum_status == "REMOVED"
    assert _config().safety_hard_maximum_reference == "configs/safety/portfolio_limits.json#position_count.fixed_position_count_cap_removed"


def test_phase22_hs_safety_config_rejects_override_legacy_hash_environment_and_invalid_values(tmp_path: Path) -> None:
    source = json.loads(Path("configs/safety/portfolio_limits.json").read_text(encoding="utf-8"))
    cases = (
        lambda item: item["position_count"].update({"override_allowed": True}),
        lambda item: item["position_count"].update({"safety_hard_maximum": 0}),
        lambda item: item["position_count"].update({"safety_hard_maximum": 10.5}),
        lambda item: item["position_count"].update({"effective_scope": ["production", "demo"]}),
        lambda item: item.update({"authority_owner": "Runtime"}),
    )
    for index, mutation in enumerate(cases):
        payload = json.loads(json.dumps(source))
        mutation(payload)
        path = tmp_path / f"bad_safety_{index}.json"
        _write_json(path, payload)
        with pytest.raises(PortfolioSafetyLimitsError):
            load_portfolio_safety_limits(path, legacy_active_max_positions=5)

    with pytest.raises(PortfolioSafetyLimitsError):
        load_portfolio_safety_limits("configs/safety/portfolio_limits.json", expected_config_hash="sha256:deadbeef", legacy_active_max_positions=5)


def test_phase22_hr_legacy_five_implicit_safety_cap_blocks(tmp_path: Path) -> None:
    config = replace(
        _config(),
        strategy_maximum_position_count=5,
        safety_hard_maximum_status="PASS",
        safety_hard_maximum_reference=_config().legacy_active_max_positions_reference,
    )
    payload, _ = build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_legacy_cap", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy_legacy_cap", summary=_policy()),
        candidate_summary=_summary(tmp_path, "candidate_legacy_cap", summary={"available_candidate_count": 10}),
        opportunity_summary=_summary(tmp_path, "opportunity_legacy_cap", summary={"available_opportunity_count": 10}),
        current_portfolio_summary=_summary(tmp_path, "current_legacy_cap", summary={"current_position_count": 2}),
        safety_hard_maximum=5,
        existing_active_max_positions=5,
        config=config,
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert payload["ceiling_authority_status"] == "BLOCK"
    assert "legacy_max_positions_must_not_be_implicit_safety_hard_maximum" in payload["reason_codes"]


def test_phase22_pr_resolved_safety_maximum_no_longer_caps_strategy_target(tmp_path: Path) -> None:
    payload, _ = build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_safety_block", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy_safety_block", summary=_policy()),
        candidate_summary=_summary(tmp_path, "candidate_safety_block", summary={"available_candidate_count": 10}),
        opportunity_summary=_summary(tmp_path, "opportunity_safety_block", summary={"available_opportunity_count": 10}),
        current_portfolio_summary=_summary(tmp_path, "current_safety_block", summary={"current_position_count": 2}),
        safety_hard_maximum=7,
        existing_active_max_positions=5,
        config=_resolved_config(),
    )

    assert payload["producer_result_status"] == "PASS"
    assert payload["strategy_fixed_position_cap_used"] is False
    assert payload["safety_hard_maximum_used_for_target_calculation"] is False


def _produce(
    tmp_path: Path,
    *,
    market: dict[str, object] | None = None,
    policy: dict[str, object] | None = None,
    candidates: int = 8,
    opportunities: int = 8,
    current: int = 2,
):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return produce_dynamic_position_count_artifact(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market", summary=market or _market()),
        portfolio_policy_summary=_summary(tmp_path, "policy", summary=policy or _policy()),
        candidate_summary=_summary(tmp_path, "candidate", summary={"available_candidate_count": candidates}),
        opportunity_summary=_summary(tmp_path, "opportunity", summary={"available_opportunity_count": opportunities}),
        current_portfolio_summary=_summary(tmp_path, "current", summary={"current_position_count": current}),
        safety_hard_maximum=10,
        existing_active_max_positions=5,
        config=_resolved_config(),
        output_path=default_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _config() -> dpc.DynamicPositionCountConfig:
    return load_dynamic_position_count_config("configs/strategy/dynamic_position_count.json")


def _resolved_config() -> dpc.DynamicPositionCountConfig:
    return _config()


def _unresolved_safety_config() -> dpc.DynamicPositionCountConfig:
    return replace(
        _config(),
        safety_hard_maximum_status="REVIEW_REQUIRED",
        safety_hard_maximum_reference="OPEN_DESIGN_DECISION",
    )


def _market() -> dict[str, object]:
    return {"trend_regime": "BULL", "market_breadth": "STRONG", "volatility_regime": "NORMAL", "confidence": 0.95, "uncertainty": "LOW"}


def _policy() -> dict[str, object]:
    return {"risk_posture": "RISK_ON", "entry_posture": "EXPAND", "confidence": 0.95, "uncertainty": "LOW"}


def _summary(
    tmp_path: Path,
    kind: str,
    *,
    status: str = "PASS",
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
    summary: dict[str, object] | None = None,
) -> DynamicPositionCountSourceSummary:
    path = tmp_path / f"{kind}_summary.json"
    payload = {
        "kind": kind,
        "status": status,
        "business_date": business_date,
        "feature_date": feature_date,
        "summary": summary or {},
    }
    _write_json(path, payload)
    return DynamicPositionCountSourceSummary(
        status=status,
        business_date=business_date,
        feature_date=feature_date,
        source_ref=str(path),
        source_hash=dpc.sha256_file(path),
        summary=summary or {},
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
