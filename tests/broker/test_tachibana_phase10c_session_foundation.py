import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
import ai_fund_lab_v2.broker.crypto as tachibana_crypto
import ai_fund_lab_v2.broker.tachibana_codec as tachibana_codec

from ai_fund_lab_v2.broker import (
    BrokerConfigurationError,
    BrokerSettings,
    BrokerTransportError,
    HttpPostBrokerTransport,
    TachibanaCodecError,
    TachibanaSecretLoader,
    TachibanaV4R9Codec,
    classify_login_ack,
    diagnose_login_request_shape,
    diagnose_private_key_file,
    normalize_balance_summary,
    normalize_buying_power,
    normalize_cash_positions,
    normalize_login_ack,
    normalize_margin_positions,
    normalize_market_quotes,
    normalize_order_detail_executions,
    normalize_order_list,
    normalize_order_list_detail,
    run_tachibana_account_balance_smoke,
    run_tachibana_account_error_reveal,
    run_tachibana_account_transport_diagnosis,
    run_tachibana_broker_snapshot,
    run_tachibana_demo_login_smoke,
    run_tachibana_executions_history_smoke,
    run_tachibana_orders_smoke,
    run_tachibana_positions_smoke,
    run_tachibana_quote_smoke,
    sanitize_mapping,
)
from ai_fund_lab_v2.broker.response import BrokerResponseEnvelope
from ai_fund_lab_v2.broker.tachibana_account_smoke import _response_summary
from ai_fund_lab_v2.broker.tachibana_account_smoke import classify_revealed_account_error
from ai_fund_lab_v2.broker.tachibana_account_smoke import classify_account_balance_issue
from ai_fund_lab_v2.broker.tachibana_account_smoke import classify_protocol_error
from ai_fund_lab_v2.broker.tachibana_account_smoke import classify_transport_compatibility
from ai_fund_lab_v2.broker.tachibana_account_smoke import diagnose_account_balance_keys
from ai_fund_lab_v2.broker.tachibana_account_smoke import diagnose_account_request_shape
from ai_fund_lab_v2.broker.tachibana_account_smoke import reveal_protocol_error
from ai_fund_lab_v2.broker.tachibana_broker_snapshot import _redaction_status, _write_json_atomic
from ai_fund_lab_v2.broker.tachibana_executions_history_smoke import _execution_dict
from ai_fund_lab_v2.broker.tachibana_orders_smoke import _order_dict
from ai_fund_lab_v2.broker.tachibana_positions_smoke import _position_dict
from ai_fund_lab_v2.broker.tachibana_quote_smoke import _quote_dict
from ai_fund_lab_v2.broker.crypto import OpenSslRsaOaepDecryptor, _classify_plaintext
from ai_fund_lab_v2.broker.transport import request as urllib_request
from ai_fund_lab_v2.broker.tachibana_smoke import _classify_failure, _diagnose_virtual_url_candidates
from ai_fund_lab_v2.cli.tachibana_demo_login_smoke import main as smoke_cli_main
from ai_fund_lab_v2.cli.tachibana_account_balance_smoke import main as account_smoke_cli_main
from ai_fund_lab_v2.cli.tachibana_broker_snapshot import main as broker_snapshot_cli_main
from ai_fund_lab_v2.cli.tachibana_executions_history_smoke import main as executions_history_smoke_cli_main
from ai_fund_lab_v2.cli.tachibana_orders_smoke import main as orders_smoke_cli_main
from ai_fund_lab_v2.cli.tachibana_positions_smoke import main as positions_smoke_cli_main
from ai_fund_lab_v2.cli.tachibana_quote_smoke import main as quote_smoke_cli_main


def test_secret_loader_reads_local_demo_files_without_repr_leak(tmp_path: Path) -> None:
    config_dir = tmp_path / "tachibana" / "demo"
    config_dir.mkdir(parents=True)
    (config_dir / "e_api_authid.txt").write_text("secret-auth-id\n", encoding="utf-8")
    (config_dir / "e_api_private_key.der").write_bytes(b"fake-key")
    settings = BrokerSettings(local_config_path=config_dir)

    secrets = TachibanaSecretLoader(settings).load()

    assert secrets.auth_id == "secret-auth-id"
    assert secrets.private_key_file == config_dir / "e_api_private_key.der"
    assert "secret-auth-id" not in repr(secrets)


def test_secret_loader_fails_closed_when_auth_file_missing(tmp_path: Path) -> None:
    config_dir = tmp_path / "tachibana" / "demo"
    config_dir.mkdir(parents=True)
    (config_dir / "e_api_private_key.der").write_bytes(b"fake-key")
    settings = BrokerSettings(local_config_path=config_dir)

    with pytest.raises(BrokerConfigurationError, match="AUTH_ID"):
        TachibanaSecretLoader(settings).load()


def test_login_ack_normalizer_redacts_session_repr() -> None:
    session = normalize_login_ack(
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sUrlRequest": "request",
            "sUrlMaster": "master",
            "sUrlPrice": "price",
            "sUrlEvent": "event",
            "sUrlEventWebSocket": "websocket",
        },
        environment="demo",
        decrypt_url=lambda value: f"https://demo-kabuka.e-shiten.jp/{value}",
        login_at=datetime(2026, 6, 27, tzinfo=timezone.utc),
    )

    text = repr(session)

    assert session.price_url == "https://demo-kabuka.e-shiten.jp/price"
    assert "https://demo-kabuka.e-shiten.jp" not in text
    assert "[REDACTED]" in text


def test_login_ack_normalizer_accepts_trimmed_demo_https_url() -> None:
    session = normalize_login_ack(
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sUrlRequest": "request",
            "sUrlMaster": "master",
            "sUrlPrice": "price",
            "sUrlEvent": "event",
            "sUrlEventWebSocket": "websocket",
        },
        environment="demo",
        decrypt_url=lambda value: f" \nhttps://demo-kabuka.e-shiten.jp/{value}\t ",
    )

    assert session.request_url == "https://demo-kabuka.e-shiten.jp/request"


def test_login_ack_normalizer_accepts_edge_null_terminated_demo_url() -> None:
    session = normalize_login_ack(
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sUrlRequest": "request",
            "sUrlMaster": "master",
            "sUrlPrice": "price",
            "sUrlEvent": "event",
            "sUrlEventWebSocket": "websocket",
        },
        environment="demo",
        decrypt_url=lambda value: f"https://demo-kabuka.e-shiten.jp/{value}\x00",
    )

    assert session.request_url == "https://demo-kabuka.e-shiten.jp/request"
    assert session.websocket_url == ""


def test_login_ack_normalizer_accepts_wss_websocket_url() -> None:
    session = normalize_login_ack(
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sUrlRequest": "request",
            "sUrlMaster": "master",
            "sUrlPrice": "price",
            "sUrlEvent": "event",
            "sUrlEventWebSocket": "websocket",
        },
        environment="demo",
        decrypt_url=lambda value: (
            "wss://demo-kabuka.e-shiten.jp/ws"
            if value == "websocket"
            else f"https://demo-kabuka.e-shiten.jp/{value}"
        ),
    )

    assert session.websocket_url == "wss://demo-kabuka.e-shiten.jp/ws"
    assert "wss://demo-kabuka.e-shiten.jp/ws" not in repr(session)


