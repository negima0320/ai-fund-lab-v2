import json
from pathlib import Path

from ai_fund_lab_v2.broker.phase14d7_external_cancel_sync import run_phase14d7_external_cancel_sync
from ai_fund_lab_v2.broker.settings import BrokerSettings


def test_phase14d7_external_cancel_sync_passes_for_cancelled_broker_order(tmp_path):
    snapshot = tmp_path / "snapshot.json"
    pending = tmp_path / "pending.json"
    _write_snapshot(snapshot, status="取消済", remaining_quantity="100")
    _write_pending(pending)

    result = run_phase14d7_external_cancel_sync(
        root=tmp_path / "runtime",
        docs_report_path=tmp_path / "docs" / "d7.md",
        json_report_path=tmp_path / "reports" / "d7.json",
        settings=BrokerSettings(environment="demo", base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9"),
        pending_plan_path=pending,
        snapshot_path=snapshot,
        run_readonly=False,
    )

    assert result.final_decision == "PHASE14D7_BROKER_STATE_SYNC_PASS"
    assert result.target_order_cancelled is True
    assert result.pending_terminal_state == "CONSUMED"
    assert result.asset_changed_by_cancel is False
    assert result.cancel_api_called is False
    assert result.submit_executed is False
    assert result.notification_sent is False


def test_phase14d7_external_cancel_sync_requires_review_when_order_still_open(tmp_path):
    snapshot = tmp_path / "snapshot.json"
    pending = tmp_path / "pending.json"
    _write_snapshot(snapshot, status="未約定", remaining_quantity="100")
    _write_pending(pending)

    result = run_phase14d7_external_cancel_sync(
        root=tmp_path / "runtime",
        docs_report_path=tmp_path / "docs" / "d7.md",
        json_report_path=tmp_path / "reports" / "d7.json",
        settings=BrokerSettings(environment="demo", base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9"),
        pending_plan_path=pending,
        snapshot_path=snapshot,
        run_readonly=False,
    )

    assert result.final_decision == "PHASE14D7_REVIEW_REQUIRED"
    assert result.target_order_cancelled is False
    assert any("not cancelled" in reason for reason in result.review_reasons)


def _write_snapshot(path: Path, *, status: str, remaining_quantity: str) -> None:
    payload = {
        "generated_at": "2026-07-07T03:30:00+00:00",
        "environment": "demo",
        "buying_power": {
            "cash_ref": "cash-1",
            "cash": "19980124",
            "buying_power": "19980124",
            "currency": "JPY",
        },
        "orders": [
            {
                "order_id_hash": "order_347b4cfc8e59e728",
                "issue_code": "9432",
                "side": "buy",
                "quantity": "100",
                "executed_quantity": "0",
                "remaining_quantity": remaining_quantity,
                "status": status,
                "as_of": "2026-07-07T03:30:00+00:00",
            }
        ],
        "positions": [],
        "executions": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_pending(path: Path) -> None:
    payload = {
        "schema_version": "1",
        "pending_plan_id": "pending-phase14d-demo-buy-order-plan",
        "state": "CONSUMED",
        "environment": "demo",
        "created_at": "2026-07-07T02:54:47+00:00",
        "updated_at": "2026-07-07T03:24:47+00:00",
        "plan_created_date": "2026-07-07T02:54:47+00:00",
        "intended_submit_date": "2026-07-07",
        "target_session_date": "2026-07-07",
        "source_order_plan": {
            "order_plan_id": "phase14d-demo-buy-order-plan",
            "path": "order_plan/phase14d-demo-buy.json",
            "artifact_hash": "sha256:test",
        },
        "approval": {
            "approval_path": "approval_artifact/phase14d-demo-buy-approval.json",
            "approval_hash": "sha256:approval",
            "approval_status": "APPROVED",
            "approved_item_ids": ["phase14d-buy-9432-100"],
            "approval_expires_at": "2026-07-07T03:24:47+00:00",
        },
        "approved_item_ids": ["phase14d-buy-9432-100"],
        "items": [
            {
                "pending_item_id": "phase14d-buy-9432-100",
                "symbol": "9432",
                "side": "BUY",
                "quantity": 100.0,
                "order_type": "MARKET",
                "estimated_price": 200.0,
                "estimated_amount": 20000.0,
                "approved": True,
                "state": "PENDING_APPROVAL",
            }
        ],
        "submit_constraints": {"expires_at": "", "allow_post_send_unknown_resubmit": False},
        "consume": {
            "consumed": True,
            "consume_reason": "phase14d demo buy submit attempted",
            "consumed_at": "2026-07-07T03:24:47+00:00",
            "submitted_order_ids": ["sha256:test-order"],
            "ledger_order_record_ids": ["ledger-order-test"],
        },
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
