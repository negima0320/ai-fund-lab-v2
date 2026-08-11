from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy
from ai_fund_lab_v2.runtime_v2.safety.portfolio_limits import load_portfolio_safety_limits
from ai_fund_lab_v2.strategy import dynamic_cash_exposure as dce
from ai_fund_lab_v2.strategy.dynamic_cash_exposure import (
    CashExposureSourceSummary,
    DynamicCashExposureConsumerError,
    DynamicCashExposureSchemaError,
    build_dynamic_cash_exposure_payload,
    default_runtime_artifact_path,
    dynamic_cash_exposure_hash,
    load_dynamic_cash_exposure_config,
    load_dynamic_cash_exposure_fixture,
    produce_dynamic_cash_exposure_artifact,
    validate_dynamic_cash_exposure_artifact,
    verify_source_hashes,
)


def test_phase22_i_produces_draft_not_eligible_artifact(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    payload = result.payload

    assert result.status == "PASS"
    assert payload["artifact_lifecycle_status"] == "DRAFT"
    assert payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert payload["minimum_cash_ratio"] <= payload["target_cash_ratio"] <= payload["maximum_cash_ratio"]
    assert payload["minimum_gross_exposure_ratio"] <= payload["target_gross_exposure_ratio"] <= payload["maximum_gross_exposure_ratio"]
    assert payload["target_cash_ratio"] >= payload["cash_safety_minimum"]
    assert payload["target_gross_exposure_ratio"] <= payload["exposure_safety_maximum"]
    assert payload["position_sizing_decided"] is False
    assert validate_dynamic_cash_exposure_artifact(payload)["status"] == "PASS"


def test_phase22_i_schema_rejects_invalid_hierarchy_ratio_and_schema(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    for mutation in (
        lambda item: item.update({"minimum_cash_ratio": 0.3, "target_cash_ratio": 0.2}),
        lambda item: item.update({"target_gross_exposure_ratio": 0.9, "maximum_gross_exposure_ratio": 0.8}),
        lambda item: item.update({"target_cash_ratio": 1.2}),
        lambda item: item.update({"schema_version": "dynamic_cash_exposure.v999"}),
    ):
        mutated = json.loads(json.dumps(payload))
        mutation(mutated)
        with pytest.raises(DynamicCashExposureSchemaError):
            validate_dynamic_cash_exposure_artifact(mutated)


def test_phase22_i_regime_relative_relationships(tmp_path: Path) -> None:
    risk_on = _produce(tmp_path / "risk_on", market={"trend_regime": "BULL", "market_breadth": "STRONG", "volatility_regime": "LOW", "confidence": 0.9, "uncertainty": "LOW"}, policy={"risk_posture": "RISK_ON", "confidence": 0.9}).payload
    balanced = _produce(tmp_path / "balanced", market={"trend_regime": "RANGE", "market_breadth": "NEUTRAL", "volatility_regime": "NORMAL", "confidence": 0.9, "uncertainty": "LOW"}, policy={"risk_posture": "BALANCED", "confidence": 0.9}).payload
    defensive = _produce(tmp_path / "defensive", market={"trend_regime": "BEAR", "market_breadth": "WEAK", "volatility_regime": "HIGH", "confidence": 0.7, "uncertainty": "MEDIUM"}, policy={"risk_posture": "DEFENSIVE", "confidence": 0.7}).payload

    assert risk_on["target_cash_ratio"] <= balanced["target_cash_ratio"]
    assert risk_on["target_gross_exposure_ratio"] >= balanced["target_gross_exposure_ratio"]
    assert defensive["target_cash_ratio"] >= balanced["target_cash_ratio"]
    assert defensive["target_gross_exposure_ratio"] <= balanced["target_gross_exposure_ratio"]


def test_phase22_i_position_count_alignment_is_metric_not_sizing(tmp_path: Path) -> None:
    for count in (3, 5, 8):
        payload = _produce(tmp_path / f"count_{count}", position_count=count).payload
        assert payload["implied_average_position_exposure"] == round(payload["target_gross_exposure_ratio"] / count, 6)
        assert payload["position_sizing_decided"] is False
        assert payload["allocation_decided"] is False
        assert payload["quantity_decided"] is False


def test_phase29_j1_dce_consumes_canonical_resolved_opportunity_capacity(tmp_path: Path) -> None:
    payload = _build_with_capacity(tmp_path, dpc_capacity=50, opportunity_summary={})

    assert payload["producer_result_status"] == "PASS"
    assert payload["target_gross_exposure_ratio"] == 1.0
    assert "low_opportunity_capacity" not in payload["reason_codes"]
    assert payload["opportunity_capacity_authority"]["resolved_value"] == 50
    assert payload["opportunity_capacity_authority"]["source"] == "dynamic_position_count.resolved_opportunity_capacity"
    assert payload["opportunity_capacity_authority"]["legacy_alias_used"] is False


def test_phase29_j1_zero_capacity_is_valid_and_low_opportunity(tmp_path: Path) -> None:
    payload = _build_with_capacity(tmp_path, dpc_capacity=0, opportunity_summary={})

    assert payload["producer_result_status"] == "PASS"
    assert payload["target_gross_exposure_ratio"] == 0.92
    assert "low_opportunity_capacity" in payload["reason_codes"]
    assert payload["opportunity_capacity_authority"]["zero_is_valid_capacity"] is True
    assert payload["opportunity_capacity_authority"]["low_opportunity_capacity"] is True


def test_phase29_j1_missing_capacity_reviews_without_zero_default(tmp_path: Path) -> None:
    payload = _build_with_capacity(tmp_path, dpc_capacity=None, opportunity_summary={})

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["target_gross_exposure_ratio"] is None
    assert payload["target_gross_exposure_ratio_resolution"] == "UNRESOLVED"
    assert "low_opportunity_capacity" not in payload["reason_codes"]
    assert "opportunity_capacity_authority_unresolved" in payload["reason_codes"]
    assert payload["opportunity_capacity_authority"]["resolved_value"] is None
    assert payload["opportunity_capacity_authority"]["missing_capacity_semantics"] == "REVIEW_REQUIRED_NOT_ZERO"


def test_phase29_j2_legacy_alias_is_observable_but_not_active_fallback(tmp_path: Path) -> None:
    payload = _build_with_capacity(tmp_path, dpc_capacity=None, opportunity_summary={"valid_opportunity_count": 5})

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["target_gross_exposure_ratio"] is None
    assert "opportunity_capacity_authority_unresolved" in payload["reason_codes"]
    assert payload["opportunity_capacity_authority"]["legacy_alias_used"] is False
    assert payload["opportunity_capacity_authority"]["legacy_alias_active_fallback_used"] is False
    assert payload["opportunity_capacity_authority"]["legacy_fields_observed"] == {"valid_opportunity_count": 5}


def test_phase29_j1_canonical_capacity_wins_over_conflicting_legacy_alias(tmp_path: Path) -> None:
    payload = _build_with_capacity(tmp_path, dpc_capacity=50, opportunity_summary={"available_opportunity_count": 0})

    assert payload["producer_result_status"] == "PASS"
    assert payload["target_gross_exposure_ratio"] == 1.0
    assert "low_opportunity_capacity" not in payload["reason_codes"]
    assert payload["opportunity_capacity_authority"]["resolved_value"] == 50
    assert payload["opportunity_capacity_authority"]["ignored_legacy_fields"] == {"available_opportunity_count": 0}


def test_phase29_j1_capacity_contract_is_deterministic_and_preserves_policy_values(tmp_path: Path) -> None:
    first = _build_with_capacity(tmp_path / "first", dpc_capacity=50, opportunity_summary={"available_opportunity_count": 0})
    second = _build_with_capacity(tmp_path / "second", dpc_capacity=50, opportunity_summary={"available_opportunity_count": 0})
    config = _config()

    assert first["target_gross_exposure_ratio"] == second["target_gross_exposure_ratio"]
    assert first["target_cash_ratio"] == second["target_cash_ratio"]
    assert first["opportunity_capacity_authority"] == second["opportunity_capacity_authority"]
    assert config.cash_policy["baseline_target_cash_ratio"] == 0.0
    assert config.exposure_policy["baseline_target_gross_exposure_ratio"] == 1.0
    assert config.cash_policy["minimum_cash_ratio"] == 0.0
    assert config.exposure_policy["maximum_gross_exposure_ratio"] == 1.0


def test_phase29_j2_risk_on_high_opportunity_exceeds_old_ceilings_without_leverage(tmp_path: Path) -> None:
    payload = _build_with_capacity(
        tmp_path,
        dpc_capacity=50,
        opportunity_summary={},
        market={"trend_regime": "BULL", "market_breadth": "STRONG", "volatility_regime": "NORMAL", "confidence": 0.9, "uncertainty": "LOW"},
        policy={"risk_posture": "RISK_ON", "confidence": 0.9, "uncertainty": "LOW"},
    )

    assert payload["target_gross_exposure_ratio"] > 0.90
    assert payload["target_gross_exposure_ratio"] <= 1.0
    assert payload["target_cash_ratio"] == 0.0
    assert payload["fixed_cash_reserve_authority_active"] is False
    assert payload["fixed_gross_exposure_ceiling_authority_active"] is False


def test_phase29_j2_risk_off_preserves_dynamic_defensive_cash(tmp_path: Path) -> None:
    payload = _build_with_capacity(
        tmp_path,
        dpc_capacity=50,
        opportunity_summary={},
        market={"trend_regime": "BEAR", "market_breadth": "WEAK", "volatility_regime": "HIGH", "confidence": 0.7, "uncertainty": "MEDIUM"},
        policy={"risk_posture": "DEFENSIVE", "confidence": 0.7, "uncertainty": "MEDIUM"},
    )

    assert payload["target_cash_ratio"] >= 0.5
    assert payload["target_gross_exposure_ratio"] <= 0.5
    assert "DYNAMIC_DEFENSIVE_CASH" in payload["residual_cash_reason_classes"]


def test_phase29_j2_no_opportunity_preserves_cash_without_forcing_full_deployment(tmp_path: Path) -> None:
    payload = _build_with_capacity(tmp_path, dpc_capacity=0, opportunity_summary={})

    assert payload["producer_result_status"] == "PASS"
    assert payload["target_cash_ratio"] > 0.0
    assert payload["target_gross_exposure_ratio"] < 1.0
    assert "NO_ELIGIBLE_OPPORTUNITY" in payload["residual_cash_reason_classes"]


def test_phase29_j2_unknown_opportunity_authority_fails_closed(tmp_path: Path) -> None:
    payload = _build_with_capacity(tmp_path, dpc_capacity=None, opportunity_summary={})

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert payload["target_gross_exposure_ratio"] is None
    assert payload["target_cash_ratio"] is None
    assert "UNKNOWN_FAIL_CLOSED" in payload["residual_cash_reason_classes"]


def test_phase29_j2_old_cash_exposure_values_are_not_active_authority(tmp_path: Path) -> None:
    payload = _build_with_capacity(tmp_path, dpc_capacity=50, opportunity_summary={})
    config = payload["config_payload"]

    assert config["cash_policy"]["baseline_target_cash_ratio"] == 0.0
    assert config["cash_policy"]["minimum_cash_ratio"] == 0.0
    assert config["exposure_policy"]["baseline_target_gross_exposure_ratio"] == 1.0
    assert config["exposure_policy"]["maximum_gross_exposure_ratio"] == 1.0
    assert config["deprecated_fixed_policy_values"]["baseline_target_cash_ratio"] == 0.2
    assert config["deprecated_fixed_policy_values"]["classification"] == "DEPRECATED_METADATA_NOT_ACTIVE_AUTHORITY"
    assert payload["strategy_minimum_cash_floor_active"] is False
    assert payload["strategy_maximum_gross_exposure_ceiling_active"] is False


def test_phase29_j2_pending_reservation_and_compound_equity_are_preserved(tmp_path: Path) -> None:
    payload = _build_with_capacity(
        tmp_path,
        dpc_capacity=50,
        opportunity_summary={},
        current_cash=1_500_000,
        current_market_value=500_000,
        pending_reserved_cash=200_000,
    )

    assert payload["portfolio_total_equity"] == 2_000_000
    assert payload["pending_reserved_cash"] == 200_000
    assert payload["net_available_cash"] == 1_300_000
    assert "PENDING_RESERVED" in payload["residual_cash_reason_classes"]


def test_phase29_j2_safety_cash_exposure_is_no_fixed_reserve_no_leverage(tmp_path: Path) -> None:
    payload = _build_with_capacity(tmp_path, dpc_capacity=50, opportunity_summary={})

    assert payload["cash_safety_minimum"] == 0.0
    assert payload["exposure_safety_maximum"] == 1.0
    assert payload["safety_minimum_cash_floor_active"] is False
    assert payload["safety_maximum_gross_exposure_ceiling_active"] is False
    assert payload["target_gross_exposure_ratio"] <= payload["cash_equity_no_leverage_cap"]


def test_phase22_i_safety_status_and_limits(tmp_path: Path) -> None:
    review, _ = build_dynamic_cash_exposure_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy", summary=_policy()),
        dynamic_position_count_summary=_summary(tmp_path, "count", summary={"target_position_count": 8, "confidence": 0.9}),
        candidate_summary=_summary(tmp_path, "candidate", summary={"available_candidate_count": 8}),
        opportunity_summary=_summary(tmp_path, "opportunity", summary={"available_opportunity_count": 8}),
        current_cash_summary=_summary(tmp_path, "cash", summary={"current_cash_ratio": 0.2}),
        current_exposure_summary=_summary(tmp_path, "exposure", summary={"current_gross_exposure_ratio": 0.8}),
        pending_reservation_summary=_summary(tmp_path, "pending", summary={}),
        safety_limit_summary=_summary(tmp_path, "safety", status="REVIEW_REQUIRED", summary={}),
        config=_config(),
    )
    assert review["producer_result_status"] == "REVIEW_REQUIRED"
    assert "safety_cash_exposure_limit_review_required" in review["reason_codes"]

    constrained, _ = build_dynamic_cash_exposure_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_bad", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy_bad", summary=_policy()),
        dynamic_position_count_summary=_summary(tmp_path, "count_bad", summary={"target_position_count": 8, "resolved_opportunity_capacity": 8, "confidence": 0.9}),
        candidate_summary=_summary(tmp_path, "candidate_bad", summary={"available_candidate_count": 8}),
        opportunity_summary=_summary(tmp_path, "opportunity_bad", summary={"available_opportunity_count": 8}),
        current_cash_summary=_summary(tmp_path, "cash_bad", summary={"current_cash_ratio": 0.2}),
        current_exposure_summary=_summary(tmp_path, "exposure_bad", summary={"current_gross_exposure_ratio": 0.8}),
        pending_reservation_summary=_summary(tmp_path, "pending_bad", summary={}),
        safety_limit_summary=_summary(tmp_path, "safety_bad", summary={"minimum_cash_ratio": 0.3, "maximum_gross_exposure_ratio": 0.7}),
        config=_config(),
    )
    assert constrained["producer_result_status"] == "PASS"
    assert constrained["target_cash_ratio"] >= 0.3
    assert constrained["target_gross_exposure_ratio"] <= 0.7

    bad, _ = build_dynamic_cash_exposure_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_bad_conflict", summary=_market()),
        portfolio_policy_summary=_summary(tmp_path, "policy_bad_conflict", summary=_policy()),
        dynamic_position_count_summary=_summary(tmp_path, "count_bad_conflict", summary={"target_position_count": 8, "resolved_opportunity_capacity": 8, "confidence": 0.9}),
        candidate_summary=_summary(tmp_path, "candidate_bad_conflict", summary={"available_candidate_count": 8}),
        opportunity_summary=_summary(tmp_path, "opportunity_bad_conflict", summary={"available_opportunity_count": 8}),
        current_cash_summary=_summary(tmp_path, "cash_bad_conflict", summary={"current_cash_ratio": 0.2}),
        current_exposure_summary=_summary(tmp_path, "exposure_bad_conflict", summary={"current_gross_exposure_ratio": 0.8}),
        pending_reservation_summary=_summary(tmp_path, "pending_bad_conflict", summary={}),
        safety_limit_summary=_summary(tmp_path, "safety_bad_conflict", summary={"minimum_cash_ratio": 0.6, "maximum_gross_exposure_ratio": 0.6}),
        config=_config(),
    )
    assert bad["producer_result_status"] == "BLOCK"
    assert "inconsistent_safety_cash_exposure_limits" in bad["reason_codes"]


