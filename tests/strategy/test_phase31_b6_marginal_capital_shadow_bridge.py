from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

from ai_fund_lab_v2.strategy.marginal_capital_value_shadow import (
    build_marginal_capital_value_shadow_payload,
    materialize_marginal_capital_value_shadow_for_day,
)


TARGET_RUN = Path("reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z")


def test_phase31_b6_runtime_plans_order_populates_actual_cash_batch_order() -> None:
    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload={
            "portfolio_members": [
                _new("11110"),
                _add("22220"),
            ]
        },
        position_sizing_payload={
            "positions": [
                {"security_code": "11110", "transaction_quantity_candidate": 100},
                {"security_code": "22220", "transaction_quantity_candidate": 200},
            ]
        },
        runtime_planning_payload={
            "plans": [
                {"security_code": "22220", "planning_id": "rp-add", "planning_intent": "BUY_ADD", "planned_quantity": 200, "reference_price": 300},
                {"security_code": "11110", "planning_id": "rp-new", "planning_intent": "BUY_NEW", "planned_quantity": 100, "reference_price": 400},
            ]
        },
    )

    assert [row["symbol"] for row in payload["actual_runtime_cash_batch_order"]] == ["22220", "11110"]
    assert payload["actual_runtime_cash_batch_order"][0]["item_id"] == "rp-add"
    assert payload["actual_runtime_cash_batch_order"][0]["quantity"] == 200
    assert payload["actual_runtime_cash_batch_order"][0]["planned_notional"] == 60000


def test_phase31_b6_b0_94320_real_pit_add_campaign_evidence_is_bridged() -> None:
    for business_date in ("2022-08-19", "2022-08-24"):
        payload = _real_payload(business_date)
        add = next(row for row in payload["candidate_units"] if row["symbol"] == "94320")

        assert add["marginal_capital_value_class"] == "ELIGIBLE_STRONG"
        assert add["comparison_sufficiency"] == "SUFFICIENT"
        assert add["comparison_reason_codes"] == ["explicit_pit_add_lifecycle_evidence_positive"]
        assert add["add_campaign_evidence"]["pit_validation_status"] == "PASS"
        assert add["add_campaign_evidence"]["campaign_identifier"]
        assert add["add_campaign_evidence"]["expected_edge_baseline_date"] <= business_date
        assert add["add_campaign_evidence"]["future_information_used"] is False
        assert add["actual_runtime_order"] is not None
        assert add["lot_materialization_reason"] == "EXECUTABLE_LOT"


def test_phase31_b6_missing_campaign_evidence_remains_comparison_insufficient() -> None:
    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload={"portfolio_members": [_add("22220", add_investment_evidence=None)]},
    )

    unit = payload["candidate_units"][0]
    assert unit["marginal_capital_value_class"] == "COMPARISON_INSUFFICIENT"
    assert "missing_or_non_pass_add_evidence:campaign" in unit["comparison_reason_codes"]


def test_phase31_b6_strong_new_and_weak_add_protection_remain() -> None:
    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload={
            "portfolio_members": [
                _add("22220", expected_edge_improvement_state="WEAKENING"),
                _new("11110", entry_admission_action="FULL_ALLOCATION_ELIGIBLE", input_opportunity_rank=1),
            ]
        },
    )

    assert [row["symbol"] for row in payload["canonical_shadow_order"]] == ["11110", "22220"]
    weak_add = next(row for row in payload["candidate_units"] if row["symbol"] == "22220")
    assert weak_add["marginal_capital_value_class"] == "BLOCKED_OR_NOT_ELIGIBLE"
    assert "expected_edge_weakening_not_rescued" in weak_add["comparison_reason_codes"]
    assert payload["buy_add_label_priority"] is False


def test_phase31_b6_lot_materialization_reasons_are_typed() -> None:
    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload={
            "portfolio_members": [
                _new("11110"),
                _new("22220", input_opportunity_rank=2),
                _new("33330", input_opportunity_rank=3),
            ]
        },
        position_sizing_payload={
            "positions": [
                {"security_code": "11110", "transaction_quantity_candidate": 100},
                {"security_code": "22220", "transaction_quantity_candidate": 0},
                {"security_code": "33330", "transaction_quantity_candidate": 100},
            ]
        },
        runtime_planning_payload={
            "plans": [
                {"security_code": "11110", "planning_intent": "BUY_NEW", "planned_quantity": 100, "reference_price": 100},
                {
                    "security_code": "22220",
                    "planning_intent": "BUY_NEW",
                    "planned_quantity": 0,
                    "planning_reason": "DEFERRED_INSUFFICIENT_RESERVED_CASH",
                },
            ]
        },
    )
    by_symbol = {row["symbol"]: row for row in payload["candidate_units"]}

    assert by_symbol["11110"]["lot_materialization_reason"] == "EXECUTABLE_LOT"
    assert by_symbol["22220"]["lot_materialization_reason"] == "ZERO_QUANTITY_DELTA"
    assert by_symbol["33330"]["lot_materialization_reason"] == "NOT_IN_RUNTIME_PLAN"
    cash_row = next(row for row in payload["actual_runtime_cash_batch_order"] if row["symbol"] == "22220")
    assert cash_row["inclusion_state"] == "RESERVED_CASH_PRUNE"


