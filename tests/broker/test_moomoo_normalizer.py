from decimal import Decimal

import pytest

from ai_fund_lab_v2.broker.moomoo import build_moomoo_mock_response, normalize_moomoo_mock_response


def test_moomoo_mock_response_normalizes_to_common_snapshots() -> None:
    normalized = normalize_moomoo_mock_response(build_moomoo_mock_response())

    accounts = normalized["accounts"]
    balance = normalized["balance"]
    positions = normalized["positions"]
    orders = normalized["orders"]
    executions = normalized["executions"]

    assert len(accounts) == 1
    assert accounts[0].broker == "moomoo"
    assert accounts[0].account_ref == "acct_alias_main"
    assert balance.broker == "moomoo"
    assert balance.cash_available == Decimal("1200000")
    assert balance.buying_power == Decimal("1150000")
    assert [position.issue_code for position in positions] == ["7203", "6758"]
    assert len(orders) == 2
    assert orders[0].side == "sell"
    assert orders[0].remaining_quantity == Decimal("0")
    assert len(executions) == 2
    assert executions[0].order_id == "MOCK-ORD-001"


def test_moomoo_normalizer_rejects_non_read_only_mock_method() -> None:
    payload = build_moomoo_mock_response()
    payload["not_read_only"] = {"ret": "OK", "data": {}}

    with pytest.raises(ValueError, match="Unexpected moomoo mock method"):
        normalize_moomoo_mock_response(payload)

