from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ai_fund_lab_v2.broker import (
    BrokerSettings,
    TachibanaSecretLoader,
    normalize_redacted_order_submit_result,
    run_tachibana_demo_order_live_smoke_foundation,
)
from ai_fund_lab_v2.runtime import OrderSide


def test_demo_order_smoke_default_skipped(tmp_path) -> None:
    result = run_tachibana_demo_order_live_smoke_foundation(reports_dir=tmp_path, settings=_settings(tmp_path))

    payload = _read(result.report_path)
    assert result.status == "SKIPPED"
    assert result.executed is False
    assert payload["executed"] is False
    assert payload["demo_order_submitted"] is False
    assert payload["broker_order_api_called"] is False


def test_demo_order_smoke_blocks_live_submit_in_phase10u(tmp_path) -> None:
    result = run_tachibana_demo_order_live_smoke_foundation(
        reports_dir=tmp_path,
        settings=_settings(tmp_path, with_second_password=True),
        run_enabled=True,
        dry_run=False,
    )

    payload = _read(result.report_path)
    assert result.status == "BLOCKED_LIVE_SUBMIT_NOT_IMPLEMENTED"
    assert payload["clmkabu_new_order_executed"] is False
    assert payload["raw_payload_saved"] is False


def test_demo_order_smoke_dry_run_ready_with_second_password_presence(tmp_path) -> None:
    result = run_tachibana_demo_order_live_smoke_foundation(
        reports_dir=tmp_path,
        settings=_settings(tmp_path, with_second_password=True),
        run_enabled=True,
        dry_run=True,
    )

    payload = _read(result.report_path)
    assert result.status == "DRY_RUN_READY"
    assert result.executed is False
    assert payload["second_password"]["present"] is True
    assert payload["second_password"]["value_loaded"] is False
    assert payload["second_password"]["value_saved"] is False
    assert payload["final_payload_summary"]["second_password_injected"] is False
    assert payload["final_payload_summary"]["raw_payload_saved"] is False
    assert payload["executor_result"]["submitted"] is False
    assert payload["post_submit_reconciliation"]["order_list"] == "NOT_EXECUTED"


def test_demo_order_smoke_missing_second_password_blocks(tmp_path) -> None:
    result = run_tachibana_demo_order_live_smoke_foundation(
        reports_dir=tmp_path,
        settings=_settings(tmp_path),
        run_enabled=True,
        dry_run=True,
    )

    payload = _read(result.report_path)
    assert result.status == "BLOCKED_SECOND_PASSWORD_MISSING"
    assert payload["second_password"]["present"] is False
    assert payload["executor_result"]["status"] == "BLOCKED_SECOND_PASSWORD_MISSING"
    assert payload["broker_order_api_called"] is False


def test_demo_order_smoke_expired_approval_blocks(tmp_path) -> None:
    result = run_tachibana_demo_order_live_smoke_foundation(
        reports_dir=tmp_path,
        settings=_settings(tmp_path, with_second_password=True),
        run_enabled=True,
        dry_run=True,
        approval_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    payload = _read(result.report_path)
    assert result.status == "BLOCKED_APPROVAL_SCOPE_MISMATCH"
    assert payload["approval"]["status"] == "BLOCKED_APPROVAL_EXPIRED"


def test_demo_order_smoke_production_blocks(tmp_path) -> None:
    result = run_tachibana_demo_order_live_smoke_foundation(
        reports_dir=tmp_path,
        settings=BrokerSettings(environment="prod", base_url="https://kabuka.e-shiten.jp/e_api_v4r9"),
        run_enabled=True,
        dry_run=True,
    )

    payload = _read(result.report_path)
    assert result.status == "BLOCKED_PRODUCTION_PROHIBITED"
    assert payload["production_order_submitted"] is False


def test_second_password_loader_reports_presence_without_value(tmp_path) -> None:
    settings = _settings(tmp_path, with_second_password=True)

    status = TachibanaSecretLoader(settings).classify_second_password_file()

    assert status.present is True
    assert status.value_loaded is False
    assert status.value_saved is False
    assert "secret" not in json.dumps(status.to_dict()).lower()


def test_redacted_order_submit_result_hashes_order_id() -> None:
    result = normalize_redacted_order_submit_result({"sResultCode": "0", "sOrderNumber": "ORDER-123456789"})
    payload = result.to_dict()

    assert payload["accepted"] is True
    assert payload["broker_order_id_hash"].startswith("sha256:")
    assert "ORDER-123456789" not in json.dumps(payload)
    assert payload["raw_order_id_saved"] is False
    assert payload["raw_response_saved"] is False


def _settings(tmp_path, *, with_second_password: bool = False) -> BrokerSettings:
    second_password_file = None
    if with_second_password:
        second_password_file = tmp_path / "second_password.txt"
        second_password_file.write_text("synthetic-test-secret\n", encoding="utf-8")
    return BrokerSettings(
        environment="demo",
        base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9",
        second_password_file=second_password_file,
    )


def _read(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