def test_phase22_i_status_hash_fixture_and_runtime_preservation(tmp_path: Path) -> None:
    payload, _ = build_dynamic_cash_exposure_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_review", status="REVIEW_REQUIRED", summary={}),
        portfolio_policy_summary=_summary(tmp_path, "policy_review", summary=_policy()),
        dynamic_position_count_summary=_summary(tmp_path, "count_review", summary={"target_position_count": 8}),
        candidate_summary=_summary(tmp_path, "candidate_review", summary={"available_candidate_count": 8}),
        opportunity_summary=_summary(tmp_path, "opportunity_review", summary={"available_opportunity_count": 8}),
        current_cash_summary=_summary(tmp_path, "cash_review", summary={"current_cash_ratio": 0.2}),
        current_exposure_summary=_summary(tmp_path, "exposure_review", summary={"current_gross_exposure_ratio": 0.8}),
        pending_reservation_summary=_summary(tmp_path, "pending_review", summary={}),
        safety_limit_summary=_safety_summary(tmp_path),
        config=None,
    )
    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "dynamic_cash_exposure_config_required" in payload["reason_codes"]

    result = _produce(tmp_path / "ok")
    assert result.payload["artifact_hash"] == dynamic_cash_exposure_hash(result.payload)
    assert verify_source_hashes(result.payload)["status"] == "PASS"
    fixture = load_dynamic_cash_exposure_fixture(result.artifact_path)
    assert fixture["schema_version"] == "dynamic_cash_exposure.v1"
    with pytest.raises(DynamicCashExposureConsumerError):
        load_dynamic_cash_exposure_fixture(result.artifact_path, for_production=True)

    policy = load_capital_deployment_policy("configs/runtime_v2/capital_deployment.json")
    manifest_fields = policy.to_manifest_fields()
    assert manifest_fields["legacy_cash_config_used"] is False
    assert manifest_fields["legacy_exposure_config_used"] is False
    assert manifest_fields["cash_exposure_fallback_used"] is False
    assert result.payload["shadow_comparison"]["runtime_behavior_changed"] is False


