from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import re
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PerformanceSnapshot, PositionSnapshot, write_ledger
from ai_fund_lab_v2.paper_trading.reporting.blog_report_v2_writer import BLOG_REPORT_V2_READY, write_blog_report_v2


def main() -> int:
    fixture = _prepare_fixture(Path(".runtime/phase9/audits/phase9t/fixture"))
    result = write_blog_report_v2(
        decision_for="2026-06-15",
        execution_date="2026-06-16",
        inference_root=fixture["inference_root"],
        ledger_path=fixture["ledger_path"],
        execution_record_path=fixture["execution_record_path"],
        listed_info_path=fixture["listed_info_path"],
        output_root=".runtime/phase9/audits/phase9t/public",
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
        {"name": "no_phase9_blog_report_heading", "ok": not markdown.startswith("# Phase9 Blog Report v4")},
        {"name": "no_ai_operation_summary_section", "ok": "## 今日のAI運用サマリー" not in markdown},
        {"name": "no_public_data_quality_section", "ok": "## Data Quality" not in markdown and "- missing_name_count:" not in markdown},
        {"name": "candidate_top50_rendered", "ok": len(payload.get("candidate_top50", [])) == 50},
        {"name": "opportunity_top20_not_rendered", "ok": "## Opportunity Top20" not in markdown},
        {"name": "top5_rendered", "ok": "## 翌営業日の購入予定候補 Top5" in markdown and "本日終値データに基づく、次回約定候補です。" in markdown and markdown.count("Opportunity Score") >= 5},
        {"name": "purchase_reason_details_rendered", "ok": "## なぜこの銘柄を選んだのか" in markdown and len(payload.get("purchase_reason_details", [])) == len(payload.get("bought", []))},
        {"name": "top5_reason_details_rendered", "ok": "## なぜこの5銘柄が購入候補なのか" in markdown and len(payload.get("top5_reason_details", [])) == 5},
        {"name": "ai_summary_deep_dive_rendered", "ok": "今回の選定は、短期から20日程度の値動きと出来高の増加を強く評価した" in markdown and bool(payload.get("ai_summary_deep_dive"))},
        {"name": "ai_summary_uses_names_not_codes", "ok": "補完銘柄1001" in markdown.split("## AIの総括", maxsplit=1)[1].split("## 注意書き", maxsplit=1)[0] and "10010" not in markdown.split("## AIの総括", maxsplit=1)[1].split("## 注意書き", maxsplit=1)[0]},
        {"name": "section_order", "ok": markdown.index("## 現在保有中の銘柄") < markdown.index("## 本日約定した銘柄") < markdown.index("## なぜこの銘柄を選んだのか") < markdown.index("## 本日の売却銘柄") < markdown.index("## Candidate Top50") < markdown.index("## 翌営業日の購入予定候補 Top5")},
        {"name": "list_format_rendered", "ok": "1. " in markdown and "/ Score " in markdown and "Opportunity Score" in markdown},
        {"name": "names_not_blank", "ok": all(row.get("name") for section in ("candidate_top50", "opportunity_top20", "bought", "holdings", "not_bought_candidates") for row in payload.get(section, []))},
        {"name": "public_codes_are_display_codes", "ok": all(not re.fullmatch(r"[0-9A-Z]{4}0", str(row.get("code", ""))) for row in public_rows)},
        {"name": "score_not_fixed_or_reason_documented", "ok": (not payload.get("data_quality", {}).get("score_all_same_flag")) or "順位に基づく公開用補助スコア" in markdown},
        {"name": "missing_score_not_default_100", "ok": "missing_score" not in markdown or "N/A" in markdown},
        {"name": "yen_formatting", "ok": "100,000円" in markdown and "-6,860円" in markdown},
        {"name": "percentage_formatting", "ok": "-0.69%" in markdown and "%" in markdown},
        {"name": "buy_details_rendered", "ok": len(payload.get("bought", [])) == 5},
        {"name": "buy_amount_rendered", "ok": all(row.get("amount") not in ("", "0") for row in payload.get("bought", []))},
        {"name": "holdings_rendered", "ok": len(payload.get("holdings", [])) == 5},
        {"name": "hold_reason_rendered", "ok": all(row.get("hold_reason") for row in payload.get("holdings", []))},
        {"name": "sell_none_rendered", "ok": "本日は売却銘柄はありません。" in markdown},
        {"name": "asset_summary_rendered", "ok": "現在資産" in markdown and Decimal(str(payload.get("summary", {}).get("current_asset") or "0")) == Decimal("993140")},
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


def _prepare_fixture(root: Path) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    inference_day = root / "inference" / "2026-06-15"
    inference_day.mkdir(parents=True, exist_ok=True)
    listed_info_path = root / "listed_info.parquet"
    candidate_features_path = root / "candidate_features.parquet"
    quotes_path = root / "quotes.parquet"
    codes = [f"{1000 + index}0" for index in range(1, 51)]
    listed = [{"Code": code, "CoName": f"補完銘柄{code[:-1]}", "Date": "2026-06-16"} for code in codes]
    pd.DataFrame(listed).to_parquet(listed_info_path, index=False)
    feature_rows = [
        {
            "target_date": "2026-06-15",
            "code": code,
            "universe_eligible": True,
            "price_momentum_return_5d": 0.10 + index / 100,
            "price_momentum_return_20d": 0.20 + index / 100,
            "volume_momentum_ratio_5d": 1.2 + index / 50,
            "volatility_return_std_20d": 0.03,
            "trend_close_over_ma_20d": 0.05 + index / 200,
            "liquidity_avg_volume_20d": 100000 + index * 1000,
        }
        for index, code in enumerate(codes, start=1)
    ]
    pd.DataFrame(feature_rows).to_parquet(candidate_features_path, index=False)
    quote_rows = []
    for code in codes[:5]:
        for day in range(1, 22):
            quote_rows.append({"date": f"2026-06-{day:02d}", "code": code, "open": 1000, "high": 1100, "low": 900, "close": 1000, "volume": 1000})
    pd.DataFrame(quote_rows).to_parquet(quotes_path, index=False)
    source_refs = {"candidate_features": str(candidate_features_path), "canonical_normalized_daily_quotes": str(quotes_path)}
    candidates = [
        {"rank": index, "code": code, "public_confidence_score": 90 - index % 10, "source_data_refs": source_refs}
        for index, code in enumerate(codes, start=1)
    ]
    opportunities = [
        {"rank": index, "code": code, "opportunity_score": 100 - index, "public_confidence_score": 80 - index % 5, "source_data_refs": source_refs}
        for index, code in enumerate(codes[:20], start=1)
    ]
    allocation = [{"code": code, "public_confidence_score": 80, "planned_amount": str(100000 + index * 1000)} for index, code in enumerate(codes[:5], start=1)]
    (inference_day / "candidate_artifact.json").write_text(json.dumps({"rows": candidates}), encoding="utf-8")
    (inference_day / "opportunity_artifact.json").write_text(json.dumps({"rows": opportunities}), encoding="utf-8")
    (inference_day / "allocation_artifact.json").write_text(json.dumps({"rows": allocation}), encoding="utf-8")
    (inference_day / "order_plan_artifact.json").write_text(json.dumps({"items": allocation}), encoding="utf-8")
    ledger = PaperTradingLedger(
        cash=Decimal("283330"),
        positions=tuple(
            PositionSnapshot(code=code, quantity=Decimal("100"), average_cost=Decimal("1000"), market_value=Decimal("99000"), unrealized_pnl=Decimal("-1000"))
            for code in codes[:5]
        ),
        performance=PerformanceSnapshot(total_equity=Decimal("993140"), cash=Decimal("283330"), market_value=Decimal("709810"), realized_pnl=Decimal("0"), unrealized_pnl=Decimal("-6860"), trade_count=5),
    )
    ledger_path = write_ledger(ledger, runtime_dir=root / ".runtime")
    execution_path = root / "executions.json"
    execution_path.write_text(
        json.dumps({"records": [{"code": code, "side": "BUY", "status": "FILLED", "quantity": "100", "fill_price": "1000", "realized_pnl": "0"} for code in codes[:5]]}),
        encoding="utf-8",
    )
    return {
        "inference_root": str(root / "inference"),
        "ledger_path": str(ledger_path),
        "execution_record_path": str(execution_path),
        "listed_info_path": str(listed_info_path),
    }


if __name__ == "__main__":
    raise SystemExit(main())
