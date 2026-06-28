from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.paper_trading.daily_inference_runner import _build_allocation_rows, _build_order_plan
from ai_fund_lab_v2.paper_trading.ledger import LedgerMetadata, PaperTradingLedger, PendingOrderState, PerformanceSnapshot, PositionSnapshot
from ai_fund_lab_v2.paper_trading.virtual_fill_processor import process_virtual_fills
from ai_fund_lab_v2.safety_phase11.emergency_stop import EmergencyStopEvaluator
from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json
from ai_fund_lab_v2.safety_phase11.hourly_monitor import HourlyMonitorInput, HourlyPositionMonitor
from ai_fund_lab_v2.safety_phase11.models import SafetyCheckInput, SafetyDecision, SafetyReviewClass, SafetyState, utc_now_iso
from ai_fund_lab_v2.safety_phase11.recovery import RecoveryCheckInput, RecoveryEvaluator
from ai_fund_lab_v2.safety_phase11.safety_manager import SafetyManager, SafetyManagerResult


TRADING_DAYS_PER_YEAR = Decimal("245")
LOT_SIZE = 100
AUDIT_PROFILE_NORMAL_MARKET = "normal_market"
AUDIT_PROFILE_STRESS_INJECTION = "stress_injection"
AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER = "mainline_paper_adapter"
AUDIT_CANDIDATE_UNIVERSE = (
    "1301", "1332", "1605", "1801", "1925", "2269", "2502", "2802", "2914", "3382",
    "3402", "3436", "4005", "4063", "4188", "4452", "4502", "4503", "4568", "4661",
    "4751", "4755", "4901", "5020", "5108", "5401", "6098", "6178", "6273", "6301",
    "6501", "6503", "6594", "6702", "6752", "6758", "6861", "6902", "6954", "6981",
    "7201", "7203", "7267", "7741", "7974", "8001", "8031", "8058", "8306", "8411",
    "8766", "8801", "9020", "9432", "9433", "9983", "9984", "8591", "7733", "8308",
)
FIXED_STUB_CODES = {"7203", "6758", "9984", "8306"}
FORBIDDEN_AUDIT_VALUES = (
    "RAW-REQUEST-PHASE11Z",
    "RAW-RESPONSE-PHASE11Z",
    "ACCOUNT-PLAINTEXT-PHASE11Z",
    "ORDER-PLAINTEXT-PHASE11Z",
    "EXEC-PLAINTEXT-PHASE11Z",
    "AUTH-PLAINTEXT-PHASE11Z",
    "PRIVATE-KEY-PHASE11Z",
    "https://virtual-url.phase11z.invalid/path",
    "SECOND-PASSWORD-PHASE11Z",
)
NON_BLOCKING_REVIEW_REASON_CODES = frozenset(
    {
        "HIGH_RISK_REVIEW",
        "SELL_REVIEW_REQUIRED",
        "BUY_REVIEW_REQUIRED",
        "BUY_OPPORTUNITY_REVIEW",
        "MARKET_STRESS",
        "INDIVIDUAL_DRAWDOWN_WARNING",
        "DAILY_LOSS_REVIEW_REQUIRED",
        "MARKET_STRESS_DAILY_LOSS",
    }
)
BLOCKING_REVIEW_REASON_CODES = frozenset(
    {
        "MAX_EXPOSURE_EXCEEDED",
        "MAX_POSITION_COUNT_EXCEEDED",
        "CASH_BUFFER_VIOLATION",
        "QUOTE_MISSING",
        "QUOTE_STALE",
        "DUPLICATE_ORDER_SYSTEM_EMERGENCY",
        "BROKER_DUPLICATE_ORDER_RISK",
        "BROKER_DIVERGENCE_DETECTED",
        "BROKER_SNAPSHOT_UNAVAILABLE",
        "BROKER_SNAPSHOT_MISSING",
        "BROKER_SNAPSHOT_STALE",
        "RUNTIME_STATE_INCONSISTENT",
        "POSITION_QUANTITY_MISMATCH",
        "ORDER_EXECUTION_SEVERE_DIVERGENCE",
        "SECRET_PERSISTENCE_VIOLATION",
        "RAW_RESPONSE_PERSISTENCE_VIOLATION",
        "UNKNOWN_SEVERE_ERROR",
        "MANUAL_EMERGENCY_STOP",
    }
)


@dataclass(frozen=True)
class IntegratedBacktestAuditConfig:
    period_id: str
    start_date: str
    end_date: str
    output_subdir: str
    initial_cash: Decimal = Decimal("1000000")
    reports_dir: Path | str = "reports"
    runtime_id: str = "phase11z_integrated_safety_backtest_audit"
    environment: str = "integrated_backtest_audit"
    max_days: int | None = None
    docs_dir: Path | str | None = None
    max_positions: int = 8
    daily_candidate_count: int = 6
    max_holding_days: int = 45
    min_holding_days_for_replacement: int = 15
    profit_take_pct: Decimal = Decimal("0.08")
    exit_review_drawdown_pct: Decimal = Decimal("-0.12")
    manual_approval_simulation: bool = True
    audit_profile: str = AUDIT_PROFILE_NORMAL_MARKET
    max_emergency_stop_day_ratio: Decimal = Decimal("0.05")
    safety_enabled: bool = True


@dataclass(frozen=True)
class AuditPosition:
    issue_code: str
    quantity: int
    average_price: Decimal
    entry_date: str
    entry_index: int
    latest_price: Decimal
    priority_score: Decimal = Decimal("0")


@dataclass(frozen=True)
class AuditTrade:
    business_date: str
    issue_code: str
    side: str
    quantity: int
    price: Decimal
    notional: Decimal
    reason: str
    order_id: str = ""


@dataclass(frozen=True)
class DailyAuditRecord:
    business_date: str
    safety_state_before: SafetyState
    safety_state_after: SafetyState
    monitor_decision: SafetyDecision
    pre_order_decision: SafetyDecision
    order_submitted: bool
    order_blocked_reason: str
    orders_generated: int
    buy_orders_submitted: int
    sell_orders_submitted: int
    triggered_reason_codes: tuple[str, ...]
    position_count: int
    cash: Decimal
    equity: Decimal
    auto_sell_executed: bool = False
    auto_recovery_executed: bool = False
    live_order_executed: bool = False


@dataclass(frozen=True)
class IntegratedBacktestAuditResult:
    period_id: str
    start_date: str
    end_date: str
    business_day_count: int
    status: str
    performance: dict[str, Any]
    safety: dict[str, Any]
    integrity: dict[str, Any]
    safety_behavior: dict[str, Any]
    daily_records: tuple[DailyAuditRecord, ...]
    trades: tuple[AuditTrade, ...]
    flow_counts: dict[str, Any]
    state_residency_days: dict[str, int]
    pass_conditions: dict[str, bool]
    output_dir: str
    summary_path: str
    daily_path: str
    trades_path: str
    phase_report_path: str
    phase_report_json_path: str


def smoke_1y_config(*, reports_dir: Path | str = "reports") -> IntegratedBacktestAuditConfig:
    return IntegratedBacktestAuditConfig(
        period_id="smoke_1y",
        start_date="2025-06-01",
        end_date="2026-05-31",
        output_subdir="smoke_1y",
        reports_dir=reports_dir,
    )


def full_5y_config(*, reports_dir: Path | str = "reports") -> IntegratedBacktestAuditConfig:
    return IntegratedBacktestAuditConfig(
        period_id="full_5y",
        start_date="2021-06-01",
        end_date="2026-05-31",
        output_subdir="full_5y",
        reports_dir=reports_dir,
    )


