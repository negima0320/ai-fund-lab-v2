"""Runtime v2 regular-path Safety evaluation.

This module connects Runtime-owned evidence to Phase11 Safety evaluation.  It
does not submit orders, mutate Current, or rely on scenario-only Safety inputs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.safety_phase11.emergency_stop import EmergencyStopEvaluator
from ai_fund_lab_v2.safety_phase11.hourly_monitor import (
    HourlyMonitorInput,
    HourlyMonitorResult,
    HourlyPositionMonitor,
)
from ai_fund_lab_v2.safety_phase11.models import (
    HumanReviewItem,
    SafetyCheckResult,
    SafetyDecision,
    SafetyEvent,
    SafetyGuardName,
    SafetySeverity,
    SafetyState,
)
from ai_fund_lab_v2.safety_phase11.report_writer import (
    write_safety_markdown_report,
    write_safety_report,
)
from ai_fund_lab_v2.runtime_v2.temporal import (
    FreshnessStatus,
    evaluate_broker_snapshot_freshness,
    resolve_temporal_context,
)
from ai_fund_lab_v2.runtime_v2.runtime_state import validate_runtime_operation_state


CURRENT_RELATIVE_PATH = Path("persistent_ledger") / "state.json"
ORDERS_RELATIVE_PATH = Path("persistent_ledger") / "orders.jsonl"
EXECUTIONS_RELATIVE_PATH = Path("persistent_ledger") / "executions.jsonl"
RUNTIME_STATE_RELATIVE_PATH = Path("runtime_state") / "current_state.json"
MARKET_EVIDENCE_RELATIVE_ROOT = Path("runtime_state") / "market"
BROKER_SNAPSHOT_RELATIVE_ROOT = Path("runtime_state") / "broker_readonly"
MANUAL_STOP_RELATIVE_ROOT = Path("safety") / "locks"
PHASE11_POLICY_VERSION = "phase11_safety_report_v2"


@dataclass(frozen=True)
class RuntimeSafetyEvaluationResult:
    status: str
    reason: str
    safety_report_path: str
    safety_markdown_report_path: str
    manifest_fields: dict[str, Any]

    def to_stage_details(self) -> dict[str, Any]:
        return dict(self.manifest_fields)


@dataclass(frozen=True)
class _EvidenceBundle:
    current: dict[str, Any]
    current_source: str
    current_as_of: str
    broker_snapshot: dict[str, Any]
    broker_snapshot_source: str
    broker_snapshot_at: str
    market: dict[str, Any]
    market_source: str
    market_as_of: str
    orders: tuple[dict[str, Any], ...]
    orders_source: str
    executions: tuple[dict[str, Any], ...]
    execution_source: str
    runtime_state: dict[str, Any]
    runtime_state_source: str
    manual_stop: dict[str, Any]
    manual_stop_source: str
    missing_evidence: tuple[str, ...]
    stale_evidence: tuple[str, ...]


def run_runtime_safety_evaluation(
    *,
    runtime_root: Path | str,
    reports_root: Path | str = "reports",
    business_date: str,
    mode: str,
    now: datetime | None = None,
) -> RuntimeSafetyEvaluationResult:
    now_dt = _aware(now or datetime.now(timezone.utc))
    root = Path(runtime_root)
    evidence = _load_evidence(root=root, business_date=business_date, mode=mode, now=now_dt)
    monitor_input = _to_monitor_input(
        evidence=evidence,
        business_date=business_date,
        mode=mode,
        runtime_id=f"runtime-v2-safety-evaluation-{business_date}",
    )
    result = HourlyPositionMonitor().evaluate(monitor_input)
    result = _augment_with_runtime_evidence_gaps(result=result, evidence=evidence)
    result = _augment_with_declared_market_reviews(result=result, evidence=evidence)
    result = _apply_emergency_evaluator(result=result, manual_stop=evidence.manual_stop)

    safety_report_path = write_safety_report(result, reports_dir=reports_root)
    markdown_report_path = write_safety_markdown_report(result, reports_dir=reports_root, safety_report_path=safety_report_path)
    expires_at = (now_dt + timedelta(hours=4)).isoformat()
    _enrich_phase11_report(
        path=safety_report_path,
        result=result,
        evidence=evidence,
        expires_at=expires_at,
        mode=mode,
    )

    status = _status_from_result(result=result, evidence=evidence)
    reason = _reason_from_result(result=result, evidence=evidence)
    manifest_fields = _manifest_fields(
        status=status,
        reason=reason,
        result=result,
        evidence=evidence,
        safety_report_path=safety_report_path,
        markdown_report_path=markdown_report_path,
        mode=mode,
    )
    return RuntimeSafetyEvaluationResult(
        status=status,
        reason=reason,
        safety_report_path=str(safety_report_path),
        safety_markdown_report_path=str(markdown_report_path),
        manifest_fields=manifest_fields,
    )


def _load_evidence(*, root: Path, business_date: str, mode: str, now: datetime) -> _EvidenceBundle:
    missing: list[str] = []
    stale: list[str] = []

    current_path = root / CURRENT_RELATIVE_PATH
    current = _read_json_file(current_path, missing, "current")
    current_as_of = _timestamp_from(current, "generated_at", "as_of", "updated_at", "business_date")
    _require_business_date(current, current_as_of, business_date, stale, "current")

    broker_path = _first_json(root / BROKER_SNAPSHOT_RELATIVE_ROOT / business_date)
    if broker_path is None:
        broker_snapshot: dict[str, Any] = {}
        broker_source = ""
        broker_at = ""
        missing.append("broker_snapshot")
    else:
        broker_snapshot = _read_json_file(broker_path, missing, "broker_snapshot")
        broker_source = str(broker_path)
        broker_at = _timestamp_from(broker_snapshot, "snapshot_at", "generated_at", "as_of", "business_date")
        _require_business_date(broker_snapshot, broker_at, business_date, stale, "broker_snapshot")
        _set_snapshot_age(broker_snapshot, broker_at, business_date, mode, now)

    market_path = _market_evidence_path(root=root, business_date=business_date)
    market = _read_json_file(market_path, missing, "market")
    market_as_of = _timestamp_from(market, "generated_at", "as_of", "business_date")
    _require_business_date(market, market_as_of, business_date, stale, "market")

    orders_path = root / ORDERS_RELATIVE_PATH
    orders = _read_jsonl(orders_path, missing, "orders")
    executions_path = root / EXECUTIONS_RELATIVE_PATH
    executions = _read_jsonl(executions_path, missing, "executions")

    runtime_state_path = root / RUNTIME_STATE_RELATIVE_PATH
    runtime_state_result = validate_runtime_operation_state(
        runtime_root=root,
        business_date=business_date,
        mode=mode,
    )
    runtime_state = dict(runtime_state_result.payload)
    if runtime_state_result.status == "HALT":
        missing.append("runtime_state_invalid")
    elif runtime_state_result.status != "READY":
        if runtime_state_result.missing_fields:
            missing.append("runtime_state")
        if runtime_state_result.stale_fields:
            stale.append("runtime_state")

    manual_path = _first_json(root / MANUAL_STOP_RELATIVE_ROOT)
    if manual_path is None:
        manual_stop = {}
        manual_source = ""
        missing.append("manual_stop_state")
    else:
        manual_stop = _read_json_file(manual_path, missing, "manual_stop_state")
        manual_source = str(manual_path)
        manual_as_of = _timestamp_from(manual_stop, "generated_at", "updated_at", "business_date")
        _require_business_date(manual_stop, manual_as_of, business_date, stale, "manual_stop_state")

    if current and str(current.get("environment") or current.get("runtime_environment") or mode) != mode:
        stale.append("current_environment_mismatch")
    if broker_snapshot and str(broker_snapshot.get("broker_mode") or broker_snapshot.get("environment") or mode) != mode:
        stale.append("broker_environment_mismatch")

    return _EvidenceBundle(
        current=current,
        current_source=str(current_path),
        current_as_of=current_as_of,
        broker_snapshot=broker_snapshot,
        broker_snapshot_source=broker_source,
        broker_snapshot_at=broker_at,
        market=market,
        market_source=str(market_path),
        market_as_of=market_as_of,
        orders=tuple(_filter_business_date(orders, business_date)),
        orders_source=str(orders_path),
        executions=tuple(_filter_business_date(executions, business_date)),
        execution_source=str(executions_path),
        runtime_state=runtime_state,
        runtime_state_source=str(runtime_state_path),
        manual_stop=manual_stop,
        manual_stop_source=manual_source,
        missing_evidence=tuple(sorted(set(missing))),
        stale_evidence=tuple(sorted(set(stale))),
    )


def _to_monitor_input(*, evidence: _EvidenceBundle, business_date: str, mode: str, runtime_id: str) -> HourlyMonitorInput:
    current = evidence.current
    market = dict(evidence.market.get("candidate_universe_market_summary") or evidence.market.get("market_summary") or {})
    quotes = dict(evidence.market.get("quotes") or {})
    positions = tuple(_normalize_position(item) for item in current.get("positions") or ())
    return HourlyMonitorInput(
        business_date=business_date,
        environment=mode,
        runtime_id=runtime_id,
        current_safety_state=str(evidence.runtime_state.get("safety_state") or evidence.runtime_state.get("current_safety_state") or SafetyState.NORMAL.value),
        broker_snapshot=dict(evidence.broker_snapshot),
        positions=positions,
        quotes=quotes,
        orders=evidence.orders,
        executions=evidence.executions,
        candidate_universe_market_summary=market,
        previous_portfolio_value=current.get("previous_total_equity") or current.get("previous_portfolio_value"),
        current_portfolio_value=current.get("total_equity") or current.get("equity") or current.get("portfolio_value"),
        manual_emergency_stop=bool(evidence.manual_stop.get("is_locked") or evidence.manual_stop.get("manual_emergency_stop")),
        config=dict(evidence.market.get("safety_config") or evidence.current.get("safety_config") or {}),
    )


def _market_evidence_path(*, root: Path, business_date: str) -> Path:
    direct = root / MARKET_EVIDENCE_RELATIVE_ROOT / business_date / "market_evidence.json"
    if direct.is_file():
        return direct
    latest = root / MARKET_EVIDENCE_RELATIVE_ROOT / "latest.json"
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return direct
    candidate = Path(str(payload.get("artifact_path") or ""))
    if candidate.is_file():
        return candidate
    return direct


def _augment_with_runtime_evidence_gaps(*, result: HourlyMonitorResult, evidence: _EvidenceBundle) -> HourlyMonitorResult:
    gap_results: list[SafetyCheckResult] = []
    for label in evidence.missing_evidence:
        gap_results.append(
            _runtime_result(
                result=result,
                decision=SafetyDecision.REVIEW_REQUIRED,
                severity=SafetySeverity.REVIEW,
                reason_code="RUNTIME_EVIDENCE_MISSING",
                message=f"Runtime Safety evidence is missing: {label}.",
                state_after=SafetyState.BUY_REVIEW_REQUIRED,
                details={"missing_evidence": label},
            )
        )
    for label in evidence.stale_evidence:
        gap_results.append(
            _runtime_result(
                result=result,
                decision=SafetyDecision.REVIEW_REQUIRED,
                severity=SafetySeverity.REVIEW,
                reason_code="RUNTIME_EVIDENCE_STALE",
                message=f"Runtime Safety evidence is stale or inconsistent: {label}.",
                state_after=SafetyState.BUY_REVIEW_REQUIRED,
                details={"stale_evidence": label},
            )
        )
    return _with_extra_results(result, tuple(gap_results))


def _augment_with_declared_market_reviews(*, result: HourlyMonitorResult, evidence: _EvidenceBundle) -> HourlyMonitorResult:
    extras: list[SafetyCheckResult] = []
    market = evidence.market
    if bool(market.get("buy_review_required")):
        extras.append(
            _runtime_result(
                result=result,
                decision=SafetyDecision.REVIEW_REQUIRED,
                severity=SafetySeverity.REVIEW,
                reason_code="BUY_REVIEW_REQUIRED",
                message=str(market.get("buy_review_reason") or "Market evidence requires human review before new buys."),
                state_after=SafetyState.BUY_REVIEW_REQUIRED,
                details={"review_scope": "BUY"},
            )
        )
    if bool(market.get("sell_review_required")):
        extras.append(
            _runtime_result(
                result=result,
                decision=SafetyDecision.REVIEW_REQUIRED,
                severity=SafetySeverity.REVIEW,
                reason_code="SELL_REVIEW_REQUIRED",
                message=str(market.get("sell_review_reason") or "Market evidence requires human review before sells."),
                details={"review_scope": "SELL"},
            )
        )
    return _with_extra_results(result, tuple(extras))


def _apply_emergency_evaluator(*, result: HourlyMonitorResult, manual_stop: dict[str, Any]) -> HourlyMonitorResult:
    emergency = EmergencyStopEvaluator(critical_broker_snapshot_stale=False).evaluate(
        result,
        manual_flag_active=bool(manual_stop.get("is_locked") or manual_stop.get("manual_emergency_stop")),
        persistence_violation_suspected=bool(manual_stop.get("persistence_violation_suspected")),
        unknown_severe_error=bool(manual_stop.get("unknown_severe_error")),
    )
    if not emergency.emergency_required:
        return result
    extra = _runtime_result(
        result=result,
        decision=SafetyDecision.EMERGENCY_STOP,
        severity=SafetySeverity.EMERGENCY,
        reason_code="RUNTIME_EMERGENCY_STOP_EVALUATOR",
        message="; ".join(emergency.reason_codes) or "Runtime emergency stop evaluator required halt.",
        state_after=SafetyState.SYSTEM_EMERGENCY_STOP,
        details={
            "blocked_actions": emergency.blocked_actions,
            "allowed_actions": emergency.allowed_actions,
            "manual_required": True,
        },
    )
    return _with_extra_results(result, (extra,))


def _with_extra_results(result: HourlyMonitorResult, extras: tuple[SafetyCheckResult, ...]) -> HourlyMonitorResult:
    if not extras:
        return result
    check_results = result.check_results + extras
    events = result.events + tuple(event for item in extras for event in item.events)
    review_items = result.review_items + tuple(review for item in extras for review in item.review_items)
    decisions = [item.decision for item in check_results]
    if SafetyDecision.EMERGENCY_STOP in decisions:
        overall = SafetyDecision.EMERGENCY_STOP
        next_state = SafetyState.SYSTEM_EMERGENCY_STOP
    elif SafetyDecision.BLOCK in decisions:
        overall = SafetyDecision.BLOCK
        next_state = _preferred_review_state(result.next_recommended_state, extras)
    elif SafetyDecision.REVIEW_REQUIRED in decisions:
        overall = SafetyDecision.REVIEW_REQUIRED
        next_state = _preferred_review_state(result.next_recommended_state, extras)
    else:
        overall = SafetyDecision.ALLOW
        next_state = result.next_recommended_state
    summary = dict(result.monitor_summary)
    if extras:
        summary["runtime_evidence_reviews"] = [item.reason_code for item in extras]
    return replace(
        result,
        overall_decision=overall,
        next_recommended_state=next_state,
        transition_allowed=overall is SafetyDecision.ALLOW and result.transition_allowed,
        transition_reason=result.transition_reason if overall is SafetyDecision.ALLOW else "runtime safety evidence review required",
        check_results=check_results,
        events=events,
        review_items=review_items,
        monitor_summary=summary,
    )


def _runtime_result(
    *,
    result: HourlyMonitorResult,
    decision: SafetyDecision,
    severity: SafetySeverity,
    reason_code: str,
    message: str,
    state_after: SafetyState | None,
    details: dict[str, Any],
) -> SafetyCheckResult:
    event = SafetyEvent(
        guard_name=SafetyGuardName.EMERGENCY_STOP,
        decision=decision,
        severity=severity,
        reason_code=reason_code,
        message=message,
        state_before=result.current_state,
        state_after=state_after,
        runtime_id=result.runtime_id,
        business_date=result.business_date,
        environment=result.environment,
        requires_human_review=decision is not SafetyDecision.ALLOW,
        details=details,
    )
    review_items: tuple[HumanReviewItem, ...] = ()
    if decision is not SafetyDecision.ALLOW:
        review_items = (
            HumanReviewItem(
                guard_name=SafetyGuardName.EMERGENCY_STOP,
                reason_code=reason_code,
                message=message,
                severity=severity,
                recommended_action="Refresh authoritative Runtime evidence and re-run only Safety evaluation.",
                event_id=event.event_id,
            ),
        )
    return SafetyCheckResult(
        guard_name=SafetyGuardName.EMERGENCY_STOP,
        decision=decision,
        severity=severity,
        reason_code=reason_code,
        message=message,
        state_before=result.current_state,
        state_after=state_after,
        events=(event,),
        review_items=review_items,
        details=details,
    )


def _enrich_phase11_report(
    *,
    path: Path,
    result: HourlyMonitorResult,
    evidence: _EvidenceBundle,
    expires_at: str,
    mode: str,
) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(
        {
            "schema_version": PHASE11_POLICY_VERSION,
            "expires_at": expires_at,
            "input_evidence_sources": _input_sources(evidence),
            "input_freshness_status": _freshness_status(evidence),
            "missing_evidence": list(evidence.missing_evidence),
            "stale_evidence": list(evidence.stale_evidence),
            "production_equivalent": mode == "production" and not evidence.missing_evidence and not evidence.stale_evidence,
            "runtime_safety_evaluation": {
                "source": "runtime_v2_regular_path",
                "current_source": evidence.current_source,
                "broker_snapshot_source": evidence.broker_snapshot_source,
                "market_source": evidence.market_source,
                "orders_source": evidence.orders_source,
                "execution_source": evidence.execution_source,
                "manual_stop_source": evidence.manual_stop_source,
                "overall_decision": result.overall_decision.value,
                "next_recommended_safety_state": result.next_recommended_state.value,
            },
        }
    )
    _atomic_write_json(path, payload)


def _manifest_fields(
    *,
    status: str,
    reason: str,
    result: HourlyMonitorResult,
    evidence: _EvidenceBundle,
    safety_report_path: Path,
    markdown_report_path: Path,
    mode: str,
) -> dict[str, Any]:
    return {
        "safety_evaluation_status": status,
        "safety_evaluation_reason": reason,
        "safety_evaluation_policy_version": PHASE11_POLICY_VERSION,
        "current_source": evidence.current_source,
        "current_as_of": evidence.current_as_of,
        "market_source": evidence.market_source,
        "market_as_of": evidence.market_as_of,
        "broker_snapshot_source": evidence.broker_snapshot_source,
        "broker_snapshot_at": evidence.broker_snapshot_at,
        "orders_source": evidence.orders_source,
        "execution_source": evidence.execution_source,
        "manual_stop_source": evidence.manual_stop_source,
        "input_freshness_status": _freshness_status(evidence),
        "missing_evidence": list(evidence.missing_evidence),
        "stale_evidence": list(evidence.stale_evidence),
        "safety_report_path": str(safety_report_path),
        "safety_markdown_report_path": str(markdown_report_path),
        "overall_decision": result.overall_decision.value,
        "next_recommended_safety_state": result.next_recommended_state.value,
        "review_required": status in {"REVIEW_REQUIRED", "BLOCKED", "HALT"},
        "production_equivalent": mode == "production" and not evidence.missing_evidence and not evidence.stale_evidence,
    }


def _status_from_result(*, result: HourlyMonitorResult, evidence: _EvidenceBundle) -> str:
    if result.overall_decision is SafetyDecision.EMERGENCY_STOP:
        return "HALT"
    if result.overall_decision is SafetyDecision.BLOCK:
        return "BLOCKED"
    if evidence.missing_evidence or evidence.stale_evidence or result.overall_decision is SafetyDecision.REVIEW_REQUIRED:
        return "REVIEW_REQUIRED"
    return "PASS"


def _reason_from_result(*, result: HourlyMonitorResult, evidence: _EvidenceBundle) -> str:
    if evidence.missing_evidence:
        return "missing evidence: " + ", ".join(evidence.missing_evidence)
    if evidence.stale_evidence:
        return "stale evidence: " + ", ".join(evidence.stale_evidence)
    if result.review_items:
        return "; ".join(item.reason_code for item in result.review_items[:3])
    return result.overall_decision.value


def _input_sources(evidence: _EvidenceBundle) -> dict[str, str]:
    return {
        "current": evidence.current_source,
        "broker_snapshot": evidence.broker_snapshot_source,
        "market": evidence.market_source,
        "orders": evidence.orders_source,
        "executions": evidence.execution_source,
        "runtime_state": evidence.runtime_state_source,
        "manual_stop": evidence.manual_stop_source,
    }


def _freshness_status(evidence: _EvidenceBundle) -> str:
    if evidence.missing_evidence:
        return "MISSING_EVIDENCE"
    if evidence.stale_evidence:
        return "STALE_EVIDENCE"
    return "PASS"


def _read_json_file(path: Path, missing: list[str], label: str) -> dict[str, Any]:
    if not path.exists():
        missing.append(label)
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        missing.append(label + "_invalid_json")
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, missing: list[str], label: str) -> list[dict[str, Any]]:
    if not path.exists():
        missing.append(label)
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            missing.append(label + "_invalid_json")
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _first_json(directory: Path) -> Path | None:
    if not directory.exists():
        return None
    files = sorted(path for path in directory.glob("*.json") if path.is_file())
    return files[-1] if files else None


def _filter_business_date(rows: list[dict[str, Any]], business_date: str) -> list[dict[str, Any]]:
    filtered = []
    for row in rows:
        row_date = str(row.get("business_date") or row.get("target_session_date") or row.get("created_at") or "")
        if not row_date or row_date.startswith(business_date):
            filtered.append(row)
    return filtered


def _normalize_position(position: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(position)
    code = str(normalized.get("issue_code") or normalized.get("symbol") or "")
    if code:
        normalized["issue_code"] = code
        normalized["symbol"] = code
    if "market_value" not in normalized and normalized.get("quantity") is not None and normalized.get("price") is not None:
        try:
            normalized["market_value"] = str(float(normalized["quantity"]) * float(normalized["price"]))
        except (TypeError, ValueError):
            pass
    return normalized


def _timestamp_from(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(payload.get(key) or "")
        if value:
            return value
    return ""


def _require_business_date(payload: dict[str, Any], timestamp: str, business_date: str, stale: list[str], label: str) -> None:
    if not payload:
        return
    payload_date = str(payload.get("business_date") or payload.get("target_session_date") or "")
    if payload_date and payload_date != business_date:
        stale.append(label)
        return
    if payload_date == business_date:
        return
    if timestamp and len(timestamp) >= 10 and not timestamp.startswith(business_date):
        stale.append(label)


def _set_snapshot_age(payload: dict[str, Any], timestamp: str, business_date: str, mode: str, now: datetime) -> None:
    context = resolve_temporal_context(
        runtime_business_date=business_date,
        runtime_mode=mode,
        broker_environment=mode,
        now=now,
    )
    max_age = int((payload.get("safety_config") or {}).get("max_broker_snapshot_age_seconds") or 900)
    evidence = evaluate_broker_snapshot_freshness(
        context=context,
        snapshot_at=timestamp,
        max_age_seconds=max_age,
        generated_at=str(payload.get("generated_at") or ""),
        now=now,
    )
    payload["freshness_status"] = evidence.status.value
    payload["freshness_reason"] = evidence.reason
    parsed = _parse_datetime(timestamp)
    if parsed is None or evidence.status == FreshnessStatus.REVIEW_REQUIRED:
        payload.setdefault("stale", True)
        return
    age = max(0, int((now - parsed).total_seconds()))
    payload.setdefault("age_seconds", age)
    if evidence.status == FreshnessStatus.STALE:
        payload.setdefault("stale", True)


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return _aware(parsed)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _preferred_review_state(current: SafetyState, extras: tuple[SafetyCheckResult, ...]) -> SafetyState:
    for item in extras:
        if item.state_after in {SafetyState.SYSTEM_EMERGENCY_STOP, SafetyState.EMERGENCY_STOP, SafetyState.BUY_REVIEW_REQUIRED}:
            return item.state_after
    return current


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
