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
ONE_LOT_SOFT_CAP_REASON = "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP"
LEGACY_ONE_LOT_SOFT_CAP_REASON = "LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP"
MINIMUM_EXECUTABLE_ONE_LOT_REASON = "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED"
MINIMUM_EXECUTABLE_ONE_LOT_AUTHORITY_TYPE = "PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION"
TARGET_WEIGHT_ABSOLUTE_TOLERANCE = 0.000001


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
    one_lot_authority_consumed: bool = False
    one_lot_authority_reason: str = ""
    discrete_authorized_quantity: float = 0.0
    discrete_authorized_notional: float = 0.0
    phase29_l19_lot_resolution: dict[str, Any] | None = None

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
            "one_lot_authority_consumed": self.one_lot_authority_consumed,
            "one_lot_authority_reason": self.one_lot_authority_reason,
            "discrete_authorized_quantity": self.discrete_authorized_quantity,
            "discrete_authorized_notional": self.discrete_authorized_notional,
            "phase29_l19_lot_resolution": dict(self.phase29_l19_lot_resolution or {}),
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
    lot_resolution = _lot_resolution(row)
    maximum_weight = _optional_float(
        row.get("maximum_position_weight"),
        payload.get("effective_maximum_position_weight"),
        lot_resolution.get("strategy_cap_weight") if lot_resolution else None,
        lot_resolution.get("strategy_target_cap") if lot_resolution else None,
    )
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
    minimum_one_lot_authority = _minimum_executable_one_lot_authority(row, target_weight=target_weight)
    one_lot_authority = (
        minimum_one_lot_authority
        if minimum_one_lot_authority["status"] == "PASS"
        else _one_lot_strategy_soft_cap_authority(row, target_weight=target_weight, maximum_weight=maximum_weight)
    )
    if selected_amount <= 0:
        binding = "NO_NEW_DEPLOYMENT"
        reason = "position_sizing_no_new_deployment"
    if one_lot_authority["status"] == "PASS" and one_lot_authority.get("authority_type") == MINIMUM_EXECUTABLE_ONE_LOT_AUTHORITY_TYPE:
        binding = "MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION"
        reason = "minimum_executable_one_lot_authority_consumed"
        selected_amount = max(selected_amount, float(one_lot_authority["authorized_notional"]))
    if maximum_weight is not None and target_weight > maximum_weight:
        if one_lot_authority["status"] == "PASS":
            if one_lot_authority.get("authority_type") == MINIMUM_EXECUTABLE_ONE_LOT_AUTHORITY_TYPE:
                binding = "MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION"
                reason = "minimum_executable_one_lot_authority_consumed"
            else:
                binding = "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP"
                reason = "one_lot_strategy_soft_cap_overshoot_authority_consumed"
            selected_amount = max(selected_amount, float(one_lot_authority["authorized_notional"]))
        else:
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
        one_lot_authority_consumed=one_lot_authority["status"] == "PASS",
        one_lot_authority_reason=str(one_lot_authority.get("reason") or ""),
        discrete_authorized_quantity=float(one_lot_authority.get("authorized_quantity") or 0.0),
        discrete_authorized_notional=float(one_lot_authority.get("authorized_notional") or 0.0),
        phase29_l19_lot_resolution=dict(one_lot_authority.get("lot_resolution") or lot_resolution or {}),
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


