import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline


def test_phase14e21_execution_readonly_ingests_broker_evidence_without_overwriting_demo_asset(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-demo-1m",
            "environment": "demo",
            "source": "phase14e8_demo_operation_initial_state",
            "as_of": "2026-07-08",
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "review_required": False,
            "production_equivalent": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
            "generated_from": [],
            "created_at": "2026-07-08",
        },
    )
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-e21",
            "state": "CONSUMED",
            "environment": "demo",
            "created_at": "2026-07-08",
            "updated_at": "2026-07-08",
            "plan_created_date": "2026-07-08",
            "intended_submit_date": "2026-07-08",
            "target_session_date": "2026-07-08",
            "source_order_plan": {
                "order_plan_id": "order-e21",
                "path": "x",
                "artifact_hash": "sha256:x",
            },
            "approval": None,
            "approved_item_ids": [],
            "items": [],
            "submit_constraints": {
                "requires_manual_approval": True,
                "pending_only_submit": True,
                "duplicate_submit_guard": True,
                "expires_at": "",
                "max_order_amount": None,
            },
            "consume": {"consumed": True, "consume_reason": "test"},
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
        },
    )

    def fake_snapshot(**kwargs):
        snapshot_path = Path(kwargs["snapshot_path"])
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(
            snapshot_path,
            {
                "generated_at": "2026-07-08T09:05:00+09:00",
                "orders": [
                    {
                        "order_id_hash": "order_e21",
                        "issue_code": "6522",
                        "side": "buy",
                        "quantity": "100",
                        "executed_quantity": "0",
                        "remaining_quantity": "0",
                        "status": "失効",
                        "as_of": "2026-07-08T09:05:00+09:00",
                    }
                ],
                "executions": [],
                "positions": [],
                "buying_power": {
                    "raw_clmid": "CLMZanKaiKanougaku",
                    "cash_available": "20000000",
                    "buying_power": "20000000",
                    "currency": "JPY",
                },
            },
        )
        _write_json(Path(kwargs["report_path"]), {"status": "PASS"})
        return type("SnapshotResult", (), {"status": "PASS"})()

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        snapshot_provider=fake_snapshot,
    )

    current = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    assert result.status == "REVIEW_REQUIRED"
    assert result.orderlist_readonly_connected is True
    assert result.execution_reflection_connected is True
    assert result.ledger_connected is True
    assert result.asset_connected is True
    assert result.asset_current_written is False
    assert result.reconcile_findings > 0
    assert current["cash"] == 1_000_000
    assert current["positions"] == []
    assert (runtime_root / "persistent_ledger" / "orders.jsonl").read_text(encoding="utf-8")
    assert (runtime_root / "persistent_ledger" / "cash.jsonl").read_text(encoding="utf-8")


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