def _produce(tmp_path: Path, *, market: dict[str, object] | None = None, policy: dict[str, object] | None = None, position_count: int = 8):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return produce_dynamic_cash_exposure_artifact(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market", summary=market or _market()),
        portfolio_policy_summary=_summary(tmp_path, "policy", summary=policy or _policy()),
        dynamic_position_count_summary=_summary(tmp_path, "count", summary={"target_position_count": position_count, "resolved_opportunity_capacity": position_count, "confidence": 0.9}),
        candidate_summary=_summary(tmp_path, "candidate", summary={"available_candidate_count": position_count}),
        opportunity_summary=_summary(tmp_path, "opportunity", summary={"available_opportunity_count": position_count}),
        current_cash_summary=_summary(tmp_path, "cash", summary={"current_cash_ratio": 0.2}),
        current_exposure_summary=_summary(tmp_path, "exposure", summary={"current_gross_exposure_ratio": 0.8}),
        pending_reservation_summary=_summary(tmp_path, "pending", summary={}),
        safety_limit_summary=_safety_summary(tmp_path),
        config=_config(),
        output_path=default_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _build_with_capacity(
    tmp_path: Path,
    *,
    dpc_capacity: int | None,
    opportunity_summary: dict[str, object],
    market: dict[str, object] | None = None,
    policy: dict[str, object] | None = None,
    current_cash: float = 200000,
    current_market_value: float = 800000,
    pending_reserved_cash: float = 0.0,
) -> dict[str, object]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    dpc_summary = {"target_position_count": 8, "confidence": 0.9}
    if dpc_capacity is not None:
        dpc_summary["resolved_opportunity_capacity"] = dpc_capacity
    payload, _ = build_dynamic_cash_exposure_payload(
        business_date="2026-07-15",
        market_context_summary=_summary(tmp_path, "market_j1", summary=market or _market()),
        portfolio_policy_summary=_summary(tmp_path, "policy_j1", summary=policy or _policy()),
        dynamic_position_count_summary=_summary(tmp_path, "count_j1", summary=dpc_summary),
        candidate_summary=_summary(tmp_path, "candidate_j1", summary={"available_candidate_count": 8}),
        opportunity_summary=_summary(tmp_path, "opportunity_j1", summary=opportunity_summary),
        current_cash_summary=_summary(tmp_path, "cash_j1", summary={"current_cash_ratio": 0.2, "current_cash": current_cash}),
        current_exposure_summary=_summary(tmp_path, "exposure_j1", summary={"current_gross_exposure_ratio": 0.8, "current_market_value": current_market_value}),
        pending_reservation_summary=_summary(tmp_path, "pending_j1", summary={"pending_reserved_cash": pending_reserved_cash} if pending_reserved_cash else {}),
        safety_limit_summary=_safety_summary(tmp_path),
        config=_config(),
    )
    return payload


def _config():
    return load_dynamic_cash_exposure_config("configs/strategy/dynamic_cash_exposure.json")


def _market() -> dict[str, object]:
    return {"trend_regime": "RANGE", "market_breadth": "NEUTRAL", "volatility_regime": "NORMAL", "confidence": 0.9, "uncertainty": "LOW"}


def _policy() -> dict[str, object]:
    return {"risk_posture": "BALANCED", "confidence": 0.9, "uncertainty": "LOW"}


def _safety_summary(tmp_path: Path) -> CashExposureSourceSummary:
    limits = load_portfolio_safety_limits("configs/safety/portfolio_limits.json", legacy_active_max_positions=5)
    return _summary(tmp_path, "safety", summary={"minimum_cash_ratio": limits.minimum_cash_ratio, "maximum_gross_exposure_ratio": limits.maximum_gross_exposure_ratio})


def _summary(tmp_path: Path, kind: str, *, status: str = "PASS", business_date: str = "2026-07-15", feature_date: str = "2026-07-15", summary: dict[str, object] | None = None) -> CashExposureSourceSummary:
    path = tmp_path / f"{kind}_summary.json"
    payload = {"kind": kind, "status": status, "business_date": business_date, "feature_date": feature_date, "summary": summary or {}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return CashExposureSourceSummary(status, business_date, feature_date, str(path), dce.sha256_file(path), summary or {})
