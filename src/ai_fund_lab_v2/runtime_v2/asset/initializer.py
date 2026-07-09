"""Runtime v2 fixed Current initialization helpers."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.asset.builder import build_current_asset_state
from ai_fund_lab_v2.runtime_v2.asset.writer import asset_state_to_payload, write_current_asset_state
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerCashRecord, LedgerEventRecord
from ai_fund_lab_v2.runtime_v2.ledger.writer import ledger_record_to_payload, write_ledger_records


PERSISTENT_LEDGER_FILES = (
    "state.json",
    "orders.jsonl",
    "executions.jsonl",
    "positions.jsonl",
    "cash.jsonl",
    "events.jsonl",
)


def initialize_demo_operation_current_sot(
    *,
    runtime_root: Path = Path(".runtime"),
    business_date: str,
    backup_root: Path = Path(".runtime/backups/phase14e8"),
) -> dict[str, str]:
    """Initialize fixed Current SoT for demo operation evaluation capital."""

    capability = get_broker_capability("demo")
    if capability.default_evaluation_capital is None:
        raise ValueError("demo default evaluation capital is required")
    if _is_mode_rooted_runtime_path(runtime_root):
        raise ValueError("mode-rooted Current path is not allowed")

    persistent_ledger = runtime_root / "persistent_ledger"
    backup_dir = _next_backup_dir(backup_root / business_date)
    _backup_existing_current(persistent_ledger, backup_dir)

    cash_record = LedgerCashRecord(
        record_id=f"ledger-cash-phase14e8-demo-initial-{business_date}",
        record_type="cash",
        schema_version="1",
        environment="demo",
        source="phase14e8_demo_operation_initial_state",
        created_at=business_date,
        dedup_key=f"phase14e8:demo-initial-cash:{business_date}",
        review_required=False,
        production_equivalent=False,
        cash_key=f"phase14e8-demo-initial-cash-{business_date}",
        cash=capability.default_evaluation_capital,
        buying_power=capability.default_evaluation_capital,
        currency="JPY",
        as_of=business_date,
    )
    event_record = LedgerEventRecord(
        record_id=f"ledger-event-phase14e8-demo-initial-{business_date}",
        record_type="event",
        schema_version="1",
        environment="demo",
        source="phase14e8_demo_operation_initial_state",
        created_at=business_date,
        dedup_key=f"phase14e8:demo-initial-event:{business_date}",
        review_required=False,
        production_equivalent=False,
        event_id=f"phase14e8-demo-operation-initialized-{business_date}",
        event_type="DEMO_OPERATION_INITIALIZED",
        severity="INFO",
        message="Runtime demo operation Current SoT initialized with evaluation capital JPY 1,000,000 and no positions.",
        related_id="broker_capability",
    )
    state = build_current_asset_state(
        environment="demo",
        positions=(),
        cash_records=(cash_record,),
        source="phase14e8_demo_operation_initial_state",
        as_of=business_date,
    )
    state = replace(
        state,
        review_required=False,
        production_equivalent=False,
        current_state_confirmed_empty=True,
    )

    write_current_asset_state(persistent_ledger / "state.json", state)
    write_ledger_records(persistent_ledger / "orders.jsonl", ())
    write_ledger_records(persistent_ledger / "executions.jsonl", ())
    write_ledger_records(persistent_ledger / "positions.jsonl", ())
    write_ledger_records(persistent_ledger / "cash.jsonl", (cash_record,))
    write_ledger_records(persistent_ledger / "events.jsonl", (event_record,))

    manifest = {
        "schema_version": "1",
        "business_date": business_date,
        "source": "phase14e8_demo_operation_initial_state",
        "runtime_root": str(runtime_root),
        "backup_dir": str(backup_dir),
        "state_path": str(persistent_ledger / "state.json"),
        "cash": capability.default_evaluation_capital,
        "buying_power": capability.default_evaluation_capital,
        "positions": [],
        "capability": asdict(capability),
        "state_payload": asset_state_to_payload(state),
        "cash_payload": ledger_record_to_payload(cash_record),
        "event_payload": ledger_record_to_payload(event_record),
    }
    manifest_path = backup_dir / "initialization_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "backup_dir": str(backup_dir),
        "manifest_path": str(manifest_path),
        "state_path": str(persistent_ledger / "state.json"),
    }


def _backup_existing_current(persistent_ledger: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    for filename in PERSISTENT_LEDGER_FILES:
        source = persistent_ledger / filename
        if source.exists():
            shutil.copy2(source, backup_dir / filename)


def _next_backup_dir(base: Path) -> Path:
    if not base.exists():
        return base
    index = 2
    while True:
        candidate = base.with_name(f"{base.name}_{index}")
        if not candidate.exists():
            return candidate
        index += 1


def _is_mode_rooted_runtime_path(path: Path) -> bool:
    parts = path.parts
    runtime_modes = {"production", "demo", "simulation", "backtest"}
    return any(
        part == ".runtime"
        and index + 1 < len(parts)
        and parts[index + 1] in runtime_modes
        for index, part in enumerate(parts)
    )
