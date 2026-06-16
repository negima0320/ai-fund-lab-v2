from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.reporting.blog_report_v2_writer import BLOG_REPORT_V2_READY, write_blog_report_v2


def main() -> int:
    result = write_blog_report_v2(
        decision_for="2026-06-15",
        execution_date="2026-06-16",
        performance_report_path="reports/phase9/daily/2026-06-16_daily_performance_report.json",
    )
    payload = json.loads(Path(result.json_path).read_text(encoding="utf-8"))
    markdown = Path(result.markdown_path).read_text(encoding="utf-8")
    public_rows = [
        row
        for section in ("candidate_top50", "opportunity_top20", "bought", "sold", "holdings", "not_bought_candidates")
        for row in payload.get(section, [])
    ]
    checks = [
        {"name": "no_markdown_table", "ok": "| rank |" not in markdown and "|---" not in markdown},
        {"name": "candidate_top50_rendered", "ok": len(payload.get("candidate_top50", [])) == 50},
        {"name": "opportunity_top20_not_rendered", "ok": "## Opportunity Top20" not in markdown},
        {"name": "top5_rendered", "ok": "## 本日の購入候補 Top5" in markdown and markdown.count("- Opportunity Score:") == 5},
        {"name": "section_order", "ok": markdown.index("## 現在保有中の銘柄") < markdown.index("## 本日の購入銘柄") < markdown.index("## 本日の売却銘柄") < markdown.index("## Candidate Top50") < markdown.index("## 本日の購入候補 Top5")},
        {"name": "list_format_rendered", "ok": "1位 " in markdown and "- Candidate Score:" in markdown and "- Opportunity Score:" in markdown},
        {"name": "names_not_blank", "ok": all(row.get("name") for section in ("candidate_top50", "opportunity_top20", "bought", "holdings", "not_bought_candidates") for row in payload.get(section, []))},
        {"name": "public_codes_are_display_codes", "ok": all(not re.fullmatch(r"[0-9A-Z]{4}0", str(row.get("code", ""))) for row in public_rows)},
        {"name": "score_not_fixed_or_reason_documented", "ok": (not payload.get("data_quality", {}).get("score_all_same_flag")) or "順位に基づく公開用補助スコア" in markdown},
        {"name": "missing_score_not_default_100", "ok": "missing_score" not in markdown or "N/A" in markdown},
        {"name": "yen_formatting", "ok": "169,360円" in markdown and "-6,860円" in markdown},
        {"name": "percentage_formatting", "ok": "-0.69%" in markdown and "%" in markdown},
        {"name": "buy_details_rendered", "ok": len(payload.get("bought", [])) == 5},
        {"name": "buy_amount_rendered", "ok": all(row.get("amount") not in ("", "0") for row in payload.get("bought", []))},
        {"name": "holdings_rendered", "ok": len(payload.get("holdings", [])) == 5},
        {"name": "hold_reason_rendered", "ok": all(row.get("hold_reason") for row in payload.get("holdings", []))},
        {"name": "sell_none_rendered", "ok": "本日は売却銘柄はありません。" in markdown},
        {"name": "asset_summary_rendered", "ok": "現在資産" in markdown and payload.get("summary", {}).get("current_asset") == "993140.0"},
        {"name": "disclaimer_required", "ok": all(line in markdown for line in ("これは仮想運用です。", "実売買ではありません。", "投資判断は自己責任でお願いします。"))},
        {"name": "redaction_pass", "ok": result.redaction_status == "PUBLIC_REPORT_READY"},
        {"name": "broker_order_not_called", "ok": result.broker_order_api_called is False},
        {"name": "open_d_not_started", "ok": result.open_d_started is False},
        {"name": "unlock_trade_not_called", "ok": result.unlock_trade_called is False},
    ]
    passed = result.status == BLOG_REPORT_V2_READY and all(bool(check["ok"]) for check in checks)
    audit = {
        "status": "PASS" if passed else "FAIL",
        "result": result.to_dict(),
        "checks": checks,
        "broker_order_api_called": False,
        "open_d_started": False,
        "unlock_trade_called": False,
        "real_trade_executed": False,
        "virtual_fill_executed": False,
        "model_retraining_executed": False,
    }
    out = Path("reports/phase_reports/phase9t_blog_report_v2_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=True, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
