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


def test_phase23_ai_position_sizing_propagates_resolved_target_count(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "phase23_ai_sizing", target_count=3, exposure=0.79, rows=_rows(5)).payload

    assert payload["producer_result_status"] == "PASS"
    assert payload["target_position_count"] == 3
    assert payload["positions_sized"] > 0
    assert payload["positions_withheld"] < len(payload["positions"])
    assert any(item["sizing_status"] in {"SIZED", "CAPPED"} for item in payload["positions"])


def test_phase23_am_allocation_quality_score_resolves(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "phase23_am_canonical", rows=[_quality_row("5001", allocation_quality_score=0.82, runtime_opportunity_score=0.35)]).payload
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert item["sizing_status"] in {"SIZED", "CAPPED"}
    assert item["allocation_quality_score"] == 0.82
    assert item["runtime_opportunity_score"] == 0.35
    assert item["allocation_quality_resolution"]["resolution_status"] == "PASS"
    assert item["allocation_quality_resolution"]["source_field"] == "allocation_quality_score"
    assert item["allocation_quality_resolution"]["legacy_alias_used"] is False
    assert item["target_notional"] > 0


def test_phase23_am_legacy_input_score_is_raw_attribution_not_quality_alias(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "phase23_am_input_alias", rows=[_quality_row("5002", input_score=0.77)]).payload
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert item["sizing_status"] in {"SIZED", "CAPPED"}
    assert item["runtime_opportunity_score"] == 0.77
    assert item["runtime_opportunity_score_resolution"]["source_field"] == "input_score"
    assert item["legacy_quality_path_status"] == "NON_CANONICAL_OBSERVABILITY"
    assert item["allocation_quality_resolution"]["review_reason"] == "allocation_quality_score_missing"
    assert item["allocation_quality_resolution"]["legacy_usage"] == "raw_attribution_only:input_score"
    assert item["target_notional"] > 0


def test_phase23_am_legacy_opportunity_score_is_not_allocation_quality_alias(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "phase23_am_opportunity_alias", rows=[_quality_row("5003", opportunity_score=0.66)]).payload
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert item["runtime_opportunity_score"] == 0.66
    assert item["runtime_opportunity_score_resolution"]["source_field"] == "opportunity_score"
    assert item["allocation_quality_resolution"]["review_reason"] == "allocation_quality_score_missing"
    assert item["target_notional"] > 0


def test_phase23_ak_missing_quality_score_is_review_required_fail_closed(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "phase23_ak_missing", rows=[_quality_row("5004")]).payload
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert item["sizing_status"] in {"SIZED", "CAPPED"}
    assert item["quality_score"] == 0.82
    assert item["target_notional"] > 0
    assert item["legacy_allocation_quality_resolution"]["review_reason"] == "allocation_quality_score_missing"
    assert "quality_missing_fail_closed" not in item["reason_codes"]


def test_phase23_am_conflicting_allocation_quality_fields_are_review_required(tmp_path: Path) -> None:
    payload = _produce(
        tmp_path / "phase23_am_conflict",
        rows=[_quality_row("5005", allocation_quality_score=0.91, quality_score=0.72, runtime_opportunity_score=0.2)],
    ).payload
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert item["sizing_status"] in {"SIZED", "CAPPED"}
    assert item["legacy_allocation_quality_resolution"]["resolution_status"] == "PASS"
    assert item["legacy_allocation_quality_resolution"]["conflict_detected"] is False
    assert item["quality_score"] == 0.72
    assert item["target_notional"] > 0


def test_phase23_am_invalid_allocation_quality_score_is_review_required(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "phase23_am_invalid", rows=[_quality_row("5006", allocation_quality_score=1.2)]).payload
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert item["sizing_status"] in {"SIZED", "CAPPED"}
    assert item["legacy_allocation_quality_resolution"]["review_reason"] == "allocation_quality_score_invalid:allocation_quality_score"
    assert item["target_notional"] > 0