def _one_lot_strategy_soft_cap_authority(
    row: Mapping[str, Any],
    *,
    target_weight: float,
    maximum_weight: float | None,
) -> dict[str, Any]:
    empty = {
        "status": "NOT_APPLICABLE",
        "reason": "",
        "authorized_quantity": 0.0,
        "authorized_notional": 0.0,
        "lot_resolution": {},
    }
    if maximum_weight is None or target_weight <= maximum_weight + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    lot_resolution = _lot_resolution(row)
    if not lot_resolution:
        return empty
    semantic = str(
        row.get("semantic_buy_type")
        or row.get("planning_intent")
        or lot_resolution.get("semantic_type")
        or ""
    ).upper()
    if semantic not in {"BUY_NEW", "BUY_ADD", "REENTRY"}:
        return empty
    if _explicit_hard_blocker_present(row, semantic=semantic):
        return empty
    if str(lot_resolution.get("boundary_classification") or "") != "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX":
        return empty
    if lot_resolution.get("strategy_cap_overshoot_applied") is not True:
        return empty
    if lot_resolution.get("one_lot_fallback_applied") is not True:
        return empty
    if str(lot_resolution.get("one_lot_feasibility_status") or "") != "PASS":
        return empty
    reason = str(
        row.get("strategy_cap_overshoot_reason")
        or row.get("one_lot_authority_reason")
        or lot_resolution.get("lot_overshoot_reason")
        or ""
    )
    if reason not in {ONE_LOT_SOFT_CAP_REASON, LEGACY_ONE_LOT_SOFT_CAP_REASON}:
        return empty
    one_lot_quantity = _optional_float(lot_resolution.get("one_lot_quantity"))
    if one_lot_quantity is None or one_lot_quantity <= 0:
        return empty
    requested_quantity = _optional_float(
        row.get("discrete_authorized_quantity"),
        row.get("final_quantity_delta"),
        row.get("final_allocated_quantity"),
        row.get("executable_quantity_delta"),
        row.get("quantity_delta_candidate"),
        row.get("transaction_quantity_candidate"),
        row.get("target_quantity_candidate"),
        row.get("lot_adjusted_quantity"),
        row.get("planned_quantity"),
        row.get("selected_quantity"),
        lot_resolution.get("final_allocated_quantity"),
        lot_resolution.get("executable_quantity_delta"),
    )
    if requested_quantity is None or requested_quantity <= 0:
        return empty
    if abs(requested_quantity - one_lot_quantity) > TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    safety_cap = _optional_float(lot_resolution.get("safety_hard_cap"), lot_resolution.get("safety_hard_cap_weight"))
    post_trade_weight = _optional_float(lot_resolution.get("post_trade_weight"), lot_resolution.get("one_lot_weight"), target_weight)
    if safety_cap is None or post_trade_weight is None or post_trade_weight > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    if lot_resolution.get("safety_hard_cap_preserved") is False:
        return empty
    safety_margin = _optional_float(lot_resolution.get("safety_margin_after_trade"))
    if safety_margin is not None and safety_margin < -TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    authorized_notional = _optional_float(
        row.get("discrete_authorized_notional"),
        lot_resolution.get("one_lot_notional"),
        row.get("lot_adjusted_notional"),
    )
    if authorized_notional is None or authorized_notional <= 0:
        return empty
    return {
        "status": "PASS",
        "reason": reason,
        "authority_type": "PORTFOLIO_CONSTRUCTION_ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT",
        "authorized_quantity": float(one_lot_quantity),
        "authorized_notional": float(authorized_notional),
        "lot_resolution": dict(lot_resolution),
    }


def _minimum_executable_one_lot_authority(
    row: Mapping[str, Any],
    *,
    target_weight: float,
) -> dict[str, Any]:
    empty = {
        "status": "NOT_APPLICABLE",
        "reason": "",
        "authority_type": "",
        "authorized_quantity": 0.0,
        "authorized_notional": 0.0,
        "lot_resolution": {},
    }
    lot_resolution = _lot_resolution(row)
    if not lot_resolution:
        return empty
    authority = lot_resolution.get("minimum_executable_one_lot_authority")
    if not isinstance(authority, Mapping):
        authority = row.get("minimum_executable_one_lot_authority")
    if not isinstance(authority, Mapping):
        return empty
    if str(authority.get("authority_type") or "") != MINIMUM_EXECUTABLE_ONE_LOT_AUTHORITY_TYPE:
        return empty
    if str(authority.get("decision") or "") not in {"ADMIT", "ADMIT_ONE_LOT"}:
        return empty
    if str(authority.get("reason") or authority.get("admission_reason") or "") != MINIMUM_EXECUTABLE_ONE_LOT_REASON:
        return empty
    if str(lot_resolution.get("minimum_executable_one_lot_reason") or "") != MINIMUM_EXECUTABLE_ONE_LOT_REASON:
        return empty
    if lot_resolution.get("minimum_executable_one_lot_admitted") is not True:
        return empty
    semantic = str(row.get("semantic_buy_type") or lot_resolution.get("semantic_type") or authority.get("intent") or "").upper()
    if semantic not in {"BUY_NEW", "REENTRY"}:
        return empty
    if str(authority.get("intent") or semantic).upper() != semantic:
        return empty
    current_quantity = _optional_float(row.get("current_quantity"), authority.get("current_quantity"))
    if current_quantity is not None and current_quantity > TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    if _explicit_hard_blocker_present(row, semantic=semantic):
        return empty
    if str(lot_resolution.get("one_lot_feasibility_status") or "") != "PASS":
        return empty
    if lot_resolution.get("one_lot_fallback_applied") is not True:
        return empty
    if lot_resolution.get("safety_hard_cap_preserved") is not True:
        return empty
    if lot_resolution.get("strategy_cap_preserved") is not True:
        return empty
    one_lot_quantity = _optional_float(lot_resolution.get("one_lot_quantity"))
    final_quantity = _optional_float(
        row.get("discrete_authorized_quantity"),
        row.get("final_quantity_delta"),
        row.get("final_allocated_quantity"),
        row.get("executable_quantity_delta"),
        row.get("quantity_delta_candidate"),
        row.get("transaction_quantity_candidate"),
        row.get("target_quantity_candidate"),
        row.get("lot_adjusted_quantity"),
        row.get("planned_quantity"),
        row.get("selected_quantity"),
        lot_resolution.get("final_allocated_quantity"),
        lot_resolution.get("executable_quantity_delta"),
        authority.get("ps_final_quantity"),
    )
    if one_lot_quantity is None or one_lot_quantity <= 0:
        return empty
    if final_quantity is None or abs(final_quantity - one_lot_quantity) > TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    one_lot_notional = _optional_float(lot_resolution.get("one_lot_notional"), authority.get("one_lot_notional"))
    authorized_notional = _optional_float(
        row.get("discrete_authorized_notional"),
        row.get("lot_adjusted_notional"),
        authority.get("one_lot_notional"),
        lot_resolution.get("one_lot_notional"),
    )
    if one_lot_notional is None or authorized_notional is None or authorized_notional <= 0:
        return empty
    if abs(authorized_notional - one_lot_notional) > max(0.01, one_lot_notional * TARGET_WEIGHT_ABSOLUTE_TOLERANCE):
        return empty
    one_lot_weight = _optional_float(lot_resolution.get("one_lot_weight"), authority.get("one_lot_weight"), target_weight)
    strategy_cap = _optional_float(lot_resolution.get("strategy_cap_weight"), lot_resolution.get("strategy_target_cap"), authority.get("strategy_cap"))
    safety_cap = _optional_float(lot_resolution.get("safety_hard_cap"), lot_resolution.get("safety_hard_cap_weight"), authority.get("safety_cap"))
    post_trade_weight = _optional_float(lot_resolution.get("post_trade_weight"), lot_resolution.get("final_target_weight"), one_lot_weight)
    projected_weight = _optional_float(authority.get("projected_one_lot_portfolio_weight"), one_lot_weight, post_trade_weight)
    if strategy_cap is not None and projected_weight is not None and projected_weight > strategy_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    if strategy_cap is not None and post_trade_weight is not None and post_trade_weight > strategy_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    if safety_cap is None or post_trade_weight is None or post_trade_weight > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    safety_margin = _optional_float(lot_resolution.get("safety_margin_after_trade"))
    if safety_margin is not None and safety_margin < -TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    return {
        "status": "PASS",
        "reason": MINIMUM_EXECUTABLE_ONE_LOT_REASON,
        "authority_type": MINIMUM_EXECUTABLE_ONE_LOT_AUTHORITY_TYPE,
        "authorized_quantity": float(one_lot_quantity),
        "authorized_notional": float(authorized_notional),
        "lot_resolution": dict(lot_resolution),
    }


