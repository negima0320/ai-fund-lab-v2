from __future__ import annotations

import base64
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.settings import BrokerConfigurationError


@dataclass
class OpenSslRsaOaepDecryptor:
    private_key_file: Path
    key_format: str = "der"
    fallback_private_key_file: Path | None = None
    _diagnosis: dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.key_format = self.key_format.lower()

    def safe_diagnosis(self) -> dict[str, Any]:
        return dict(self._diagnosis)

    def __call__(self, encrypted_value: str) -> str:
        encrypted_bytes, ciphertext_diagnosis = _decode_ciphertext(encrypted_value)
        self._diagnosis = {
            "ciphertext": ciphertext_diagnosis,
            "backend_preference": ["cryptography", "openssl_cli"],
            "cryptography_available": _cryptography_available(),
            "attempts": [],
        }
        errors: list[Exception] = []
        attempts = [(self.private_key_file, self.key_format, "primary")]
        if self.fallback_private_key_file is not None and self.fallback_private_key_file != self.private_key_file:
            attempts.append((self.fallback_private_key_file, "pem", "fallback"))
        for key_file, key_format, role in attempts:
            try:
                decrypted, plaintext_decode = _decrypt_with_cryptography(encrypted_bytes, key_file, key_format=key_format)
                self._diagnosis["attempts"].append({"backend": "cryptography", "role": role, "key_format": key_format, "success": True})
                self._diagnosis["selected_backend"] = "cryptography"
                self._diagnosis["plaintext"] = _classify_plaintext(decrypted, plaintext_decode)
                return decrypted
            except BrokerConfigurationError as exc:
                self._diagnosis["attempts"].append({"backend": "cryptography", "role": role, "key_format": key_format, "success": False})
                errors.append(exc)
            try:
                decrypted, plaintext_decode = _decrypt_with_openssl(encrypted_bytes, key_file, key_format=key_format)
                self._diagnosis["attempts"].append({"backend": "openssl_cli", "role": role, "key_format": key_format, "success": True})
                self._diagnosis["selected_backend"] = "openssl_cli"
                self._diagnosis["plaintext"] = _classify_plaintext(decrypted, plaintext_decode)
                return decrypted
            except BrokerConfigurationError as exc:
                self._diagnosis["attempts"].append({"backend": "openssl_cli", "role": role, "key_format": key_format, "success": False})
                errors.append(exc)
        self._diagnosis["selected_backend"] = ""
        raise BrokerConfigurationError("Tachibana encrypted URL decrypt failed.") from errors[-1] if errors else None


def _cryptography_available() -> bool:
    try:
        import cryptography  # noqa: F401
    except Exception:
        return False
    return True


def _decrypt_with_cryptography(encrypted_bytes: bytes, private_key_file: Path, *, key_format: str) -> tuple[str, dict[str, Any]]:
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except Exception as exc:
        raise BrokerConfigurationError("cryptography backend is not available.") from exc
    try:
        key_data = private_key_file.read_bytes()
        if key_format.lower() == "pem":
            private_key = serialization.load_pem_private_key(key_data, password = None)
        elif key_format.lower() == "der":
            private_key = serialization.load_der_private_key(key_data, password = None)
        else:
            raise BrokerConfigurationError("TACHIBANA_API_PRIVATE_KEY_FORMAT must be der or pem.")
        decrypted = private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        )
    except BrokerConfigurationError:
        raise
    except Exception as exc:
        raise BrokerConfigurationError("Tachibana encrypted URL decrypt failed.") from exc
    return _decode_plaintext_bytes(decrypted)


def _decode_ciphertext(encrypted_value: str) -> tuple[bytes, dict[str, Any]]:
    stripped_whitespace = bool(re.search(r"\s", encrypted_value))
    normalized = re.sub(r"\s+", "", encrypted_value)
    alphabet = "urlsafe" if ("-" in normalized or "_" in normalized) else "standard"
    padding_added = (-len(normalized) % 4)
    normalized = normalized + ("=" * padding_added)
    decoder = base64.urlsafe_b64decode if alphabet == "urlsafe" else base64.b64decode
    try:
        decoded = decoder(normalized) if alphabet == "urlsafe" else decoder(normalized, validate=True)
    except ValueError as exc:
        raise BrokerConfigurationError("Tachibana encrypted URL was not valid base64.") from exc
    return decoded, {
        "base64_alphabet": alphabet,
        "whitespace_stripped": stripped_whitespace,
        "padding_added": padding_added,
        "decoded_bytes_length": len(decoded),
    }


def _decode_plaintext_bytes(value: bytes) -> tuple[str, dict[str, Any]]:
    diagnosis = {
        "utf8_decode_success": False,
        "cp932_decode_success": False,
        "latin1_fallback_used": False,
    }
    try:
        text = value.decode("utf-8")
        diagnosis["utf8_decode_success"] = True
    except UnicodeDecodeError:
        try:
            text = value.decode("cp932")
            diagnosis["cp932_decode_success"] = True
        except UnicodeDecodeError:
            text = value.decode("latin1")
            diagnosis["latin1_fallback_used"] = True
            return text, diagnosis
        return text, diagnosis
    try:
        value.decode("cp932")
        diagnosis["cp932_decode_success"] = True
    except UnicodeDecodeError:
        diagnosis["cp932_decode_success"] = False
    return text, diagnosis