def test_login_ack_normalizer_accepts_ws_websocket_url() -> None:
    session = normalize_login_ack(
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sUrlRequest": "request",
            "sUrlMaster": "master",
            "sUrlPrice": "price",
            "sUrlEvent": "event",
            "sUrlEventWebSocket": "websocket",
        },
        environment="demo",
        decrypt_url=lambda value: (
            "ws://demo-kabuka.e-shiten.jp/ws"
            if value == "websocket"
            else f"https://demo-kabuka.e-shiten.jp/{value}"
        ),
    )

    assert session.websocket_url == "ws://demo-kabuka.e-shiten.jp/ws"


def test_login_ack_normalizer_treats_invalid_websocket_url_as_optional_unavailable() -> None:
    session = normalize_login_ack(
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sUrlRequest": "request",
            "sUrlMaster": "master",
            "sUrlPrice": "price",
            "sUrlEvent": "event",
            "sUrlEventWebSocket": "websocket",
        },
        environment="demo",
        decrypt_url=lambda value: (
            "not-a-websocket-url"
            if value == "websocket"
            else f"https://demo-kabuka.e-shiten.jp/{value}"
        ),
    )

    assert session.websocket_url == ""


def test_login_ack_normalizer_fails_closed_for_control_char_url() -> None:
    with pytest.raises(BrokerConfigurationError, match="invalid URL"):
        normalize_login_ack(
            {
                "sCLMID": "CLMAuthLoginAck",
                "sResultCode": "0",
                "sUrlRequest": "request",
                "sUrlMaster": "master",
                "sUrlPrice": "price",
                "sUrlEvent": "event",
                "sUrlEventWebSocket": "websocket",
            },
            environment="demo",
            decrypt_url=lambda value: f"https://demo-kabuka.e-shiten.jp/{value}\x01",
        )


def test_login_ack_normalizer_fails_closed_for_non_url_plaintext() -> None:
    with pytest.raises(BrokerConfigurationError, match="invalid URL"):
        normalize_login_ack(
            {
                "sCLMID": "CLMAuthLoginAck",
                "sResultCode": "0",
                "sUrlRequest": "request",
                "sUrlMaster": "master",
                "sUrlPrice": "price",
                "sUrlEvent": "event",
                "sUrlEventWebSocket": "websocket",
            },
            environment="demo",
            decrypt_url=lambda value: f"not-a-url-{value}",
        )


def test_plaintext_classifier_records_shape_without_plaintext_value() -> None:
    value = " \thttps://demo-kabuka.e-shiten.jp/session\x00 "

    diagnosis = _classify_plaintext(
        value,
        {"utf8_decode_success": True, "cp932_decode_success": True, "latin1_fallback_used": False},
    )

    assert diagnosis["plaintext_length"] == len(value)
    assert diagnosis["stripped_length"] == len(value.strip())
    assert diagnosis["starts_with_https"] is True
    assert diagnosis["contains_https"] is True
    assert diagnosis["leading_whitespace"] is True
    assert diagnosis["trailing_whitespace"] is True
    assert diagnosis["null_byte_present"] is True
    assert diagnosis["url_candidate_count"] == 1
    assert diagnosis["url_validation_failure_reason"] == "none"
    assert "https://demo-kabuka.e-shiten.jp/session" not in json.dumps(diagnosis)


def test_plaintext_classifier_classifies_non_url_without_leaking_value() -> None:
    diagnosis = _classify_plaintext("secret plaintext")

    assert diagnosis["url_candidate_count"] == 0
    assert diagnosis["url_validation_failure_reason"] == "no_url_candidate"
    assert "secret plaintext" not in json.dumps(diagnosis)


def test_login_ack_normalizer_fails_closed_for_bad_clmid() -> None:
    with pytest.raises(BrokerConfigurationError, match="CLMAuthLoginAck"):
        normalize_login_ack({"sCLMID": "CLMUnknown", "sResultCode": "0"}, environment="demo", decrypt_url=lambda value: value)


def test_login_ack_normalizer_fails_closed_when_contract_document_unread() -> None:
    with pytest.raises(BrokerConfigurationError, match="unread contract document"):
        normalize_login_ack(
            {
                "sCLMID": "CLMAuthLoginAck",
                "sResultCode": "0",
                "sKinsyouhouMidokuFlg": "1",
                "sUrlRequest": "request",
                "sUrlMaster": "master",
                "sUrlPrice": "price",
                "sUrlEvent": "event",
                "sUrlEventWebSocket": "websocket",
            },
            environment="demo",
            decrypt_url=lambda value: f"https://demo-kabuka.e-shiten.jp/{value}",
        )


def test_sanitizer_redacts_virtual_url_keys() -> None:
    payload = {
        "sUrlRequest": "encrypted-request-url",
        "sUrlPrice": "encrypted-price-url",
        "nested": {"websocket_url": "https://demo.example/ws"},
    }

    assert sanitize_mapping(payload) == {
        "sUrlRequest": "[REDACTED]",
        "sUrlPrice": "[REDACTED]",
        "nested": {"websocket_url": "[REDACTED]"},
    }


def test_http_post_transport_posts_json_and_redacts_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"sCLMID":"CLMAuthLoginAck","sResultCode":"0","sUrlRequest":"encrypted"}'

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["body"] = req.data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr(urllib_request, "urlopen", fake_urlopen)
    transport = HttpPostBrokerTransport(endpoint_url="https://demo.example/auth/", timeout_seconds=7, rate_limit_per_second=0)

    response = transport.request({"sCLMID": "CLMAuthLoginRequest", "sAuthId": "secret-auth-id"})

    assert response["sCLMID"] == "CLMAuthLoginAck"
    assert captured["url"] == "https://demo.example/auth/"
    assert captured["timeout"] == 7
    assert json.loads(captured["body"])["sAuthId"] == "secret-auth-id"


def test_http_post_transport_supports_official_sample_like_form_content_type(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"sCLMID":"CLMZanKaiSummary","p_errno":"0","sSummaryGenkabuKaituke":"1000"}'

    def fake_urlopen(req, timeout):
        captured["body"] = req.data.decode("utf-8")
        captured["content_type"] = req.get_header("Content-type")
        return FakeResponse()

    monkeypatch.setattr(urllib_request, "urlopen", fake_urlopen)
    transport = HttpPostBrokerTransport(
        endpoint_url="https://demo.example/request/",
        rate_limit_per_second=0,
        body_mode="form_urlencoded_json_string",
    )

    response = transport.request({"p_no": 1, "p_sd_date": "2026.06.27-12:00:00.000", "sCLMID": "CLMZanKaiSummary"})

    assert response["sCLMID"] == "CLMZanKaiSummary"
    assert json.loads(captured["body"])["sCLMID"] == "CLMZanKaiSummary"
    assert captured["content_type"] == "application/x-www-form-urlencoded; charset=UTF-8"


