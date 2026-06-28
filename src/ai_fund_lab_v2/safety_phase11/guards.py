from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from ai_fund_lab_v2.safety_phase11.models import (
    HumanReviewItem,
    SafetyCheckInput,
    SafetyCheckResult,
    SafetyDecision,
    SafetyEvent,
    SafetyGuardName,
    SafetySeverity,
    SafetyState,
    decimal_or_none,
    decimal_or_zero,
)
from ai_fund_lab_v2.safety_phase11.state_machine import coerce_state


class SafetyGuard(Protocol):
    guard_name: SafetyGuardName

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyCheckResult: ...


def _cash_available(check_input: SafetyCheckInput) -> Decimal | None:
    cash = decimal_or_none(check_input.order_plan.get("cash_basis"))
    if cash is None:
        cash = decimal_or_none(check_input.broker_snapshot.get("buying_power"))
    if cash is None:
        cash = decimal_or_none(check_input.broker_snapshot.get("cash_available"))
    return cash


def _exposure_base_equity(check_input: SafetyCheckInput, total_exposure: Decimal, cash_available: Decimal | None) -> Decimal | None:
    equity = (
        decimal_or_none(check_input.config.get("base_equity"))
        or decimal_or_none(check_input.config.get("current_total_equity"))
        or decimal_or_none(check_input.order_plan.get("base_equity"))
        or decimal_or_none(check_input.order_plan.get("current_total_equity"))
        or decimal_or_none(check_input.broker_snapshot.get("total_equity"))
        or decimal_or_none(check_input.broker_snapshot.get("equity"))
        or decimal_or_none(check_input.ledger_state.get("total_equity"))
        or decimal_or_none(check_input.ledger_state.get("equity"))
    )
    buying_power = (
        decimal_or_none(check_input.config.get("buying_power"))
        or decimal_or_none(check_input.order_plan.get("buying_power"))
        or decimal_or_none(check_input.broker_snapshot.get("buying_power"))
        or decimal_or_none(check_input.broker_snapshot.get("cash_available"))
    )
    if equity is None and cash_available is not None:
        equity = cash_available + total_exposure
    basis = str(check_input.config.get("exposure_basis") or "equity").lower()
    if basis == "buying_power":
        return buying_power or equity
    if basis == "min_equity_buying_power":
        values = [item for item in (equity, buying_power) if item is not None]
        return min(values) if values else None
    return equity or buying_power


@dataclass(frozen=True)
class DuplicateOrderGuard:
    guard_name: SafetyGuardName = SafetyGuardName.DUPLICATE_ORDER

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyCheckResult:
        state = coerce_state(check_input.current_state)
        order = check_input.order_plan
        issue_code = str(order.get("issue_code") or order.get("symbol") or "")
        side = str(order.get("side") or "").upper()
        active_statuses = {"OPEN", "PENDING", "ACCEPTED", "WAITING_FILL", "PARTIAL", "PARTIALLY_FILLED"}
        keys = [
            (str(item.get("issue_code") or item.get("symbol") or ""), str(item.get("side") or "").upper())
            for item in check_input.open_orders
            if str(item.get("status") or "OPEN").upper() in active_statuses
        ]
        if issue_code and side and (issue_code, side) in keys:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.EMERGENCY_STOP,
                SafetySeverity.EMERGENCY,
                "DUPLICATE_ORDER_SYSTEM_EMERGENCY",
                "Active duplicate order exists for the same issue and side.",
                state_after=SafetyState.SYSTEM_EMERGENCY_STOP,
                issue_code=issue_code,
                recommended_action="Stop order flow and reconcile broker open orders before submitting another order.",
                details={"refined_classification": "SYSTEM_EMERGENCY_STOP", "system_fault": True},
            )
        duplicates = {key for key, count in Counter(keys).items() if count > 1 and key[0] and key[1]}
        if duplicates:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.EMERGENCY_STOP,
                SafetySeverity.EMERGENCY,
                "BROKER_DUPLICATE_ORDER_RISK",
                "Broker open orders contain duplicate active orders.",
                state_after=SafetyState.SYSTEM_EMERGENCY_STOP,
                recommended_action="Stop order flow and reconcile broker orders.",
                details={"duplicate_keys": sorted([f"{symbol}:{side}" for symbol, side in duplicates])},
            )
        return SafetyCheckResult.allow(self.guard_name, state)