def _classify_plaintext(value: str, decode_diagnosis: dict[str, Any] | None = None) -> dict[str, Any]:
    stripped = value.strip()
    stripped_without_edge_null = stripped.strip("\x00").strip()
    control_char_present = any(ord(char) < 32 for char in value)
    null_byte_present = "\x00" in value
    printable_count = sum(1 for char in value if char.isprintable() or char in "\t\r\n")
    printable_ratio = 1.0 if not value else printable_count / len(value)
    url_candidate_count = stripped.count("https://") + stripped.count("http://") + stripped.count("wss://") + stripped.count("ws://")
    diagnosis = {
        "plaintext_length": len(value),
        "stripped_length": len(stripped),
        "is_empty": not bool(stripped_without_edge_null),
        "starts_with_https": stripped_without_edge_null.startswith("https://"),
        "starts_with_http": stripped_without_edge_null.startswith("http://"),
        "starts_with_wss": stripped_without_edge_null.startswith("wss://"),
        "starts_with_ws": stripped_without_edge_null.startswith("ws://"),
        "contains_https": "https://" in stripped_without_edge_null,
        "contains_http": "http://" in stripped_without_edge_null,
        "contains_wss": "wss://" in stripped_without_edge_null,
        "contains_ws": "ws://" in stripped_without_edge_null,
        "leading_whitespace": bool(value) and value[0].isspace(),
        "trailing_whitespace": bool(value) and value[-1].isspace(),
        "control_char_present": control_char_present,
        "null_byte_present": null_byte_present,
        "printable_ratio_bucket": _bucket_printable_ratio(printable_ratio, bool(value)),
        "url_candidate_count": url_candidate_count,
        "url_validation_failure_reason": _classify_url_validation_failure(value),
    }
    diagnosis.update(
        decode_diagnosis
        or {
            "utf8_decode_success": True,
            "cp932_decode_success": True,
            "latin1_fallback_used": False,
        }
    )
    # Backward-compatible aliases used by the earlier Phase10-D diagnostics.
    diagnosis["decoded_text_length"] = diagnosis["stripped_length"]
    diagnosis["starts_with_error_marker"] = stripped.startswith("#### ERR")
    diagnosis["empty"] = diagnosis["is_empty"]
    return diagnosis


def _bucket_printable_ratio(ratio: float, has_value: bool) -> str:
    if not has_value:
        return "empty"
    if ratio == 1.0:
        return "all_printable"
    if ratio >= 0.95:
        return "mostly_printable"
    if ratio >= 0.75:
        return "partially_printable"
    return "low_printable"


def _classify_url_validation_failure(value: str) -> str:
    stripped = value.strip()
    without_edge_null = stripped.strip("\x00").strip()
    if not without_edge_null:
        return "empty"
    if "\x00" in without_edge_null:
        return "null_byte_present"
    if any(ord(char) < 32 for char in without_edge_null):
        return "control_char_present"
    if without_edge_null.startswith("https://"):
        return "none"
    if without_edge_null.startswith("wss://") or without_edge_null.startswith("ws://"):
        return "websocket_url_not_valid_for_https_context"
    if stripped != without_edge_null and without_edge_null.startswith("https://"):
        return "edge_null_trim_required"
    if "https://" in without_edge_null:
        return "https_not_at_start"
    if without_edge_null.startswith("http://"):
        return "non_https_scheme"
    if "http://" in without_edge_null:
        return "http_not_at_start_or_non_https"
    return "no_url_candidate"


def _decrypt_with_openssl(encrypted_bytes: bytes, private_key_file: Path, *, key_format: str) -> tuple[str, dict[str, Any]]:
    key_format = key_format.lower()
    with tempfile.NamedTemporaryFile(prefix="tachibana-url-", suffix=".bin") as encrypted_file:
        encrypted_file.write(encrypted_bytes)
        encrypted_file.flush()
        cmd = [
            "openssl",
            "pkeyutl",
            "-decrypt",
            "-inkey",
            str(private_key_file),
            "-in",
            encrypted_file.name,
            "-pkeyopt",
            "rsa_padding_mode:oaep",
            "-pkeyopt",
            "rsa_oaep_md:sha256",
            "-pkeyopt",
            "rsa_mgf1_md:sha256",
        ]
        if key_format == "der":
            cmd.extend(["-keyform", "DER"])
        elif key_format != "pem":
            raise BrokerConfigurationError("TACHIBANA_API_PRIVATE_KEY_FORMAT must be der or pem.")
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, timeout=10)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            raise BrokerConfigurationError("Tachibana encrypted URL decrypt failed.") from exc
    return _decode_plaintext_bytes(result.stdout)