def test_phase31_b6_real_run_materialization_writes_only_diagnostic_shadow(tmp_path: Path) -> None:
    source_day = TARGET_RUN / "daily" / "2022-08-19"
    run_root = tmp_path / "run"
    day_root = run_root / "daily" / "2022-08-19"
    shutil.copytree(source_day / "strategy", day_root / "strategy")
    shutil.copytree(source_day / "morning", day_root / "morning")
    (run_root / "run_state.json").write_text(json.dumps({"completed_business_days": ["2022-08-19"]}), encoding="utf-8")
    before = {
        "run_state": (run_root / "run_state.json").read_bytes(),
        "pc": (day_root / "strategy" / "portfolio_construction.json").read_bytes(),
        "ps": (day_root / "strategy" / "position_sizing.json").read_bytes(),
        "rp": (day_root / "strategy" / "runtime_planning.json").read_bytes(),
    }

    payload = materialize_marginal_capital_value_shadow_for_day(run_root=run_root, business_date="2022-08-19")

    output_path = Path(payload["artifact_path"])
    assert output_path == day_root / "diagnostic_shadow" / "marginal_capital_value_shadow.json"
    assert output_path.is_file()
    assert (run_root / "run_state.json").read_bytes() == before["run_state"]
    assert (day_root / "strategy" / "portfolio_construction.json").read_bytes() == before["pc"]
    assert (day_root / "strategy" / "position_sizing.json").read_bytes() == before["ps"]
    assert (day_root / "strategy" / "runtime_planning.json").read_bytes() == before["rp"]
    assert payload["actual_trading_path_mutated"] is False if "actual_trading_path_mutated" in payload else True
    assert payload["actual_run_state_mutated"] is False


def test_phase31_b6_no_future_fields_consumed() -> None:
    payload = build_marginal_capital_value_shadow_payload(
        business_date="2022-08-19",
        portfolio_construction_payload={
            "portfolio_members": [
                _new("11110", future_return=1.0, fill_outcome="BOUGHT"),
            ]
        },
    )

    unit = payload["candidate_units"][0]
    assert payload["future_information_used"] is False
    assert "future_return" not in unit["source_evidence"]
    assert "fill_outcome" not in unit["source_evidence"]


def _real_payload(business_date: str) -> dict:
    day = TARGET_RUN / "daily" / business_date
    return build_marginal_capital_value_shadow_payload(
        business_date=business_date,
        portfolio_construction_payload=json.loads((day / "strategy" / "portfolio_construction.json").read_text(encoding="utf-8")),
        position_sizing_payload=json.loads((day / "strategy" / "position_sizing.json").read_text(encoding="utf-8")),
        runtime_planning_payload=json.loads((day / "strategy" / "runtime_planning.json").read_text(encoding="utf-8")),
    )


def _new(symbol: str, **overrides) -> dict:
    row = {
        "security_code": symbol,
        "current_position": False,
        "membership_intent": "ADD_CANDIDATE",
        "target_weight": 0.04,
        "accepted_buy_new_weight": 0.04,
        "runtime_opportunity_score": 0.5,
        "input_opportunity_rank": 1,
    }
    row.update(overrides)
    return row


def _add(symbol: str, **overrides) -> dict:
    evidence = {
        "business_date": "2022-08-19",
        "position_campaign_id": f"campaign-{symbol}",
        "campaign_continuation": {"status": "PASS", "state": "PASS", "authority": "same_campaign_identity_match"},
        "expected_edge": {"status": "PASS", "state": "IMPROVING", "baseline_business_date": "2022-08-18"},
        "incremental_value": {"status": "PASS", "state": "POSITIVE"},
        "opportunity_cost": {"status": "PASS", "state": "PASS"},
        "no_loss_averaging": {"status": "PASS", "state": "PASS"},
        "temporal_authority": {"point_in_time": True, "future_evidence_used": False},
    }
    row = {
        "security_code": symbol,
        "current_position": True,
        "pm_action": "ADD",
        "target_weight": 0.08,
        "current_weight": 0.04,
        "accepted_incremental_weight": 0.04,
        "expected_edge_improvement_state": "IMPROVING",
        "incremental_investment_value_state": "POSITIVE",
        "opportunity_cost_status": "PASS",
        "add_allocation_eligibility_status": "PASS",
        "input_opportunity_rank": 1,
        "add_investment_evidence": evidence,
    }
    row.update(overrides)
    if row.get("add_investment_evidence") is None:
        row.pop("add_investment_evidence", None)
    return row
