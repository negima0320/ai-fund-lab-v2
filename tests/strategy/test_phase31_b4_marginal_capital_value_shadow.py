from __future__ import annotations

import copy
import json
from pathlib import Path

from ai_fund_lab_v2.strategy.marginal_capital_value_shadow import (
    AUTHORITY_TYPE,
    MODE,
    PRODUCER,
    build_marginal_capital_value_shadow_payload,
    write_marginal_capital_value_shadow_artifact,
)


def test_phase31_b4_shadow_artifact_produced_and_non_mutating(tmp_path: Path) -> None:
    pc, ps, rp, pending = _base_inputs()
    originals = copy.deepcopy((pc, ps, rp, pending))

    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload=pc,
        position_sizing_payload=ps,
        runtime_planning_payload=rp,
        pending_payload=pending,
        source_artifacts={"portfolio_construction": "strategy/portfolio_construction.json"},
        source_hashes={"portfolio_construction": "sha256:pc"},
    )
    path = write_marginal_capital_value_shadow_artifact(payload, tmp_path / "strategy" / "marginal_capital_value_shadow.json")

    assert path.is_file()
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["producer"] == PRODUCER
    assert stored["authority_type"] == AUTHORITY_TYPE
    assert stored["mode"] == MODE
    assert stored["future_information_used"] is False
    assert stored["actual_decision_mutated"] is False
    assert stored["actual_pc_decision_mutated"] is False
    assert stored["actual_ps_quantity_mutated"] is False
    assert stored["actual_runtime_order_mutated"] is False
    assert stored["actual_pending_mutated"] is False
    assert stored["actual_submit_or_execution_mutated"] is False
    assert (pc, ps, rp, pending) == originals


def test_phase31_b4_buy_add_and_buy_new_labels_alone_do_not_raise_priority() -> None:
    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload={
            "portfolio_members": [
                _member("22220", current_position=True, pm_action="ADD", accepted_incremental_weight=0.03),
                _member("11110", current_position=False, membership_intent="ADD_CANDIDATE", target_weight=0.03, accepted_buy_new_weight=0.03),
            ]
        },
    )

    by_symbol = {row["symbol"]: row for row in payload["candidate_units"]}
    assert by_symbol["22220"]["marginal_capital_value_class"] == "COMPARISON_INSUFFICIENT"
    assert by_symbol["11110"]["marginal_capital_value_class"] == "COMPARISON_INSUFFICIENT"
    assert payload["buy_add_label_priority"] is False
    assert payload["buy_new_label_priority"] is False
    assert [row["symbol"] for row in payload["canonical_shadow_order"]] == ["11110", "22220"]


def test_phase31_b4_strong_new_can_outrank_weak_add() -> None:
    pc = {
        "portfolio_members": [
            _member(
                "94320",
                current_position=True,
                pm_action="ADD",
                accepted_incremental_weight=0.04,
                expected_edge_improvement_state="WEAKENING",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
                construction_priority=1,
            ),
            _member(
                "60980",
                current_position=False,
                membership_intent="ADD_CANDIDATE",
                target_weight=0.04,
                accepted_buy_new_weight=0.04,
                entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
                input_opportunity_rank=1,
                construction_priority=2,
            ),
        ]
    }

    payload = build_marginal_capital_value_shadow_payload(business_date="2022-08-19", portfolio_construction_payload=pc)

    assert [row["symbol"] for row in payload["canonical_shadow_order"]] == ["60980", "94320"]
    add = next(row for row in payload["candidate_units"] if row["symbol"] == "94320")
    assert add["marginal_capital_value_class"] == "BLOCKED_OR_NOT_ELIGIBLE"
    assert "expected_edge_weakening_not_rescued" in add["comparison_reason_codes"]
    assert payload["b0_development_cases_reproducible"] is True


def test_phase31_b4_strong_add_can_outrank_comparable_new_only_with_explicit_pit_lifecycle_evidence() -> None:
    pc = {
        "portfolio_members": [
            _member(
                "22220",
                current_position=False,
                membership_intent="ADD_CANDIDATE",
                target_weight=0.04,
                accepted_buy_new_weight=0.04,
                runtime_opportunity_score=0.7,
                input_opportunity_rank=1,
                construction_priority=1,
            ),
            _member(
                "33330",
                current_position=True,
                pm_action="ADD",
                accepted_incremental_weight=0.04,
                expected_edge_improvement_state="IMPROVING",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
                add_allocation_eligibility_status="PASS",
                same_campaign_continuation_status="CONTINUING",
                construction_priority=2,
            ),
        ]
    }

    payload = build_marginal_capital_value_shadow_payload(business_date="2022-08-19", portfolio_construction_payload=pc)

    assert [row["symbol"] for row in payload["canonical_shadow_order"]] == ["33330", "22220"]
    add = next(row for row in payload["candidate_units"] if row["symbol"] == "33330")
    assert add["marginal_capital_value_class"] == "ELIGIBLE_STRONG"
    assert add["comparison_sufficiency"] == "SUFFICIENT"


