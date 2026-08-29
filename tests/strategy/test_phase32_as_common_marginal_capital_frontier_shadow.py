from __future__ import annotations

import copy
import json
from pathlib import Path

from ai_fund_lab_v2.strategy.common_marginal_capital_frontier_shadow import (
    ARTIFACT_MODE,
    PRODUCER,
    SCHEMA_VERSION,
    assert_shadow_frontier_not_production_consumer,
    build_canonical_marginal_capital_frontier_payload,
    stable_payload_hash,
    write_canonical_marginal_capital_frontier_artifact,
)


BUSINESS_DATE = "2026-08-28"


def test_phase32_as_shadow_frontier_builds_all_required_candidate_types_and_is_non_authoritative(tmp_path: Path) -> None:
    pc = _pc([_new("10010"), _reentry("20020"), _add("30030", current_quantity=100)])
    original = copy.deepcopy(pc)

    payload = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=pc,
        cash_payload={"available_cash": 1_000_000.0},
    )
    path = write_canonical_marginal_capital_frontier_artifact(payload, tmp_path / "canonical_marginal_capital_frontier.json")
    stored = json.loads(path.read_text(encoding="utf-8"))

    semantic_types = {row["semantic_type"] for row in stored["frontier_candidates"]}
    assert stored["schema_version"] == SCHEMA_VERSION
    assert stored["artifact_mode"] == ARTIFACT_MODE
    assert stored["producer"] == PRODUCER
    assert {"NEW_FIRST_LOT", "REENTRY_FIRST_LOT", "ADD_NEXT_LOT", "CASH_OPTIONALITY"} <= semantic_types
    assert stored["feeds_position_sizing"] is False
    assert stored["feeds_runtime_planning"] is False
    assert stored["feeds_pending"] is False
    assert stored["feeds_orders"] is False
    assert stored["feeds_execution"] is False
    assert stored["feeds_safety_authority"] is False
    assert stored["production_consumer_count"] == 0
    assert assert_shadow_frontier_not_production_consumer(stored) is True
    assert pc == original


def test_phase32_as_repeated_add_next_lots_recompute_hypothetical_state_and_diminish_headroom() -> None:
    payload = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_add("30030", current_quantity=100, current_weight=0.05, single_name_cap=0.50)]),
        cash_payload={"available_cash": 1_000_000.0},
        max_add_lots_per_position=3,
    )

    add_rows = [row for row in payload["frontier_candidates"] if row["semantic_type"] == "ADD_NEXT_LOT"]
    assert [row["increment_index"] for row in add_rows] == [1, 2, 3]
    assert [(row["pre_quantity"], row["post_quantity"]) for row in add_rows] == [(100, 200), (200, 300), (300, 400)]
    headroom = [row["diminishing_marginal_context"]["headroom_after"] for row in add_rows]
    cash_after = [row["diminishing_marginal_context"]["cash_after"] for row in add_rows]
    assert headroom[0] > headroom[1] > headroom[2]
    assert cash_after[0] > cash_after[1] > cash_after[2]
    assert all(row["hypothetical_only"] is True for row in add_rows)
    assert all(row["portfolio_state_mutated"] is False for row in add_rows)


def test_phase32_br_add_repeated_lots_use_executable_increment_for_next_pre_state() -> None:
    payload = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_add("94340", current_quantity=700, current_weight=0.10, single_name_cap=0.50)]),
        position_sizing_payload={"positions": [{"security_code": "94340", "trading_unit": 100, "transaction_quantity_candidate": 200}]},
        cash_payload={"available_cash": 1_000_000.0},
        max_add_lots_per_position=3,
    )

    add_rows = [row for row in payload["frontier_candidates"] if row["semantic_type"] == "ADD_NEXT_LOT"]
    assert [(row["pre_quantity"], row["post_quantity"], row["increment_quantity"]) for row in add_rows] == [
        (700, 900, 200),
        (900, 1100, 200),
        (1100, 1300, 200),
    ]
    assert all(row["increment_quantity_source_authority"] == "PS_PREFLIGHT_TRANSACTION_QUANTITY_CANDIDATE" for row in add_rows)


def test_phase32_as_cash_can_win_without_forcing_security_deployment() -> None:
    payload = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010", rank=1), _add("30030", current_quantity=100)]),
        cash_payload={"available_cash": 1_000_000.0, "cash_preferred": True},
    )

    winner = _winner(payload)
    assert winner["semantic_type"] == "CASH_OPTIONALITY"
    assert payload["frontier_result"]["cash_frontier_disposition"] == "SHADOW_WINNER"
    assert payload["shadow_target_projection"]["accepted_shadow_candidate_count"] == 0


def test_phase32_as_cap_and_insufficient_cash_blocks_preserve_desirability() -> None:
    payload = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(
            [
                _add("30030", current_quantity=100, current_weight=0.19, single_name_cap=0.20, reference_price=2_000.0),
                _new("40040", reference_price=5_000.0, single_name_cap=1.0),
            ]
        ),
        cash_payload={"available_cash": 100_000.0},
    )

    by_symbol = {row["symbol"]: row for row in payload["frontier_candidates"] if row["semantic_type"] != "CASH_OPTIONALITY"}
    assert by_symbol["30030"]["shadow_disposition"] == "INFEASIBLE_CAP_BLOCKED"
    assert by_symbol["30030"]["desirability"]["category"] == "DESIRABILITY"
    assert by_symbol["30030"]["feasibility"]["category"] == "FEASIBILITY"
    assert by_symbol["40040"]["shadow_disposition"] == "INFEASIBLE_INSUFFICIENT_CASH"


