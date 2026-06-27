from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.client import TachibanaReadOnlyClient
from ai_fund_lab_v2.broker.crypto import OpenSslRsaOaepDecryptor
from ai_fund_lab_v2.broker.diagnosis import classify_login_ack, diagnose_login_request_shape, diagnose_private_key_file
from ai_fund_lab_v2.broker.diagnosis import VIRTUAL_URL_KEYS
from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.broker.response import BrokerResponseEnvelope
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping, sanitize_text
from ai_fund_lab_v2.broker.secrets import DEFAULT_PRIVATE_KEY_PEM_FILENAME, TachibanaSecretLoader
from ai_fund_lab_v2.broker.session import _sanitize_decrypted_https_url, _sanitize_decrypted_websocket_url, normalize_login_ack
from ai_fund_lab_v2.broker.settings import BrokerConfigurationError, BrokerSettings, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_codec import TachibanaV4R9Codec
from ai_fund_lab_v2.broker.transport import HttpPostBrokerTransport


@dataclass(frozen=True)
class TachibanaDemoLoginSmokeResult:
    status: str
    executed: bool
    report_path: Path
    message: str = ""


def run_tachibana_demo_login_smoke(
    *,
    reports_dir: Path,
    run_enabled: bool = False,
    report_filename: str = "phase10c_tachibana_demo_login_smoke_result.json",
    source: str = "phase10c_demo_login_smoke",
    env: dict[str, str] | None = None,
    settings: BrokerSettings | None = None,
) -> TachibanaDemoLoginSmokeResult:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / report_filename
    resolved_settings = settings or load_broker_settings(env=env)
    if not run_enabled:
        payload = {
            "status": "SKIPPED",
            "executed": False,
            "created_at": utc_now_iso(),
            "broker": "tachibana",
            "source": source,
            "environment": resolved_settings.environment,
            "message": "Explicit run flag was not provided; no Tachibana demo login was executed.",
            "secret_saved": False,
            "virtual_url_saved": False,
        }
        _write_json(report_path, payload)
        return TachibanaDemoLoginSmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])
    if not resolved_settings.readonly_smoke_enabled:
        payload = {
            "status": "SKIPPED",
            "executed": False,
            "created_at": utc_now_iso(),
            "broker": "tachibana",
            "source": source,
            "environment": resolved_settings.environment,
            "message": "TACHIBANA_API_READONLY_SMOKE_ENABLED is false; no Tachibana demo login was executed.",
            "secret_saved": False,
            "virtual_url_saved": False,
        }
        _write_json(report_path, payload)
        return TachibanaDemoLoginSmokeResult(status="SKIPPED", executed=False, report_path=report_path, message=payload["message"])
    diagnosis: dict[str, Any] = {}
    try:
        resolved_settings.require_demo_environment()
        secrets = TachibanaSecretLoader(resolved_settings).load()
        auth_settings = replace(
            resolved_settings,
            auth_id=secrets.auth_id,
            auth_id_file=secrets.auth_id_file,
            private_key_file=secrets.private_key_file,
            private_key_format=secrets.private_key_format,
        )
        fallback_key_file = _resolve_fallback_key_file(auth_settings)
        diagnosis["key_file_metadata"] = diagnose_private_key_file(auth_settings.private_key_file, key_format=auth_settings.private_key_format)
        if fallback_key_file is not None:
            diagnosis["fallback_key_file_metadata"] = diagnose_private_key_file(fallback_key_file, key_format="pem")
        codec = TachibanaV4R9Codec()
        auth_transport = HttpPostBrokerTransport(
            endpoint_url=auth_settings.auth_url,
            timeout_seconds=auth_settings.timeout_seconds,
            rate_limit_per_second=auth_settings.rate_limit_per_second,
            codec=codec,
        )
        client = TachibanaReadOnlyClient(auth_settings, auth_transport)
        decryptor = OpenSslRsaOaepDecryptor(
            auth_settings.require_private_key_file(),
            key_format=auth_settings.private_key_format,
            fallback_private_key_file=fallback_key_file,
        )
        login_payload = client.build_login_request()
        diagnosis["request_shape"] = diagnose_login_request_shape(auth_settings, login_payload)
        login_response = BrokerResponseEnvelope(auth_transport.request(login_payload))
        diagnosis["login_ack"] = classify_login_ack(login_response.raw, decrypt_attempted=False, decrypt_success=False)
        if diagnosis["login_ack"].get("virtual_url_keys_present"):
            diagnosis["login_ack"] = classify_login_ack(login_response.raw, decrypt_attempted=True, decrypt_success=False)
            diagnosis["virtual_url_candidates"] = _diagnose_virtual_url_candidates(
                login_response.raw,
                private_key_file=auth_settings.require_private_key_file(),
                key_format=auth_settings.private_key_format,
                fallback_private_key_file=fallback_key_file,
            )
        try:
            session = normalize_login_ack(login_response, environment=auth_settings.environment, decrypt_url=decryptor)
        except BrokerConfigurationError:
            diagnosis["decrypt"] = decryptor.safe_diagnosis()
            raise
        diagnosis["login_ack"] = classify_login_ack(login_response.raw, decrypt_attempted=True, decrypt_success=True)
        diagnosis["decrypt"] = decryptor.safe_diagnosis()
        logout_transport = HttpPostBrokerTransport(
            endpoint_url=session.request_url,
            timeout_seconds=auth_settings.timeout_seconds,
            rate_limit_per_second=auth_settings.rate_limit_per_second,
            codec=codec,
        )
        logout_response = client.logout(session, transport=logout_transport)
        payload = {
            "status": "PASS" if logout_response.is_success() else "PASS_WITH_LOGOUT_WARNING",
            "executed": True,
            "created_at": utc_now_iso(),
            "broker": "tachibana",
            "source": source,
            "environment": auth_settings.environment,
            "diagnosis": diagnosis,
            "login": {"status": "PASS"},
            "logout": {
                "status": "PASS" if logout_response.is_success() else "WARNING",
                "attempted": True,
                "result_code": logout_response.result_code,
                "result_text": sanitize_text(logout_response.result_text),
            },
            "account_api_called": False,
            "positions_api_called": False,
            "orders_api_called": False,
            "quotes_api_called": False,
            "secret_saved": False,
            "virtual_url_saved": False,
        }
        _write_json(report_path, payload)
        return TachibanaDemoLoginSmokeResult(status=str(payload["status"]), executed=True, report_path=report_path)
    except BrokerConfigurationError as exc:
        payload = _failure_payload(resolved_settings, "FAILED_CONFIGURATION", str(exc), source=source, diagnosis=diagnosis)
    except Exception as exc:  # noqa: BLE001 - sanitized boundary for manual smoke CLI.
        payload = _failure_payload(resolved_settings, "FAILED_LOGIN_SESSION", str(exc), source=source, diagnosis=diagnosis)
    _write_json(report_path, payload)
    return TachibanaDemoLoginSmokeResult(status=str(payload["status"]), executed=True, report_path=report_path, message=str(payload["message"]))