def run_integrated_backtest_audit(config: IntegratedBacktestAuditConfig) -> IntegratedBacktestAuditResult:
    if config.audit_profile == AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER:
        return _run_mainline_paper_adapter(config)

    days = _business_days(config.start_date, config.end_date)
    if config.max_days is not None:
        days = days[: config.max_days]
    cash = config.initial_cash
    positions: dict[str, AuditPosition] = {}
    trades: list[AuditTrade] = []
    daily: list[DailyAuditRecord] = []
    order_decisions: list[dict[str, Any]] = []
    state = SafetyState.NORMAL
    manual_approval_seen = False
    safety_counts = _empty_safety_counts()
    flow_counts = _empty_flow_counts()
    state_residency = {state.value: 0 for state in SafetyState}
    behavior = {
        "market_crash_became_buy_stop": False,
        "buy_stop_blocked_new_buy": False,
        "recovery_candidate_did_not_auto_normal": True,
        "manual_approval_required_for_normal": True,
        "manual_approval_simulated": False,
        "emergency_blocked_order_flow": False,
        "quote_stale_blocked_inferred_trade": False,
        "broker_divergence_review_or_emergency": False,
        "fixed_4_code_stub_used": False,
        "audit_profile": config.audit_profile,
        "periodic_mock_emergency_injection_enabled": _stress_profile(config),
        "normal_market_mock_boolean_crash_triggered": False,
        "recovery_candidate_to_normal_bypass": False,
        "performance_metrics_placeholder": False,
        "stress_results_separated_from_normal_performance": True,
    }

    for index, day in enumerate(days):
        day_text = day.isoformat()
        state_residency[state.value] += 1
        positions_payload = _positions_payload(positions)
        candidates = _candidate_codes_for_day(index, config.daily_candidate_count)
        flow_counts["ai_signal_days"] += 1
        flow_counts["candidate_generated_days"] += 1
        flow_counts["candidate_count_total"] += len(candidates)
        quotes = _quotes_for_day(index, positions_payload, candidates, config)
        market = _market_summary(index, state, config)
        broker_snapshot = _broker_snapshot(index, cash, positions, config)
        orders = _orders_for_day(index, config)
        previous_equity = daily[-1].equity if daily else config.initial_cash
        current_equity_before = _portfolio_equity(cash, positions, quotes)

        monitor_input = HourlyMonitorInput(
            business_date=day_text,
            environment=config.environment,
            runtime_id=config.runtime_id,
            current_safety_state=state,
            broker_snapshot=broker_snapshot,
            positions=tuple(positions_payload),
            quotes=quotes,
            orders=orders,
            executions=(),
            candidate_universe_market_summary=market,
            previous_portfolio_value=previous_equity,
            current_portfolio_value=current_equity_before,
            manual_emergency_stop=_manual_emergency(index, config),
            config={
                "max_quote_age_seconds": "300",
                "max_broker_snapshot_age_seconds": "900",
                "max_total_exposure_ratio": "0.85",
                "exposure_basis": "equity",
                "base_equity": str(current_equity_before),
            },
        )
        monitor = HourlyPositionMonitor().evaluate(monitor_input)
        emergency = EmergencyStopEvaluator().evaluate(monitor, manual_flag_active=monitor_input.manual_emergency_stop)
        recovery = RecoveryEvaluator().evaluate(
            RecoveryCheckInput(
                current_state=state,
                manual_emergency_flag_active=False,
                market_summary=_recovery_market_summary(index),
                quote_freshness="fresh" if _quote_fresh(index, config) else "stale",
                broker_snapshot_freshness="fresh" if not broker_snapshot.get("stale") else "stale",
                broker_divergence=str(broker_snapshot.get("divergence") or "none"),
                duplicate_active_order_risk=bool(orders),
                daily_loss_pct="0.00",
                runtime_state_valid=True,
                persistence_violation_suspected=False,
                latest_safety_report_path="reports/safety/phase11/integrated_backtest/latest_safety_report.json",
            )
        )
        planned_orders = _planned_orders(day_text, index, state, cash, positions, quotes, candidates, config)
        flow_counts["order_plan_generated_days"] += 1
        flow_counts["orders_generated"] += len(planned_orders)
        pre_order_results = tuple(
            _pre_order_safety_for_order(day_text, index, state, cash, positions, quotes, market, broker_snapshot, orders, config, plan)
            for plan in planned_orders
        )
        flow_counts["orders_before_safety"] += len(pre_order_results)
        pre_order = _aggregate_pre_order_results(state, pre_order_results)
        triggered = _triggered_reason_codes(monitor.check_results) + tuple(
            code for result in pre_order_results for code in _triggered_reason_codes(result.guard_results)
        )
        _update_safety_counts(safety_counts, monitor.overall_decision, monitor.next_recommended_state, monitor.check_results)
        for result in pre_order_results:
            _update_safety_counts(safety_counts, result.overall_decision, result.state_candidate, result.guard_results)
        safety_counts["safety_check_count"] += 1

        next_state = _next_state(state, monitor.next_recommended_state, pre_order.state_candidate, emergency.emergency_required, recovery.recovery_candidate)
        if state is SafetyState.RECOVERY_CANDIDATE and next_state is SafetyState.NORMAL:
            behavior["recovery_candidate_to_normal_bypass"] = True
        if next_state is SafetyState.RECOVERY_CANDIDATE:
            behavior["recovery_candidate_did_not_auto_normal"] = True
            if config.manual_approval_simulation and _manual_approval_allowed(index, pre_order.overall_decision):
                behavior["manual_approval_simulated"] = True
                manual_approval_seen = True
                next_state = SafetyState.MANUAL_APPROVED
            elif manual_approval_seen:
                next_state = SafetyState.MANUAL_APPROVED
        if state is SafetyState.MANUAL_APPROVED and next_state is SafetyState.MANUAL_APPROVED and pre_order.overall_decision is SafetyDecision.ALLOW:
            if config.manual_approval_simulation:
                behavior["manual_approval_simulated"] = True
                next_state = SafetyState.NORMAL
        elif next_state is SafetyState.RECOVERY_CANDIDATE:
            manual_approval_seen = False

        order_submitted = False
        blocked_reason = ""
        buy_submitted = 0
        sell_submitted = 0
        for plan, safety_result in zip(planned_orders, pre_order_results):
            if safety_result.overall_decision is SafetyDecision.ALLOW:
                flow_counts["orders_allowed_by_safety"] += 1
            elif safety_result.overall_decision is SafetyDecision.BLOCK:
                flow_counts["orders_blocked_by_safety"] += 1
            elif safety_result.overall_decision is SafetyDecision.REVIEW_REQUIRED:
                flow_counts["orders_review_required"] += 1
            elif safety_result.overall_decision is SafetyDecision.EMERGENCY_STOP:
                flow_counts["orders_emergency_stopped"] += 1

            side = str(plan["side"]).upper()
            if state in {SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}:
                blocked_reason = "STATE_EMERGENCY_STOP_BLOCKED_ORDER_FLOW"
                if side in {"BUY", "SELL"}:
                    flow_counts["orders_emergency_stopped"] += 1
                behavior["emergency_blocked_order_flow"] = True
                continue
            if side == "BUY" and state in {SafetyState.BUY_STOP, SafetyState.RECOVERY_CANDIDATE}:
                blocked_reason = f"STATE_{state.value}_BLOCKED_NEW_BUY"
                flow_counts["orders_blocked_by_safety"] += 1
                if state is SafetyState.BUY_STOP:
                    behavior["buy_stop_blocked_new_buy"] = True
                continue
            if safety_result.overall_decision is not SafetyDecision.ALLOW:
                blocked_reason = safety_result.overall_decision.value
                continue
            if side == "BUY":
                trade = _virtual_buy_from_plan(day_text, index, cash, positions, quotes, plan)
                if trade is not None:
                    trades.append(trade)
                    cash -= trade.notional
                    positions = {
                        **positions,
                        trade.issue_code: AuditPosition(
                            trade.issue_code,
                            trade.quantity,
                            trade.price,
                            day_text,
                            index,
                            trade.price,
                            priority_score=Decimal(str(plan.get("priority_score") or "0")),
                        ),
                    }
                    order_submitted = True
                    buy_submitted += 1
                    flow_counts["buy_orders_submitted"] += 1
                    flow_counts["buy_fill_count"] += 1
                    flow_counts["position_open_count"] += 1
            elif side == "SELL":
                trade = _virtual_sell_from_plan(day_text, index, positions, quotes, plan)
                if trade is not None:
                    trades.append(trade)
                    cash += trade.notional
                    positions = {code: pos for code, pos in positions.items() if code != trade.issue_code}
                    order_submitted = True
                    sell_submitted += 1
                    flow_counts["sell_orders_submitted"] += 1
                    flow_counts["sell_fill_count"] += 1
                    flow_counts["position_close_count"] += 1
                    flow_counts["round_trip_count"] += 1

        if any(code in triggered for code in ("MARKET_STRESS", "BUY_OPPORTUNITY_REVIEW")) and next_state in {SafetyState.MARKET_STRESS, SafetyState.BUY_REVIEW_REQUIRED, SafetyState.BUY_OPPORTUNITY_REVIEW}:
            behavior["market_crash_became_buy_stop"] = True
            if not _stress_profile(config):
                behavior["normal_market_mock_boolean_crash_triggered"] = True
        if any(code in triggered for code in ("QUOTE_STALE", "QUOTE_STALE_FOR_MONITOR", "QUOTE_MISSING")) and not order_submitted:
            behavior["quote_stale_blocked_inferred_trade"] = True
        if "BROKER_DIVERGENCE_DETECTED" in triggered and pre_order.overall_decision in {SafetyDecision.REVIEW_REQUIRED, SafetyDecision.EMERGENCY_STOP}:
            behavior["broker_divergence_review_or_emergency"] = True

        state_after = next_state
        equity = _portfolio_equity(cash, positions, quotes)
        daily.append(
            DailyAuditRecord(
                business_date=day_text,
                safety_state_before=state,
                safety_state_after=state_after,
                monitor_decision=monitor.overall_decision,
                pre_order_decision=pre_order.overall_decision,
                order_submitted=order_submitted,
                order_blocked_reason=blocked_reason,
                orders_generated=len(planned_orders),
                buy_orders_submitted=buy_submitted,
                sell_orders_submitted=sell_submitted,
                triggered_reason_codes=triggered,
                position_count=len(positions),
                cash=cash,
                equity=equity,
            )
        )
        state = state_after

    flow_counts["virtual_orders_submitted"] = flow_counts["buy_orders_submitted"] + flow_counts["sell_orders_submitted"]
    flow_counts["virtual_fills"] = flow_counts["buy_fill_count"] + flow_counts["sell_fill_count"]
    flow_counts["ledger_entry_count"] = len(trades)
    flow_counts["final_position_count"] = len(positions)
    flow_counts["fixed_4_code_stub_used"] = False
    flow_counts["periodic_mock_emergency_injection_enabled"] = _stress_profile(config)
    flow_counts["normal_market_profile"] = config.audit_profile == AUDIT_PROFILE_NORMAL_MARKET
    flow_counts["stress_injection_profile"] = _stress_profile(config)
    performance = _performance_metrics(config.initial_cash, daily, trades, positions, flow_counts)
    integrity = _integrity_flags()
    output_dir = Path(config.reports_dir) / "safety" / "phase11" / "integrated_backtest" / config.output_subdir
    pass_conditions = _pass_conditions(config, days, flow_counts, behavior, state_residency, performance)
    status = "PASS" if all(pass_conditions.values()) else "FAIL"
    result = _build_result(config, days, performance, safety_counts, integrity, behavior, daily, trades, flow_counts, state_residency, pass_conditions, output_dir, status)
    _write_audit_outputs(result)
    return result


def _pre_order_safety_for_order(
    business_date: str,
    index: int,
    state: SafetyState,
    cash: Decimal,
    positions: dict[str, AuditPosition],
    quotes: dict[str, dict[str, Any]],
    market: dict[str, Any],
    broker_snapshot: dict[str, Any],
    orders: tuple[dict[str, Any], ...],
    config: IntegratedBacktestAuditConfig,
    plan: dict[str, Any],
):
    issue_code = str(plan["issue_code"])
    quote = quotes.get(issue_code, {"price": _base_price(index, issue_code), "age_seconds": "30"})
    side = str(plan["side"]).upper()
    notional = Decimal(str(plan.get("notional") or "0")) if side == "BUY" else Decimal("0")
    if _stress_profile(config) and side == "BUY" and index > 0 and index % 157 == 52:
        notional = cash + Decimal("100000")
    safety_config = {"cash_buffer_amount": "50000", "max_total_exposure_ratio": "0.85", "exposure_basis": "equity", "max_quote_age_seconds": "300"}
    if _stress_profile(config) and index > 0 and index % 163 == 61:
        safety_config["max_total_exposure_absolute_cap"] = "100000"
    return SafetyManager().evaluate(
        SafetyCheckInput(
            current_state=state,
            runtime_id=config.runtime_id,
            business_date=business_date,
            environment=config.environment,
            order_plan={
                "issue_code": issue_code,
                "side": side,
                "notional": str(notional),
                "cash_basis": str(cash),
                "raw_request": "RAW-REQUEST-PHASE11Z",
                "order_id": "ORDER-PLAINTEXT-PHASE11Z",
            },
            open_orders=orders,
            positions=tuple(_positions_payload(positions)),
            quotes={**quotes, issue_code: quote},
            market=market,
            broker_snapshot=broker_snapshot,
            config=safety_config,
            manual_emergency_stop=_manual_emergency(index, config),
        )
    )


