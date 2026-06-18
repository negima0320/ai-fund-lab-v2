from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, load_ledger
from ai_fund_lab_v2.paper_trading.reporting.redaction_checker import check_public_report_redaction


BLOG_REPORT_V2_READY = "BLOG_REPORT_V2_READY"
BLOG_REPORT_V2_NOT_READY = "BLOG_REPORT_V2_NOT_READY"
DISCLAIMER_LINES = (
    "これは仮想運用です。",
    "実売買ではありません。",
    "投資判断は自己責任でお願いします。",
)


@dataclass(frozen=True)
class BlogReportV2Result:
    status: str
    markdown_path: str
    json_path: str
    decision_for: str
    execution_date: str
    candidate_count: int
    opportunity_count: int
    buy_count: int
    sell_count: int
    holding_count: int
    redaction_status: str
    redaction_violations: tuple[str, ...] = ()
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    virtual_fill_executed: bool = False
    model_retraining_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["redaction_violations"] = list(self.redaction_violations)
        return payload


def write_blog_report_v2(
    *,
    decision_for: str,
    execution_date: str,
    inference_root: Path | str = ".runtime/phase9/inference",
    ledger_path: Path | str = ".runtime/phase9/ledger/latest.json",
    execution_record_path: Path | str | None = None,
    performance_report_path: Path | str | None = None,
    listed_info_path: Path | str = ".runtime/data/raw/jquants/listed_issues/data.parquet",
    auto_approval_path: Path | str | None = None,
    output_root: Path | str = "reports/public/phase9_daily",
    report_version: str = "v4",
) -> BlogReportV2Result:
    if report_version not in {"v3", "v4"}:
        raise ValueError(f"Unsupported blog report version: {report_version}")
    inference_dir = Path(inference_root) / decision_for
    ledger = load_ledger(ledger_path)
    name_map = _load_listed_name_map(Path(listed_info_path))
    candidate_source_rows = _rows_from_artifact(inference_dir / "candidate_artifact.json")
    opportunity_source_rows = _rows_from_artifact(inference_dir / "opportunity_artifact.json")
    candidates = _candidate_top50(candidate_source_rows, name_map=name_map)
    opportunities = _opportunity_top20(opportunity_source_rows, name_map=name_map)
    allocation_rows = _rows_from_artifact(inference_dir / "allocation_artifact.json")
    order_rows = _items_from_artifact(inference_dir / "order_plan_artifact.json")
    approval_path = Path(auto_approval_path) if auto_approval_path else Path(".runtime/phase9/auto_approval") / decision_for / "auto_approval_artifact.json"
    approval_rows = _approval_items(approval_path)
    execution_path = Path(execution_record_path) if execution_record_path else Path(".runtime/phase9/ledger/executions") / f"{execution_date}_executions.json"
    executions = _load_execution_records(execution_path)
    buys = _buy_rows(executions, allocation_rows=approval_rows + allocation_rows, order_rows=order_rows, name_map=name_map)
    sells = _sell_rows(executions, name_map=name_map)
    holdings = _holding_rows(ledger, name_map=name_map)
    not_bought = _not_bought_rows(opportunities=opportunities, buys=buys)
    summary = _asset_summary(
        ledger=ledger,
        decision_for=decision_for,
        execution_date=execution_date,
        performance_report_path=Path(performance_report_path) if performance_report_path else None,
    )
    data_quality = _data_quality(
        sections=[candidates, opportunities, buys, sells, holdings, not_bought],
        candidate_source_rows=candidate_source_rows,
        opportunity_source_rows=opportunity_source_rows,
    )
    payload = {
        "schema_version": "phase9.public_blog_report_v2.v1",
        "report_type": "public_blog_report_v2",
        "generated_at": utc_now_iso(),
        "summary": summary,
        "candidate_top50": candidates,
        "opportunity_top20": opportunities,
        "bought": buys,
        "sold": sells,
        "holdings": holdings,
        "not_bought_candidates": not_bought,
        "ai_summary": _ai_summary(summary=summary, candidate_count=len(candidates), opportunity_count=len(opportunities), buy_count=len(buys), sell_count=len(sells)),
        "data_quality": data_quality,
        "disclaimer": list(DISCLAIMER_LINES),
    }
    markdown = _render_markdown_v4(payload) if report_version == "v4" else _render_markdown_v3(payload)
    redaction = check_public_report_redaction(markdown)
    payload["data_quality"]["redaction_status"] = redaction.status
    payload["data_quality"]["public_report_ready"] = redaction.ready
    status = BLOG_REPORT_V2_READY if redaction.ready else BLOG_REPORT_V2_NOT_READY
    output_dir = Path(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / f"{execution_date}_blog_report_{report_version}.md"
    json_path = output_dir / f"{execution_date}_blog_report_{report_version}.json"
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return BlogReportV2Result(
        status=status,
        markdown_path=str(markdown_path),
        json_path=str(json_path),
        decision_for=decision_for,
        execution_date=execution_date,
        candidate_count=len(candidates),
        opportunity_count=len(opportunities),
        buy_count=len(buys),
        sell_count=len(sells),
        holding_count=len(holdings),
        redaction_status=redaction.status,
        redaction_violations=redaction.violations,
    )


def _candidate_top50(rows: list[dict[str, Any]], *, name_map: dict[str, str]) -> list[dict[str, Any]]:
    same = _score_all_same(rows[:50], key="public_confidence_score")
    output = []
    for index, row in enumerate(rows[:50], start=1):
        rank = int(row.get("rank") or index)
        code = _code(row)
        output.append(
            {
                "rank": rank,
                "code": _display_code(code),
                "name": _name_for(code, row=row, name_map=name_map),
                "candidate_score": _display_score(row.get("public_confidence_score"), rank=rank, same_score=same),
                "candidate_score_note": _score_note(row.get("public_confidence_score"), same_score=same),
                "short_reason": _candidate_reason(rank),
            }
        )
    return output


def _opportunity_top20(rows: list[dict[str, Any]], *, name_map: dict[str, str]) -> list[dict[str, Any]]:
    same_opp = _score_all_same(rows[:20], key="public_confidence_score")
    same_conf = _score_all_same(rows[:20], key="public_confidence_score")
    output = []
    for index, row in enumerate(rows[:20], start=1):
        rank = int(row.get("rank") or index)
        code = _code(row)
        confidence = _display_score(row.get("public_confidence_score"), rank=rank, same_score=same_conf)
        confidence_int = None if confidence == "N/A" else int(float(confidence))
        output.append(
            {
                "rank": rank,
                "code": _display_code(code),
                "name": _name_for(code, row=row, name_map=name_map),
                "opportunity_score": _display_score(row.get("public_confidence_score"), rank=rank, same_score=same_opp),
                "opportunity_score_note": _score_note(row.get("public_confidence_score"), same_score=same_opp),
                "public_confidence_score": confidence,
                "public_confidence_label": "N/A" if confidence_int is None else _label(confidence_int),
                "public_confidence_note": _score_note(row.get("public_confidence_score"), same_score=same_conf),
                "short_reason": _opportunity_reason(rank),
            }
        )
    return output


def _old_opportunity_top20_unused(path: Path) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(_rows_from_artifact(path)[:20], start=1):
        score = int(row.get("public_confidence_score") or _score(row.get("opportunity_score")))
        rows.append(
            {
                "rank": int(row.get("rank") or index),
                "code": _code(row),
                "name": str(row.get("issue_name") or row.get("name") or ""),
                "opportunity_score": _score(row.get("opportunity_score")),
                "public_confidence_score": score,
                "public_confidence_label": str(row.get("public_confidence_label") or _label(score)),
                "short_reason": str(row.get("short_reason") or "上位候補として残りました。"),
            }
        )
    return rows


def _buy_rows(executions: list[dict[str, Any]], *, allocation_rows: list[dict[str, Any]], order_rows: list[dict[str, Any]], name_map: dict[str, str]) -> list[dict[str, Any]]:
    by_code = {_code(row): row for row in allocation_rows + order_rows}
    same_conf = _score_all_same(allocation_rows + order_rows, key="public_confidence_score")
    rows = []
    for index, record in enumerate(executions, start=1):
        if str(record.get("status") or "").upper() != "FILLED" or str(record.get("side") or "").upper() != "BUY":
            continue
        code = _code(record)
        source = by_code.get(code, {})
        quantity = Decimal(str(record.get("quantity") or "0"))
        fill_price = Decimal(str(record.get("fill_price") or "0"))
        score = _display_score(source.get("public_confidence_score"), rank=index, same_score=same_conf)
        score_int = None if score == "N/A" else int(float(score))
        rows.append(
            {
                "code": _display_code(code),
                "name": _name_for(code, row=source, name_map=name_map),
                "quantity": str(quantity),
                "fill_price": str(fill_price),
                "fill_price_display": _yen(fill_price),
                "amount": str(quantity * fill_price),
                "amount_display": _yen(quantity * fill_price),
                "public_confidence_score": score,
                "public_confidence_label": "N/A" if score_int is None else _label(score_int),
                "public_confidence_note": _score_note(source.get("public_confidence_score"), same_score=same_conf),
                "buy_reason": _buy_reason(index),
            }
        )
    return rows


def _sell_rows(executions: list[dict[str, Any]], *, name_map: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for record in executions:
        if str(record.get("status") or "").upper() == "FILLED" and str(record.get("side") or "").upper() == "SELL":
            rows.append(
                {
                    "code": _display_code(_code(record)),
                    "name": _name_for(_code(record), row=record, name_map=name_map),
                    "quantity": str(record.get("quantity") or "0"),
                    "sell_price": str(record.get("fill_price") or "0"),
                    "sell_price_display": _yen(record.get("fill_price") or "0"),
                    "realized_pnl": str(record.get("realized_pnl") or "0"),
                    "realized_pnl_display": _yen(record.get("realized_pnl") or "0"),
                    "holding_days": "",
                    "sell_reason": "Position Managementの売却判断による仮想売却です。",
                }
            )
    return rows


def _holding_rows(ledger: PaperTradingLedger, *, name_map: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for position in ledger.positions:
        latest_price = Decimal("0") if position.quantity <= 0 else position.market_value / position.quantity
        cost_basis = position.average_cost * position.quantity
        pnl_rate = Decimal("0") if cost_basis == 0 else position.unrealized_pnl / cost_basis
        rows.append(
            {
                "code": _display_code(position.code),
                "name": _name_for(position.code, row={"name": position.name}, name_map=name_map),
                "quantity": str(position.quantity),
                "average_cost": str(position.average_cost),
                "average_cost_display": _yen(position.average_cost),
                "latest_price": str(latest_price),
                "latest_price_display": _yen(latest_price),
                "market_value": str(position.market_value),
                "market_value_display": _yen(position.market_value),
                "unrealized_pnl": str(position.unrealized_pnl),
                "unrealized_pnl_display": _yen(position.unrealized_pnl),
                "unrealized_pnl_rate": str(pnl_rate),
                "unrealized_pnl_rate_display": _percent(pnl_rate),
                "hold_reason": "初回購入後の評価期間中です。売却条件は未達で、次回のPosition判断を待ちます。",
            }
        )
    return rows


def _not_bought_rows(*, opportunities: list[dict[str, Any]], buys: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bought_codes = {row["code"] for row in buys}
    rows = []
    for row in opportunities:
        if row["code"] in bought_codes:
            continue
        rows.append(
            {
                "rank": row["rank"],
                "code": row["code"],
                "name": row["name"] or "名称未取得",
                "public_confidence_score": row["public_confidence_score"],
                "reason_not_bought": "上位20には入りましたが、5銘柄上限と資金配分上の優先順位により見送りました。",
            }
        )
    return rows


def _asset_summary(*, ledger: PaperTradingLedger, decision_for: str, execution_date: str, performance_report_path: Path | None) -> dict[str, Any]:
    initial = ledger.metadata.initial_cash if ledger.metadata.initial_cash > 0 else Decimal("1000000")
    current = ledger.performance.total_equity
    pnl = current - initial
    pnl_rate = Decimal("0") if initial <= 0 else pnl / initial
    valuation_context = _valuation_context_from_performance_report(performance_report_path)
    return {
        "decision_for": decision_for,
        "execution_date": execution_date,
        "initial_asset": str(initial),
        "initial_asset_display": _yen(initial),
        "current_asset": str(current),
        "current_asset_display": _yen(current),
        "pnl": str(pnl),
        "pnl_display": _yen(pnl),
        "pnl_rate": str(pnl_rate),
        "pnl_rate_display": _percent(pnl_rate),
        "cash": str(ledger.cash),
        "cash_display": _yen(ledger.cash),
        "market_value": str(ledger.performance.market_value),
        "market_value_display": _yen(ledger.performance.market_value),
        "positions_count": len(ledger.positions),
        "pending_orders_count": len(ledger.pending_orders),
        "realized_pnl": str(ledger.performance.realized_pnl),
        "unrealized_pnl": str(ledger.performance.unrealized_pnl),
        "unrealized_pnl_display": _yen(ledger.performance.unrealized_pnl),
        "performance_report_available": bool(performance_report_path and performance_report_path.is_file()),
        **valuation_context,
    }


def _valuation_context_from_performance_report(path: Path | None) -> dict[str, Any]:
    defaults = {
        "valuation_date": "",
        "quote_source_path": "",
        "quote_source_max_date": "",
        "stale_price_source": False,
    }
    if not path or not path.is_file():
        return defaults
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return defaults
    valuation = payload.get("valuation") if isinstance(payload, dict) else {}
    if not isinstance(valuation, dict):
        return defaults
    return {
        "valuation_date": str(valuation.get("valuation_date") or ""),
        "quote_source_path": str(valuation.get("quote_source_path") or ""),
        "quote_source_max_date": str(valuation.get("quote_source_max_date") or ""),
        "stale_price_source": bool(valuation.get("stale_price_source", False)),
    }


def _ai_summary(*, summary: dict[str, Any], candidate_count: int, opportunity_count: int, buy_count: int, sell_count: int) -> str:
    sell_text = "売却はありませんでした" if sell_count == 0 else f"{sell_count}銘柄を仮想売却しました"
    return (
        f"本日はCandidate {candidate_count}銘柄からOpportunity上位{opportunity_count}銘柄へ絞り込み、"
        f"最終的に{buy_count}銘柄を仮想購入しました。{sell_text}。"
        f"終値評価では損益が {summary['pnl_display']}、評価損益が {summary['unrealized_pnl_display']} となりました。"
    )


def _render_markdown_v4(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Phase9 Blog Report v4",
        "",
        "## 今日のAI運用サマリー",
        "",
        f"- decision_for: {summary['decision_for']}",
        f"- execution_date: {summary['execution_date']}",
        f"- valuation_date: {summary['valuation_date'] or summary['execution_date']}",
        f"- quote_source_max_date: {summary['quote_source_max_date'] or 'N/A'}",
        f"- stale_price_source: {summary['stale_price_source']}",
        f"- 初期資産: {summary['initial_asset_display']}",
        f"- 現在資産: {summary['current_asset_display']}",
        f"- 損益: {summary['pnl_display']}",
        f"- 損益率: {summary['pnl_rate_display']}",
        f"- cash: {summary['cash_display']}",
        f"- market_value: {summary['market_value_display']}",
        f"- positions count: {summary['positions_count']}",
        f"- pending orders count: {summary['pending_orders_count']}",
        "",
        "## 資産状況",
        "",
        f"- 現金: {summary['cash_display']}",
        f"- 株式評価額: {summary['market_value_display']}",
        f"- 現在資産: {summary['current_asset_display']}",
        f"- 損益: {summary['pnl_display']}",
        f"- 損益率: {summary['pnl_rate_display']}",
        f"- 実現損益: {_yen(summary['realized_pnl'])}",
        f"- 含み損益: {summary['unrealized_pnl_display']}",
        "",
        "## 現在保有中の銘柄",
        "",
    ]
    if payload["holdings"]:
        for index, row in enumerate(payload["holdings"], start=1):
            lines.append(
                f"{index}. {_public_text(row['code'])} {_public_text(row['name'])} / "
                f"{_public_quantity(row['quantity'])}株 / 評価額 {row['market_value_display']} / "
                f"損益 {_signed_yen(row['unrealized_pnl'])}"
            )
        lines.append("")
    else:
        lines += ["現在保有中の銘柄はありません。", ""]

    lines += ["## 本日の購入銘柄", ""]
    if payload["bought"]:
        for index, row in enumerate(payload["bought"], start=1):
            lines.append(
                f"{index}. {_public_text(row['code'])} {_public_text(row['name'])} / "
                f"{_public_quantity(row['quantity'])}株 / 約定価格 {_price(row['fill_price'])}"
            )
        lines += ["", "購入理由: AI評価上位かつ資金配分ルールを満たしたため。", ""]
    else:
        lines += ["本日は購入銘柄はありません。", ""]

    lines += ["## 本日の売却銘柄", ""]
    if payload["sold"]:
        for index, row in enumerate(payload["sold"], start=1):
            lines.append(
                f"{index}. {_public_text(row['code'])} {_public_text(row['name'])} / "
                f"{_public_quantity(row['quantity'])}株 / 約定価格 {_price(row['sell_price'])} / "
                f"損益 {_signed_yen(row['realized_pnl'])}"
            )
        lines.append("")
    else:
        lines += ["本日は売却銘柄はありません。", ""]

    lines += ["## Candidate Top50", ""]
    for row in payload["candidate_top50"]:
        lines.append(
            f"{row['rank']}. {_public_text(row['code'])} {_public_text(row['name'])} / "
            f"Score {row['candidate_score']}"
        )
    lines.append("")

    lines += ["## 本日の購入候補 Top5", ""]
    for row in payload["opportunity_top20"][:5]:
        lines.append(
            f"{row['rank']}. {_public_text(row['code'])} {_public_text(row['name'])} / "
            f"Opportunity Score {row['opportunity_score']} / AI信頼度 {row['public_confidence_score']}"
        )
    lines += [
        "",
        "## AIの総括",
        "",
        f"本日はCandidate {len(payload['candidate_top50'])}銘柄からOpportunity上位{len(payload['opportunity_top20'])}銘柄へ絞り込みました。",
        "",
        f"その中から{len(payload['bought'])}銘柄を仮想購入しています。",
        "",
        f"初日の終値評価では {summary['pnl_display']}（{summary['pnl_rate_display']}）となりました。",
        "",
        "公開ブログでは、読みやすさを優先して理由・補足の長文は省略しています。",
        "",
        "## Data Quality",
        "",
        f"- missing_name_count: {payload['data_quality']['missing_name_count']}",
        f"- score_missing_count: {payload['data_quality']['score_missing_count']}",
        f"- score_saturation_count: {payload['data_quality']['score_saturation_count']}",
        f"- score_saturation_flag: {payload['data_quality']['score_saturation_flag']}",
        f"- listed_info_unmatched_count: {payload['data_quality']['listed_info_unmatched_count']}",
        f"- stale_price_count: {payload['data_quality']['stale_price_count']}",
        f"- disallowed_product_count: {payload['data_quality']['disallowed_product_count']}",
        f"- universe_hard_gate_violation_count: {payload['data_quality']['universe_hard_gate_violation_count']}",
        "",
        "## 注意書き",
        "",
    ]
    lines.extend(DISCLAIMER_LINES)
    lines += ["", "内部特徴量、詳細なモデル構造、口座情報、安全装置の詳細は公開していません。", ""]
    return "\n".join(lines)


def _render_markdown_v3(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Phase9 Blog Report v3",
        "",
        "## 今日のAI運用サマリー",
        "",
        f"- decision_for: {summary['decision_for']}",
        f"- execution_date: {summary['execution_date']}",
        f"- 初期資産: {summary['initial_asset_display']}",
        f"- 現在資産: {summary['current_asset_display']}",
        f"- 損益: {summary['pnl_display']}",
        f"- 損益率: {summary['pnl_rate_display']}",
        f"- cash: {summary['cash_display']}",
        f"- market_value: {summary['market_value_display']}",
        f"- positions count: {summary['positions_count']}",
        f"- pending orders count: {summary['pending_orders_count']}",
        "",
        "## 資産状況",
        "",
        _katex_array(
            headers=("Cash", "Market Value", "Total Equity", "Realized PnL", "Unrealized PnL"),
            rows=[
                (
                    _katex_number(summary["cash_display"]),
                    _katex_number(summary["market_value_display"]),
                    _katex_number(summary["current_asset_display"]),
                    _katex_number(_yen(summary["realized_pnl"])),
                    _katex_number(summary["unrealized_pnl_display"]),
                )
            ],
            aligns="rrrrr",
        ),
        "",
        "## 現在保有中の銘柄",
        "",
    ]
    if payload["holdings"]:
        lines.extend(
            [
                _katex_array(
                    headers=("Code", "Qty", "Price", "Market Value", "PnL"),
                    rows=[
                        (
                            _katex_code(row["code"]),
                            _katex_number(row["quantity"]),
                            _katex_number(row["latest_price"]),
                            _katex_number(row["market_value_display"]),
                            _katex_number(row["unrealized_pnl_display"]),
                        )
                        for row in payload["holdings"]
                    ],
                    aligns="lrrrr",
                ),
                "",
                "保有理由はいずれも、売却条件未達・保有継続判定です。",
                "",
            ]
        )
    else:
        lines += ["現在保有中の銘柄はありません。", ""]
    lines += ["## 本日の購入銘柄", ""]
    if payload["bought"]:
        lines.extend(
            [
                _katex_array(
                    headers=("Code", "Qty", "Price", "Reason"),
                    rows=[
                        (
                            _katex_code(row["code"]),
                            _katex_number(row["quantity"]),
                            _katex_number(row["fill_price"]),
                            _katex_text("AI上位"),
                        )
                        for row in payload["bought"]
                    ],
                    aligns="lrrl",
                ),
                "",
                "購入理由: Opportunity上位、資金配分ルール採用、AI評価上位。",
                "",
            ]
        )
    else:
        lines += ["本日は購入銘柄はありません。", ""]
    lines += ["", "## 本日の売却銘柄", ""]
    if payload["sold"]:
        lines.extend(
            [
                _katex_array(
                    headers=("Code", "Qty", "Price", "Reason"),
                    rows=[
                        (
                            _katex_code(row["code"]),
                            _katex_number(row["quantity"]),
                            _katex_number(row["sell_price"]),
                            _katex_text("売却判断"),
                        )
                        for row in payload["sold"]
                    ],
                    aligns="lrrl",
                ),
                "",
            ]
        )
    else:
        lines.append("本日は売却銘柄はありません。")
    lines += [
        "",
        "## Candidate Top50",
        "",
        "上位10件のみ表形式で表示します。11位以降は従来形式で表示します。",
        "",
        _katex_array(
            headers=("Rank", "Code", "Score"),
            rows=[
                (
                    _katex_number(row["rank"]),
                    _katex_code(row["code"]),
                    _katex_number(row["candidate_score"]),
                )
                for row in payload["candidate_top50"][:10]
            ],
            aligns="rlr",
        ),
        "",
    ]
    for row in payload["candidate_top50"][10:]:
        lines.extend(
            [
                f"{row['rank']}位 {row['code']} {row['name']}",
                f"- Candidate Score: {row['candidate_score']}",
                f"- 理由: {row['short_reason']}",
                f"- 補足: {row['candidate_score_note']}",
                "",
            ]
        )
    lines += [
        "## 本日の購入候補 Top5",
        "",
        _katex_array(
            headers=("Rank", "Code", "Score", "Confidence"),
            rows=[
                (
                    _katex_number(row["rank"]),
                    _katex_code(row["code"]),
                    _katex_number(row["opportunity_score"]),
                    _katex_number(row["public_confidence_score"]),
                )
                for row in payload["opportunity_top20"][:5]
            ],
            aligns="rlrr",
        ),
        "",
    ]
    for row in payload["opportunity_top20"][:5]:
        lines.extend(
            [
                f"{row['rank']}位 {row['code']} {row['name']}",
                f"- Opportunity Score: {row['opportunity_score']}",
                f"- AI信頼度: {row['public_confidence_score']}",
                f"- 理由: {row['short_reason']}",
                f"- 補足: {row['public_confidence_note']}",
                "",
            ]
        )
    lines += [
        "## AIの総括",
        "",
        f"本日はCandidate {len(payload['candidate_top50'])}銘柄からOpportunity上位{len(payload['opportunity_top20'])}銘柄へ絞り込みました。",
        "",
        f"その中から{len(payload['bought'])}銘柄を仮想購入しています。",
        "",
        f"初日の終値評価では {summary['pnl_display']}（{summary['pnl_rate_display']}）となりました。",
        "",
        "引き続き保有銘柄の動向と次回AI判断を確認します。",
        "",
        "## Data Quality",
        "",
        f"- missing_name_count: {payload['data_quality']['missing_name_count']}",
        f"- score_missing_count: {payload['data_quality']['score_missing_count']}",
        f"- score_saturation_count: {payload['data_quality']['score_saturation_count']}",
        f"- score_saturation_flag: {payload['data_quality']['score_saturation_flag']}",
        "",
        "一部銘柄名はJ-Quants listed_infoに基づいて補完しています。",
        "",
        "## 注意書き",
        "",
    ]
    lines.extend(DISCLAIMER_LINES)
    lines += ["", "内部特徴量、詳細なモデル構造、口座情報、安全装置の詳細は公開していません。", ""]
    return "\n".join(lines)


def _katex_array(*, headers: tuple[str, ...], rows: list[tuple[str, ...]], aligns: str) -> str:
    if len(headers) != len(aligns):
        raise ValueError("headers and aligns must have the same length")
    if any(len(row) != len(headers) for row in rows):
        raise ValueError("all rows must match header length")
    column_spec = "|" + "|".join(aligns) + "|"
    lines = [
        "$$",
        rf"\begin{{array}}{{{column_spec}}}",
        r"\hline",
        " & ".join(_katex_text(header) for header in headers) + r" \\\\ \hline",
    ]
    lines.extend(" & ".join(row) + r" \\\\ \hline" for row in rows)
    lines += [r"\end{array}", "$$"]
    return "\n".join(lines)


def _public_text(value: Any) -> str:
    return str(value or "").replace("|", "／").replace("\n", " ").strip()


def _public_quantity(value: Any) -> str:
    numeric = Decimal(str(value or "0"))
    if numeric == numeric.to_integral_value():
        return f"{int(numeric):,}"
    return f"{numeric.normalize():,}"


def _price(value: Any) -> str:
    numeric = Decimal(str(value or "0"))
    if numeric == numeric.to_integral_value():
        return f"{int(numeric):,}円"
    text = f"{numeric:,.2f}".rstrip("0").rstrip(".")
    return f"{text}円"


def _signed_yen(value: Any) -> str:
    numeric = Decimal(str(value or "0")).quantize(Decimal("1"))
    if numeric > 0:
        return f"+{int(numeric):,}円"
    return _yen(numeric)


def _katex_text(value: Any) -> str:
    text = str(value or "")
    return r"\text{" + "".join(_katex_escape_text_char(char) for char in text) + "}"


def _katex_code(value: Any) -> str:
    return _katex_text(value)


def _katex_number(value: Any) -> str:
    text = str(value or "0").replace("円", "").replace(",", "").strip()
    return _katex_escape_math_text(text)


def _katex_escape_math_text(value: Any) -> str:
    text = str(value or "")
    return "".join(_katex_escape_math_char(char) for char in text)


def _katex_escape_text_char(char: str) -> str:
    mapping = {
        "\\": r"\textbackslash{}",
        "_": r"\_",
        "%": r"\%",
        "&": r"\&",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
    }
    return mapping.get(char, char)


def _katex_escape_math_char(char: str) -> str:
    mapping = {
        "\\": r"\backslash{}",
        "_": r"\_",
        "%": r"\%",
        "&": r"\&",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
    }
    return mapping.get(char, char)


def _load_listed_name_map(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        frame = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    except Exception:
        return {}
    code_col = _first_existing_column(frame, ("code", "Code", "LocalCode"))
    name_col = _first_existing_column(frame, ("CoName", "CompanyName", "Name", "name", "IssueName"))
    if not code_col or not name_col:
        return {}
    date_col = _first_existing_column(frame, ("Date", "date", "target_date"))
    if date_col:
        frame = frame.sort_values(date_col)
    names: dict[str, str] = {}
    for row in frame.to_dict(orient="records"):
        code = _normalize_code(row.get(code_col))
        name = str(row.get(name_col) or "").strip()
        if not code or not name:
            continue
        for variant in _code_variants(code):
            names[variant] = name
    return names


def _first_existing_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    for column in candidates:
        if column in frame.columns:
            return column
    return ""


def _name_for(code: str, *, row: dict[str, Any], name_map: dict[str, str]) -> str:
    explicit = str(row.get("issue_name") or row.get("name") or "").strip()
    if explicit:
        return explicit
    normalized = _normalize_code(code)
    for variant in _code_variants(normalized):
        if name_map.get(variant):
            return name_map[variant]
    return "名称未取得"


def _normalize_code(value: Any) -> str:
    return str(value or "").strip().upper()


def _display_code(value: Any) -> str:
    code = _normalize_code(value)
    if len(code) == 5 and code.endswith("0"):
        return code[:-1]
    return code


def _code_variants(code: str) -> tuple[str, ...]:
    if not code:
        return ()
    variants = [code]
    if len(code) == 4:
        variants.append(f"{code}0")
    if len(code) == 5 and code.endswith("0"):
        variants.append(code[:-1])
    return tuple(dict.fromkeys(variants))


def _score_all_same(rows: list[dict[str, Any]], *, key: str) -> bool:
    values = [_score_value(row.get(key)) for row in rows]
    values = [value for value in values if value is not None]
    return bool(values) and len(set(values)) == 1 and len(values) > 1


def _display_score(value: Any, *, rank: int, same_score: bool) -> str:
    numeric = _score_value(value)
    if numeric is None:
        return "N/A"
    if same_score:
        return str(max(1, min(100, 101 - int(rank))))
    return str(max(0, min(100, int(round(numeric)))))


def _score_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return numeric


def _score_note(value: Any, *, same_score: bool) -> str:
    if _score_value(value) is None:
        return "missing_score"
    if same_score:
        return "元スコアが同値のため、順位に基づく公開用補助スコアで表示しています。"
    return "公開用に0-100へ丸めた説明スコアです。"


def _candidate_reason(rank: int) -> str:
    if rank <= 10:
        return "Candidate AIの初期選定で上位に入りました。"
    if rank <= 30:
        return "流動性と値動き条件を満たし、候補群に残りました。"
    return "初期スクリーニング条件を満たした監視候補です。"


def _opportunity_reason(rank: int) -> str:
    if rank <= 5:
        return "Opportunity上位として、購入検討の優先度が高い候補です。"
    if rank <= 20:
        return "Opportunity上位20に残った候補です。"
    return "Opportunity候補です。"


def _buy_reason(index: int) -> str:
    return "Opportunity上位からCapital Allocationに採用され、100株単位で購入可能かつ資金配分条件を満たしました。"


def _yen(value: Any) -> str:
    numeric = Decimal(str(value or "0")).quantize(Decimal("1"))
    sign = "-" if numeric < 0 else ""
    return f"{sign}{abs(int(numeric)):,}円"


def _percent(value: Any) -> str:
    numeric = Decimal(str(value or "0")) * Decimal("100")
    return f"{numeric.quantize(Decimal('0.01'))}%"


def _data_quality(
    *,
    sections: list[list[dict[str, Any]]],
    candidate_source_rows: list[dict[str, Any]],
    opportunity_source_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    flattened = [row for section in sections for row in section]
    missing_name_count = sum(1 for row in flattened if row.get("name") == "名称未取得")
    score_missing_count = sum(
        1
        for row in flattened
        for key in ("candidate_score", "opportunity_score", "public_confidence_score")
        if row.get(key) == "N/A"
    )
    source_rows = [*candidate_source_rows[:50], *opportunity_source_rows[:20]]
    listed_info_unmatched_count = _count_hard_gate_issue(source_rows, "is_current_listed")
    stale_price_count = _count_hard_gate_issue(source_rows, "is_fresh_price")
    disallowed_product_count = _count_hard_gate_issue(source_rows, "is_allowed_product")
    hard_gate_reason_count = sum(1 for row in source_rows if str(row.get("universe_exclusion_reason") or "").strip())
    score_saturation_count = sum(1 for row in source_rows if bool(row.get("score_saturation_flag")))
    return {
        "missing_name_count": missing_name_count,
        "score_missing_count": score_missing_count,
        "listed_info_unmatched_count": listed_info_unmatched_count,
        "stale_price_count": stale_price_count,
        "disallowed_product_count": disallowed_product_count,
        "universe_hard_gate_violation_count": max(
            missing_name_count,
            listed_info_unmatched_count,
            stale_price_count,
            disallowed_product_count,
            hard_gate_reason_count,
        ),
        "candidate_score_all_same_flag": _score_all_same(candidate_source_rows[:50], key="score"),
        "opportunity_score_all_same_flag": _score_all_same(opportunity_source_rows[:20], key="opportunity_score"),
        "public_confidence_all_same_flag": _score_all_same(opportunity_source_rows[:20], key="public_confidence_score"),
        "score_all_same_flag": _score_all_same(candidate_source_rows[:50], key="score")
        or _score_all_same(opportunity_source_rows[:20], key="opportunity_score")
        or _score_all_same(opportunity_source_rows[:20], key="public_confidence_score"),
        "score_saturation_count": score_saturation_count,
        "score_saturation_flag": score_saturation_count > 0,
        "score_display_policy": "missing score is N/A; rank uses raw_score_preclip/rank_score when available; public display is bounded to 0-100.",
        "redaction_status": "UNKNOWN",
        "public_report_ready": False,
    }


def _count_hard_gate_issue(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is False)


def _rows_from_artifact(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows") if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict)]


def _items_from_artifact(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("items") if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict)]


def _approval_items(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[Any] = []
    if isinstance(payload, dict):
        rows.extend(payload.get("approved_items") or [])
        rows.extend(payload.get("items") or [])
    return [row for row in rows if isinstance(row, dict)]


def _load_execution_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("records") if isinstance(payload, dict) else []
    return [row for row in rows if isinstance(row, dict)]


def _code(row: dict[str, Any]) -> str:
    return str(row.get("code") or row.get("issue_code") or row.get("Code") or "")


def _score(value: Any) -> str:
    try:
        return str(round(float(value), 4))
    except (TypeError, ValueError):
        return "0"


def _label(score: int) -> str:
    if score >= 90:
        return "非常に強い"
    if score >= 75:
        return "強い"
    if score >= 60:
        return "やや強い"
    if score >= 40:
        return "中立"
    if score >= 25:
        return "弱い"
    return "見送り"


def _public_reason(reason: str) -> str:
    mapping = {
        "CAP5_PRIMARY_SELL_FIRST_BUY_AFTER_FILL": "資金配分ルール上、購入対象に入りました。",
        "CAP5 paper allocation candidate.": "資金配分ルール上、購入対象に入りました。",
    }
    return mapping.get(reason, reason)
