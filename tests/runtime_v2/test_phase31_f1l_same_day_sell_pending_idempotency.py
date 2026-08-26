from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import attach_approval_link, promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import SellExitDecision, run_sell_planning_pending_pipeline


BUSINESS_DATE = "2022-09-07"
MULTI_SELL_DATE = "2022-10-12"
COMPOSITE_DATE = "2022-08-23"


def test_phase31_f1l_93600_equivalent_same_day_sell_exit_pending_reused(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93600", quantity=100, price=1429)
    existing = _write_existing_pending(
        runtime_root,
        items=(
            _pending_item(
                "strategy-c8537cd09201c855e2b4",
                "93600",
                "SELL",
                100,
                source_decision_type="SELL_EXIT",
                planning_authority_source="rp-2022-09-07-93600-sell_exit-816e30699b8499ff",
                state="CREATED",
            ),
        ),
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    after = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")
    continuity = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "pending_continuity_evidence.json")
    equivalence = _load_json(
        runtime_root
        / "runtime_state"
        / "sell_pipeline"
        / BUSINESS_DATE
        / "same_day_sell_pending_equivalence_evidence.json"
    )

    assert result.status == "PASS"
    assert result.pending_plan_id == existing.pending_plan_id
    assert result.pending_composition_model == "SAME_DAY_EQUIVALENT_SELL_PENDING_IDEMPOTENCY"
    assert result.pending_composition_status == "PASS"
    assert result.selected_symbols == ("93600",)
    assert before == after
    assert continuity["pending_reconciliation"]["pending_equivalence_status"] == "EQUIVALENT"
    assert continuity["pending_reconciliation"]["resolution_action"] == "REUSE_EXISTING_PENDING"
    assert continuity["original_pending_preserved"] is True
    assert continuity["pending_reconciliation"]["duplicate_pending_created"] is False
    assert equivalence["quantity_equivalence"] == "FULL_EXIT_QUANTITY_MATCHES_CURRENT_POSITION"


def test_phase31_f1o_actual_path_non_executable_reduce_reuses_equivalent_sell_exit_pending(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93600", quantity=100, price=1429)
    existing = _write_existing_pending(
        runtime_root,
        items=(
            _pending_item(
                "strategy-c8537cd09201c855e2b4",
                "93600",
                "SELL",
                100,
                source_decision_type="SELL_EXIT",
                planning_authority_source="rp-2022-09-07-93600-sell_exit-816e30699b8499ff",
                state="CREATED",
            ),
        ),
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="93600",
                quantity=0,
                reason="risk_increased_but_trend_not_broken",
                source_decision="REDUCE",
                reduce_intensity="LIGHT",
                source_decision_id="pm-2022-09-07-93600-reduce",
            ),
        ),
        environment_capability_context=_historical_context(tmp_path),
    )

    after = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")
    continuity = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "pending_continuity_evidence.json")
    equivalence = _load_json(
        runtime_root
        / "runtime_state"
        / "sell_pipeline"
        / BUSINESS_DATE
        / "same_day_sell_pending_equivalence_evidence.json"
    )
    order_plan = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "order_plan.json")

    assert result.status == "PASS"
    assert result.pending_plan_id == existing.pending_plan_id
    assert result.reason == "IDEMPOTENT_EXISTING_PENDING:SAME_DAY_EQUIVALENT_SELL_PENDING_REUSED"
    assert result.pending_composition_model == "SAME_DAY_EQUIVALENT_SELL_PENDING_IDEMPOTENCY"
    assert result.pending_composition_status == "PASS"
    assert result.selected_symbols == ("93600",)
    assert before == after
    assert continuity["pending_reconciliation"]["pending_equivalence_status"] == "EQUIVALENT"
    assert continuity["pending_reconciliation"]["resolution_action"] == "REUSE_EXISTING_PENDING"
    assert continuity["original_pending_preserved"] is True
    assert continuity["pending_reconciliation"]["duplicate_pending_created"] is False
    assert equivalence["current_position_quantity"] == 100.0
    assert equivalence["quantity_equivalence"] == "FULL_EXIT_QUANTITY_MATCHES_CURRENT_POSITION"
    assert order_plan["non_executable_sell_decisions"][0]["symbol"] == "93600"
    assert order_plan["non_executable_sell_decisions"][0]["quantity_contract"]["reason"] == "REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY"


