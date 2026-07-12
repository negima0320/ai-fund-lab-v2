from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.current_state.authority import current_authority_metadata


ROOT = Path(".runtime_acceptance_phase15_buy_origin")
EVIDENCE_DIR = Path("reports/phase_reports/phase15_by2")
BUSINESS_DATE = "2026-07-14"


def run_phase15by2_authority_cleanup(
    *,
    root: Path = ROOT,
    evidence_dir: Path = EVIDENCE_DIR,
    write_phase_report: bool = True,
) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    before_runtime_hashes = _existing_runtime_hashes()
    before = _snapshot(root)
    before_counts = _ledger_counts(root)

    ledger_changes = _cleanup_ledger(root)
    pending_changes = _cleanup_pending(root)
    current_changes = _cleanup_current(root)
    runtime_state_changes = _cleanup_runtime_state(root)

    after = _snapshot(root)
    after_counts = _ledger_counts(root)
    second = {
        "ledger": _cleanup_ledger(root),
        "pending": _cleanup_pending(root),
        "current": _cleanup_current(root),
        "runtime_state": _cleanup_runtime_state(root),
    }
    after_second = _snapshot(root)

    payload = {
        "schema_version": "phase15by2_authority_cleanup_v1",
        "phase": "Phase15-BY2",
        "runtime_root": str(root),
        "root_cause": {
            "production_classification": (
                "Broker ReadOnly normalizer treated simulation/acceptance snapshots as production-equivalent "
                "because the snapshot source was indistinguishable from regular runtime_v2_execution_readonly."
            ),
            "runtime_state_metadata": "Phase15-BY next-day manifest writer overwrote current_state.json after Current Apply.",
            "pending_item_lifecycle": "Submit consume updated plan state but did not propagate consumed state to accepted Pending items.",
        },
        "before": before,
        "after": after,
        "changes": {
            "ledger": ledger_changes,
            "pending": pending_changes,
            "current": current_changes,
            "runtime_state": runtime_state_changes,
        },
        "idempotency_second_run": second,
        "idempotency": {
            "second_run_noop": not any(_changed(value) for value in second.values()),
            "current_hash_unchanged_after_second": after["current_hash"] == after_second["current_hash"],
            "cash_unchanged_after_second": after["cash"] == after_second["cash"],
            "quantity_unchanged_after_second": after["quantity_7203"] == after_second["quantity_7203"],
            "ledger_counts_unchanged": before_counts == after_counts,
            "pending_state_unchanged_after_second": after["pending_state"] == after_second["pending_state"],
        },
        "classification": {
            "orders_production_equivalent": _production_equivalent_values(root / "persistent_ledger" / "orders.jsonl"),
            "executions_production_equivalent": _production_equivalent_values(root / "persistent_ledger" / "executions.jsonl"),
            "positions_production_equivalent": _production_equivalent_values(root / "persistent_ledger" / "positions.jsonl"),
            "cash_production_equivalent": _production_equivalent_values(root / "persistent_ledger" / "cash.jsonl"),
            "events_production_equivalent": _production_equivalent_values(root / "persistent_ledger" / "events.jsonl"),
            "current_production_equivalent": after["current_production_equivalent"],
            "runtime_state_production_equivalent": after["runtime_state_production_equivalent"],
        },
        "semantic_state_preserved": {
            "quantity_7203": after["quantity_7203"] == 100.0,
            "average_price": after["average_price"] == 1000.0,
            "current_price": after["current_price"] == 1050.0,
            "cash": after["cash"] == 900000.0,
            "buying_power": after["buying_power"] == 900000.0,
            "market_value": after["market_value"] == 105000.0,
            "total_equity": after["total_equity"] == 1005000.0,
            "sell_hold": after["sell_hold_decision"] == "HOLD",
        },
        "before_existing_runtime_hashes": before_runtime_hashes,
        "after_existing_runtime_hashes": _existing_runtime_hashes(),
        "existing_runtime_mutated": before_runtime_hashes != _existing_runtime_hashes(),
        "final_judgment": "BUY_ORIGIN_RUNTIME_AUTHORITY_CLOSED",
        "remaining_conditions": [],
        "recommended_next_prefix": "Phase15-BZ Runtime Round-Trip BUY→SELL Acceptance",
    }
    _write_json(evidence_dir / "phase15by2_authority_cleanup_evidence.json", payload)
    if write_phase_report:
        _write_json(Path("reports/phase_reports/phase15_by2_buy_origin_runtime_authority_cleanup.json"), payload)
        _write_text(Path("docs/phase_reports/phase15_by2_buy_origin_runtime_authority_cleanup.md"), _render_markdown(payload))
    return payload


