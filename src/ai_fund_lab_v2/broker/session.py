from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

from ai_fund_lab_v2.broker.diagnosis import normalize_zero_flag
from ai_fund_lab_v2.broker.response import BrokerResponseEnvelope
from ai_fund_lab_v2.broker.settings import BrokerConfigurationError


UrlDecryptor = Callable[[str], str]


@dataclass(frozen=True)
class TachibanaSession:
    request_url: str = field(repr=False)
    master_url: str = field(repr=False)
    price_url: str = field(repr=False)
    event_url: str = field(repr=False)
    websocket_url: str = field(repr=False)
    login_at: datetime
    environment: str

    def __repr__(self) -> str:
        return (
            "TachibanaSession("
            "request_url=[REDACTED], "
            "master_url=[REDACTED], "
            "price_url=[REDACTED], "
            "event_url=[REDACTED], "
            "websocket_url=[REDACTED], "
            f"login_at='{self.login_at.isoformat()}', "
            f"environment='{self.environment}'"
            ")"
        )


def normalize_login_ack(
    response: BrokerResponseEnvelope | dict[str, object],
    *,
    environment: str,
    decrypt_url: UrlDecryptor,
    login_at: datetime | None = None,
) -> TachibanaSession:
    envelope = response if isinstance(response, BrokerResponseEnvelope) else BrokerResponseEnvelope(dict(response))
    if envelope.clmid != "CLMAuthLoginAck":
        raise BrokerConfigurationError("Tachibana login response was not CLMAuthLoginAck.")
    if not envelope.is_success():
        raise BrokerConfigurationError("Tachibana login failed.")
    raw = envelope.raw
    _require_kinsyouhou_midoku_read(raw)
    session = TachibanaSession(
        request_url=_decrypt_required(raw, "sUrlRequest", decrypt_url, kind="https"),
        master_url=_decrypt_required(raw, "sUrlMaster", decrypt_url, kind="https"),
        price_url=_decrypt_required(raw, "sUrlPrice", decrypt_url, kind="https"),
        event_url=_decrypt_required(raw, "sUrlEvent", decrypt_url, kind="https"),
        websocket_url=_decrypt_required(raw, "sUrlEventWebSocket", decrypt_url, kind="websocket", optional=True),
        login_at=login_at or datetime.now(timezone.utc),
        environment=environment,
    )
    _validate_session_urls(session)
    return session


def _require_kinsyouhou_midoku_read(raw: dict[str, object]) -> None:
    if "sKinsyouhouMidokuFlg" not in raw:
        return
    if normalize_zero_flag(raw.get("sKinsyouhouMidokuFlg")) != "0":
        raise BrokerConfigurationError("Tachibana login ack indicates unread contract document.")


def _decrypt_required(raw: dict[str, object], key: str, decrypt_url: UrlDecryptor, *, kind: str, optional: bool = False) -> str:
    encrypted = str(raw.get(key) or "")
    if not encrypted:
        if optional:
            return ""
        raise BrokerConfigurationError(f"Tachibana login response is missing {key}.")
    try:
        if kind == "websocket":
            decrypted = _sanitize_decrypted_websocket_url(decrypt_url(encrypted), optional=optional)
        else:
            decrypted = _sanitize_decrypted_https_url(decrypt_url(encrypted))
    except BrokerConfigurationError:
        raise
    except Exception as exc:
        raise BrokerConfigurationError("Tachibana login URL decrypt failed.") from exc
    if not decrypted and not optional:
        raise BrokerConfigurationError("Tachibana login URL decrypt returned an empty value.")
    return decrypted


def _sanitize_decrypted_url(value: str) -> str:
    return _sanitize_decrypted_https_url(value)


def _sanitize_decrypted_https_url(value: str) -> str:
    without_edge_null = _strip_decrypted_url(value)
    if not without_edge_null:
        raise BrokerConfigurationError("Tachibana login URL decrypt returned an empty value.")
    if not without_edge_null.startswith("https://"):
        raise BrokerConfigurationError("Tachibana login URL decrypt returned an invalid URL.")
    parsed = urlparse(without_edge_null)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or not (host.endswith(".e-shiten.jp") and "demo" in host):
        raise BrokerConfigurationError("Tachibana login URL decrypt returned an invalid URL.")
    return without_edge_null


def _sanitize_decrypted_websocket_url(value: str, *, optional: bool) -> str:
    try:
        without_edge_null = _strip_decrypted_url(value)
    except BrokerConfigurationError:
        if optional:
            return ""
        raise
    if not without_edge_null:
        return "" if optional else _raise_empty_url()
    if not (without_edge_null.startswith("wss://") or without_edge_null.startswith("ws://")):
        return "" if optional else _raise_invalid_url()
    parsed = urlparse(without_edge_null)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"wss", "ws"} or not host or not (host.endswith(".e-shiten.jp") and "demo" in host):
        return "" if optional else _raise_invalid_url()
    return without_edge_null


def _strip_decrypted_url(value: str) -> str:
    stripped = value.strip()
    without_edge_null = stripped.strip("\x00").strip()
    if "\x00" in without_edge_null:
        raise BrokerConfigurationError("Tachibana login URL decrypt returned an invalid URL.")
    if any(ord(char) < 32 or ord(char) > 126 for char in without_edge_null):
        raise BrokerConfigurationError("Tachibana login URL decrypt returned an invalid URL.")
    return without_edge_null


def _raise_empty_url() -> str:
    raise BrokerConfigurationError("Tachibana login URL decrypt returned an empty value.")


def _raise_invalid_url() -> str:
    raise BrokerConfigurationError("Tachibana login URL decrypt returned an invalid URL.")


def _validate_session_urls(session: TachibanaSession) -> None:
    for value in (
        session.request_url,
        session.master_url,
        session.price_url,
        session.event_url,
    ):
        try:
            _sanitize_decrypted_https_url(value)
        except BrokerConfigurationError as exc:
            raise BrokerConfigurationError("Tachibana login URL decrypt returned an invalid URL.")
    if session.websocket_url:
        try:
            _sanitize_decrypted_websocket_url(session.websocket_url, optional=False)
        except BrokerConfigurationError as exc:
            raise BrokerConfigurationError("Tachibana login URL decrypt returned an invalid URL.")