@dataclass(frozen=True)
class CashBufferGuard:
    guard_name: SafetyGuardName = SafetyGuardName.CASH_BUFFER

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyCheckResult:
        state = coerce_state(check_input.current_state)
        notional = decimal_or_zero(check_input.order_plan.get("notional") or check_input.order_plan.get("estimated_notional"))
        cash = decimal_or_none(check_input.order_plan.get("cash_basis"))
        if cash is None:
            cash = decimal_or_none(check_input.broker_snapshot.get("buying_power"))
        buffer_amount = decimal_or_zero(check_input.config.get("cash_buffer_amount"))
        buffer_ratio = decimal_or_zero(check_input.config.get("cash_buffer_ratio"))
        if cash is None:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.REVIEW_REQUIRED,
                SafetySeverity.REVIEW,
                "CASH_BASIS_MISSING",
                "Cash or buying power is missing.",
                recommended_action="Refresh broker snapshot before order submission.",
            )
        if notional <= 0:
            return SafetyCheckResult.allow(self.guard_name, state, reason_code="NO_NOTIONAL_TO_CHECK")
        required_buffer = max(buffer_amount, cash * buffer_ratio)
        if cash - notional < required_buffer:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.BLOCK,
                SafetySeverity.BLOCK,
                "CASH_BUFFER_VIOLATION",
                "Order would breach the configured cash buffer.",
                state_after=SafetyState.BUY_REVIEW_REQUIRED,
                recommended_action="Reduce order notional or refresh cash basis.",
                details={"refined_classification": "BUY_REVIEW_REQUIRED", "system_fault": False},
            )
        return SafetyCheckResult.allow(self.guard_name, state)


@dataclass(frozen=True)
class MaxExposureGuard:
    guard_name: SafetyGuardName = SafetyGuardName.MAX_EXPOSURE

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyCheckResult:
        state = coerce_state(check_input.current_state)
        side = str(check_input.order_plan.get("side") or "").upper()
        issue_code = str(check_input.order_plan.get("issue_code") or check_input.order_plan.get("symbol") or "")
        if side and side != "BUY":
            return SafetyCheckResult.allow(
                self.guard_name,
                state,
                reason_code="EXPOSURE_REDUCING_ORDER",
                message="Max exposure guard applies only to new buy exposure.",
                details={"side": side, "issue_code": issue_code},
            )
        total_exposure = sum(decimal_or_zero(item.get("market_value")) for item in check_input.positions)
        proposed = decimal_or_zero(check_input.order_plan.get("notional") or check_input.order_plan.get("estimated_notional"))
        cash_available = _cash_available(check_input)
        base_equity = _exposure_base_equity(check_input, total_exposure, cash_available)
        ratio = decimal_or_none(check_input.config.get("max_total_exposure_ratio"))
        if ratio is None:
            ratio = Decimal("0.85")
        absolute_cap = decimal_or_none(check_input.config.get("max_total_exposure_absolute_cap"))
        if absolute_cap is None:
            absolute_cap = decimal_or_none(check_input.config.get("max_total_exposure"))
        ratio_cap = base_equity * ratio if base_equity is not None else None
        candidate_caps = [cap for cap in (ratio_cap, absolute_cap) if cap is not None and cap > 0]
        max_exposure = min(candidate_caps) if candidate_caps else None
        projected_exposure = total_exposure + proposed
        max_positions = check_input.config.get("max_position_count")
        details = {
            "refined_classification": "BUY_REVIEW_REQUIRED",
            "system_fault": False,
            "current_exposure": str(total_exposure),
            "projected_exposure": str(projected_exposure),
            "base_equity": str(base_equity) if base_equity is not None else None,
            "max_total_exposure_ratio": str(ratio),
            "max_allowed_exposure": str(max_exposure) if max_exposure is not None else None,
            "max_total_exposure_absolute_cap": str(absolute_cap) if absolute_cap is not None else None,
            "cash_available": str(cash_available) if cash_available is not None else None,
            "position_count": len(check_input.positions),
            "side": side,
            "issue_code": issue_code,
            "exposure_basis": str(check_input.config.get("exposure_basis") or "equity"),
        }
        if max_exposure is not None and projected_exposure > max_exposure:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.BLOCK,
                SafetySeverity.BLOCK,
                "MAX_EXPOSURE_EXCEEDED",
                "Proposed order would exceed max total exposure ratio cap.",
                state_after=SafetyState.BUY_REVIEW_REQUIRED,
                issue_code=issue_code,
                recommended_action="Reduce exposure before allowing new buys.",
                details=details,
            )
        if max_positions is not None and len(check_input.positions) >= int(max_positions) and proposed > 0:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.BLOCK,
                SafetySeverity.BLOCK,
                "MAX_POSITION_COUNT_EXCEEDED",
                "Proposed order would exceed max position count.",
                state_after=SafetyState.BUY_REVIEW_REQUIRED,
                issue_code=issue_code,
                recommended_action="Review portfolio concentration before new buys.",
                details=details,
            )
        return SafetyCheckResult.allow(self.guard_name, state, details=details)