def _failure_payload(settings: BrokerSettings, status: str, message: str, *, source: str, diagnosis: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "executed": True,
        "created_at": utc_now_iso(),
        "broker": "tachibana",
        "source": source,
        "environment": settings.environment,
        "message": "Tachibana demo login/session smoke failed before a usable session was confirmed.",
        "diagnosis": diagnosis or {},
        "failure_classification": _classify_failure_from_diagnosis(diagnosis) or _classify_failure(message),
        "login": {"status": "UNKNOWN_OR_FAILED"},
        "logout": {"attempted": False, "status": "NOT_EXECUTED"},
        "account_api_called": False,
        "positions_api_called": False,
        "orders_api_called": False,
        "quotes_api_called": False,
        "secret_saved": False,
        "virtual_url_saved": False,
    }


def _classify_failure(message: str) -> str:
    normalized = message.lower()
    if "codec can't decode" in normalized or "unsupported encoding" in normalized:
        return "response_decode_error"
    if "invalid json" in normalized:
        return "response_json_parse_error"
    if "decrypt" in normalized:
        return "virtual_url_decrypt_error"
    if "tachibana login failed" in normalized:
        return "login_ack_result_error"
    if "unread contract document" in normalized:
        return "login_ack_kinsyouhou_midoku"
    if "not clmauthloginack" in normalized:
        return "login_ack_shape_error"
    if "demo-only" in normalized or "demo base url" in normalized:
        return "demo_guard_error"
    if "auth_id" in normalized or "private_key" in normalized:
        return "local_secret_configuration_error"
    if "timed out" in normalized or "urlopen" in normalized or "http post failed" in normalized:
        return "network_or_http_error"
    return "login_session_error"


def _classify_failure_from_diagnosis(diagnosis: dict[str, Any] | None) -> str:
    if not diagnosis:
        return ""
    login_ack = diagnosis.get("login_ack")
    if not isinstance(login_ack, dict):
        return ""
    failure_stage = str(login_ack.get("failure_stage") or "")
    if failure_stage == "api_error_envelope":
        return "api_error_envelope"
    if failure_stage == "login_ack_unexpanded_compressed_shape":
        return "response_compression_or_unexpand_error"
    if failure_stage == "login_ack_shape":
        return "login_ack_shape_error"
    if failure_stage == "login_ack_result":
        return "login_ack_result_error"
    if failure_stage == "login_ack_kinsyouhou_midoku":
        return "login_ack_kinsyouhou_midoku"
    if failure_stage == "login_ack_missing_virtual_urls":
        return "login_ack_missing_virtual_urls"
    decrypt = diagnosis.get("decrypt")
    if isinstance(decrypt, dict) and decrypt.get("selected_backend"):
        return "decrypted_url_validation_error"
    return ""


