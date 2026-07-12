from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from tests.runtime_v2.phase15bx_mainline_closure import (
    BU_AUTHORITY,
    run_phase15bx_mainline_closure,
)


def test_phase15bx_connects_normal_submit_execution_current_and_report(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_mainline_closure"
    payload = run_phase15bx_mainline_closure(
        root=root,
        evidence_dir=tmp_path / "phase15_bx",
        write_phase_report=False,
    )

    assert payload["final_judgment"] == "NORMAL_RUNTIME_MAINLINE_CONNECTED_WITH_CONDITIONS"
    assert payload["runtime_mutation"]["new_broker_write"] is False
    assert payload["runtime_mutation"]["production_write"] is False
    assert payload["normal_submit_pipeline"]["status"] == "PASS"
    assert payload["normal_submit_pipeline"]["accepted_count"] == 1
    assert payload["normal_submit_pipeline"]["pending_consumed"] is True
    assert payload["normal_execution_processor"]["status"] == "PASS"
    assert payload["normal_execution_processor"]["execution_equivalent_count"] == 1
    assert payload["normal_execution_processor"]["fallback"]["used"] is True
    assert payload["normal_current_projector"]["position_6501_quantity"] == 100.0
    assert payload["normal_current_projector"]["cash"] == 17_704_424.0
    assert payload["normal_current_projector"]["market_value"] == 470_000.0
    assert payload["normal_current_projector"]["execution_price"] == 100.0
    assert payload["normal_current_projector"]["valuation_price"] == 4700.0
    assert payload["normal_current_projector"]["production_equivalent"] is False
    assert payload["normal_current_apply"]["first_status"] == "APPLIED"
    assert payload["normal_current_apply"]["second_status"] == "NOOP_ALREADY_APPLIED"
    assert payload["idempotency"]["position_6501_stayed_100"] is True
    assert payload["idempotency"]["cash_not_double_counted"] is True
    assert payload["idempotency"]["ledger_duplicate_delta"] == {
        "orders": 0,
        "executions": 0,
        "positions": 0,
        "cash": 0,
        "events": 0,
    }
    assert payload["report"]["generated"] is True
    assert payload["report"]["notification_sent"] is False

    current = json.loads((root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    assert current["positions"][0]["symbol"] == "6501"
    assert current["positions"][0]["quantity"] == 100.0
    runtime_state = json.loads((root / "runtime_state" / "current_state.json").read_text(encoding="utf-8"))
    assert runtime_state["state"] == "CURRENT_APPLIED"
    assert runtime_state["current_hash"] == payload["normal_current_apply"]["current_hash"]


def test_phase15bx_demo_execution_fallback_is_rejected_in_production(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_mainline_closure"
    root.mkdir(parents=True)

    result = run_execution_readonly_pipeline(
        runtime_root=root,
        business_date="2026-07-13",
        mode="production",
        snapshot_provider=lambda **_: None,
        demo_execution_fallback_authority_path=BU_AUTHORITY,
    )

    assert result.status == "BLOCKED"
    assert "prohibited in production" in result.reason
