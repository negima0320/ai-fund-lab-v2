from __future__ import annotations

import inspect
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_fund_lab_v2.operations import operations
from ai_fund_lab_v2.operations.io import OperationPaths, read_json, stable_hash, write_json
from ai_fund_lab_v2.operations.operations import run_approval_prepare, run_daily_plan
from ai_fund_lab_v2.operations.pending_order_plan import (
    build_pending_order_plan,
    link_approval_to_pending_order_plan,
    read_pending_order_plan,
    write_pending_order_plan,
)


JST = ZoneInfo("Asia/Tokyo")


def test_approval_approved_updates_pending_state_and_hashes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setattr(
        "ai_fund_lab_v2.operations.pending_order_plan.current_jst",
        lambda: datetime(2026, 7, 3, 19, 0, tzinfo=JST),
    )
    paths = OperationPaths(tmp_path)
    _write_market_gate(paths, "2026-07-03")
    run_daily_plan(
        trade_date="2026-07-03",
        root=tmp_path,
        plan_items=[_plan_item("buy_2026-07-03_65220_001", "65220")],
    )

    result = run_approval_prepare(trade_date="2026-07-03", root=tmp_path, auto_demo_approval=True)
    pending = read_pending_order_plan(tmp_path)
    approval_path = paths.dated("approval_artifact", "2026-07-03", "approval_artifact.json")
    approval = read_json(approval_path)

    assert result["pending_order_plan_approval_linkage"]["linked"] is True
    assert pending["state"] == "APPROVED"
    assert pending["approval"]["status"] == "APPROVED"
    assert pending["approval"]["approval_id"] == approval["approval_id"]
    assert pending["approval"]["path"] == "approval_artifact/2026-07-03/approval_artifact.json"
    assert pending["approval"]["hash"] == stable_hash(approval)
    assert pending["approval"]["approved_item_ids"] == approval["approved_item_ids"]
    assert pending["approval"]["approval_expires_at"] == approval["approval_expires_at"]
    assert pending["approval"]["approval_max_notional"] == approval["approval_max_notional"]
    assert pending["approval"]["approval_max_notional_source"] == approval["approval_max_notional_source"]
    assert pending["approval"]["source_order_plan_hash"] == pending["source_order_plan"]["hash"]
    assert pending["submit_constraints"]["allow_dated_order_plan_fallback"] is False
    assert pending["raw_request_saved"] is False
    assert pending["raw_response_saved"] is False
    assert pending["secret_saved"] is False
    assert approval_path.exists()


