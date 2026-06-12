from __future__ import annotations

from ai_fund_lab_v2.safety.models import ReconciliationResult, SafetyReport, TradingLock


def build_safety_report(
    result: ReconciliationResult,
    lock: TradingLock,
    broker_snapshot_id: str | None = None,
) -> SafetyReport:
    return SafetyReport(
        status=result.status,
        checked_at=result.checked_at,
        broker_snapshot_id=broker_snapshot_id,
        issue_count=len(result.issues),
        issues=result.issues,
        trading_locked=lock.is_locked,
    )
