from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd

import ai_fund_lab_v2.paper_trading.unified_daily_runner as unified_module
from scripts.run_aifundlab_daily_paper_trading import resolve_jst_business_date
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PerformanceSnapshot, PositionSnapshot, write_ledger
from ai_fund_lab_v2.paper_trading.unified_daily_runner import UNIFIED_DAILY_RUNNER_BLOCKED, UNIFIED_DAILY_RUNNER_COMPLETED, run_unified_daily_paper_trading


def test_phase9w_date_omitted_uses_jst_today_business_date() -> None:
    resolved = resolve_jst_business_date(datetime(2026, 6, 18, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")))

    assert resolved == "2026-06-18"


def test_phase9w_allow_api_fetch_false_does_not_call_market_refresh(tmp_path: Path) -> None:
    ledger_path = _write_position_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path, "2026-06-18")

    def unexpected_refresh(**_: object) -> object:
        raise AssertionError("market refresh should not be called")

    result = run_unified_daily_paper_trading(
        run_date="2026-06-18",
        ledger_path=ledger_path,
        mode="dry-run",
        allow_api_fetch=False,
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
        market_data_refresh_runner=unexpected_refresh,
    )

    assert result.status == UNIFIED_DAILY_RUNNER_COMPLETED
    assert result.step_statuses["market_data_refresh"] == "SKIPPED_API_FETCH_NOT_ALLOWED"


def test_phase9w_allow_api_fetch_calls_refresh_and_updates_canonical(tmp_path: Path) -> None:
    ledger_path = _write_position_ledger(tmp_path)
    quotes_path = tmp_path / ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet"
    _write_quotes(tmp_path, "2026-06-17", path=quotes_path)
    refreshed_path = tmp_path / ".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet"
    refreshed_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"target_date": "2026-06-18", "Date": "2026-06-18", "Code": "10010", "Open": 1010, "High": 1012, "Low": 1009, "Close": 1010, "Volume": 1000}]
    ).to_parquet(refreshed_path, index=False)
    calls: list[dict[str, object]] = []

    def fake_refresh(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(
            status="COMPLETED",
            requested_from_date=kwargs["from_date"],
            requested_to_date=kwargs["to_date"],
            data_until="2026-06-18",
            latest_successful_daily_quotes_date="2026-06-18",
            latest_normalized_daily_quotes_date="2026-06-18",
            jquants_api_fetch_executed=True,
            warnings=(),
            blocked_reasons=(),
            endpoints=(SimpleNamespace(endpoint="daily_quotes", normalized_path=str(refreshed_path)),),
        )

    result = run_unified_daily_paper_trading(
        run_date="2026-06-18",
        ledger_path=ledger_path,
        mode="dry-run",
        allow_api_fetch=True,
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
        market_data_refresh_runner=fake_refresh,
    )
    canonical = pd.read_parquet(quotes_path)

    assert calls and calls[0]["from_date"] == "2026-06-18"
    assert calls[0]["to_date"] == "2026-06-18"
    assert result.status == UNIFIED_DAILY_RUNNER_COMPLETED
    assert result.step_statuses["canonical_normalized_update"] == "CANONICAL_NORMALIZED_UPDATED"
    assert result.business_dates.decision_for == "2026-06-18"
    assert str(canonical["date"].astype(str).min()) == "2026-06-17"
    assert str(canonical["date"].astype(str).max()) == "2026-06-18"
    assert {"date", "code", "open", "high", "low", "close", "volume"}.issubset(canonical.columns)


def test_phase9w_stale_valuation_blocks_tracker_and_marks_blog(tmp_path: Path) -> None:
    ledger_path = _write_position_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path, "2026-06-17")
    _write_minimal_blog_artifacts(tmp_path, "2026-06-18")

    result = run_unified_daily_paper_trading(
        run_date="2026-06-18",
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
    markdown = Path(result.blog_report_v2_markdown_path).read_text(encoding="utf-8")

    assert result.status == UNIFIED_DAILY_RUNNER_BLOCKED
    assert result.step_statuses["valuation_context"]["stale_price_source"] is True
    assert result.step_statuses["tracker_update"] == "SKIPPED_BLOCKED"
    assert result.step_statuses["blog_report_v2"] == "BLOG_REPORT_V2_STALE_PRICE_SOURCE"
    assert "DATA_NOT_READY / STALE_PRICE_SOURCE" in markdown
    assert "quote_source_max_date_stale:2026-06-17<valuation:2026-06-18" in result.blocked_reasons


def test_phase9w_feature_refresh_auto_executes_when_artifacts_missing_and_inference_continues(tmp_path: Path, monkeypatch) -> None:
    ledger_path = _write_position_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path, "2026-06-18")
    feature_calls: list[tuple[bool, bool, str]] = []

    def fake_feature_refresh(**kwargs: object) -> SimpleNamespace:
        feature_calls.append((bool(kwargs["dry_run"]), bool(kwargs["execute"]), str(kwargs["target_data_until"])))
        if kwargs["execute"]:
            return SimpleNamespace(
                status="FEATURES_READY",
                manifest_path=str(tmp_path / "feature_manifest.json"),
                warnings=(),
                blocked_reasons=(),
            )
        return SimpleNamespace(
            status="FEATURE_REFRESH_REQUIRED",
            manifest_path=str(tmp_path / "feature_audit_manifest.json"),
            warnings=(),
            blocked_reasons=("candidate_feature_artifact_missing",),
        )

    def fake_inference(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            status="INFERENCE_READY",
            manifest_path=str(tmp_path / "inference_manifest.json"),
            warnings=(),
            blocked_reasons=(),
        )

    monkeypatch.setattr(unified_module, "run_feature_refresh", fake_feature_refresh)
    monkeypatch.setattr(unified_module, "run_daily_inference", fake_inference)

    result = unified_module.run_unified_daily_paper_trading(
        run_date="2026-06-18",
        ledger_path=ledger_path,
        mode="dry-run",
        runtime_dir=tmp_path / ".runtime",
        operation_root=tmp_path / ".runtime" / "daily_operation",
        quotes_path=quotes_path,
        reports_root=tmp_path / "reports",
        phase_report_markdown_path=tmp_path / "phase9u.md",
        phase_report_json_path=tmp_path / "phase9u.json",
        skip_inference=False,
        skip_tracker_update=True,
        skip_blog_report_v2=True,
    )

    assert feature_calls == [(True, False, "2026-06-18"), (False, True, "2026-06-18")]
    assert result.status == UNIFIED_DAILY_RUNNER_COMPLETED
    assert result.step_statuses["feature_refresh_audit"] == "FEATURE_REFRESH_REQUIRED"
    assert result.step_statuses["feature_refresh_execute"] == "FEATURES_READY"
    assert result.step_statuses["feature_refresh"] == "FEATURES_READY"
    assert result.step_statuses["daily_inference"] == "INFERENCE_READY"


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


def _write_quotes(tmp_path: Path, day: str, *, path: Path | None = None) -> Path:
    output = path or tmp_path / "quotes.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    close = 1010 if day == "2026-06-18" else 990
    pd.DataFrame([{"date": day, "code": "10010", "open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1000}]).to_parquet(output, index=False)
    return output


def _write_minimal_blog_artifacts(tmp_path: Path, day: str) -> None:
    root = tmp_path / ".runtime" / "phase9" / "inference" / day
    root.mkdir(parents=True, exist_ok=True)
    rows = [{"rank": 1, "code": "10010", "issue_name": "", "public_confidence_score": 80, "short_reason": "公開用サンプルです。"}]
    (root / "candidate_artifact.json").write_text('{"rows":[{"rank":1,"code":"10010","public_confidence_score":80}]}', encoding="utf-8")
    (root / "opportunity_artifact.json").write_text('{"rows":[{"rank":1,"code":"10010","public_confidence_score":80}]}', encoding="utf-8")
    (root / "allocation_artifact.json").write_text('{"rows":[]}', encoding="utf-8")
    (root / "order_plan_artifact.json").write_text('{"items":[]}', encoding="utf-8")