def test_approval_linkage_hash_mismatch_does_not_approve_pending(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setattr(
        "ai_fund_lab_v2.operations.pending_order_plan.current_jst",
        lambda: datetime(2026, 7, 3, 19, 0, tzinfo=JST),
    )
    paths = OperationPaths(tmp_path)
    _write_market_gate(paths, "2026-07-03")
    run_daily_plan(
        trade_date="2026-07-03",
        root=tmp_path,
        plan_items=[_plan_item("buy_2026-07-03_65220_001", "65220")],
    )
    order_plan_path = paths.dated("order_plan", "2026-07-03", "order_plan.json")
    order_plan = read_json(order_plan_path)
    order_plan["items"][0]["quantity"] = "200"
    write_json(order_plan_path, order_plan)

    result = run_approval_prepare(trade_date="2026-07-03", root=tmp_path, auto_demo_approval=True)
    pending = read_pending_order_plan(tmp_path)

    assert result["pending_order_plan_approval_linkage"]["linked"] is False
    assert pending["state"] == "BLOCKED"
    assert "source_order_plan_hash_mismatch" in pending["approval"]["linkage_reasons"]


def test_approval_linkage_item_id_mismatch_does_not_approve_pending(tmp_path: Path) -> None:
    paths = OperationPaths(tmp_path)
    trade_date = "2026-07-03"
    order_plan = _order_plan(trade_date=trade_date, plan_id="operation_plan_2026-07-03_test")
    order_plan_path = paths.dated("order_plan", trade_date, "order_plan.json")
    write_json(order_plan_path, order_plan)
    pending = build_pending_order_plan(
        root=tmp_path,
        order_plan=order_plan,
        order_plan_path=order_plan_path,
        plan_created_date=trade_date,
        intended_submit_date="2026-07-06",
        target_session_date="2026-07-06",
        promotion_source="test",
    )
    write_pending_order_plan(tmp_path, pending)
    approval = {
        "artifact_type": "approval_artifact",
        "approval_id": "approval_test",
        "status": "APPROVED",
        "plan_id": order_plan["plan_id"],
        "approved_item_ids": ["missing_item"],
        "approval_expires_at": "2026-07-04T00:00:00+00:00",
        "approval_max_notional": "850000",
        "approval_max_notional_source": "dynamic_max_exposure",
        "production_order_allowed": False,
    }
    approval_path = paths.dated("approval_artifact", trade_date, "approval_artifact.json")
    write_json(approval_path, approval)

    result = link_approval_to_pending_order_plan(
        root=tmp_path,
        order_plan=order_plan,
        order_plan_path=order_plan_path,
        approval=approval,
        approval_path=approval_path,
    )
    loaded = read_pending_order_plan(tmp_path)

    assert result["linked"] is False
    assert loaded["state"] == "BLOCKED"
    assert "approved_item_ids_not_in_pending_items" in loaded["approval"]["linkage_reasons"]


def test_approval_review_required_blocks_pending(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setattr(
        "ai_fund_lab_v2.operations.pending_order_plan.current_jst",
        lambda: datetime(2026, 7, 3, 19, 0, tzinfo=JST),
    )
    paths = OperationPaths(tmp_path)
    _write_market_gate(paths, "2026-07-03")
    run_daily_plan(
        trade_date="2026-07-03",
        root=tmp_path,
        plan_items=[_plan_item("buy_2026-07-03_65220_001", "65220")],
    )

    result = run_approval_prepare(
        trade_date="2026-07-03",
        root=tmp_path,
        auto_demo_approval=True,
        max_notional=Decimal("120000"),
    )
    pending = read_pending_order_plan(tmp_path)

    assert result["approved"] is False
    assert pending["state"] == "BLOCKED"
    assert pending["approval"]["status"] == "REVIEW_REQUIRED"
    assert pending["state"] != "APPROVED"


def test_approval_prepare_without_pending_keeps_dated_approval_behavior(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    _write_market_gate(paths, "2026-07-03")
    order_plan = _order_plan(trade_date="2026-07-03", plan_id="operation_plan_2026-07-03_test")
    write_json(paths.dated("order_plan", "2026-07-03", "order_plan.json"), order_plan)

    result = run_approval_prepare(trade_date="2026-07-03", root=tmp_path, auto_demo_approval=True)

    assert result["approved"] is True
    assert result["pending_order_plan_approval_linkage"]["status"] == "SKIPPED_PENDING_MISSING"
    assert paths.dated("approval_artifact", "2026-07-03", "approval_artifact.json").exists()


def test_submit_mainline_remains_unconnected_to_pending_after_phase_b() -> None:
    source = inspect.getsource(operations.run_submit_operation)
    assert "_resolve_submit_order_plan_date" not in source
    assert "load_pending_order_plan_for_submit" in source
    assert "link_approval_to_pending_order_plan" not in source


def _write_market_gate(paths: OperationPaths, trade_date: str) -> None:
    feature_path = paths.dated("feature_artifacts", trade_date, "candidate_features.parquet")
    feature_path.write_bytes(b"placeholder")
    write_json(
        paths.dated("market_refresh", trade_date, "market_refresh_manifest.json"),
        {
            "business_date": trade_date,
            "status": "PASS",
            "data_until": trade_date,
            "latest_available_market_date": trade_date,
            "feature_freshness_status": "PASS",
            "ai_feature_contamination_audit": {"status": "PASS"},
        },
    )
    write_json(
        paths.dated("feature_refresh", trade_date, "feature_refresh_manifest.json"),
        {
            "business_date": trade_date,
            "status": "PASS",
            "data_until": trade_date,
            "latest_available_market_date": trade_date,
            "feature_freshness_status": "PASS",
            "latest_feature_path": str(feature_path),
            "ai_feature_contamination_audit": {"status": "PASS"},
        },
    )


def _order_plan(*, trade_date: str, plan_id: str) -> dict[str, object]:
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
        "items": [_plan_item(f"buy_{trade_date}_65220_001", "65220")],
        "buy_item_count": 1,
        "sell_item_count": 0,
    }


def _plan_item(item_id: str, issue_code: str) -> dict[str, str]:
    return {
        "item_id": item_id,
        "issue_code": issue_code,
        "code": issue_code,
        "name": "Test",
        "side": "BUY",
        "quantity": "100",
        "limit_price": "1000",
        "expected_notional": "100000",
        "estimated_value": "100000",
    }
