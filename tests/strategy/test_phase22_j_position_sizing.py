from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy
from ai_fund_lab_v2.runtime_v2.safety.portfolio_limits import load_portfolio_safety_limits
from ai_fund_lab_v2.strategy import position_sizing as ps
from ai_fund_lab_v2.strategy.position_sizing import (
    PositionSizingConsumerError,
    PositionSizingSchemaError,
    PositionSizingSourceSummary,
    build_position_sizing_payload,
    default_runtime_artifact_path,
    load_position_sizing_config,
    load_position_sizing_fixture,
    position_sizing_hash,
    produce_position_sizing_artifact,
    validate_position_sizing_artifact,
    verify_source_hashes,
)


def test_phase22_j_produces_sizing_intent_without_quantity_or_runtime_connection(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    payload = result.payload

    assert result.status == "PASS"
    assert payload["artifact_lifecycle_status"] == "DRAFT"
    assert payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert payload["concrete_target_weight_decided"] is True
    assert payload["target_notional_decided"] is True
    assert payload["share_quantity_decided"] is False
    assert payload["lot_rounding_decided"] is False
    assert payload["runtime_switch_performed"] is False
    assert payload["total_target_weight"] <= payload["target_gross_exposure_ratio"]
    assert all("quantity" not in item for item in payload["positions"])
    assert validate_position_sizing_artifact(payload)["status"] == "PASS"


def test_phase22_j_schema_rejects_invalid_weights_notional_quantity_and_lot(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    for mutation in (
        lambda item: item["positions"][0].update({"target_weight": -0.1}),
        lambda item: item.update({"total_target_weight": item["target_gross_exposure_ratio"] + 0.1}),
        lambda item: item["positions"][0].update({"target_notional": -1}),
        lambda item: item["positions"][0].update({"quantity": 100}),
        lambda item: item.update({"lot_size": 100}),
    ):
        mutated = json.loads(json.dumps(payload))
        mutation(mutated)
        with pytest.raises(PositionSizingSchemaError):
            validate_position_sizing_artifact(mutated)


def test_phase22_j_base_allocation_count_and_exposure(tmp_path: Path) -> None:
    for count, exposure in ((3, 0.6), (5, 0.8), (8, 0.8)):
        payload = _produce(tmp_path / f"{count}_{exposure}", target_count=count, exposure=exposure, rows=_rows(count)).payload
        assert payload["target_position_count"] == count
        assert payload["target_gross_exposure_ratio"] == exposure
        assert payload["positions"][0]["base_weight"] == round(exposure / count, 6)
        assert payload["total_target_weight"] <= exposure


def test_phase22_j_quality_and_volatility_adjustments_are_relative_and_fail_closed(tmp_path: Path) -> None:
    rows = [
        _row("1001", score=0.9, volatility=0.02),
        _row("1002", score=0.2, volatility=0.02),
        _row("1003", score=0.7, volatility=0.06),
    ]
    payload = _produce(tmp_path, rows=rows).payload
    by_code = {item["security_code"]: item for item in payload["positions"]}
    assert by_code["1001"]["quality_adjustment"] >= by_code["1002"]["quality_adjustment"]
    assert by_code["1001"]["target_weight"] >= by_code["1002"]["target_weight"]
    assert by_code["1003"]["volatility_adjustment"] <= by_code["1001"]["volatility_adjustment"]

    missing_quality = _produce(tmp_path / "missing_quality", rows=[_row("2001", score=None)]).payload
    assert missing_quality["producer_result_status"] == "REVIEW_REQUIRED"
    assert missing_quality["positions"][0]["sizing_status"] == "QUALITY_UNAVAILABLE"

    missing_vol = _produce(tmp_path / "missing_vol", rows=[_row("2002", volatility=None)]).payload
    assert missing_vol["producer_result_status"] == "REVIEW_REQUIRED"
    assert missing_vol["positions"][0]["sizing_status"] == "VOLATILITY_UNAVAILABLE"


def test_phase22_j_pm_intent_adjustment_without_sell_quantity(tmp_path: Path) -> None:
    rows = [
        _row("3001", membership="ADD_CANDIDATE", pm_action="NEW", current_weight=0.0),
        _row("3002", membership="RETAIN", pm_action="HOLD", current_weight=0.08),
        _row("3003", membership="RETAIN", pm_action="ADD", current_weight=0.05),
        _row("3004", membership="REDUCE_CANDIDATE", pm_action="REDUCE", current_weight=0.12),
        _row("3005", membership="REMOVE_CANDIDATE", pm_action="EXIT", current_weight=0.1),
    ]
    payload = _produce(tmp_path, rows=rows, target_count=5).payload
    by_code = {item["security_code"]: item for item in payload["positions"]}
    assert by_code["3005"]["target_weight"] == 0
    assert by_code["3004"]["target_weight"] < by_code["3004"]["current_weight"]
    assert by_code["3003"]["target_weight"] > by_code["3003"]["current_weight"]
    assert payload["share_quantity_decided"] is False
    assert payload["lot_rounding_decided"] is False


def test_phase22_j_minimum_notional_and_high_price_withheld(tmp_path: Path) -> None:
    exact = _produce(tmp_path / "exact", rows=[_row("4001", price=490.1961)], target_count=8, exposure=0.4).payload
    assert exact["positions"][0]["target_notional"] >= exact["positions"][0]["minimum_meaningful_notional"]

    high_price = _produce(tmp_path / "high", rows=[_row("4002", price=5000)], target_count=8, exposure=0.4).payload
    assert high_price["producer_result_status"] == "REVIEW_REQUIRED"
    assert high_price["positions"][0]["sizing_status"] == "MINIMUM_NOTIONAL_UNMET"
    assert high_price["positions"][0]["target_weight"] == 0


def test_phase22_j_safety_status_hash_fixture_pit_and_runtime_preservation(tmp_path: Path) -> None:
    review, _ = build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc", rows=_rows(2)),
        capital_deployment_summary=_summary(tmp_path, "cd"),
        dynamic_position_count_summary=_summary(tmp_path, "dpc", summary={"target_position_count": 2}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce", summary={"target_gross_exposure_ratio": 0.4}),
        position_management_summary=_summary(tmp_path, "pm"),
        opportunity_summary=_summary(tmp_path, "opp"),
        current_position_summary=_summary(tmp_path, "cur", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(tmp_path, "pv"),
        safety_limit_summary=_summary(tmp_path, "safety", status="REVIEW_REQUIRED", summary={}),
        config=_config(),
    )
    assert review["producer_result_status"] == "REVIEW_REQUIRED"
    assert "safety_concentration_limit_review_required" in review["reason_codes"]

    bad_safety, _ = build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc_bad", rows=_rows(1)),
        capital_deployment_summary=_summary(tmp_path, "cd_bad"),
        dynamic_position_count_summary=_summary(tmp_path, "dpc_bad", summary={"target_position_count": 1}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce_bad", summary={"target_gross_exposure_ratio": 0.3}),
        position_management_summary=_summary(tmp_path, "pm_bad"),
        opportunity_summary=_summary(tmp_path, "opp_bad"),
        current_position_summary=_summary(tmp_path, "cur_bad", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(tmp_path, "pv_bad"),
        safety_limit_summary=_summary(tmp_path, "safety_bad", summary={"maximum_position_weight": 0.2}),
        config=_config(),
    )
    assert bad_safety["producer_result_status"] == "BLOCK"

    future, _ = build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc_future", rows=_rows(1), feature_date="2026-07-16"),
        capital_deployment_summary=_summary(tmp_path, "cd_future"),
        dynamic_position_count_summary=_summary(tmp_path, "dpc_future", summary={"target_position_count": 1}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce_future", summary={"target_gross_exposure_ratio": 0.3}),
        position_management_summary=_summary(tmp_path, "pm_future"),
        opportunity_summary=_summary(tmp_path, "opp_future"),
        current_position_summary=_summary(tmp_path, "cur_future", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(tmp_path, "pv_future"),
        safety_limit_summary=_safety(tmp_path),
        config=_config(),
    )
    assert future["producer_result_status"] == "BLOCK"

    result = _produce(tmp_path / "ok")
    assert result.payload["artifact_hash"] == position_sizing_hash(result.payload)
    assert verify_source_hashes(result.payload)["status"] == "PASS"
    assert load_position_sizing_fixture(result.artifact_path)["schema_version"] == "position_sizing.v1"
    with pytest.raises(PositionSizingConsumerError):
        load_position_sizing_fixture(result.artifact_path, for_production=True)

    policy = load_capital_deployment_policy("configs/runtime_v2/capital_deployment.json")
    assert policy.max_position_weight == 0.2
    assert policy.max_positions == 5
    assert policy.target_investment_ratio == 0.85
    assert result.payload["shadow_comparison"]["runtime_behavior_changed"] is False


def test_phase22_pw_configured_max_above_safety_cap_is_distinct_from_produced_weight(tmp_path: Path) -> None:
    payload, _ = build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc", rows=[]),
        capital_deployment_summary=_summary(tmp_path, "cd"),
        dynamic_position_count_summary=_summary(tmp_path, "dpc", summary={"target_position_count": 0}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce", summary={"target_gross_exposure_ratio": 0.0}),
        position_management_summary=_summary(tmp_path, "pm"),
        opportunity_summary=_summary(tmp_path, "opp"),
        current_position_summary=_summary(tmp_path, "cur", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(tmp_path, "pv"),
        safety_limit_summary=_summary(tmp_path, "safety", summary={"maximum_position_weight": 0.25}),
        config=_custom_config(strategy_maximum_position_weight=0.3),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert payload["positions"] == []
    assert payload["total_target_weight"] == 0
    assert "configured_max_position_weight_above_safety_cap" in payload["reason_codes"]
    assert "strategy_position_weight_above_safety_cap" not in payload["reason_codes"]
    assert "produced_position_weight_above_safety_cap" not in payload["reason_codes"]


def test_phase22_qa_reads_nested_canonical_safety_concentration_authority(tmp_path: Path) -> None:
    limits = load_portfolio_safety_limits("configs/safety/portfolio_limits.json", legacy_active_max_positions=5)
    payload, _ = build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc", rows=_rows(5)),
        capital_deployment_summary=_summary(tmp_path, "cd"),
        dynamic_position_count_summary=_summary(tmp_path, "dpc", summary={"target_position_count": 5}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce", summary={"target_gross_exposure_ratio": 0.8}),
        position_management_summary=_summary(tmp_path, "pm"),
        opportunity_summary=_summary(tmp_path, "opp"),
        current_position_summary=_summary(tmp_path, "cur", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(tmp_path, "pv"),
        safety_limit_summary=_summary(tmp_path, "safety", summary=limits.to_contract_payload()),
        config=_config(),
    )

    assert payload["producer_result_status"] == "PASS"
    assert payload["strategy_maximum_position_weight"] == 0.18
    assert payload["safety_maximum_position_weight"] == 0.25
    assert payload["safety_maximum_position_weight_source"].endswith("#concentration.maximum_position_weight")
    assert payload["safety_authority_status"] == "PASS"
    assert payload["effective_maximum_position_weight"] == 0.18
    assert payload["effective_maximum_position_weight_derivation"] == "min(strategy_maximum_position_weight, safety_maximum_position_weight)"
    assert payload["explicit_zero_cap"] is False
    assert payload["emergency_brake_active"] is False
    assert payload["dynamic_position_count"] == 5
    assert payload["dynamic_cash_exposure"] == 0.8
    assert payload["aggregate_exposure_cap"] == 0.8
    assert payload["positions_sized"] > 0
    assert payload["total_target_weight"] > 0
    assert "configured_max_position_weight_above_safety_cap" not in payload["reason_codes"]


def test_phase22_qa_missing_safety_authority_is_not_converted_to_zero(tmp_path: Path) -> None:
    payload, _ = build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc", rows=_rows(2)),
        capital_deployment_summary=_summary(tmp_path, "cd"),
        dynamic_position_count_summary=_summary(tmp_path, "dpc", summary={"target_position_count": 2}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce", summary={"target_gross_exposure_ratio": 0.4}),
        position_management_summary=_summary(tmp_path, "pm"),
        opportunity_summary=_summary(tmp_path, "opp"),
        current_position_summary=_summary(tmp_path, "cur", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(tmp_path, "pv"),
        safety_limit_summary=_summary(tmp_path, "safety", summary={"authority_owner": "Safety Layer"}),
        config=_config(),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert payload["safety_maximum_position_weight"] is None
    assert payload["effective_maximum_position_weight"] is None
    assert payload["safety_authority_status"] == "BLOCK"
    assert "missing_safety_maximum_position_weight_authority" in payload["reason_codes"]
    assert "configured_max_position_weight_above_safety_cap" not in payload["reason_codes"]
    assert validate_position_sizing_artifact(payload)["status"] == "PASS"


def test_phase22_qa_explicit_zero_safety_cap_requires_authority(tmp_path: Path) -> None:
    without_authority, _ = build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc_zero_missing", rows=_rows(1)),
        capital_deployment_summary=_summary(tmp_path, "cd_zero_missing"),
        dynamic_position_count_summary=_summary(tmp_path, "dpc_zero_missing", summary={"target_position_count": 1}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce_zero_missing", summary={"target_gross_exposure_ratio": 0.2}),
        position_management_summary=_summary(tmp_path, "pm_zero_missing"),
        opportunity_summary=_summary(tmp_path, "opp_zero_missing"),
        current_position_summary=_summary(tmp_path, "cur_zero_missing", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(tmp_path, "pv_zero_missing"),
        safety_limit_summary=_summary(tmp_path, "safety_zero_missing", summary={"maximum_position_weight": 0.0}),
        config=_config(),
    )
    assert without_authority["producer_result_status"] == "BLOCK"
    assert "explicit_zero_safety_cap_without_authority" in without_authority["reason_codes"]

    explicit_zero, _ = build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc_zero", rows=_rows(1)),
        capital_deployment_summary=_summary(tmp_path, "cd_zero"),
        dynamic_position_count_summary=_summary(tmp_path, "dpc_zero", summary={"target_position_count": 1}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce_zero", summary={"target_gross_exposure_ratio": 0.2}),
        position_management_summary=_summary(tmp_path, "pm_zero"),
        opportunity_summary=_summary(tmp_path, "opp_zero"),
        current_position_summary=_summary(tmp_path, "cur_zero", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(tmp_path, "pv_zero"),
        safety_limit_summary=_summary(tmp_path, "safety_zero", summary={"maximum_position_weight": 0.0, "emergency_brake_active": True}),
        config=_config(),
    )
    assert explicit_zero["producer_result_status"] == "PASS"
    assert explicit_zero["safety_maximum_position_weight"] == 0
    assert explicit_zero["effective_maximum_position_weight"] == 0
    assert explicit_zero["explicit_zero_cap"] is True
    assert explicit_zero["emergency_brake_active"] is True
    assert explicit_zero["total_target_weight"] == 0


def test_phase22_pw_reason_codes_distinguish_actual_weight_and_aggregate_exposure(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "reason_contract").payload

    produced_overweight = json.loads(json.dumps(payload))
    produced_overweight["positions"][0]["target_weight"] = produced_overweight["safety_maximum_position_weight"] + 0.01
    with pytest.raises(PositionSizingSchemaError) as actual_error:
        validate_position_sizing_artifact(produced_overweight)
    assert "target_weight_above_safety_cap:0" in str(actual_error.value)

    aggregate_over = json.loads(json.dumps(payload))
    aggregate_over["total_target_weight"] = aggregate_over["target_gross_exposure_ratio"] + 0.01
    with pytest.raises(PositionSizingSchemaError) as aggregate_error:
        validate_position_sizing_artifact(aggregate_over)
    assert "aggregate_target_weight_above_exposure_cap" in str(aggregate_error.value)


def test_phase22_pw_valid_configuration_has_no_cap_violation_reason(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "valid_contract").payload

    assert payload["producer_result_status"] == "PASS"
    assert "configured_max_position_weight_above_safety_cap" not in payload["reason_codes"]
    assert "produced_position_weight_above_safety_cap" not in payload["reason_codes"]
    assert "aggregate_target_weight_above_exposure_cap" not in payload["reason_codes"]


def _produce(tmp_path: Path, *, rows: list[dict[str, object]] | None = None, target_count: int = 5, exposure: float = 0.8):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return produce_position_sizing_artifact(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc", rows=rows or _rows(target_count)),
        capital_deployment_summary=_summary(tmp_path, "cd"),
        dynamic_position_count_summary=_summary(tmp_path, "dpc", summary={"target_position_count": target_count}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce", summary={"target_gross_exposure_ratio": exposure}),
        position_management_summary=_summary(tmp_path, "pm"),
        opportunity_summary=_summary(tmp_path, "opp"),
        current_position_summary=_summary(tmp_path, "cur", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(tmp_path, "pv"),
        safety_limit_summary=_safety(tmp_path),
        config=_config(),
        output_path=default_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _config():
    return load_position_sizing_config("configs/strategy/position_sizing.json")


def _custom_config(*, strategy_maximum_position_weight: float) -> ps.PositionSizingConfig:
    base = _config()
    return ps.PositionSizingConfig(
        config_version=base.config_version,
        config_source=base.config_source,
        sizing_method=base.sizing_method,
        opportunity_adjustment=base.opportunity_adjustment,
        volatility_adjustment=base.volatility_adjustment,
        pm_intent_adjustment=base.pm_intent_adjustment,
        minimum_meaningful_notional=base.minimum_meaningful_notional,
        strategy_maximum_position_weight=strategy_maximum_position_weight,
        safety_concentration_reference=base.safety_concentration_reference,
    )


def _safety(tmp_path: Path) -> PositionSizingSourceSummary:
    limits = load_portfolio_safety_limits("configs/safety/portfolio_limits.json", legacy_active_max_positions=5)
    return _summary(tmp_path, "safety", summary=limits.to_contract_payload())


def _rows(count: int) -> list[dict[str, object]]:
    return [_row(str(1000 + index), score=0.5 + index * 0.02, volatility=0.03, priority=index) for index in range(1, count + 1)]


def _row(code: str, *, score: float | None = 0.7, volatility: float | None = 0.03, price: float = 600.0, membership: str = "ADD_CANDIDATE", pm_action: str = "NEW", current_weight: float = 0.0, priority: int = 1) -> dict[str, object]:
    row = {
        "security_code": code,
        "position_reference": f"member-{code}",
        "membership_intent": membership,
        "pm_action": pm_action,
        "current_weight": current_weight,
        "opportunity_confidence": 0.9,
        "confidence": 0.9,
        "reference_price": price,
        "allocation_priority": priority,
    }
    if score is not None:
        row["opportunity_score"] = score
    if volatility is not None:
        row["volatility"] = volatility
    return row


def _summary(tmp_path: Path, kind: str, *, status: str = "PASS", business_date: str = "2026-07-15", feature_date: str = "2026-07-15", rows: list[dict[str, object]] | None = None, summary: dict[str, object] | None = None) -> PositionSizingSourceSummary:
    path = tmp_path / f"{kind}_summary.json"
    payload = {"kind": kind, "status": status, "business_date": business_date, "feature_date": feature_date, "rows": rows or [], "summary": summary or {}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return PositionSizingSourceSummary(status, business_date, feature_date, str(path), ps.sha256_file(path), tuple(rows or ()), summary or {})
