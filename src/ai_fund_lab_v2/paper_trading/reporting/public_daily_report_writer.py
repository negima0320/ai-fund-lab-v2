from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.paper_trading.daily_run_result import DailyCandidate, DailyRunResult
from ai_fund_lab_v2.paper_trading.reporting.public_confidence_mapper import map_candidate_public_confidence
from ai_fund_lab_v2.paper_trading.reporting.redaction_checker import assert_public_report_ready
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest


DISCLAIMER = "本レポートは仮想運用の検証記録であり、投資助言ではありません。投資判断は自己責任でお願いします。"


def write_public_daily_report(
    *,
    manifest: DailyRunManifest,
    result: DailyRunResult,
    reports_dir: Path | str = "reports/public/phase9_daily",
) -> Path:
    markdown = render_public_daily_report_markdown(manifest=manifest, result=result)
    assert_public_report_ready(markdown)
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{manifest.run_date}_public_daily_report.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def render_public_daily_report_markdown(*, manifest: DailyRunManifest, result: DailyRunResult) -> str:
    safety_status = manifest.safety_status
    all_candidates = list(result.buy_candidates) + list(result.sell_candidates) + list(result.hold_candidates)
    overall_score = _overall_public_score(all_candidates, safety_status=safety_status)
    lines = [
        "# Phase9 Public Daily Report",
        "",
        f"- date: {manifest.run_date}",
        f"- AI総合判断: {overall_score['label']}",
        f"- 信頼度: {overall_score['score']}/100",
        "",
        "## AIの今日の判断",
        "",
        "本日は仮想運用の検証として、AIの候補判断と資産推移を確認しました。",
        "",
        "## 注目銘柄",
        "",
        _public_candidate_section("買い候補", result.buy_candidates, safety_status=safety_status),
        _public_candidate_section("売り候補", result.sell_candidates, safety_status=safety_status),
        _public_candidate_section("保有候補", result.hold_candidates, safety_status=safety_status),
        "",
        "## 資産推移",
        "",
        f"- 仮想資産: {result.total_equity}",
        f"- 評価損益: {result.unrealized_pnl}",
        f"- 保有銘柄数: {len(result.current_positions or result.positions)}",
        f"- 現金比率: {_cash_ratio(result)}",
        "",
        "## 本日の仮想約定",
        "",
        _public_execution_summary(result),
        "",
        "## 注意書き",
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines) + "\n"


def _public_candidate_section(title: str, candidates: tuple[DailyCandidate, ...], *, safety_status: str) -> str:
    lines = [f"### {title}", ""]
    if not candidates:
        lines.append("- なし")
        return "\n".join(lines)
    for candidate in candidates:
        confidence = map_candidate_public_confidence(candidate.to_dict(), safety_status=safety_status)
        name = f" {candidate.issue_name}" if candidate.issue_name else ""
        display_name = f"{candidate.issue_code}{name}" if candidate.issue_code else "日次判断停止"
        lines.extend(
            [
                f"- {display_name}",
                f"  - AI信頼度: {confidence.public_confidence_score}/100",
                f"  - ラベル: {confidence.public_confidence_label}",
                f"  - 短評: {confidence.short_reason}",
                f"  - 注意: {confidence.caution_note}",
            ]
        )
    return "\n".join(lines)


def _overall_public_score(candidates: list[DailyCandidate], *, safety_status: str) -> dict[str, Any]:
    if not candidates:
        confidence = map_candidate_public_confidence({"public_confidence_score": 50, "short_reason": "候補なし"}, safety_status=safety_status)
        return {"score": confidence.public_confidence_score, "label": confidence.public_confidence_label}
    scores = [
        map_candidate_public_confidence(candidate.to_dict(), safety_status=safety_status).public_confidence_score
        for candidate in candidates
    ]
    score = int(round(sum(scores) / len(scores)))
    confidence = map_candidate_public_confidence({"public_confidence_score": score}, safety_status=safety_status)
    return {"score": confidence.public_confidence_score, "label": confidence.public_confidence_label}


def _cash_ratio(result: DailyRunResult) -> str:
    try:
        equity = float(result.total_equity)
        cash = float(result.current_cash or result.cash)
    except (TypeError, ValueError):
        return "0.00%"
    if equity <= 0:
        return "0.00%"
    return f"{cash / equity * 100:.2f}%"


def _public_execution_summary(result: DailyRunResult) -> str:
    state = result.execution_state or {}
    filled = state.get("filled_orders", [])
    no_fill = state.get("no_fill_orders", [])
    if not filled and not no_fill:
        return "- なし"
    lines: list[str] = []
    if filled:
        lines.append(f"- 仮想約定: {len(filled)}件")
    if no_fill:
        lines.append(f"- 約定見送り: {len(no_fill)}件")
    return "\n".join(lines)