def test_http_post_transport_shape_diagnosis_saves_no_body_values() -> None:
    transport = HttpPostBrokerTransport(
        endpoint_url="https://demo.example/request/",
        rate_limit_per_second=0,
        body_mode="form_urlencoded_json_string",
        codec=TachibanaV4R9Codec(),
    )

    diagnosis = transport.diagnose_post_shape(
        {"p_no": 1, "p_sd_date": "2026.06.27-12:00:00.000", "sCLMID": "CLMZanKaiSummary"},
        endpoint_type="request_url",
    )
    serialized = json.dumps(diagnosis)

    assert diagnosis["body_mode"] == "form_urlencoded_json_string"
    assert diagnosis["form_post"] is True
    assert diagnosis["payload_compressed"] is True
    assert diagnosis["body_values_saved"] is False
    assert diagnosis["header_names"] == ["Accept", "Content-Type", "User-Agent"]
    assert "2026.06.27" not in serialized


def test_http_post_transport_accepts_cp932_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return '{"sCLMID":"CLMAuthLoginAck","sResultCode":"0","sResultText":"正常"}'.encode("cp932")

    monkeypatch.setattr(urllib_request, "urlopen", lambda req, timeout: FakeResponse())
    transport = HttpPostBrokerTransport(endpoint_url="https://demo.example/auth/", rate_limit_per_second=0)

    response = transport.request({"sCLMID": "CLMAuthLoginRequest", "sAuthId": "secret-auth-id"})

    assert response["sResultText"] == "正常"


def test_http_post_transport_rejects_non_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"not-json https://secret.example/session"

    monkeypatch.setattr(urllib_request, "urlopen", lambda req, timeout: FakeResponse())
    transport = HttpPostBrokerTransport(endpoint_url="https://demo.example/auth/", rate_limit_per_second=0)

    with pytest.raises(BrokerTransportError) as exc_info:
        transport.request({"sCLMID": "CLMAuthLoginRequest", "sAuthId": "secret-auth-id"})

    assert "https://secret.example" not in str(exc_info.value)


def test_tachibana_demo_login_smoke_default_skipped(tmp_path: Path) -> None:
    result = run_tachibana_demo_login_smoke(reports_dir=tmp_path / "reports", run_enabled=False, env={})

    assert result.status == "SKIPPED"
    assert result.executed is False
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["executed"] is False
    assert payload["virtual_url_saved"] is False