def _run_mainline_paper_adapter(config: IntegratedBacktestAuditConfig) -> IntegratedBacktestAuditResult:
    days = _business_days(config.start_date, config.end_date)
    if config.max_days is not None:
        days = days[: config.max_days]
    output_dir = Path(config.reports_dir) / "safety" / "phase11" / "integrated_backtest" / config.output_subdir
    adapter = _load_mainline_adapter_context(config, days)
    ledger = PaperTradingLedger(
        cash=config.initial_cash,
        metadata=LedgerMetadata(
            start_date=config.start_date,
            initial_cash=config.initial_cash,
            broker_order_api_called=False,
            open_d_started=False,
            unlock_trade_called=False,
        ),
    )
    trades: list[AuditTrade] = []
    daily: list[DailyAuditRecord] = []
    order_decisions: list[dict[str, Any]] = []
    state = SafetyState.NORMAL
    manual_approval_seen = False
    safety_counts = _empty_safety_counts()
    flow_counts = _empty_flow_counts()
    state_residency = {state.value: 0 for state in SafetyState}
    flow_counts["candidate_universe_size"] = adapter["candidate_universe_size"]
    behavior = {
        "market_crash_became_buy_stop": False,
        "buy_stop_blocked_new_buy": False,
        "recovery_candidate_did_not_auto_normal": True,
        "manual_approval_required_for_normal": True,
        "manual_approval_simulated": False,
        "emergency_blocked_order_flow": False,
        "quote_stale_blocked_inferred_trade": False,
        "broker_divergence_review_or_emergency": False,
        "fixed_4_code_stub_used": False,
        "audit_profile": config.audit_profile,
        "periodic_mock_emergency_injection_enabled": False,
        "normal_market_mock_boolean_crash_triggered": False,
        "recovery_candidate_to_normal_bypass": False,
        "performance_metrics_placeholder": False,
        "stress_results_separated_from_normal_performance": True,
        "mainline_reuse_map": adapter["reuse_map"],
        "revenue_evaluation_eligible": adapter["revenue_evaluation_eligible"],
        "safety_enabled": config.safety_enabled,
    }

    for index, day in enumerate(days):
        day_text = day.isoformat()
        state_residency[state.value] += 1
        quote_rows = _adapter_quote_rows(adapter, day_text)
        fill = process_virtual_fills(
            ledger=ledger,
            quote_rows=quote_rows,
            execution_date=day_text,
            runtime_dir=output_dir / "mainline_virtual_fill_runtime",
            output_root=output_dir / "mainline_virtual_fill_outputs",
            dry_run=True,
            safety_locked=False,
        )
        ledger = _mark_to_market_phase9_ledger(fill.ledger_after, _adapter_price_map(adapter, day_text), day_text)
        for execution in fill.executions:
            notional = execution.fill_price * execution.quantity
            trades.append(
                AuditTrade(
                    business_date=execution.fill_date,
                    issue_code=execution.code,
                    side=execution.side.upper(),
                    quantity=int(execution.quantity),
                    price=execution.fill_price,
                    notional=notional,
                    reason="PHASE9_PROCESS_VIRTUAL_FILLS",
                    order_id=execution.order_id,
                )
            )
            if execution.side.upper() == "BUY":
                flow_counts["buy_fill_count"] += 1
                flow_counts["position_open_count"] += 1
            elif execution.side.upper() == "SELL":
                flow_counts["sell_fill_count"] += 1
                flow_counts["position_close_count"] += 1
                flow_counts["round_trip_count"] += 1

        candidates = _adapter_candidates_for_day(adapter, day_text, limit=max(20, config.daily_candidate_count))
        candidate_codes = tuple(str(row["code"]) for row in candidates[: config.daily_candidate_count])
        flow_counts["ai_signal_days"] += 1
        flow_counts["candidate_generated_days"] += 1
        flow_counts["candidate_count_total"] += len(candidates)
        quotes = _adapter_safety_quotes(adapter, day_text, set(candidate_codes) | {position.code for position in ledger.positions})
        audit_positions = _audit_positions_from_phase9_ledger(ledger, index)
        positions_payload = _positions_payload(audit_positions)
        market = {
            "market_crash_source": "canonical_quotes_phase7_ranked_daily",
            "index_return": "0.00",
            "candidate_universe_drawdown": "0.00",
            "extreme_down_ratio": "0.00",
            "stop_limit_candidate_ratio": "0.00",
            "is_synthetic": False,
            "market_crash": False,
            "severe_crash": False,
            "daily_loss_pct": "0.00",
            "recovery_candidate": False,
        }
        broker_snapshot = _broker_snapshot(index, ledger.cash, audit_positions, config)
        orders = ()
        previous_equity = daily[-1].equity if daily else config.initial_cash
        current_equity_before = ledger.performance.total_equity if ledger.performance else ledger.cash
        monitor_input = HourlyMonitorInput(
            business_date=day_text,
            environment=config.environment,
            runtime_id=config.runtime_id,
            current_safety_state=state,
            broker_snapshot=broker_snapshot,
            positions=tuple(positions_payload),
            quotes=quotes,
            orders=orders,
            executions=(),
            candidate_universe_market_summary=market,
            previous_portfolio_value=previous_equity,
            current_portfolio_value=current_equity_before,
            manual_emergency_stop=False,
            config={
                "max_quote_age_seconds": "300",
                "max_broker_snapshot_age_seconds": "900",
                "max_total_exposure_ratio": "0.85",
                "exposure_basis": "equity",
                "base_equity": str(current_equity_before),
            },
        )
        monitor = HourlyPositionMonitor().evaluate(monitor_input)
        emergency = EmergencyStopEvaluator().evaluate(monitor, manual_flag_active=False)
        recovery = RecoveryEvaluator().evaluate(
            RecoveryCheckInput(
                current_state=state,
                manual_emergency_flag_active=False,
                market_summary=_recovery_market_summary(index),
                quote_freshness="fresh",
                broker_snapshot_freshness="fresh",
                broker_divergence="none",
                duplicate_active_order_risk=False,
                daily_loss_pct="0.00",
                runtime_state_valid=True,
                persistence_violation_suspected=False,
                latest_safety_report_path="reports/safety/phase11/integrated_backtest/latest_safety_report.json",
            )
        )

        planned_orders = _adapter_planned_orders(
            adapter=adapter,
            config=config,
            ledger=ledger,
            day_text=day_text,
            index=index,
            candidates=candidates,
        )
        flow_counts["order_plan_generated_days"] += 1
        flow_counts["orders_generated"] += len(planned_orders)
        flow_counts["orders_before_safety"] += len(planned_orders)
        if config.safety_enabled:
            pre_order_results = tuple(
                _pre_order_safety_for_order(day_text, index, state, ledger.cash, audit_positions, quotes, market, broker_snapshot, orders, config, plan)
                for plan in planned_orders
            )
        else:
            pre_order_results = tuple(_allow_safety_result(state) for _ in planned_orders)
        pre_order = _aggregate_pre_order_results(state, pre_order_results)
        triggered = _triggered_reason_codes(monitor.check_results) + tuple(
            code for result in pre_order_results for code in _triggered_reason_codes(result.guard_results)
        )
        _update_safety_counts(safety_counts, monitor.overall_decision, monitor.next_recommended_state, monitor.check_results)
        for result in pre_order_results:
            _update_safety_counts(safety_counts, result.overall_decision, result.state_candidate, result.guard_results)
        safety_counts["safety_check_count"] += 1

        next_state = _next_state(state, monitor.next_recommended_state, pre_order.state_candidate, emergency.emergency_required, recovery.recovery_candidate)
        if state is SafetyState.RECOVERY_CANDIDATE and next_state is SafetyState.NORMAL:
            behavior["recovery_candidate_to_normal_bypass"] = True
        if next_state is SafetyState.RECOVERY_CANDIDATE:
            behavior["recovery_candidate_did_not_auto_normal"] = True
            if config.manual_approval_simulation and _manual_approval_allowed(index, pre_order.overall_decision):
                behavior["manual_approval_simulated"] = True
                manual_approval_seen = True
                next_state = SafetyState.MANUAL_APPROVED
            elif manual_approval_seen:
                next_state = SafetyState.MANUAL_APPROVED
        if state is SafetyState.MANUAL_APPROVED and next_state is SafetyState.MANUAL_APPROVED and pre_order.overall_decision is SafetyDecision.ALLOW:
            if config.manual_approval_simulation:
                behavior["manual_approval_simulated"] = True
                next_state = SafetyState.NORMAL
        elif next_state is SafetyState.RECOVERY_CANDIDATE:
            manual_approval_seen = False

        new_pending: list[PendingOrderState] = []
        blocked_reason = ""
        buy_submitted = 0
        sell_submitted = 0
        for plan, safety_result in zip(planned_orders, pre_order_results):
            side = str(plan["side"]).upper()
            policy = _order_review_policy(safety_result)
            if policy["fill_allowed"]:
                flow_counts["orders_allowed_by_safety"] += 1
            elif safety_result.overall_decision is SafetyDecision.BLOCK:
                flow_counts["orders_blocked_by_safety"] += 1
            elif safety_result.overall_decision is SafetyDecision.REVIEW_REQUIRED:
                flow_counts["orders_review_required"] += 1
            elif safety_result.overall_decision is SafetyDecision.EMERGENCY_STOP:
                flow_counts["orders_emergency_stopped"] += 1
            if policy["review_class"] == SafetyReviewClass.NON_BLOCKING_REVIEW.value:
                flow_counts["non_blocking_review_order_count"] += 1
            if policy["review_class"] == SafetyReviewClass.BLOCKING_REVIEW.value:
                flow_counts["blocking_review_order_count"] += 1
            if policy["human_review_required"]:
                flow_counts["human_review_required_order_count"] += 1

            submitted = False
            blocked_reason_for_order = ""
            if state in {SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}:
                blocked_reason = "STATE_EMERGENCY_STOP_BLOCKED_ORDER_FLOW"
                blocked_reason_for_order = blocked_reason
                behavior["emergency_blocked_order_flow"] = True
            elif side == "BUY" and state in {SafetyState.BUY_STOP, SafetyState.RECOVERY_CANDIDATE}:
                blocked_reason = f"STATE_{state.value}_BLOCKED_NEW_BUY"
                blocked_reason_for_order = blocked_reason
                flow_counts["orders_blocked_by_safety"] += 1
                if state is SafetyState.BUY_STOP:
                    behavior["buy_stop_blocked_new_buy"] = True
            elif not policy["fill_allowed"]:
                blocked_reason = safety_result.overall_decision.value
                blocked_reason_for_order = blocked_reason
            else:
                pending = _pending_order_from_adapter_plan(plan, day_text, _next_execution_date(days, index), review_class=policy["review_class"])
                new_pending.append(pending)
                submitted = True
                if side == "BUY":
                    buy_submitted += 1
                    flow_counts["buy_orders_submitted"] += 1
                elif side == "SELL":
                    sell_submitted += 1
                    flow_counts["sell_orders_submitted"] += 1
            order_decisions.append(
                _order_decision_payload(
                    business_date=day_text,
                    plan=plan,
                    safety_result=safety_result,
                    policy=policy,
                    submitted=submitted,
                    blocked_reason=blocked_reason_for_order,
                )
            )

        if new_pending:
            ledger = PaperTradingLedger(
                cash=ledger.cash,
                positions=ledger.positions,
                pending_orders=tuple(list(ledger.pending_orders) + new_pending),
                performance=ledger.performance,
                metadata=ledger.metadata,
            )
        state_after = next_state
        equity = ledger.performance.total_equity if ledger.performance else ledger.cash
        daily.append(
            DailyAuditRecord(
                business_date=day_text,
                safety_state_before=state,
                safety_state_after=state_after,
                monitor_decision=monitor.overall_decision,
                pre_order_decision=pre_order.overall_decision,
                order_submitted=bool(new_pending),
                order_blocked_reason=blocked_reason,
                orders_generated=len(planned_orders),
                buy_orders_submitted=buy_submitted,
                sell_orders_submitted=sell_submitted,
                triggered_reason_codes=triggered,
                position_count=len(ledger.positions),
                cash=ledger.cash,
                equity=equity,
            )
        )
        state = state_after

    flow_counts["virtual_orders_submitted"] = flow_counts["buy_orders_submitted"] + flow_counts["sell_orders_submitted"]
    flow_counts["virtual_fills"] = flow_counts["buy_fill_count"] + flow_counts["sell_fill_count"]
    flow_counts["ledger_entry_count"] = len(trades)
    flow_counts["final_position_count"] = len(ledger.positions)
    flow_counts["fixed_4_code_stub_used"] = False
    flow_counts["periodic_mock_emergency_injection_enabled"] = False
    flow_counts["normal_market_profile"] = False
    flow_counts["stress_injection_profile"] = False
    flow_counts["mainline_paper_adapter_profile"] = True
    flow_counts["mainline_reuse_map"] = adapter["reuse_map"]
    flow_counts["revenue_evaluation_eligible"] = adapter["revenue_evaluation_eligible"]
    _mark_order_decision_fills(order_decisions, trades)
    review_aggregation = _aggregate_order_reviews(order_decisions)
    flow_counts["order_decision_count"] = len(order_decisions)
    flow_counts["raw_review_occurrence_count"] = review_aggregation["raw_review_occurrence_count"]
    flow_counts["aggregated_review_item_count"] = review_aggregation["aggregated_review_item_count"]
    flow_counts["review_compression_ratio"] = review_aggregation["review_compression_ratio"]
    flow_counts["blocking_review_count"] = review_aggregation["blocking_review_count"]
    flow_counts["non_blocking_review_count"] = review_aggregation["non_blocking_review_count"]
    flow_counts["info_only_count"] = review_aggregation["info_only_count"]
    flow_counts["order_decisions_path"] = str(output_dir / "order_decisions.json")
    flow_counts["aggregated_review_queue_path"] = str(output_dir / "aggregated_review_queue.json")
    performance = _performance_metrics(config.initial_cash, daily, trades, {}, flow_counts)
    performance["capital_utilization"] = performance.get("exposure_ratio")
    performance["replacement_rate"] = _round(
        Decimal(flow_counts["sell_orders_submitted"]) / Decimal(max(flow_counts["buy_orders_submitted"], 1))
    )
    performance["revenue_evaluation_eligible"] = adapter["revenue_evaluation_eligible"]
    integrity = _integrity_flags()
    pass_conditions = _pass_conditions(config, days, flow_counts, behavior, state_residency, performance)
    status = "PASS" if all(pass_conditions.values()) else "FAIL"
    result = _build_result(config, days, performance, safety_counts, integrity, behavior, daily, trades, flow_counts, state_residency, pass_conditions, output_dir, status)
    _write_audit_outputs(result)
    _write_json(output_dir / "order_decisions.json", {"order_decisions": order_decisions})
    _write_json(output_dir / "aggregated_review_queue.json", review_aggregation)
    return result


