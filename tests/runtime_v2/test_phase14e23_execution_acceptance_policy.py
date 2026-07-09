import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline


def test_phase14e23_order_detail_failure_is_optional_when_orderlist_position_cash_match(tmp_path):
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
            "pending_plan_id": "pending-e23",
            "state": "CONSUMED",
            "environment": "demo",
            "created_at": "2026-07-08",
            "updated_at": "2026-07-08",
            "plan_created_date": "2026-07-08",
            "intended_submit_date": "2026-07-08",
            "target_session_date": "2026-07-08",
            "source_order_plan": {"order_plan_id": "order-e23", "path": "x", "artifact_hash": "sha256:x"},
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
    _write_jsonl(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        [
            {
                "record_type": "order",
                "source": "runtime_v2_submit_pipeline",
                "status": "ACCEPTED",
                "symbol": "65220",
                "issue_code_normalization": {"broker_issue_code": "6522"},
                "record_id": "ledger-order-submit-65220",
            }
        ],
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
                        "order_id_hash": "order_e23_6522",
                        "issue_code": "6522",
                        "side": "buy",
                        "quantity": "100",
                        "executed_quantity": "100",
                        "remaining_quantity": "0",
                        "status": "全部約定",
                        "as_of": "2026-07-08T09:05:00+09:00",
                    }
                ],
                "executions": [],
                "positions": [
                    {
                        "position_id": "position_e23_6522",
                        "issue_code": "6522",
                        "quantity": "100",
                        "average_price": "102",
                        "market_value": "235000",
                    }
                ],
                "buying_power": {
                    "raw_clmid": "CLMZanKaiKanougaku",
                    "cash_available": "19949120",
                    "buying_power": "19949120",
                    "currency": "JPY",
                },
                "health": {
                    "orders": {"status": "PASS", "count": 1},
                    "positions": {"status": "PASS", "count": 1},
                    "executions": {
                        "status": "FAIL",
                        "count": 0,
                        "detail_attempted_count": 1,
                        "detail_success_count": 0,
                        "detail_failure_count": 1,
                        "failures": [
                            {
                                "classification": "FAILED_BROKER_READONLY_FETCH",
                                "failure_stage": "order_detail_response",
                                "result_code_present": True,
                                "result_code_zero": False,
                                "safe_error_class": "BrokerResponseEnvelope",
                            }
                        ],
                    },
                },
            },
        )
        _write_json(Path(kwargs["report_path"]), {"status": "FAILED_BROKER_READONLY_FETCH"})
        return type("SnapshotResult", (), {"status": "FAILED_BROKER_READONLY_FETCH"})()

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        snapshot_provider=fake_snapshot,
    )

    current = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    assert result.status == "PASS"
    assert result.execution_acceptance_status == "PASS"
    assert result.execution_acceptance_reason == "orderlist_position_cash_evidence_accepted"
    assert result.order_detail_required is False
    assert result.order_detail_status == "OPTIONAL_FAILED"
    assert result.execution_acceptance_warnings == ("order_detail_optional_missing",)
    assert result.positions_evidence_connected is True
    assert result.cash_evidence_connected is True
    assert result.ledger_executions_appended == 1
    assert result.execution_equivalent_count == 1
    assert result.asset_current_written is True
    assert result.asset_policy == "runtime_owned_fill_projection"
    assert result.runtime_owned_projection_status == "PASS"
    assert result.projected_position_count == 1
    assert result.projected_cash == 989_800
    assert result.projected_market_value == 235_000
    assert result.reconcile_status == "PASS_WITH_WARNINGS"
    assert current["cash"] == 989_800
    assert [position["symbol"] for position in current["positions"]] == ["6522"]
    executions = [
        json.loads(line)
        for line in (runtime_root / "persistent_ledger" / "executions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(executions) == 1
    execution = executions[0]
    assert execution["record_type"] == "execution"
    assert execution["execution_evidence_type"] == "execution_equivalent"
    assert execution["business_date"] == "2026-07-08"
    assert execution["symbol"] == "6522"
    assert execution["broker_issue_code"] == "6522"
    assert execution["side"] == "BUY"
    assert execution["quantity"] == 100
    assert execution["filled_quantity"] == 100
    assert execution["remaining_quantity"] == 0
    assert execution["order_status"] == "filled"
    assert execution["execution_status"] == "filled"
    assert execution["price_source"] == "position_evidence"
    assert execution["average_price"] == 102
    assert execution["market_value"] == 235000
    assert execution["detail_required"] is False
    assert execution["detail_status"] == "OPTIONAL_FAILED"
    assert "CLMOrderList" in execution["evidence_refs"]


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
