from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from ai_fund_lab_v2.config.settings import load_dotenv_file


class BrokerConfigurationError(RuntimeError):
    """Raised when required broker configuration is missing or invalid."""


DEMO_BASE_URL = "https://demo-kabuka.e-shiten.jp/e_api_v4r9"
PROD_BASE_URL = "https://kabuka.e-shiten.jp/e_api_v4r9"
DEFAULT_LOCAL_CONFIG_PATH = Path.home() / ".config" / "aifundlab" / "tachibana" / "demo"


def normalize_broker_environment(environment: str | None) -> str:
    normalized = (environment or "").strip().lower()
    if normalized == "prod":
        return "production"
    return normalized


@dataclass(frozen=True)
class BrokerSettings:
    auth_id: str | None = field(default=None, repr=False)
    auth_id_file: Path | None = field(default=None, repr=False)
    private_key_file: Path | None = field(default=None, repr=False)
    private_key_format: str = "der"
    second_password_file: Path | None = field(default=None, repr=False)
    local_config_path: Path | None = None
    base_url: str = DEMO_BASE_URL
    environment: str = "demo"
    timeout_seconds: float = 30.0
    rate_limit_per_second: float = 5.0
    readonly_smoke_enabled: bool = False
    readonly_allow_prod: bool = False
    session_cache_enabled: bool = False
    quote_symbol_limit: int = 50
    quote_columns: str = "pDPP,tDPP:T,pDOP,pDHP,pDLP,pDV,pPRP"

    def __repr__(self) -> str:
        return (
            "BrokerSettings("
            f"auth_id={'[SET]' if self.auth_id else '[MISSING]'}, "
            f"auth_id_file={'[SET]' if self.auth_id_file else '[MISSING]'}, "
            f"private_key_file={'[SET]' if self.private_key_file else '[MISSING]'}, "
            f"private_key_format='{self.private_key_format}', "
            f"second_password_file={'[SET]' if self.second_password_file else '[MISSING]'}, "
            f"local_config_path='{self.local_config_path}', "
            f"base_url='{self.base_url}', "
            f"environment='{self.environment}', "
            f"timeout_seconds={self.timeout_seconds}, "
            f"rate_limit_per_second={self.rate_limit_per_second}, "
            f"readonly_smoke_enabled={self.readonly_smoke_enabled}, "
            f"readonly_allow_prod={self.readonly_allow_prod}, "
            f"session_cache_enabled={self.session_cache_enabled}, "
            f"quote_symbol_limit={self.quote_symbol_limit}"
            ")"
        )

    @property
    def auth_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/auth/"

    def require_auth_id(self) -> str:
        if not self.auth_id:
            raise BrokerConfigurationError(
                "TACHIBANA_API_AUTH_ID is required for Tachibana broker API access. "
                "Set it in your environment or local .env file; never commit it."
            )
        return self.auth_id

    def require_demo_environment(self) -> None:
        if self.environment != "demo":
            raise BrokerConfigurationError("Tachibana Phase10-C live smoke is demo-only.")
        if self.base_url.rstrip("/") != DEMO_BASE_URL:
            raise BrokerConfigurationError("Tachibana Phase10-C live smoke requires the demo base URL.")

    def require_private_key_file(self) -> Path:
        if self.private_key_file is None:
            raise BrokerConfigurationError("TACHIBANA_API_PRIVATE_KEY_FILE is required for Tachibana login URL decrypt.")
        return self.private_key_file


def load_broker_settings(env: Mapping[str, str] | None = None) -> BrokerSettings:
    if env is None:
        load_dotenv_file()
    values = os.environ if env is None else env
    environment = normalize_broker_environment(values.get("TACHIBANA_API_ENV", "demo"))
    default_base_url = PROD_BASE_URL if environment == "production" else DEMO_BASE_URL
    local_config_path = _optional_path(values.get("TACHIBANA_API_LOCAL_CONFIG_PATH")) or DEFAULT_LOCAL_CONFIG_PATH
    return BrokerSettings(
        auth_id=_blank_to_none(values.get("TACHIBANA_API_AUTH_ID")),
        auth_id_file=_optional_path(values.get("TACHIBANA_API_AUTH_ID_FILE")),
        private_key_file=_optional_path(values.get("TACHIBANA_API_PRIVATE_KEY_FILE")),
        private_key_format=values.get("TACHIBANA_API_PRIVATE_KEY_FORMAT", "der").strip().lower(),
        second_password_file=_optional_path(values.get("TACHIBANA_API_SECOND_PASSWORD_FILE")),
        local_config_path=local_config_path,
        base_url=values.get("TACHIBANA_API_BASE_URL", default_base_url).rstrip("/"),
        environment=environment,
        timeout_seconds=float(values.get("TACHIBANA_API_TIMEOUT_SECONDS", "30")),
        rate_limit_per_second=float(values.get("TACHIBANA_API_RATE_LIMIT_PER_SECOND", "5")),
        readonly_smoke_enabled=_parse_bool(values.get("TACHIBANA_API_READONLY_SMOKE_ENABLED"), default=False),
        readonly_allow_prod=_parse_bool(values.get("TACHIBANA_API_READONLY_ALLOW_PROD"), default=False),
        session_cache_enabled=_parse_bool(values.get("TACHIBANA_API_SESSION_CACHE_ENABLED"), default=False),
        quote_symbol_limit=int(values.get("TACHIBANA_API_QUOTE_SYMBOL_LIMIT", "50")),
        quote_columns=values.get("TACHIBANA_API_QUOTE_COLUMNS", "pDPP,tDPP:T,pDOP,pDHP,pDLP,pDV,pPRP").strip(),
    )


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _optional_path(value: str | None) -> Path | None:
    stripped = _blank_to_none(value)
    if not stripped:
        return None
    return Path(stripped).expanduser()


def _parse_bool(value: str | None, *, default: bool) -> bool:
    stripped = _blank_to_none(value)
    if stripped is None:
        return default
    return stripped.lower() in {"1", "true", "yes", "y", "on"}
