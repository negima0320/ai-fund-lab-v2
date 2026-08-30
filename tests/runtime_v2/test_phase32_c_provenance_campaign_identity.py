from __future__ import annotations

from ai_fund_lab_v2.runtime_v2.planning.strategy_authority import _runtime_planning_position_campaign_id
from scripts.runtime_test import _build_fill_rows, _derive_position_campaign_state


def test_phase32_c_runtime_planning_campaign_authority_buy_add_inherits_buy_new_materializes() -> None:
    buy_add = _runtime_planning_position_campaign_id(
        plan={
            "planning_intent": "BUY_ADD",
            "marginal_capital_value_authority": {
                "source_evidence": {"current_position_campaign_id": "pc-authority-94340-0001"}
            },
        },
        symbol="94340",
        business_date="2026-07-07",
        source_decision_id="rp-buy-add-94340",
    )
    buy_new = _runtime_planning_position_campaign_id(
        plan={"planning_intent": "BUY_NEW", "planning_id": "rp-buy-new-83060"},
        symbol="83060",
        business_date="2026-07-07",
        source_decision_id="rp-buy-new-83060",
    )

    assert buy_add == "pc-authority-94340-0001"
    assert buy_new.startswith("pc-")
    assert buy_new.endswith("-83060-0001")
    assert buy_new != buy_add


def test_phase32_c_campaign_observability_uses_upstream_execution_campaign_id() -> None:
    executions = [
        {
            "business_date": "2026-07-06",
            "execution_id": "exec-buy-new",
            "symbol": "7203",
            "side": "BUY",
            "filled_quantity": 100,
            "price": 1000,
            "position_campaign_id": "pc-authority-7203-0001",
            "source_decision_id": "rp-buy-new-7203",
            "source_decision_type": "BUY_NEW",
            "pending_item_id": "pending-buy-new-7203",
            "order_plan_item_id": "opi-buy-new-7203",
        },
        {
            "business_date": "2026-07-07",
            "execution_id": "exec-buy-add",
            "symbol": "7203",
            "side": "BUY",
            "filled_quantity": 100,
            "price": 1010,
            "position_campaign_id": "pc-authority-7203-0001",
            "source_decision_id": "rp-buy-add-7203",
            "source_decision_type": "BUY_ADD",
            "pending_item_id": "pending-buy-add-7203",
            "order_plan_item_id": "opi-buy-add-7203",
        },
    ]

    campaign_state = _derive_position_campaign_state(
        run_id="run-phase32-c",
        business_date="2026-07-07",
        executions=executions,
        plans={"buy": [], "sell": []},
        current_state={"positions": [{"symbol": "7203", "quantity": 200, "market_value": 202000}]},
    )
    campaigns = campaign_state["campaigns"]
    fills = _build_fill_rows(
        run_id="run-phase32-c",
        business_date="2026-07-07",
        executions=executions,
        execution_campaign_ids=campaign_state["execution_campaign_ids"],
        plans={"buy": [], "sell": []},
    )

    assert len(campaigns) == 1
    assert campaigns[0]["position_campaign_id"] == "pc-authority-7203-0001"
    assert campaigns[0]["campaign_identity_authority_status"] == "COMPLETE"
    assert campaigns[0]["events"][1]["stage"] == "ADD"
    assert fills[0]["position_campaign_id"] == "pc-authority-7203-0001"
    assert fills[0]["source_decision_id"] == "rp-buy-add-7203"
    assert fills[0]["pending_item_id"] == "pending-buy-add-7203"
    assert fills[0]["order_plan_item_id"] == "opi-buy-add-7203"


def test_phase32_c_reentry_after_exit_uses_new_upstream_campaign_id() -> None:
    executions = [
        {
            "business_date": "2026-07-06",
            "execution_id": "exec-buy-new",
            "symbol": "7203",
            "side": "BUY",
            "filled_quantity": 100,
            "price": 1000,
            "position_campaign_id": "pc-authority-7203-0001",
        },
        {
            "business_date": "2026-07-07",
            "execution_id": "exec-exit",
            "symbol": "7203",
            "side": "SELL",
            "filled_quantity": 100,
            "price": 990,
            "position_campaign_id": "pc-authority-7203-0001",
            "source_decision_id": "pm-exit-7203",
            "source_decision_type": "EXIT",
        },
        {
            "business_date": "2026-07-08",
            "execution_id": "exec-reentry",
            "symbol": "7203",
            "side": "BUY",
            "filled_quantity": 100,
            "price": 1010,
            "position_campaign_id": "pc-authority-7203-0002",
            "source_decision_id": "rp-reentry-7203",
            "source_decision_type": "BUY_NEW",
        },
    ]

    campaign_state = _derive_position_campaign_state(
        run_id="run-phase32-c",
        business_date="2026-07-08",
        executions=executions,
        plans={"buy": [], "sell": []},
        current_state={"positions": [{"symbol": "7203", "quantity": 100, "market_value": 101000}]},
    )

    campaigns = campaign_state["campaigns"]
    assert [row["position_campaign_id"] for row in campaigns] == [
        "pc-authority-7203-0001",
        "pc-authority-7203-0002",
    ]
    assert campaigns[0]["campaign_status"] == "CLOSED"
    assert campaigns[1]["campaign_status"] == "OPEN"
