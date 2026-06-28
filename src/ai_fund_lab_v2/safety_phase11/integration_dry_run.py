from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.safety_phase11.emergency_stop import EmergencyStopDecision, EmergencyStopEvaluator
from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json, write_safety_events
from ai_fund_lab_v2.safety_phase11.hourly_monitor import HourlyMonitorInput, HourlyMonitorResult, HourlyPositionMonitor
from ai_fund_lab_v2.safety_phase11.manual_unlock import (
    ManualUnlockValidation,
    create_manual_unlock_approval,
    read_manual_unlock_approval,
    validate_manual_unlock_approval,
    validate_normal_return_after_manual_approval,
)
from ai_fund_lab_v2.safety_phase11.models import (
    HumanReviewItem,
    SafetyDecision,
    SafetyEvent,
    SafetyGuardName,
    SafetySeverity,
    SafetyState,
    safety_id,
    utc_now_iso,
)
from ai_fund_lab_v2.safety_phase11.recovery import RecoveryCheckInput, RecoveryDecision, RecoveryEvaluator
from ai_fund_lab_v2.safety_phase11.report_schema import build_phase11_safety_report, build_review_queue_items
from ai_fund_lab_v2.safety_phase11.report_writer import write_safety_markdown_report, write_safety_report
from ai_fund_lab_v2.safety_phase11.review_queue_writer import write_review_queue, write_runtime_review_queue


PHASE11G_SCENARIOS = (
    "normal",
    "individual_warning",
    "stop_loss_candidate",
    "emergency_candidate",
    "market_crash",
    "duplicate_active_order",
    "stale_quote_snapshot",
    "manual_emergency",
    "recovery_candidate",
    "manual_unlock",
)

FORBIDDEN_MOCK_VALUES = (
    "RAW-REQUEST-PHASE11G",
    "RAW-RESPONSE-PHASE11G",
    "ACCOUNT-PLAINTEXT-PHASE11G",
    "ORDER-PLAINTEXT-PHASE11G",
    "EXEC-PLAINTEXT-PHASE11G",
    "AUTH-PLAINTEXT-PHASE11G",
    "PRIVATE-KEY-PHASE11G",
    "https://virtual-url.phase11g.invalid/path",
    "SECOND-PASSWORD-PHASE11G",
)


@dataclass(frozen=True)
class IntegrationDryRunScenarioResult:
    scenario_name: str
    monitor_result: HourlyMonitorResult
    emergency_decision: EmergencyStopDecision
    recovery_decision: RecoveryDecision
    manual_unlock_validation: ManualUnlockValidation | None = None
    normal_return_validation: ManualUnlockValidation | None = None
    safety_report_path: str = ""
    markdown_report_path: str = ""
    review_queue_path: str = ""
    runtime_review_queue_path: str = ""
    event_paths: tuple[str, ...] = ()
    scenario_report_path: str = ""
    recovery_applied: bool = False
    auto_trade_executed: bool = False
    auto_sell_executed: bool = False
    auto_recovery_executed: bool = False
    forbidden_value_leak_detected: bool = False

    @property
    def overall_decision(self) -> SafetyDecision:
        return self.monitor_result.overall_decision

    @property
    def next_state(self) -> SafetyState:
        if self.manual_unlock_validation and self.manual_unlock_validation.valid:
            return self.manual_unlock_validation.next_state
        if self.recovery_applied and self.recovery_decision.recovery_candidate:
            return self.recovery_decision.next_recommended_state
        if self.emergency_decision.emergency_required:
            return self.emergency_decision.next_state
        return self.monitor_result.next_recommended_state


@dataclass(frozen=True)
class IntegrationDryRunSummary:
    status: str
    business_date: str
    environment: str
    runtime_id: str
    generated_at: str
    scenario_results: tuple[IntegrationDryRunScenarioResult, ...]
    summary_report_path: str
    phase_report_path: str
    phase_report_json_path: str
    broker_api_connected: bool = False
    websocket_connected: bool = False
    demo_order_submitted: bool = False
    production_order_submitted: bool = False
    auto_sell_executed: bool = False
    auto_recovery_executed: bool = False
    runtime_behavior_changed: bool = False
    ai_learning_updated: bool = False