def _resolve_fallback_key_file(settings: BrokerSettings) -> Path | None:
    if settings.private_key_format == "pem":
        return None
    if settings.local_config_path is None:
        return None
    candidate = settings.local_config_path / DEFAULT_PRIVATE_KEY_PEM_FILENAME
    return candidate if candidate.is_file() else None


def _diagnose_virtual_url_candidates(
    raw: dict[str, Any],
    *,
    private_key_file: Path,
    key_format: str,
    fallback_private_key_file: Path | None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for field_name in VIRTUAL_URL_KEYS:
        encrypted = raw.get(field_name)
        field_diagnosis: dict[str, Any] = {
            "field_name": field_name,
            "field_present": encrypted is not None,
            "ciphertext_length": len(str(encrypted or "")),
            "base64_classification": "missing",
            "decoded_byte_length": 0,
            "decrypt_attempted": False,
            "decrypt_success": False,
            "plaintext_length": 0,
            "plaintext_contains_http": False,
            "plaintext_contains_https": False,
            "plaintext_contains_ws": False,
            "plaintext_contains_wss": False,
            "starts_with_http": False,
            "starts_with_https": False,
            "starts_with_ws": False,
            "starts_with_wss": False,
            "control_char_present": False,
            "null_byte_present": False,
            "validation_passed": False,
            "websocket_optional_unavailable": False,
            "failure_classification": "missing_field",
        }
        if not encrypted:
            candidates.append(field_diagnosis)
            continue
        decryptor = OpenSslRsaOaepDecryptor(
            private_key_file,
            key_format=key_format,
            fallback_private_key_file=fallback_private_key_file,
        )
        field_diagnosis["decrypt_attempted"] = True
        try:
            decrypted = decryptor(str(encrypted))
        except BrokerConfigurationError:
            decrypt_diagnosis = decryptor.safe_diagnosis()
            ciphertext = decrypt_diagnosis.get("ciphertext", {})
            field_diagnosis["base64_classification"] = str(ciphertext.get("base64_alphabet") or "unknown")
            field_diagnosis["decoded_byte_length"] = int(ciphertext.get("decoded_bytes_length") or 0)
            field_diagnosis["failure_classification"] = "decrypt_failed"
            candidates.append(field_diagnosis)
            continue
        decrypt_diagnosis = decryptor.safe_diagnosis()
        ciphertext = decrypt_diagnosis.get("ciphertext", {})
        plaintext = decrypt_diagnosis.get("plaintext", {})
        field_diagnosis["base64_classification"] = str(ciphertext.get("base64_alphabet") or "unknown")
        field_diagnosis["decoded_byte_length"] = int(ciphertext.get("decoded_bytes_length") or 0)
        field_diagnosis["decrypt_success"] = True
        if isinstance(plaintext, dict):
            field_diagnosis["plaintext_length"] = int(plaintext.get("plaintext_length") or 0)
            field_diagnosis["plaintext_contains_http"] = bool(plaintext.get("contains_http"))
            field_diagnosis["plaintext_contains_https"] = bool(plaintext.get("contains_https"))
            field_diagnosis["plaintext_contains_ws"] = bool(plaintext.get("contains_ws"))
            field_diagnosis["plaintext_contains_wss"] = bool(plaintext.get("contains_wss"))
            field_diagnosis["starts_with_http"] = bool(plaintext.get("starts_with_http"))
            field_diagnosis["starts_with_https"] = bool(plaintext.get("starts_with_https"))
            field_diagnosis["starts_with_ws"] = bool(plaintext.get("starts_with_ws"))
            field_diagnosis["starts_with_wss"] = bool(plaintext.get("starts_with_wss"))
            field_diagnosis["control_char_present"] = bool(plaintext.get("control_char_present"))
            field_diagnosis["null_byte_present"] = bool(plaintext.get("null_byte_present"))
            field_diagnosis["failure_classification"] = str(plaintext.get("url_validation_failure_reason") or "validation_unknown")
        try:
            if field_name == "sUrlEventWebSocket":
                websocket_url = _sanitize_decrypted_websocket_url(decrypted, optional=True)
                field_diagnosis["validation_passed"] = True
                field_diagnosis["websocket_optional_unavailable"] = not bool(websocket_url)
                if not websocket_url:
                    field_diagnosis["failure_classification"] = "websocket_optional_unavailable"
                else:
                    field_diagnosis["failure_classification"] = ""
            else:
                _sanitize_decrypted_https_url(decrypted)
                field_diagnosis["validation_passed"] = True
                field_diagnosis["websocket_optional_unavailable"] = False
                field_diagnosis["failure_classification"] = ""
        except BrokerConfigurationError:
            field_diagnosis["validation_passed"] = False
        candidates.append(field_diagnosis)
    return candidates


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize_mapping(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
