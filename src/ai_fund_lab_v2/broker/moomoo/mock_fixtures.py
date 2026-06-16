from __future__ import annotations

from copy import deepcopy
from typing import Any


def build_moomoo_mock_response() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "metadata": {
            "broker": "moomoo",
            "source": "mock",
            "environment": "readonly_mock",
            "as_of": "2026-06-15T09:00:00+09:00",
            "currency": "JPY",
            "account_ref": "acct_alias_main",
        },
        "get_acc_list": {
            "ret": "OK",
            "data": [
                {
                    "account_ref": "acct_alias_main",
                    "account_label": "main_jp_cash",
                    "trd_env": "REAL",
                    "acc_type": "CASH",
                    "acc_status": "ACTIVE",
                    "trdmarket_auth": ["JP"],
                }
            ],
        },
        "accinfo_query": {
            "ret": "OK",
            "data": {
                "currency": "JPY",
                "jp_cash": "1200000",
                "jpy_net_cash_power": "1150000",
                "jp_avl_withdrawal_cash": "1100000",
                "jpy_assets": "1800000",
                "risk_status": "LEVEL1",
            },
        },
        "position_list_query": {
            "ret": "OK",
            "data": [
                {
                    "code": "JP.7203",
                    "stock_name": "TOYOTA",
                    "qty": "100",
                    "can_sell_qty": "100",
                    "cost_price": "2500",
                    "nominal_price": "2600",
                    "market_val": "260000",
                    "pl_val": "10000",
                    "position_market": "JP",
                    "currency": "JPY",
                },
                {
                    "code": "JP.6758",
                    "stock_name": "SONY GROUP",
                    "qty": "100",
                    "can_sell_qty": "0",
                    "cost_price": "13000",
                    "nominal_price": "13100",
                    "market_val": "1310000",
                    "pl_val": "10000",
                    "position_market": "JP",
                    "currency": "JPY",
                },
            ],
        },
        "order_list_query": {
            "ret": "OK",
            "data": [
                {
                    "order_id": "MOCK-ORD-001",
                    "code": "JP.7203",
                    "stock_name": "TOYOTA",
                    "trd_side": "SELL",
                    "order_type": "NORMAL",
                    "order_status": "FILLED",
                    "qty": "100",
                    "dealt_qty": "100",
                    "price": "2600",
                    "dealt_avg_price": "2600",
                    "create_time": "2026-06-15 09:00:00",
                    "updated_time": "2026-06-15 09:05:00",
                    "currency": "JPY",
                    "last_err_msg": "",
                }
            ],
        },
        "history_order_list_query": {
            "ret": "OK",
            "data": [
                {
                    "order_id": "MOCK-ORD-H001",
                    "code": "JP.6501",
                    "stock_name": "HITACHI",
                    "trd_side": "BUY",
                    "order_type": "NORMAL",
                    "order_status": "FILLED",
                    "qty": "100",
                    "dealt_qty": "100",
                    "price": "3800",
                    "dealt_avg_price": "3800",
                    "create_time": "2026-06-14 09:00:00",
                    "updated_time": "2026-06-14 09:03:00",
                    "currency": "JPY",
                    "last_err_msg": "",
                }
            ],
        },
    }
    return deepcopy(payload)

