from ai_fund_lab_v2.broker import hash_account_id, sanitize_mapping, sanitize_text


def test_sanitize_text_masks_urls() -> None:
    text = "request url https://demo-kabuka.e-shiten.jp/e_api_v4r9/request/secret"

    sanitized = sanitize_text(text)

    assert "https://demo-kabuka" not in sanitized
    assert "[REDACTED]" in sanitized


def test_sanitize_mapping_masks_sensitive_values_recursively() -> None:
    data = {
        "sAuthId": "secret-auth",
        "request_url": "https://example.test/secret",
        "account_id": "123456",
        "nested": {"token": "secret-token", "safe": "value"},
        "rows": [{"cookie": "secret-cookie", "url": "https://example.test/session"}],
    }

    sanitized = sanitize_mapping(data)

    text = str(sanitized)
    assert "secret-auth" not in text
    assert "https://example.test" not in text
    assert "123456" not in text
    assert "secret-token" not in text
    assert "secret-cookie" not in text
    assert sanitized["nested"]["safe"] == "value"


def test_hash_account_id_is_stable_and_not_plaintext() -> None:
    first = hash_account_id("account-001")
    second = hash_account_id("account-001")

    assert first == second
    assert first != "account-001"
    assert len(first) == 16
