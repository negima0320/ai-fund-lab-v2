from __future__ import annotations

from ai_fund_lab_v2.operations.exit_adapter import generate_sell_items_from_positions


def test_exit_adapter_generates_sell_item_from_explicit_exit_position():
    result = generate_sell_items_from_positions(
        [
            {
                "code": "7203",
                "position_id": "pos_7203",
                "lot_reference": "lot_1",
                "quantity": "100",
                "entry_price": "1200",
                "current_price": "1000",
                "exit_action": "EXIT",
                "exit_reason": "trend_break",
                "sell_reason": "trend_break",
            }
        ],
        trade_date="2026-06-29",
        exit_source="position_management_ai",
    )

    assert result.status == "PASS"
    assert result.sell_items[0]["side"] == "SELL"
    assert result.sell_items[0]["position_id"] == "pos_7203"
    assert result.sell_items[0]["exit_source"] == "position_management_ai"
    assert result.sell_items[0]["sell_reason"] == "trend_break"
    assert result.ai_training_input_used is False


def test_exit_adapter_returns_empty_when_no_positions():
    result = generate_sell_items_from_positions([], trade_date="2026-06-29")

    assert result.status == "PASS"
    assert result.sell_items == []
