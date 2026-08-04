"""Runtime cash/exposure authority resolution.

Runtime consumes already-materialized Strategy / Portfolio Policy cash and
gross-exposure targets. It deliberately does not fall back to legacy
``target_investment_ratio``, ``cash_buffer``, or fixed ``max_exposure`` values.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.strategy.dynamic_cash_exposure import validate_dynamic_cash_exposure_artifact


AUTHORITY_WINNER = "strategy_dynamic_cash_exposure"
MISSING_AUTHORITY_WINNER = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class CashExposureAuthority:
    status: str
    reason: str
    strategy_requested_cash_ratio: float | None
    selected_dynamic_cash_ratio: float | None
    strategy_requested_exposure_ratio: float | None
    selected_dynamic_exposure_ratio: float | None
    current_total_equity: float | None
    active_deployment_capital: float | None
    current_cash: float | None
    current_market_value: float
    target_exposure_amount: float
    selected_runtime_exposure_limit: float
    safety_exposure_limit: float | None
    target_cash_amount: float
    available_cash_after_target: float
    remaining_exposure_capacity: float
    planning_budget: float
    cash_exposure_authority_winner: str
    cash_exposure_binding_constraint: str
    legacy_cash_config_used: bool
    legacy_exposure_config_used: bool
    cash_exposure_fallback_used: bool
    runtime_mode: str
    business_date: str
    producer: str
    consumer: str
    runtime_path: str
    authority_source: str
    authority_hash: str

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    def with_runtime_state(
        self,
        *,
        current_cash: float | None,
        current_market_value: float,
        current_total_equity: float | None,
        active_deployment_capital: float | None,
    ) -> "CashExposureAuthority":
        return _with_runtime_state(
            self,
            current_cash=current_cash,
            current_market_value=current_market_value,
            current_total_equity=current_total_equity,
            active_deployment_capital=active_deployment_capital,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cash_exposure_authority_status": self.status,
            "cash_exposure_authority_reason": self.reason,
            "strategy_requested_cash_ratio": self.strategy_requested_cash_ratio,
            "selected_dynamic_cash_ratio": self.selected_dynamic_cash_ratio,
            "strategy_requested_exposure_ratio": self.strategy_requested_exposure_ratio,
            "selected_dynamic_exposure_ratio": self.selected_dynamic_exposure_ratio,
            "current_total_equity": self.current_total_equity,
            "active_deployment_capital": self.active_deployment_capital,
            "current_cash": self.current_cash,
            "current_market_value": self.current_market_value,
            "target_exposure_amount": self.target_exposure_amount,
            "selected_runtime_exposure_limit": self.selected_runtime_exposure_limit,
            "safety_exposure_limit": self.safety_exposure_limit,
            "target_cash_amount": self.target_cash_amount,
            "available_cash_after_target": self.available_cash_after_target,
            "remaining_exposure_capacity": self.remaining_exposure_capacity,
            "planning_budget": self.planning_budget,
            "cash_exposure_authority_winner": self.cash_exposure_authority_winner,
            "cash_exposure_binding_constraint": self.cash_exposure_binding_constraint,
            "legacy_cash_config_used": self.legacy_cash_config_used,
            "legacy_exposure_config_used": self.legacy_exposure_config_used,
            "cash_exposure_fallback_used": self.cash_exposure_fallback_used,
            "runtime_mode": self.runtime_mode,
            "business_date": self.business_date,
            "cash_exposure_producer": self.producer,
            "cash_exposure_consumer": self.consumer,
            "cash_exposure_runtime_path": self.runtime_path,
            "cash_exposure_authority_source": self.authority_source,
            "cash_exposure_authority_hash": self.authority_hash,
        }


def resolve_cash_exposure_authority(
    *,
    runtime_root: Path | str | None = None,
    business_date: str,
    runtime_mode: str,
    current_total_equity: float | None,
    active_deployment_capital: float | None,
    current_cash: float | None,
    current_market_value: float,
    policy_context: Mapping[str, Any] | None = None,
    artifact_path: Path | str | None = None,
    consumer: str = "runtime_v2_buy_admission",
) -> CashExposureAuthority:
    payload, source = _load_authority_payload(
        runtime_root=Path(runtime_root) if runtime_root is not None else None,
        business_date=business_date,
        policy_context=policy_context,
        artifact_path=Path(artifact_path) if artifact_path is not None else None,
    )
    if payload is None:
        return _missing_authority(
            reason="dynamic_cash_exposure_authority_missing",
            business_date=business_date,
            runtime_mode=runtime_mode,
            current_total_equity=current_total_equity,
            active_deployment_capital=active_deployment_capital,
            current_cash=current_cash,
            current_market_value=current_market_value,
            consumer=consumer,
        )
    if source != "policy_context":
        try:
            validate_dynamic_cash_exposure_artifact(dict(payload))
        except Exception as exc:  # noqa: BLE001 - evidence keeps the validation reason.
            return _missing_authority(
                reason=f"dynamic_cash_exposure_authority_invalid:{exc}",
                business_date=business_date,
                runtime_mode=runtime_mode,
                current_total_equity=current_total_equity,
                active_deployment_capital=active_deployment_capital,
                current_cash=current_cash,
                current_market_value=current_market_value,
                consumer=consumer,
                source=source,
                authority_hash=_stable_hash(dict(payload)),
            )
    requested_cash = _optional_ratio(
        payload.get("selected_dynamic_cash_ratio"),
        payload.get("target_cash_ratio"),
        payload.get("baseline_cash_ratio"),
    )
    requested_exposure = _optional_ratio(
        payload.get("selected_dynamic_exposure_ratio"),
        payload.get("target_gross_exposure_ratio"),
        payload.get("baseline_gross_exposure_ratio"),
    )
    if requested_cash is None or requested_exposure is None:
        return _missing_authority(
            reason="dynamic_cash_exposure_ratio_unresolved",
            business_date=business_date,
            runtime_mode=runtime_mode,
            current_total_equity=current_total_equity,
            active_deployment_capital=active_deployment_capital,
            current_cash=current_cash,
            current_market_value=current_market_value,
            consumer=consumer,
            source=source,
            authority_hash=_stable_hash(dict(payload)),
        )
    safety_limit = _optional_ratio(
        payload.get("exposure_safety_maximum"),
        payload.get("maximum_gross_exposure_ratio"),
        payload.get("safety_exposure_limit"),
    )
    selected_exposure = requested_exposure
    binding = "STRATEGY_POLICY"
    if safety_limit is not None and selected_exposure > safety_limit:
        selected_exposure = safety_limit
        binding = "SAFETY_HARD_LIMIT"
    authority = CashExposureAuthority(
        status="PASS",
        reason="dynamic_cash_exposure_authority_resolved",
        strategy_requested_cash_ratio=requested_cash,
        selected_dynamic_cash_ratio=requested_cash,
        strategy_requested_exposure_ratio=requested_exposure,
        selected_dynamic_exposure_ratio=selected_exposure,
        current_total_equity=current_total_equity,
        active_deployment_capital=active_deployment_capital,
        current_cash=current_cash,
        current_market_value=max(float(current_market_value), 0.0),
        target_exposure_amount=0.0,
        selected_runtime_exposure_limit=0.0,
        safety_exposure_limit=safety_limit,
        target_cash_amount=0.0,
        available_cash_after_target=0.0,
        remaining_exposure_capacity=0.0,
        planning_budget=0.0,
        cash_exposure_authority_winner=AUTHORITY_WINNER,
        cash_exposure_binding_constraint=binding,
        legacy_cash_config_used=False,
        legacy_exposure_config_used=False,
        cash_exposure_fallback_used=False,
        runtime_mode=runtime_mode,
        business_date=business_date,
        producer="strategy.dynamic_cash_exposure",
        consumer=consumer,
        runtime_path="Production/Demo/Historical common runtime_v2",
        authority_source=source,
        authority_hash=_stable_hash(dict(payload)),
    )
    return _with_runtime_state(
        authority,
        current_cash=current_cash,
        current_market_value=current_market_value,
        current_total_equity=current_total_equity,
        active_deployment_capital=active_deployment_capital,
    )


def cash_exposure_authority_from_context(
    context: Mapping[str, Any] | None,
    *,
    business_date: str,
    runtime_mode: str,
    current_total_equity: float | None,
    active_deployment_capital: float | None,
    current_cash: float | None,
    current_market_value: float,
    consumer: str = "runtime_v2_buy_admission",
) -> CashExposureAuthority:
    return resolve_cash_exposure_authority(
        runtime_root=None,
        business_date=business_date,
        runtime_mode=runtime_mode,
        current_total_equity=current_total_equity,
        active_deployment_capital=active_deployment_capital,
        current_cash=current_cash,
        current_market_value=current_market_value,
        policy_context=context,
        consumer=consumer,
    )


def _with_runtime_state(
    authority: CashExposureAuthority,
    *,
    current_cash: float | None,
    current_market_value: float,
    current_total_equity: float | None,
    active_deployment_capital: float | None,
) -> CashExposureAuthority:
    market_value = max(float(current_market_value), 0.0)
    capital = None if active_deployment_capital is None else float(active_deployment_capital)
    if not authority.passed or capital is None:
        return replace(
            authority,
            current_total_equity=current_total_equity,
            active_deployment_capital=capital,
            current_cash=current_cash,
            current_market_value=market_value,
            target_exposure_amount=0.0,
            selected_runtime_exposure_limit=0.0,
            target_cash_amount=0.0,
            available_cash_after_target=0.0,
            remaining_exposure_capacity=0.0,
            planning_budget=0.0,
            cash_exposure_binding_constraint="REVIEW_REQUIRED",
        )
    target_exposure_amount = capital * float(authority.selected_dynamic_exposure_ratio or 0.0)
    target_cash_amount = capital * float(authority.selected_dynamic_cash_ratio or 0.0)
    cash_capacity = 0.0 if current_cash is None else max(float(current_cash) - target_cash_amount, 0.0)
    exposure_capacity = max(target_exposure_amount - market_value, 0.0)
    planning_budget = min(cash_capacity, exposure_capacity)
    binding = authority.cash_exposure_binding_constraint
    reason = authority.reason
    if current_cash is None:
        binding = "CURRENT_CASH"
        reason = "dynamic_cash_exposure_current_cash_missing"
        planning_budget = 0.0
    elif cash_capacity <= 0:
        binding = "CURRENT_CASH"
        reason = "dynamic_cash_exposure_current_cash_at_or_below_target"
    elif exposure_capacity <= 0:
        binding = "CURRENT_EXPOSURE"
        reason = "dynamic_cash_exposure_current_exposure_at_or_above_target"
    elif cash_capacity < exposure_capacity:
        binding = "CURRENT_CASH"
    elif exposure_capacity < cash_capacity and binding == "STRATEGY_POLICY":
        binding = "STRATEGY_POLICY"
    return replace(
        authority,
        reason=reason,
        current_total_equity=current_total_equity,
        active_deployment_capital=capital,
        current_cash=current_cash,
        current_market_value=market_value,
        target_exposure_amount=target_exposure_amount,
        selected_runtime_exposure_limit=target_exposure_amount,
        target_cash_amount=target_cash_amount,
        available_cash_after_target=cash_capacity,
        remaining_exposure_capacity=exposure_capacity,
        planning_budget=planning_budget,
        cash_exposure_binding_constraint=binding,
    )


def _missing_authority(
    *,
    reason: str,
    business_date: str,
    runtime_mode: str,
    current_total_equity: float | None,
    active_deployment_capital: float | None,
    current_cash: float | None,
    current_market_value: float,
    consumer: str,
    source: str = "",
    authority_hash: str = "",
) -> CashExposureAuthority:
    return CashExposureAuthority(
        status="REVIEW_REQUIRED",
        reason=reason,
        strategy_requested_cash_ratio=None,
        selected_dynamic_cash_ratio=None,
        strategy_requested_exposure_ratio=None,
        selected_dynamic_exposure_ratio=None,
        current_total_equity=current_total_equity,
        active_deployment_capital=active_deployment_capital,
        current_cash=current_cash,
        current_market_value=max(float(current_market_value), 0.0),
        target_exposure_amount=0.0,
        selected_runtime_exposure_limit=0.0,
        safety_exposure_limit=None,
        target_cash_amount=0.0,
        available_cash_after_target=0.0,
        remaining_exposure_capacity=0.0,
        planning_budget=0.0,
        cash_exposure_authority_winner=MISSING_AUTHORITY_WINNER,
        cash_exposure_binding_constraint="REVIEW_REQUIRED",
        legacy_cash_config_used=False,
        legacy_exposure_config_used=False,
        cash_exposure_fallback_used=False,
        runtime_mode=runtime_mode,
        business_date=business_date,
        producer="strategy.dynamic_cash_exposure",
        consumer=consumer,
        runtime_path="Production/Demo/Historical common runtime_v2",
        authority_source=source,
        authority_hash=authority_hash,
    )


def _load_authority_payload(
    *,
    runtime_root: Path | None,
    business_date: str,
    policy_context: Mapping[str, Any] | None,
    artifact_path: Path | None,
) -> tuple[Mapping[str, Any] | None, str]:
    if policy_context:
        nested = policy_context.get("cash_exposure_authority")
        if isinstance(nested, Mapping):
            return nested, "policy_context"
        if _optional_ratio(
            policy_context.get("selected_dynamic_cash_ratio"),
            policy_context.get("target_cash_ratio"),
        ) is not None and _optional_ratio(
            policy_context.get("selected_dynamic_exposure_ratio"),
            policy_context.get("target_gross_exposure_ratio"),
        ) is not None:
            return policy_context, "policy_context"
    paths: list[Path] = []
    if artifact_path is not None:
        paths.append(artifact_path)
    if runtime_root is not None:
        paths.extend(
            [
                runtime_root / "strategy_artifacts" / "dynamic_cash_exposure" / business_date / "dynamic_cash_exposure.json",
                runtime_root / "strategy_artifacts" / business_date / "dynamic_cash_exposure.json",
                runtime_root / "strategy" / business_date / "dynamic_cash_exposure.json",
                runtime_root / "strategy" / "dynamic_cash_exposure.json",
            ]
        )
    for path in paths:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")), str(path)
    return None, ""


def _optional_ratio(*values: Any) -> float | None:
    for value in values:
        if value in (None, "") or isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if 0.0 <= number <= 1.0:
            return number
    return None


def _stable_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