@dataclass(frozen=True)
class QuoteStaleGuard:
    guard_name: SafetyGuardName = SafetyGuardName.QUOTE_STALE

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyCheckResult:
        state = coerce_state(check_input.current_state)
        max_age = decimal_or_zero(check_input.config.get("max_quote_age_seconds") or "300")
        issue_code = str(check_input.order_plan.get("issue_code") or check_input.order_plan.get("symbol") or "")
        quote = check_input.quotes.get(issue_code, {}) if issue_code else {}
        age = decimal_or_none(quote.get("age_seconds"))
        stale = bool(quote.get("stale"))
        if issue_code and (not quote or age is None):
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.BLOCK,
                SafetySeverity.BLOCK,
                "QUOTE_MISSING",
                "Quote is missing for the target issue.",
                state_after=SafetyState.BUY_REVIEW_REQUIRED,
                issue_code=issue_code,
                recommended_action="Refresh realtime quote before order submission.",
                details={"refined_classification": "BUY_REVIEW_REQUIRED", "critical_stale": False},
            )
        if stale or (age is not None and age > max_age):
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.BLOCK,
                SafetySeverity.BLOCK,
                "QUOTE_STALE",
                "Quote is stale for the target issue.",
                state_after=SafetyState.BUY_REVIEW_REQUIRED,
                issue_code=issue_code,
                recommended_action="Do not trade from stale quote data.",
                details={"refined_classification": "BUY_REVIEW_REQUIRED", "critical_stale": False},
            )
        return SafetyCheckResult.allow(self.guard_name, state)


