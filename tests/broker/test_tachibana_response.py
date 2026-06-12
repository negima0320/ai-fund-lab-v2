from ai_fund_lab_v2.broker import BrokerResponseEnvelope


def test_response_envelope_exposes_status_fields_and_raw() -> None:
    raw = {"sCLMID": "CLMZanKaiSummary", "sResultCode": "0", "sResultText": "", "sWarningCode": "0", "sWarningText": ""}

    envelope = BrokerResponseEnvelope(raw)

    assert envelope.raw is raw
    assert envelope.clmid == "CLMZanKaiSummary"
    assert envelope.result_code == "0"
    assert envelope.result_text == ""
    assert envelope.warning_code == "0"
    assert envelope.warning_text == ""
    assert envelope.is_success()


def test_response_envelope_safe_repr_sanitizes_urls_and_secrets() -> None:
    envelope = BrokerResponseEnvelope(
        {
            "sCLMID": "CLMAuthLoginAck",
            "sResultCode": "0",
            "sUrlRequest": "https://demo-kabuka.e-shiten.jp/e_api_v4r9/request/secret",
            "account_id": "secret-account",
        }
    )

    text = repr(envelope)

    assert "https://demo-kabuka" not in text
    assert "secret-account" not in text
    assert "[REDACTED]" in text


def test_response_envelope_failure_status() -> None:
    envelope = BrokerResponseEnvelope({"sCLMID": "CLMOrderList", "sResultCode": "100", "sResultText": "error"})

    assert not envelope.is_success()
    assert envelope.result_text == "error"