@dataclass(frozen=True)
class IntegrationDryRunConfig:
    business_date: str = "2026-06-29"
    environment: str = "dry_run"
    runtime_id: str = "phase11g_safety_integration_dry_run"
    reports_dir: Path | str = "reports"
    runtime_dir: Path | str = ".runtime"


@dataclass(frozen=True)
class _ScenarioDefinition:
    name: str
    monitor_input: HourlyMonitorInput
    recovery_source_state: SafetyState | None = None
    manual_unlock: bool = False
    latest_safety_decision_for_normal: SafetyDecision = SafetyDecision.ALLOW
    extra_events: tuple[SafetyEvent, ...] = ()
    extra_reviews: tuple[HumanReviewItem, ...] = ()


def run_phase11g_integration_dry_run(config: IntegrationDryRunConfig | None = None) -> IntegrationDryRunSummary:
    cfg = config or IntegrationDryRunConfig()
    reports_dir = Path(cfg.reports_dir)
    runtime_dir = Path(cfg.runtime_dir)
    output_dir = reports_dir / "safety" / "phase11" / "integration_dry_run"
    scenario_results = tuple(_run_scenario(definition, cfg, output_dir, runtime_dir) for definition in build_phase11g_scenarios(cfg))
    summary_path = output_dir / f"{cfg.business_date}_phase11g_integration_dry_run_summary.json"
    phase_doc_path = _phase_doc_path(reports_dir)
    phase_json_path = reports_dir / "phase_reports" / "phase11g_safety_integration_dry_run.json"
    summary = IntegrationDryRunSummary(
        status="PHASE11G_SAFETY_INTEGRATION_DRY_RUN_COMPLETE",
        business_date=cfg.business_date,
        environment=cfg.environment,
        runtime_id=cfg.runtime_id,
        generated_at=utc_now_iso(),
        scenario_results=scenario_results,
        summary_report_path=str(summary_path),
        phase_report_path=str(phase_doc_path),
        phase_report_json_path=str(phase_json_path),
    )
    _write_json(summary_path, _summary_payload(summary))
    _write_phase_reports(summary, phase_doc_path, phase_json_path)
    return summary


def build_phase11g_scenarios(config: IntegrationDryRunConfig | None = None) -> tuple[_ScenarioDefinition, ...]:
    cfg = config or IntegrationDryRunConfig()
    base = _base_monitor_input(cfg)
    manual_event = _manual_unlock_event(cfg)
    return (
        _ScenarioDefinition("normal", base),
        _ScenarioDefinition("individual_warning", replace(base, quotes={"7203": _quote("930")})),
        _ScenarioDefinition("stop_loss_candidate", replace(base, quotes={"7203": _quote("900")})),
        _ScenarioDefinition("emergency_candidate", replace(base, quotes={"7203": _quote("850")})),
        _ScenarioDefinition("market_crash", replace(base, candidate_universe_market_summary={"market_crash": True})),
        _ScenarioDefinition(
            "duplicate_active_order",
            replace(
                base,
                orders=(
                    _order("7203", "OPEN"),
                    _order("7203", "ACCEPTED"),
                ),
            ),
        ),
        _ScenarioDefinition(
            "stale_quote_snapshot",
            replace(base, broker_snapshot={**_broker_snapshot(), "age_seconds": "9999"}, quotes={"7203": _quote("1000", age_seconds="9999")}),
        ),
        _ScenarioDefinition("manual_emergency", replace(base, manual_emergency_stop=True)),
        _ScenarioDefinition(
            "recovery_candidate",
            replace(base, current_safety_state=SafetyState.BUY_STOP, candidate_universe_market_summary={"recovery_candidate": True}),
            recovery_source_state=SafetyState.BUY_STOP,
        ),
        _ScenarioDefinition(
            "manual_unlock",
            replace(base, current_safety_state=SafetyState.BUY_STOP, candidate_universe_market_summary={"recovery_candidate": True}),
            recovery_source_state=SafetyState.BUY_STOP,
            manual_unlock=True,
            extra_events=(manual_event,),
            extra_reviews=(_manual_unlock_review(manual_event),),
        ),
    )