def test_phase31_f1r_actual_20221012_multi_sell_equivalent_set_reused(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_safety_decision(runtime_root, business_date=MULTI_SELL_DATE)
    _write_current_state_many(
        runtime_root,
        {
            "28130": (100, 2070),
            "70690": (100, 1190),
            "70780": (100, 2050),
            "82540": (100, 3480),
        },
        business_date=MULTI_SELL_DATE,
    )
    existing = _write_existing_pending(
        runtime_root,
        items=(
            _pending_exit_item("strategy-ff6150356527e7421792", "82540", business_date=MULTI_SELL_DATE),
            _pending_exit_item("strategy-337529c427c528511a94", "70780", business_date=MULTI_SELL_DATE),
            _pending_exit_item("strategy-bf07fdd0f8cc396d376d", "70690", business_date=MULTI_SELL_DATE),
            _pending_exit_item("strategy-3cfa58a2032ed029b5ec", "28130", business_date=MULTI_SELL_DATE),
        ),
        business_date=MULTI_SELL_DATE,
        target_session_date=MULTI_SELL_DATE,
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=MULTI_SELL_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(symbol="28130", quantity=0, reason="risk_increased", source_decision="REDUCE", reduce_intensity="LIGHT"),
            SellExitDecision(symbol="70690", quantity=0, reason="risk_increased", source_decision="REDUCE", reduce_intensity="LIGHT"),
            SellExitDecision(symbol="70780", quantity=0, reason="risk_increased", source_decision="REDUCE", reduce_intensity="LIGHT"),
            SellExitDecision(symbol="82540", quantity=0, reason="risk_increased", source_decision="REDUCE", reduce_intensity="LIGHT"),
        ),
        environment_capability_context=_historical_context(tmp_path),
    )

    after = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")
    equivalence = _load_json(
        runtime_root
        / "runtime_state"
        / "sell_pipeline"
        / MULTI_SELL_DATE
        / "same_day_sell_pending_equivalence_evidence.json"
    )
    assert result.status == "PASS"
    assert result.pending_plan_id == existing.pending_plan_id
    assert result.pending_composition_model == "SAME_DAY_EQUIVALENT_SELL_PENDING_IDEMPOTENCY"
    assert set(result.selected_symbols) == {"28130", "70690", "70780", "82540"}
    assert before == after
    assert equivalence["pending_equivalence_status"] == "EQUIVALENT"
    assert equivalence["quantity_equivalence"] == "FULL_EXIT_SET_MATCHES_CURRENT_POSITIONS"
    assert equivalence["pending_symbol_set"] == ["28130", "70690", "70780", "82540"]
    assert equivalence["authoritative_sell_exit_symbol_set"] == ["28130", "70690", "70780", "82540"]
    assert equivalence["duplicate_pending_created"] is False


def test_phase31_f1t_actual_20220823_buy_sell_composite_continuation_reused(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_safety_decision(runtime_root, business_date=COMPOSITE_DATE)
    _write_current_state_many(
        runtime_root,
        {
            "60540": (100, 328),
            "99840": (100, 1434.8),
            "70140": (100, 680),
            "94320": (600, 151.6),
        },
        business_date=COMPOSITE_DATE,
    )
    existing = _write_20220823_composite_pending(runtime_root)
    _write_strategy_planning_authority(
        runtime_root,
        business_date=COMPOSITE_DATE,
        rows=(
            {"symbol": "60540", "planning_intent": "SELL_EXIT", "planned_quantity": 100},
            {"symbol": "99840", "planning_intent": "NO_ORDER", "planned_quantity": 0},
            {"symbol": "70140", "planning_intent": "NO_ORDER", "planned_quantity": 0},
        ),
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=COMPOSITE_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(symbol="60540", quantity=0, reason="peak_drawdown_warning", source_decision="REDUCE", reduce_intensity="STRONG"),
            SellExitDecision(symbol="99840", quantity=0, reason="risk_increased_but_trend_not_broken", source_decision="REDUCE", reduce_intensity="LIGHT"),
            SellExitDecision(symbol="70140", quantity=0, reason="risk_increased_but_trend_not_broken", source_decision="REDUCE", reduce_intensity="LIGHT"),
        ),
        environment_capability_context=_historical_context(tmp_path),
    )

    after = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")
    pending_after = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    evidence = _load_json(
        runtime_root
        / "runtime_state"
        / "sell_pipeline"
        / COMPOSITE_DATE
        / "same_day_buy_sell_composite_pending_continuation_evidence.json"
    )

    assert result.status == "PASS"
    assert result.pending_plan_id == existing.pending_plan_id
    assert result.pending_composition_model == "SAME_DAY_CANONICAL_BUY_SELL_COMPOSITE_PENDING_CONTINUATION"
    assert result.selected_symbols == ("60540",)
    assert before == after
    assert evidence["canonical_sell_symbol_set"] == ["60540"]
    assert evidence["pending_sell_symbol_set"] == ["60540"]
    assert evidence["per_symbol_canonical_sell"]["60540"]["canonical_action"] == "SELL_EXIT"
    assert evidence["per_symbol_canonical_sell"]["60540"]["canonical_quantity"] == 100.0
    assert evidence["buy_item_count"] == 5
    assert evidence["sell_item_count"] == 1
    assert evidence["buy_items_preserved"] is True
    assert evidence["duplicate_pending_created"] is False
    assert [item["symbol"] for item in pending_after["items"] if item["side"] == "BUY"] == [
        "94320",
        "38150",
        "72980",
        "44410",
        "71730",
    ]
    assert [item["symbol"] for item in pending_after["items"] if item["side"] == "SELL"] == ["60540"]