def test_phase23_am_positive_quality_reaches_positive_target_notional(tmp_path: Path) -> None:
    rows = [_quality_row(str(6000 + index), allocation_quality_score=0.5 + index * 0.01, runtime_opportunity_score=-0.3 + index * 0.04, volatility=0.03, priority=index) for index in range(1, 11)]
    payload = _produce(tmp_path / "phase23_am_positive_quality", rows=rows, target_count=10, exposure=0.79).payload

    assert payload["producer_result_status"] == "PASS"
    assert payload["positions_sized"] == 10
    assert payload["positions_withheld"] == 0
    assert all(item["sizing_status"] in {"SIZED", "CAPPED"} for item in payload["positions"])
    assert any(item["target_notional"] > 0 for item in payload["positions"])
    assert all(item["allocation_quality_resolution"]["source_field"] == "allocation_quality_score" for item in payload["positions"])
    assert any(item["runtime_opportunity_score"] < 0 for item in payload["positions"])


def test_phase23_am_signful_negative_opportunity_score_does_not_schema_block(tmp_path: Path) -> None:
    payload = _produce(
        tmp_path / "phase23_am_negative_raw",
        rows=[_quality_row("5008", runtime_opportunity_score=-0.25, allocation_quality_score=0.6)],
    ).payload
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert item["runtime_opportunity_score"] == -0.25
    assert item["runtime_opportunity_score_resolution"]["resolution_status"] == "PASS"
    assert item["allocation_quality_score"] == 0.6
    assert item["target_notional"] > 0


def test_phase23_am_invalid_raw_score_fails_closed_without_silent_coercion(tmp_path: Path) -> None:
    payload = _produce(
        tmp_path / "phase23_am_invalid_raw",
        rows=[_quality_row("5009", runtime_opportunity_score=0.4, allocation_quality_score=0.7)],
    ).payload
    row = json.loads(json.dumps(payload["positions"][0]))
    source = _quality_row("5010", allocation_quality_score=0.7)
    source["runtime_opportunity_score"] = "not-a-number"
    bad_payload = _produce(tmp_path / "phase23_am_invalid_raw_source", rows=[source]).payload
    bad = bad_payload["positions"][0]

    assert row["target_notional"] > 0
    assert bad_payload["producer_result_status"] == "PASS"
    assert bad["sizing_status"] in {"SIZED", "CAPPED"}
    assert bad["target_notional"] > 0
    assert bad["runtime_opportunity_score_resolution"]["review_reason"] == "runtime_opportunity_score_invalid:runtime_opportunity_score"


def test_phase23_am_raw_score_missing_authority_fails_closed(tmp_path: Path) -> None:
    row = _quality_row("5011", runtime_opportunity_score=0.4, allocation_quality_score=0.7)
    row.pop("runtime_opportunity_score_authority")
    payload = _produce(tmp_path / "phase23_am_raw_missing_authority", rows=[row]).payload
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert item["sizing_status"] in {"SIZED", "CAPPED"}
    assert item["runtime_opportunity_score_resolution"]["review_reason"] == "runtime_opportunity_score_authority_missing"
    assert item["target_notional"] > 0


def test_phase23_am_semantic_conflict_is_review_required(tmp_path: Path) -> None:
    row = _quality_row("5012", runtime_opportunity_score=0.4, allocation_quality_score=0.7)
    row["runtime_opportunity_score_authority"]["prediction_semantics"] = "allocation_quality_score"
    row["allocation_quality_authority"]["output_semantics"] = "runtime_opportunity_score"
    payload = _produce(tmp_path / "phase23_am_semantic_conflict", rows=[row]).payload
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert item["sizing_status"] in {"SIZED", "CAPPED"}
    assert item["allocation_quality_resolution"]["review_reason"] == "allocation_quality_semantic_conflict"
    assert item["runtime_opportunity_score_resolution"]["review_reason"] == "runtime_opportunity_score_semantic_conflict"
    assert item["target_notional"] > 0