def test_tachibana_demo_login_smoke_cli_default_skipped(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = smoke_cli_main(["--reports-dir", str(tmp_path / "reports")])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["status"] == "SKIPPED"
    assert captured["executed"] is False


def test_tachibana_account_balance_smoke_default_skipped(tmp_path: Path) -> None:
    result = run_tachibana_account_balance_smoke(reports_dir=tmp_path / "reports", run_enabled=False, env={})

    assert result.status == "SKIPPED"
    assert result.executed is False
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["executed"] is False
    assert payload["raw_response_saved"] is False


def test_tachibana_account_transport_diagnosis_default_skipped(tmp_path: Path) -> None:
    result = run_tachibana_account_transport_diagnosis(reports_dir=tmp_path / "reports", run_enabled=False, env={})

    assert result.status == "SKIPPED"
    assert result.executed is False
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["executed"] is False
    assert payload["raw_response_saved"] is False


def test_tachibana_account_error_reveal_default_skipped(tmp_path: Path) -> None:
    result = run_tachibana_account_error_reveal(reports_dir=tmp_path / "reports", run_enabled=False, env={})

    assert result.status == "SKIPPED"
    assert result.executed is False
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["executed"] is False
    assert payload["raw_response_saved"] is False


def test_tachibana_account_balance_smoke_cli_default_skipped(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = account_smoke_cli_main(["--reports-dir", str(tmp_path / "reports")])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["status"] == "SKIPPED"
    assert captured["executed"] is False


def test_tachibana_account_balance_smoke_demo_only_guard(tmp_path: Path) -> None:
    settings = BrokerSettings(
        environment="prod",
        base_url="https://kabuka.e-shiten.jp/e_api_v4r9",
        readonly_smoke_enabled=True,
    )

    result = run_tachibana_account_balance_smoke(reports_dir=tmp_path / "reports", run_enabled=True, settings=settings)

    assert result.status == "FAILED_CONFIGURATION"
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["failure_classification"] == "demo_guard_error"
    assert payload["account_api_called"] is False


def test_tachibana_positions_smoke_default_skipped(tmp_path: Path) -> None:
    result = run_tachibana_positions_smoke(reports_dir=tmp_path / "reports", run_enabled=False, env={})

    assert result.status == "SKIPPED"
    assert result.executed is False
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["executed"] is False
    assert payload["raw_response_saved"] is False


def test_tachibana_positions_smoke_cli_default_skipped(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = positions_smoke_cli_main(["--reports-dir", str(tmp_path / "reports")])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["status"] == "SKIPPED"
    assert captured["executed"] is False


def test_tachibana_positions_smoke_demo_only_guard(tmp_path: Path) -> None:
    settings = BrokerSettings(
        environment="prod",
        base_url="https://kabuka.e-shiten.jp/e_api_v4r9",
        readonly_smoke_enabled=True,
    )

    result = run_tachibana_positions_smoke(reports_dir=tmp_path / "reports", run_enabled=True, settings=settings)

    assert result.status == "FAILED_CONFIGURATION"
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["failure_classification"] == "demo_guard_error"
    assert payload["positions_api_called"] is False


def test_tachibana_orders_smoke_default_skipped(tmp_path: Path) -> None:
    result = run_tachibana_orders_smoke(reports_dir=tmp_path / "reports", run_enabled=False, env={})

    assert result.status == "SKIPPED"
    assert result.executed is False
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["executed"] is False
    assert payload["raw_response_saved"] is False


def test_tachibana_orders_smoke_cli_default_skipped(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = orders_smoke_cli_main(["--reports-dir", str(tmp_path / "reports")])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["status"] == "SKIPPED"
    assert captured["executed"] is False


def test_tachibana_orders_smoke_demo_only_guard(tmp_path: Path) -> None:
    settings = BrokerSettings(
        environment="prod",
        base_url="https://kabuka.e-shiten.jp/e_api_v4r9",
        readonly_smoke_enabled=True,
    )

    result = run_tachibana_orders_smoke(reports_dir=tmp_path / "reports", run_enabled=True, settings=settings)

    assert result.status == "FAILED_CONFIGURATION"
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["failure_classification"] == "demo_guard_error"
    assert payload["orders_api_called"] is False


def test_tachibana_executions_history_smoke_default_skipped(tmp_path: Path) -> None:
    result = run_tachibana_executions_history_smoke(reports_dir=tmp_path / "reports", run_enabled=False, env={})

    assert result.status == "SKIPPED"
    assert result.executed is False
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["executed"] is False
    assert payload["raw_response_saved"] is False


def test_tachibana_executions_history_smoke_cli_default_skipped(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = executions_history_smoke_cli_main(["--reports-dir", str(tmp_path / "reports")])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["status"] == "SKIPPED"
    assert captured["executed"] is False


def test_tachibana_executions_history_smoke_demo_only_guard(tmp_path: Path) -> None:
    settings = BrokerSettings(
        environment="prod",
        base_url="https://kabuka.e-shiten.jp/e_api_v4r9",
        readonly_smoke_enabled=True,
    )

    result = run_tachibana_executions_history_smoke(reports_dir=tmp_path / "reports", run_enabled=True, settings=settings)

    assert result.status == "FAILED_CONFIGURATION"
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["failure_classification"] == "demo_guard_error"
    assert payload["executions_api_called"] is False


def test_tachibana_quote_smoke_default_skipped(tmp_path: Path) -> None:
    result = run_tachibana_quote_smoke(reports_dir=tmp_path / "reports", run_enabled=False, env={})

    assert result.status == "SKIPPED"
    assert result.executed is False
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["executed"] is False
    assert payload["raw_response_saved"] is False


def test_tachibana_quote_smoke_cli_default_skipped(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = quote_smoke_cli_main(["--reports-dir", str(tmp_path / "reports")])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["status"] == "SKIPPED"
    assert captured["executed"] is False


def test_tachibana_quote_smoke_demo_only_guard(tmp_path: Path) -> None:
    settings = BrokerSettings(
        environment="prod",
        base_url="https://kabuka.e-shiten.jp/e_api_v4r9",
        readonly_smoke_enabled=True,
    )

    result = run_tachibana_quote_smoke(reports_dir=tmp_path / "reports", run_enabled=True, settings=settings)

    assert result.status == "FAILED_CONFIGURATION"
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["failure_classification"] == "demo_guard_error"
    assert payload["quotes_api_called"] is False


def test_tachibana_broker_snapshot_default_skipped(tmp_path: Path) -> None:
    snapshot_path = tmp_path / ".runtime/broker/tachibana/demo/latest_broker_snapshot.json"
    result = run_tachibana_broker_snapshot(reports_dir=tmp_path / "reports", snapshot_path=snapshot_path, run_enabled=False, env={})

    assert result.status == "SKIPPED"
    assert result.executed is False
    assert snapshot_path.exists() is False
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["executed"] is False
    assert payload["snapshot_written"] is False


def test_tachibana_broker_snapshot_cli_default_skipped(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    snapshot_path = tmp_path / ".runtime/broker/tachibana/demo/latest_broker_snapshot.json"
    exit_code = broker_snapshot_cli_main(["--reports-dir", str(tmp_path / "reports"), "--snapshot-path", str(snapshot_path)])

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["status"] == "SKIPPED"
    assert captured["executed"] is False
    assert snapshot_path.exists() is False


def test_tachibana_broker_snapshot_demo_only_guard_does_not_write_snapshot(tmp_path: Path) -> None:
    snapshot_path = tmp_path / ".runtime/broker/tachibana/demo/latest_broker_snapshot.json"
    settings = BrokerSettings(
        environment="prod",
        base_url="https://kabuka.e-shiten.jp/e_api_v4r9",
        readonly_smoke_enabled=True,
    )

    result = run_tachibana_broker_snapshot(
        reports_dir=tmp_path / "reports",
        snapshot_path=snapshot_path,
        run_enabled=True,
        settings=settings,
    )

    assert result.status == "FAILED_CONFIGURATION"
    assert snapshot_path.exists() is False
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["failure_classification"] == "demo_guard_error"
    assert payload["snapshot_written"] is False


def test_tachibana_broker_snapshot_redaction_status_schema() -> None:
    status = _redaction_status()

    assert status == {
        "raw_response_saved": False,
        "virtual_url_saved": False,
        "auth_identifier_saved": False,
        "private_secret_saved": False,
        "account_customer_id_saved": False,
        "order_number_plaintext_saved": False,
        "execution_id_plaintext_saved": False,
    }


def test_tachibana_broker_snapshot_atomic_write_replaces_complete_json(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "latest_broker_snapshot.json"

    _write_json_atomic(snapshot_path, {"schema_version": "tachibana_broker_snapshot_v1", "value": 1})
    _write_json_atomic(snapshot_path, {"schema_version": "tachibana_broker_snapshot_v1", "value": 2})

    assert json.loads(snapshot_path.read_text(encoding="utf-8"))["value"] == 2
    assert not snapshot_path.with_suffix(".json.tmp").exists()


def test_account_balance_normalizers_return_money_fields_without_account_id() -> None:
    account = normalize_balance_summary(
        BrokerResponseEnvelope(
            {
                "sCLMID": "CLMZanKaiSummary",
                "sResultCode": "0",
                "sGenbutuKabuKaituke": "1,234",
                "sSyukkinKanougaku": "123",
                "sCustomerId": "customer-secret",
            }
        )
    )
    buying_power = normalize_buying_power(
        BrokerResponseEnvelope(
            {
                "sCLMID": "CLMZanKaiKanougaku",
                "sResultCode": "0",
                "sGenbutuKabuKaituke": "2,345",
                "sCustomerId": "customer-secret",
            }
        )
    )

    assert str(account.buying_power) == "1234"
    assert str(account.withdrawable_cash) == "123"
    assert str(buying_power.buying_power) == "2345"
    assert "customer-secret" not in json.dumps(sanitize_mapping(account.__dict__), default=str)
    assert "customer-secret" not in json.dumps(sanitize_mapping(buying_power.__dict__), default=str)


def test_position_normalizers_return_sanitized_position_fields_without_account_id() -> None:
    cash = normalize_cash_positions(
        BrokerResponseEnvelope(
            {
                "sCLMID": "CLMGenbutuKabuList",
                "sResultCode": "0",
                "aGenbutuKabuList": [
                    {
                        "sIssueCode": "7203",
                        "sIssueName": "TOYOTA",
                        "sQuantity": "100",
                        "sAveragePrice": "2,000",
                        "sMarketValue": "250000",
                        "sUnrealizedPnl": "50000",
                        "sCustomerId": "customer-secret",
                    }
                ],
            }
        )
    )
    margin = normalize_margin_positions(
        BrokerResponseEnvelope(
            {
                "sCLMID": "CLMShinyouTategyokuList",
                "sResultCode": "0",
                "aShinyouTategyokuList": [
                    {
                        "sIssueCode": "6758",
                        "sIssueName": "SONY",
                        "sQuantity": "10",
                        "sBokaTanka": "1000",
                        "sHyokaGaku": "12000",
                        "sHyokaSoneki": "2000",
                        "sCustomerId": "customer-secret",
                    }
                ],
            }
        )
    )

    assert cash[0].issue_code == "7203"
    assert str(cash[0].quantity) == "100"
    assert str(cash[0].average_price) == "2000"
    assert str(cash[0].market_value) == "250000"
    assert str(cash[0].unrealized_pnl) == "50000"
    assert margin[0].issue_code == "6758"
    assert str(margin[0].market_value) == "12000"
    assert "customer-secret" not in json.dumps([_position_dict(item) for item in cash + margin], default=str)


def test_order_normalizers_hash_order_number_and_keep_sanitized_fields() -> None:
    orders = normalize_order_list(
        BrokerResponseEnvelope(
            {
                "sCLMID": "CLMOrderList",
                "sResultCode": "0",
                "aOrderList": [
                    {
                        "sOrderNumber": "ORDER-SECRET-001",
                        "sOrderIssueCode": "7203",
                        "sIssueName": "TOYOTA",
                        "sOrderBaibaiKubun": "1",
                        "sOrderOrderSuryou": "100",
                        "sOrderOrderPrice": "2500",
                        "sOrderStatus": "accepted",
                        "sOrderYakuzyouStatus": "none",
                        "sOrderOrderDateTime": "2026-06-27 09:00:00",
                    }
                ],
            }
        )
    )
    details = normalize_order_list_detail(
        BrokerResponseEnvelope(
            {
                "sCLMID": "CLMOrderListDetail",
                "sResultCode": "0",
                "aOrderList": [
                    {
                        "sOrderOrderNumber": "ORDER-SECRET-001",
                        "sOrderIssueCode": "7203",
                        "sOrderYakuzyouSuryo": "10",
                        "sOrderYakuzyouPrice": "2510",
                        "sOrderYakuzyouStatus": "partial",
                    }
                ],
            }
        )
    )

    assert orders[0].order_id == "ORDER-SECRET-001"
    assert orders[0].issue_code == "7203"
    assert orders[0].side == "buy"
    assert str(orders[0].quantity) == "100"
    assert str(orders[0].price) == "2500"
    assert details[0].order_id == "ORDER-SECRET-001"
    assert str(details[0].executed_quantity) == "10"
    serialized = json.dumps([_order_dict(item) for item in orders + details], default=str)
    assert "ORDER-SECRET-001" not in serialized
    assert "order_id_hash" in serialized


def test_execution_normalizer_and_serializer_do_not_save_order_number_plaintext() -> None:
    executions = normalize_order_detail_executions(
        BrokerResponseEnvelope(
            {
                "sCLMID": "CLMOrderListDetail",
                "sResultCode": "0",
                "sOrderIssueCode": "7203",
                "sIssueName": "TOYOTA",
                "aYakuzyouSikkouList": [
                    {
                        "sYakuzyouDate": "20260627090102",
                        "sYakuzyouSuryou": "100",
                        "sYakuzyouPrice": "2500.5",
                    }
                ],
            }
        ),
        order_id="ORDER-SECRET-001",
    )

    assert executions[0].order_id == "ORDER-SECRET-001"
    assert executions[0].issue_code == "7203"
    assert str(executions[0].quantity) == "100"
    serialized = json.dumps([_execution_dict(item) for item in executions], default=str)
    assert "ORDER-SECRET-001" not in serialized
    assert executions[0].executed_at == "20260627090102"
    assert "order_id_hash" in serialized
    assert "execution_id_hash" in serialized


def test_quote_normalizer_and_serializer_keep_sanitized_quote_fields() -> None:
    quotes = normalize_market_quotes(
        BrokerResponseEnvelope(
            {
                "sCLMID": "CLMMfdsGetMarketPrice",
                "sResultCode": "0",
                "aCLMMfdsMarketPrice": [
                    {
                        "sIssueCode": "7203",
                        "pDPP": "2500.5",
                        "tDPP:T": "09:00:01",
                        "pDOP": "2490",
                        "pDHP": "2510",
                        "pDLP": "2480",
                        "pDV": "123456",
                        "pPRP": "1.23",
                        "sUrlRequest": "secret-virtual-url",
                    }
                ],
            }
        )
    )

    serialized = json.dumps([_quote_dict(item) for item in quotes], default=str)
    assert quotes[0]["issue_code"] == "7203"
    assert str(quotes[0]["last_price"]) == "2500.5"
    assert "secret-virtual-url" not in serialized
    assert "raw_response" not in serialized.lower()


def test_response_summary_keeps_key_names_without_sensitive_values() -> None:
    summary = _response_summary({"sCLMID": "CLMZanKaiSummary", "sResultCode": "0", "p_errno": "0", "sCustomerId": "customer-secret"})

    assert summary["sCLMID"] == "CLMZanKaiSummary"
    assert summary["api_error_number_present"] is True
    assert "[REDACTED_FIELD_NAME]" in summary["sanitized_key_names"]
    assert "customer-secret" not in json.dumps(summary)


def test_account_balance_key_diagnosis_redacts_values_and_identifies_candidates() -> None:
    diagnosis = diagnose_account_balance_keys(
        {
            "sCLMID": "CLMZanKaiKanougaku",
            "sSummaryGenkabuKaituke": "20000000",
            "sSyukkin": "17989000",
            "sIPOKounyu": "17989000",
            "sSinyouSinkidate": "54512121",
            "sCustomerId": "secret-customer",
        }
    )
    serialized = json.dumps(diagnosis, ensure_ascii=False)

    assert diagnosis["nonzero_numeric_field_count"] == 4
    assert diagnosis["web_display_candidates"]["web_cash_buying_power"]["matches_web_display_candidate"] is True
    assert diagnosis["web_display_candidates"]["web_withdrawable_cash"]["matches_web_display_candidate"] is True
    assert diagnosis["web_display_candidates"]["web_ipo_buying_power"]["matches_web_display_candidate"] is True
    assert diagnosis["web_display_candidates"]["web_margin_buying_power"]["matches_web_display_candidate"] is True
    assert "20000000" not in serialized
    assert "17989000" not in serialized
    assert "54512121" not in serialized
    assert "secret-customer" not in serialized
    assert "sCustomerId" not in serialized
    assert "[REDACTED_FIELD_NAME]" in serialized


def test_account_protocol_error_classifies_without_values() -> None:
    diagnosis = classify_protocol_error({"p_errno": "2", "p_err": "internal error occurs with session inactive"})
    serialized = json.dumps(diagnosis)

    assert diagnosis["p_errno_present"] is True
    assert diagnosis["p_errno_numeric"] is True
    assert diagnosis["p_errno_zero"] is False
    assert diagnosis["p_errno_digit_length"] == 1
    assert diagnosis["p_err_present"] is True
    assert diagnosis["p_err_length_bucket"] in {"medium", "long"}
    assert diagnosis["p_err_classification"] in {"session_related", "client_internal_error_related"}
    assert diagnosis["protocol_error_present"] is True
    assert "internal error occurs" not in serialized
    assert '"2"' not in serialized


def test_account_protocol_error_zero_is_not_error() -> None:
    diagnosis = classify_protocol_error({"p_errno": "0", "p_err": ""})

    assert diagnosis["p_errno_present"] is True
    assert diagnosis["p_errno_numeric"] is True
    assert diagnosis["p_errno_zero"] is True
    assert diagnosis["p_err_empty"] is True
    assert diagnosis["protocol_error_present"] is False


def test_account_request_shape_diagnosis_saves_no_values() -> None:
    payload = {
        "p_no": 123,
        "p_sd_date": "2026.06.27-12:34:56.789",
        "sCLMID": "CLMZanKaiKanougaku",
        "sIssueCode": "",
        "sSizyouC": "",
    }

    diagnosis = diagnose_account_request_shape(payload, endpoint_type="request_url", codec=TachibanaV4R9Codec())
    serialized = json.dumps(diagnosis)

    assert diagnosis["sclmid"] == "CLMZanKaiKanougaku"
    assert diagnosis["endpoint_type"] == "request_url"
    assert diagnosis["payload_compressed"] is True
    assert diagnosis["p_no_present"] is True
    assert diagnosis["p_sd_date_present"] is True
    assert diagnosis["sIssueCode_present"] is True
    assert diagnosis["sSizyouC_present"] is True
    assert diagnosis["encoded_sclmid_key"] == "333"
    assert diagnosis["values_saved"] is False
    assert "2026.06.27" not in serialized
    assert "123" not in serialized


def test_account_balance_issue_classifier_for_protocol_error() -> None:
    account_error = classify_protocol_error({"p_errno": "2", "p_err": "opaque protocol error"})
    buying_error = classify_protocol_error({"p_errno": "2", "p_err": "opaque protocol error"})
    account_shape = diagnose_account_request_shape(
        {"p_no": 1, "p_sd_date": "x", "sCLMID": "CLMZanKaiSummary"},
        endpoint_type="request_url",
        codec=TachibanaV4R9Codec(),
    )
    buying_shape = diagnose_account_request_shape(
        {"p_no": 2, "p_sd_date": "x", "sCLMID": "CLMZanKaiKanougaku", "sIssueCode": "", "sSizyouC": ""},
        endpoint_type="request_url",
        codec=TachibanaV4R9Codec(),
    )
    no_business_fields = diagnose_account_balance_keys({"p_errno": "2", "p_err": "opaque protocol error", "sCLMID": "CLMZanKaiSummary"})

    classification = classify_account_balance_issue(
        account_error=account_error,
        buying_power_error=buying_error,
        account_shape=account_shape,
        buying_power_shape=buying_shape,
        account_field_diagnosis=no_business_fields,
        buying_power_field_diagnosis=no_business_fields,
    )

    assert classification["primary"] == "UNKNOWN_PROTOCOL_ERROR"
    assert classification["request_shape_missing"] is False
    assert classification["protocol_error_present"] is True
    assert classification["business_fields_present"] is False


def test_transport_compatibility_classifier_detects_alternate_mode_success() -> None:
    classification = classify_transport_compatibility(
        [
            {
                "body_mode": "json_body",
                "business_fields_present": False,
                "protocol_error_present": True,
            },
            {
                "body_mode": "form_urlencoded_json_string",
                "business_fields_present": True,
                "protocol_error_present": False,
            },
        ]
    )

    assert classification["primary"] == "POST_BODY_MODE_MISMATCH"
    assert "CONTENT_TYPE_MISMATCH" in classification["candidates"]
    assert classification["alternate_mode_business_fields_present"] is True


def test_transport_compatibility_classifier_keeps_protocol_error_when_both_modes_fail() -> None:
    classification = classify_transport_compatibility(
        [
            {
                "body_mode": "json_body",
                "business_fields_present": False,
                "protocol_error_present": True,
            },
            {
                "body_mode": "form_urlencoded_json_string",
                "business_fields_present": False,
                "protocol_error_present": True,
            },
        ]
    )

    assert classification["primary"] == "UNKNOWN_PROTOCOL_ERROR"
    assert "ACCOUNT_PERMISSION_OR_STATE" in classification["candidates"]


def test_reveal_protocol_error_persists_only_allowed_error_values() -> None:
    reveal = reveal_protocol_error(
        {
            "sCLMID": "CLMZanKaiSummary",
            "p_errno": "2",
            "p_err": "session inactive",
            "p_no": "1",
            "p_sd_date": "2026.06.27-12:00:00.000",
        },
        request_payload={"p_no": 1, "p_sd_date": "2026.06.27-12:00:00.000", "sCLMID": "CLMZanKaiSummary"},
        endpoint_type="request_url",
        body_mode="json_body",
        codec=TachibanaV4R9Codec(),
    )
    serialized = json.dumps(reveal)

    assert reveal["clmid"] == "CLMZanKaiSummary"
    assert reveal["p_errno"] == "2"
    assert reveal["p_err"] == "session inactive"
    assert reveal["p_errno_saved"] is True
    assert reveal["p_err_saved"] is True
    assert reveal["raw_response_saved"] is False
    assert reveal["request_body_values_saved"] is False
    assert "2026.06.27" not in serialized


def test_revealed_account_error_classifier_identifies_session_precondition() -> None:
    classification = classify_revealed_account_error(
        [
            {"p_errno": "2", "p_err": "session inactive", "business_fields_present": False},
            {"p_errno": "2", "p_err": "session inactive", "business_fields_present": False},
        ]
    )

    assert classification["primary"] == "REQUEST_PRECONDITION_MISSING"
    assert classification["p_errno_values"] == ["2"]


def test_revealed_account_error_classifier_identifies_p_no_precondition() -> None:
    classification = classify_revealed_account_error(
        [
            {"p_errno": "6", "p_err": "引数（p_no:[1] <= 前要求.p_no:[1]）エラー。", "business_fields_present": False},
            {"p_errno": "6", "p_err": "引数（p_no:[1] <= 前要求.p_no:[1]）エラー。", "business_fields_present": False},
        ]
    )

    assert classification["primary"] == "REQUEST_PRECONDITION_MISSING"
    assert classification["p_errno_values"] == ["6"]


def test_tachibana_failure_classifier_identifies_login_ack_result_error() -> None:
    assert _classify_failure("Tachibana login failed.") == "login_ack_result_error"


def test_login_ack_classifier_records_success_without_virtual_url_values() -> None:
    diagnosis = classify_login_ack(
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sResultText": "",
            "sKinsyouhouMidokuFlg": "0",
            "sUrlRequest": "secret-request-url",
            "sUrlPrice": "secret-price-url",
        },
        decrypt_attempted=True,
        decrypt_success=True,
    )

    assert diagnosis["failure_stage"] == "session_decrypt_or_normalize"
    assert diagnosis["result_code_success"] is True
    assert diagnosis["result_text_classification"] == "empty"
    assert diagnosis["kinsyouhou_midoku_present"] is True
    assert diagnosis["kinsyouhou_midoku"] == "0"
    assert diagnosis["kinsyouhou_midoku_is_zero"] is True
    assert diagnosis["virtual_url_keys_present"] is True
    assert "sUrlRequest" not in diagnosis["ack_keys_sanitized"]
    assert "secret-request-url" not in json.dumps(diagnosis)


def test_login_ack_classifier_records_failed_nonsecret_result_code() -> None:
    diagnosis = classify_login_ack({"sCLMID": "CLMAuthLoginAck", "sResultCode": "101", "sResultText": "認証エラー"})

    assert diagnosis["failure_stage"] == "login_ack_result"
    assert diagnosis["result_code"] == "101"
    assert diagnosis["result_code_success"] is False
    assert diagnosis["result_text_classification"] == "auth_related"


def test_login_ack_classifier_records_contract_document_unread_flag() -> None:
    diagnosis = classify_login_ack(
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sResultText": "",
            "sKinsyouhouMidokuFlg": "1",
            "sUrlRequest": "secret-request-url",
        }
    )

    assert diagnosis["failure_stage"] == "login_ack_kinsyouhou_midoku"
    assert diagnosis["kinsyouhou_midoku_present"] is True
    assert diagnosis["kinsyouhou_midoku"] == "1"
    assert diagnosis["kinsyouhou_midoku_is_zero"] is False
    assert "secret-request-url" not in json.dumps(diagnosis)


def test_login_ack_classifier_records_missing_contract_document_flag() -> None:
    diagnosis = classify_login_ack({"sCLMID": "CLMAuthLoginAck", "sResultCode": "0", "sResultText": "", "sUrlRequest": "secret-request-url"})

    assert diagnosis["failure_stage"] == "session_decrypt_or_normalize"
    assert diagnosis["kinsyouhou_midoku_present"] is False
    assert diagnosis["kinsyouhou_midoku"] == ""
    assert diagnosis["kinsyouhou_midoku_is_zero"] is False


def test_login_ack_classifier_handles_unknown_shape() -> None:
    diagnosis = classify_login_ack({"p_errno": 2, "p_err": "internal error"})

    assert diagnosis["failure_stage"] == "api_error_envelope"
    assert diagnosis["clmid_is_login_ack"] is False
    assert diagnosis["result_code_present"] is False


@pytest.mark.parametrize("result_code", [0, "0", "00", "０", "", None])
def test_login_ack_classifier_accepts_result_code_type_variants(result_code) -> None:
    diagnosis = classify_login_ack({"sCLMID": "CLMAuthLoginAck", "sResultCode": result_code, "sResultText": ""})

    assert diagnosis["result_code_success"] is True


def test_request_shape_diagnosis_does_not_leak_auth_id() -> None:
    settings = BrokerSettings(auth_id="secret-auth-id")
    payload = {"p_no": 1, "p_sd_date": "2026.06.27-12:00:00.000", "sCLMID": "CLMAuthLoginRequest", "sAuthId": "secret-auth-id"}

    diagnosis = diagnose_login_request_shape(settings, payload)

    assert diagnosis["endpoint_type"] == "auth"
    assert diagnosis["endpoint_is_demo"] is True
    assert diagnosis["http_method"] == "POST"
    assert diagnosis["sclmid_is_login_request"] is True
    assert diagnosis["credential_length"] == len("secret-auth-id")
    assert "secret-auth-id" not in json.dumps(diagnosis)


def test_private_key_file_diagnosis_uses_metadata_only(tmp_path: Path) -> None:
    key_path = tmp_path / "e_api_private_key.der"
    key_path.write_bytes(b"fake-key")

    diagnosis = diagnose_private_key_file(key_path, key_format="der")

    assert diagnosis["key_file_present"] is True
    assert diagnosis["key_file_extension"] == "der"
    assert diagnosis["key_file_size_bytes"] == 8
    assert diagnosis["key_format_matches_extension"] is True


def test_private_key_file_diagnosis_identifies_readable_pem(tmp_path: Path) -> None:
    key_path = tmp_path / "e_api_private_key.pem"
    key_path.write_text("not-a-real-key", encoding="utf-8")

    diagnosis = diagnose_private_key_file(key_path, key_format="pem")

    assert diagnosis["key_file_present"] is True
    assert diagnosis["key_file_extension"] == "pem"
    assert "key_openssl_no_pass_readable" in diagnosis
    assert "not-a-real-key" not in json.dumps(diagnosis)


def test_login_ack_classifier_detects_unexpanded_compressed_shape() -> None:
    diagnosis = classify_login_ack({"286": "x", "287": "y", "333": "z"})

    assert diagnosis["failure_stage"] == "login_ack_unexpanded_compressed_shape"


def test_tachibana_v4r9_codec_compresses_login_request_without_leaking_secret() -> None:
    codec = TachibanaV4R9Codec()

    encoded = codec.encode_request(
        {
            "p_no": 1,
            "p_sd_date": "2026.06.27-12:00:00.000",
            "sCLMID": "CLMAuthLoginRequest",
            "sAuthId": "secret-auth-id",
        }
    )

    assert encoded == {
        "288": "1",
        "290": "2026.06.27-12:00:00.000",
        "333": "CLMAuthLoginRequest",
        "317": "secret-auth-id",
    }
    assert sanitize_mapping({"sAuthId": encoded["317"]})["sAuthId"] == "[REDACTED]"


def test_tachibana_v4r9_codec_uncompresses_numeric_login_ack_without_virtual_url_values_in_diagnosis() -> None:
    codec = TachibanaV4R9Codec()

    decoded = codec.decode_response(
        {
            "333": "CLMAuthLoginAck",
            "519": "0",
            "688": "0",
            "689": "",
            "873": "secret-request-url",
            "872": "secret-price-url",
        }
    )
    diagnosis = classify_login_ack(decoded)

    assert decoded["sCLMID"] == "CLMAuthLoginAck"
    assert decoded["sKinsyouhouMidokuFlg"] == "0"
    assert decoded["sResultCode"] == "0"
    assert decoded["sUrlRequest"] == "secret-request-url"
    assert diagnosis["virtual_url_keys_present"] is True
    assert "secret-request-url" not in json.dumps(diagnosis)


def test_tachibana_v4r9_login_ack_virtual_url_mapping_matches_official_v4r9() -> None:
    assert tachibana_codec.TACHIBANA_V4R9_LOGIN_ACK_COLUMNS["sUrlEvent"] == 869
    assert tachibana_codec.TACHIBANA_V4R9_LOGIN_ACK_COLUMNS["sUrlEventWebSocket"] == 870
    assert tachibana_codec.TACHIBANA_V4R9_LOGIN_ACK_COLUMNS["sUrlMaster"] == 871
    assert tachibana_codec.TACHIBANA_V4R9_LOGIN_ACK_COLUMNS["sUrlPrice"] == 872
    assert tachibana_codec.TACHIBANA_V4R9_LOGIN_ACK_COLUMNS["sUrlRequest"] == 873
    assert TachibanaV4R9Codec().decode_response(
        {
            "869": "secret-event-url",
            "870": "secret-websocket-url",
            "871": "secret-master-url",
            "872": "secret-price-url",
            "873": "secret-request-url",
        }
    ) == {
        "sUrlEvent": "secret-event-url",
        "sUrlEventWebSocket": "secret-websocket-url",
        "sUrlMaster": "secret-master-url",
        "sUrlPrice": "secret-price-url",
        "sUrlRequest": "secret-request-url",
    }


def test_virtual_url_candidate_diagnosis_classifies_wrong_and_correct_fields_without_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeDecryptor:
        def __init__(self, private_key_file, key_format, fallback_private_key_file=None):
            self._diagnosis = {}

        def __call__(self, encrypted_value: str) -> str:
            if encrypted_value == "good-cipher":
                self._diagnosis = {
                    "ciphertext": {"base64_alphabet": "standard"},
                    "plaintext": {"contains_http": True, "contains_https": True, "contains_ws": False, "contains_wss": False},
                }
                return "https://demo-kabuka.e-shiten.jp/e_api_v4r9/request/"
            self._diagnosis = {
                "ciphertext": {"base64_alphabet": "standard"},
                "plaintext": {"contains_http": False, "contains_https": False, "contains_ws": False, "contains_wss": False},
            }
            return "not-a-url"

        def safe_diagnosis(self):
            return self._diagnosis

    monkeypatch.setattr("ai_fund_lab_v2.broker.tachibana_smoke.OpenSslRsaOaepDecryptor", FakeDecryptor)

    diagnosis = _diagnose_virtual_url_candidates(
        {
            "sUrlRequest": "good-cipher",
            "sUrlMaster": "bad-cipher",
            "sUrlPrice": "bad-cipher",
            "sUrlEvent": "bad-cipher",
            "sUrlEventWebSocket": "bad-cipher",
        },
        private_key_file=tmp_path / "key.pem",
        key_format="pem",
        fallback_private_key_file=None,
    )

    by_field = {item["field_name"]: item for item in diagnosis}

    assert by_field["sUrlRequest"]["decrypt_success"] is True
    assert by_field["sUrlRequest"]["base64_classification"] == "standard"
    assert by_field["sUrlRequest"]["decoded_byte_length"] == 0
    assert by_field["sUrlRequest"]["plaintext_length"] == 0
    assert by_field["sUrlRequest"]["plaintext_contains_https"] is True
    assert by_field["sUrlRequest"]["starts_with_https"] is False
    assert by_field["sUrlRequest"]["validation_passed"] is True
    assert by_field["sUrlRequest"]["failure_classification"] == ""
    assert by_field["sUrlMaster"]["decrypt_success"] is True
    assert by_field["sUrlMaster"]["plaintext_contains_https"] is False
    assert by_field["sUrlMaster"]["validation_passed"] is False
    assert by_field["sUrlMaster"]["failure_classification"] == "validation_unknown"
    assert by_field["sUrlEventWebSocket"]["validation_passed"] is True
    assert by_field["sUrlEventWebSocket"]["websocket_optional_unavailable"] is True
    assert "good-cipher" not in json.dumps(diagnosis)
    assert "https://demo-kabuka.e-shiten.jp" not in json.dumps(diagnosis)
    assert sanitize_mapping({"virtual_url_candidates": diagnosis})["virtual_url_candidates"] == diagnosis


def test_login_ack_classifier_prioritizes_success_ack_over_auxiliary_error_keys() -> None:
    diagnosis = classify_login_ack(
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sResultText": "",
            "sUrlRequest": "secret-request-url",
            "p_errno": "0",
            "p_err": "",
        }
    )

    assert diagnosis["failure_stage"] == "session_decrypt_or_normalize"


def test_tachibana_v4r9_codec_uncompresses_api_error_envelope() -> None:
    diagnosis = classify_login_ack(TachibanaV4R9Codec().decode_response({"286": "internal", "287": "2", "288": "1", "333": "CLMAuthLoginRequest"}))

    assert diagnosis["failure_stage"] == "api_error_envelope"
    assert diagnosis["api_error_number_present"] is True
    assert diagnosis["api_error_text_present"] is True


def test_http_post_transport_applies_codec_without_saving_raw_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"333":"CLMAuthLoginAck","688":"0","689":"","873":"encrypted-request"}'

    def fake_urlopen(req, timeout):
        captured["body"] = req.data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr(urllib_request, "urlopen", fake_urlopen)
    transport = HttpPostBrokerTransport(endpoint_url="https://demo.example/auth/", rate_limit_per_second=0, codec=TachibanaV4R9Codec())

    response = transport.request({"p_no": 1, "p_sd_date": "2026.06.27-12:00:00.000", "sCLMID": "CLMAuthLoginRequest", "sAuthId": "secret-auth-id"})

    assert json.loads(captured["body"])["333"] == "CLMAuthLoginRequest"
    assert response["sCLMID"] == "CLMAuthLoginAck"
    assert response["sUrlRequest"] == "encrypted-request"


def test_tachibana_v4r9_codec_failed_uncompress_fails_closed() -> None:
    codec = TachibanaV4R9Codec()
    malformed = {}
    malformed["333"] = malformed

    with pytest.raises(TachibanaCodecError):
        codec.decode_response(malformed)


def test_openssl_decryptor_uses_oaep_sha256_and_mgf1_sha256(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    key_path = tmp_path / "key.pem"
    key_path.write_text("fake", encoding="utf-8")
    calls = []

    def fake_run(cmd, check, capture_output, timeout):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=b"https://demo.example/session")

    monkeypatch.setattr(tachibana_crypto.subprocess, "run", fake_run)

    result = OpenSslRsaOaepDecryptor(key_path, key_format="pem")("Y2lwaGVy")

    assert result == "https://demo.example/session"
    assert "rsa_padding_mode:oaep" in calls[0]
    assert "rsa_oaep_md:sha256" in calls[0]
    assert "rsa_mgf1_md:sha256" in calls[0]


def test_openssl_decryptor_falls_back_to_pem_without_leaking_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    der_path = tmp_path / "key.der"
    pem_path = tmp_path / "key.pem"
    der_path.write_bytes(b"fake-der")
    pem_path.write_text("fake-pem", encoding="utf-8")
    calls = []

    def fake_run(cmd, check, capture_output, timeout):
        calls.append(cmd)
        if str(der_path) in cmd:
            raise subprocess.CalledProcessError(1, cmd, stderr=b"decrypt failed")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"https://demo.example/fallback")

    monkeypatch.setattr(tachibana_crypto.subprocess, "run", fake_run)

    result = OpenSslRsaOaepDecryptor(der_path, key_format="der", fallback_private_key_file=pem_path)("Y2lwaGVy")

    assert result == "https://demo.example/fallback"
    assert any("-keyform" in cmd and "DER" in cmd for cmd in calls)
    assert any(str(pem_path) in cmd for cmd in calls)
    diagnosis = OpenSslRsaOaepDecryptor(der_path, key_format="der", fallback_private_key_file=pem_path)


def test_decryptor_records_ciphertext_diagnosis_without_ciphertext(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    key_path = tmp_path / "key.pem"
    key_path.write_text("fake", encoding="utf-8")

    def fake_run(cmd, check, capture_output, timeout):
        return subprocess.CompletedProcess(cmd, 0, stdout=b"https://demo.example/session")

    monkeypatch.setattr(tachibana_crypto.subprocess, "run", fake_run)
    decryptor = OpenSslRsaOaepDecryptor(key_path, key_format="pem")

    decryptor("Y2lwaGVy")
    diagnosis = decryptor.safe_diagnosis()

    assert diagnosis["ciphertext"]["base64_alphabet"] == "standard"
    assert diagnosis["ciphertext"]["decoded_bytes_length"] == len(b"cipher")
    assert diagnosis["plaintext"]["starts_with_https"] is True
    assert "Y2lwaGVy" not in json.dumps(diagnosis)
    assert "https://demo.example/session" not in json.dumps(diagnosis)


def test_decryptor_accepts_urlsafe_base64_without_leaking_ciphertext(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    key_path = tmp_path / "key.pem"
    key_path.write_text("fake", encoding="utf-8")

    def fake_run(cmd, check, capture_output, timeout):
        return subprocess.CompletedProcess(cmd, 0, stdout=b"https://demo.example/session")

    monkeypatch.setattr(tachibana_crypto.subprocess, "run", fake_run)
    decryptor = OpenSslRsaOaepDecryptor(key_path, key_format="pem")

    decryptor("--8")

    assert decryptor.safe_diagnosis()["ciphertext"]["base64_alphabet"] == "urlsafe"