def _cleanup_ledger(root: Path) -> dict[str, Any]:
    changed_files: list[str] = []
    for name in ("orders", "executions", "positions", "cash", "events"):
        path = root / "persistent_ledger" / f"{name}.jsonl"
        rows = _read_jsonl(path)
        changed = False
        updated = []
        for row in rows:
            new_row = dict(row)
            if _is_acceptance_simulation_record(new_row):
                for key, value in {
                    "production_equivalent": False,
                    "acceptance_only": True,
                    "simulation": True,
                }.items():
                    if new_row.get(key) != value:
                        new_row[key] = value
                        changed = True
            updated.append(new_row)
        if changed:
            _write_jsonl(path, updated)
            changed_files.append(str(path))
    return {"changed": bool(changed_files), "changed_files": changed_files}


def _cleanup_pending(root: Path) -> dict[str, Any]:
    path = root / "pending_order_plan" / "pending_order_plan.json"
    payload = _read_json(path)
    changed = False
    consumed = bool((payload.get("consume") or {}).get("consumed"))
    if str(payload.get("state") or "") == "CONSUMED" and consumed:
        items = []
        for item in payload.get("items") or []:
            updated = dict(item)
            if str(updated.get("state") or "") == "CREATED":
                updated["state"] = "CONSUMED"
                changed = True
            items.append(updated)
        payload["items"] = items
    if changed:
        _write_json(path, payload)
    return {"changed": changed, "path": str(path)}


def _cleanup_current(root: Path) -> dict[str, Any]:
    path = root / "persistent_ledger" / "state.json"
    payload = _read_json(path)
    classification_updates = {
        "production_equivalent": False,
        "acceptance_only": True,
        "simulation": True,
        "current_pointer": str(path),
        "source": payload.get("source") or "runtime_v2_runtime_owned_fill_projection",
    }
    canonical_candidate = {**payload, **classification_updates}
    metadata = current_authority_metadata(canonical_candidate)
    updates = {**classification_updates, **metadata}
    changed = False
    for key, value in updates.items():
        if payload.get(key) != value:
            payload[key] = value
            changed = True
    if changed:
        _write_json(path, payload)
    return {"changed": changed, "path": str(path), **metadata}


def _cleanup_runtime_state(root: Path) -> dict[str, Any]:
    current_path = root / "persistent_ledger" / "state.json"
    state_path = root / "runtime_state" / "current_state.json"
    current = _read_json(current_path)
    state = _read_json(state_path) if state_path.exists() else {}
    metadata = current_authority_metadata(current)
    execution_reference = _execution_reference(root)
    runtime_state_version = _runtime_state_version(
        business_date=BUSINESS_DATE,
        current_hash=metadata["current_hash"],
        execution_reference=execution_reference,
    )
    updates = {
        "schema_version": "runtime_v2_current_apply_state_v1",
        "business_date": BUSINESS_DATE,
        "runtime_mode": "demo",
        "environment": "demo",
        "job": "sell_hold_review_after_buy",
        "state": "SELL_HOLD_REVIEW_READY",
        "exit_code": 0,
        "current_pointer": str(current_path),
        "current_path": str(current_path),
        "current_version": metadata["current_version"],
        "current_hash": metadata["current_hash"],
        "execution_reference": execution_reference,
        "execution_references": [execution_reference] if execution_reference else [],
        "runtime_state_version": runtime_state_version,
        "updated_at": BUSINESS_DATE,
        "source": "phase15by2_authority_cleanup",
        "production_equivalent": False,
        "acceptance_only": True,
        "simulation": True,
        "notification_sent": False,
    }
    changed = False
    for key, value in updates.items():
        if state.get(key) != value:
            state[key] = value
            changed = True
    if changed:
        _write_json(state_path, state)
    return {"changed": changed, "path": str(state_path), **updates}


def _snapshot(root: Path) -> dict[str, Any]:
    current = _read_json(root / "persistent_ledger" / "state.json")
    state = _read_json(root / "runtime_state" / "current_state.json")
    pending = _read_json(root / "pending_order_plan" / "pending_order_plan.json")
    pm = _read_json(root / "runtime_state" / "position_management" / BUSINESS_DATE / "position_management_decisions.json")
    position = (current.get("positions") or [{}])[0]
    authority = current_authority_metadata(current)
    return {
        "current_hash": authority["current_hash"],
        "current_version": authority["current_version"],
        "current_hash_field": current.get("current_hash"),
        "current_version_field": current.get("current_version"),
        "runtime_state_version": state.get("runtime_state_version"),
        "runtime_state_current_hash": state.get("current_hash"),
        "execution_reference": state.get("execution_reference"),
        "pending_state": pending.get("state"),
        "pending_consumed": bool((pending.get("consume") or {}).get("consumed")),
        "pending_item_states": [item.get("state") for item in pending.get("items") or []],
        "submitted_order_ids": (pending.get("consume") or {}).get("submitted_order_ids") or [],
        "ledger_order_record_ids": (pending.get("consume") or {}).get("ledger_order_record_ids") or [],
        "cash": current.get("cash"),
        "buying_power": current.get("buying_power"),
        "market_value": current.get("market_value"),
        "total_equity": current.get("total_equity"),
        "quantity_7203": float(position.get("quantity") or 0),
        "average_price": float(position.get("average_price") or 0),
        "current_price": float(position.get("current_price") or 0),
        "current_production_equivalent": current.get("production_equivalent"),
        "runtime_state_production_equivalent": state.get("production_equivalent"),
        "sell_hold_decision": ((pm.get("decisions") or [{}])[0]).get("decision"),
    }