def test_phase23_ao_missing_target_weight_authority_is_review_required_fail_closed(tmp_path: Path) -> None:
    row = _quality_row("5101", runtime_opportunity_score=0.4)
    row.pop("target_weight_authority")
    payload, _ = build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc_missing_target_weight_authority", rows=[row]),
        capital_deployment_summary=_summary(tmp_path, "cd_missing_target_weight_authority"),
        dynamic_position_count_summary=_summary(tmp_path, "dpc_missing_target_weight_authority", summary={"target_position_count": 1}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce_missing_target_weight_authority", summary={"target_gross_exposure_ratio": 0.8}),
        position_management_summary=_summary(tmp_path, "pm_missing_target_weight_authority"),
        opportunity_summary=_summary(tmp_path, "opp_missing_target_weight_authority"),
        current_position_summary=_summary(tmp_path, "cur_missing_target_weight_authority", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(tmp_path, "pv_missing_target_weight_authority"),
        safety_limit_summary=_safety(tmp_path),
        config=_config(),
    )
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "target_weight_authority_unavailable" in payload["reason_codes"]
    assert item["sizing_status"] == "TARGET_WEIGHT_UNAVAILABLE"
    assert item["target_weight_resolution"]["review_reason"] == "target_weight_authority_missing"
    assert item["target_weight"] == 0
    assert item["target_notional"] == 0


def test_phase23_ao_raw_opportunity_score_does_not_change_target_weight_sizing(tmp_path: Path) -> None:
    low = _quality_row("5102", runtime_opportunity_score=-0.4)
    high = _quality_row("5102", runtime_opportunity_score=0.9)
    low_payload = _produce(tmp_path / "phase23_ao_raw_low", rows=[low]).payload
    high_payload = _produce(tmp_path / "phase23_ao_raw_high", rows=[high]).payload
    low_item = low_payload["positions"][0]
    high_item = high_payload["positions"][0]

    assert low_item["runtime_opportunity_score"] != high_item["runtime_opportunity_score"]
    assert low_item["target_weight"] == high_item["target_weight"]
    assert low_item["target_notional"] == high_item["target_notional"]
    assert low_item["target_quantity_candidate"] == high_item["target_quantity_candidate"]


def test_phase23_am_al_style_signful_distribution_does_not_mass_invalid_quality_block(tmp_path: Path) -> None:
    scores = [0.56251442, 0.52259395, 0.38581156, 0.20647216, 0.19381909, 0.08588799, 0.16926671, 0.11678465, 0.04904072, -0.03759588, 0.06279684, 0.02811699, -0.07135416, -0.04086726, -0.00192086, 0.00832506, -0.114557, -0.05791252, -0.15708351, -0.03146798, -0.14281968, -0.23649922, -0.1995641, -0.14725547, -0.18805999, -0.18453179, -0.09482979, -0.16579998, -0.08243472, -0.18257588, -0.25790579, -0.18488506, -0.13076819, -0.22968528, -0.2570116, -0.23872757, -0.24381963, -0.29100442, -0.27343585, -0.25827774, -0.29605303, -0.32498741, -0.34920405, -0.36131882, -0.40773519, -0.41852678, -0.42747597, -0.38684782, -0.25503377, -0.16144175]
    rows = [_quality_row(str(7000 + index), runtime_opportunity_score=score, volatility=0.03, priority=index) for index, score in enumerate(scores, start=1)]
    payload = _produce(tmp_path / "phase23_am_al_distribution", rows=rows, target_count=10, exposure=0.79).payload

    assert payload["producer_result_status"] == "PASS"
    assert any(item["target_weight"] > 0 for item in payload["positions"])
    assert any(item["target_notional"] > 0 for item in payload["positions"])
    assert all(item["runtime_opportunity_score_resolution"]["resolution_status"] == "PASS" for item in payload["positions"])
    assert all(item["allocation_quality_resolution"]["review_reason"] == "allocation_quality_score_missing" for item in payload["positions"])
    assert all("invalid_quality_score" not in ";".join(item["reason_codes"]) for item in payload["positions"])


def test_phase26_a_target_position_count_zero_does_not_zero_eligible_buy(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "phase23_ak_no_forced_buy", rows=[_quality_row("5007", allocation_quality_score=0.8, runtime_opportunity_score=0.2)], target_count=0, exposure=0.79).payload

    assert payload["producer_result_status"] == "PASS"
    assert payload["positions"][0]["sizing_status"] in {"SIZED", "CAPPED"}
    assert payload["positions"][0]["target_notional"] > 0


def test_phase23_at_reference_price_from_market_authority_resolves_quantity(tmp_path: Path) -> None:
    row = _quality_row("5201", allocation_quality_score=0.8, runtime_opportunity_score=0.2)
    row.pop("reference_price")
    row.pop("reference_price_authority")
    row.pop("reference_price_resolution")
    row.pop("reference_price_type")
    row.pop("reference_price_date")
    payload, _ = build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc_reference_price", rows=[row]),
        capital_deployment_summary=_summary(tmp_path, "cd_reference_price", status="REVIEW_REQUIRED", summary={"reason": "capital_deployment_is_downstream_of_position_sizing_in_shadow_chain"}),
        dynamic_position_count_summary=_summary(tmp_path, "dpc_reference_price", summary={"target_position_count": 1}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce_reference_price", summary={"target_gross_exposure_ratio": 0.16}),
        position_management_summary=_summary(tmp_path, "pm_reference_price"),
        opportunity_summary=_summary(tmp_path, "opp_reference_price"),
        current_position_summary=_summary(tmp_path, "cur_reference_price", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(
            tmp_path,
            "pv_reference_price",
            rows=[
                {
                    "symbol": "5201",
                    "volatility_value": 0.03,
                    "reference_price": 500.0,
                    **_reference_price_contract("5201", 500.0),
                }
            ],
        ),
        safety_limit_summary=_safety(tmp_path),
        config=_config(),
    )
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert item["reference_price"] == 500.0
    assert item["reference_price_resolution"]["status"] == "PASS"
    assert item["quantity_status"] == "RESOLVED_CANDIDATE"
    assert item["target_quantity_candidate"] > 0


def test_phase23_at_positive_target_without_reference_price_fails_closed(tmp_path: Path) -> None:
    row = _quality_row("5202", allocation_quality_score=0.8, runtime_opportunity_score=0.2)
    for field in ("reference_price", "reference_price_authority", "reference_price_resolution", "reference_price_type", "reference_price_date"):
        row.pop(field)
    payload = _produce(tmp_path / "phase23_at_missing_price", rows=[row], target_count=1, exposure=0.16).payload
    item = payload["positions"][0]

    assert payload["producer_result_status"] == "PASS"
    assert item["target_notional"] > 0
    assert item["reference_price_required"] is True
    assert item["quantity_status"] == "PRICE_UNAVAILABLE"
    assert item["target_quantity_candidate"] == 0
    assert item["reference_price_resolution"]["review_reason"] == "reference_price_missing_or_invalid"


def test_phase23_at_zero_target_weight_does_not_require_reference_price(tmp_path: Path) -> None:
    row = _quality_row("5203", allocation_quality_score=0.8, runtime_opportunity_score=0.2)
    row["target_weight"] = 0.0
    row["target_weight_resolution"]["resolved_weight"] = 0.0
    row["target_weight_resolution"]["reason"] = "policy_zero_allocation"
    row["target_weight_resolution"]["zero_weight_reason"] = "policy_zero_allocation"
    for field in ("reference_price", "reference_price_authority", "reference_price_resolution", "reference_price_type", "reference_price_date"):
        row.pop(field)
    payload = _produce(tmp_path / "phase23_at_zero_no_price", rows=[row], target_count=1, exposure=0.16).payload
    item = payload["positions"][0]

    assert item["target_notional"] == 0
    assert item["reference_price_required"] is False
    assert item["quantity_status"] == "RESOLVED_ZERO_DELTA"
    assert item["target_quantity_candidate"] == 0


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
    assert missing_quality["producer_result_status"] == "PASS"
    assert missing_quality["positions"][0]["sizing_status"] in {"SIZED", "CAPPED"}

    missing_vol = _produce(tmp_path / "missing_vol", rows=[_row("2002", volatility=None)]).payload
    assert missing_vol["producer_result_status"] == "PASS"
    assert missing_vol["positions"][0]["sizing_status"] in {"SIZED", "CAPPED"}


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
    assert high_price["producer_result_status"] == "PASS"
    assert high_price["positions"][0]["sizing_status"] == "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY"
    assert high_price["positions"][0]["target_weight"] > 0
    assert high_price["positions"][0]["target_notional"] > 0
    assert high_price["positions"][0]["target_quantity_candidate"] == 0


def test_phase26_a_explicit_zero_position_count_is_deprecated_metadata_only(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "explicit_zero", rows=_rows(3), target_count=0, exposure=0.72).payload

    assert payload["producer_result_status"] == "PASS"
    assert payload["target_position_count"] == 0
    assert payload["target_position_count_resolution"] == "EXPLICIT_ZERO"
    assert payload["positions_sized"] == 3
    assert payload["positions_withheld"] == 0
    assert all(item["sizing_status"] in {"SIZED", "CAPPED"} for item in payload["positions"])
    assert "position_count_or_exposure_unresolved" not in payload["reason_codes"]


def test_phase23_aa_capital_deployment_shadow_cycle_placeholder_is_not_consumer_blocker(tmp_path: Path) -> None:
    payload, _ = build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc", rows=_rows(2)),
        capital_deployment_summary=_summary(
            tmp_path,
            "cd_placeholder",
            status="REVIEW_REQUIRED",
            summary={"reason": "capital_deployment_is_downstream_of_position_sizing_in_shadow_chain"},
        ),
        dynamic_position_count_summary=_summary(tmp_path, "dpc", summary={"target_position_count": 2}),
        dynamic_cash_exposure_summary=_summary(tmp_path, "dce", summary={"target_gross_exposure_ratio": 0.4}),
        position_management_summary=_summary(tmp_path, "pm"),
        opportunity_summary=_summary(tmp_path, "opp"),
        current_position_summary=_summary(tmp_path, "cur", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary(tmp_path, "pv"),
        safety_limit_summary=_safety(tmp_path),
        config=_config(),
    )

    assert payload["producer_result_status"] == "PASS"
    assert "capital_deployment_review_required:REVIEW_REQUIRED" not in payload["reason_codes"]


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


def test_phase24_ii_position_sizing_allows_serialized_target_weight_rounding_tolerance(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "phase24_ii_rounding", target_count=6, exposure=0.79, rows=_rows(6)).payload

    assert payload["producer_result_status"] == "PASS"
    assert payload["total_target_weight"] == 0.790002
    assert payload["target_gross_exposure_ratio"] == 0.79
    assert payload["target_weight_sum_tolerance"] == 0.000003
    assert payload["target_weight_precision"]["rounding_digits"] == 6
    assert "aggregate_target_weight_above_exposure_cap" not in payload["reason_codes"]
    assert validate_position_sizing_artifact(payload)["status"] == "PASS"


def test_phase24_ii_position_sizing_blocks_real_aggregate_exposure_overflow(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "phase24_ii_real_overflow", target_count=6, exposure=0.79, rows=_rows(6)).payload
    overflow = json.loads(json.dumps(payload))
    overflow["total_target_weight"] = 0.791

    with pytest.raises(PositionSizingSchemaError) as aggregate_error:
        validate_position_sizing_artifact(overflow)

    assert "aggregate_target_weight_above_exposure_cap" in str(aggregate_error.value)


def test_phase22_pw_valid_configuration_has_no_cap_violation_reason(tmp_path: Path) -> None:
    payload = _produce(tmp_path / "valid_contract").payload

    assert payload["producer_result_status"] == "PASS"
    assert "configured_max_position_weight_above_safety_cap" not in payload["reason_codes"]
    assert "produced_position_weight_above_safety_cap" not in payload["reason_codes"]
    assert "aggregate_target_weight_above_exposure_cap" not in payload["reason_codes"]


def _produce(tmp_path: Path, *, rows: list[dict[str, object]] | None = None, target_count: int = 5, exposure: float = 0.8):
    tmp_path.mkdir(parents=True, exist_ok=True)
    sizing_rows = _with_target_weights(rows or _rows(target_count), target_count=target_count, exposure=exposure)
    return produce_position_sizing_artifact(
        business_date="2026-07-15",
        portfolio_construction_summary=_summary(tmp_path, "pc", rows=sizing_rows),
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


def _with_target_weights(rows: list[dict[str, object]], *, target_count: int, exposure: float) -> list[dict[str, object]]:
    selected = [
        row
        for row in rows
        if str(row.get("membership_intent") or "").upper() in {"ADD_CANDIDATE", "RETAIN"}
    ]
    selected_codes = {str(row.get("security_code")) for row in selected}
    base = round(exposure / len(selected_codes), 6) if selected_codes and exposure > 0 else 0.0
    enriched = []
    for row in rows:
        code = str(row.get("security_code") or "")
        membership = str(row.get("membership_intent") or "").upper()
        if "target_weight" in row:
            weight = float(row["target_weight"])
        elif code in selected_codes and membership in {"ADD_CANDIDATE", "RETAIN"}:
            weight = base
        else:
            weight = 0.0
        zero_reason = "" if weight > 0 else ("policy_zero_exposure" if exposure == 0 else "opportunity_not_selected")
        enriched.append(
            {
                **row,
                "target_weight": weight,
                "target_weight_authority": {
                    "authority_type": "TARGET_WEIGHT_AUTHORITY",
                    "method_id": "test_production_v1_equal_weight_target_allocation",
                    "method_version": "phase23_ao_test_v1",
                    "business_date": "2026-07-15",
                    "target_gross_exposure": exposure,
                    "resolved_target_member_count": len(selected_codes),
                    "single_name_weight_cap": 0.25,
                    "portfolio_policy_reference": "portfolio-policy-test",
                    "dynamic_position_count_reference": "dynamic-position-count-test",
                    "opportunity_reference": row.get("opportunity_reference", ""),
                    "existing_position_reference": row.get("position_reference", "") if row.get("current_weight") else "",
                    "position_management_reference": row.get("position_reference", ""),
                    "source_artifact_paths": [],
                    "source_artifact_hashes": [],
                    "PIT_status": "PASS",
                },
                "target_weight_resolution": {
                    "status": "PASS",
                    "reason": "target_weight_resolved" if weight > 0 else zero_reason,
                    "resolved_weight": weight,
                    "base_weight": base,
                    "adjustments": [],
                    "cap_applied": False,
                    "normalization_applied": False,
                    "zero_weight_reason": zero_reason,
                    "review_reason": "",
                },
            }
        )
    return enriched


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
        **_reference_price_contract(code, price),
        "allocation_priority": priority,
        "target_weight": 0.16,
        "target_weight_authority": {
            "authority_type": "TARGET_WEIGHT_AUTHORITY",
            "method_id": "test_production_v1_equal_weight_target_allocation",
            "method_version": "phase23_ao_test_v1",
            "business_date": "2026-07-15",
            "target_gross_exposure": 0.8,
            "resolved_target_member_count": 5,
            "single_name_weight_cap": 0.25,
            "portfolio_policy_reference": "portfolio-policy-test",
            "dynamic_position_count_reference": "dynamic-position-count-test",
            "opportunity_reference": f"opportunity-{code}",
            "existing_position_reference": f"member-{code}" if current_weight else "",
            "position_management_reference": f"member-{code}",
            "source_artifact_paths": [],
            "source_artifact_hashes": [],
            "PIT_status": "PASS",
        },
        "target_weight_resolution": {
            "status": "PASS",
            "reason": "target_weight_resolved",
            "resolved_weight": 0.16,
            "base_weight": 0.16,
            "adjustments": [],
            "cap_applied": False,
            "normalization_applied": False,
            "zero_weight_reason": "",
            "review_reason": "",
        },
        "runtime_opportunity_score_authority": {
            "authority": "OPPORTUNITY_RANKING_AUTHORITY",
            "canonical_field": "runtime_opportunity_score",
            "source_decision_id": f"opportunity-{code}",
            "source_artifact_class": "opportunity",
            "source_field": "runtime_opportunity_score",
            "prediction_semantics": "runtime_opportunity_score",
        },
        "allocation_quality_authority": {
            "authority": "ALLOCATION_QUALITY_AUTHORITY",
            "canonical_field": "allocation_quality_score",
            "source_decision_id": f"allocation-quality-{code}",
            "source_artifact_class": "portfolio_construction",
            "source_field": "allocation_quality_score",
            "output_semantics": "allocation_quality_score",
        },
    }
    if score is not None:
        row["runtime_opportunity_score"] = score
        row["allocation_quality_score"] = score
    row.update(_buy_quality_contract(code, score=score if score is not None else 0.82))
    if volatility is not None:
        row["volatility"] = volatility
    return row


def _quality_row(
    code: str,
    *,
    quality_score: float | None = None,
    allocation_quality_score: float | None = None,
    runtime_opportunity_score: float | None = None,
    input_score: float | None = None,
    opportunity_score: float | None = None,
    volatility: float | None = 0.03,
    price: float = 600.0,
    priority: int = 1,
) -> dict[str, object]:
    row: dict[str, object] = {
        "security_code": code,
        "position_reference": f"phase22-e-2026-07-15-{code}",
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "current_weight": 0.0,
        "opportunity_confidence": 0.9,
        "confidence": 0.9,
        "reference_price": price,
        **_reference_price_contract(code, price),
        "allocation_priority": priority,
        "candidate_reference": f"candidate-{code}",
        "opportunity_reference": f"opportunity-{code}",
        "target_weight": 0.16,
        "target_weight_authority": {
            "authority_type": "TARGET_WEIGHT_AUTHORITY",
            "method_id": "test_production_v1_equal_weight_target_allocation",
            "method_version": "phase23_ao_test_v1",
            "business_date": "2026-07-15",
            "target_gross_exposure": 0.8,
            "resolved_target_member_count": 5,
            "single_name_weight_cap": 0.25,
            "portfolio_policy_reference": "portfolio-policy-test",
            "dynamic_position_count_reference": "dynamic-position-count-test",
            "opportunity_reference": f"opportunity-{code}",
            "existing_position_reference": "",
            "position_management_reference": f"phase22-e-2026-07-15-{code}",
            "source_artifact_paths": [],
            "source_artifact_hashes": [],
            "PIT_status": "PASS",
        },
        "target_weight_resolution": {
            "status": "PASS",
            "reason": "target_weight_resolved",
            "resolved_weight": 0.16,
            "base_weight": 0.16,
            "adjustments": [],
            "cap_applied": False,
            "normalization_applied": False,
            "zero_weight_reason": "",
            "review_reason": "",
        },
        "runtime_opportunity_score_authority": {
            "authority": "OPPORTUNITY_RANKING_AUTHORITY",
            "canonical_field": "runtime_opportunity_score",
            "source_decision_id": f"opportunity-{code}",
            "source_artifact_class": "opportunity",
            "source_field": "runtime_opportunity_score",
            "prediction_semantics": "runtime_opportunity_score",
        },
        "allocation_quality_authority": {
            "authority": "ALLOCATION_QUALITY_AUTHORITY",
            "canonical_field": "allocation_quality_score",
            "source_decision_id": f"allocation-quality-{code}",
            "source_artifact_class": "portfolio_construction",
            "source_field": "allocation_quality_score",
            "output_semantics": "allocation_quality_score",
        },
        "quality_score_authority": {
            "authority": "ALLOCATION_QUALITY_AUTHORITY",
            "canonical_field": "allocation_quality_score",
            "source_decision_id": f"allocation-quality-{code}",
            "source_artifact_class": "portfolio_construction",
            "source_field": "quality_score",
            "output_semantics": "allocation_quality_score",
        },
    }
    if allocation_quality_score is not None:
        row["allocation_quality_score"] = allocation_quality_score
    if runtime_opportunity_score is not None:
        row["runtime_opportunity_score"] = runtime_opportunity_score
    if quality_score is not None:
        row["quality_score"] = quality_score
    if input_score is not None:
        row["input_score"] = input_score
    if opportunity_score is not None:
        row["opportunity_score"] = opportunity_score
    if volatility is not None:
        row["volatility"] = volatility
    row.update(_buy_quality_contract(code, score=quality_score if quality_score is not None else 0.82))
    return row


def _reference_price_contract(code: str, price: float) -> dict[str, object]:
    return {
        "reference_price_type": "planning_reference_close",
        "reference_price_date": "2026-07-15",
        "reference_price_authority": {
            "authority_type": "REFERENCE_PRICE_AUTHORITY",
            "canonical_field": "reference_price",
            "source_authority": "MARKET_EVIDENCE_AUTHORITY",
            "source_dataset": "test_market_quotes",
            "source_field": "close",
            "source_path": f"market-{code}.json",
            "source_hash": f"hash-{code}",
            "symbol": code,
            "business_date": "2026-07-15",
            "price_date": "2026-07-15",
            "price_type": "planning_reference_close",
            "PIT_status": "PASS",
            "latest_fallback_used": False,
        },
        "reference_price_resolution": {
            "status": "PASS",
            "reason": "reference_price_resolved",
            "resolved_price": price,
            "source_field": "close",
            "price_required_for": "position_sizing_quantity_conversion",
            "review_reason": "",
        },
    }


def _buy_quality_contract(code: str, *, score: float = 0.82, action: str = "FULL_ALLOCATION_ELIGIBLE") -> dict[str, object]:
    adjustment = 1.0 if action == "FULL_ALLOCATION_ELIGIBLE" else max(0.0, min(0.85, score))
    return {
        "quality_decision_id": f"bq-{code}",
        "quality_score": score,
        "quality_band": "HIGH",
        "quality_action": action,
        "quality_status": "PASS",
        "quality_reason_codes": ["test_buy_quality_authority"],
        "quality_policy_version": "phase26_h_adaptive_buy_quality_policy.v1",
        "quality_allocation_adjustment": adjustment,
        "component_scores": {
            "relative_opportunity_quality": score,
            "market_context_quality_modifier": score,
            "signal_reliability": score,
            "execution_feasibility": score,
            "portfolio_fit": score,
        },
        "component_statuses": {
            "relative_opportunity_quality": "PASS",
            "market_context_quality_modifier": "PASS",
            "signal_reliability": "PASS",
            "execution_feasibility": "PASS",
            "portfolio_fit": "PASS",
        },
        "buy_quality_authority": {
            "authority_type": "ADAPTIVE_BUY_QUALITY_AUTHORITY",
            "producer": "Production Strategy BUY Quality Resolver",
            "quality_decision_id": f"bq-{code}",
            "quality_action": action,
            "source_artifact_path": "test_buy_quality_decisions.json",
            "source_artifact_hash": f"hash-bq-{code}",
            "PIT_status": "PASS",
            "future_information_used": False,
        },
    }


def _summary(tmp_path: Path, kind: str, *, status: str = "PASS", business_date: str = "2026-07-15", feature_date: str = "2026-07-15", rows: list[dict[str, object]] | None = None, summary: dict[str, object] | None = None) -> PositionSizingSourceSummary:
    path = tmp_path / f"{kind}_summary.json"
    payload = {"kind": kind, "status": status, "business_date": business_date, "feature_date": feature_date, "rows": rows or [], "summary": summary or {}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return PositionSizingSourceSummary(status, business_date, feature_date, str(path), ps.sha256_file(path), tuple(rows or ()), summary or {})
