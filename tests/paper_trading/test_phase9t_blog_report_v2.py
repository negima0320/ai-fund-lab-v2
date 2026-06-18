from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PerformanceSnapshot, PositionSnapshot, write_ledger
from ai_fund_lab_v2.paper_trading.reporting.blog_report_v2_writer import BLOG_REPORT_V2_READY, write_blog_report_v2


def test_phase9t_blog_report_v2_renders_required_sections(tmp_path: Path) -> None:
    inference_root = _write_inference_artifacts(tmp_path)
    ledger_path = _write_ledger(tmp_path)
    execution_path = _write_executions(tmp_path)
    listed_info_path = _write_listed_info(tmp_path)

    result = write_blog_report_v2(
        decision_for="2026-06-15",
        execution_date="2026-06-16",
        inference_root=inference_root,
        ledger_path=ledger_path,
        execution_record_path=execution_path,
        listed_info_path=listed_info_path,
        output_root=tmp_path / "public",
    )
    payload = json.loads(Path(result.json_path).read_text(encoding="utf-8"))
    markdown = Path(result.markdown_path).read_text(encoding="utf-8")

    assert result.status == BLOG_REPORT_V2_READY
    assert result.markdown_path.endswith("_blog_report_v4.md")
    assert result.json_path.endswith("_blog_report_v4.json")
    assert result.candidate_count == 50
    assert result.opportunity_count == 20
    assert result.buy_count == 5
    assert result.sell_count == 0
    assert result.holding_count == 5
    assert len(payload["candidate_top50"]) == 50
    assert len(payload["opportunity_top20"]) == 20
    assert len(payload["bought"]) == 5
    assert payload["candidate_top50"][0]["code"] == "1001"
    assert payload["opportunity_top20"][0]["code"] == "1001"
    assert payload["bought"][0]["code"] == "1001"
    assert payload["holdings"][0]["code"] == "1001"
    assert "10010 " not in markdown
    assert "1001 補完銘柄1001" in markdown
    assert all(Decimal(row["amount"]) > 0 for row in payload["bought"])
    assert all(row["amount_display"].endswith("円") for row in payload["bought"])
    assert len(payload["holdings"]) == 5
    assert all(row["hold_reason"] for row in payload["holdings"])
    assert all(row["name"] != "" for row in payload["holdings"])
    assert payload["holdings"][0]["unrealized_pnl_rate_display"].endswith("%")
    assert payload["summary"]["current_asset"] == "993140.0"
    assert payload["summary"]["current_asset_display"] == "993,140円"
    assert payload["summary"]["pnl_rate_display"] == "-0.69%"
    assert "|" not in markdown
    assert "```latex" not in markdown
    assert "```" not in markdown
    assert "$$" not in markdown
    assert "\\begin{array}" not in markdown
    assert "- Candidate Score:" not in markdown
    assert "- Opportunity Score:" not in markdown
    assert "Candidate AIの初期選定で上位に入りました。" not in markdown
    assert "公開用に0-100へ丸めた説明スコアです。" not in markdown
    candidate_section = _section(markdown, "## Candidate Top50", "## 本日の購入候補 Top5")
    candidate_lines = [line for line in candidate_section.splitlines() if line and line[0].isdigit()]
    assert len(candidate_lines) == 50
    for row in payload["candidate_top50"]:
        assert f"{row['rank']}. {row['code']} 補完銘柄{row['code']} / Score {row['candidate_score']}" in candidate_section
    for row in payload["opportunity_top20"][:5]:
        assert (
            f"{row['rank']}. {row['code']} {row['name']} / "
            f"Opportunity Score {row['opportunity_score']} / AI信頼度 {row['public_confidence_score']}"
        ) in markdown
        assert row["short_reason"] not in markdown
        assert row["public_confidence_note"] not in markdown
    assert "## Opportunity Top20" not in markdown
    assert "## 資産状況" in markdown
    assert "- 現金: 283,330円" in markdown
    assert "- 株式評価額: 709,810円" in markdown
    assert "- 現在資産: 993,140円" in markdown
    assert "- 損益: -6,860円" in markdown
    assert "## 本日の購入候補 Top5" in markdown
    assert "## 本日の購入銘柄" in markdown
    assert "## 現在保有中の銘柄" in markdown
    assert "1. 1001 補完銘柄1001 / 100株 / 評価額 99,000円 / 損益 -1,000円" in markdown
    assert "1. 1001 補完銘柄1001 / 100株 / 約定価格 100円" in markdown
    assert "購入理由: AI評価上位かつ資金配分ルールを満たしたため。" in markdown
    assert markdown.index("## 現在保有中の銘柄") < markdown.index("## 本日の購入銘柄")
    assert markdown.index("## 本日の購入銘柄") < markdown.index("## 本日の売却銘柄")
    assert markdown.index("## 本日の売却銘柄") < markdown.index("## Candidate Top50")
    assert markdown.index("## Candidate Top50") < markdown.index("## 本日の購入候補 Top5")
    assert "本日は売却銘柄はありません。" in markdown
    assert "## Data Quality" in markdown
    assert "- missing_name_count: 0" in markdown
    assert "- listed_info_unmatched_count: 0" in markdown
    assert "- stale_price_count: 0" in markdown
    assert "- disallowed_product_count: 0" in markdown
    assert "- universe_hard_gate_violation_count: 0" in markdown
    assert "score_all_same_flag" not in markdown
    assert "J-Quants listed_info" not in markdown
    assert "これは仮想運用です。" in markdown
    assert "実売買ではありません。" in markdown
    assert "投資判断は自己責任でお願いします。" in markdown
    assert result.redaction_status == "PUBLIC_REPORT_READY"
    assert payload["data_quality"]["missing_name_count"] == 0
    assert payload["data_quality"]["listed_info_unmatched_count"] == 0
    assert payload["data_quality"]["stale_price_count"] == 0
    assert payload["data_quality"]["disallowed_product_count"] == 0
    assert payload["data_quality"]["universe_hard_gate_violation_count"] == 0
    assert payload["data_quality"]["score_all_same_flag"] is False


