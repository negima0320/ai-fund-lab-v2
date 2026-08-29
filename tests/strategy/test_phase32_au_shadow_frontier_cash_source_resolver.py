from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.common_marginal_capital_frontier_shadow import (
    assert_shadow_frontier_not_production_consumer,
    build_canonical_marginal_capital_frontier_payload,
    materialize_canonical_marginal_capital_frontier_for_day,
    resolve_shadow_cash_state_for_day,
)


BUSINESS_DATE = "2026-08-28"


def test_phase32_au_portfolio_policy_cash_resolves_with_lineage() -> None:
    cash = resolve_shadow_cash_state_for_day(
        portfolio_policy_payload={"current_cash_summary": {"buying_power": 250_000.0, "cash": 250_000.0}},
        valuation_projection_payload={"buying_power": 100_000.0},
        source_artifacts={"portfolio_policy": "strategy/portfolio_policy.json", "valuation_projection": "valuation_projection.json"},
        source_hashes={"portfolio_policy": "sha256:policy", "valuation_projection": "sha256:valuation"},
    )

    assert cash["cash_source_status"] == "PASS"
    assert cash["available_cash"] == 250_000.0
    assert cash["cash_source_role"] == "portfolio_policy.current_cash_summary"
    assert cash["cash_source_hash"] == "sha256:policy"
    assert any(item["role"] == "current_valuation_refresh.valuation_projection" for item in cash["cash_source_lineage"])


def test_phase32_au_valuation_projection_fallback_resolves_when_policy_cash_missing() -> None:
    cash = resolve_shadow_cash_state_for_day(
        portfolio_policy_payload={},
        valuation_projection_payload={"cash": 123_450.0},
        source_artifacts={"valuation_projection": "current_valuation_refresh/valuation_projection.json"},
        source_hashes={"valuation_projection": "sha256:valuation"},
    )

    assert cash["cash_source_status"] == "PASS"
    assert cash["available_cash"] == 123_450.0
    assert cash["cash_source_role"] == "current_valuation_refresh.valuation_projection"


def test_phase32_au_conflicting_cash_evidence_fails_closed_within_selected_authority() -> None:
    cash = resolve_shadow_cash_state_for_day(
        portfolio_policy_payload={"current_cash_summary": {"buying_power": 250_000.0, "cash": 249_000.0}},
        valuation_projection_payload={"cash": 250_000.0},
    )
    payload = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010")]),
        cash_payload=cash,
    )

    assert cash["cash_source_status"] == "REVIEW_REQUIRED"
    assert cash["cash_source_reason"] == "conflicting_decision_time_cash_evidence"
    assert _candidate(payload, "10010")["shadow_disposition"] == "REVIEW_REQUIRED"
    assert _candidate(payload, "CASH")["shadow_disposition"] == "REVIEW_REQUIRED"


def test_phase32_au_missing_cash_fails_closed_not_false_insufficient_cash() -> None:
    cash = resolve_shadow_cash_state_for_day(portfolio_policy_payload={}, valuation_projection_payload={})
    payload = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010")]),
        cash_payload=cash,
    )

    assert cash["cash_source_status"] == "REVIEW_REQUIRED"
    assert _candidate(payload, "10010")["shadow_disposition"] == "REVIEW_REQUIRED"
    assert payload["metrics"]["insufficient_cash_count"] == 0


def test_phase32_au_broad_day_materialization_uses_policy_cash_and_avoids_false_cash_collapse(tmp_path: Path) -> None:
    day = tmp_path / "daily" / BUSINESS_DATE
    (day / "strategy").mkdir(parents=True)
    (day / "current_valuation_refresh").mkdir()
    (day / "strategy" / "portfolio_construction.json").write_text(
        json.dumps(_pc([_new("10010"), _add("20020")])),
        encoding="utf-8",
    )
    (day / "strategy" / "position_sizing.json").write_text(
        json.dumps({"portfolio_value": 1_000_000.0, "positions": []}),
        encoding="utf-8",
    )
    (day / "strategy" / "portfolio_policy.json").write_text(
        json.dumps({"current_cash_summary": {"buying_power": 300_000.0, "cash": 300_000.0, "current_cash": 300_000.0}}),
        encoding="utf-8",
    )
    (day / "current_valuation_refresh" / "valuation_projection.json").write_text(json.dumps({"cash": 120_000.0}), encoding="utf-8")
    (day / "current_valuation_refresh" / "safety_authority_decision.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")

    payload = materialize_canonical_marginal_capital_frontier_for_day(run_root=tmp_path, business_date=BUSINESS_DATE)

    assert payload["cash_source_status"] == "PASS"
    assert payload["cash_source_lineage"][0]["role"] == "portfolio_policy.current_cash_summary"
    assert payload["metrics"]["insufficient_cash_count"] == 0
    assert any(row["shadow_disposition"] == "SHADOW_WINNER" for row in payload["frontier_candidates"])
    assert assert_shadow_frontier_not_production_consumer(payload) is True


def test_phase32_au_deterministic_rerun_and_production_consumer_count_zero() -> None:
    cash = resolve_shadow_cash_state_for_day(
        portfolio_policy_payload={"current_cash_summary": {"buying_power": 250_000.0, "cash": 250_000.0}},
    )
    first = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010"), _add("20020")]),
        cash_payload=cash,
    )
    second = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010"), _add("20020")]),
        cash_payload=cash,
    )

    assert first["artifact_hash"] == second["artifact_hash"]
    assert first["determinism_key"] == second["determinism_key"]
    assert first["production_consumer_count"] == 0
    assert assert_shadow_frontier_not_production_consumer(first) is True


def _candidate(payload: dict, symbol: str) -> dict:
    return next(row for row in payload["frontier_candidates"] if row["symbol"] == symbol)


def _pc(members: list[dict]) -> dict:
    return {"portfolio_value": 1_000_000.0, "portfolio_members": members}


def _new(symbol: str) -> dict:
    return {
        "security_code": symbol,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "semantic_buy_type": "BUY_NEW",
        "candidate_id": f"candidate-{symbol}",
        "runtime_opportunity_score": 0.9,
        "input_opportunity_rank": 1,
        "entry_admission_action": "FULL_ALLOCATION_ELIGIBLE",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "reference_price": 1_000.0,
        "trading_unit": 100,
    }


def _add(symbol: str) -> dict:
    return {
        "security_code": symbol,
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "position_campaign_id": f"pc-{symbol}-0001",
        "current_quantity": 100,
        "current_weight": 0.05,
        "runtime_opportunity_score": 0.8,
        "input_opportunity_rank": 2,
        "expected_edge_improvement_state": "IMPROVING",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "add_allocation_eligibility_status": "PASS",
        "same_campaign_continuation_status": "CONTINUING",
        "reference_price": 1_000.0,
        "trading_unit": 100,
    }
