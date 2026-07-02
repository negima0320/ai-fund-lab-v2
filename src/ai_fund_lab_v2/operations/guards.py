from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL

FORBIDDEN_AI_FEATURE_SOURCES = {
    "broker_snapshot",
    "paper_ledger",
    "safety_result",
    "audit_result",
    "pnl",
    "cash",
    "portfolio",
    "portfolio_state",
    "selected",
    "bought",
    "affordable",
    "affordable_data",
}


@dataclass(frozen=True)
class MaxExposureDecision:
    status: str
    allowed: bool
    reason: str
    base_equity: Decimal
    max_allowed_exposure: Decimal
    current_exposure: Decimal
    projected_exposure: Decimal
    side: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allowed": self.allowed,
            "reason": self.reason,
            "base_equity": str(self.base_equity),
            "max_allowed_exposure": str(self.max_allowed_exposure),
            "current_exposure": str(self.current_exposure),
            "projected_exposure": str(self.projected_exposure),
            "side": self.side,
            "max_total_exposure_ratio": "0.85",
            "basis": "broker_actual_equity_or_buying_power",
            "paper_ledger_equity_allowed": False,
        }


def normalize_runtime_environment(env: str | None) -> str:
    normalized = (env or "").strip().lower()
    if normalized == "prod":
        return "production"
    return normalized


def validate_runtime_environment(
    env: str | None,
    *,
    base_url: str | None = None,
    production_order_allowed: bool = False,
) -> dict[str, Any]:
    normalized = normalize_runtime_environment(env)
    reasons: list[str] = []
    if normalized not in {"demo", "production"}:
        reasons.append("runtime_environment_unset_or_invalid")
    if production_order_allowed:
        reasons.append("production_order_allowed_true")
    if base_url and normalized == "demo" and base_url.rstrip("/") != DEMO_BASE_URL:
        reasons.append("demo_env_requires_demo_base_url")
    if base_url and normalized == "production" and base_url.rstrip("/") != PROD_BASE_URL:
        reasons.append("production_env_requires_production_base_url")
    return {
        "status": "PASS" if not reasons else "BLOCK",
        "allowed": not reasons,
        "environment": normalized,
        "base_url": base_url or "",
        "production_order_allowed": production_order_allowed,
        "reasons": reasons,
    }


def validate_demo_environment(env: str | None, *, base_url: str | None = None, production_order_allowed: bool = False) -> dict[str, Any]:
    result = validate_runtime_environment(env, base_url=base_url, production_order_allowed=production_order_allowed)
    if result["environment"] != "demo":
        result["reasons"].append("demo_submit_requires_demo_environment")
        result["allowed"] = False
        result["status"] = "BLOCK"
    if base_url and base_url.rstrip("/") == PROD_BASE_URL:
        result["reasons"].append("production_base_url_detected")
        result["allowed"] = False
        result["status"] = "BLOCK"
    return result


def evaluate_max_exposure(
    *,
    side: str,
    order_value: Decimal,
    current_exposure: Decimal,
    broker_actual_equity: Decimal | None = None,
    buying_power: Decimal | None = None,
    ratio: Decimal = Decimal("0.85"),
) -> MaxExposureDecision:
    normalized_side = side.upper()
    base_equity = _positive_or_none(broker_actual_equity) or _positive_or_none(buying_power)
    if base_equity is None:
        return MaxExposureDecision(
            status="BLOCK",
            allowed=False,
            reason="broker_actual_equity_and_buying_power_missing",
            base_equity=Decimal("0"),
            max_allowed_exposure=Decimal("0"),
            current_exposure=current_exposure,
            projected_exposure=current_exposure,
            side=normalized_side,
        )
    max_allowed = base_equity * ratio
    if normalized_side != "BUY":
        return MaxExposureDecision(
            status="ALLOW",
            allowed=True,
            reason="sell_or_exposure_reducing_order_not_blocked_by_max_exposure",
            base_equity=base_equity,
            max_allowed_exposure=max_allowed,
            current_exposure=current_exposure,
            projected_exposure=current_exposure,
            side=normalized_side,
        )
    projected = current_exposure + order_value
    if projected > max_allowed:
        return MaxExposureDecision(
            status="BLOCK",
            allowed=False,
            reason="MAX_EXPOSURE_EXCEEDED",
            base_equity=base_equity,
            max_allowed_exposure=max_allowed,
            current_exposure=current_exposure,
            projected_exposure=projected,
            side=normalized_side,
        )
    return MaxExposureDecision(
        status="ALLOW",
        allowed=True,
        reason="max_exposure_pass",
        base_equity=base_equity,
        max_allowed_exposure=max_allowed,
        current_exposure=current_exposure,
        projected_exposure=projected,
        side=normalized_side,
    )


def ai_feature_contamination_audit(feature_sources: list[str]) -> dict[str, Any]:
    normalized = {item.strip().lower() for item in feature_sources}
    forbidden = sorted(normalized & FORBIDDEN_AI_FEATURE_SOURCES)
    return {
        "status": "PASS" if not forbidden else "BLOCK",
        "forbidden_sources_detected": forbidden,
        "jquants_only": not forbidden,
        "ai_retraining_executed": False,
        "backtest_run": False,
    }


def artifact_leakage_audit(payload: Any) -> dict[str, Any]:
    text = str(payload).lower()
    forbidden_markers = [
        "raw_response_saved': true",
        '"raw_response_saved": true',
        "raw_payload_saved': true",
        '"raw_payload_saved": true',
        "production_order_submitted': true",
        '"production_order_submitted": true',
        "secondpassword",
        "second_password=",
        '"second_password":',
        "ssecondpassword",
        "private_key=",
        "auth_id=",
    ]
    hits = [marker for marker in forbidden_markers if marker in text]
    return {"status": "PASS" if not hits else "BLOCK", "hits": hits}


def _positive_or_none(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value if value > 0 else None