def test_phase31_b4_zero_increment_add_is_not_fabricated_as_shadow_candidate() -> None:
    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload={
            "portfolio_members": [
                _member(
                    "94320",
                    current_position=True,
                    pm_action="ADD",
                    accepted_incremental_weight=0.0,
                    expected_edge_improvement_state="IMPROVING",
                    incremental_investment_value_state="POSITIVE",
                    opportunity_cost_status="PASS",
                ),
                _member(
                    "60980",
                    current_position=False,
                    membership_intent="ADD_CANDIDATE",
                    target_weight=0.04,
                    accepted_buy_new_weight=0.04,
                    entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
                    input_opportunity_rank=1,
                ),
            ]
        },
    )

    assert [row["symbol"] for row in payload["candidate_units"]] == ["60980"]


def test_phase31_b4_comparison_insufficient_is_explicit_and_shadow_difference_observable() -> None:
    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload={
            "portfolio_members": [
                _member("22220", current_position=True, pm_action="ADD", accepted_incremental_weight=0.03, construction_priority=1),
                _member(
                    "11110",
                    current_position=False,
                    membership_intent="ADD_CANDIDATE",
                    target_weight=0.03,
                    accepted_buy_new_weight=0.03,
                    entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
                    input_opportunity_rank=1,
                    construction_priority=2,
                ),
            ]
        },
        runtime_planning_payload={"cash_batch": [{"symbol": "22220", "side": "BUY"}, {"symbol": "11110", "side": "BUY"}]},
    )

    add = next(row for row in payload["candidate_units"] if row["symbol"] == "22220")
    assert add["marginal_capital_value_class"] == "COMPARISON_INSUFFICIENT"
    assert payload["comparison_status"] == "COMPARISON_INSUFFICIENT_PRESENT"
    assert any(row["classification"] != "NO_DIFFERENCE" for row in payload["order_differences"])


def test_phase31_b4_does_not_consume_future_or_outcome_fields_and_preserves_lot_evidence() -> None:
    pc = {
        "portfolio_members": [
            _member(
                "55550",
                current_position=False,
                membership_intent="ADD_CANDIDATE",
                target_weight=0.04,
                accepted_buy_new_weight=0.04,
                entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
                input_opportunity_rank=1,
                future_return=0.5,
                fill_outcome="BOUGHT",
                lot_first_feasibility_classification="PASS",
            )
        ]
    }
    ps = {
        "positions": [
            {
                "security_code": "55550",
                "transaction_quantity_candidate": 100,
                "quantity_delta_candidate": 100,
                "phase29_l19_lot_resolution": {"one_lot_feasibility_status": "PASS"},
            }
        ]
    }

    payload = build_marginal_capital_value_shadow_payload(business_date="2022-08-19", portfolio_construction_payload=pc, position_sizing_payload=ps)
    unit = payload["candidate_units"][0]

    assert payload["future_information_used"] is False
    assert "future_return" not in unit["source_evidence"]
    assert "fill_outcome" not in unit["source_evidence"]
    assert unit["lot_aware_quantity_requirement"]["ps_transaction_quantity_candidate"] == 100
    assert unit["lot_feasibility"] == "PASS"


def test_phase31_b4_caps_buy_sell_independence_and_pending_membership_are_observability_only() -> None:
    pc, ps, rp, pending = _base_inputs()

    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload=pc,
        position_sizing_payload=ps,
        runtime_planning_payload=rp,
        pending_payload=pending,
    )

    assert payload["normal_strategy_cap_changed"] is False
    assert payload["safety_hard_cap_changed"] is False
    assert payload["buy_sell_independence_preserved"] is True
    assert {"symbol": "99990", "side": "SELL", "status": "PENDING"} in payload["actual_pending_membership"]
    assert all(row["lifecycle_intent"] in {"BUY_NEW", "BUY_ADD"} for row in payload["candidate_units"])


def _base_inputs() -> tuple[dict, dict, dict, dict]:
    pc = {
        "portfolio_members": [
            _member(
                "60980",
                current_position=False,
                membership_intent="ADD_CANDIDATE",
                target_weight=0.04,
                accepted_buy_new_weight=0.04,
                entry_admission_action="FULL_ALLOCATION_ELIGIBLE",
                input_opportunity_rank=1,
                construction_priority=1,
            ),
            _member(
                "94320",
                current_position=True,
                pm_action="ADD",
                current_weight=0.08,
                target_weight=0.12,
                accepted_incremental_weight=0.04,
                expected_edge_improvement_state="IMPROVING",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
                add_allocation_eligibility_status="PASS",
                same_campaign_continuation_status="CONTINUING",
                construction_priority=2,
            ),
        ]
    }
    ps = {
        "positions": [
            {"security_code": "60980", "transaction_quantity_candidate": 100, "quantity_delta_candidate": 100},
            {"security_code": "94320", "transaction_quantity_candidate": 100, "quantity_delta_candidate": 100},
        ]
    }
    rp = {"cash_batch": [{"symbol": "60980", "side": "BUY"}, {"symbol": "94320", "side": "BUY"}]}
    pending = {"pending_orders": [{"symbol": "99990", "side": "SELL", "status": "PENDING"}]}
    return pc, ps, rp, pending


def _member(symbol: str, **overrides) -> dict:
    row = {
        "security_code": symbol,
        "current_position": False,
        "membership_intent": "EXCLUDE",
        "pm_action": "",
        "current_weight": 0.0,
        "target_weight": 0.0,
        "construction_priority": 1,
    }
    row.update(overrides)
    return row
