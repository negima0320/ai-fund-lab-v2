from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger
from ai_fund_lab_v2.paper_trading.ledger_valuation import LedgerValuationResult


def write_daily_performance_reports(
    *,
    run_date: str,
    ledger_before: PaperTradingLedger,
    ledger_after: PaperTradingLedger,
    valuation_result: LedgerValuationResult,
    internal_root: Path | str = "reports/phase9/daily",
    public_root: Path | str = "reports/public/phase9_daily",
    initial_equity: Decimal = Decimal("1000000"),
    warnings: list[str] | None = None,
) -> dict[str, str]:
    payload = _payload(
        run_date=run_date,
        ledger_before=ledger_before,
        ledger_after=ledger_after,
        valuation_result=valuation_result,
        initial_equity=initial_equity,
        warnings=warnings or [],
    )
    internal_json = Path(internal_root) / f"{run_date}_daily_performance_report.json"
    internal_md = Path(internal_root) / f"{run_date}_daily_performance_report.md"
    public_md = Path(public_root) / f"{run_date}_public_performance_summary.md"
    for path in (internal_json, internal_md, public_md):
        path.parent.mkdir(parents=True, exist_ok=True)
    internal_json.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    internal_md.write_text(_render_internal_markdown(payload), encoding="utf-8")
    public_md.write_text(_render_public_markdown(payload), encoding="utf-8")
    return {
        "internal_json": str(internal_json),
        "internal_markdown": str(internal_md),
        "public_markdown": str(public_md),
    }


def _payload(
    *,
    run_date: str,
    ledger_before: PaperTradingLedger,
    ledger_after: PaperTradingLedger,
    valuation_result: LedgerValuationResult,
    initial_equity: Decimal,
    warnings: list[str],
) -> dict[str, Any]:
    before_equity = ledger_before.performance.total_equity
    after_equity = ledger_after.performance.total_equity
    daily_return = Decimal("0") if before_equity <= 0 else (after_equity - before_equity) / before_equity
    cumulative_return = Decimal("0") if initial_equity <= 0 else (after_equity - initial_equity) / initial_equity
    return {
        "schema_version": "phase9.daily_performance_report.v1",
        "run_date": run_date,
        "status": "DAILY_PERFORMANCE_REPORTED",
        "cash": str(ledger_after.cash),
        "market_value": str(ledger_after.performance.market_value),
        "total_equity": str(after_equity),
        "realized_pnl": str(ledger_after.performance.realized_pnl),
        "unrealized_pnl": str(ledger_after.performance.unrealized_pnl),
        "daily_equity_change": str(after_equity - before_equity),
        "daily_return": str(daily_return),
        "cumulative_return": str(cumulative_return),
        "position_count": len(ledger_after.positions),
        "pending_order_count": len(ledger_after.pending_orders),
        "trade_count": ledger_after.performance.trade_count,
        "positions": [
            {
                "code": position.code,
                "quantity": str(position.quantity),
                "average_cost": str(position.average_cost),
                "market_value": str(position.market_value),
                "unrealized_pnl": str(position.unrealized_pnl),
                "holding_days": position.holding_days,
            }
            for position in ledger_after.positions
        ],
        "valuation": valuation_result.to_dict(),
        "warnings": warnings,
        "notice": "virtual_operation_under_validation",
        "broker_order_api_called": False,
        "open_d_started": False,
        "unlock_trade_called": False,
        "virtual_fill_executed": False,
        "created_at": utc_now_iso(),
    }


def _render_internal_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9 Daily Performance Report",
        "",
        f"- run_date: {payload['run_date']}",
        f"- status: {payload['status']}",
        f"- total_equity: {payload['total_equity']}",
        f"- cash: {payload['cash']}",
        f"- market_value: {payload['market_value']}",
        f"- realized_pnl: {payload['realized_pnl']}",
        f"- unrealized_pnl: {payload['unrealized_pnl']}",
        f"- daily_equity_change: {payload['daily_equity_change']}",
        f"- cumulative_return: {payload['cumulative_return']}",
        f"- position_count: {payload['position_count']}",
        f"- pending_order_count: {payload['pending_order_count']}",
        f"- trade_count: {payload['trade_count']}",
        "",
        "## Positions",
        "",
    ]
    for position in payload["positions"]:
        lines.append(
            f"- {position['code']} qty={position['quantity']} avg={position['average_cost']} "
            f"value={position['market_value']} unrealized={position['unrealized_pnl']}"
        )
    if payload["warnings"]:
        lines += ["", "## Warnings", ""]
        lines.extend(f"- {warning}" for warning in payload["warnings"])
    return "\n".join(lines) + "\n"


def _render_public_markdown(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Phase9 Public Performance Summary",
            "",
            "この記録は仮想運用・検証中のPaper Trading結果です。投資判断は自己責任でお願いします。",
            "",
            f"- 対象日: {payload['run_date']}",
            f"- 仮想資産: {payload['total_equity']} JPY",
            f"- 現金: {payload['cash']} JPY",
            f"- 保有銘柄数: {payload['position_count']}",
            f"- 評価損益: {payload['unrealized_pnl']} JPY",
            f"- 累計リターン: {payload['cumulative_return']}",
            "",
            "内部スコア、特徴量、安全装置の詳細、口座情報は公開対象外です。",
            "",
        ]
    )
