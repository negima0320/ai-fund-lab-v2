from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.paper_trading.daily_run_result import DailyRunResult
from ai_fund_lab_v2.paper_trading.reporting.public_daily_report_writer import DISCLAIMER
from ai_fund_lab_v2.paper_trading.reporting.public_confidence_mapper import map_candidate_public_confidence
from ai_fund_lab_v2.paper_trading.reporting.redaction_checker import assert_public_report_ready
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest
from ai_fund_lab_v2.safety_phase11.public_report_section import render_safety_market_review_section


def write_blog_draft(
    *,
    manifest: DailyRunManifest,
    result: DailyRunResult,
    reports_dir: Path | str = "reports/public/phase9_daily",
) -> Path:
    markdown = render_blog_draft_markdown(manifest=manifest, result=result)
    assert_public_report_ready(markdown)
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{manifest.run_date}_blog_draft.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def render_blog_draft_markdown(*, manifest: DailyRunManifest, result: DailyRunResult) -> str:
    lines = [
        f"# AI Fund Lab Phase9 仮想運用メモ {manifest.run_date}",
        "",
        "## 今日のAI判断",
        "",
        "Phase9では、毎営業日のAI判断を仮想運用として検証しています。",
        "",
        "## 資産推移",
        "",
        f"- 仮想資産: {result.total_equity}",
        f"- 評価損益: {result.unrealized_pnl}",
        f"- 売買回数: {result.trade_count}",
        "",
        "## 注目銘柄",
        "",
        _notable_symbols(result),
        "",
        "## 所感",
        "",
        "本日はAI判断の読みやすさ、Safety状態、Human Reviewの運用確認を中心に見ています。",
        "",
        render_safety_market_review_section(result.safety_state),
        "",
        "## 翌営業日の注目点",
        "",
        f"- 仮想約定予定日: {manifest.virtual_execution_date}",
        "- No Fill条件に該当する銘柄がないか確認",
        "- Human Reviewの判断が運用上わかりやすいか確認",
        "",
        "## 注意書き",
        "",
        "仮想運用 / 検証中 / 投資判断は自己責任",
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines) + "\n"


def _notable_symbols(result: DailyRunResult) -> str:
    candidates = list(result.buy_candidates)[:5]
    if not candidates:
        return "- なし"
    lines: list[str] = []
    for candidate in candidates:
        confidence = map_candidate_public_confidence(candidate.to_dict(), safety_status=str(result.safety_state.get("status", "OK")))
        name = f" {candidate.issue_name}" if candidate.issue_name else ""
        lines.append(f"- {candidate.issue_code}{name}: AI信頼度 {confidence.public_confidence_score}/100 ({confidence.public_confidence_label})")
    return "\n".join(lines)