@dataclass(frozen=True)
class MarketCrashGuard:
    guard_name: SafetyGuardName = SafetyGuardName.MARKET_CRASH

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyCheckResult:
        state = coerce_state(check_input.current_state)
        market = check_input.market
        crash = bool(market.get("market_crash") or market.get("crash_detected"))
        severe = bool(market.get("severe_crash") or market.get("emergency_crash"))
        if severe:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.REVIEW_REQUIRED,
                SafetySeverity.REVIEW,
                "BUY_OPPORTUNITY_REVIEW",
                "Severe market stress detected. Treat as buy opportunity review, not system emergency.",
                state_after=SafetyState.BUY_OPPORTUNITY_REVIEW,
                recommended_action="Human review required for crash-day buy opportunity. Do not auto-sell or auto-stop solely from market decline.",
                details={
                    "market_crash_status": "buy_opportunity_review",
                    "refined_classification": "BUY_OPPORTUNITY_REVIEW",
                    "emergency_stop": False,
                    "auto_sell_executed": False,
                    "auto_buy_stop": False,
                },
            )
        if crash:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.REVIEW_REQUIRED,
                SafetySeverity.REVIEW,
                "MARKET_STRESS",
                "Market stress detected. Human review required; this is not a system emergency.",
                state_after=SafetyState.MARKET_STRESS,
                recommended_action="Review market stress and proposed buys as possible opportunity candidates.",
                details={
                    "market_crash_status": "market_stress",
                    "refined_classification": "MARKET_STRESS",
                    "emergency_stop": False,
                    "auto_sell_executed": False,
                    "auto_buy_stop": False,
                },
            )
        return SafetyCheckResult.allow(self.guard_name, state, details={"market_crash_status": "normal"})


@dataclass(frozen=True)
class BrokerDivergenceGuard:
    guard_name: SafetyGuardName = SafetyGuardName.BROKER_DIVERGENCE

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyCheckResult:
        state = coerce_state(check_input.current_state)
        divergence = check_input.broker_snapshot.get("divergence") or check_input.broker_snapshot.get("divergence_status")
        if not divergence or str(divergence).upper() in {"NONE", "OK", "MATCHED"}:
            return SafetyCheckResult.allow(self.guard_name, state, details={"divergence_summary": "none"})
        severe = str(check_input.broker_snapshot.get("divergence_severity") or "").upper() in {"HALT", "EMERGENCY", "SEVERE"}
        decision = SafetyDecision.EMERGENCY_STOP if severe else SafetyDecision.REVIEW_REQUIRED
        severity = SafetySeverity.EMERGENCY if severe else SafetySeverity.REVIEW
        state_after = SafetyState.SYSTEM_EMERGENCY_STOP if severe else None
        return _result(
            check_input,
            self.guard_name,
            decision,
            severity,
            "BROKER_DIVERGENCE_DETECTED",
            "Broker state diverges from runtime or ledger reference.",
            state_after=state_after,
            recommended_action="Treat broker as source of truth and reconcile before trading.",
            details={"divergence_summary": str(divergence), "refined_classification": "SYSTEM_EMERGENCY_STOP" if severe else "REVIEW_REQUIRED", "system_fault": True},
        )


@dataclass(frozen=True)
class DailyLossGuard:
    guard_name: SafetyGuardName = SafetyGuardName.DAILY_LOSS

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyCheckResult:
        state = coerce_state(check_input.current_state)
        daily_loss_pct = decimal_or_none(check_input.market.get("daily_loss_pct"))
        if daily_loss_pct is None:
            return SafetyCheckResult.allow(self.guard_name, state)
        buy_stop_threshold = decimal_or_zero(check_input.config.get("daily_loss_buy_stop_pct") or "-0.05")
        emergency_threshold = decimal_or_zero(check_input.config.get("daily_loss_emergency_pct") or "-0.10")
        if daily_loss_pct <= emergency_threshold:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.REVIEW_REQUIRED,
                SafetySeverity.REVIEW,
                "MARKET_STRESS_DAILY_LOSS",
                "Daily loss breached stress threshold. Review required, but loss alone is not a system emergency.",
                state_after=SafetyState.MARKET_STRESS,
                recommended_action="Review portfolio loss and valuation evidence. Do not auto-sell or emergency-stop solely from loss.",
                details={"refined_classification": "MARKET_STRESS", "daily_loss_pct": str(daily_loss_pct), "emergency_stop": False},
            )
        if daily_loss_pct <= buy_stop_threshold:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.REVIEW_REQUIRED,
                SafetySeverity.REVIEW,
                "DAILY_LOSS_REVIEW_REQUIRED",
                "Daily loss breached review threshold.",
                state_after=SafetyState.BUY_REVIEW_REQUIRED,
                recommended_action="Human review required before new buys. Loss alone does not trigger system emergency.",
                details={"refined_classification": "BUY_REVIEW_REQUIRED", "daily_loss_pct": str(daily_loss_pct), "emergency_stop": False},
            )
        return SafetyCheckResult.allow(self.guard_name, state)