def test_phase32_as_safety_and_risk_pacing_blocks_are_explicit() -> None:
    safety_payload = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010")]),
        safety_payload={"status": "BLOCK"},
        cash_payload={"available_cash": 1_000_000.0},
    )
    risk_payload = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([_new("10010")]),
        risk_pacing_payload={"status": "BLOCK"},
        cash_payload={"available_cash": 1_000_000.0},
    )

    assert _candidate(safety_payload, "10010")["shadow_disposition"] == "INELIGIBLE_SAFETY_BLOCKED"
    assert _candidate(risk_payload, "10010")["shadow_disposition"] == "INELIGIBLE_RISK_PACING_BLOCKED"


def test_phase32_as_missing_campaign_identity_fails_closed_for_add() -> None:
    row = _add("30030", current_quantity=100)
    row.pop("position_campaign_id")

    payload = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([row]),
        cash_payload={"available_cash": 1_000_000.0},
    )

    add = _candidate(payload, "30030")
    assert add["shadow_disposition"] == "REVIEW_REQUIRED"
    assert "stale_or_missing_campaign_identity" in add["constraints"]["reason_codes"]
    assert "missing_position_campaign_id" in add["observability"]["reason_codes"]


def test_phase32_as_stable_ids_and_deterministic_rerun_ignore_input_order() -> None:
    members = [_new("10010", rank=2), _reentry("20020", rank=1), _add("30030", current_quantity=100, rank=3)]
    first = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(members),
        cash_payload={"available_cash": 1_000_000.0},
    )
    second = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc(list(reversed(members))),
        cash_payload={"available_cash": 1_000_000.0},
    )

    assert first["artifact_hash"] == second["artifact_hash"]
    assert first["determinism_key"] == second["determinism_key"]
    assert [row["candidate_id"] for row in first["frontier_candidates"]] == [
        row["candidate_id"] for row in second["frontier_candidates"]
    ]
    assert stable_payload_hash(first) == first["artifact_hash"]


def test_phase32_as_forbidden_outcome_fields_are_not_lineage_inputs() -> None:
    member = _new("10010", future_return=0.8, fill_outcome="WINNER")
    payload = build_canonical_marginal_capital_frontier_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_payload=_pc([member]),
        cash_payload={"available_cash": 1_000_000.0},
    )
    candidate = _candidate(payload, "10010")

    assert payload["future_information_used"] is False
    assert payload["historical_outcome_used"] is False
    assert "future_return" not in candidate["lineage"]["raw_evidence"]
    assert "fill_outcome" not in candidate["lineage"]["raw_evidence"]


def _winner(payload: dict) -> dict:
    return next(row for row in payload["frontier_candidates"] if row["shadow_disposition"] == "SHADOW_WINNER")


def _candidate(payload: dict, symbol: str) -> dict:
    return next(row for row in payload["frontier_candidates"] if row["symbol"] == symbol)


def _pc(members: list[dict]) -> dict:
    return {
        "portfolio_value": 1_000_000.0,
        "portfolio_members": members,
        "portfolio_policy_allocation_authority": {
            "risk_pacing_evidence": {
                "risk_pacing_intent": "NORMAL_DEPLOYMENT",
                "market_quality_state": "HEALTHY",
            }
        },
    }


def _new(symbol: str, *, rank: int = 2, reference_price: float = 1_000.0, **overrides) -> dict:
    row = {
        "security_code": symbol,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "semantic_buy_type": "BUY_NEW",
        "candidate_id": f"candidate-{symbol}",
        "runtime_opportunity_score": 0.9,
        "input_opportunity_rank": rank,
        "quality_score": 0.8,
        "entry_admission_action": "FULL_ALLOCATION_ELIGIBLE",
        "entry_admission_state": "HEALTHY_CONTINUATION_ENTRY",
        "entry_admission_evidence_sufficiency": "SUFFICIENT",
        "target_weight": 0.05,
        "single_name_cap": overrides.pop("single_name_cap", 0.30),
        "reference_price": reference_price,
        "trading_unit": 100,
    }
    row.update(overrides)
    return row


def _reentry(symbol: str, *, rank: int = 1, reference_price: float = 1_000.0, **overrides) -> dict:
    row = _new(symbol, rank=rank, reference_price=reference_price)
    row.update(
        {
            "semantic_buy_type": "REENTRY",
            "reentry_recovery_status": "PASS",
            "previous_exit_reason_class": "TREND_AND_OPPORTUNITY_BROKEN",
        }
    )
    row.update(overrides)
    return row


def _add(
    symbol: str,
    *,
    current_quantity: int,
    current_weight: float = 0.05,
    single_name_cap: float = 0.30,
    rank: int = 3,
    reference_price: float = 1_000.0,
    **overrides,
) -> dict:
    row = {
        "security_code": symbol,
        "current_position": True,
        "membership_intent": "RETAIN",
        "pm_action": "ADD",
        "position_campaign_id": f"pc-{symbol}-0001",
        "pm_decision_id": f"pm-{symbol}",
        "current_quantity": current_quantity,
        "current_weight": current_weight,
        "target_weight": current_weight,
        "single_name_cap": single_name_cap,
        "runtime_opportunity_score": 0.85,
        "input_opportunity_rank": rank,
        "quality_score": 0.78,
        "expected_edge_improvement_state": "IMPROVING",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "add_allocation_eligibility_status": "PASS",
        "same_campaign_continuation_status": "CONTINUING",
        "no_loss_averaging_status": "PASS",
        "reference_price": reference_price,
        "trading_unit": 100,
    }
    row.update(overrides)
    return row
