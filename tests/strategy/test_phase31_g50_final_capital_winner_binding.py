from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.safety.portfolio_limits import load_portfolio_safety_limits
from ai_fund_lab_v2.strategy import position_sizing as ps
from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework
from ai_fund_lab_v2.strategy.position_sizing import (
    PositionSizingSourceSummary,
    build_position_sizing_payload,
    load_position_sizing_config,
)


BUSINESS_DATE = "2026-07-15"


def test_phase31_g50_cash_winner_blocks_new_buy_before_position_sizing() -> None:
    rows = [_new_row(str(1000 + index), quality="COMPARABLE_MARGINAL") for index in range(22)]
    competition = _competition(rows, "CAUTIOUS_DEPLOYMENT")

    payload = _position_sizing_payload(rows, competition)

    assert competition["capital_competition_winner_type"] == "CASH_OPTIONALITY"
    assert competition["canonical_deployment_set"]["selected_deployments"] == []
    assert payload["canonical_deployment_set_consumption"]["status"] == "PASS"
    assert payload["canonical_deployment_set_consumption"]["defeated_security_positive_increment_count"] == 0
    assert payload["positions_sized"] == 22
    assert all(item["quantity_delta_candidate"] == 0 for item in payload["positions"])
    assert all(item["incremental_buy_notional"] == 0 for item in payload["positions"])
    assert all(
        item["canonical_deployment_set_sizing_eligibility"] == "DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION"
        for item in payload["positions"]
    )


def test_phase31_g50_security_winner_exclusive_set_reaches_position_sizing() -> None:
    rows = [
        _new_row("44490", quality="STRONG"),
        _new_row("69930", quality="COMPARABLE_MARGINAL"),
        _new_row("66630", quality="COMPARABLE_MARGINAL"),
    ]
    competition = _competition(rows, "CAUTIOUS_DEPLOYMENT")

    payload = _position_sizing_payload(rows, competition)
    by_symbol = {item["security_code"]: item for item in payload["positions"]}

    assert competition["capital_competition_winner_type"] == "NEW_BUY"
    assert competition["capital_competition_winner_symbol"] == "44490"
    assert competition["canonical_deployment_set"]["cardinality_contract"] == "SINGLE"
    assert competition["canonical_deployment_set"]["selected_symbol_set"] == ["44490"]
    assert by_symbol["44490"]["quantity_delta_candidate"] > 0
    assert by_symbol["44490"]["canonical_deployment_set_sizing_eligibility"] == "SELECTED_FOR_DEPLOYMENT"
    assert by_symbol["69930"]["quantity_delta_candidate"] == 0
    assert by_symbol["66630"]["quantity_delta_candidate"] == 0


def test_phase31_g50_add_lost_to_cash_preserves_existing_baseline_without_increment() -> None:
    rows = [_add_row("67580", quality="COMPARABLE_MARGINAL")]
    competition = _competition(rows, "CAUTIOUS_DEPLOYMENT")

    payload = _position_sizing_payload(rows, competition)
    item = payload["positions"][0]

    assert competition["capital_competition_winner_type"] == "CASH_OPTIONALITY"
    assert item["current_quantity"] == 100
    assert item["target_quantity_candidate"] == 100
    assert item["quantity_delta_candidate"] == 0
    assert item["target_weight"] == item["current_weight"]
    assert item["baseline_quantity_preserved"] is True
    assert item["canonical_deployment_set_sizing_eligibility"] == "DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION"


def test_phase31_g50_cash_winner_does_not_force_existing_hold_exit() -> None:
    rows = [_hold_row("72030")]
    competition = _competition([_new_row("60980", quality="COMPARABLE_MARGINAL")], "CAUTIOUS_DEPLOYMENT")

    payload = _position_sizing_payload(rows, competition)
    item = payload["positions"][0]

    assert competition["capital_competition_winner_type"] == "CASH_OPTIONALITY"
    assert item["pm_action"] == "HOLD"
    assert item["target_quantity_candidate"] == 100
    assert item["quantity_delta_candidate"] == 0
    assert item["baseline_quantity_preserved"] is True
    assert item["canonical_deployment_set_sizing_eligibility"] == "NOT_INCREMENTAL_DEPLOYMENT_COMPETITOR"


def _position_sizing_payload(rows: list[dict[str, object]], competition: dict[str, object]) -> dict[str, object]:
    payload, _ = build_position_sizing_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_summary=_summary(
            "portfolio_construction",
            rows=rows,
            summary={
                "business_date": BUSINESS_DATE,
                "capital_competition": competition,
                "canonical_deployment_set": competition["canonical_deployment_set"],
            },
        ),
        capital_deployment_summary=_summary("capital_deployment"),
        dynamic_position_count_summary=_summary("dynamic_position_count", summary={"target_position_count": len(rows)}),
        dynamic_cash_exposure_summary=_summary("dynamic_cash_exposure", summary={"target_gross_exposure_ratio": 0.8}),
        position_management_summary=_summary("position_management"),
        opportunity_summary=_summary("opportunity"),
        current_position_summary=_summary("current_position", summary={"portfolio_value": 1_000_000}),
        price_volatility_summary=_summary("price_volatility"),
        safety_limit_summary=_safety_summary(),
        config=load_position_sizing_config("configs/strategy/position_sizing.json"),
    )
    return payload