@dataclass(frozen=True)
class EmergencyStopGuard:
    guard_name: SafetyGuardName = SafetyGuardName.EMERGENCY_STOP

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyCheckResult:
        state = coerce_state(check_input.current_state)
        if check_input.manual_emergency_stop or bool(check_input.runtime_state.get("manual_emergency_stop")):
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.EMERGENCY_STOP,
                SafetySeverity.EMERGENCY,
                "MANUAL_EMERGENCY_STOP",
                "Manual emergency stop flag is active.",
                state_after=SafetyState.SYSTEM_EMERGENCY_STOP,
                recommended_action="Keep all order flow stopped until manual review clears the flag.",
            )
        if bool(check_input.runtime_state.get("state_inconsistent")):
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.EMERGENCY_STOP,
                SafetySeverity.EMERGENCY,
                "RUNTIME_STATE_INCONSISTENT",
                "Runtime state is inconsistent.",
                state_after=SafetyState.SYSTEM_EMERGENCY_STOP,
                recommended_action="Audit runtime manifests before continuing.",
            )
        return SafetyCheckResult.allow(self.guard_name, state)


@dataclass(frozen=True)
class IndividualCrashGuard:
    guard_name: SafetyGuardName = SafetyGuardName.INDIVIDUAL_CRASH

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyCheckResult:
        state = coerce_state(check_input.current_state)
        worst_position: dict | None = None
        worst_drawdown: Decimal | None = None
        for position in check_input.positions:
            drawdown = _position_drawdown(position, check_input.quotes)
            if drawdown is None:
                continue
            if worst_drawdown is None or drawdown < worst_drawdown:
                worst_drawdown = drawdown
                worst_position = position
        if worst_drawdown is None:
            return SafetyCheckResult.allow(self.guard_name, state)
        issue_code = str((worst_position or {}).get("issue_code") or (worst_position or {}).get("symbol") or "")
        if worst_drawdown <= Decimal("-0.15"):
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.REVIEW_REQUIRED,
                SafetySeverity.REVIEW,
                "HIGH_RISK_REVIEW",
                "Individual position drawdown reached -15% high-risk review threshold.",
                state_after=SafetyState.WARNING,
                issue_code=issue_code,
                recommended_action="Human review required for hold, sell, reduce, or add decision. Phase11 does not auto-sell.",
                details={"drawdown_pct": str(worst_drawdown), "refined_classification": "HIGH_RISK_REVIEW", "emergency_stop": False, "auto_sell_executed": False},
            )
        if worst_drawdown <= Decimal("-0.10"):
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.REVIEW_REQUIRED,
                SafetySeverity.REVIEW,
                "SELL_REVIEW_REQUIRED",
                "Individual position drawdown reached -10% sell-review threshold.",
                state_after=SafetyState.WARNING,
                issue_code=issue_code,
                recommended_action="Review sell, hold, reduce, or add decision. Phase11 does not auto-sell.",
                details={"drawdown_pct": str(worst_drawdown), "refined_classification": "SELL_REVIEW_REQUIRED", "emergency_stop": False, "auto_sell_executed": False},
            )
        if worst_drawdown <= Decimal("-0.07"):
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.REVIEW_REQUIRED,
                SafetySeverity.WARNING,
                "INDIVIDUAL_DRAWDOWN_WARNING",
                "Individual position drawdown reached -7% warning threshold.",
                state_after=SafetyState.WARNING,
                issue_code=issue_code,
                recommended_action="Monitor position and include it in Safety Report.",
                details={"drawdown_pct": str(worst_drawdown), "refined_classification": "WARNING", "emergency_stop": False, "auto_sell_executed": False},
            )
        return SafetyCheckResult.allow(self.guard_name, state)


