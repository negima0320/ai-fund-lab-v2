"""Secret-safe broker configuration diagnostics.

The helpers in this module intentionally expose only booleans and coarse
classifications. They must not return credential values, full paths, raw
requests, raw responses, or decrypted broker URLs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.secrets import (
    DEFAULT_AUTH_ID_FILENAME,
    DEFAULT_PRIVATE_KEY_DER_FILENAME,
    DEFAULT_PRIVATE_KEY_PEM_FILENAME,
)
from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL, BrokerSettings

CONFIGURATION_CLASSIFICATIONS = {
    "missing_auth_id_file",
    "missing_private_key_file",
    "missing_second_password_file",
    "missing_local_config",
    "invalid_demo_url",
    "login_endpoint_missing",
    "account_mapping_missing",
    "demo_environment_mismatch",
    "unknown_configuration_error",
    "configuration_ready",
}


def build_broker_configuration_diagnostic(
    settings: BrokerSettings,
    *,
    error: BaseException | None = None,
) -> dict[str, Any]:
    """Return a secret-safe diagnostic payload for operator manifests."""

    local_config = _path_status(settings.local_config_path)
    auth_id_file = _path_status(_resolve_auth_id_file(settings))
    private_key_file = _path_status(_resolve_private_key_file(settings))
    second_password_file = _path_status(settings.second_password_file)
    demo_base_url_present = settings.base_url.rstrip("/") == DEMO_BASE_URL
    production_base_url_present = settings.base_url.rstrip("/") == PROD_BASE_URL

    classification = _classify(
        settings=settings,
        error=error,
        local_config=local_config,
        auth_id_file=auth_id_file,
        private_key_file=private_key_file,
        second_password_file=second_password_file,
        demo_base_url_present=demo_base_url_present,
    )
    next_action = _next_action(classification)

    return {
        "schema_version": "1",
        "classification": classification,
        "next_action": next_action,
        "configured": classification == "configuration_ready",
        "environment": settings.environment,
        "demo_base_url_present": demo_base_url_present,
        "production_base_url_present": production_base_url_present,
        "local_config_present": bool(local_config["file_exists"]),
        "local_config": local_config,
        "auth_id": {
            "configured": bool(settings.auth_id),
        },
        "auth_id_file": auth_id_file,
        "private_key_file": private_key_file,
        "private_key_format": settings.private_key_format,
        "second_password_file": second_password_file,
        "error_class": error.__class__.__name__ if error is not None else "",
    }


def _classify(
    *,
    settings: BrokerSettings,
    error: BaseException | None,
    local_config: dict[str, bool],
    auth_id_file: dict[str, bool],
    private_key_file: dict[str, bool],
    second_password_file: dict[str, bool],
    demo_base_url_present: bool,
) -> str:
    if settings.environment != "demo":
        return "demo_environment_mismatch"
    if not demo_base_url_present:
        return "invalid_demo_url"
    if settings.local_config_path is None or not local_config["file_exists"] or not local_config["file_readable"]:
        return "missing_local_config"
    if not settings.auth_id and (
        not auth_id_file["configured"] or not auth_id_file["file_exists"] or not auth_id_file["file_readable"]
    ):
        return "missing_auth_id_file"
    if (
        not private_key_file["configured"]
        or not private_key_file["file_exists"]
        or not private_key_file["file_readable"]
    ):
        return "missing_private_key_file"
    if (
        not second_password_file["configured"]
        or not second_password_file["file_exists"]
        or not second_password_file["file_readable"]
    ):
        return "missing_second_password_file"

    if error is None:
        return "configuration_ready"

    message = str(error).lower()
    if "auth_id" in message:
        return "missing_auth_id_file"
    if "private_key" in message or "private key" in message:
        return "missing_private_key_file"
    if "second_password" in message or "second password" in message:
        return "missing_second_password_file"
    if "local_config" in message or "local config" in message:
        return "missing_local_config"
    if "demo" in message and ("environment" in message or "base url" in message):
        return "demo_environment_mismatch"
    if "base url" in message or "invalid demo url" in message:
        return "invalid_demo_url"
    if "login" in message and ("url" in message or "endpoint" in message or "decrypt" in message):
        return "login_endpoint_missing"
    if "account" in message and "mapping" in message:
        return "account_mapping_missing"
    return "unknown_configuration_error"


def _next_action(classification: str) -> str:
    return {
        "missing_auth_id_file": "configure_tachibana_auth_id_file",
        "missing_private_key_file": "configure_tachibana_private_key_file",
        "missing_second_password_file": "configure_tachibana_second_password_file",
        "missing_local_config": "configure_tachibana_local_config",
        "invalid_demo_url": "set_tachibana_demo_base_url",
        "login_endpoint_missing": "check_tachibana_login_endpoint_or_private_key_pair",
        "account_mapping_missing": "check_tachibana_account_mapping",
        "demo_environment_mismatch": "set_tachibana_api_env_demo",
        "unknown_configuration_error": "inspect_sanitized_broker_configuration_and_rerun_submit_once_fixed",
        "configuration_ready": "no_configuration_action_required",
    }.get(classification, "inspect_sanitized_broker_configuration")


def _resolve_auth_id_file(settings: BrokerSettings) -> Path | None:
    if settings.auth_id_file is not None:
        return settings.auth_id_file
    if settings.local_config_path is None:
        return None
    candidate = settings.local_config_path / DEFAULT_AUTH_ID_FILENAME
    return candidate


def _resolve_private_key_file(settings: BrokerSettings) -> Path | None:
    if settings.private_key_file is not None:
        return settings.private_key_file
    if settings.local_config_path is None:
        return None
    filename = DEFAULT_PRIVATE_KEY_PEM_FILENAME if settings.private_key_format == "pem" else DEFAULT_PRIVATE_KEY_DER_FILENAME
    return settings.local_config_path / filename


def _path_status(path: Path | str | None) -> dict[str, bool]:
    if path is None:
        return {
            "configured": False,
            "file_exists": False,
            "file_readable": False,
        }
    path = Path(path)
    exists = False
    readable = False
    try:
        exists = path.exists()
        readable = exists and _readable(path)
    except OSError:
        exists = False
        readable = False
    return {
        "configured": True,
        "file_exists": exists,
        "file_readable": readable,
    }


def _readable(path: Path) -> bool:
    try:
        if path.is_dir():
            next(path.iterdir(), None)
            return True
        with path.open("rb") as handle:
            handle.read(1)
        return True
    except OSError:
        return False