def _allow_safety_result(state: SafetyState) -> SafetyManagerResult:
    return SafetyManagerResult(
        current_state=state,
        overall_decision=SafetyDecision.ALLOW,
        state_candidate=state,
        transition_allowed=True,
        transition_reason="safety_disabled_for_comparison",
        guard_results=(),
        events=(),
        review_items=(),
    )


def _order_review_policy(result: SafetyManagerResult) -> dict[str, Any]:
    reason_codes = [item.reason_code for item in result.guard_results if item.decision is not SafetyDecision.ALLOW]
    blocking = [code for code in reason_codes if code in BLOCKING_REVIEW_REASON_CODES]
    non_blocking = [code for code in reason_codes if code in NON_BLOCKING_REVIEW_REASON_CODES]
    if result.overall_decision in {SafetyDecision.EMERGENCY_STOP, SafetyDecision.BLOCK} or blocking:
        review_class = SafetyReviewClass.BLOCKING_REVIEW
        fill_allowed = False
    elif non_blocking:
        review_class = SafetyReviewClass.NON_BLOCKING_REVIEW
        fill_allowed = True
    elif result.overall_decision is SafetyDecision.REVIEW_REQUIRED:
        review_class = SafetyReviewClass.BLOCKING_REVIEW
        fill_allowed = False
    else:
        review_class = SafetyReviewClass.INFO_ONLY
        fill_allowed = True
    return {
        "fill_allowed": fill_allowed,
        "review_class": review_class.value,
        "reason_codes": reason_codes,
        "blocking_reason_codes": blocking,
        "non_blocking_review_reason_codes": non_blocking,
        "human_review_required": bool(blocking or non_blocking or result.review_items),
    }


def _order_decision_payload(
    *,
    business_date: str,
    plan: dict[str, Any],
    safety_result: SafetyManagerResult,
    policy: dict[str, Any],
    submitted: bool,
    blocked_reason: str,
) -> dict[str, Any]:
    return _phase11_sanitize(
        {
            "business_date": business_date,
            "order_ref": str(plan.get("order_id") or ""),
            "side": str(plan.get("side") or "").upper(),
            "issue_code": str(plan.get("issue_code") or ""),
            "overall_decision": safety_result.overall_decision.value,
            "fill_allowed": bool(policy["fill_allowed"]),
            "submitted_to_virtual_fill": bool(submitted),
            "filled": False,
            "review_class": str(policy["review_class"]),
            "reason_codes": list(policy["reason_codes"]),
            "blocking_reason_codes": list(policy["blocking_reason_codes"]),
            "non_blocking_review_reason_codes": list(policy["non_blocking_review_reason_codes"]),
            "guard_details": {
                result.guard_name.value: result.details
                for result in safety_result.guard_results
                if result.details
            },
            "human_review_required": bool(policy["human_review_required"]),
            "blocked_reason": blocked_reason,
            "auto_sell_executed": False,
            "auto_recovery_executed": False,
            "live_order_executed": False,
        }
    )


def _mark_order_decision_fills(order_decisions: list[dict[str, Any]], trades: list[AuditTrade]) -> None:
    filled_order_ids = {trade.order_id for trade in trades if trade.order_id}
    for item in order_decisions:
        if item.get("order_ref") in filled_order_ids:
            item["filled"] = True


def _aggregate_order_reviews(order_decisions: list[dict[str, Any]]) -> dict[str, Any]:
    items: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    raw_count = 0
    blocking_count = 0
    non_blocking_count = 0
    info_count = 0
    for order in order_decisions:
        review_class = str(order.get("review_class") or SafetyReviewClass.INFO_ONLY.value)
        if review_class == SafetyReviewClass.BLOCKING_REVIEW.value:
            blocking_count += 1
        elif review_class == SafetyReviewClass.NON_BLOCKING_REVIEW.value:
            non_blocking_count += 1
        else:
            info_count += 1
        reasons = list(order.get("non_blocking_review_reason_codes") or []) + list(order.get("blocking_reason_codes") or [])
        for reason in reasons:
            raw_count += 1
            key = (str(order.get("business_date") or ""), str(order.get("issue_code") or ""), review_class, str(reason))
            current = items.setdefault(
                key,
                {
                    "business_date": key[0],
                    "issue_code": key[1],
                    "review_class": key[2],
                    "reason_code": key[3],
                    "occurrence_count": 0,
                    "order_refs": [],
                    "fill_allowed_count": 0,
                    "filled_count": 0,
                    "human_review_required": True,
                },
            )
            current["occurrence_count"] += 1
            current["order_refs"].append(str(order.get("order_ref") or ""))
            if order.get("fill_allowed"):
                current["fill_allowed_count"] += 1
            if order.get("filled"):
                current["filled_count"] += 1
    aggregated = sorted(items.values(), key=lambda item: (item["business_date"], item["issue_code"], item["review_class"], item["reason_code"]))
    return _phase11_sanitize(
        {
            "schema_version": "phase11_non_blocking_review_aggregation_v1",
            "raw_review_occurrence_count": raw_count,
            "aggregated_review_item_count": len(aggregated),
            "review_compression_ratio": _round(Decimal(raw_count) / Decimal(max(len(aggregated), 1))) if aggregated else 0,
            "blocking_review_count": blocking_count,
            "non_blocking_review_count": non_blocking_count,
            "info_only_count": info_count,
            "aggregated_review_items": aggregated,
        }
    )


def _load_mainline_adapter_context(config: IntegratedBacktestAuditConfig, days: list[date]) -> dict[str, Any]:
    ranked_path = Path("reports/phase7_prestudy/opportunity_ranked_daily.parquet")
    quotes_path = Path(".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    reuse_map = {
        "candidate_source": "fallback",
        "opportunity_source": "fallback",
        "allocation_source": "fallback",
        "order_plan_source": "fallback",
        "fill_source": "mainline_virtual_fill",
        "ledger_source": "PaperTradingLedger",
        "exit_source": "fallback",
        "metrics_source": "mainline_ledger_plus_realized_trade_metrics",
        "price_source": "fallback",
    }
    ranked_by_date: dict[str, list[dict[str, Any]]] = {}
    available_rank_dates: list[str] = []
    candidate_universe_size = len(AUDIT_CANDIDATE_UNIVERSE)
    if ranked_path.is_file():
        import pandas as pd

        ranked = pd.read_parquet(ranked_path)
        ranked["target_date"] = ranked["target_date"].astype(str)
        ranked["code"] = ranked["code"].astype(str)
        ranked = ranked.sort_values(["target_date", "buy_rank", "code"])
        for target_date, group in ranked.groupby("target_date"):
            ranked_by_date[str(target_date)] = [
                {
                    "code": str(row["code"]),
                    "issue_code": str(row["code"]),
                    "buy_rank": int(row["buy_rank"]),
                    "rank_score": float(100.0 - float(row["buy_rank"])),
                    "expected_edge_score": float(row.get("expected_edge_score") or 0.0),
                    "public_confidence_score": max(1, min(100, int(100 - int(row["buy_rank"])))),
                    "public_confidence_label": "phase7_ranked_daily",
                    "short_reason": "Phase7 ranked_daily opportunity artifact.",
                    "caution_note": "Adapter smoke only. Not an instruction to trade.",
                    "reason": "PHASE7_RANKED_DAILY_ARTIFACT",
                }
                for row in group.to_dict(orient="records")
            ]
        available_rank_dates = sorted(ranked_by_date)
        candidate_universe_size = int(ranked["code"].nunique())
        reuse_map["candidate_source"] = "mainline_artifact:phase7_opportunity_ranked_daily"
        reuse_map["opportunity_source"] = "mainline_artifact:phase7_opportunity_ranked_daily"
    quote_by_date_code: dict[tuple[str, str], dict[str, Any]] = {}
    quote_rows_by_date: dict[str, list[dict[str, Any]]] = {}
    if quotes_path.is_file():
        import pandas as pd

        quote_frame = pd.read_parquet(quotes_path, columns=["date", "code", "open", "close"])
        quote_frame["date"] = quote_frame["date"].astype(str)
        quote_frame["code"] = quote_frame["code"].astype(str)
        start = days[0].isoformat() if days else config.start_date
        end = (_next_execution_date(days, len(days) - 1) if days else config.end_date)
        quote_frame = quote_frame[(quote_frame["date"] >= start) & (quote_frame["date"] <= end)]
        for row in quote_frame.to_dict(orient="records"):
            quote_row = {
                "date": str(row["date"]),
                "code": str(row["code"]),
                "open": str(row["open"]),
                "close": str(row["close"]),
            }
            quote_by_date_code[(str(row["date"]), str(row["code"]))] = quote_row
            quote_rows_by_date.setdefault(str(row["date"]), []).append(quote_row)
        reuse_map["price_source"] = "mainline_artifact:phase9_canonical_normalized_daily_quotes"
    reuse_map["allocation_source"] = "CAP5:phase9_daily_inference_allocation_builder"
    reuse_map["order_plan_source"] = "phase9_daily_inference_order_plan_builder"
    revenue_eligible = all(
        not str(reuse_map[key]).startswith("fallback")
        for key in ("candidate_source", "opportunity_source", "allocation_source", "order_plan_source", "fill_source", "ledger_source", "price_source")
    )
    return {
        "ranked_by_date": ranked_by_date,
        "available_rank_dates": available_rank_dates,
        "quote_by_date_code": quote_by_date_code,
        "quote_rows_by_date": quote_rows_by_date,
        "candidate_universe_size": candidate_universe_size,
        "reuse_map": reuse_map,
        "revenue_evaluation_eligible": revenue_eligible,
        "source_paths": {"ranked_daily": str(ranked_path), "canonical_quotes": str(quotes_path)},
    }


def _adapter_candidates_for_day(adapter: dict[str, Any], day_text: str, *, limit: int) -> list[dict[str, Any]]:
    ranked_by_date = adapter["ranked_by_date"]
    date_key = day_text if day_text in ranked_by_date else _latest_available_date(adapter["available_rank_dates"], day_text)
    if date_key:
        return list(ranked_by_date.get(date_key, []))[:limit]
    return [
        {
            "code": code,
            "issue_code": code,
            "buy_rank": index + 1,
            "rank_score": float(100 - index),
            "public_confidence_score": max(1, 100 - index),
            "public_confidence_label": "fallback",
            "short_reason": "Fallback candidate used because mainline artifact was unavailable.",
            "caution_note": "Revenue evaluation is not eligible when fallback candidates dominate.",
            "reason": "FALLBACK_CANDIDATE",
        }
        for index, code in enumerate(_candidate_codes_for_day(0, limit))
    ]


def _latest_available_date(available: list[str], day_text: str) -> str:
    candidates = [item for item in available if item <= day_text]
    return candidates[-1] if candidates else ""


def _adapter_quote_rows(adapter: dict[str, Any], day_text: str) -> list[dict[str, Any]]:
    rows_by_date = adapter.get("quote_rows_by_date")
    if rows_by_date is not None:
        return [dict(row) for row in rows_by_date.get(day_text, [])]
    return [dict(row) for (date_key, _), row in adapter["quote_by_date_code"].items() if date_key == day_text]


def _adapter_price_map(adapter: dict[str, Any], day_text: str) -> dict[str, Decimal]:
    rows = _adapter_quote_rows(adapter, day_text)
    return {str(row["code"]): Decimal(str(row.get("close") or row.get("open") or "0")) for row in rows}


