from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.operations.io import OperationPaths, write_json
from ai_fund_lab_v2.operations.operations import (
    INCOMPLETE_OPERATION_DAY,
    MARKET_CLOSED_DAY,
    NORMAL_OPERATION_DAY,
    RECOVERY_DAY,
    _market_calendar,
    _operation_flow_integrity_guard,
)


def _guard(root: Path, trade_date: str, statuses: dict[str, str], order_plan: dict) -> dict:
    paths = OperationPaths(root)
    return _operation_flow_integrity_guard(
        paths,
        trade_date,
        market_calendar=_market_calendar(paths, trade_date),
        status_refs=statuses,
        current_status_refs=statuses,
        order_plan=order_plan,
    )


def test_business_day_with_daily_plan_skipped_is_incomplete(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    order_plan = {"status": "PASS", "feature_candidate_audit": {"candidate_count": 10, "candidate_feature_path": str(tmp_path / "features.parquet")}}
    (tmp_path / "features.parquet").write_text("placeholder", encoding="utf-8")
    statuses = {"market_refresh": "PASS", "daily_plan": "SKIPPED_MARKET_CLOSED", "approval": "MISSING", "submit": "MISSING", "fill_monitor": "PASS", "safety_monitor": "PASS", "reconcile": "PASS", "operation_audit": "PASS"}

    guard = _guard(tmp_path, "2026-07-01", statuses, order_plan)

    assert guard["operation_day_type"] == INCOMPLETE_OPERATION_DAY
    assert guard["normal_report_allowed"] is False


def test_recovery_metadata_marks_recovery_day(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    write_json(paths.dated("daily_manifest", "2026-07-01", "daily_manifest.json"), {"business_date": "2026-07-01", "recovery_day": True})
    feature = tmp_path / "features.parquet"
    feature.write_text("placeholder", encoding="utf-8")
    order_plan = {"status": "PASS", "feature_candidate_audit": {"candidate_count": 10, "candidate_feature_path": str(feature)}}
    statuses = {"market_refresh": "PASS", "daily_plan": "PASS", "approval": "APPROVED", "submit": "PASS", "fill_monitor": "PASS", "safety_monitor": "PASS", "reconcile": "PASS", "operation_audit": "PASS"}

    guard = _guard(tmp_path, "2026-07-01", statuses, order_plan)

    assert guard["operation_day_type"] == RECOVERY_DAY
    assert guard["report_mode"] == "RECOVERY_REPORT"


def test_market_closed_day_classification(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    guard = _guard(tmp_path, "2026-09-21", {}, {})

    assert guard["operation_day_type"] == MARKET_CLOSED_DAY
    assert guard["candidate_top50_allowed"] is False


def test_full_pass_business_day_is_normal_operation_day(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    paths = OperationPaths(tmp_path)
    feature = tmp_path / "features.parquet"
    feature.write_text("placeholder", encoding="utf-8")
    write_json(paths.dated("order_plan", "2026-07-01", "order_plan.json"), {"business_date": "2026-07-01", "status": "PASS"})
    order_plan = {"status": "PASS", "feature_candidate_audit": {"candidate_count": 10, "candidate_feature_path": str(feature)}}
    statuses = {"market_refresh": "PASS", "daily_plan": "PASS", "approval": "APPROVED", "submit": "PASS", "fill_monitor": "PASS", "safety_monitor": "PASS", "reconcile": "PASS", "operation_audit": "PASS"}

    guard = _guard(tmp_path, "2026-07-01", statuses, order_plan)

    assert guard["operation_day_type"] == NORMAL_OPERATION_DAY
    assert guard["normal_report_allowed"] is True
