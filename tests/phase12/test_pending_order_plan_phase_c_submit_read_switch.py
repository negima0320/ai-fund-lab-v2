from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ai_fund_lab_v2.operations import operations
from ai_fund_lab_v2.operations.io import OperationPaths, read_json, stable_hash, write_json
from ai_fund_lab_v2.operations.operations import run_submit_operation
from ai_fund_lab_v2.operations.pending_order_plan import (
    build_pending_order_plan,
    read_pending_order_plan,
    write_pending_order_plan,
)


SUBMIT_DATE = "2026-07-06"
PLAN_DATE = "2026-07-03"


def test_submit_reads_approved_pending_and_writes_pending_metadata(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    _write_approved_pending(tmp_path)

    result = run_submit_operation(trade_date=SUBMIT_DATE, root=tmp_path, execute_order=False)

    assert result["status"] == "PASS"
    assert result["submit_source"] == "pending_order_plan"
    assert result["dated_order_plan_fallback_used"] is False
    assert result["uses_pending_order_plan"] is True
    assert result["uses_previous_business_day_order_plan"] is False
    assert result["pending_plan_id"].startswith("pending_2026-07-03_")
    assert result["plan_created_date"] == PLAN_DATE
    assert result["intended_submit_date"] == SUBMIT_DATE
    assert result["target_session_date"] == SUBMIT_DATE
    assert result["source_order_plan"]["path"] == "order_plan/2026-07-03/order_plan.json"
    assert result["approval"]["path"] == "approval_artifact/2026-07-03/approval_artifact.json"
    assert result["submitted_orders"][0]["status"] == "DRY_RUN_READY"
    assert result["broker_order_api_called"] is False
    written = read_json(Path(result["submitted_orders_path"]))
    assert written["submit_source"] == "pending_order_plan"
    assert written["dated_order_plan_fallback_used"] is False
    assert written["secret_saved"] is False
    assert written["raw_response_saved"] is False


def test_submit_blocks_when_pending_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")

    result = run_submit_operation(trade_date=SUBMIT_DATE, root=tmp_path, execute_order=False)

    assert result["status"] == "BLOCK"
    assert "pending_order_plan_missing" in result["blocks"]
    assert result["dated_order_plan_fallback_used"] is False
    assert result["submitted_orders"] == []


def test_submit_blocks_when_pending_state_not_approved(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    _write_approved_pending(tmp_path, pending_state="PENDING_APPROVAL")

    result = run_submit_operation(trade_date=SUBMIT_DATE, root=tmp_path, execute_order=False)

    assert result["status"] == "BLOCK"
    assert "pending_state_not_approved:PENDING_APPROVAL" in result["blocks"]


def test_submit_blocks_on_intended_or_target_date_mismatch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    _write_approved_pending(tmp_path, intended_submit_date="2026-07-07", target_session_date="2026-07-08")

    result = run_submit_operation(trade_date=SUBMIT_DATE, root=tmp_path, execute_order=False)

    assert result["status"] == "BLOCK"
    assert "intended_submit_date_mismatch" in result["blocks"]
    assert "target_session_date_mismatch" in result["blocks"]


def test_submit_blocks_on_approval_hash_mismatch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    _write_approved_pending(tmp_path)
    approval_path = paths.dated("approval_artifact", PLAN_DATE, "approval_artifact.json")
    approval = read_json(approval_path)
    approval["approval_max_notional"] = "1"
    write_json(approval_path, approval)

    result = run_submit_operation(trade_date=SUBMIT_DATE, root=tmp_path, execute_order=False)

    assert result["status"] == "BLOCK"
    assert "approval_hash_mismatch" in result["blocks"]


def test_submit_blocks_on_order_plan_hash_mismatch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    _write_approved_pending(tmp_path)
    order_plan_path = paths.dated("order_plan", PLAN_DATE, "order_plan.json")
    order_plan = read_json(order_plan_path)
    order_plan["items"][0]["quantity"] = "200"
    write_json(order_plan_path, order_plan)

    result = run_submit_operation(trade_date=SUBMIT_DATE, root=tmp_path, execute_order=False)

    assert result["status"] == "BLOCK"
    assert "source_order_plan_hash_mismatch" in result["blocks"]


def test_submit_blocks_on_approved_item_id_mismatch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    pending = _write_approved_pending(tmp_path)
    pending["approval"]["approved_item_ids"] = ["missing_item"]
    write_pending_order_plan(tmp_path, pending)

    result = run_submit_operation(trade_date=SUBMIT_DATE, root=tmp_path, execute_order=False)

    assert result["status"] == "BLOCK"
    assert "pending_approved_item_ids_not_in_pending_items" in result["blocks"]


def test_submit_blocks_on_expired_approval(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    pending = _write_approved_pending(tmp_path)
    expired = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    approval_path = paths.dated("approval_artifact", PLAN_DATE, "approval_artifact.json")
    approval = read_json(approval_path)
    approval["approval_expires_at"] = expired
    write_json(approval_path, approval)
    pending["approval"]["approval_expires_at"] = expired
    pending["approval"]["hash"] = stable_hash(approval)
    write_pending_order_plan(tmp_path, pending)

    result = run_submit_operation(trade_date=SUBMIT_DATE, root=tmp_path, execute_order=False)

    assert result["status"] == "BLOCK"
    assert "approval_expired" in result["blocks"]


def test_submit_blocks_consumed_pending(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    _write_approved_pending(tmp_path, pending_state="CONSUMED")

    result = run_submit_operation(trade_date=SUBMIT_DATE, root=tmp_path, execute_order=False)

    assert result["status"] == "BLOCK"
    assert "pending_state_terminal:consumed" in result["blocks"]


def test_submit_review_required_for_stale_submitting_pending(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    pending = _write_approved_pending(tmp_path, pending_state="SUBMITTING")
    pending["updated_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    write_pending_order_plan(tmp_path, pending)

    result = run_submit_operation(trade_date=SUBMIT_DATE, root=tmp_path, execute_order=False)

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["submitted_orders"] == []
    assert "pending_state_submitting_stale" in result["review_required_reasons"]


def test_submit_ignores_current_dated_plan_when_pending_is_previous_business_source(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    _write_approved_pending(tmp_path)
    current_order_plan = _order_plan(
        trade_date=SUBMIT_DATE,
        plan_id="operation_plan_2026-07-06_wrong",
        item_id="buy_2026-07-06_99990_001",
        issue_code="99990",
    )
    current_order_plan_path = paths.dated("order_plan", SUBMIT_DATE, "order_plan.json")
    write_json(current_order_plan_path, current_order_plan)
    current_approval = _approval(
        plan_id=current_order_plan["plan_id"],
        approved_item_ids=["buy_2026-07-06_99990_001"],
    )
    write_json(paths.dated("approval_artifact", SUBMIT_DATE, "approval_artifact.json"), current_approval)

    result = run_submit_operation(trade_date=SUBMIT_DATE, root=tmp_path, execute_order=False)

    assert result["status"] == "PASS"
    assert result["source_order_plan"]["path"] == "order_plan/2026-07-03/order_plan.json"
    assert result["submitted_orders"][0]["issue_code"] == "65220"
    assert result["dated_order_plan_fallback_used"] is False


def test_submit_mainline_no_longer_calls_resolve_submit_order_plan_date() -> None:
    source = inspect.getsource(operations.run_submit_operation)
    assert "_resolve_submit_order_plan_date" not in source
    assert "load_pending_order_plan_for_submit" in source


def _write_approved_pending(
    root: Path,
    *,
    pending_state: str = "APPROVED",
    intended_submit_date: str = SUBMIT_DATE,
    target_session_date: str = SUBMIT_DATE,
) -> dict[str, object]:
    paths = OperationPaths(root)
    order_plan = _order_plan(
        trade_date=PLAN_DATE,
        plan_id="operation_plan_2026-07-03_test",
        item_id="buy_2026-07-03_65220_001",
        issue_code="65220",
    )
    order_plan_path = paths.dated("order_plan", PLAN_DATE, "order_plan.json")
    write_json(order_plan_path, order_plan)
    approval = _approval(plan_id=order_plan["plan_id"], approved_item_ids=["buy_2026-07-03_65220_001"])
    approval_path = paths.dated("approval_artifact", PLAN_DATE, "approval_artifact.json")
    write_json(approval_path, approval)
    pending = build_pending_order_plan(
        root=root,
        order_plan=order_plan,
        order_plan_path=order_plan_path,
        plan_created_date=PLAN_DATE,
        intended_submit_date=intended_submit_date,
        target_session_date=target_session_date,
        promotion_source="test",
    )
    pending["state"] = pending_state
    pending["approval"].update(
        {
            "status": "APPROVED",
            "approval_id": approval["approval_id"],
            "path": "approval_artifact/2026-07-03/approval_artifact.json",
            "hash": stable_hash(approval),
            "approved_item_ids": approval["approved_item_ids"],
            "approval_expires_at": approval["approval_expires_at"],
            "approval_max_notional": approval["approval_max_notional"],
            "approval_max_notional_source": approval["approval_max_notional_source"],
            "source_order_plan_hash": stable_hash(order_plan),
        }
    )
    write_pending_order_plan(root, pending)
    return read_pending_order_plan(root)


def _order_plan(*, trade_date: str, plan_id: str, item_id: str, issue_code: str) -> dict[str, object]:
    return {
        "artifact_type": "order_plan",
        "plan_id": plan_id,
        "created_at": "2026-07-03T10:00:00+00:00",
        "environment": "demo",
        "business_date": trade_date,
        "status": "PASS",
        "requires_approval": True,
        "production_order_allowed": False,
        "demo_order_allowed": False,
        "items": [
            {
                "item_id": item_id,
                "issue_code": issue_code,
                "code": issue_code,
                "name": "Test",
                "side": "BUY",
                "order_type": "CASH_EQUITY",
                "price_type": "LIMIT",
                "quantity": "100",
                "limit_price": "1000",
                "expected_notional": "100000",
                "estimated_value": "100000",
            }
        ],
        "buy_item_count": 1,
        "sell_item_count": 0,
    }


def _approval(*, plan_id: str, approved_item_ids: list[str]) -> dict[str, object]:
    return {
        "artifact_type": "approval_artifact",
        "approval_id": "operation_approval_test",
        "environment": "demo",
        "business_date": PLAN_DATE,
        "plan_id": plan_id,
        "approved_item_ids": approved_item_ids,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "approval_expires_at": (datetime.now(timezone.utc) + timedelta(hours=16)).isoformat(),
        "approval_source": "demo_auto_approval",
        "demo_order_allowed": True,
        "production_order_allowed": False,
        "max_notional": "850000",
        "approval_max_notional": "850000",
        "approval_max_notional_source": "dynamic_max_exposure",
        "status": "APPROVED",
    }