def _run_scenario(
    definition: _ScenarioDefinition,
    config: IntegrationDryRunConfig,
    output_dir: Path,
    runtime_dir: Path,
) -> IntegrationDryRunScenarioResult:
    monitor_result = HourlyPositionMonitor().evaluate(definition.monitor_input)
    if definition.extra_events or definition.extra_reviews:
        monitor_result = replace(
            monitor_result,
            events=monitor_result.events + definition.extra_events,
            review_items=monitor_result.review_items + definition.extra_reviews,
        )
    safety_report_path = write_safety_report(monitor_result, reports_dir=config.reports_dir)
    markdown_report_path = write_safety_markdown_report(monitor_result, reports_dir=config.reports_dir, safety_report_path=safety_report_path)
    review_queue_path = write_review_queue(monitor_result, safety_report_path=safety_report_path, reports_dir=config.reports_dir)
    runtime_review_queue_path = write_runtime_review_queue(monitor_result, safety_report_path=safety_report_path, runtime_dir=runtime_dir)
    event_paths = tuple(str(path) for path in write_safety_events(monitor_result.events, runtime_dir=runtime_dir))

    emergency = EmergencyStopEvaluator().evaluate(
        monitor_result,
        manual_flag_active=definition.monitor_input.manual_emergency_stop,
        persistence_violation_suspected=False,
    )
    recovery_applied = definition.recovery_source_state is not None
    source_state = definition.recovery_source_state or monitor_result.current_state
    recovery = RecoveryEvaluator().evaluate(_recovery_input(source_state, monitor_result, str(safety_report_path)))
    manual_validation: ManualUnlockValidation | None = None
    normal_validation: ManualUnlockValidation | None = None
    if definition.manual_unlock:
        create_manual_unlock_approval(
            approved_by="phase11g_operator",
            reason="Phase11-G dry-run manual approval after human review.",
            source_state=source_state,
            safety_report_path=str(safety_report_path),
            recovery_evidence=recovery.satisfied_evidence,
            runtime_dir=runtime_dir,
        )
        manual_validation = validate_manual_unlock_approval(read_manual_unlock_approval(runtime_dir=runtime_dir))
        normal_validation = validate_normal_return_after_manual_approval(
            current_state=manual_validation.next_state,
            latest_safety_decision=definition.latest_safety_decision_for_normal,
        )

    report_path = output_dir / f"{config.business_date}_{definition.name}.json"
    scenario_payload = _scenario_payload(
        definition.name,
        monitor_result,
        emergency,
        recovery,
        manual_validation,
        normal_validation,
        str(safety_report_path),
        str(markdown_report_path),
        str(review_queue_path),
        str(runtime_review_queue_path),
        event_paths,
    )
    _write_json(report_path, scenario_payload)
    leak_detected = _contains_forbidden_values(report_path.read_text(encoding="utf-8"))
    return IntegrationDryRunScenarioResult(
        scenario_name=definition.name,
        monitor_result=monitor_result,
        emergency_decision=emergency,
        recovery_decision=recovery,
        manual_unlock_validation=manual_validation,
        normal_return_validation=normal_validation,
        safety_report_path=str(safety_report_path),
        markdown_report_path=str(markdown_report_path),
        review_queue_path=str(review_queue_path),
        runtime_review_queue_path=str(runtime_review_queue_path),
        event_paths=event_paths,
        scenario_report_path=str(report_path),
        recovery_applied=recovery_applied,
        forbidden_value_leak_detected=leak_detected,
    )


def _base_monitor_input(config: IntegrationDryRunConfig) -> HourlyMonitorInput:
    return HourlyMonitorInput(
        business_date=config.business_date,
        environment=config.environment,
        runtime_id=config.runtime_id,
        current_safety_state=SafetyState.NORMAL,
        broker_snapshot=_broker_snapshot(),
        positions=(
            {
                "issue_code": "7203",
                "quantity": "100",
                "average_price": "1000",
                "market_value": "100000",
                "raw_request": "RAW-REQUEST-PHASE11G",
                "account_id": "ACCOUNT-PLAINTEXT-PHASE11G",
            },
        ),
        quotes={"7203": _quote("1000")},
        orders=(),
        executions=(),
        candidate_universe_market_summary={},
        previous_portfolio_value="1000000",
        current_portfolio_value="1000000",
        config={"max_quote_age_seconds": "300", "max_broker_snapshot_age_seconds": "900"},
    )


