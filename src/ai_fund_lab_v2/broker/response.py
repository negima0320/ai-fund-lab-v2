from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping


@dataclass(frozen=True)
class BrokerResponseEnvelope:
    raw: dict[str, Any]

    @property
    def clmid(self) -> str:
        return str(self.raw.get("sCLMID") or "")

    @property
    def result_code(self) -> str:
        return str(self.raw.get("sResultCode") or "")

    @property
    def result_text(self) -> str:
        return str(self.raw.get("sResultText") or "")

    @property
    def warning_code(self) -> str:
        return str(self.raw.get("sWarningCode") or "")

    @property
    def warning_text(self) -> str:
        return str(self.raw.get("sWarningText") or "")

    def is_success(self) -> bool:
        return self.result_code in ("", "0")

    def safe_dict(self) -> dict[str, Any]:
        return sanitize_mapping(self.raw)

    def __repr__(self) -> str:
        return f"BrokerResponseEnvelope({self.safe_dict()!r})"
