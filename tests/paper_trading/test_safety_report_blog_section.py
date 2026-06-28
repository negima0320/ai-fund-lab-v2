from decimal import Decimal

from ai_fund_lab_v2.paper_trading.daily_run_result import DailyCandidate, DailyPosition, DailyRunResult
from ai_fund_lab_v2.paper_trading.reporting.blog_draft_writer import render_blog_draft_markdown
from ai_fund_lab_v2.paper_trading.reporting.public_daily_report_writer import render_public_daily_report_markdown
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest


def test_public_daily_report_includes_safety_market_review_section():
    markdown = render_public_daily_report_markdown(manifest=_manifest(), result=_result(_market_stress_state()))
    assert "## Safety / Market Review" in markdown
    assert "Market Stress: yes" in markdown
    assert "Buy Opportunity Review: yes" in markdown
    assert "自動停止ではありません" in markdown
    assert "買い場候補として確認してください" in markdown
    assert "市場急落によりEmergency Stop" not in markdown
    assert "暴落のため自動売却" not in markdown


def test_blog_draft_includes_position_review_without_auto_sell():
    markdown = render_blog_draft_markdown(manifest=_manifest(), result=_result(_position_review_state()))
    assert "## Safety / Market Review" in markdown
    assert "Position Review: yes" in markdown
    assert "Sell Review Required: yes" in markdown
    assert "High Risk Review: yes" in markdown
    assert "Auto Sell Executed: false" in markdown
    assert "売却 / 保有 / 買い増しを確認してください" in markdown


def test_blog_public_section_marks_only_system_emergency_as_stop():
    markdown = render_public_daily_report_markdown(manifest=_manifest(), result=_result(_system_emergency_state()))
    assert "System Emergency: yes" in markdown
    assert "発注停止 / 人間確認必須" in markdown
    assert "Market Stress: no" in markdown


def _manifest() -> DailyRunManifest:
    return DailyRunManifest(
        run_date="2026-06-29",
        data_until="2026-06-29",
        train_until="2026-06-26",
        decision_for="2026-06-29",
        virtual_order_date="2026-06-30",
        virtual_execution_date="2026-06-30",
        safety_status="READY_FOR_REVIEW",
        human_review_status="pending",
        report_status="OK",
    )


def _result(safety_state):
    return DailyRunResult(
        buy_candidates=(DailyCandidate(issue_code="7203", issue_name="Toyota", side="BUY", public_confidence_score=70),),
        sell_candidates=(),
        hold_candidates=(DailyCandidate(issue_code="9432", issue_name="NTT", side="HOLD", public_confidence_score=60),),
        cash=Decimal("300000"),
        current_cash=Decimal("300000"),
        positions=(DailyPosition(issue_code="9432", issue_name="NTT", quantity=Decimal("100"), market_value=Decimal("16000")),),
        current_positions=(DailyPosition(issue_code="9432", issue_name="NTT", quantity=Decimal("100"), market_value=Decimal("16000")),),
        total_equity=Decimal("1016000"),
        unrealized_pnl=Decimal("4000"),
        trade_count=1,
        safety_state=safety_state,
    )


def _market_stress_state():
    return {
        "next_recommended_safety_state": "BUY_OPPORTUNITY_REVIEW",
        "market_stress": True,
        "buy_opportunity_review": True,
        "review_required_items": [{"reason_code": "BUY_OPPORTUNITY_REVIEW"}],
        "recommended_human_actions": ["買い場候補として確認してください"],
    }


def _position_review_state():
    return {
        "next_recommended_safety_state": "WARNING",
        "review_required_items": [{"reason_code": "SELL_REVIEW_REQUIRED"}, {"reason_code": "HIGH_RISK_REVIEW"}],
        "recommended_human_actions": ["売却 / 保有 / 買い増しを確認してください"],
    }


def _system_emergency_state():
    return {
        "next_recommended_safety_state": "SYSTEM_EMERGENCY_STOP",
        "system_emergency": True,
        "review_required_items": [{"reason_code": "DUPLICATE_ORDER_SYSTEM_EMERGENCY"}],
        "recommended_human_actions": ["Stop order flow and reconcile broker orders."],
    }
