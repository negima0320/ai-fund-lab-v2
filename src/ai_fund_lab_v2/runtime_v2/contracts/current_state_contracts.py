"""Runtime v2 current state contract metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentStateContract:
    name: str
    path_object_type: str
    file_kind: str
    required_fields: tuple[str, ...]
    append_only: bool
    snapshot: bool
    owner_component: str
    writer_components: tuple[str, ...]
    reader_components: tuple[str, ...]


CURRENT_STATE_CONTRACTS: dict[str, CurrentStateContract] = {
    "runtime_state": CurrentStateContract(
        name="runtime_state",
        path_object_type="runtime_state",
        file_kind="json",
        required_fields=(
            "schema_version",
            "runtime_id",
            "run_id",
            "state",
            "environment",
            "updated_at",
        ),
        append_only=False,
        snapshot=True,
        owner_component="Runtime State Runtime",
        writer_components=("Runtime State Runtime",),
        reader_components=("Runtime Orchestrator", "Report Builder", "Audit Runtime"),
    ),
    "pending_order_plan": CurrentStateContract(
        name="pending_order_plan",
        path_object_type="pending_order_plan",
        file_kind="json",
        required_fields=(
            "schema_version",
            "pending_plan_id",
            "state",
            "environment",
            "created_at",
            "updated_at",
            "items",
        ),
        append_only=False,
        snapshot=True,
        owner_component="Pending Runtime",
        writer_components=("Pending Runtime",),
        reader_components=("Approval Runtime", "Submit Runtime", "Report Builder"),
    ),
    "persistent_ledger_state": CurrentStateContract(
        name="persistent_ledger_state",
        path_object_type="persistent_ledger_state",
        file_kind="json",
        required_fields=(
            "schema_version",
            "asset_state_id",
            "environment",
            "updated_at",
            "positions",
            "cash",
            "buying_power",
            "review_required",
        ),
        append_only=False,
        snapshot=True,
        owner_component="Asset Runtime",
        writer_components=("Asset Runtime",),
        reader_components=(
            "Current State Reader",
            "Pending Plan Runtime",
            "Approval Runtime",
            "Submit Runtime",
            "Report Builder",
        ),
    ),
    "persistent_ledger_orders": CurrentStateContract(
        name="persistent_ledger_orders",
        path_object_type="persistent_ledger_orders",
        file_kind="jsonl",
        required_fields=(
            "schema_version",
            "ledger_record_id",
            "recorded_at",
            "environment",
            "source",
            "review_required",
        ),
        append_only=True,
        snapshot=False,
        owner_component="Ledger Runtime",
        writer_components=("Ledger Runtime",),
        reader_components=("Reconciliation Runtime", "Report Builder", "Audit Runtime"),
    ),
    "persistent_ledger_executions": CurrentStateContract(
        name="persistent_ledger_executions",
        path_object_type="persistent_ledger_executions",
        file_kind="jsonl",
        required_fields=(
            "schema_version",
            "ledger_record_id",
            "execution_key",
            "recorded_at",
            "environment",
            "source",
            "review_required",
        ),
        append_only=True,
        snapshot=False,
        owner_component="Ledger Runtime",
        writer_components=("Ledger Runtime",),
        reader_components=("Reconciliation Runtime", "Report Builder", "Audit Runtime"),
    ),
    "persistent_ledger_positions": CurrentStateContract(
        name="persistent_ledger_positions",
        path_object_type="persistent_ledger_positions",
        file_kind="jsonl",
        required_fields=(
            "schema_version",
            "ledger_record_id",
            "position_key",
            "recorded_at",
            "environment",
            "source",
            "review_required",
        ),
        append_only=True,
        snapshot=False,
        owner_component="Ledger Runtime",
        writer_components=("Ledger Runtime",),
        reader_components=("Current State Reader", "Report Builder", "Audit Runtime"),
    ),
    "persistent_ledger_cash": CurrentStateContract(
        name="persistent_ledger_cash",
        path_object_type="persistent_ledger_cash",
        file_kind="jsonl",
        required_fields=(
            "schema_version",
            "ledger_record_id",
            "cash_snapshot_key",
            "recorded_at",
            "environment",
            "source",
            "review_required",
        ),
        append_only=True,
        snapshot=False,
        owner_component="Ledger Runtime",
        writer_components=("Ledger Runtime",),
        reader_components=("Current State Reader", "Report Builder", "Audit Runtime"),
    ),
    "persistent_ledger_events": CurrentStateContract(
        name="persistent_ledger_events",
        path_object_type="persistent_ledger_events",
        file_kind="jsonl",
        required_fields=(
            "schema_version",
            "event_id",
            "recorded_at",
            "environment",
            "event_type",
            "severity",
            "review_required",
        ),
        append_only=True,
        snapshot=False,
        owner_component="Ledger Runtime",
        writer_components=("Ledger Runtime",),
        reader_components=("Report Builder", "Audit Runtime"),
    ),
    "notification_delivery_ledger": CurrentStateContract(
        name="notification_delivery_ledger",
        path_object_type="notification_delivery_ledger",
        file_kind="jsonl",
        required_fields=(
            "schema_version",
            "delivery_id",
            "payload_hash",
            "channel",
            "target_date",
            "recorded_at",
            "status",
            "retry_allowed",
            "review_required",
        ),
        append_only=True,
        snapshot=False,
        owner_component="Notification Runtime",
        writer_components=("Notification Runtime",),
        reader_components=("Notification Runtime", "Report Builder", "Audit Runtime"),
    ),
}
