from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping

from ai_fund_lab_v2.config.settings import load_dotenv_file


class BrokerConfigurationError(RuntimeError):
    """Raised when required broker configuration is missing or invalid."""


@dataclass(frozen=True)
class BrokerSettings:
    auth_id: str | None = field(default=None, repr=False)
    base_url: str = "https://demo-kabuka.e-shiten.jp/e_api_v4r9"
    environment: str = "demo"
    timeout_seconds: float = 30.0

    def __repr__(self) -> str:
        return (
            "BrokerSettings("
            f"auth_id={'[SET]' if self.auth_id else '[MISSING]'}, "
            f"base_url='{self.base_url}', "
            f"environment='{self.environment}', "
            f"timeout_seconds={self.timeout_seconds}"
            ")"
        )

    def require_auth_id(self) -> str:
        if not self.auth_id:
            raise BrokerConfigurationError(
                "TACHIBANA_API_AUTH_ID is required for Tachibana broker API access. "
                "Set it in your environment or local .env file; never commit it."
            )
        return self.auth_id


def load_broker_settings(env: Mapping[str, str] | None = None) -> BrokerSettings:
    if env is None:
        load_dotenv_file()
    values = os.environ if env is None else env
    environment = values.get("TACHIBANA_API_ENV", "demo").strip().lower()
    default_base_url = (
        "https://kabuka.e-shiten.jp/e_api_v4r9"
        if environment == "prod"
        else "https://demo-kabuka.e-shiten.jp/e_api_v4r9"
    )
    return BrokerSettings(
        auth_id=_blank_to_none(values.get("TACHIBANA_API_AUTH_ID")),
        base_url=values.get("TACHIBANA_API_BASE_URL", default_base_url).rstrip("/"),
        environment=environment,
        timeout_seconds=float(values.get("TACHIBANA_API_TIMEOUT_SECONDS", "30")),
    )


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