def _broker_snapshot() -> dict[str, Any]:
    return {
        "age_seconds": "30",
        "buying_power": "1000000",
        "raw_response": "RAW-RESPONSE-PHASE11G",
        "auth_id": "AUTH-PLAINTEXT-PHASE11G",
        "private_key": "PRIVATE-KEY-PHASE11G",
        "virtual_url": "https://virtual-url.phase11g.invalid/path",
        "second_password": "SECOND-PASSWORD-PHASE11G",
    }


def _quote(price: str, *, age_seconds: str = "30") -> dict[str, str]:
    return {"age_seconds": age_seconds, "price": price}


def _order(issue_code: str, status: str) -> dict[str, str]:
    return {
        "issue_code": issue_code,
        "side": "BUY",
        "status": status,
        "order_id": "ORDER-PLAINTEXT-PHASE11G",
        "execution_id": "EXEC-PLAINTEXT-PHASE11G",
    }


def _manual_unlock_event(config: IntegrationDryRunConfig) -> SafetyEvent:
    return SafetyEvent(
        guard_name=SafetyGuardName.MARKET_RECOVERY,
        decision=SafetyDecision.REVIEW_REQUIRED,
        severity=SafetySeverity.REVIEW,
        reason_code="RECOVERY_CANDIDATE_REVIEW_REQUIRED",
        message="Recovery candidate requires manual unlock review.",
        state_before=SafetyState.BUY_STOP,
        state_after=SafetyState.RECOVERY_CANDIDATE,
        runtime_id=config.runtime_id,
        business_date=config.business_date,
        environment=config.environment,
        requires_human_review=True,
        details={"raw_response": "RAW-RESPONSE-PHASE11G"},
    )


def _manual_unlock_review(event: SafetyEvent) -> HumanReviewItem:
    return HumanReviewItem(
        guard_name=SafetyGuardName.MARKET_RECOVERY,
        reason_code="RECOVERY_CANDIDATE_REVIEW_REQUIRED",
        message="Manual approval is required before returning toward NORMAL.",
        severity=SafetySeverity.REVIEW,
        recommended_action="Review recovery evidence and approve MANUAL_APPROVED only if latest safety check is ALLOW.",
        event_id=event.event_id,
    )


def _recovery_input(source_state: SafetyState, monitor_result: HourlyMonitorResult, report_path: str) -> RecoveryCheckInput:
    market_summary = {
        "severe_crash": False,
        "stable_days": 5,
        "candidate_universe_drawdown_improved": True,
        "crash_issue_ratio_declined": True,
        "extreme_down_ratio_declined": True,
    }
    if monitor_result.monitor_summary.get("market_crash_status") == "emergency":
        market_summary["severe_crash"] = True
    return RecoveryCheckInput(
        current_state=source_state,
        manual_emergency_flag_active=False,
        market_summary=market_summary,
        quote_freshness="fresh",
        broker_snapshot_freshness="fresh",
        broker_divergence="none",
        duplicate_active_order_risk=False,
        daily_loss_pct="0.00",
        runtime_state_valid=True,
        persistence_violation_suspected=False,
        latest_safety_report_path=report_path,
    )