def test_phase31_f1l_equivalent_pending_does_not_duplicate_or_change_identity(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93600", quantity=100, price=1429)
    _write_existing_pending(
        runtime_root,
        items=(
            _pending_item(
                "original-sell-exit-93600",
                "93600",
                "SELL",
                100,
                source_decision_type="SELL_EXIT",
                planning_authority_source="rp-2022-09-07-93600-sell_exit",
            ),
        ),
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    assert result.status == "PASS"
    assert [item["pending_item_id"] for item in pending["items"]] == ["original-sell-exit-93600"]
    assert len(pending["items"]) == 1


def test_phase31_f1o_missing_current_position_still_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="68360", quantity=100, price=1429)
    existing = _write_existing_pending(
        runtime_root,
        items=(_pending_item("sell-exit-missing-position", "93600", "SELL", 100, source_decision_type="SELL_EXIT"),),
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="93600",
                quantity=0,
                reason="risk_increased_but_trend_not_broken",
                source_decision="REDUCE",
                reduce_intensity="LIGHT",
                source_decision_id="pm-2022-09-07-93600-reduce",
            ),
        ),
        environment_capability_context=_historical_context(tmp_path),
    )

    continuity = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "pending_continuity_evidence.json")
    equivalence_path = (
        runtime_root
        / "runtime_state"
        / "sell_pipeline"
        / BUSINESS_DATE
        / "same_day_sell_pending_equivalence_evidence.json"
    )
    assert result.status == "REVIEW_REQUIRED"
    assert result.pending_plan_id == existing.pending_plan_id
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before
    assert "PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED" in continuity["reason_codes"]
    assert not equivalence_path.exists()


