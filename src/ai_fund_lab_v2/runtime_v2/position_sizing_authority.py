"""Runtime position-sizing authority resolution.

Runtime consumes Strategy Position Sizing notional candidates. It does not
derive BUY notional from fixed runtime position weights, equal-weight fallback,
or ``CapitalDeploymentPolicy.max_position_weight``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.strategy.position_sizing import validate_position_sizing_artifact
from ai_fund_lab_v2.runtime_v2.symbol_identity import same_symbol_identity


AUTHORITY_WINNER = "strategy_position_sizing"
MISSING_AUTHORITY_WINNER = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class PositionSizingAuthority:
    status: str
    reason: str
    symbol: str
    portfolio_policy_source: str
    portfolio_policy_authority_winner: str
    position_sizing_source: str
    position_sizing_authority_winner: str
    active_deployment_capital: float | None
    selected_dynamic_exposure_ratio: float | None
    selected_runtime_exposure_limit: float | None
    selected_dynamic_position_count: int | None
    current_position_market_value: float
    strategy_requested_position_weight: float | None
    selected_position_weight: float | None
    strategy_requested_position_amount: float | None
    selected_position_amount: float
    remaining_add_capacity: float
    lot_adjusted_quantity: float
    lot_adjusted_notional: float
    position_sizing_binding_constraint: str
    position_sizing_fallback_used: bool
    legacy_position_sizing_used: bool
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

    def with_lot_adjustment(self, *, quantity: float, notional: float) -> "PositionSizingAuthority":
        binding = self.position_sizing_binding_constraint
        if self.passed and notional <= 0:
            binding = "MINIMUM_LOT"
        return replace(
            self,
            lot_adjusted_quantity=max(float(quantity), 0.0),
            lot_adjusted_notional=max(float(notional), 0.0),
            position_sizing_binding_constraint=binding,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_sizing_authority_status": self.status,
            "position_sizing_authority_reason": self.reason,
            "portfolio_policy_source": self.portfolio_policy_source,
            "portfolio_policy_authority_winner": self.portfolio_policy_authority_winner,
            "position_sizing_source": self.position_sizing_source,
            "position_sizing_authority_winner": self.position_sizing_authority_winner,
            "active_deployment_capital": self.active_deployment_capital,
            "selected_dynamic_exposure_ratio": self.selected_dynamic_exposure_ratio,
            "selected_runtime_exposure_limit": self.selected_runtime_exposure_limit,
            "selected_dynamic_position_count": self.selected_dynamic_position_count,
            "current_position_market_value": self.current_position_market_value,
            "strategy_requested_position_weight": self.strategy_requested_position_weight,
            "selected_position_weight": self.selected_position_weight,
            "strategy_requested_position_amount": self.strategy_requested_position_amount,
            "selected_position_amount": self.selected_position_amount,
            "remaining_add_capacity": self.remaining_add_capacity,
            "lot_adjusted_quantity": self.lot_adjusted_quantity,
            "lot_adjusted_notional": self.lot_adjusted_notional,
            "position_sizing_binding_constraint": self.position_sizing_binding_constraint,
            "position_sizing_fallback_used": self.position_sizing_fallback_used,
            "legacy_position_sizing_used": self.legacy_position_sizing_used,
            "runtime_mode": self.runtime_mode,
            "business_date": self.business_date,
            "position_sizing_producer": self.producer,
            "position_sizing_consumer": self.consumer,
            "position_sizing_runtime_path": self.runtime_path,
            "position_sizing_authority_source": self.authority_source,
            "position_sizing_authority_hash": self.authority_hash,
        }


def resolve_position_sizing_authority(
    *,
    symbol: str,
    runtime_root: Path | str | None = None,
    business_date: str,
    runtime_mode: str,
    active_deployment_capital: float | None,
    selected_dynamic_exposure_ratio: float | None,
    selected_runtime_exposure_limit: float | None,
    selected_dynamic_position_count: int | None,
    current_position_market_value: float,
    policy_context: Mapping[str, Any] | None = None,
    artifact_path: Path | str | None = None,
    consumer: str = "runtime_v2_buy_admission",
) -> PositionSizingAuthority:
    payload, source = _load_authority_payload(
        runtime_root=Path(runtime_root) if runtime_root is not None else None,
        business_date=business_date,
        policy_context=policy_context,
        artifact_path=Path(artifact_path) if artifact_path is not None else None,
    )
    if payload is None:
        return _missing(
            reason="position_sizing_authority_missing",
            symbol=symbol,
            business_date=business_date,
            runtime_mode=runtime_mode,
            active_deployment_capital=active_deployment_capital,
            selected_dynamic_exposure_ratio=selected_dynamic_exposure_ratio,
            selected_runtime_exposure_limit=selected_runtime_exposure_limit,
            selected_dynamic_position_count=selected_dynamic_position_count,
            current_position_market_value=current_position_market_value,
            consumer=consumer,
        )
    if source != "policy_context":
        try:
            validate_position_sizing_artifact(dict(payload))
        except Exception as exc:  # noqa: BLE001 - closure evidence records the exact reason.
            return _missing(
                reason=f"position_sizing_authority_invalid:{exc}",
                symbol=symbol,
                business_date=business_date,
                runtime_mode=runtime_mode,
                active_deployment_capital=active_deployment_capital,
                selected_dynamic_exposure_ratio=selected_dynamic_exposure_ratio,
                selected_runtime_exposure_limit=selected_runtime_exposure_limit,
                selected_dynamic_position_count=selected_dynamic_position_count,
                current_position_market_value=current_position_market_value,
                consumer=consumer,
                source=source,
                authority_hash=_stable_hash(dict(payload)),
            )
    row = _position_row(payload, symbol)
    if row is None:
        return _missing(
            reason="position_sizing_symbol_authority_missing",
            symbol=symbol,
            business_date=business_date,
            runtime_mode=runtime_mode,
            active_deployment_capital=active_deployment_capital,
            selected_dynamic_exposure_ratio=selected_dynamic_exposure_ratio,
            selected_runtime_exposure_limit=selected_runtime_exposure_limit,
            selected_dynamic_position_count=selected_dynamic_position_count,
            current_position_market_value=current_position_market_value,
            consumer=consumer,
            source=source,
            authority_hash=_stable_hash(dict(payload)),
        )
    target_weight = _optional_float(row.get("target_weight"), row.get("selected_position_weight"))
    target_notional = _optional_float(row.get("target_notional"), row.get("selected_position_amount"))
    incremental_buy = _optional_float(row.get("incremental_buy_notional"), row.get("remaining_add_capacity"))
    maximum_weight = _optional_float(row.get("maximum_position_weight"), payload.get("effective_maximum_position_weight"))
    if target_weight is None or target_notional is None or incremental_buy is None:
        return _missing(
            reason="position_sizing_notional_unresolved",
            symbol=symbol,
            business_date=business_date,
            runtime_mode=runtime_mode,
            active_deployment_capital=active_deployment_capital,
            selected_dynamic_exposure_ratio=selected_dynamic_exposure_ratio,
            selected_runtime_exposure_limit=selected_runtime_exposure_limit,
            selected_dynamic_position_count=selected_dynamic_position_count,
            current_position_market_value=current_position_market_value,
            consumer=consumer,
            source=source,
            authority_hash=_stable_hash(dict(payload)),
        )
    selected_amount = max(float(incremental_buy), 0.0)
    binding = "PORTFOLIO_POLICY"
    reason = "position_sizing_authority_resolved"
    if selected_amount <= 0:
        binding = "NO_NEW_DEPLOYMENT"
        reason = "position_sizing_no_new_deployment"
    if maximum_weight is not None and target_weight > maximum_weight:
        binding = "SAFETY_CONCENTRATION_LIMIT"
        reason = "position_sizing_above_effective_maximum_position_weight"
    portfolio_policy_source = _portfolio_policy_source(payload, row)
    authority = PositionSizingAuthority(
        status="PASS",
        reason=reason,
        symbol=symbol,
        portfolio_policy_source=portfolio_policy_source,
        portfolio_policy_authority_winner="portfolio_policy_target_weight",
        position_sizing_source=source,
        position_sizing_authority_winner=AUTHORITY_WINNER,
        active_deployment_capital=active_deployment_capital,
        selected_dynamic_exposure_ratio=selected_dynamic_exposure_ratio,
        selected_runtime_exposure_limit=selected_runtime_exposure_limit,
        selected_dynamic_position_count=selected_dynamic_position_count,
        current_position_market_value=max(float(current_position_market_value), 0.0),
        strategy_requested_position_weight=target_weight,
        selected_position_weight=target_weight,
        strategy_requested_position_amount=target_notional,
        selected_position_amount=selected_amount,
        remaining_add_capacity=selected_amount,
        lot_adjusted_quantity=0.0,
        lot_adjusted_notional=0.0,
        position_sizing_binding_constraint=binding,
        position_sizing_fallback_used=False,
        legacy_position_sizing_used=False,
        runtime_mode=runtime_mode,
        business_date=business_date,
        producer="strategy.position_sizing",
        consumer=consumer,
        runtime_path="Production/Demo/Historical common runtime_v2",
        authority_source=source,
        authority_hash=_stable_hash(dict(payload)),
    )
    if binding == "SAFETY_CONCENTRATION_LIMIT":
        return replace(authority, status="REVIEW_REQUIRED")
    return authority


def position_sizing_authority_from_context(
    context: Mapping[str, Any] | None,
    *,
    symbol: str,
    business_date: str,
    runtime_mode: str,
    active_deployment_capital: float | None,
    selected_dynamic_exposure_ratio: float | None,
    selected_runtime_exposure_limit: float | None,
    selected_dynamic_position_count: int | None,
    current_position_market_value: float,
    consumer: str = "runtime_v2_buy_admission",
) -> PositionSizingAuthority:
    return resolve_position_sizing_authority(
        symbol=symbol,
        runtime_root=None,
        business_date=business_date,
        runtime_mode=runtime_mode,
        active_deployment_capital=active_deployment_capital,
        selected_dynamic_exposure_ratio=selected_dynamic_exposure_ratio,
        selected_runtime_exposure_limit=selected_runtime_exposure_limit,
        selected_dynamic_position_count=selected_dynamic_position_count,
        current_position_market_value=current_position_market_value,
        policy_context=context,
        consumer=consumer,
    )


def _missing(
    *,
    reason: str,
    symbol: str,
    business_date: str,
    runtime_mode: str,
    active_deployment_capital: float | None,
    selected_dynamic_exposure_ratio: float | None,
    selected_runtime_exposure_limit: float | None,
    selected_dynamic_position_count: int | None,
    current_position_market_value: float,
    consumer: str,
    source: str = "",
    authority_hash: str = "",
) -> PositionSizingAuthority:
    return PositionSizingAuthority(
        status="REVIEW_REQUIRED",
        reason=reason,
        symbol=symbol,
        portfolio_policy_source="",
        portfolio_policy_authority_winner=MISSING_AUTHORITY_WINNER,
        position_sizing_source=source,
        position_sizing_authority_winner=MISSING_AUTHORITY_WINNER,
        active_deployment_capital=active_deployment_capital,
        selected_dynamic_exposure_ratio=selected_dynamic_exposure_ratio,
        selected_runtime_exposure_limit=selected_runtime_exposure_limit,
        selected_dynamic_position_count=selected_dynamic_position_count,
        current_position_market_value=max(float(current_position_market_value), 0.0),
        strategy_requested_position_weight=None,
        selected_position_weight=None,
        strategy_requested_position_amount=None,
        selected_position_amount=0.0,
        remaining_add_capacity=0.0,
        lot_adjusted_quantity=0.0,
        lot_adjusted_notional=0.0,
        position_sizing_binding_constraint="REVIEW_REQUIRED",
        position_sizing_fallback_used=False,
        legacy_position_sizing_used=False,
        runtime_mode=runtime_mode,
        business_date=business_date,
        producer="strategy.position_sizing",
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
        nested = policy_context.get("position_sizing_authority")
        if isinstance(nested, Mapping):
            return nested, "policy_context"
        if isinstance(policy_context.get("positions"), list) or _optional_float(policy_context.get("selected_position_amount")) is not None:
            return policy_context, "policy_context"
    paths: list[Path] = []
    if artifact_path is not None:
        paths.append(artifact_path)
    if runtime_root is not None:
        paths.extend(
            [
                runtime_root / "strategy_artifacts" / "position_sizing" / business_date / "position_sizing.json",
                runtime_root / "strategy_artifacts" / business_date / "position_sizing.json",
                runtime_root / "strategy" / business_date / "position_sizing.json",
                runtime_root / "strategy" / "position_sizing.json",
            ]
        )
    for path in paths:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")), str(path)
    return None, ""


def _position_row(payload: Mapping[str, Any], symbol: str) -> Mapping[str, Any] | None:
    if _optional_float(payload.get("selected_position_amount")) is not None:
        return payload
    for row in payload.get("positions") or ():
        if not isinstance(row, Mapping):
            continue
        code = str(row.get("security_code") or row.get("symbol") or "").strip()
        if same_symbol_identity(code, symbol):
            return row
    return None


def _portfolio_policy_source(payload: Mapping[str, Any], row: Mapping[str, Any]) -> str:
    authority = row.get("target_weight_authority")
    if isinstance(authority, Mapping):
        ref = authority.get("portfolio_policy_reference")
        if isinstance(ref, Mapping):
            return str(ref.get("path") or ref.get("source_ref") or "")
        if isinstance(ref, str):
            return ref
    for item in payload.get("source_artifacts") or ():
        if isinstance(item, Mapping) and str(item.get("role") or "") == "portfolio_policy":
            return str(item.get("path") or item.get("source_ref") or "")
    return str(payload.get("portfolio_policy_source") or "")


def _optional_float(*values: Any) -> float | None:
    for value in values:
        if value in (None, "") or isinstance(value, bool):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _stable_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
