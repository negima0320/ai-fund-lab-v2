"""Asset Runtime skeleton for Runtime v2."""

from ai_fund_lab_v2.runtime_v2.asset.builder import (
    build_current_asset_state,
    build_current_asset_state_from_orders,
)
from ai_fund_lab_v2.runtime_v2.asset.capability_policy import (
    AssetReflectionDecision,
    apply_broker_cash_policy,
    decide_asset_reflection_from_broker_evidence,
    should_auto_replace_positions_from_broker,
)
from ai_fund_lab_v2.runtime_v2.asset.initializer import initialize_demo_operation_current_sot
from ai_fund_lab_v2.runtime_v2.asset.models import (
    CurrentAssetPosition,
    CurrentAssetState,
)
from ai_fund_lab_v2.runtime_v2.asset.runtime_owned_fill_projection import (
    RuntimeOwnedFillProjectionResult,
    project_runtime_owned_fills_to_current,
)
from ai_fund_lab_v2.runtime_v2.asset.writer import (
    asset_state_to_payload,
    write_current_asset_state,
)

__all__ = [
    "AssetReflectionDecision",
    "CurrentAssetPosition",
    "CurrentAssetState",
    "RuntimeOwnedFillProjectionResult",
    "apply_broker_cash_policy",
    "asset_state_to_payload",
    "build_current_asset_state",
    "build_current_asset_state_from_orders",
    "decide_asset_reflection_from_broker_evidence",
    "initialize_demo_operation_current_sot",
    "project_runtime_owned_fills_to_current",
    "should_auto_replace_positions_from_broker",
    "write_current_asset_state",
]
