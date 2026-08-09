import json

from ai_fund_lab_v2.broker.runtime_v2_demo_submit_adapter import RuntimeV2TachibanaDemoSubmitAdapter
from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.broker.tachibana_order_request import (
    TachibanaCashStockOrderRequest,
    TachibanaCashStockOrderRequestBuilder,
)
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability, is_symbol_allowed_by_capability
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult
from ai_fund_lab_v2.runtime_v2.submit.pipeline import RuntimeV2SubmitAdapter, run_submit_pipeline

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import (
    _approved_pending,
    _runtime_root,
    _write_asset_state,
    _write_policy,
)


def test_phase14e19_runtime_v2_command_uses_existing_normalizer_for_broker_request():
    request = TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(
        _command("65220"),
        second_password_present=True,
    )
    summary = TachibanaCashStockOrderRequestBuilder().build_safe_summary(request)

    assert summary["internal_issue_code"] == "65220"
    assert summary["issue_code"] == "6522"
    assert summary["issue_code_normalization"]["original_symbol"] == "65220"
    assert summary["issue_code_normalization"]["broker_issue_code"] == "6522"
    assert summary["issue_code_normalization"]["normalization_rule"] == "JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR"


def test_phase14e19_four_character_issue_code_is_preserved():
    request = TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(
        _command("7203"),
        second_password_present=True,
    )
    summary = TachibanaCashStockOrderRequestBuilder().build_safe_summary(request)

    assert summary["internal_issue_code"] == "7203"
    assert summary["issue_code"] == "7203"
    assert summary["issue_code_normalization"]["normalization_rule"] == "BROKER_4CHAR_ALREADY_NORMALIZED"


def test_phase14e19_demo_adapter_dry_run_blocks_missing_listed_info_before_broker_api():
    adapter = RuntimeV2TachibanaDemoSubmitAdapter(settings=_demo_settings())
    command = _command("65220", listed_info=None)

    result = adapter.submit(command)

    assert result.status == "BLOCKED"
    assert result.broker_api_called is False
    assert "broker issue code normalization failed" in result.reason


def test_phase28_d48_runtime_v2_command_blocks_unsupported_broker_category_before_broker_api():
    adapter = RuntimeV2TachibanaDemoSubmitAdapter(settings=_demo_settings())
    command = _command(
        "48750",
        listed_info={
            "code": "48750",
            "market": "スタンダード",
            "product_category": "021",
            "security_type": "021",
            "current_listed": True,
        },
    )

    result = adapter.submit(command)

    assert result.status == "BLOCKED"
    assert result.broker_api_called is False
    assert result.reason == "broker issue code normalization failed: BROKER_PRODUCT_CATEGORY_UNSUPPORTED"


def test_phase14e19_demo_9000_block_and_production_capability_still_allows_9000():
    demo_adapter = RuntimeV2TachibanaDemoSubmitAdapter(settings=_demo_settings())

    result = demo_adapter.submit(_command("9432"))

    assert result.status == "BLOCKED"
    assert result.reason == "9000-series symbols excluded from demo fill test candidates"
    assert is_symbol_allowed_by_capability("9432", get_broker_capability("production")) is True
    assert is_symbol_allowed_by_capability("9432", get_broker_capability("demo")) is False


def test_phase14e19_submit_pipeline_writes_normalization_and_response_metadata_to_manifest_and_ledger(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    pending = _approved_pending(("65220",), policy_path=policy_path)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_MetadataAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    ledger_rows = [
        json.loads(line)
        for line in (runtime_root / "persistent_ledger" / "orders.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert result.status == "PASS"
    assert result.item_results[0].issue_code_normalization["original_symbol"] == "65220"
    assert result.item_results[0].issue_code_normalization["broker_issue_code"] == "6522"
    assert result.item_results[0].response_classification["business_classification"] == "ACCEPTED"
    assert ledger_rows[0]["issue_code_normalization"]["broker_issue_code"] == "6522"
    assert ledger_rows[0]["response_classification"]["business_classification"] == "ACCEPTED"


class _MetadataAdapter(RuntimeV2SubmitAdapter):
    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        request = TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(command, second_password_present=True)
        return RuntimeV2SubmitResult(
            status="DRY_RUN_READY",
            submitted=False,
            accepted=False,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            reason="metadata adapter preflight",
            issue_code_normalization=dict(request.issue_code_normalization),
        )

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        request = TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(command, second_password_present=True)
        return RuntimeV2SubmitResult(
            status="ACCEPTED",
            submitted=True,
            accepted=True,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            broker_order_id_hash="sha256:test-order",
            reason="metadata adapter accepted",
            issue_code_normalization=dict(request.issue_code_normalization),
            response_classification={
                "p_errno": "0",
                "sResultCode": "0",
                "p_err_classification": "",
                "business_classification": "ACCEPTED",
                "order_number_present": True,
                "result_code_present": True,
            },
        )


def _command(symbol: str, listed_info="__default__"):
    return RuntimeV2SubmitCommand(
        command_id="cmd-e19-" + symbol,
        environment="demo",
        pending_plan_id="pending-e19",
        pending_item_id="item-e19",
        approval_hash="sha256:approval-e19",
        symbol=symbol,
        side="BUY",
        quantity=100.0,
        order_type="MARKET",
        price_type="MARKET",
        limit_price=0.0,
        estimated_amount=100000.0,
        target_session_date="2026-07-08",
        live_order_allowed=True,
        listed_info=_listed_info(symbol) if listed_info == "__default__" else listed_info,
    )


def _listed_info(symbol: str):
    return {
        "code": symbol,
        "market": "プライム",
        "product_category": "011",
        "security_type": "011",
        "current_listed": True,
    }


def _demo_settings():
    return BrokerSettings(
        environment="demo",
        base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9",
        second_password_file="/tmp/phase14e19-second-password",
    )
