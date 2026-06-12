import pytest

from ai_fund_lab_v2.broker import BrokerConfigurationError, load_broker_settings


def test_broker_settings_loads_from_env_mapping() -> None:
    settings = load_broker_settings(
        {
            "TACHIBANA_API_AUTH_ID": "secret-auth-id",
            "TACHIBANA_API_BASE_URL": "https://demo.example/e_api_v4r9/",
            "TACHIBANA_API_ENV": "demo",
            "TACHIBANA_API_TIMEOUT_SECONDS": "12.5",
        }
    )

    assert settings.require_auth_id() == "secret-auth-id"
    assert settings.base_url == "https://demo.example/e_api_v4r9"
    assert settings.environment == "demo"
    assert settings.timeout_seconds == 12.5


def test_broker_settings_repr_does_not_leak_auth_id() -> None:
    settings = load_broker_settings({"TACHIBANA_API_AUTH_ID": "very-secret-auth-id"})

    text = repr(settings)

    assert "very-secret-auth-id" not in text
    assert "auth_id=[SET]" in text


def test_missing_broker_auth_id_raises_clear_error_without_secret() -> None:
    settings = load_broker_settings({})

    with pytest.raises(BrokerConfigurationError, match="TACHIBANA_API_AUTH_ID is required"):
        settings.require_auth_id()
