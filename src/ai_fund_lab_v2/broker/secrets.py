from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_fund_lab_v2.broker.settings import BrokerConfigurationError, BrokerSettings


DEFAULT_AUTH_ID_FILENAME = "e_api_authid.txt"
DEFAULT_PRIVATE_KEY_DER_FILENAME = "e_api_private_key.der"
DEFAULT_PRIVATE_KEY_PEM_FILENAME = "e_api_private_key.pem"


@dataclass(frozen=True)
class TachibanaSecrets:
    auth_id: str = ""
    auth_id_file: Path | None = None
    private_key_file: Path | None = None
    private_key_format: str = "der"

    def __repr__(self) -> str:
        return (
            "TachibanaSecrets("
            f"auth_id={'[SET]' if self.auth_id else '[MISSING]'}, "
            f"auth_id_file={'[SET]' if self.auth_id_file else '[MISSING]'}, "
            f"private_key_file={'[SET]' if self.private_key_file else '[MISSING]'}, "
            f"private_key_format='{self.private_key_format}'"
            ")"
        )


@dataclass(frozen=True)
class TachibanaSecondPasswordStatus:
    file_configured: bool
    file_exists: bool = False
    file_readable: bool = False
    nonempty: bool = False
    value_loaded: bool = False
    value_saved: bool = False
    failure_classification: str = ""

    @property
    def present(self) -> bool:
        return self.file_configured and self.file_exists and self.file_readable and self.nonempty

    def to_dict(self) -> dict[str, object]:
        return {
            "file_configured": self.file_configured,
            "file_exists": self.file_exists,
            "file_readable": self.file_readable,
            "nonempty": self.nonempty,
            "present": self.present,
            "value_loaded": self.value_loaded,
            "value_saved": self.value_saved,
            "failure_classification": self.failure_classification,
        }


class TachibanaSecretLoader:
    def __init__(self, settings: BrokerSettings) -> None:
        self.settings = settings

    def load(self) -> TachibanaSecrets:
        auth_id = self.settings.auth_id or self._read_auth_id_file(self._resolve_auth_id_file())
        private_key_file = self._resolve_private_key_file()
        private_key_format = self.settings.private_key_format
        self._require_regular_file(private_key_file, "TACHIBANA_API_PRIVATE_KEY_FILE")
        return TachibanaSecrets(
            auth_id=auth_id,
            auth_id_file=self._resolve_auth_id_file(),
            private_key_file=private_key_file,
            private_key_format=private_key_format,
        )

    def classify_second_password_file(self) -> TachibanaSecondPasswordStatus:
        path = self.settings.second_password_file
        if path is None:
            return TachibanaSecondPasswordStatus(file_configured=False, failure_classification="SECOND_PASSWORD_FILE_NOT_CONFIGURED")
        try:
            exists = path.is_file()
        except OSError:
            return TachibanaSecondPasswordStatus(file_configured=True, failure_classification="SECOND_PASSWORD_FILE_NOT_ACCESSIBLE")
        if not exists:
            return TachibanaSecondPasswordStatus(
                file_configured=True,
                file_exists=False,
                failure_classification="SECOND_PASSWORD_FILE_MISSING",
            )
        try:
            nonempty = bool(path.read_bytes().strip())
        except OSError:
            return TachibanaSecondPasswordStatus(
                file_configured=True,
                file_exists=True,
                file_readable=False,
                failure_classification="SECOND_PASSWORD_FILE_UNREADABLE",
            )
        return TachibanaSecondPasswordStatus(
            file_configured=True,
            file_exists=True,
            file_readable=True,
            nonempty=nonempty,
            failure_classification="" if nonempty else "SECOND_PASSWORD_FILE_EMPTY",
        )

    def load_second_password_value_for_demo_order_only(self) -> str:
        status = self.classify_second_password_file()
        if not status.present or self.settings.second_password_file is None:
            raise BrokerConfigurationError(status.failure_classification or "SECOND_PASSWORD_FILE_NOT_READY")
        try:
            value = self.settings.second_password_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise BrokerConfigurationError("TACHIBANA_API_SECOND_PASSWORD_FILE is not readable.") from exc
        if not value:
            raise BrokerConfigurationError("TACHIBANA_API_SECOND_PASSWORD_FILE is empty.")
        return value

    def _resolve_auth_id_file(self) -> Path | None:
        if self.settings.auth_id_file is not None:
            return self.settings.auth_id_file
        if self.settings.local_config_path is None:
            return None
        candidate = self.settings.local_config_path / DEFAULT_AUTH_ID_FILENAME
        return candidate if candidate.exists() else None

    def _resolve_private_key_file(self) -> Path:
        if self.settings.private_key_file is not None:
            return self.settings.private_key_file
        if self.settings.local_config_path is None:
            raise BrokerConfigurationError("TACHIBANA_API_PRIVATE_KEY_FILE or TACHIBANA_API_LOCAL_CONFIG_PATH is required.")
        filename = DEFAULT_PRIVATE_KEY_PEM_FILENAME if self.settings.private_key_format == "pem" else DEFAULT_PRIVATE_KEY_DER_FILENAME
        return self.settings.local_config_path / filename

    def _read_auth_id_file(self, path: Path | None) -> str:
        if path is None:
            raise BrokerConfigurationError("TACHIBANA_API_AUTH_ID or TACHIBANA_API_AUTH_ID_FILE is required.")
        self._require_regular_file(path, "TACHIBANA_API_AUTH_ID_FILE")
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise BrokerConfigurationError("TACHIBANA_API_AUTH_ID_FILE is not readable.") from exc
        if not value:
            raise BrokerConfigurationError("TACHIBANA_API_AUTH_ID_FILE is empty.")
        return value

    def _require_regular_file(self, path: Path, name: str) -> None:
        try:
            if not path.is_file():
                raise BrokerConfigurationError(f"{name} must point to an existing file.")
        except OSError as exc:
            raise BrokerConfigurationError(f"{name} is not accessible.") from exc
