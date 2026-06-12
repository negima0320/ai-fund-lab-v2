from __future__ import annotations

from ai_fund_lab_v2.safety.models import ReconciliationResult, ReconciliationSeverity, SafetyStatus, TradingLock


def build_trading_lock(result: ReconciliationResult) -> TradingLock:
    halt_issues = tuple(issue for issue in result.issues if issue.severity == ReconciliationSeverity.HALT)
    is_locked = result.status == SafetyStatus.HALT or bool(halt_issues)
    reason_codes = tuple(issue.code for issue in halt_issues) if halt_issues else tuple(issue.code for issue in result.issues)
    reason = ",".join(reason_codes) if reason_codes else "none"
    return TradingLock(is_locked=is_locked, reason=reason, status=result.status, issues=result.issues)
