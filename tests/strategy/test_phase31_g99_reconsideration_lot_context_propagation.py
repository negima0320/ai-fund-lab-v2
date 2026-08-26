from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ai_fund_lab_v2.strategy.portfolio_construction import build_capital_competition_framework


TARGET_RUN = "runtime-test-historical-extended-smoke-20260824T121719329586Z"
G80_REFERENCE_RUN = "runtime-test-historical-extended-smoke-20260823T140946562431Z"


def test_phase31_g99_actual_reconsideration_rows_receive_canonical_lot_context() -> None:
    states = Counter()
    projected_nonzero = 0
    positive_rows = 0

    for business_date in _completed_business_dates(TARGET_RUN):
        multi = _producer_equivalent_multi(TARGET_RUN, business_date)
        compatibility_by_key = _compatibility_by_key(multi)
        for row in _g97_positive_allocations(multi):
            positive_rows += 1
            compatibility = compatibility_by_key[(row["competitor_type"], row["symbol"])]
            states[compatibility["compatibility_state"]] += 1
            projected_nonzero += int((compatibility.get("projected_quantity_delta_evidence_only") or 0) > 0)

    assert positive_rows == 142
    assert states["INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED"] == 0
    assert states["LOT_EXECUTABLE_COMPATIBLE"] > 0
    assert states["LOT_INFEASIBLE_RESIDUAL_REQUIRED"] > 0
    assert projected_nonzero == states["LOT_EXECUTABLE_COMPATIBLE"]


def test_phase31_g99_anchor_rows_no_longer_fail_for_missing_lot_context() -> None:
    anchors = {
        "2023-03-22": {"94320": "LOT_EXECUTABLE_COMPATIBLE"},
        "2023-04-07": {
            "83060": "LOT_INFEASIBLE_RESIDUAL_REQUIRED",
            "77760": "LOT_INFEASIBLE_RESIDUAL_REQUIRED",
            "44440": "LOT_INFEASIBLE_RESIDUAL_REQUIRED",
        },
        "2023-04-14": {"94320": "LOT_EXECUTABLE_COMPATIBLE"},
        "2023-04-18": {"59350": "LOT_INFEASIBLE_RESIDUAL_REQUIRED"},
    }

    for business_date, expected_by_symbol in anchors.items():
        multi = _producer_equivalent_multi(TARGET_RUN, business_date)
        compatibility_by_key = _compatibility_by_key(multi)
        allocations = {row["symbol"]: row for row in _g97_positive_allocations(multi)}
        for symbol, expected_state in expected_by_symbol.items():
            row = allocations[symbol]
            compatibility = compatibility_by_key[(row["competitor_type"], symbol)]

            assert compatibility["compatibility_state"] == expected_state
            assert compatibility["compatibility_state"] != "INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED"
            assert compatibility["reference_price"] > 0
            assert compatibility["portfolio_value"] > 0
            assert compatibility["minimum_executable_weight"] > 0
            assert row["lot_sizing_context"]["portfolio_value"] == compatibility["portfolio_value"]
            assert row["lot_sizing_context"]["reference_price"] == compatibility["reference_price"]
            assert compatibility["pc_quantity_authority"] is False
            assert multi["capital_conservation"]["status"] == "PASS"


def test_phase31_g99_cash_defer_and_safety_terminal_preserved() -> None:
    expected_cash = {
        "2023-04-05": {"83060", "59350", "77760", "44440"},
        "2023-04-06": {"83060", "59350", "43880", "94340", "77760"},
    }
    for business_date, symbols in expected_cash.items():
        multi = _producer_equivalent_multi(TARGET_RUN, business_date)
        allocations = {row["symbol"] for row in _g97_positive_allocations(multi)}
        deferrals = {
            row["symbol"]: row
            for row in multi["cash_preferred_security_deferrals"]
            if row.get("residual_reconsideration_authoritative_binding")
        }

        assert symbols.isdisjoint(allocations)
        assert symbols <= set(deferrals)
        assert all(deferrals[symbol]["authorized_allocation_weight"] == 0.0 for symbol in symbols)
        assert all(deferrals[symbol]["participation_deferral_resolution"] == "CASH_PREFERRED_DEFER" for symbol in symbols)

    multi_0406 = _producer_equivalent_multi(TARGET_RUN, "2023-04-06")
    terminals = {
        row["symbol"]: row
        for row in multi_0406["residual_reconsideration_authoritative_binding_evidence"]["terminal_rows"]
    }
    assert terminals["67310"]["source_shadow_outcome"] == "SHADOW_SAFETY_TERMINAL"
    assert multi_0406["residual_reconsideration_authoritative_binding_evidence"]["safety_terminal_resurrection_count"] == 0


def test_phase31_g99_known_g80_weak_tail_not_resurrected() -> None:
    expected_weak_tail_symbols = {
        "2023-07-21": {"14390"},
        "2023-07-24": {"69320"},
        "2023-08-01": {"37600", "87500"},
    }
    resurrected = 0
    for business_date, symbols in expected_weak_tail_symbols.items():
        multi = _producer_equivalent_multi(G80_REFERENCE_RUN, business_date)
        allocations = {row["symbol"] for row in _g97_positive_allocations(multi)}
        resurrected += len(symbols & allocations)

    assert resurrected == 0


def _producer_equivalent_multi(run_id: str, business_date: str) -> dict[str, object]:
    strategy_dir = Path("reports/runtime_tests/runs") / run_id / "daily" / business_date / "strategy"
    pc = json.loads((strategy_dir / "portfolio_construction.json").read_text())
    risk_pacing_evidence = (pc.get("portfolio_policy_allocation_authority") or {}).get("risk_pacing_evidence") or {}
    multi = pc["capital_competition"]["canonical_multi_allocation_deployment_set"]
    competition = build_capital_competition_framework(
        members=pc["portfolio_members"],
        target_gross_exposure=pc.get("target_gross_exposure"),
        total_target_weight=pc.get("total_target_weight")
        or sum(float(row.get("target_weight") or 0.0) for row in pc["portfolio_members"]),
        business_date=business_date,
        incremental_budget_evidence={"available_incremental_budget": multi.get("available_incremental_budget")},
        lot_reallocation_evidence=pc.get("lot_aware_final_reallocation") or {},
        risk_pacing_evidence=risk_pacing_evidence,
    )
    return competition["canonical_multi_allocation_deployment_set"]


def _completed_business_dates(run_id: str) -> list[str]:
    daily = Path("reports/runtime_tests/runs") / run_id / "daily"
    return sorted(path.name for path in daily.iterdir() if (path / "strategy" / "portfolio_construction.json").is_file())


def _g97_positive_allocations(multi: dict[str, object]) -> list[dict[str, object]]:
    return [
        row
        for row in multi["security_allocations"]
        if row.get("residual_reconsideration_authoritative_binding")
    ]


def _compatibility_by_key(multi: dict[str, object]) -> dict[tuple[str, str], dict[str, object]]:
    compatibility = multi["lot_aware_allocation_to_sizing_compatibility"]
    return {
        (row["competitor_type"], row["symbol"]): row
        for row in compatibility["compatibility_rows"]
    }
