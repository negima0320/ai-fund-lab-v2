"""Runtime position-count authority resolution.

This module consumes already-materialized Strategy / Portfolio Policy dynamic
position-count evidence. It deliberately does not fall back to legacy
``CapitalDeploymentPolicy.max_positions`` as a Runtime BUY admission authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.strategy.dynamic_position_count import validate_dynamic_position_count_artifact


AUTHORITY_WINNER = "safety_hard_maximum_only"
MISSING_AUTHORITY_WINNER = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class PositionCountAuthority:
    status: str
    reason: str
    strategy_requested_position_count: int | None
    selected_dynamic_position_count: int
    current_position_count: int
    available_position_slots: int
    effective_order_limit: int
    safety_hard_maximum: int | None
    position_count_authority_winner: str
    position_count_binding_constraint: str
    legacy_position_count_config_used: bool
    position_count_fallback_used: bool
    runtime_mode: str
    business_date: str
    producer: str
    consumer: str
    runtime_path: str
    authority_source: str
    authority_hash: str
    configured_legacy_max_positions: int | None
    operator_order_limit: int | None = None

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    def with_current_position_count(self, current_position_count: int) -> "PositionCountAuthority":
        return _with_current_position_count(self, current_position_count)

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_count_authority_status": self.status,
            "position_count_authority_reason": self.reason,
            "strategy_requested_position_count": self.strategy_requested_position_count,
            "selected_dynamic_position_count": self.selected_dynamic_position_count,
            "current_position_count": self.current_position_count,
            "available_position_slots": self.available_position_slots,
            "effective_order_limit": self.effective_order_limit,
            "safety_hard_maximum": self.safety_hard_maximum,
            "position_count_authority_winner": self.position_count_authority_winner,
            "position_count_binding_constraint": self.position_count_binding_constraint,
            "legacy_position_count_config_used": self.legacy_position_count_config_used,
            "position_count_fallback_used": self.position_count_fallback_used,
            "runtime_mode": self.runtime_mode,
            "business_date": self.business_date,
            "position_count_producer": self.producer,
            "position_count_consumer": self.consumer,
            "position_count_runtime_path": self.runtime_path,
            "position_count_authority_source": self.authority_source,
            "position_count_authority_hash": self.authority_hash,
            "configured_legacy_max_positions": self.configured_legacy_max_positions,
            "legacy_runtime_max_positions": self.configured_legacy_max_positions,
            "operator_order_limit": self.operator_order_limit,
        }


def resolve_position_count_authority(
    *,
    runtime_root: Path | str | None = None,
    business_date: str,
    runtime_mode: str,
    current_position_count: int,
    configured_legacy_max_positions: int | None,
    operator_order_limit: int | None = None,
    policy_context: Mapping[str, Any] | None = None,
    artifact_path: Path | str | None = None,
    consumer: str = "runtime_v2_buy_admission",
) -> PositionCountAuthority:
    payload, source = _load_authority_payload(
        runtime_root=Path(runtime_root) if runtime_root is not None else None,
        business_date=business_date,
        policy_context=policy_context,
        artifact_path=Path(artifact_path) if artifact_path is not None else None,
    )
    if payload is None:
        return _missing_authority(
            reason="dynamic_position_count_authority_missing",
            business_date=business_date,
            runtime_mode=runtime_mode,
            current_position_count=current_position_count,
            configured_legacy_max_positions=configured_legacy_max_positions,
            operator_order_limit=operator_order_limit,
            consumer=consumer,
        )
    if source != "policy_context":
        try:
            validate_dynamic_position_count_artifact(dict(payload))
        except Exception as exc:  # noqa: BLE001 - evidence keeps the validation reason.
            return _missing_authority(
                reason=f"dynamic_position_count_authority_invalid:{exc}",
                business_date=business_date,
                runtime_mode=runtime_mode,
                current_position_count=current_position_count,
                configured_legacy_max_positions=configured_legacy_max_positions,
                operator_order_limit=operator_order_limit,
                consumer=consumer,
                source=source,
                authority_hash=_stable_hash(dict(payload)),
            )
    requested = _optional_int(
        payload.get("selected_dynamic_position_count"),
        payload.get("target_position_count"),
        payload.get("actual_target_position_count"),
        payload.get("dynamic_position_count"),
    )
    safety_hard_maximum = _optional_int(payload.get("safety_hard_maximum"), payload.get("maximum_position_count"))
    selected = safety_hard_maximum if safety_hard_maximum is not None else 0
    binding = "SAFETY_HARD_MAXIMUM" if safety_hard_maximum is not None else "NO_FIXED_POSITION_COUNT_LIMIT"
    authority = PositionCountAuthority(
        status="PASS",
        reason="target_position_count_decision_authority_removed",
        strategy_requested_position_count=None if requested is None else int(requested),
        selected_dynamic_position_count=selected,
        current_position_count=max(int(current_position_count), 0),
        available_position_slots=0,
        effective_order_limit=0,
        safety_hard_maximum=safety_hard_maximum,
        position_count_authority_winner=AUTHORITY_WINNER,
        position_count_binding_constraint=binding,
        legacy_position_count_config_used=False,
        position_count_fallback_used=False,
        runtime_mode=runtime_mode,
        business_date=business_date,
        producer="strategy.portfolio_policy.safety_hard_maximum",
        consumer=consumer,
        runtime_path="Production/Demo/Historical common runtime_v2",
        authority_source=source,
        authority_hash=_stable_hash(dict(payload)),
        configured_legacy_max_positions=configured_legacy_max_positions,
        operator_order_limit=operator_order_limit,
    )
    return _with_current_position_count(authority, current_position_count)


def position_count_authority_from_context(
    context: Mapping[str, Any] | None,
    *,
    business_date: str,
    runtime_mode: str,
    current_position_count: int,
    configured_legacy_max_positions: int | None,
    operator_order_limit: int | None = None,
    consumer: str = "runtime_v2_buy_admission",
) -> PositionCountAuthority:
    return resolve_position_count_authority(
        runtime_root=None,
        business_date=business_date,
        runtime_mode=runtime_mode,
        current_position_count=current_position_count,
        configured_legacy_max_positions=configured_legacy_max_positions,
        operator_order_limit=operator_order_limit,
        policy_context=context,
        consumer=consumer,
    )


def _with_current_position_count(authority: PositionCountAuthority, current_position_count: int) -> PositionCountAuthority:
    current_count = max(int(current_position_count), 0)
    if authority.safety_hard_maximum is None:
        available = 0
        effective = max(int(authority.operator_order_limit), 0) if authority.operator_order_limit is not None else 0
    else:
        available = max(authority.safety_hard_maximum - current_count, 0)
        effective = available
    binding = authority.position_count_binding_constraint
    reason = authority.reason
    if authority.passed and authority.safety_hard_maximum is not None and current_count >= authority.safety_hard_maximum:
        binding = "SAFETY_HARD_MAXIMUM"
        reason = "safety_hard_maximum_current_holdings_at_or_above_limit"
    if authority.operator_order_limit is not None:
        effective = min(effective, max(int(authority.operator_order_limit), 0)) if authority.safety_hard_maximum is not None else max(int(authority.operator_order_limit), 0)
        if effective < available:
            binding = "OPERATOR_LIMIT"
            reason = "operator_order_limit_capped_orders"
    return replace(
        authority,
        reason=reason,
        current_position_count=current_count,
        available_position_slots=available,
        effective_order_limit=effective,
        position_count_binding_constraint=binding,
    )


def _missing_authority(
    *,
    reason: str,
    business_date: str,
    runtime_mode: str,
    current_position_count: int,
    configured_legacy_max_positions: int | None,
    operator_order_limit: int | None,
    consumer: str,
    source: str = "",
    authority_hash: str = "",
) -> PositionCountAuthority:
    return PositionCountAuthority(
        status="REVIEW_REQUIRED",
        reason=reason,
        strategy_requested_position_count=None,
        selected_dynamic_position_count=0,
        current_position_count=max(int(current_position_count), 0),
        available_position_slots=0,
        effective_order_limit=0,
        safety_hard_maximum=None,
        position_count_authority_winner=MISSING_AUTHORITY_WINNER,
        position_count_binding_constraint="REVIEW_REQUIRED",
        legacy_position_count_config_used=False,
        position_count_fallback_used=False,
        runtime_mode=runtime_mode,
        business_date=business_date,
        producer="strategy.portfolio_policy.internal_dynamic_position_count",
        consumer=consumer,
        runtime_path="Production/Demo/Historical common runtime_v2",
        authority_source=source,
        authority_hash=authority_hash,
        configured_legacy_max_positions=configured_legacy_max_positions,
        operator_order_limit=operator_order_limit,
    )


def _load_authority_payload(
    *,
    runtime_root: Path | None,
    business_date: str,
    policy_context: Mapping[str, Any] | None,
    artifact_path: Path | None,
) -> tuple[Mapping[str, Any] | None, str]:
    if policy_context:
        nested = policy_context.get("position_count_authority")
        if isinstance(nested, Mapping):
            return nested, "policy_context"
        if _optional_int(
            policy_context.get("safety_hard_maximum"),
            policy_context.get("maximum_position_count"),
            policy_context.get("selected_dynamic_position_count"),
            policy_context.get("target_position_count"),
            policy_context.get("dynamic_position_count"),
        ) is not None:
            return policy_context, "policy_context"
    paths: list[Path] = []
    if artifact_path is not None:
        paths.append(artifact_path)
    if runtime_root is not None:
        paths.extend(
            [
                runtime_root / "strategy_artifacts" / "dynamic_position_count" / business_date / "dynamic_position_count.json",
                runtime_root / "strategy_artifacts" / business_date / "dynamic_position_count.json",
                runtime_root / "strategy" / business_date / "dynamic_position_count.json",
                runtime_root / "strategy" / "dynamic_position_count.json",
            ]
        )
    for path in paths:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")), str(path)
    return None, ""


def _optional_int(*values: Any) -> int | None:
    for value in values:
        if value in (None, "") or isinstance(value, bool):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _stable_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
