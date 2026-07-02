from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.broker.allowlist import BrokerAllowlistError, ensure_demo_order_clmid, ensure_read_only_clmid
from ai_fund_lab_v2.broker.secrets import TachibanaSecretLoader
from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL, BrokerSettings
from ai_fund_lab_v2.broker.tachibana_order_request import TachibanaCashStockOrderRequest, TachibanaCashStockOrderRequestBuilder
from ai_fund_lab_v2.broker.transport import DemoOrderBrokerTransport
from ai_fund_lab_v2.operations.io import OperationPaths, write_json
from ai_fund_lab_v2.operations.operations import _normalize_item_for_demo_wire
from ai_fund_lab_v2.operations.operations import run_approval_prepare, run_demo_submit
from ai_fund_lab_v2.runtime import OrderSide, PriceType


TRADE_DATE = "2026-06-29"


def test_readonly_allowlist_still_rejects_new_order() -> None:
    with pytest.raises(BrokerAllowlistError):
        ensure_read_only_clmid("CLMKabuNewOrder")


def test_demo_order_allowlist_fails_closed_for_production() -> None:
    with pytest.raises(BrokerAllowlistError):
        ensure_demo_order_clmid(
            "CLMKabuNewOrder",
            environment="production",
            base_url=PROD_BASE_URL,
            demo_base_url=DEMO_BASE_URL,
            demo_order_wire_execution=True,
            production_order_allowed=False,
        )


def test_demo_order_transport_requires_wire_flag() -> None:
    transport = DemoOrderBrokerTransport(
        endpoint_url="https://demo-kabuka.e-shiten.jp/request",
        settings=BrokerSettings(environment="demo", base_url=DEMO_BASE_URL),
        demo_order_wire_execution=False,
    )

    with pytest.raises(BrokerAllowlistError):
        transport.request({"sCLMID": "CLMKabuNewOrder"})


def test_final_payload_injects_second_password_but_safe_summary_does_not() -> None:
    request = TachibanaCashStockOrderRequest(
        issue_code="92560",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        order_price_type=PriceType.LIMIT,
        order_price=Decimal("5410"),
        second_password_present=True,
    )
    builder = TachibanaCashStockOrderRequestBuilder()

    safe = builder.build_safe_summary(request)
    final = builder.build_final_payload_with_second_password(request, second_password_value="dummy-secret")

    assert safe["second_password_present"] is True
    assert safe["second_password_value_saved"] is False
    assert "sSecondPassword" not in safe
    assert final["sSecondPassword"] == "dummy-secret"


def test_second_password_loader_value_not_in_status(tmp_path: Path) -> None:
    secret_path = tmp_path / "second_password.txt"
    secret_path.write_text("dummy-secret\n", encoding="utf-8")
    loader = TachibanaSecretLoader(BrokerSettings(second_password_file=secret_path))

    status = loader.classify_second_password_file()
    value = loader.load_second_password_value_for_demo_order_only()

    assert status.present is True
    assert status.value_loaded is False
    assert status.value_saved is False
    assert "dummy-secret" not in str(status.to_dict())
    assert value == "dummy-secret"


def test_demo_wire_notional_normalization_from_jquants_close(tmp_path: Path) -> None:
    paths = OperationPaths(tmp_path)
    write_json(
        paths.dated("feature_refresh", TRADE_DATE, "latest_features.json"),
        {"data_until": "2026-06-26"},
    )
    parquet_path = tmp_path / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"Date": "2026-06-26", "target_date": "2026-06-26", "Code": "92560", "code": "92560", "Close": 5410},
        ]
    ).to_parquet(parquet_path)

    item = {
        "item_id": "buy_2026-06-29_92560_001",
        "issue_code": "92560",
        "code": "92560",
        "side": "BUY",
        "quantity": "100",
        "order_type": "CASH_EQUITY",
        "price_type": "LIMIT",
        "limit_price": "0",
        "estimated_value": "0",
        "expected_notional": "0",
        "production_order_allowed": False,
    }

    normalized = _normalize_item_for_demo_wire(item, paths=paths, trade_date=TRADE_DATE)

    assert normalized["limit_price"] == "5410"
    assert normalized["expected_notional"] == "541000"
    assert normalized["estimated_value"] == "541000"
    assert normalized["production_order_allowed"] is False


def test_demo_submit_blocks_overall_when_second_password_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setenv("TACHIBANA_API_BASE_URL", DEMO_BASE_URL)
    monkeypatch.setenv("TACHIBANA_API_SECOND_PASSWORD_FILE", "")
    paths = OperationPaths(tmp_path)
    write_json(
        paths.dated("order_plan", TRADE_DATE, "order_plan.json"),
        {
            "artifact_type": "order_plan",
            "plan_id": "plan1",
            "business_date": TRADE_DATE,
            "items": [
                {
                    "item_id": "buy_2026-06-29_92560_001",
                    "issue_code": "92560",
                    "code": "92560",
                    "side": "BUY",
                    "quantity": "100",
                    "order_type": "CASH_EQUITY",
                    "price_type": "LIMIT",
                    "limit_price": "0",
                    "estimated_value": "0",
                    "expected_notional": "0",
                    "production_order_allowed": False,
                }
            ],
        },
    )
    write_json(paths.dated("safety_result", TRADE_DATE, "safety_result.json"), {"status": "ALLOW"})
    write_json(
        paths.dated("broker_snapshot_summary", TRADE_DATE, "broker_snapshot_summary.json"),
        {"broker_actual_equity": "20000000", "buying_power": "20000000", "current_exposure": "0"},
    )
    write_json(paths.dated("positions", TRADE_DATE, "positions.json"), {"positions": []})
    write_json(paths.dated("feature_refresh", TRADE_DATE, "latest_features.json"), {"data_until": "2026-06-26"})
    parquet_path = tmp_path / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": "2026-06-26", "target_date": "2026-06-26", "Code": "92560", "code": "92560", "Close": 5410}]).to_parquet(parquet_path)
    listed_path = tmp_path / "feature_refresh" / TRADE_DATE / "jquants" / "listed_issues" / "listed_info_for_feature.parquet"
    listed_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Code": "92560", "code": "92560", "MktNm": "グロース", "ProdCat": "011"}]).to_parquet(listed_path)

    run_approval_prepare(trade_date=TRADE_DATE, root=tmp_path, approve=True, approver_label="test", max_notional=Decimal("600000"))
    result = run_demo_submit(trade_date=TRADE_DATE, root=tmp_path, execute_demo_order=True)

    assert result["status"] == "BLOCK"
    assert result["broker_order_api_called"] is False
    assert result["demo_order_submitted"] is False
    assert result["submitted_orders"][0]["status"] == "BLOCKED_SECOND_PASSWORD_MISSING"
