from ai_fund_lab_v2.broker.runtime_v2_demo_submit_adapter import RuntimeV2TachibanaDemoSubmitAdapter
from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.broker.tachibana_order_request import TachibanaCashStockOrderRequest
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand


def test_phase14d4_adapter_accepts_runtime_v2_command_in_dry_run_without_broker_api():
    adapter = RuntimeV2TachibanaDemoSubmitAdapter(settings=_demo_settings())

    result = adapter.submit(_command(symbol="7203"))

    assert result.status == "DRY_RUN_READY"
    assert result.submitted is False
    assert result.broker_api_called is False
    assert result.raw_request_saved is False
    assert result.raw_response_saved is False
    assert "CLMKabuNewOrder" in result.reason


def test_phase14d4_adapter_blocks_production_endpoint():
    adapter = RuntimeV2TachibanaDemoSubmitAdapter(
        settings=BrokerSettings(environment="production", base_url="https://kabuka.e-shiten.jp/e_api_v4r9")
    )

    result = adapter.submit(_command(symbol="7203"))

    assert result.status == "BLOCKED"
    assert result.broker_api_called is False
    assert result.reason == "settings environment is not demo"


def test_phase14d4_adapter_explicitly_blocks_production_base_url_even_when_environment_is_demo():
    adapter = RuntimeV2TachibanaDemoSubmitAdapter(
        settings=BrokerSettings(environment="demo", base_url="https://kabuka.e-shiten.jp/e_api_v4r9")
    )

    result = adapter.submit(_command(symbol="7203"))

    assert result.status == "BLOCKED"
    assert result.broker_api_called is False
    assert result.reason == "production endpoint blocked"


def test_phase14d4_adapter_blocks_9000_series_symbols_for_demo_fill_test():
    adapter = RuntimeV2TachibanaDemoSubmitAdapter(settings=_demo_settings())

    result = adapter.submit(_command(symbol="9432"))

    assert result.status == "BLOCKED"
    assert result.reason == "9000-series symbols excluded from demo fill test candidates"


def test_phase14d4_tachibana_request_can_be_built_from_runtime_v2_command_without_legacy_order_command():
    request = TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(
        _command(symbol="65220"),
        second_password_present=True,
    )
    metadata = request.safe_metadata()

    assert metadata["internal_issue_code"] == "65220"
    assert metadata["issue_code"] == "6522"
    assert metadata["issue_code_normalization"]["normalization_rule"] == "JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR"
    assert metadata["side"] == "BUY"
    assert metadata["order_price_type"] == "MARKET"
    assert metadata["quantity"] == "100.0"
    assert metadata["second_password_value_saved"] is False


def test_phase14d4_adapter_blocks_non_pending_source():
    adapter = RuntimeV2TachibanaDemoSubmitAdapter(settings=_demo_settings())

    result = adapter.submit(_command(symbol="7203", source_current_path="order_plan/2026-07-07/order_plan.json"))

    assert result.status == "BLOCKED"
    assert result.reason == "submit source must be pending_order_plan current"


def _demo_settings():
    return BrokerSettings(
        environment="demo",
        base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9",
        second_password_file="/tmp/phase14d4-second-password",
    )


def _command(symbol: str, source_current_path: str = "pending_order_plan/pending_order_plan.json"):
    return RuntimeV2SubmitCommand(
        command_id="cmd-1",
        environment="demo",
        pending_plan_id="pending-1",
        pending_item_id="item-1",
        approval_hash="sha256:approval",
        symbol=symbol,
        side="BUY",
        quantity=100.0,
        order_type="MARKET",
        price_type="MARKET",
        limit_price=0.0,
        estimated_amount=20000,
        target_session_date="2026-07-07",
        live_order_allowed=True,
        source_current_path=source_current_path,
        listed_info=_listed_info(symbol),
    )


def _listed_info(symbol: str):
    return {
        "code": symbol,
        "market": "プライム",
        "product_category": "011",
        "security_type": "011",
        "current_listed": True,
    }
