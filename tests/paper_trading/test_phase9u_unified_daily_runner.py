from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, PerformanceSnapshot, PositionSnapshot, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.run_lock import RunLockError, acquire_run_lock
from ai_fund_lab_v2.paper_trading.unified_daily_runner import UNIFIED_DAILY_RUNNER_COMPLETED, run_unified_daily_paper_trading


def test_phase9u_dry_run_does_not_mutate_ledger(tmp_path: Path) -> None:
    ledger_path = _write_position_ledger(tmp_path)
    before = Path(ledger_path).read_text(encoding="utf-8")
    quotes_path = _write_quotes(tmp_path)

    result = run_unified_daily_paper_trading(
        run_date="2026-06-16",
        ledger_path=ledger_path,
        mode="dry-run",
        runtime_dir=tmp_path / ".runtime",
        operation_root=tmp_path / ".runtime" / "daily_operation",
        quotes_path=quotes_path,
        reports_root=tmp_path / "reports",
        phase_report_markdown_path=tmp_path / "phase9u.md",
        phase_report_json_path=tmp_path / "phase9u.json",
        skip_feature_refresh=True,
        skip_inference=True,
        skip_tracker_update=True,
        skip_blog_report_v2=True,
    )

    assert result.status == UNIFIED_DAILY_RUNNER_COMPLETED
    assert Path(ledger_path).read_text(encoding="utf-8") == before
    assert result.step_statuses["market_data_refresh"] == "SKIPPED_API_FETCH_NOT_ALLOWED"
    assert result.broker_order_api_called is False
    assert result.open_d_started is False
    assert result.unlock_trade_called is False


def test_phase9u_paper_trading_can_mutate_paper_ledger_by_valuation(tmp_path: Path) -> None:
    ledger_path = _write_position_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path)

    result = run_unified_daily_paper_trading(
        run_date="2026-06-16",
        ledger_path=ledger_path,
        mode="paper-trading",
        runtime_dir=tmp_path / ".runtime",
        operation_root=tmp_path / ".runtime" / "daily_operation",
        quotes_path=quotes_path,
        reports_root=tmp_path / "reports",
        phase_report_markdown_path=tmp_path / "phase9u.md",
        phase_report_json_path=tmp_path / "phase9u.json",
        skip_feature_refresh=True,
        skip_inference=True,
        skip_tracker_update=True,
        skip_blog_report_v2=True,
    )
    latest = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.status == UNIFIED_DAILY_RUNNER_COMPLETED
    assert latest.performance.total_equity == Decimal("999000")
    assert result.step_statuses["ledger_valuation"] == "LEDGER_VALUATION_UPDATED"
    assert Path(result.operation_log_json_path).is_file()


def test_phase9u_fill_step_runs_before_inference_step(tmp_path: Path) -> None:
    ledger_path = _write_pending_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path)

    result = run_unified_daily_paper_trading(
        run_date="2026-06-16",
        ledger_path=ledger_path,
        mode="dry-run",
        runtime_dir=tmp_path / ".runtime",
        operation_root=tmp_path / ".runtime" / "daily_operation",
        quotes_path=quotes_path,
        reports_root=tmp_path / "reports",
        phase_report_markdown_path=tmp_path / "phase9u.md",
        phase_report_json_path=tmp_path / "phase9u.json",
        skip_feature_refresh=True,
        skip_inference=True,
        skip_tracker_update=True,
        skip_blog_report_v2=True,
    )
    keys = list(result.step_statuses)

    assert result.step_statuses["virtual_fill"] == "FIRST_VIRTUAL_FILL_DRY_RUN"
    assert keys.index("virtual_fill") < keys.index("daily_inference")


def test_phase9u_blog_report_and_tracker_and_operation_log(tmp_path: Path) -> None:
    ledger_path = _write_position_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path)
    _write_minimal_blog_artifacts(tmp_path)

    result = run_unified_daily_paper_trading(
        run_date="2026-06-16",
        ledger_path=ledger_path,
        mode="report-only",
        approval_mode="review_only",
        runtime_dir=tmp_path / ".runtime",
        operation_root=tmp_path / ".runtime" / "daily_operation",
        quotes_path=quotes_path,
        reports_root=tmp_path / "reports",
        phase_report_markdown_path=tmp_path / "phase9u.md",
        phase_report_json_path=tmp_path / "phase9u.json",
        skip_feature_refresh=True,
        skip_inference=True,
    )

    assert result.step_statuses["tracker_update"] == "TRACKER_UPDATED"
    assert result.step_statuses["blog_report_v2"] == "BLOG_REPORT_V2_READY"
    assert Path(result.blog_report_v2_markdown_path).is_file()
    assert Path(result.operation_log_json_path).is_file()


def test_phase9u_run_lock_blocks_duplicate(tmp_path: Path) -> None:
    operation_root = tmp_path / ".runtime" / "daily_operation"
    acquire_run_lock(run_id="already_running", run_date="2026-06-16", mode="dry-run", operation_root=operation_root)

    with pytest.raises(RunLockError):
        run_unified_daily_paper_trading(
            run_date="2026-06-16",
            ledger_path=_write_position_ledger(tmp_path),
            mode="dry-run",
            operation_root=operation_root,
            skip_feature_refresh=True,
            skip_inference=True,
            skip_tracker_update=True,
            skip_blog_report_v2=True,
            phase_report_markdown_path=tmp_path / "phase9u.md",
            phase_report_json_path=tmp_path / "phase9u.json",
        )


def _write_position_ledger(tmp_path: Path) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("900000"),
        positions=(PositionSnapshot(code="10010", quantity=Decimal("100"), average_cost=Decimal("1000"), market_value=Decimal("100000")),),
        performance=PerformanceSnapshot(
            total_equity=Decimal("1000000"),
            cash=Decimal("900000"),
            market_value=Decimal("100000"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            trade_count=1,
        ),
    )
    return write_ledger(ledger, runtime_dir=tmp_path / ".runtime")


def _write_pending_ledger(tmp_path: Path) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("1000000"),
        pending_orders=(PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-16"),),
    )
    return write_ledger(ledger, runtime_dir=tmp_path / ".runtime")


def _write_quotes(tmp_path: Path) -> Path:
    path = tmp_path / "quotes.parquet"
    pd.DataFrame([{"date": "2026-06-16", "code": "10010", "open": 1000, "close": 990}]).to_parquet(path, index=False)
    return path


def _write_minimal_blog_artifacts(tmp_path: Path) -> None:
    day = tmp_path / ".runtime" / "phase9" / "inference" / "2026-06-16"
    day.mkdir(parents=True)
    rows = [{"rank": 1, "code": "10010", "issue_name": "", "public_confidence_score": 80, "short_reason": "公開用サンプルです。"}]
    (day / "candidate_artifact.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    (day / "opportunity_artifact.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    (day / "allocation_artifact.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    (day / "order_plan_artifact.json").write_text(json.dumps({"items": rows}), encoding="utf-8")
