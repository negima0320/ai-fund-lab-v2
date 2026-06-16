from __future__ import annotations

from ai_fund_lab_v2.paper_trading.daily_run_result import DailyPosition, DailyRunResult
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger
from ai_fund_lab_v2.paper_trading.virtual_fill_processor import VirtualFillResult


def apply_ledger_to_daily_result(result: DailyRunResult, ledger: PaperTradingLedger) -> DailyRunResult:
    positions = tuple(
        DailyPosition(
            issue_code=position.code,
            issue_name=position.name,
            quantity=position.quantity,
            average_cost=position.average_cost,
            market_value=position.market_value,
            unrealized_pnl=position.unrealized_pnl,
            holding_days=position.holding_days,
        )
        for position in ledger.positions
    )
    pending_orders = tuple(order.to_dict() if hasattr(order, "to_dict") else _pending_order_dict(order) for order in ledger.pending_orders)
    performance = ledger.performance
    return DailyRunResult(
        buy_candidates=result.buy_candidates,
        sell_candidates=result.sell_candidates,
        hold_candidates=result.hold_candidates,
        cash=ledger.cash,
        current_cash=ledger.cash,
        positions=positions,
        current_positions=positions,
        pending_orders=pending_orders,
        total_equity=performance.total_equity if performance else result.total_equity,
        market_value=performance.market_value if performance else result.market_value,
        realized_pnl=performance.realized_pnl if performance else result.realized_pnl,
        unrealized_pnl=performance.unrealized_pnl if performance else result.unrealized_pnl,
        trade_count=performance.trade_count if performance else result.trade_count,
        safety_state=result.safety_state,
        review_state=result.review_state,
        artifact_state=result.artifact_state,
        execution_state=result.execution_state,
    )


def _pending_order_dict(order) -> dict[str, object]:
    return {
        "order_id": order.order_id,
        "code": order.code,
        "side": order.side,
        "quantity": str(order.quantity),
        "created_at": order.created_at,
        "status": order.status,
        "dependency_order_id": getattr(order, "dependency_order_id", ""),
        "no_fill_reason": getattr(order, "no_fill_reason", ""),
    }


def apply_virtual_fill_to_daily_result(result: DailyRunResult, fill_result: VirtualFillResult) -> DailyRunResult:
    ledger_result = apply_ledger_to_daily_result(result, fill_result.ledger_after)
    return DailyRunResult(
        buy_candidates=ledger_result.buy_candidates,
        sell_candidates=ledger_result.sell_candidates,
        hold_candidates=ledger_result.hold_candidates,
        cash=ledger_result.cash,
        current_cash=ledger_result.current_cash,
        positions=ledger_result.positions,
        current_positions=ledger_result.current_positions,
        pending_orders=ledger_result.pending_orders,
        total_equity=ledger_result.total_equity,
        market_value=ledger_result.market_value,
        realized_pnl=ledger_result.realized_pnl,
        unrealized_pnl=ledger_result.unrealized_pnl,
        trade_count=ledger_result.trade_count,
        safety_state=ledger_result.safety_state,
        review_state=ledger_result.review_state,
        artifact_state=ledger_result.artifact_state,
        execution_state={
            "status": fill_result.status,
            "filled_orders": [record.to_dict() for record in fill_result.executions],
            "no_fill_orders": [record.to_dict() for record in fill_result.no_fill_orders],
            "ledger_before_path": fill_result.ledger_before_path,
            "ledger_after_path": fill_result.ledger_after_path,
            "ledger_diff_path": fill_result.ledger_diff_path,
            "execution_paths": list(fill_result.execution_paths),
            "dry_run": fill_result.dry_run,
        },
    )
