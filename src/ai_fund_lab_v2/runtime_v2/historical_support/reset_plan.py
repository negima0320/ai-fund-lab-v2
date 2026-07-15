"""Trading State reset plan support for historical Runtime tests.

The functions in this module build and validate a reset plan only. They do not
execute reset, delete files, or initialize Current/Ledger/Pending.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.historical_support.common import file_ref


@dataclass(frozen=True)
class HistoricalInitialStateConfig:
    cash: float = 1_000_000.0
    buying_power: float = 1_000_000.0
    positions: int = 0
    pending: int = 0
    open_orders: int = 0
    executions: int = 0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    currency: str = "JPY"


RESETTABLE_RELATIVE_PATHS: tuple[str, ...] = (
    "persistent_ledger/state.json",
    "persistent_ledger/orders.jsonl",
    "persistent_ledger/executions.jsonl",
    "persistent_ledger/positions.jsonl",
    "persistent_ledger/cash.jsonl",
    "persistent_ledger/events.jsonl",
    "pending_order_plan/pending_order_plan.json",
    "pending_order_plan/history",
    "runtime_state/current_state.json",
    "runtime_state/authoritative_pending_apply_candidate",
    "runtime_state/human_approval",
    "runtime_state/human_review",
    "runtime_state/historical_broker",
    "runtime_state/pending_promotion_candidate",
    "runtime_state/broker_readonly",
    "runtime_state/current_migration",
    "runtime_state/current_valuation",
    "runtime_state/data_readiness",
    "runtime_state/position_management",
    "runtime_state/safety",
    "runtime_state/run_manifest",
    "runtime_state/logs",
    "runtime_state/market",
    "runtime_state/morning_pipeline",
    "operations/feature_date_contract",
    "operations/feature_consumer_readiness",
    "operations/feature_artifacts",
    "operations/feature_refresh",
    "operations/market_refresh",
    "broker/sync_results",
)

RESET_EXCLUDED_RELATIVE_PREFIXES: tuple[str, ...] = (
    "artifact_registry",
    "artifacts",
    "operations/jquants",
    "phase9/canonical_data",
    "data/raw",
    "candidate_ai",
    "opportunity_ai",
    "configs",
)


def build_reset_plan(
    *,
    runtime_root: Path | str,
    environment_id: str,
    run_id: str,
    git_commit: str,
    runtime_version: str,
    initial_state: HistoricalInitialStateConfig | None = None,
) -> dict[str, Any]:
    """Build a non-mutating reset plan manifest for normal ``.runtime``."""

    root = Path(runtime_root)
    config = initial_state or HistoricalInitialStateConfig()
    targets = [
        {
            "path": rel,
            "action": "BACKUP_THEN_RESET_OR_INITIALIZE",
            "required": rel in {
                "persistent_ledger/state.json",
                "pending_order_plan/pending_order_plan.json",
                "runtime_state/current_state.json",
            },
            "current_ref": file_ref(root / rel, root=root),
        }
        for rel in RESETTABLE_RELATIVE_PATHS
    ]
    return {
        "schema_version": "runtime_historical_trading_state_reset_plan_v1",
        "runtime_root": str(root),
        "runtime_root_policy": "normal .runtime only",
        "environment_id": environment_id,
        "run_id": run_id,
        "git_commit": git_commit,
        "runtime_version": runtime_version,
        "initial_state_config": asdict(config),
        "all_or_nothing_required": True,
        "manual_json_edit_prohibited": True,
        "partial_reset_prohibited": True,
        "targets": targets,
        "reset_exclusion_prefixes": list(RESET_EXCLUDED_RELATIVE_PREFIXES),
        "execution_status": "PLAN_ONLY_NOT_EXECUTED",
    }


def validate_reset_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate reset scope and exclusion boundaries without mutating files."""

    errors: list[str] = []
    warnings: list[str] = []
    runtime_root = str(plan.get("runtime_root") or "")
    if not runtime_root.endswith(".runtime"):
        errors.append("runtime_root must be the normal .runtime path")
    targets = plan.get("targets")
    if not isinstance(targets, list) or not targets:
        errors.append("reset plan has no targets")
        targets = []
    allowed = set(RESETTABLE_RELATIVE_PATHS)
    for target in targets:
        rel = str(target.get("path") or "")
        if rel not in allowed:
            errors.append(f"target is outside accepted resettable scope: {rel}")
        for prefix in RESET_EXCLUDED_RELATIVE_PREFIXES:
            if rel == prefix or rel.startswith(prefix + "/"):
                errors.append(f"target includes reset-excluded prefix: {rel}")
    required_refs = {
        str(target.get("path")): target.get("current_ref") or {}
        for target in targets
        if bool(target.get("required"))
    }
    for rel, ref in required_refs.items():
        if not ref.get("exists"):
            warnings.append(f"required reset target currently missing: {rel}")
    status = "PASS" if not errors else "HALT"
    return {
        "schema_version": "runtime_historical_reset_plan_validation_v1",
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "reset_execution_allowed_by_plan": status == "PASS",
        "reset_executed": False,
    }