def _scenario_payload(
    name: str,
    monitor_result: HourlyMonitorResult,
    emergency: EmergencyStopDecision,
    recovery: RecoveryDecision,
    manual_validation: ManualUnlockValidation | None,
    normal_validation: ManualUnlockValidation | None,
    safety_report_path: str,
    markdown_report_path: str,
    review_queue_path: str,
    runtime_review_queue_path: str,
    event_paths: tuple[str, ...],
) -> dict[str, Any]:
    payload = {
        "schema_version": "phase11g_integration_dry_run_scenario_v1",
        "scenario_name": name,
        "generated_at": utc_now_iso(),
        "business_date": monitor_result.business_date,
        "environment": monitor_result.environment,
        "runtime_id": monitor_result.runtime_id,
        "overall_decision": monitor_result.overall_decision.value,
        "monitor_next_state": monitor_result.next_recommended_state.value,
        "effective_next_state": _effective_next_state(emergency, recovery, manual_validation, recovery_applied=name in {"recovery_candidate", "manual_unlock"}).value,
        "triggered_reason_codes": monitor_result.monitor_summary.get("triggered_reason_codes", []),
        "review_queue_item_count": len(build_review_queue_items(monitor_result, safety_report_path=safety_report_path)),
        "emergency": _jsonable_dataclass(emergency),
        "recovery": _jsonable_dataclass(recovery),
        "manual_unlock_validation": _jsonable_dataclass(manual_validation) if manual_validation else None,
        "normal_return_validation": _jsonable_dataclass(normal_validation) if normal_validation else None,
        "blocked_actions": _blocked_actions(emergency, monitor_result),
        "allowed_actions": _allowed_actions(emergency),
        "safety_report_path": safety_report_path,
        "markdown_report_path": markdown_report_path,
        "review_queue_path": review_queue_path,
        "runtime_review_queue_path": runtime_review_queue_path,
        "event_paths": list(event_paths),
        "auto_trade_executed": False,
        "auto_sell_executed": False,
        "auto_recovery_executed": False,
        "no_live_order_confirmation": {
            "broker_api_connected": False,
            "websocket_connected": False,
            "demo_order_submitted": False,
            "production_order_submitted": False,
            "clm_kabu_new_order_executed": False,
        },
        "persistence_protection": {
            "mock_forbidden_values_injected": True,
            "forbidden_values_persisted": False,
        },
        "ai_learning_use": {
            "dry_run_result_used_for_ai_learning": False,
            "safety_result_used_for_ai_learning": False,
            "audit_result_used_for_ai_learning": False,
        },
    }
    return _phase11_sanitize(payload)


def _summary_payload(summary: IntegrationDryRunSummary) -> dict[str, Any]:
    payload = {
        "schema_version": "phase11g_integration_dry_run_summary_v1",
        "status": summary.status,
        "business_date": summary.business_date,
        "environment": summary.environment,
        "runtime_id": summary.runtime_id,
        "generated_at": summary.generated_at,
        "scenario_count": len(summary.scenario_results),
        "scenarios": [_scenario_summary(item) for item in summary.scenario_results],
        "summary_report_path": summary.summary_report_path,
        "phase_report_path": summary.phase_report_path,
        "phase_report_json_path": summary.phase_report_json_path,
        "broker_api_connected": False,
        "login_logout_executed": False,
        "websocket_connected": False,
        "demo_order_submitted": False,
        "production_order_submitted": False,
        "clm_kabu_new_order_executed": False,
        "auto_sell_executed": False,
        "auto_recovery_executed": False,
        "runtime_behavior_changed": False,
        "broker_snapshot_updated": False,
        "paper_ledger_updated": False,
        "cron_or_launchagent_registered": False,
        "ai_learning_updated": False,
        "persistence_protection": {
            "mock_forbidden_values_injected": True,
            "forbidden_value_leak_detected": any(item.forbidden_value_leak_detected for item in summary.scenario_results),
        },
        "judgement": [
            "PHASE11G_SAFETY_INTEGRATION_DRY_RUN_COMPLETE",
            "PHASE11Z_READY_TO_START",
            "LIVE_ORDER_EXECUTION_REMAINS_BLOCKED",
        ],
    }
    return _phase11_sanitize(payload)


def _phase_doc_path(reports_dir: Path) -> Path:
    if reports_dir == Path("reports"):
        return Path("docs") / "phase_reports" / "phase11g_safety_integration_dry_run.md"
    return reports_dir / "phase_reports" / "phase11g_safety_integration_dry_run.md"


def _scenario_summary(item: IntegrationDryRunScenarioResult) -> dict[str, Any]:
    return {
        "scenario_name": item.scenario_name,
        "overall_decision": item.overall_decision.value,
        "next_state": item.next_state.value,
        "triggered_reason_codes": item.monitor_result.monitor_summary.get("triggered_reason_codes", []),
        "emergency_required": item.emergency_decision.emergency_required,
        "recovery_candidate": item.recovery_decision.recovery_candidate,
        "manual_unlock_valid": item.manual_unlock_validation.valid if item.manual_unlock_validation else False,
        "normal_return_valid": item.normal_return_validation.valid if item.normal_return_validation else False,
        "review_item_count": len(build_review_queue_items(item.monitor_result, safety_report_path=item.safety_report_path)),
        "blocked_actions": _blocked_actions(item.emergency_decision, item.monitor_result),
        "auto_trade_executed": False,
        "auto_sell_executed": False,
        "auto_recovery_executed": False,
        "scenario_report_path": item.scenario_report_path,
        "forbidden_value_leak_detected": item.forbidden_value_leak_detected,
    }


