from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.paper_trading.daily_run_result import DailyCandidate, DailyPosition, DailyRunResult
from ai_fund_lab_v2.paper_trading.reporting.blog_draft_writer import write_blog_draft
from ai_fund_lab_v2.paper_trading.reporting.internal_daily_report_writer import write_internal_daily_report
from ai_fund_lab_v2.paper_trading.reporting.public_daily_report_writer import write_public_daily_report
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest


def test_report_writers_create_internal_public_and_blog_outputs(tmp_path: Path) -> None:
    manifest = _manifest()
    result = _result()

    internal_md, internal_json = write_internal_daily_report(manifest=manifest, result=result, reports_dir=tmp_path / "internal")
    public_md = write_public_daily_report(manifest=manifest, result=result, reports_dir=tmp_path / "public")
    blog_md = write_blog_draft(manifest=manifest, result=result, reports_dir=tmp_path / "public")

    assert internal_md.exists()
    assert internal_json.exists()
    assert public_md.exists()
    assert blog_md.exists()
    assert "BUY" in internal_md.read_text(encoding="utf-8")
    public_text = public_md.read_text(encoding="utf-8")
    assert "AI信頼度: 81/100" in public_text
    assert "投資助言ではありません" in public_text
    blog_text = blog_md.read_text(encoding="utf-8")
    assert "仮想運用 / 検証中 / 投資判断は自己責任" in blog_text


def _manifest() -> DailyRunManifest:
    return DailyRunManifest(
        run_date="2026-06-16",
        data_until="2026-06-16",
        train_until="2026-06-12",
        decision_for="2026-06-16",
        virtual_order_date="2026-06-17",
        virtual_execution_date="2026-06-17",
        safety_status="OK",
        human_review_status="pending",
        report_status="OK",
    )


def _result() -> DailyRunResult:
    return DailyRunResult(
        buy_candidates=(
            DailyCandidate(
                issue_code="7203",
                issue_name="Toyota Motor",
                side="BUY",
                public_confidence_score=81,
                short_reason="トレンドと流動性が比較的良好です。",
                caution_note="仮想運用での検証中です。",
            ),
        ),
        sell_candidates=(DailyCandidate(issue_code="6758", issue_name="Sony Group", side="SELL", public_confidence_score=44),),
        hold_candidates=(DailyCandidate(issue_code="9432", issue_name="NTT", side="HOLD", public_confidence_score=66),),
        cash=Decimal("250000"),
        positions=(DailyPosition(issue_code="9432", issue_name="NTT", quantity=Decimal("100"), market_value=Decimal("16000")),),
        total_equity=Decimal("1016000"),
        realized_pnl=Decimal("12000"),
        unrealized_pnl=Decimal("4000"),
        trade_count=3,
        safety_state={"status": "OK"},
        review_state={"status": "pending"},
    )

