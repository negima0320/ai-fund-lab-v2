from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL
from ai_fund_lab_v2.operations.io import OperationPaths, write_json
from ai_fund_lab_v2.operations.operations import run_demo_matched_opposite_order_fill_test


TRADE_DATE = "2026-06-29"


def _write_listed_info(root: Path) -> None:
    path = root / "feature_refresh" / TRADE_DATE / "jquants" / "listed_issues" / "listed_info_for_feature.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Code": "92560", "code": "92560", "MktNm": "グロース", "ProdCat": "011"}]).to_parquet(path)


def _write_common_artifacts(root: Path, *, include_buy: bool = True) -> None:
    paths = OperationPaths(root)
    _write_listed_info(root)
    write_json(paths.dated("safety_monitor", TRADE_DATE, "safety_monitor_result.json"), {"status": "PASS", "safety_state": "ALLOW"})
    write_json(
        paths.dated("broker_buying_power", TRADE_DATE, "buying_power.json"),
        {"artifact_type": "broker_buying_power", "business_date": TRADE_DATE, "buying_power": "19458494", "raw_response_saved": False, "secret_saved": False},
    )
    orders = [
        {
            "issue_code": "9256",
            "side": "3",
            "quantity": "100",
            "executed_quantity": "0",
            "remaining_quantity": "100",
            "status": "未約定",
            "price": "5410.0000",
            "raw_response_saved": False,
            "secret_saved": False,
        }
    ] if include_buy else []
    write_json(paths.dated("broker_orders", TRADE_DATE, "orders.json"), {"artifact_type": "broker_orders", "business_date": TRADE_DATE, "orders": orders, "raw_response_saved": False, "secret_saved": False})
    write_json(paths.dated("broker_executions", TRADE_DATE, "executions.json"), {"artifact_type": "broker_executions", "business_date": TRADE_DATE, "executions": [], "raw_response_saved": False, "secret_saved": False})
    write_json(paths.dated("broker_positions", TRADE_DATE, "positions.json"), {"artifact_type": "broker_positions", "business_date": TRADE_DATE, "positions": [], "raw_response_saved": False, "secret_saved": False})
    write_json(paths.dated("broker_snapshot_summary", TRADE_DATE, "broker_snapshot_summary.json"), {"orders_count": len(orders), "executions_count": 0, "positions_count": 0, "buying_power": "19458494", "raw_response_saved": False, "secret_saved": False})


def test_matched_opposite_sell_dry_run_requires_existing_buy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setenv("TACHIBANA_API_BASE_URL", DEMO_BASE_URL)
    _write_common_artifacts(tmp_path, include_buy=False)

    result = run_demo_matched_opposite_order_fill_test(trade_date=TRADE_DATE, root=tmp_path, execute_sell_order=False)

    assert result["status"] == "BLOCK"
    assert result["buy_reorder_executed"] is False
    assert result["sell_order_attempted"] is False
    assert "existing_buy_waiting_order_not_found" in result["blocks"]


def test_matched_opposite_sell_dry_run_records_approval_without_buy_reorder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setenv("TACHIBANA_API_BASE_URL", DEMO_BASE_URL)
    _write_common_artifacts(tmp_path, include_buy=True)

    result = run_demo_matched_opposite_order_fill_test(trade_date=TRADE_DATE, root=tmp_path, execute_sell_order=False)

    assert result["status"] == "PASS"
    assert result["buy_reorder_executed"] is False
    assert result["buy_clm_kabu_new_order_called"] is False
    assert result["sell_order_attempted"] is False
    assert result["approval"]["approval_scope"] == "DEMO_MATCHED_OPPOSITE_ORDER_FILL_TEST"
    assert result["sell_order"]["sell_reason"] == "demo_matched_opposite_order_fill_test"
    assert result["sell_order"]["price_type"] == "MARKET"
    assert result["sell_order"]["broker_issue_code"] == "9256"
    assert result["raw_request_saved"] is False
    assert result["raw_response_saved"] is False
    assert result["secret_saved"] is False


def test_matched_opposite_sell_fails_closed_in_production(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "production")
    monkeypatch.setenv("TACHIBANA_API_BASE_URL", PROD_BASE_URL)
    _write_common_artifacts(tmp_path, include_buy=True)

    result = run_demo_matched_opposite_order_fill_test(trade_date=TRADE_DATE, root=tmp_path, execute_sell_order=True)

    assert result["status"] == "BLOCK"
    assert result["sell_order_attempted"] is False
    assert result["sell_order_executed"] is False
    assert result["production_order_submitted"] is False
