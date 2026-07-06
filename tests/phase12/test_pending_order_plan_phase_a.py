from __future__ import annotations

import inspect
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_fund_lab_v2.operations import operations
from ai_fund_lab_v2.operations.io import OperationPaths, read_json, stable_hash, write_json
from ai_fund_lab_v2.operations.operations import run_daily_plan
from ai_fund_lab_v2.operations.pending_order_plan import (
    build_pending_order_plan,
    pending_order_plan_path,
    read_pending_order_plan,
    validate_pending_order_plan,
    write_pending_order_plan,
)


JST = ZoneInfo("Asia/Tokyo")


def test_pending_order_plan_writer_reader_schema_hash_and_safety(tmp_path: Path) -> None:
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
    result = write_pending_order_plan(tmp_path, pending)
    loaded = read_pending_order_plan(tmp_path)

    assert result["validation"]["status"] == "PASS"
    assert loaded["artifact_type"] == "pending_order_plan"
    assert loaded["schema_version"] == 1
    assert loaded["state"] == "PENDING_APPROVAL"
    assert loaded["plan_created_date"] == "2026-07-03"
    assert loaded["intended_submit_date"] == "2026-07-06"
    assert loaded["target_session_date"] == "2026-07-06"
    assert loaded["source_order_plan"]["path"] == "order_plan/2026-07-03/order_plan.json"
    assert loaded["source_order_plan"]["hash"] == stable_hash(order_plan)
    assert loaded["submit_constraints"]["allow_dated_order_plan_fallback"] is False
    assert loaded["raw_request_saved"] is False
    assert loaded["raw_response_saved"] is False
    assert loaded["secret_saved"] is False
    assert validate_pending_order_plan(loaded)["status"] == "PASS"
    assert Path(result["history_path"]).exists()


def test_daily_plan_promotes_friday_evening_pending_for_monday(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setattr(
        "ai_fund_lab_v2.operations.pending_order_plan.current_jst",
        lambda: datetime(2026, 7, 3, 19, 0, tzinfo=JST),
    )
    _write_market_gate(paths := OperationPaths(tmp_path), "2026-07-03")

    result = run_daily_plan(
        trade_date="2026-07-03",
        root=tmp_path,
        plan_items=[_plan_item("buy_2026-07-03_65220_001", "65220")],
    )
    pending = read_pending_order_plan(tmp_path)

    assert result["status"] == "PASS"
    assert result["pending_order_plan_promotion"]["promoted"] is True
    assert pending["plan_created_date"] == "2026-07-03"
    assert pending["intended_submit_date"] == "2026-07-06"
    assert pending["target_session_date"] == "2026-07-06"
    assert pending["promotion"]["promotion_policy"] == "after_close_next_business_session_only"
    assert pending["source_order_plan"]["buy_item_count"] == 1
    assert pending_order_plan_path(tmp_path).exists()


def test_daily_plan_morning_manual_run_does_not_promote_pending(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setattr(
        "ai_fund_lab_v2.operations.pending_order_plan.current_jst",
        lambda: datetime(2026, 7, 3, 8, 0, tzinfo=JST),
    )
    _write_market_gate(OperationPaths(tmp_path), "2026-07-03")

    result = run_daily_plan(
        trade_date="2026-07-03",
        root=tmp_path,
        plan_items=[_plan_item("buy_2026-07-03_65220_001", "65220")],
    )

    assert result["status"] == "PASS"
    assert result["pending_order_plan_promotion"]["promoted"] is False
    assert result["pending_order_plan_promotion"]["blocked_reason"] == "before_market_close_planning_cutoff"
    assert not pending_order_plan_path(tmp_path).exists()
    assert (tmp_path / "order_plan" / "2026-07-03" / "order_plan.json").exists()


def test_daily_plan_does_not_promote_when_unconsumed_pending_conflicts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setattr(
        "ai_fund_lab_v2.operations.pending_order_plan.current_jst",
        lambda: datetime(2026, 7, 3, 19, 0, tzinfo=JST),
    )
    paths = OperationPaths(tmp_path)
    _write_market_gate(paths, "2026-07-03")
    existing_order_plan = _order_plan(trade_date="2026-07-02", plan_id="operation_plan_2026-07-02_existing")
    existing_path = paths.dated("order_plan", "2026-07-02", "order_plan.json")
    write_json(existing_path, existing_order_plan)
    existing = build_pending_order_plan(
        root=tmp_path,
        order_plan=existing_order_plan,
        order_plan_path=existing_path,
        plan_created_date="2026-07-02",
        intended_submit_date="2026-07-06",
        target_session_date="2026-07-06",
        promotion_source="test",
    )
    existing["state"] = "APPROVED"
    write_pending_order_plan(tmp_path, existing)

    result = run_daily_plan(
        trade_date="2026-07-03",
        root=tmp_path,
        plan_items=[_plan_item("buy_2026-07-03_65220_001", "65220")],
    )
    loaded = read_pending_order_plan(tmp_path)

    assert result["pending_order_plan_promotion"]["promoted"] is False
    assert result["pending_order_plan_promotion"]["blocked_reason"] == "unconsumed_pending_order_plan_conflict"
    assert loaded["pending_plan_id"] == existing["pending_plan_id"]
    assert loaded["state"] == "APPROVED"


def test_submit_mainline_is_not_connected_to_pending_order_plan() -> None:
    source = inspect.getsource(operations.run_submit_operation)
    assert "_resolve_submit_order_plan_date" not in source
    assert "load_pending_order_plan_for_submit" in source


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