@dataclass(frozen=True)
class MarketRecoveryGuard:
    guard_name: SafetyGuardName = SafetyGuardName.MARKET_RECOVERY

    def evaluate(self, check_input: SafetyCheckInput) -> SafetyCheckResult:
        state = coerce_state(check_input.current_state)
        recovery_candidate = bool(check_input.market.get("recovery_candidate"))
        manual_approved = bool(check_input.market.get("manual_approved") or check_input.runtime_state.get("manual_approved"))
        if recovery_candidate and state in {SafetyState.BUY_STOP, SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP}:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.REVIEW_REQUIRED,
                SafetySeverity.REVIEW,
                "RECOVERY_CANDIDATE_REVIEW_REQUIRED",
                "Recovery conditions are candidates only and require human review.",
                state_after=SafetyState.RECOVERY_CANDIDATE,
                recommended_action="Review recovery evidence before manual approval.",
                details={"recovery_candidate_status": "candidate"},
            )
        if manual_approved and state is SafetyState.RECOVERY_CANDIDATE:
            return _result(
                check_input,
                self.guard_name,
                SafetyDecision.REVIEW_REQUIRED,
                SafetySeverity.REVIEW,
                "MANUAL_APPROVAL_RECORDED",
                "Manual approval is recorded; state machine may move to MANUAL_APPROVED before NORMAL.",
                state_after=SafetyState.MANUAL_APPROVED,
                recommended_action="Apply manual approval transition, then rerun safety check before NORMAL.",
                details={"recovery_candidate_status": "manual_approved"},
            )
        return SafetyCheckResult.allow(self.guard_name, state, details={"recovery_candidate_status": "not_candidate"})


def _position_drawdown(position: dict, quotes: dict[str, dict]) -> Decimal | None:
    issue_code = str(position.get("issue_code") or position.get("symbol") or "")
    reference = decimal_or_none(position.get("average_price") or position.get("acquisition_price") or position.get("reference_price"))
    latest = decimal_or_none(position.get("latest_price"))
    if latest is None and issue_code:
        latest = decimal_or_none(quotes.get(issue_code, {}).get("price") or quotes.get(issue_code, {}).get("latest_price"))
    if reference is None or reference <= 0 or latest is None:
        return None
    return (latest - reference) / reference


def _result(
    check_input: SafetyCheckInput,
    guard_name: SafetyGuardName,
    decision: SafetyDecision,
    severity: SafetySeverity,
    reason_code: str,
    message: str,
    *,
    state_after: SafetyState | None = None,
    issue_code: str | None = None,
    recommended_action: str,
    details: dict | None = None,
) -> SafetyCheckResult:
    state_before = coerce_state(check_input.current_state)
    requires_review = decision in {SafetyDecision.REVIEW_REQUIRED, SafetyDecision.BLOCK, SafetyDecision.EMERGENCY_STOP}
    event = SafetyEvent(
        guard_name=guard_name,
        decision=decision,
        severity=severity,
        reason_code=reason_code,
        message=message,
        state_before=state_before,
        state_after=state_after,
        runtime_id=check_input.runtime_id,
        business_date=check_input.business_date,
        environment=check_input.environment,
        issue_code=issue_code,
        requires_human_review=requires_review,
        details=details or {},
    )
    review_items: tuple[HumanReviewItem, ...] = ()
    if requires_review:
        review_items = (
            HumanReviewItem(
                guard_name=guard_name,
                reason_code=reason_code,
                message=message,
                severity=severity,
                recommended_action=recommended_action,
                issue_code=issue_code,
                event_id=event.event_id,
            ),
        )
    return SafetyCheckResult(
        guard_name=guard_name,
        decision=decision,
        severity=severity,
        reason_code=reason_code,
        message=message,
        state_before=state_before,
        state_after=state_after,
        events=(event,),
        review_items=review_items,
        details=details or {},
    )