def _competition(rows: list[dict[str, object]], risk_pacing_intent: str) -> dict[str, object]:
    return build_capital_competition_framework(
        members=rows,
        target_gross_exposure=0.8,
        total_target_weight=sum(float(row.get("target_weight") or 0.0) for row in rows),
        business_date=BUSINESS_DATE,
        risk_pacing_evidence={
            "risk_pacing_intent": risk_pacing_intent,
            "risk_pacing_as_of": BUSINESS_DATE,
            "risk_pacing_evidence_completeness": "COMPLETE",
            "mode": "AUTHORITATIVE",
            "risk_pacing_component_evidence": {
                "business_date": BUSINESS_DATE,
                "market_quality_state": "SHORT_TERM_BREADTH_BREAKDOWN",
                "market_quality_evidence_completeness": "COMPLETE",
                "future_information_used": False,
                "historical_outcome_used": False,
            },
        },
    )


def _new_row(symbol: str, *, quality: str) -> dict[str, object]:
    return {
        **_base_row(symbol, quality=quality),
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "current_weight": 0.0,
        "current_quantity": 0,
        "target_weight": 0.1,
        "accepted_buy_new_weight": 0.1,
    }


def _add_row(symbol: str, *, quality: str) -> dict[str, object]:
    return {
        **_base_row(symbol, quality=quality),
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "current_weight": 0.05,
        "current_quantity": 100,
        "target_weight": 0.15,
        "accepted_incremental_weight": 0.1,
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "add_allocation_eligibility_status": "PASS",
        "same_campaign_continuation_status": "CONTINUING",
    }


def _hold_row(symbol: str) -> dict[str, object]:
    return {
        **_base_row(symbol, quality="NOT_APPLICABLE"),
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "HOLD",
        "current_weight": 0.05,
        "baseline_existing_weight": 0.05,
        "current_quantity": 100,
        "target_weight": 0.05,
    }


def _base_row(symbol: str, *, quality: str) -> dict[str, object]:
    return {
        "security_code": symbol,
        "symbol": symbol,
        "position_reference": f"pc-{symbol}",
        "member_id": f"pc-{symbol}",
        "business_date": BUSINESS_DATE,
        "confidence": 0.9,
        "opportunity_confidence": 0.9,
        "reference_price": 500.0,
        "reference_price_type": "planning_reference_close",
        "reference_price_date": BUSINESS_DATE,
        "reference_price_authority": {
            "authority_type": "REFERENCE_PRICE_AUTHORITY",
            "business_date": BUSINESS_DATE,
            "price_date": BUSINESS_DATE,
            "PIT_status": "PASS",
            "latest_fallback_used": False,
        },
        "reference_price_resolution": {
            "status": "PASS",
            "reason": "reference_price_resolved",
            "resolved_price": 500.0,
            "review_reason": "",
        },
        "trading_unit": 100,
        "volatility": 0.03,
        "allocation_quality_score": 0.8,
        "runtime_opportunity_score": 0.7,
        "quality_score": 0.8,
        "quality_decision_id": f"bq-{symbol}",
        "quality_band": "HIGH",
        "quality_action": "FULL_ALLOCATION_ELIGIBLE",
        "quality_status": "PASS",
        "quality_reason_codes": ["test_quality"],
        "quality_policy_version": "phase31_g50_test_quality.v1",
        "quality_allocation_adjustment": 1.0,
        "component_scores": {"test": 0.8},
        "component_statuses": {"test": "PASS"},
        "buy_quality_authority": {
            "authority_type": "ADAPTIVE_BUY_QUALITY_AUTHORITY",
            "quality_decision_id": f"bq-{symbol}",
            "quality_action": "FULL_ALLOCATION_ELIGIBLE",
            "PIT_status": "PASS",
            "future_information_used": False,
        },
        "target_weight_authority": {
            "authority_type": "TARGET_WEIGHT_AUTHORITY",
            "PIT_status": "PASS",
            "business_date": BUSINESS_DATE,
        },
        "target_weight_resolution": {
            "status": "PASS",
            "reason": "target_weight_resolved",
            "resolved_weight": 0.1,
            "base_weight": 0.1,
            "adjustments": [],
            "zero_weight_reason": "",
            "review_reason": "",
        },
        "canonical_opportunity_quality_class": quality,
        "marginal_capital_value_authority": {
            "canonical_opportunity_quality_class": quality,
            "opportunity_quality_evidence": {
                "canonical_opportunity_quality_class": quality,
                "opportunity_quality_hash": f"oq-{symbol}-{quality}",
                "reason_codes": [quality],
                "future_information_used": False,
                "historical_outcome_used": False,
            },
            "future_information_used": False,
        },
    }


def _summary(
    kind: str,
    *,
    rows: list[dict[str, object]] | None = None,
    summary: dict[str, object] | None = None,
) -> PositionSizingSourceSummary:
    payload = {
        "kind": kind,
        "status": "PASS",
        "business_date": BUSINESS_DATE,
        "feature_date": BUSINESS_DATE,
        "rows": rows or [],
        "summary": summary or {},
    }
    source_hash = ps.stable_payload_hash(payload)
    return PositionSizingSourceSummary(
        "PASS",
        BUSINESS_DATE,
        BUSINESS_DATE,
        f"memory://phase31_g50/{kind}.json",
        source_hash,
        tuple(rows or ()),
        summary or {},
    )


def _safety_summary() -> PositionSizingSourceSummary:
    limits = load_portfolio_safety_limits("configs/safety/portfolio_limits.json", legacy_active_max_positions=5)
    return _summary("safety", summary=limits.to_contract_payload())
