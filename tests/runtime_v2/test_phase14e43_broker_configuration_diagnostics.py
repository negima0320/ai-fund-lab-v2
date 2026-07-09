from pathlib import Path

from ai_fund_lab_v2.broker.config_diagnostics import build_broker_configuration_diagnostic
from ai_fund_lab_v2.broker.runtime_v2_demo_submit_adapter import RuntimeV2TachibanaDemoSubmitAdapter
from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL, BrokerConfigurationError, BrokerSettings
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand
from ai_fund_lab_v2.runtime_v2.submit.pipeline import SubmitItemResult, SubmitPipelineResult


def test_phase14e43_missing_auth_id_file_is_secret_safe(tmp_path):
    settings = _settings(tmp_path, auth_id_file=tmp_path / "missing-auth-id.txt")
    _write(tmp_path / "key.der", b"not-a-real-key")
    _write(tmp_path / "second.txt", b"not-a-secret-for-test")

    diagnostic = build_broker_configuration_diagnostic(settings)

    assert diagnostic["classification"] == "missing_auth_id_file"
    assert diagnostic["next_action"] == "configure_tachibana_auth_id_file"
    assert diagnostic["auth_id_file"]["configured"] is True
    assert diagnostic["auth_id_file"]["file_exists"] is False
    assert "not-a-secret-for-test" not in str(diagnostic)
    assert str(tmp_path) not in str(diagnostic)


def test_phase14e43_login_url_error_classifies_login_endpoint_missing(tmp_path):
    _write(tmp_path / "auth.txt", b"auth-id")
    _write(tmp_path / "key.der", b"not-a-real-key")
    _write(tmp_path / "second.txt", b"not-a-secret-for-test")
    settings = _settings(tmp_path)

    diagnostic = build_broker_configuration_diagnostic(
        settings,
        error=BrokerConfigurationError("Tachibana login URL decrypt returned an invalid URL."),
    )

    assert diagnostic["classification"] == "login_endpoint_missing"
    assert diagnostic["next_action"] == "check_tachibana_login_endpoint_or_private_key_pair"
    assert diagnostic["configured"] is False
    assert "auth-id" not in str(diagnostic)


def test_phase14e43_adapter_blocked_result_contains_configuration_diagnostic():
    command = _command()
    settings = BrokerSettings(environment="production", base_url=PROD_BASE_URL)
    adapter = RuntimeV2TachibanaDemoSubmitAdapter(settings=settings, dry_run=False)

    result = adapter.submit(command)

    assert result.status == "BLOCKED"
    assert result.configuration_diagnostic["classification"] == "demo_environment_mismatch"
    assert result.next_action == "set_tachibana_api_env_demo"


def test_phase14e43_submit_stage_details_preserve_diagnostic():
    result = SubmitPipelineResult(
        status="BLOCKED",
        reason="no pending items were submitted",
        pending_plan_id="pending-e43",
        pending_path=".runtime/pending_order_plan/pending_order_plan.json",
        orders_ledger_path=".runtime/persistent_ledger/orders.jsonl",
        demo_submit_executed=False,
        submitted_count=0,
        accepted_count=0,
        rejected_count=0,
        unknown_count=0,
        blocked_count=1,
        pending_consumed=False,
        submitted_order_ids=(),
        ledger_order_record_ids=(),
        submitted_symbols=(),
        item_results=(
            SubmitItemResult(
                pending_item_id="item-1",
                symbol="72030",
                side="BUY",
                quantity=100,
                preflight_status="PASS",
                submit_status="PRE_SEND_FAILURE",
                submitted=False,
                accepted=False,
                rejected=False,
                unknown=False,
                blocked=True,
                review_required=False,
                broker_order_id_hash="",
                ledger_order_record_id="",
                reason="BrokerConfigurationError",
                issue_code_normalization={},
                response_classification={"business_classification": "PRE_SEND_FAILURE"},
                configuration_diagnostic={
                    "classification": "missing_second_password_file",
                    "next_action": "configure_tachibana_second_password_file",
                    "second_password_file": {"configured": False, "file_exists": False, "file_readable": False},
                },
                next_action="configure_tachibana_second_password_file",
            ),
        ),
    )

    details = result.to_stage_details()

    item = details["item_results"][0]
    assert item["configuration_diagnostic"]["classification"] == "missing_second_password_file"
    assert item["next_action"] == "configure_tachibana_second_password_file"


def _settings(tmp_path: Path, **overrides) -> BrokerSettings:
    tmp_path.mkdir(parents=True, exist_ok=True)
    values = {
        "environment": "demo",
        "base_url": DEMO_BASE_URL,
        "local_config_path": tmp_path,
        "auth_id_file": tmp_path / "auth.txt",
        "private_key_file": tmp_path / "key.der",
        "second_password_file": tmp_path / "second.txt",
    }
    values.update(overrides)
    return BrokerSettings(**values)


def _write(path: Path, content: bytes) -> None:
    path.write_bytes(content)


def _command() -> RuntimeV2SubmitCommand:
    return RuntimeV2SubmitCommand(
        command_id="cmd-e43",
        environment="demo",
        pending_plan_id="pending-e43",
        pending_item_id="item-1",
        approval_hash="sha256:approval",
        symbol="72030",
        side="BUY",
        quantity=100,
        order_type="MARKET",
        price_type="MARKET",
        limit_price=0,
        estimated_amount=100000,
        target_session_date="2026-07-09",
        live_order_allowed=True,
    )
