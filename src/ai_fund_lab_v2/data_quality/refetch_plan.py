from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from ai_fund_lab_v2.data_quality.raw_quality import RawQualityChecker
from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import ENDPOINT_PATHS


@dataclass(frozen=True)
class RefetchPlanItem:
    endpoint_name: str
    endpoint: str
    target_date: str | None
    reason: str
    current_status: str
    validation_status: str
    record_count: int
    suggested_command: str
    priority: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_refetch_plan(
    checker: RawQualityChecker,
    endpoint_name: str,
    from_date: str,
    to_date: str,
    reason: str = "all",
) -> list[RefetchPlanItem]:
    reports = checker.check_many(endpoint_name, from_date, to_date)
    items: list[RefetchPlanItem] = []
    for report in reports:
        if reason in ("all", "validation_error") and report.validation.get("status") != "OK":
            items.append(plan_item(report.endpoint_name, None, "validation_error", report.status, report.validation.get("status"), report.record_count))
        if reason in ("all", "missing", "empty"):
            for missing_date in report.missing_dates:
                item_reason = "empty" if missing_date in report.empty_dates else "missing"
                if reason != "all" and reason != item_reason and not (reason == "missing" and item_reason == "empty"):
                    continue
                items.append(plan_item(report.endpoint_name, missing_date, item_reason, report.status, report.validation.get("status"), report.record_count))
        if reason in ("all", "empty") and report.record_count == 0:
            items.append(plan_item(report.endpoint_name, None, "record_count_zero", report.status, report.validation.get("status"), report.record_count))
    return items


def plan_item(endpoint_name: str, target_date: str | None, reason: str, status: str, validation_status: str, record_count: int) -> RefetchPlanItem:
    priority = priority_for(endpoint_name, reason)
    date_arg = f"--date {target_date}" if target_date else ""
    command = f"python3 scripts/fetch_jquants_daily.py --endpoint {endpoint_name} {date_arg}".strip()
    return RefetchPlanItem(
        endpoint_name=endpoint_name,
        endpoint=ENDPOINT_PATHS[endpoint_name],
        target_date=target_date,
        reason=reason,
        current_status=status,
        validation_status=validation_status,
        record_count=record_count,
        suggested_command=command,
        priority=priority,
    )


def priority_for(endpoint_name: str, reason: str) -> str:
    if endpoint_name in ("daily_quotes", "trading_calendar") and reason in ("missing", "empty", "validation_error", "record_count_zero"):
        return "HIGH"
    if endpoint_name == "listed_issues":
        return "MEDIUM"
    if endpoint_name == "fins_summary":
        return "LOW"
    return "MEDIUM"
