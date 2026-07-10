"""Capital Deployment Policy contract for Runtime v2.

Runtime reads this policy as an external contract. It does not provide hidden
defaults for capital allocation, position count, or order notional limits.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "policy_version",
    "policy_source",
    "evaluation_capital",
    "target_investment_ratio",
    "cash_buffer",
    "max_exposure",
    "max_position_weight",
    "max_positions",
    "min_order_amount",
    "max_buy_order_amount",
    "max_sell_liquidation_amount",
    "buy_notional_policy",
    "sell_liquidation_policy",
    "manual_review_threshold",
)

POLICY_HASH_FIELDS = (
    "policy_version",
    "policy_source",
    "evaluation_capital",
    "target_investment_ratio",
    "cash_buffer",
    "max_exposure",
    "max_position_weight",
    "max_positions",
    "min_order_amount",
    "max_buy_order_amount",
    "max_sell_liquidation_amount",
    "buy_notional_policy",
    "sell_liquidation_policy",
    "manual_review_threshold",
)


class CapitalDeploymentPolicyError(ValueError):
    """Raised when the explicit Capital Deployment Policy cannot be used."""


@dataclass(frozen=True)
class ManualReviewThreshold:
    buy_amount: float | None
    sell_liquidation_amount: float | None


@dataclass(frozen=True)
class CapitalDeploymentPolicy:
    policy_version: str
    policy_source: str
    evaluation_capital: float
    target_investment_ratio: float
    cash_buffer: float
    max_exposure: float
    max_position_weight: float
    max_positions: int
    min_order_amount: float
    max_buy_order_amount: float | None
    max_sell_liquidation_amount: float | None
    buy_notional_policy: str
    sell_liquidation_policy: str
    manual_review_threshold: ManualReviewThreshold
    loaded_from: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["manual_review_threshold"] = asdict(self.manual_review_threshold)
        return payload

    def to_manifest_fields(self) -> dict[str, Any]:
        return {
            "capital_deployment_policy_loaded": True,
            "capital_deployment_policy_source": self.policy_source,
            "capital_deployment_policy_path": self.loaded_from,
            "capital_deployment_policy_version": self.policy_version,
            "evaluation_capital": self.evaluation_capital,
            "target_investment_ratio": self.target_investment_ratio,
            "cash_buffer": self.cash_buffer,
            "max_exposure": self.max_exposure,
            "max_position_weight": self.max_position_weight,
            "active_max_positions": self.max_positions,
            "max_positions_source": self.policy_source,
            "max_positions_policy_version": self.policy_version,
            "max_buy_order_amount": self.max_buy_order_amount,
            "max_sell_liquidation_amount": self.max_sell_liquidation_amount,
            "buy_notional_policy": self.buy_notional_policy,
            "sell_liquidation_policy": self.sell_liquidation_policy,
            "policy_validation_status": "PASS",
            "policy_missing": False,
        }


def capital_deployment_policy_hash_payload(policy: CapitalDeploymentPolicy) -> dict[str, Any]:
    return {
        "policy_version": policy.policy_version,
        "policy_source": policy.policy_source,
        "evaluation_capital": policy.evaluation_capital,
        "target_investment_ratio": policy.target_investment_ratio,
        "cash_buffer": policy.cash_buffer,
        "max_exposure": policy.max_exposure,
        "max_position_weight": policy.max_position_weight,
        "max_positions": policy.max_positions,
        "min_order_amount": policy.min_order_amount,
        "max_buy_order_amount": policy.max_buy_order_amount,
        "max_sell_liquidation_amount": policy.max_sell_liquidation_amount,
        "buy_notional_policy": policy.buy_notional_policy,
        "sell_liquidation_policy": policy.sell_liquidation_policy,
        "manual_review_threshold": asdict(policy.manual_review_threshold),
    }


def capital_deployment_policy_hash(policy: CapitalDeploymentPolicy) -> str:
    return _stable_policy_hash(capital_deployment_policy_hash_payload(policy))


def capital_deployment_policy_hash_from_context(policy_context: dict[str, Any]) -> str:
    return _stable_policy_hash(
        {field: policy_context.get(field) for field in POLICY_HASH_FIELDS}
    )


def _stable_policy_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_capital_deployment_policy(path: Path | str) -> CapitalDeploymentPolicy:
    """Load and validate an explicit Capital Deployment Policy JSON file."""

    policy_path = Path(path)
    if not policy_path.exists():
        raise CapitalDeploymentPolicyError(f"capital deployment policy missing: {policy_path}")
    if not policy_path.is_file():
        raise CapitalDeploymentPolicyError(f"capital deployment policy is not a file: {policy_path}")
    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CapitalDeploymentPolicyError(f"capital deployment policy invalid json: {exc}") from exc
    if not isinstance(payload, dict):
        raise CapitalDeploymentPolicyError("capital deployment policy must be a JSON object")

    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise CapitalDeploymentPolicyError("capital deployment policy missing required fields: " + ",".join(missing))

    threshold_payload = payload["manual_review_threshold"]
    if not isinstance(threshold_payload, dict):
        raise CapitalDeploymentPolicyError("manual_review_threshold must be a JSON object")
    threshold_missing = [field for field in ("buy_amount", "sell_liquidation_amount") if field not in threshold_payload]
    if threshold_missing:
        raise CapitalDeploymentPolicyError(
            "manual_review_threshold missing required fields: " + ",".join(threshold_missing)
        )

    policy = CapitalDeploymentPolicy(
        policy_version=_required_text(payload, "policy_version"),
        policy_source=_required_text(payload, "policy_source"),
        evaluation_capital=_required_non_negative_number(payload, "evaluation_capital", positive=True),
        target_investment_ratio=_required_ratio(payload, "target_investment_ratio"),
        cash_buffer=_required_ratio(payload, "cash_buffer"),
        max_exposure=_required_non_negative_number(payload, "max_exposure"),
        max_position_weight=_required_ratio(payload, "max_position_weight"),
        max_positions=_required_positive_int(payload, "max_positions"),
        min_order_amount=_required_non_negative_number(payload, "min_order_amount"),
        max_buy_order_amount=_optional_non_negative_number(payload, "max_buy_order_amount"),
        max_sell_liquidation_amount=_optional_non_negative_number(payload, "max_sell_liquidation_amount"),
        buy_notional_policy=_required_text(payload, "buy_notional_policy"),
        sell_liquidation_policy=_required_text(payload, "sell_liquidation_policy"),
        manual_review_threshold=ManualReviewThreshold(
            buy_amount=_optional_non_negative_number(threshold_payload, "buy_amount"),
            sell_liquidation_amount=_optional_non_negative_number(threshold_payload, "sell_liquidation_amount"),
        ),
        loaded_from=str(policy_path),
    )
    if policy.cash_buffer + policy.target_investment_ratio > 1.0:
        raise CapitalDeploymentPolicyError("target_investment_ratio + cash_buffer must be <= 1.0")
    if policy.max_exposure > policy.evaluation_capital:
        raise CapitalDeploymentPolicyError("max_exposure must be <= evaluation_capital")
    return policy


def missing_policy_manifest_fields(path: Path | str | None, *, reason: str) -> dict[str, Any]:
    return {
        "capital_deployment_policy_loaded": False,
        "capital_deployment_policy_source": "",
        "capital_deployment_policy_path": str(path or ""),
        "capital_deployment_policy_version": "",
        "evaluation_capital": None,
        "target_investment_ratio": None,
        "cash_buffer": None,
        "max_exposure": None,
        "max_position_weight": None,
        "active_max_positions": None,
        "max_positions_source": "",
        "max_positions_policy_version": "",
        "max_buy_order_amount": None,
        "max_sell_liquidation_amount": None,
        "buy_notional_policy": "",
        "sell_liquidation_policy": "",
        "policy_validation_status": reason,
        "policy_missing": True,
    }


def invalid_policy_manifest_fields(path: Path | str | None, *, reason: str) -> dict[str, Any]:
    payload = missing_policy_manifest_fields(path, reason=reason)
    payload["policy_missing"] = False
    return payload


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str) or not value.strip():
        raise CapitalDeploymentPolicyError(f"{field} must be a non-empty string")
    return value.strip()


def _required_ratio(payload: dict[str, Any], field: str) -> float:
    value = _required_non_negative_number(payload, field)
    if value > 1.0:
        raise CapitalDeploymentPolicyError(f"{field} must be <= 1.0")
    return value


def _required_non_negative_number(payload: dict[str, Any], field: str, *, positive: bool = False) -> float:
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CapitalDeploymentPolicyError(f"{field} must be a number")
    number = float(value)
    if positive and number <= 0:
        raise CapitalDeploymentPolicyError(f"{field} must be > 0")
    if not positive and number < 0:
        raise CapitalDeploymentPolicyError(f"{field} must be >= 0")
    return number


def _optional_non_negative_number(payload: dict[str, Any], field: str) -> float | None:
    value = payload[field]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CapitalDeploymentPolicyError(f"{field} must be a number or null")
    number = float(value)
    if number < 0:
        raise CapitalDeploymentPolicyError(f"{field} must be >= 0")
    return number


def _required_positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise CapitalDeploymentPolicyError(f"{field} must be an integer")
    if value <= 0:
        raise CapitalDeploymentPolicyError(f"{field} must be > 0")
    return value