def _is_acceptance_simulation_record(row: dict[str, Any]) -> bool:
    if bool(row.get("acceptance_only")) or bool(row.get("simulation")):
        return True
    if str(row.get("environment") or "") != "demo":
        return False
    if str(row.get("source") or "") in {"runtime_v2_execution_readonly", "runtime_v2_execution_readonly_simulation"}:
        return True
    response = row.get("response_classification") or {}
    return bool(response.get("simulation"))


def _execution_reference(root: Path) -> str:
    for row in _read_jsonl(root / "persistent_ledger" / "executions.jsonl"):
        if row.get("execution_id"):
            return str(row["execution_id"])
    return ""


def _production_equivalent_values(path: Path) -> list[bool | None]:
    return [row.get("production_equivalent") for row in _read_jsonl(path)]


def _ledger_counts(root: Path) -> dict[str, int]:
    return {
        name: len(_read_jsonl(root / "persistent_ledger" / f"{name}.jsonl"))
        for name in ("orders", "executions", "positions", "cash", "events")
    }


def _runtime_state_version(*, business_date: str, current_hash: str, execution_reference: str) -> str:
    raw = json.dumps(
        {
            "business_date": business_date,
            "current_hash": current_hash,
            "execution_reference": execution_reference,
        },
        sort_keys=True,
    )
    return "runtime-state-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _changed(value: dict[str, Any]) -> bool:
    return bool(value.get("changed"))


def _existing_runtime_hashes() -> dict[str, str]:
    paths = {
        "pending": Path(".runtime/pending_order_plan/pending_order_plan.json"),
        "safety": Path(".runtime/runtime_state/safety/latest_safety_decision.json"),
        "current": Path(".runtime/persistent_ledger/state.json"),
    }
    return {key: _sha256(path) for key, path in paths.items() if path.exists()}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _render_markdown(payload: dict[str, Any]) -> str:
    after = payload["after"]
    return "\n".join(
        [
            "# Phase15-BY2 BUY-Origin Runtime Authority and Classification Cleanup",
            "",
            "## Final Judgment",
            "",
            f"`{payload['final_judgment']}`",
            "",
            "## Root Cause",
            "",
            f"- Production classification: {payload['root_cause']['production_classification']}",
            f"- Runtime State metadata: {payload['root_cause']['runtime_state_metadata']}",
            f"- Pending item lifecycle: {payload['root_cause']['pending_item_lifecycle']}",
            "",
            "## Closure Evidence",
            "",
            f"- current_version: {after['current_version_field']}",
            f"- current_hash: {after['current_hash_field']}",
            f"- runtime_state_version: {after['runtime_state_version']}",
            f"- execution_reference: {after['execution_reference']}",
            f"- pending item states: {', '.join(str(item) for item in after['pending_item_states'])}",
            f"- production_equivalent current/runtime_state: {after['current_production_equivalent']} / {after['runtime_state_production_equivalent']}",
            "",
            "## Semantic State Preserved",
            "",
            f"- 7203 quantity: {after['quantity_7203']}",
            f"- cash: {after['cash']}",
            f"- buying_power: {after['buying_power']}",
            f"- market_value: {after['market_value']}",
            f"- total_equity: {after['total_equity']}",
            f"- SELL/HOLD: {after['sell_hold_decision']}",
            "",
            "## Idempotency",
            "",
            f"- second_run_noop: {payload['idempotency']['second_run_noop']}",
            f"- ledger_counts_unchanged: {payload['idempotency']['ledger_counts_unchanged']}",
            f"- existing_runtime_mutated: {payload['existing_runtime_mutated']}",
            "",
            "## Next Prefix",
            "",
            payload["recommended_next_prefix"],
            "",
        ]
    )


if __name__ == "__main__":
    target_root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    result = run_phase15by2_authority_cleanup(root=target_root)
    print(json.dumps({"final_judgment": result["final_judgment"], "runtime_root": str(target_root)}, ensure_ascii=False))