def test_phase31_f1l_different_quantity_remains_review_required(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93600", quantity=100, price=1429)
    existing = _write_existing_pending(
        runtime_root,
        items=(_pending_item("sell-exit-93600-half", "93600", "SELL", 50, source_decision_type="SELL_EXIT"),),
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    continuity = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "pending_continuity_evidence.json")
    assert result.status == "REVIEW_REQUIRED"
    assert result.pending_plan_id == existing.pending_plan_id
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before
    assert "PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED" in continuity["reason_codes"]


def test_phase31_f1l_ambiguous_multiple_sell_pending_remains_review_required(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93600", quantity=100, price=1429)
    _write_existing_pending(
        runtime_root,
        items=(
            _pending_item("sell-exit-93600-a", "93600", "SELL", 100, source_decision_type="SELL_EXIT"),
            _pending_item("sell-exit-93600-b", "93600", "SELL", 100, source_decision_type="SELL_EXIT"),
        ),
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before


def test_phase31_f1r_multi_sell_quantity_mismatch_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state_many(runtime_root, {"28130": (100, 2070), "70690": (100, 1190)})
    _write_existing_pending(
        runtime_root,
        items=(
            _pending_exit_item("sell-exit-28130", "28130", quantity=100),
            _pending_exit_item("sell-exit-70690-half", "70690", quantity=50),
        ),
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before


def test_phase31_f1r_mixed_buy_sell_pending_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="28130", quantity=100, price=2070)
    _write_existing_pending(
        runtime_root,
        items=(
            _pending_exit_item("sell-exit-28130", "28130"),
            _pending_item("buy-71380", "71380", "BUY", 100, source_decision_type="BUY_NEW"),
        ),
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.pending_composition_model == "PRESERVE_ACTIVE_PENDING_ON_NO_SIGNAL"


def test_phase31_f1r_multi_sell_reduce_member_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state_many(runtime_root, {"28130": (100, 2070), "70690": (100, 1190)})
    _write_existing_pending(
        runtime_root,
        items=(
            _pending_exit_item("sell-exit-28130", "28130"),
            _pending_item("sell-reduce-70690", "70690", "SELL", 100, source_decision_type="SELL_REDUCE"),
        ),
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"


def test_phase31_f1r_submitted_pending_item_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state_many(runtime_root, {"28130": (100, 2070), "70690": (100, 1190)})
    _write_existing_pending(
        runtime_root,
        items=(
            _pending_exit_item("sell-exit-28130", "28130"),
            _pending_exit_item("sell-exit-70690-submitted", "70690", state="SUBMITTED"),
        ),
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"


def test_phase31_f1t_missing_canonical_sell_authority_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_safety_decision(runtime_root, business_date=COMPOSITE_DATE)
    _write_current_state(runtime_root, symbol="60540", quantity=100, price=328)
    _write_20220823_composite_pending(runtime_root)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=COMPOSITE_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"


def test_phase31_f1t_composite_sell_set_mismatch_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_safety_decision(runtime_root, business_date=COMPOSITE_DATE)
    _write_current_state_many(runtime_root, {"60540": (100, 328), "99840": (100, 1434.8)}, business_date=COMPOSITE_DATE)
    _write_20220823_composite_pending(runtime_root)
    _write_strategy_planning_authority(
        runtime_root,
        business_date=COMPOSITE_DATE,
        rows=(
            {"symbol": "60540", "planning_intent": "SELL_EXIT", "planned_quantity": 100},
            {"symbol": "99840", "planning_intent": "SELL_EXIT", "planned_quantity": 100},
        ),
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=COMPOSITE_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"


def test_phase31_f1t_composite_sell_quantity_mismatch_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_safety_decision(runtime_root, business_date=COMPOSITE_DATE)
    _write_current_state(runtime_root, symbol="60540", quantity=100, price=328)
    _write_20220823_composite_pending(runtime_root)
    _write_strategy_planning_authority(
        runtime_root,
        business_date=COMPOSITE_DATE,
        rows=({"symbol": "60540", "planning_intent": "SELL_EXIT", "planned_quantity": 50},),
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=COMPOSITE_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"


def test_phase31_f1t_composite_duplicate_sell_symbol_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_safety_decision(runtime_root, business_date=COMPOSITE_DATE)
    _write_current_state(runtime_root, symbol="60540", quantity=100, price=328)
    _write_existing_pending(
        runtime_root,
        business_date=COMPOSITE_DATE,
        target_session_date=COMPOSITE_DATE,
        items=(
            _pending_item("buy-94320", "94320", "BUY", 200, source_decision_type="BUY_ADD", business_date=COMPOSITE_DATE),
            _pending_exit_item("sell-60540-a", "60540", business_date=COMPOSITE_DATE),
            _pending_exit_item("sell-60540-b", "60540", business_date=COMPOSITE_DATE),
        ),
    )
    _write_strategy_planning_authority(
        runtime_root,
        business_date=COMPOSITE_DATE,
        rows=({"symbol": "60540", "planning_intent": "SELL_EXIT", "planned_quantity": 100},),
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=COMPOSITE_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"


def test_phase31_f1l_different_session_pending_remains_review_required(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93600", quantity=100, price=1429)
    existing = _write_existing_pending(
        runtime_root,
        items=(_pending_item("sell-exit-93600-prior", "93600", "SELL", 100, source_decision_type="SELL_EXIT"),),
        business_date="2022-09-06",
        target_session_date="2022-09-06",
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.pending_plan_id == existing.pending_plan_id
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before


def test_phase31_f1l_sell_reduce_different_exposure_not_equivalent(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93600", quantity=100, price=1429)
    _write_existing_pending(
        runtime_root,
        items=(_pending_item("sell-reduce-93600", "93600", "SELL", 50, source_decision_type="SELL_REDUCE"),),
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"


def test_phase31_f1l_existing_buy_pending_semantics_unchanged(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93600", quantity=100, price=1429)
    _write_existing_pending(
        runtime_root,
        items=(_pending_item("buy-71380", "71380", "BUY", 100, source_decision_type="BUY_NEW"),),
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "NO_SIGNAL"
    assert result.pending_composition_model == "PRESERVE_EXISTING_BUY_PENDING"


def test_phase31_f1l_existing_f1f_pm_exit_path_still_materializes_new_sell(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93600", quantity=100, price=1429)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="93600",
                quantity=100,
                reason="pm_discrete_control_persistent_deterioration_exit",
                source_decision="EXIT",
                source_decision_id="pm-2022-09-07-93600-reduce",
            ),
        ),
        environment_capability_context=_historical_context(tmp_path),
    )

    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    assert result.status == "PASS"
    assert result.pending_composition_model == "SINGLE_PENDING_NO_EXISTING_BUY"
    assert pending["items"][0]["symbol"] == "93600"
    assert pending["items"][0]["side"] == "SELL"
    assert pending["items"][0]["quantity"] == 100
    assert pending["items"][0]["source_decision_type"] == "EXIT"


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    ledger = root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_safety_decision(root)
    return root


def _write_current_state(root: Path, *, symbol: str, quantity: float, price: float) -> None:
    _write_current_state_many(root, {symbol: (quantity, price)})


def _write_current_state_many(
    root: Path,
    positions: dict[str, tuple[float, float]],
    *,
    business_date: str = BUSINESS_DATE,
) -> None:
    market_value = sum(float(quantity) * float(price) for quantity, price in positions.values())
    payload = {
        "schema_version": "1",
        "asset_state_id": "asset-phase31-f1l",
        "environment": "historical",
        "source": "fixture",
        "as_of": business_date,
        "positions": [
            {
                "symbol": symbol,
                "quantity": float(quantity),
                "average_price": float(price),
                "market_value": float(quantity) * float(price),
                "source": "fixture",
                "as_of": business_date,
            }
            for symbol, (quantity, price) in positions.items()
        ],
        "cash": 1_000_000,
        "buying_power": 1_000_000,
        "market_value": market_value,
        "total_equity": 1_000_000 + market_value,
        "review_required": False,
        "production_equivalent": True,
        "current_state_confirmed_empty": False,
        "current_positions_unknown": False,
        "cash_unknown": False,
        "buying_power_unknown": False,
        "generated_from": ["fixture"],
        "created_at": business_date,
        "updated_at": business_date,
    }
    _write_json(root / "persistent_ledger" / "state.json", payload)


def _pending_exit_item(
    pending_item_id: str,
    symbol: str,
    *,
    quantity: float = 100,
    business_date: str = BUSINESS_DATE,
    state: str = "CREATED",
) -> PendingOrderItem:
    return _pending_item(
        pending_item_id,
        symbol,
        "SELL",
        quantity,
        source_decision_type="SELL_EXIT",
        planning_authority_source=f"rp-{business_date}-{symbol}-sell_exit",
        state=state,
        business_date=business_date,
    )


def _pending_item(
    pending_item_id: str,
    symbol: str,
    side: str,
    quantity: float,
    *,
    source_decision_type: str = "",
    planning_authority_source: str = "",
    state: str = "READY",
    business_date: str = BUSINESS_DATE,
) -> PendingOrderItem:
    quantity_contract = None
    if source_decision_type:
        quantity_contract = {
            "source_decision": source_decision_type,
            "planning_intent": source_decision_type,
            "source_planning_id": planning_authority_source,
            "selected_quantity": quantity,
            "planned_quantity": quantity,
        }
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type="MARKET",
        estimated_price=100,
        estimated_amount=quantity * 100,
        approved=True,
        state=state,
        quantity_contract=quantity_contract,
        source_decision_type=source_decision_type,
        source_pm_business_date=business_date,
        source_position_symbol=symbol,
        planning_authority_source=planning_authority_source,
    )


def _write_20220823_composite_pending(root: Path):
    return _write_existing_pending(
        root,
        business_date=COMPOSITE_DATE,
        target_session_date=COMPOSITE_DATE,
        items=(
            _pending_item("strategy-57bb2383d2b1b5924b90", "94320", "BUY", 200, source_decision_type="BUY_ADD", business_date=COMPOSITE_DATE),
            _pending_item("strategy-66a1b334f63e0324a84a", "38150", "BUY", 100, source_decision_type="BUY_NEW", business_date=COMPOSITE_DATE),
            _pending_item("strategy-4eb2ec68f84e80e158b7", "72980", "BUY", 100, source_decision_type="BUY_NEW", business_date=COMPOSITE_DATE),
            _pending_item("strategy-6090689bf22804b320a6", "44410", "BUY", 100, source_decision_type="BUY_NEW", business_date=COMPOSITE_DATE),
            _pending_item("strategy-877a83282c34de5d4ec3", "71730", "BUY", 100, source_decision_type="BUY_NEW", business_date=COMPOSITE_DATE),
            _pending_item(
                "strategy-334522c9134974a8cfad",
                "60540",
                "SELL",
                100,
                source_decision_type="SELL_EXIT",
                planning_authority_source="rp-2022-08-23-60540-sell_exit-c5f5bce7bf475987",
                state="CREATED",
                business_date=COMPOSITE_DATE,
            ),
        ),
    )


def _write_strategy_planning_authority(
    root: Path,
    *,
    business_date: str,
    rows: tuple[dict, ...],
) -> None:
    payload = {
        "schema_version": "strategy_planning_authority_fixture.v1",
        "business_date": business_date,
        "target_session_date": business_date,
        "planning_authority": "strategy_runtime_planning",
        "planning_authority_winner": "strategy_runtime_planning",
        "planning_source": "runtime_planning.v1",
        "items": [
            {
                "symbol": row["symbol"],
                "security_code": row["symbol"],
                "planning_intent": row["planning_intent"],
                "planned_quantity": row["planned_quantity"],
                "quantity": row["planned_quantity"],
                "planning_id": f"rp-{business_date}-{row['symbol']}-{str(row['planning_intent']).lower()}",
                "pending_item_id": f"strategy-authority-{row['symbol']}",
            }
            for row in rows
        ],
        "future_information_used": False,
    }
    _write_json(root / "runtime_state" / "strategy_planning" / business_date / "order_plan.json", payload)


def _write_existing_pending(
    root: Path,
    *,
    items: tuple[PendingOrderItem, ...],
    state: PendingPlanState = PendingPlanState.APPROVED,
    business_date: str = BUSINESS_DATE,
    target_session_date: str = BUSINESS_DATE,
):
    order_plan_path = root / "fixtures" / "existing_order_plan.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_path.write_text(json.dumps({"order_plan_id": "order-plan-existing"}), encoding="utf-8")
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-existing",
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash="sha256:fixture",
        environment="historical",
        plan_created_date=business_date,
        intended_submit_date=target_session_date,
        target_session_date=target_session_date,
        items=items,
    )
    pending = attach_approval_link(
        pending,
        approval_path=str(root / "fixtures" / "existing_approval.json"),
        approval_hash="sha256:approval",
        approval_status="APPROVED",
        approved_item_ids=tuple(item.pending_item_id for item in items),
        approval_expires_at=f"{target_session_date}T15:00:00+09:00",
    )
    pending = replace(pending, state=state)
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    return pending


def _write_safety_decision(root: Path, *, business_date: str = BUSINESS_DATE) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": f"safety-{business_date}",
            "business_date": business_date,
            "mode": "historical",
            "status": "PASS",
            "decision": "NEUTRAL",
            "reason": "fixture",
            "review_required": False,
            "halt_runtime": False,
            "block_buy": False,
            "block_sell": False,
            "safety_policy_version": "fixture",
            "safety_source": "fixture",
            "action_permissions": {
                "sell_planning": "ALLOWED_FOR_REPLAY",
                "sell_submit": "ALLOWED_FOR_REPLAY",
            },
        },
    )


def _historical_context(tmp_path: Path) -> dict:
    return {
        "runtime_mode": "historical",
        "historical_replay": True,
        "broker_environment": "historical_simulated",
        "simulation": True,
        "broker_write": False,
        "external_delivery": False,
        "tachibana_demo_write": False,
        "tachibana_production_write": False,
        "submit_enabled": False,
        "runtime_test_run_id": "phase31-f1l-focused",
        "runtime_test_profile_id": "focused",
        "runtime_test_evidence_root": str(tmp_path / "reports"),
    }


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