def _lot_resolution(row: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = row.get("phase29_l19_lot_resolution")
    if isinstance(direct, Mapping):
        return direct
    resolution = row.get("target_weight_resolution")
    if isinstance(resolution, Mapping):
        lot_aware = resolution.get("lot_aware_final_reallocation")
        if isinstance(lot_aware, Mapping):
            nested = lot_aware.get("phase29_l19_lot_resolution")
            if isinstance(nested, Mapping):
                return nested
    nested_authority = row.get("position_sizing_authority")
    if isinstance(nested_authority, Mapping):
        nested = nested_authority.get("phase29_l19_lot_resolution")
        if isinstance(nested, Mapping):
            return nested
    return {}


def _explicit_hard_blocker_present(row: Mapping[str, Any], *, semantic: str) -> bool:
    quality_status = str(row.get("quality_status") or row.get("buy_quality_status") or "").upper()
    quality_action = str(row.get("quality_action") or row.get("reentry_buy_quality_action") or "").upper()
    if quality_status in {"REJECT", "REJECTED", "BLOCK", "BLOCKED", "REVIEW_REQUIRED", "FAIL", "FAILED"}:
        return True
    if quality_action in {"REJECT", "REJECTED", "BLOCK", "BLOCKED", "NO_BUY", "INELIGIBLE"}:
        return True
    for field in (
        "liquidity_capacity_status",
        "capacity_status",
        "reentry_capacity_status",
    ):
        value = str(row.get(field) or "").upper()
        if value in {"SEVERE", "EXCESSIVE", "BLOCK", "BLOCKED", "REVIEW_REQUIRED", "FAIL", "FAILED"}:
            return True
    corporate_action = str(row.get("corporate_action_status") or row.get("reentry_corporate_action_status") or "").upper()
    if any(marker in corporate_action for marker in ("HALT", "QUARANTINE", "BLOCK", "REVIEW", "SUSPEND")):
        return True
    if semantic == "REENTRY":
        for field in (
            "reentry_cooldown_status",
            "reentry_recovery_status",
            "reentry_momentum_recovery_status",
            "reentry_opportunity_qualification_status",
        ):
            value = str(row.get(field) or "").upper()
            if value in {"FAIL", "FAILED", "BLOCK", "BLOCKED", "REVIEW_REQUIRED", "COOLDOWN_ACTIVE", "NOT_ELIGIBLE"}:
                return True
    return False


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