def test_phase9t_blog_report_v2_missing_name_and_score_fallbacks(tmp_path: Path) -> None:
    inference_root = _write_inference_artifacts(tmp_path, include_missing_score=True)
    ledger_path = _write_ledger(tmp_path)
    execution_path = _write_executions(tmp_path)
    listed_info_path = _write_listed_info(tmp_path, omit_code="10050")

    result = write_blog_report_v2(
        decision_for="2026-06-15",
        execution_date="2026-06-16",
        inference_root=inference_root,
        ledger_path=ledger_path,
        execution_record_path=execution_path,
        listed_info_path=listed_info_path,
        output_root=tmp_path / "public",
    )
    payload = json.loads(Path(result.json_path).read_text(encoding="utf-8"))
    markdown = Path(result.markdown_path).read_text(encoding="utf-8")

    assert payload["candidate_top50"][0]["candidate_score"] == "N/A"
    assert payload["candidate_top50"][0]["candidate_score_note"] == "missing_score"
    assert any(row["name"] == "名称未取得" for row in payload["holdings"])
    assert payload["data_quality"]["missing_name_count"] > 0
    assert payload["data_quality"]["score_missing_count"] > 0
    assert result.redaction_status == "PUBLIC_REPORT_READY"
    assert "|" not in markdown
    assert "## Data Quality" in markdown
    assert "- missing_name_count:" in markdown
    assert "## 注意書き" in markdown


def _section(markdown: str, start: str, end: str) -> str:
    return markdown.split(start, maxsplit=1)[1].split(end, maxsplit=1)[0]


def _write_inference_artifacts(tmp_path: Path, *, include_missing_score: bool = False) -> Path:
    root = tmp_path / "inference"
    day = root / "2026-06-15"
    day.mkdir(parents=True)
    candidates = [
        {
            "rank": index,
            "code": f"{1000 + index}0",
            "issue_name": "",
            "score": None if include_missing_score and index == 1 else 100 - index / 10,
            "public_confidence_score": None if include_missing_score and index == 1 else 90 - index % 10,
            "short_reason": "候補条件を満たしました。",
        }
        for index in range(1, 51)
    ]
    opportunities = [
        {
            "rank": index,
            "code": f"{1000 + index}0",
            "issue_name": "",
            "opportunity_score": 100 - index,
            "public_confidence_score": 80 - index % 5,
            "short_reason": "上位候補です。",
        }
        for index in range(1, 21)
    ]
    allocation = [
        {
            "code": code,
            "issue_name": "",
            "public_confidence_score": 80,
            "short_reason": "CAP5 paper allocation candidate.",
        }
        for code in ("10010", "10020", "10030", "10040", "10050")
    ]
    (day / "candidate_artifact.json").write_text(json.dumps({"rows": candidates}), encoding="utf-8")
    (day / "opportunity_artifact.json").write_text(json.dumps({"rows": opportunities}), encoding="utf-8")
    (day / "allocation_artifact.json").write_text(json.dumps({"rows": allocation}), encoding="utf-8")
    (day / "order_plan_artifact.json").write_text(json.dumps({"items": allocation}), encoding="utf-8")
    return root


def _write_ledger(tmp_path: Path) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("283330.0"),
        positions=tuple(
            PositionSnapshot(
                code=code,
                quantity=Decimal("100"),
                average_cost=Decimal("1000"),
                market_value=Decimal("99000"),
                unrealized_pnl=Decimal("-1000"),
            )
            for code in ("10010", "10020", "10030", "10040", "10050")
        ),
        performance=PerformanceSnapshot(
            total_equity=Decimal("993140.0"),
            cash=Decimal("283330.0"),
            market_value=Decimal("709810.0"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("-6860.0"),
            trade_count=5,
        ),
    )
    return write_ledger(ledger, runtime_dir=tmp_path / ".runtime")


def _write_executions(tmp_path: Path) -> Path:
    path = tmp_path / "executions.json"
    records = [
        {"code": code, "side": "BUY", "status": "FILLED", "quantity": "100", "fill_price": str(price), "realized_pnl": "0"}
        for code, price in zip(("10010", "10020", "10030", "10040", "10050"), (100, 200, 300, 400, 500))
    ]
    path.write_text(json.dumps({"records": records}), encoding="utf-8")
    return path


def _write_listed_info(tmp_path: Path, *, omit_code: str = "") -> Path:
    path = tmp_path / "listed_info.parquet"
    rows = [{"Code": f"{1000 + index}0", "CoName": f"補完銘柄{1000 + index}", "Date": "2026-06-16"} for index in range(1, 51)]
    rows = [row for row in rows if row["Code"] != omit_code]
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path