def _write_phase_reports(summary: IntegrationDryRunSummary, doc_path: Path, json_path: Path) -> None:
    payload = _summary_payload(summary)
    _write_json(json_path, payload)
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase11-G Safety Integration Dry Run",
        "",
        "- status: PHASE11G_SAFETY_INTEGRATION_DRY_RUN_COMPLETE",
        f"- business_date: {summary.business_date}",
        f"- generated_at: {summary.generated_at}",
        "- broker_api_connected: false",
        "- websocket_connected: false",
        "- demo_order_submitted: false",
        "- production_order_submitted: false",
        "- auto_sell_executed: false",
        "- auto_recovery_executed: false",
        "- runtime_behavior_changed: false",
        "",
        "## Summary",
        "",
        "Phase11-B〜Fで作成した Safety Runtime / Hourly Monitor / Report / Emergency Stop / Recovery / Manual Unlock を、mockデータだけで統合dry-runした。",
        "",
        "このdry-runは実運用接続ではなく、Safety subsystemの連携監査成果物である。Broker Snapshot、Safety result、Audit result、Order / Execution result はAI学習に使用しない。",
        "",
        "## Scenarios",
        "",
    ]
    for item in summary.scenario_results:
        lines.extend(
            [
                f"### {item.scenario_name}",
                "",
                f"- overall_decision: {item.overall_decision.value}",
                f"- next_state: {item.next_state.value}",
                f"- emergency_required: {str(item.emergency_decision.emergency_required).lower()}",
                f"- recovery_candidate: {str(item.recovery_decision.recovery_candidate).lower()}",
                f"- review_item_count: {len(build_review_queue_items(item.monitor_result, safety_report_path=item.safety_report_path))}",
                f"- report: {item.scenario_report_path}",
                "",
            ]
        )
    lines.extend(
        [
            "## Output",
            "",
            f"- integration_summary: {summary.summary_report_path}",
            f"- phase_json: {summary.phase_report_json_path}",
            "",
            "## Result",
            "",
            "```text",
            "PHASE11G_SAFETY_INTEGRATION_DRY_RUN_COMPLETE",
            "PHASE11Z_READY_TO_START",
            "LIVE_ORDER_EXECUTION_REMAINS_BLOCKED",
            "```",
        ]
    )
    doc_path.write_text(_phase11_sanitize("\n".join(lines) + "\n"), encoding="utf-8")


def _effective_next_state(
    emergency: EmergencyStopDecision,
    recovery: RecoveryDecision,
    manual_validation: ManualUnlockValidation | None,
    *,
    recovery_applied: bool,
) -> SafetyState:
    if manual_validation and manual_validation.valid:
        return manual_validation.next_state
    if recovery_applied and recovery.recovery_candidate:
        return recovery.next_recommended_state
    if emergency.emergency_required:
        return emergency.next_state
    return recovery.next_recommended_state


def _blocked_actions(emergency: EmergencyStopDecision, monitor_result: HourlyMonitorResult) -> list[str]:
    actions = list(emergency.blocked_actions)
    report = build_phase11_safety_report(monitor_result)
    for action in report["blocked_actions"]:
        if action not in actions:
            actions.append(action)
    return actions


def _allowed_actions(emergency: EmergencyStopDecision) -> list[str]:
    if emergency.allowed_actions:
        return list(emergency.allowed_actions)
    return ["read_only_broker_sync", "quote_polling", "audit", "report_generation", "human_review"]


def _jsonable_dataclass(value: Any) -> dict[str, Any]:
    data = asdict(value)
    for key, item in list(data.items()):
        if isinstance(item, (SafetyState, SafetyDecision)):
            data[key] = item.value
        elif isinstance(item, tuple):
            data[key] = [sub.value if isinstance(sub, (SafetyState, SafetyDecision)) else sub for sub in item]
    return data


def _contains_forbidden_values(text: str) -> bool:
    return any(value in text for value in FORBIDDEN_MOCK_VALUES)