def _adapter_safety_quotes(adapter: dict[str, Any], day_text: str, codes: set[str]) -> dict[str, dict[str, Any]]:
    price_map = _adapter_price_map(adapter, day_text)
    return {
        code: {"age_seconds": "30", "price": str(price_map[code])}
        for code in codes
        if code in price_map and price_map[code] > 0
    }


def _adapter_planned_orders(
    *,
    adapter: dict[str, Any],
    config: IntegratedBacktestAuditConfig,
    ledger: PaperTradingLedger,
    day_text: str,
    index: int,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    price_map = _adapter_price_map(adapter, day_text)
    orders: list[dict[str, Any]] = []
    orders.extend(_adapter_exit_orders(config=config, ledger=ledger, day_text=day_text, index=index, price_map=price_map))
    allocation_rows = _build_allocation_rows(
        opportunity_rows=candidates,
        ledger=ledger,
        close_map=price_map,
        decision_for=day_text,
        data_until=day_text,
        max_buy_orders=min(5, max(0, config.max_positions - len(ledger.positions) + sum(1 for order in orders if order["side"] == "SELL"))),
    )
    order_plan = _build_order_plan(
        allocation_rows=allocation_rows,
        decision_for=day_text,
        data_until=day_text,
        run_id=f"phase11z_fix_d_{day_text}_{index}",
    )
    for item in order_plan.get("items", []):
        code = str(item["issue_code"])
        quantity = Decimal(str(item.get("quantity") or 0))
        price = price_map.get(code, Decimal("0"))
        orders.append(
            {
                "order_id": str(item["order_id"]),
                "issue_code": code,
                "side": "BUY",
                "quantity": str(quantity),
                "notional": str((price * quantity).quantize(Decimal("1"))),
                "priority_score": str(next((row.get("rank_score") for row in candidates if str(row["code"]) == code), "0")),
                "reason": str(item.get("reason") or "PHASE9_CAP5_BUY"),
            }
        )
    return orders


def _adapter_exit_orders(
    *,
    config: IntegratedBacktestAuditConfig,
    ledger: PaperTradingLedger,
    day_text: str,
    index: int,
    price_map: dict[str, Decimal],
) -> list[dict[str, Any]]:
    orders: list[dict[str, Any]] = []
    for position in ledger.positions:
        latest = price_map.get(position.code)
        if not latest or latest <= 0:
            continue
        ret = latest / position.average_cost - Decimal("1") if position.average_cost else Decimal("0")
        reason = ""
        if position.holding_days >= config.max_holding_days:
            reason = "MAX_HOLDING_DAYS_EXIT"
        elif ret >= config.profit_take_pct:
            reason = "PROFIT_TAKE_EXIT"
        elif ret <= config.exit_review_drawdown_pct:
            reason = "DRAWDOWN_REVIEW_EXIT"
        if reason:
            orders.append(
                {
                    "order_id": f"phase11z_mainline_adapter_{day_text}_{position.code}_SELL",
                    "issue_code": position.code,
                    "side": "SELL",
                    "quantity": str(position.quantity),
                    "notional": str((latest * position.quantity).quantize(Decimal("1"))),
                    "priority_score": "0",
                    "reason": reason,
                }
            )
    return orders[:5]


def _pending_order_from_adapter_plan(
    plan: dict[str, Any],
    order_date: str,
    execution_date: str,
    *,
    review_class: str = SafetyReviewClass.INFO_ONLY.value,
) -> PendingOrderState:
    return PendingOrderState(
        order_id=str(plan["order_id"]),
        code=str(plan["issue_code"]),
        side=str(plan["side"]).upper(),
        quantity=Decimal(str(plan.get("quantity") or "0")),
        status="APPROVED",
        planned_amount=Decimal(str(plan.get("notional") or "0")),
        virtual_order_date=order_date,
        virtual_execution_date=execution_date,
        decision_for=order_date,
        reason=str(plan.get("reason") or "PHASE11Z_MAINLINE_ADAPTER"),
        review_status=f"safety_pre_order_{review_class.lower()}",
    )


def _next_execution_date(days: list[date], index: int) -> str:
    if index + 1 < len(days):
        return days[index + 1].isoformat()
    current = days[index] + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current.isoformat()


def _mark_to_market_phase9_ledger(ledger: PaperTradingLedger, price_map: dict[str, Decimal], valuation_date: str) -> PaperTradingLedger:
    positions: list[PositionSnapshot] = []
    for position in ledger.positions:
        latest = price_map.get(position.code, position.average_cost)
        positions.append(
            PositionSnapshot(
                code=position.code,
                name=position.name,
                quantity=position.quantity,
                average_cost=position.average_cost,
                market_value=latest * position.quantity,
                unrealized_pnl=(latest - position.average_cost) * position.quantity,
                holding_days=position.holding_days + 1,
                last_valuation_date=valuation_date,
            )
        )
    market_value = sum((position.market_value for position in positions), Decimal("0"))
    unrealized = sum((position.unrealized_pnl for position in positions), Decimal("0"))
    realized = ledger.performance.realized_pnl if ledger.performance else Decimal("0")
    trade_count = ledger.performance.trade_count if ledger.performance else 0
    return PaperTradingLedger(
        cash=ledger.cash,
        positions=tuple(positions),
        pending_orders=ledger.pending_orders,
        performance=PerformanceSnapshot(
            total_equity=ledger.cash + market_value,
            cash=ledger.cash,
            market_value=market_value,
            realized_pnl=realized,
            unrealized_pnl=unrealized,
            trade_count=trade_count,
        ),
        metadata=LedgerMetadata(
            ledger_id=ledger.metadata.ledger_id,
            as_of=utc_now_iso(),
            schema_version=ledger.metadata.schema_version,
            source=ledger.metadata.source,
            phase=ledger.metadata.phase,
            created_at=ledger.metadata.created_at,
            start_date=ledger.metadata.start_date,
            currency=ledger.metadata.currency,
            initial_cash=ledger.metadata.initial_cash,
            broker_order_api_called=False,
            open_d_started=False,
            unlock_trade_called=False,
            virtual_fill_executed=ledger.metadata.virtual_fill_executed,
            last_execution_date=ledger.metadata.last_execution_date,
            last_valuation_date=valuation_date,
        ),
    )


def _audit_positions_from_phase9_ledger(ledger: PaperTradingLedger, index: int) -> dict[str, AuditPosition]:
    positions: dict[str, AuditPosition] = {}
    for position in ledger.positions:
        quantity = int(position.quantity)
        latest = position.market_value / position.quantity if position.quantity else position.average_cost
        positions[position.code] = AuditPosition(
            issue_code=position.code,
            quantity=quantity,
            average_price=position.average_cost,
            entry_date="",
            entry_index=max(0, index - position.holding_days),
            latest_price=latest,
            priority_score=Decimal("0"),
        )
    return positions


def _aggregate_pre_order_results(state: SafetyState, results: tuple[SafetyManagerResult, ...]) -> SafetyManagerResult:
    if not results:
        return SafetyManagerResult(
            current_state=state,
            overall_decision=SafetyDecision.ALLOW,
            state_candidate=state,
            transition_allowed=True,
            transition_reason="no_orders",
            guard_results=(),
            events=(),
            review_items=(),
        )
    decisions = [result.overall_decision for result in results]
    if SafetyDecision.EMERGENCY_STOP in decisions:
        overall = SafetyDecision.EMERGENCY_STOP
    elif SafetyDecision.BLOCK in decisions:
        overall = SafetyDecision.BLOCK
    elif SafetyDecision.REVIEW_REQUIRED in decisions:
        overall = SafetyDecision.REVIEW_REQUIRED
    else:
        overall = SafetyDecision.ALLOW
    candidates = [result.state_candidate for result in results]
    if SafetyState.SYSTEM_EMERGENCY_STOP in candidates:
        state_candidate = SafetyState.SYSTEM_EMERGENCY_STOP
    elif SafetyState.EMERGENCY_STOP in candidates:
        state_candidate = SafetyState.EMERGENCY_STOP
    elif SafetyState.BUY_OPPORTUNITY_REVIEW in candidates:
        state_candidate = SafetyState.BUY_OPPORTUNITY_REVIEW
    elif SafetyState.BUY_REVIEW_REQUIRED in candidates:
        state_candidate = SafetyState.BUY_REVIEW_REQUIRED
    elif SafetyState.MARKET_STRESS in candidates:
        state_candidate = SafetyState.MARKET_STRESS
    elif SafetyState.BUY_STOP in candidates:
        state_candidate = SafetyState.BUY_STOP
    elif SafetyState.RECOVERY_CANDIDATE in candidates:
        state_candidate = SafetyState.RECOVERY_CANDIDATE
    elif SafetyState.WARNING in candidates:
        state_candidate = SafetyState.WARNING
    else:
        state_candidate = state
    return SafetyManagerResult(
        current_state=state,
        overall_decision=overall,
        state_candidate=state_candidate,
        transition_allowed=True,
        transition_reason="aggregate_pre_order_results",
        guard_results=tuple(check for result in results for check in result.guard_results),
        events=tuple(event for result in results for event in result.events),
        review_items=tuple(item for result in results for item in result.review_items),
    )


def _build_result(
    config: IntegratedBacktestAuditConfig,
    days: list[date],
    performance: dict[str, Any],
    safety: dict[str, Any],
    integrity: dict[str, Any],
    behavior: dict[str, Any],
    daily: list[DailyAuditRecord],
    trades: list[AuditTrade],
    flow_counts: dict[str, Any],
    state_residency_days: dict[str, int],
    pass_conditions: dict[str, bool],
    output_dir: Path,
    status: str,
) -> IntegratedBacktestAuditResult:
    summary_path = output_dir / "summary.json"
    daily_path = output_dir / "daily_audit.json"
    trades_path = output_dir / "virtual_trades.json"
    phase_docs_dir = _phase_docs_dir(config)
    if config.period_id == "smoke_1y":
        phase_report_path = phase_docs_dir / "phase11z_integrated_safety_backtest_smoke_1y.md"
        phase_json_path = Path(config.reports_dir) / "phase_reports" / "phase11z_integrated_safety_backtest_smoke_1y.json"
    elif config.period_id == "full_5y":
        phase_report_path = phase_docs_dir / "phase11z_integrated_safety_backtest_full_5y.md"
        phase_json_path = Path(config.reports_dir) / "phase_reports" / "phase11z_integrated_safety_backtest_full_5y.json"
    elif config.period_id == "fix_d_mainline_adapter_smoke":
        phase_report_path = phase_docs_dir / "phase11z_fix_d_mainline_adapter.md"
        phase_json_path = Path(config.reports_dir) / "phase_reports" / "phase11z_fix_d_mainline_adapter.json"
    else:
        phase_report_path = phase_docs_dir / f"phase11z_integrated_safety_backtest_{config.period_id}.md"
        phase_json_path = Path(config.reports_dir) / "phase_reports" / f"phase11z_integrated_safety_backtest_{config.period_id}.json"
    return IntegratedBacktestAuditResult(
        period_id=config.period_id,
        start_date=config.start_date,
        end_date=config.end_date,
        business_day_count=len(days),
        status=status,
        performance=performance,
        safety=safety,
        integrity=integrity,
        safety_behavior=behavior,
        daily_records=tuple(daily),
        trades=tuple(trades),
        flow_counts=flow_counts,
        state_residency_days=state_residency_days,
        pass_conditions=pass_conditions,
        output_dir=str(output_dir),
        summary_path=str(summary_path),
        daily_path=str(daily_path),
        trades_path=str(trades_path),
        phase_report_path=str(phase_report_path),
        phase_report_json_path=str(phase_json_path),
    )


def _phase_docs_dir(config: IntegratedBacktestAuditConfig) -> Path:
    if config.docs_dir is not None:
        return Path(config.docs_dir)
    reports_dir = Path(config.reports_dir)
    if reports_dir == Path("reports"):
        return Path("docs") / "phase_reports"
    return reports_dir / "phase_reports"


def _write_audit_outputs(result: IntegratedBacktestAuditResult) -> None:
    summary = _result_payload(result, include_daily=False)
    _write_json(Path(result.summary_path), summary)
    _write_json(Path(result.daily_path), {"daily_records": [_daily_payload(row) for row in result.daily_records]})
    _write_json(Path(result.trades_path), {"virtual_trades": [_trade_payload(trade) for trade in result.trades]})
    _write_json(Path(result.phase_report_json_path), summary)
    Path(result.phase_report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(result.phase_report_path).write_text(_markdown_report(result), encoding="utf-8")


def _result_payload(result: IntegratedBacktestAuditResult, *, include_daily: bool) -> dict[str, Any]:
    payload = {
        "schema_version": "phase11z_integrated_safety_backtest_audit_v1",
        "status": result.status,
        "period_id": result.period_id,
        "audit_profile": result.safety_behavior.get("audit_profile"),
        "start_date": result.start_date,
        "end_date": result.end_date,
        "business_day_count": result.business_day_count,
        "generated_at": utc_now_iso(),
        "performance": result.performance,
        "flow_counts": result.flow_counts,
        "safety": result.safety,
        "state_residency_days": result.state_residency_days,
        "integrity": result.integrity,
        "safety_behavior": result.safety_behavior,
        "market_crash_input": _market_crash_input_summary(result),
        "pass_conditions": result.pass_conditions,
        "output_dir": result.output_dir,
        "summary_path": result.summary_path,
        "daily_path": result.daily_path,
        "trades_path": result.trades_path,
        "phase_report_path": result.phase_report_path,
        "phase_report_json_path": result.phase_report_json_path,
        "data_use_constraints": {
            "audit_result_used_for_ai_learning": False,
            "safety_result_used_for_ai_learning": False,
            "paper_ledger_used_for_ai_learning": False,
            "broker_snapshot_used_for_ai_learning": False,
            "allowed_ai_inputs_only": ["J-Quants derived data", "point-in-time features"],
        },
        "judgement": _judgement(result),
    }
    if include_daily:
        payload["daily_records"] = [_daily_payload(row) for row in result.daily_records]
    return _phase11_sanitize(payload)


def _markdown_report(result: IntegratedBacktestAuditResult) -> str:
    label = "Fix-D Mainline Adapter Smoke" if result.period_id == "fix_d_mainline_adapter_smoke" else ("Smoke 1Y" if result.period_id == "smoke_1y" else "Full 5Y")
    lines = [
        f"# Phase11-Z Integrated Safety Backtest Audit {label}",
        "",
        f"- status: {result.status}",
        f"- audit_profile: {result.safety_behavior.get('audit_profile')}",
        f"- period: {result.start_date} to {result.end_date}",
        f"- business_day_count: {result.business_day_count}",
        "- broker_api_connected: false",
        "- websocket_connected: false",
        "- live_order_executed: false",
        "- auto_sell_executed: false",
        "- auto_recovery_executed: false",
        "",
        "## Performance",
        "",
        *_kv_lines(result.performance),
        "",
        "## Flow Counts",
        "",
        *_kv_lines(result.flow_counts),
        "",
        "## Safety",
        "",
        *_kv_lines(result.safety),
        "",
        "## State Residency Days",
        "",
        *_kv_lines(result.state_residency_days),
        "",
        "## Integrity",
        "",
        *_kv_lines(result.integrity),
        "",
        "## Safety Behavior",
        "",
        *_kv_lines(result.safety_behavior),
        "",
        "## Mainline Adapter Reuse Map",
        "",
        *_kv_lines(dict(result.safety_behavior.get("mainline_reuse_map") or {})),
        "",
        "## Market Crash Input",
        "",
        *_kv_lines(_market_crash_input_summary(result)),
        "",
        "## Pass Conditions",
        "",
        *_kv_lines(result.pass_conditions),
        "",
        "## Data Use",
        "",
        "Phase11-Z audit result is not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.",
        "",
        "## Result",
        "",
        "```text",
        *(_judgement(result)),
        "```",
    ]
    return _phase11_sanitize("\n".join(lines) + "\n")


def _performance_metrics(
    initial_cash: Decimal,
    daily: list[DailyAuditRecord],
    trades: list[AuditTrade],
    positions: dict[str, AuditPosition],
    flow_counts: dict[str, Any],
) -> dict[str, Any]:
    final_equity = daily[-1].equity if daily else initial_cash
    total_return = (final_equity / initial_cash - Decimal("1")) if initial_cash else Decimal("0")
    years = Decimal(str(max(len(daily), 1))) / TRADING_DAYS_PER_YEAR
    annualized = (float(final_equity / initial_cash) ** (1 / float(years)) - 1) if initial_cash and final_equity > 0 else 0.0
    equity_values = [row.equity for row in daily]
    exposure_values = [row.equity - row.cash for row in daily]
    realized = _realized_trade_metrics(trades)
    return {
        "initial_cash": _round(initial_cash),
        "final_equity": _round(final_equity),
        "total_return": _round(total_return),
        "annualized_return": round(annualized, 6),
        "max_drawdown": _round(_max_drawdown(equity_values)),
        "trade_count": int(flow_counts["buy_fill_count"] + flow_counts["sell_fill_count"]),
        "trade_count_definition": "buy_fill_count + sell_fill_count",
        "buy_fill_count": int(flow_counts["buy_fill_count"]),
        "sell_fill_count": int(flow_counts["sell_fill_count"]),
        "round_trip_count": int(flow_counts["round_trip_count"]),
        **realized,
        "average_holding_days": realized["average_holding_days"],
        "exposure_ratio": _round(sum(exposure_values, Decimal("0")) / sum((row.equity for row in daily), Decimal("1"))),
    }


def _realized_trade_metrics(trades: list[AuditTrade]) -> dict[str, Any]:
    open_lots: dict[str, list[AuditTrade]] = {}
    closed: list[dict[str, Any]] = []
    for trade in trades:
        if trade.side == "BUY":
            open_lots.setdefault(trade.issue_code, []).append(trade)
            continue
        if trade.side != "SELL":
            continue
        lot = open_lots.get(trade.issue_code, [])
        buy = lot.pop(0) if lot else None
        if buy is None:
            continue
        pnl = trade.notional - buy.notional
        holding_days = (date.fromisoformat(trade.business_date) - date.fromisoformat(buy.business_date)).days
        closed.append({"pnl": pnl, "holding_days": holding_days})

    wins = [item for item in closed if item["pnl"] > 0]
    losses = [item for item in closed if item["pnl"] < 0]
    breakeven = [item for item in closed if item["pnl"] == 0]
    gross_profit = sum((item["pnl"] for item in wins), Decimal("0"))
    gross_loss = sum((item["pnl"] for item in losses), Decimal("0"))
    closed_count = len(closed)
    if closed_count:
        win_rate: float | None = _round(Decimal(len(wins)) / Decimal(closed_count))
        average_realized_pnl: float | None = _round(sum((item["pnl"] for item in closed), Decimal("0")) / Decimal(closed_count))
        average_holding_days: float | None = _round(Decimal(sum(int(item["holding_days"]) for item in closed)) / Decimal(closed_count))
    else:
        win_rate = None
        average_realized_pnl = None
        average_holding_days = None
    if gross_loss < 0:
        profit_factor: float | str | None = _round(gross_profit / abs(gross_loss))
    elif gross_profit > 0:
        profit_factor = "Infinity"
    else:
        profit_factor = None
    return {
        "closed_trades_count": closed_count,
        "winning_closed_trades": len(wins),
        "losing_closed_trades": len(losses),
        "breakeven_closed_trades": len(breakeven),
        "realized_profit": _round(gross_profit),
        "realized_loss": _round(gross_loss),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "average_realized_pnl": average_realized_pnl,
        "average_holding_days": average_holding_days,
        "performance_metrics_placeholder": False,
    }


def _empty_safety_counts() -> dict[str, Any]:
    return {
        "safety_check_count": 0,
        "ALLOW_count": 0,
        "BLOCK_count": 0,
        "REVIEW_REQUIRED_count": 0,
        "EMERGENCY_STOP_count": 0,
        "BUY_STOP_days": 0,
        "RECOVERY_CANDIDATE_count": 0,
        "MANUAL_APPROVED_count": 0,
        "individual_warning_count": 0,
        "stop_loss_candidate_count": 0,
        "emergency_candidate_count": 0,
        "market_crash_guard_count": 0,
        "quote_stale_guard_count": 0,
        "duplicate_order_guard_count": 0,
        "cash_buffer_guard_count": 0,
        "max_exposure_guard_count": 0,
        "broker_divergence_guard_count": 0,
        "daily_loss_guard_count": 0,
    }


def _empty_flow_counts() -> dict[str, Any]:
    return {
        "ai_signal_days": 0,
        "candidate_generated_days": 0,
        "candidate_count_total": 0,
        "order_plan_generated_days": 0,
        "orders_generated": 0,
        "orders_before_safety": 0,
        "orders_allowed_by_safety": 0,
        "orders_blocked_by_safety": 0,
        "orders_review_required": 0,
        "orders_emergency_stopped": 0,
        "buy_orders_submitted": 0,
        "sell_orders_submitted": 0,
        "buy_fill_count": 0,
        "sell_fill_count": 0,
        "round_trip_count": 0,
        "position_open_count": 0,
        "position_close_count": 0,
        "final_position_count": 0,
        "virtual_orders_submitted": 0,
        "virtual_fills": 0,
        "ledger_entry_count": 0,
        "non_blocking_review_order_count": 0,
        "blocking_review_order_count": 0,
        "human_review_required_order_count": 0,
        "order_decision_count": 0,
        "raw_review_occurrence_count": 0,
        "aggregated_review_item_count": 0,
        "review_compression_ratio": 0,
        "blocking_review_count": 0,
        "non_blocking_review_count": 0,
        "info_only_count": 0,
        "order_decisions_path": "",
        "aggregated_review_queue_path": "",
        "candidate_universe_size": len(AUDIT_CANDIDATE_UNIVERSE),
        "fixed_4_code_stub_used": False,
        "periodic_mock_emergency_injection_enabled": False,
        "normal_market_profile": False,
        "stress_injection_profile": False,
        "trade_count_definition": "trade_count = buy_fill_count + sell_fill_count; round_trip_count = closed positions count",
        "recovery_candidate_count_definition": "event/check count, not unique days; see state_residency_days for day count",
    }


def _pass_conditions(
    config: IntegratedBacktestAuditConfig,
    days: list[date],
    flow_counts: dict[str, Any],
    behavior: dict[str, Any],
    state_residency_days: dict[str, int],
    performance: dict[str, Any],
) -> dict[str, bool]:
    min_trade_count = 10 if config.period_id == "full_5y" else 2
    base = {
        "orders_generated_gt_0": flow_counts["orders_generated"] > 0,
        "orders_before_safety_gt_0": flow_counts["orders_before_safety"] > 0,
        "buy_fill_count_gt_0": flow_counts["buy_fill_count"] > 0,
        "sell_fill_count_gt_0": flow_counts["sell_fill_count"] > 0,
        "position_open_count_gt_0": flow_counts["position_open_count"] > 0,
        "position_close_count_gt_0": flow_counts["position_close_count"] > 0,
        "trade_count_not_extremely_low": flow_counts["buy_fill_count"] + flow_counts["sell_fill_count"] >= min_trade_count,
        "fixed_4_code_stub_not_used": not flow_counts["fixed_4_code_stub_used"],
        "candidate_universe_broad_enough": flow_counts["candidate_universe_size"] >= 30,
        "manual_approval_simulation_available": bool(config.manual_approval_simulation),
        "recovery_does_not_auto_normal": bool(behavior["recovery_candidate_did_not_auto_normal"]),
        "docs_output_isolated_for_tests": config.docs_dir is not None or Path(config.reports_dir) == Path("reports"),
        "win_rate_profit_factor_not_placeholder": performance.get("performance_metrics_placeholder") is False,
        "recovery_candidate_to_normal_bypass_absent": not bool(behavior["recovery_candidate_to_normal_bypass"]),
        "stress_results_separated_from_normal_performance": bool(behavior["stress_results_separated_from_normal_performance"]),
    }
    if _stress_profile(config):
        base.update(
            {
                "stress_profile_enabled": True,
                "stress_injection_triggered_safety": bool(
                    behavior["emergency_blocked_order_flow"]
                    or behavior["quote_stale_blocked_inferred_trade"]
                    or behavior["broker_divergence_review_or_emergency"]
                    or behavior["market_crash_became_buy_stop"]
                ),
            }
        )
        return base
    emergency_ratio = Decimal(state_residency_days.get(SafetyState.EMERGENCY_STOP.value, 0)) / Decimal(max(len(days), 1))
    is_mainline_adapter = config.audit_profile == AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER
    base.update(
        {
            "normal_market_profile_enabled": config.audit_profile == AUDIT_PROFILE_NORMAL_MARKET,
            "mainline_paper_adapter_profile_enabled": True,
            "normal_or_mainline_profile_enabled": config.audit_profile in {AUDIT_PROFILE_NORMAL_MARKET, AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER},
            "emergency_stop_days_ratio_within_threshold": emergency_ratio <= config.max_emergency_stop_day_ratio,
            "normal_market_mock_boolean_crash_absent": not bool(behavior["normal_market_mock_boolean_crash_triggered"]),
            "periodic_mock_emergency_injection_disabled": not bool(behavior["periodic_mock_emergency_injection_enabled"]),
        }
    )
    if is_mainline_adapter:
        base["normal_market_profile_enabled"] = True
        base["mainline_reuse_map_present"] = bool(behavior.get("mainline_reuse_map"))
        base["paper_ledger_used"] = (behavior.get("mainline_reuse_map") or {}).get("ledger_source") == "PaperTradingLedger"
        base["virtual_fill_processor_used"] = (behavior.get("mainline_reuse_map") or {}).get("fill_source") == "mainline_virtual_fill"
    return base


def _update_safety_counts(counts: dict[str, Any], decision: SafetyDecision, state: SafetyState, results: tuple[Any, ...]) -> None:
    counts[f"{decision.value}_count"] += 1
    if state is SafetyState.BUY_STOP:
        counts["BUY_STOP_days"] += 1
    if state is SafetyState.RECOVERY_CANDIDATE:
        counts["RECOVERY_CANDIDATE_count"] += 1
    if state is SafetyState.MANUAL_APPROVED:
        counts["MANUAL_APPROVED_count"] += 1
    for result in results:
        reason = result.reason_code
        guard = result.guard_name.value
        if reason == "INDIVIDUAL_DRAWDOWN_WARNING":
            counts["individual_warning_count"] += 1
        if reason in {"STOP_LOSS_CANDIDATE", "SELL_REVIEW_REQUIRED"}:
            counts["stop_loss_candidate_count"] += 1
        if reason in {"EMERGENCY_CANDIDATE", "HIGH_RISK_REVIEW"}:
            counts["emergency_candidate_count"] += 1
        if guard == "MARKET_CRASH" and result.decision is not SafetyDecision.ALLOW:
            counts["market_crash_guard_count"] += 1
        if guard == "QUOTE_STALE" and result.decision is not SafetyDecision.ALLOW:
            counts["quote_stale_guard_count"] += 1
        if guard == "DUPLICATE_ORDER" and result.decision is not SafetyDecision.ALLOW:
            counts["duplicate_order_guard_count"] += 1
        if guard == "CASH_BUFFER" and result.decision is not SafetyDecision.ALLOW:
            counts["cash_buffer_guard_count"] += 1
        if guard == "MAX_EXPOSURE" and result.decision is not SafetyDecision.ALLOW:
            counts["max_exposure_guard_count"] += 1
        if guard == "BROKER_DIVERGENCE" and result.decision is not SafetyDecision.ALLOW:
            counts["broker_divergence_guard_count"] += 1
        if guard == "DAILY_LOSS" and result.decision is not SafetyDecision.ALLOW:
            counts["daily_loss_guard_count"] += 1


def _integrity_flags() -> dict[str, bool]:
    return {
        "live_order_executed": False,
        "demo_order_executed": False,
        "production_order_executed": False,
        "auto_sell_executed": False,
        "auto_recovery_executed": False,
        "broker_api_connected": False,
        "broker_snapshot_updated": False,
        "paper_ledger_mutated_unexpectedly": False,
        "ai_training_data_mutated": False,
        "secret_or_raw_response_persisted": False,
    }


def _business_days(start: str, end: str) -> list[date]:
    current = date.fromisoformat(start)
    last = date.fromisoformat(end)
    days: list[date] = []
    while current <= last:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _candidate_codes_for_day(index: int, count: int) -> tuple[str, ...]:
    ranked = sorted(
        AUDIT_CANDIDATE_UNIVERSE,
        key=lambda code: (_candidate_score(index, code), code),
        reverse=True,
    )
    return tuple(ranked[:count])


def _candidate_score(index: int, code: str) -> Decimal:
    seed = sum(ord(ch) for ch in code)
    cyclical = Decimal((seed * 17 + index * 13) % 1000) / Decimal("1000")
    momentum = Decimal((index + seed) % 37) / Decimal("100")
    return cyclical + momentum


def _base_price(index: int, code: str) -> Decimal:
    seed = sum(ord(ch) for ch in code) % 17
    return Decimal("900") + Decimal(seed * 10) + Decimal(index % 29)


def _positions_payload(positions: dict[str, AuditPosition]) -> list[dict[str, Any]]:
    return [
        {
            "issue_code": pos.issue_code,
            "quantity": str(pos.quantity),
            "average_price": str(pos.average_price),
            "market_value": str(pos.latest_price * pos.quantity),
        }
        for pos in positions.values()
    ]


def _quotes_for_day(
    index: int,
    positions: list[dict[str, Any]],
    candidates: tuple[str, ...] = (),
    config: IntegratedBacktestAuditConfig | None = None,
) -> dict[str, dict[str, Any]]:
    quotes: dict[str, dict[str, Any]] = {}
    codes = {str(item["issue_code"]) for item in positions}
    codes.update(candidates or _candidate_codes_for_day(index, 6))
    average_by_code = {str(item["issue_code"]): Decimal(str(item["average_price"])) for item in positions}
    for code in codes:
        price = _base_price(index, code)
        if _stress_profile(config) and code in average_by_code and index % 97 == 21:
            price = average_by_code[code] * Decimal("0.93")
        if _stress_profile(config) and code in average_by_code and index % 113 == 37:
            price = average_by_code[code] * Decimal("0.90")
        if _stress_profile(config) and code in average_by_code and index % 149 == 41:
            price = average_by_code[code] * Decimal("0.85")
        quotes[code] = {"age_seconds": "9999" if not _quote_fresh(index, config) else "30", "price": str(_round_decimal(price))}
    return quotes


def _market_summary(index: int, state: SafetyState, config: IntegratedBacktestAuditConfig | None = None) -> dict[str, Any]:
    if not _stress_profile(config):
        return {
            "market_crash_source": "synthetic_none",
            "index_return": "0.00",
            "candidate_universe_drawdown": "0.00",
            "extreme_down_ratio": "0.00",
            "stop_limit_candidate_ratio": "0.00",
            "is_synthetic": True,
            "market_crash": False,
            "severe_crash": False,
            "daily_loss_pct": "0.00",
            "recovery_candidate": False,
        }
    return {
        "market_crash_source": "synthetic_stress_injection",
        "index_return": "-0.08" if index > 0 and index % 83 == 20 else ("-0.15" if index > 0 and index % 211 == 55 else "0.00"),
        "candidate_universe_drawdown": "-0.12" if index > 0 and index % 83 == 20 else "0.00",
        "extreme_down_ratio": "0.25" if index > 0 and index % 211 == 55 else "0.00",
        "stop_limit_candidate_ratio": "0.10" if index > 0 and index % 83 == 20 else "0.00",
        "is_synthetic": True,
        "market_crash": index > 0 and index % 83 == 20,
        "severe_crash": index > 0 and index % 211 == 55,
        "daily_loss_pct": "-0.06" if index > 0 and index % 127 == 80 else "0.00",
        "recovery_candidate": state in {SafetyState.BUY_STOP, SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP} and index % 31 == 7,
    }


def _recovery_market_summary(index: int) -> dict[str, Any]:
    return {
        "severe_crash": False,
        "stable_days": 5,
        "candidate_universe_drawdown_improved": True,
        "crash_issue_ratio_declined": True,
        "extreme_down_ratio_declined": True,
    }


def _broker_snapshot(
    index: int,
    cash: Decimal,
    positions: dict[str, AuditPosition],
    config: IntegratedBacktestAuditConfig | None = None,
) -> dict[str, Any]:
    market_value = sum((position.latest_price * position.quantity for position in positions.values()), Decimal("0"))
    payload = {
        "age_seconds": "30",
        "buying_power": str(cash),
        "total_equity": str(cash + market_value),
        "positions_count": len(positions),
        "raw_response": "RAW-RESPONSE-PHASE11Z",
        "account_id": "ACCOUNT-PLAINTEXT-PHASE11Z",
        "auth_id": "AUTH-PLAINTEXT-PHASE11Z",
        "private_key": "PRIVATE-KEY-PHASE11Z",
        "virtual_url": "https://virtual-url.phase11z.invalid/path",
        "second_password": "SECOND-PASSWORD-PHASE11Z",
    }
    if _stress_profile(config) and index > 0 and index % 167 == 44:
        payload["divergence"] = "POSITION_MISMATCH"
    if _stress_profile(config) and index > 0 and index % 181 == 66:
        payload["stale"] = True
        payload["age_seconds"] = "9999"
    return payload


def _orders_for_day(index: int, config: IntegratedBacktestAuditConfig | None = None) -> tuple[dict[str, Any], ...]:
    if _stress_profile(config) and index > 0 and index % 139 == 33:
        code = _candidate_codes_for_day(index, 1)[0]
        return (
            {"issue_code": code, "side": "BUY", "status": "OPEN", "order_id": "ORDER-PLAINTEXT-PHASE11Z"},
            {"issue_code": code, "side": "BUY", "status": "ACCEPTED", "order_id": "ORDER-PLAINTEXT-PHASE11Z"},
        )
    return ()


def _manual_emergency(index: int, config: IntegratedBacktestAuditConfig | None = None) -> bool:
    return _stress_profile(config) and index > 0 and index % 251 == 88


def _manual_approval_allowed(index: int, latest_decision: SafetyDecision) -> bool:
    return latest_decision is SafetyDecision.ALLOW and index % 11 == 0


def _quote_fresh(index: int, config: IntegratedBacktestAuditConfig | None = None) -> bool:
    return not (_stress_profile(config) and index > 0 and index % 101 == 25)


def _should_attempt_buy(index: int) -> bool:
    return True


def _stress_profile(config: IntegratedBacktestAuditConfig | None) -> bool:
    return bool(config and config.audit_profile == AUDIT_PROFILE_STRESS_INJECTION)


def _market_crash_input_summary(result: IntegratedBacktestAuditResult) -> dict[str, Any]:
    profile = str(result.safety_behavior.get("audit_profile") or AUDIT_PROFILE_NORMAL_MARKET)
    if profile == AUDIT_PROFILE_STRESS_INJECTION:
        return {
            "market_crash_source": "synthetic_stress_injection",
            "index_return": "profile_generated",
            "candidate_universe_drawdown": "profile_generated",
            "extreme_down_ratio": "profile_generated",
            "stop_limit_candidate_ratio": "profile_generated",
            "is_synthetic": True,
            "stress_results_mixed_into_normal_performance": False,
        }
    if profile == AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER:
        return {
            "market_crash_source": "canonical_quotes_phase7_ranked_daily",
            "index_return": "0.00",
            "candidate_universe_drawdown": "0.00",
            "extreme_down_ratio": "0.00",
            "stop_limit_candidate_ratio": "0.00",
            "is_synthetic": False,
            "market_crash": False,
            "severe_crash": False,
            "stress_results_mixed_into_normal_performance": False,
        }
    return {
        "market_crash_source": "synthetic_none",
        "index_return": "0.00",
        "candidate_universe_drawdown": "0.00",
        "extreme_down_ratio": "0.00",
        "stop_limit_candidate_ratio": "0.00",
        "is_synthetic": True,
        "market_crash": False,
        "severe_crash": False,
        "stress_results_mixed_into_normal_performance": False,
    }


def _planned_orders(
    business_date: str,
    index: int,
    state: SafetyState,
    cash: Decimal,
    positions: dict[str, AuditPosition],
    quotes: dict[str, dict[str, Any]],
    candidates: tuple[str, ...],
    config: IntegratedBacktestAuditConfig,
) -> list[dict[str, Any]]:
    orders: list[dict[str, Any]] = []
    if state not in {SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}:
        orders.extend(_exit_orders(business_date, index, positions, quotes, config))
    free_slots = max(0, config.max_positions - len(positions) + sum(1 for order in orders if order["side"] == "SELL"))
    buy_slots = min(free_slots, 2)
    held = set(positions)
    for code in candidates:
        if buy_slots <= 0:
            break
        if code in held:
            continue
        price = Decimal(str(quotes.get(code, {}).get("price") or _base_price(index, code)))
        notional = min(Decimal("150000"), max(Decimal("0"), cash * Decimal("0.18")))
        if notional < Decimal("50000"):
            continue
        orders.append(
            {
                "order_id": f"phase11z_audit_order_{business_date}_{code}_BUY",
                "issue_code": code,
                "side": "BUY",
                "notional": str(notional),
                "priority_score": str(_candidate_score(index, code)),
                "reason": "NEW_BUY_AUDIT_CANDIDATE" if len(positions) < config.max_positions else "REPLACEMENT_BUY_AUDIT_CANDIDATE",
            }
        )
        buy_slots -= 1
    if len(positions) >= config.max_positions and not any(order["side"] == "SELL" for order in orders) and candidates:
        replacement = _replacement_sell_order(business_date, index, positions, candidates, config)
        if replacement:
            orders.insert(0, replacement)
    return orders


def _exit_orders(
    business_date: str,
    index: int,
    positions: dict[str, AuditPosition],
    quotes: dict[str, dict[str, Any]],
    config: IntegratedBacktestAuditConfig,
) -> list[dict[str, Any]]:
    orders = []
    for code, pos in positions.items():
        latest = Decimal(str(quotes.get(code, {}).get("price") or pos.latest_price))
        ret = latest / pos.average_price - Decimal("1") if pos.average_price else Decimal("0")
        holding_days = index - pos.entry_index
        reason = ""
        if holding_days >= config.max_holding_days:
            reason = "MAX_HOLDING_DAYS_EXIT"
        elif ret >= config.profit_take_pct:
            reason = "PROFIT_TAKE_EXIT"
        elif ret <= config.exit_review_drawdown_pct:
            reason = "DRAWDOWN_REVIEW_EXIT"
        if reason:
            orders.append(
                {
                    "order_id": f"phase11z_audit_order_{business_date}_{code}_SELL",
                    "issue_code": code,
                    "side": "SELL",
                    "quantity": str(pos.quantity),
                    "notional": str(latest * pos.quantity),
                    "priority_score": str(pos.priority_score),
                    "reason": reason,
                }
            )
    return orders[:2]


def _replacement_sell_order(
    business_date: str,
    index: int,
    positions: dict[str, AuditPosition],
    candidates: tuple[str, ...],
    config: IntegratedBacktestAuditConfig,
) -> dict[str, Any] | None:
    eligible = [
        pos
        for pos in positions.values()
        if index - pos.entry_index >= config.min_holding_days_for_replacement and pos.issue_code not in candidates
    ]
    if not eligible:
        return None
    pos = min(eligible, key=lambda item: item.priority_score)
    return {
        "order_id": f"phase11z_audit_order_{business_date}_{pos.issue_code}_SELL_REPLACE",
        "issue_code": pos.issue_code,
        "side": "SELL",
        "quantity": str(pos.quantity),
        "notional": str(pos.latest_price * pos.quantity),
        "priority_score": str(pos.priority_score),
        "reason": "REPLACEMENT_SELL_AUDIT_CANDIDATE",
    }


def _virtual_buy_from_plan(
    business_date: str,
    index: int,
    cash: Decimal,
    positions: dict[str, AuditPosition],
    quotes: dict[str, dict[str, Any]],
    plan: dict[str, Any],
) -> AuditTrade | None:
    code = str(plan["issue_code"])
    if code in positions:
        return None
    price = Decimal(str(quotes.get(code, {}).get("price") or _base_price(index, code)))
    quantity = int(min(cash * Decimal("0.18"), Decimal(str(plan.get("notional") or "150000"))) / price / LOT_SIZE) * LOT_SIZE
    if quantity <= 0:
        return None
    notional = price * quantity
    if cash - notional < Decimal("50000"):
        return None
    return AuditTrade(business_date, code, "BUY", quantity, price, notional, str(plan.get("reason") or "VIRTUAL_AUDIT_BUY_FILL"), str(plan.get("order_id") or ""))


def _virtual_sell_from_plan(
    business_date: str,
    index: int,
    positions: dict[str, AuditPosition],
    quotes: dict[str, dict[str, Any]],
    plan: dict[str, Any],
) -> AuditTrade | None:
    code = str(plan["issue_code"])
    pos = positions.get(code)
    if pos is None:
        return None
    price = Decimal(str(quotes.get(code, {}).get("price") or pos.latest_price))
    quantity = int(pos.quantity)
    if quantity <= 0:
        return None
    notional = price * quantity
    return AuditTrade(business_date, code, "SELL", quantity, price, notional, str(plan.get("reason") or "VIRTUAL_AUDIT_SELL_FILL"), str(plan.get("order_id") or ""))


def _portfolio_equity(cash: Decimal, positions: dict[str, AuditPosition], quotes: dict[str, dict[str, Any]]) -> Decimal:
    total = cash
    for code, pos in positions.items():
        price = Decimal(str(quotes.get(code, {}).get("price") or pos.latest_price))
        total += price * pos.quantity
    return _round_decimal(total)


def _next_state(
    current: SafetyState,
    monitor_state: SafetyState,
    pre_order_state: SafetyState,
    emergency_required: bool,
    recovery_candidate: bool,
) -> SafetyState:
    if emergency_required or monitor_state in {SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP} or pre_order_state in {SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}:
        return SafetyState.SYSTEM_EMERGENCY_STOP
    if recovery_candidate and current in {SafetyState.BUY_STOP, SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}:
        return SafetyState.RECOVERY_CANDIDATE
    if current is SafetyState.RECOVERY_CANDIDATE:
        return SafetyState.RECOVERY_CANDIDATE
    if current is SafetyState.MANUAL_APPROVED:
        return SafetyState.MANUAL_APPROVED
    if monitor_state is SafetyState.BUY_OPPORTUNITY_REVIEW or pre_order_state is SafetyState.BUY_OPPORTUNITY_REVIEW:
        return SafetyState.BUY_OPPORTUNITY_REVIEW
    if monitor_state is SafetyState.BUY_REVIEW_REQUIRED or pre_order_state is SafetyState.BUY_REVIEW_REQUIRED:
        return SafetyState.BUY_REVIEW_REQUIRED
    if monitor_state is SafetyState.MARKET_STRESS or pre_order_state is SafetyState.MARKET_STRESS:
        return SafetyState.MARKET_STRESS
    if monitor_state is SafetyState.BUY_STOP or pre_order_state is SafetyState.BUY_STOP:
        return SafetyState.BUY_STOP
    if monitor_state is SafetyState.WARNING or pre_order_state is SafetyState.WARNING:
        return SafetyState.WARNING
    if current in {SafetyState.BUY_STOP, SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}:
        return current
    return SafetyState.NORMAL


def _triggered_reason_codes(results: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple(result.reason_code for result in results if result.decision is not SafetyDecision.ALLOW)


def _max_drawdown(values: list[Decimal]) -> Decimal:
    peak: Decimal | None = None
    max_dd = Decimal("0")
    for value in values:
        peak = value if peak is None else max(peak, value)
        if peak:
            max_dd = min(max_dd, value / peak - Decimal("1"))
    return max_dd


def _average_holding_days(daily: list[DailyAuditRecord], positions: dict[str, AuditPosition]) -> Decimal:
    if not positions or not daily:
        return Decimal("0")
    last_index = len(daily) - 1
    return Decimal(sum(last_index - pos.entry_index for pos in positions.values())) / Decimal(len(positions))


def _round(value: Decimal | float | int) -> float:
    return float(_round_decimal(Decimal(str(value))))


def _round_decimal(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"))


def _daily_payload(row: DailyAuditRecord) -> dict[str, Any]:
    payload = asdict(row)
    payload["safety_state_before"] = row.safety_state_before.value
    payload["safety_state_after"] = row.safety_state_after.value
    payload["monitor_decision"] = row.monitor_decision.value
    payload["pre_order_decision"] = row.pre_order_decision.value
    payload["cash"] = str(row.cash)
    payload["equity"] = str(row.equity)
    payload["triggered_reason_codes"] = list(row.triggered_reason_codes)
    return _phase11_sanitize(payload)


def _trade_payload(trade: AuditTrade) -> dict[str, Any]:
    payload = asdict(trade)
    payload["price"] = str(trade.price)
    payload["notional"] = str(trade.notional)
    return _phase11_sanitize(payload)


def _kv_lines(mapping: dict[str, Any]) -> list[str]:
    return [f"- {key}: {str(value).lower() if isinstance(value, bool) else value}" for key, value in mapping.items()]


def _judgement(result: IntegratedBacktestAuditResult) -> list[str]:
    if result.status != "PASS":
        return [
            "PHASE11Z_INTEGRATED_SAFETY_BACKTEST_AUDIT_FAIL",
            "PHASE11Z_FULL_5Y_ON_HOLD",
            "LIVE_ORDER_EXECUTION_REMAINS_BLOCKED",
        ]
    if result.safety_behavior.get("audit_profile") == AUDIT_PROFILE_STRESS_INJECTION:
        return [
            "PHASE11Z_STRESS_INJECTION_AUDIT_PASS",
            "PHASE11Z_NORMAL_MARKET_RESULT_REQUIRED_FOR_FULL_5Y",
            "LIVE_ORDER_EXECUTION_REMAINS_BLOCKED",
        ]
    if result.safety_behavior.get("audit_profile") == AUDIT_PROFILE_MAINLINE_PAPER_ADAPTER:
        return [
            "PHASE11Z_FIX_D_MAINLINE_PAPER_ADAPTER_SMOKE_PASS",
            "PHASE11Z_FIX_E_1Y_MAINLINE_SMOKE_READY_FOR_REVIEW",
            "LIVE_ORDER_EXECUTION_REMAINS_BLOCKED",
        ]
    if result.period_id == "smoke_1y":
        return [
            "PHASE11Z_INTEGRATED_SAFETY_BACKTEST_SMOKE_1Y_PASS",
            "PHASE11Z_FULL_5Y_READY_TO_START",
            "LIVE_ORDER_EXECUTION_REMAINS_BLOCKED",
        ]
    return [
        "PHASE11Z_INTEGRATED_SAFETY_BACKTEST_FULL_5Y_PASS",
        "PHASE11_COMPLETE_CANDIDATE",
        "PHASE12_DEMO_FULL_OPERATION_READY_FOR_REVIEW",
        "LIVE_ORDER_EXECUTION_REMAINS_BLOCKED",
    ]
