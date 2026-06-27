from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, BrokerSettings


VIRTUAL_URL_KEYS: tuple[str, ...] = (
    "sUrlRequest",
    "sUrlMaster",
    "sUrlPrice",
    "sUrlEvent",
    "sUrlEventWebSocket",
)
SENSITIVE_ACK_KEYS: frozenset[str] = frozenset(VIRTUAL_URL_KEYS)
FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def normalize_result_code(value: Any) -> str:
    if value is None:
        return ""
    normalized = str(value).strip().translate(FULLWIDTH_DIGITS)
    if normalized and normalized.isdigit() and set(normalized) == {"0"}:
        return "0"
    return normalized


def is_success_result_code(value: Any) -> bool:
    return normalize_result_code(value) in {"", "0"}


def normalize_zero_flag(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().translate(FULLWIDTH_DIGITS)


def classify_result_text(value: Any) -> str:
    if value is None:
        return "missing"
    text = str(value).strip()
    if not text:
        return "empty"
    lowered = text.lower()
    if "auth" in lowered or "認証" in text:
        return "auth_related"
    if "api" in lowered:
        return "api_related"
    if "login" in lowered or "ログイン" in text:
        return "login_related"
    if "format" in lowered or "形式" in text:
        return "format_related"
    return "present_nonempty"


def classify_login_ack(raw: dict[str, Any], *, decrypt_attempted: bool = False, decrypt_success: bool = False) -> dict[str, Any]:
    result_code = normalize_result_code(raw.get("sResultCode"))
    kinsyouhou_midoku = normalize_zero_flag(raw.get("sKinsyouhouMidokuFlg"))
    ack_keys = sorted(str(key) for key in raw.keys() if str(key) not in SENSITIVE_ACK_KEYS)
    virtual_url_keys = sorted(key for key in VIRTUAL_URL_KEYS if key in raw)
    clmid = str(raw.get("sCLMID") or "")
    return {
        "failure_stage": _classify_failure_stage(
            clmid=clmid,
            result_code=result_code,
            kinsyouhou_midoku=kinsyouhou_midoku,
            kinsyouhou_midoku_present="sKinsyouhouMidokuFlg" in raw,
            virtual_url_keys_present=bool(virtual_url_keys),
            ack_keys=ack_keys,
        ),
        "clmid_present": bool(clmid),
        "clmid_is_login_ack": clmid == "CLMAuthLoginAck",
        "api_error_number_present": "p_errno" in raw,
        "api_error_text_present": "p_err" in raw,
        "result_code_present": "sResultCode" in raw,
        "result_code": result_code,
        "result_code_success": is_success_result_code(raw.get("sResultCode")),
        "result_text_present": "sResultText" in raw,
        "result_text_classification": classify_result_text(raw.get("sResultText")),
        "kinsyouhou_midoku_present": "sKinsyouhouMidokuFlg" in raw,
        "kinsyouhou_midoku": kinsyouhou_midoku,
        "kinsyouhou_midoku_is_zero": kinsyouhou_midoku == "0",
        "ack_keys_sanitized": ack_keys,
        "virtual_url_keys_present": bool(virtual_url_keys),
        "virtual_url_key_names_present": virtual_url_keys,
        "virtual_url_decryption_attempted": decrypt_attempted,
        "virtual_url_decryption_success": decrypt_success,
    }


def diagnose_login_request_shape(settings: BrokerSettings, payload: dict[str, Any]) -> dict[str, Any]:
    parsed = urlparse(settings.auth_url)
    auth_id = str(payload.get("sAuthId") or "")
    return {
        "endpoint_type": "auth",
        "endpoint_scheme": parsed.scheme,
        "endpoint_host": parsed.netloc,
        "endpoint_path": parsed.path,
        "endpoint_is_demo": settings.base_url.rstrip("/") == DEMO_BASE_URL,
        "base_url_has_trailing_slash": settings.base_url.endswith("/"),
        "http_method": "POST",
        "content_type": "application/json; charset=utf-8",
        "sclmid_is_login_request": payload.get("sCLMID") == "CLMAuthLoginRequest",
        "p_no_present": "p_no" in payload,
        "p_sd_date_present": "p_sd_date" in payload,
        "credential_present": bool(auth_id),
        "credential_length": len(auth_id),
    }


def diagnose_private_key_file(path: Path | None, *, key_format: str) -> dict[str, Any]:
    if path is None:
        return {
            "key_file_present": False,
            "key_file_extension": "",
            "key_file_size_bytes": 0,
            "key_format_setting": key_format,
            "key_format_matches_extension": False,
            "key_file_readable": False,
            "key_openssl_no_pass_readable": False,
            "key_appears_encrypted": False,
        }
    try:
        exists = path.is_file()
        size = path.stat().st_size if exists else 0
        readable = exists
    except OSError:
        exists = False
        size = 0
        readable = False
    extension = path.suffix.lower().lstrip(".")
    openssl_metadata = (
        _diagnose_openssl_key_read(path, key_format=key_format)
        if exists
        else {"key_openssl_no_pass_readable": False, "key_appears_encrypted": False}
    )
    return {
        "key_file_present": exists,
        "key_file_extension": extension,
        "key_file_size_bytes": size,
        "key_format_setting": key_format,
        "key_format_matches_extension": extension == key_format.lower(),
        "key_file_readable": readable,
        **openssl_metadata,
    }


def _diagnose_openssl_key_read(path: Path, *, key_format: str) -> dict[str, Any]:
    cmd = ["openssl", "pkey", "-in", str(path), "-noout"]
    if key_format.lower() == "der":
        cmd.extend(["-inform", "DER"])
    elif key_format.lower() == "pem":
        cmd.extend(["-inform", "PEM"])
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return {"key_openssl_no_pass_readable": False, "key_appears_encrypted": False}
    stderr = result.stderr.decode("utf-8", errors="ignore")
    return {
        "key_openssl_no_pass_readable": result.returncode == 0,
        "key_appears_encrypted": "EncryptedPrivateKeyInfo" in stderr or "encrypted" in stderr.lower(),
    }


def _classify_failure_stage(
    *,
    clmid: str,
    result_code: str,
    kinsyouhou_midoku: str,
    kinsyouhou_midoku_present: bool,
    virtual_url_keys_present: bool,
    ack_keys: list[str],
) -> str:
    if "p_errno" in ack_keys and not (clmid == "CLMAuthLoginAck" and result_code in {"", "0"} and virtual_url_keys_present):
        return "api_error_envelope"
    if clmid != "CLMAuthLoginAck":
        if ack_keys and all(key.isdigit() for key in ack_keys):
            return "login_ack_unexpanded_compressed_shape"
        return "login_ack_shape"
    if result_code not in {"", "0"}:
        return "login_ack_result"
    if kinsyouhou_midoku_present and kinsyouhou_midoku != "0":
        return "login_ack_kinsyouhou_midoku"
    if not virtual_url_keys_present:
        return "login_ack_missing_virtual_urls"
    return "session_decrypt_or_normalize"
