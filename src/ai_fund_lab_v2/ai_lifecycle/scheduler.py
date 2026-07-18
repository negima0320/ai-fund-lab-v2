from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class LifecycleSchedulerInput:
    component: str
    decision_date: str
    label_safe_cutoff_advanced_business_days: int
    minimum_new_candidate_rows: int
    source_freshness_status: str
    accepted_registry_lock_active: bool = False
    overlapping_run_active: bool = False
    model_age_warning: bool = False


@dataclass(frozen=True)
class LifecycleSchedulerDecision:
    status: str
    reason: str
    lifecycle_trigger_required: bool
    promotion_request_allowed: bool
    registry_accepted_event_allowed: bool
    runtime_hot_swap_allowed: bool
    buy_restart_allowed: bool
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LifecycleRetryPolicy:
    max_attempts: int = 2
    retry_delay_seconds: int = 0
    timeout_seconds: int = 300
    retryable_errors: tuple[str, ...] = ("TRANSIENT_ERROR", "LOCK_TIMEOUT")
    non_retryable_errors: tuple[str, ...] = ("VALIDATION_FAILED", "AUTHORITY_REJECTED")


@dataclass(frozen=True)
class LifecycleSchedulerRunResult:
    run_id: str
    component: str
    decision: str
    final_state: str
    reason: str
    attempt: int
    lock_status: str
    timeout_status: str
    idempotency_key: str
    status_artifact_path: str
    operator_report_path: str
    alert_payload_path: str
    registry_accepted_event_generated: bool = False
    runtime_switch_performed: bool = False
    buy_restarted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_weekly_lifecycle_eligibility(input_: LifecycleSchedulerInput) -> LifecycleSchedulerDecision:
    blockers: list[str] = []
    if input_.accepted_registry_lock_active:
        blockers.append("accepted_registry_lock_active")
    if input_.overlapping_run_active:
        blockers.append("overlapping_lifecycle_run")
    if input_.source_freshness_status not in {"PASS", "WARN"}:
        blockers.append("source_freshness_not_ready")
    enough_cutoff = input_.label_safe_cutoff_advanced_business_days >= 5 or input_.model_age_warning
    enough_rows = input_.minimum_new_candidate_rows >= 250
    if not enough_cutoff:
        blockers.append("label_safe_cutoff_not_advanced")
    if not enough_rows:
        blockers.append("minimum_new_candidate_rows_not_met")
    if blockers:
        status = "NO_PROMOTION"
        trigger = False
        reason = ",".join(blockers)
    else:
        status = "ELIGIBLE"
        trigger = True
        reason = "weekly lifecycle eligibility passed"
    return LifecycleSchedulerDecision(
        status=status,
        reason=reason,
        lifecycle_trigger_required=trigger,
        promotion_request_allowed=trigger,
        registry_accepted_event_allowed=False,
        runtime_hot_swap_allowed=False,
        buy_restart_allowed=False,
        evidence=asdict(input_),
    )


class WeeklyLifecycleSchedulerOperator:
    def __init__(self, *, state_root: Path | str, retry_policy: LifecycleRetryPolicy | None = None, now: Callable[[], datetime] | None = None) -> None:
        self.state_root = Path(state_root)
        self.retry_policy = retry_policy or LifecycleRetryPolicy()
        self._now = now or (lambda: datetime.now(timezone.utc))

    def run(
        self,
        input_: LifecycleSchedulerInput,
        *,
        idempotency_key: str,
        action: Callable[[], str] | None = None,
    ) -> LifecycleSchedulerRunResult:
        run_id = f"weekly-lifecycle-{input_.component}-{idempotency_key}"
        run_dir = self.state_root / "runs" / input_.component / idempotency_key
        status_path = run_dir / "status.json"
        report_path = run_dir / "operator_report.json"
        alert_path = run_dir / "alert_payload.json"
        if status_path.exists():
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            return LifecycleSchedulerRunResult(**payload["result"])
        decision = evaluate_weekly_lifecycle_eligibility(input_)
        lock_status = self._acquire_lock(input_.component, idempotency_key)
        if lock_status != "ACQUIRED":
            result = self._result(run_id, input_, "BLOCKED", lock_status.lower(), 0, lock_status, "NOT_STARTED", idempotency_key, status_path, report_path, alert_path)
            self._write_artifacts(result, decision)
            return result
        final_state = "FAILED"
        reason = ""
        attempt = 0
        timeout_status = "NOT_TIMED_OUT"
        try:
            if not decision.lifecycle_trigger_required:
                final_state = "ELIGIBLE_NO_ACTION" if decision.status == "ELIGIBLE" else "NOT_ELIGIBLE"
                reason = decision.reason
            else:
                for attempt in range(1, self.retry_policy.max_attempts + 1):
                    started = self._now()
                    try:
                        outcome = action() if action else "PROMOTION_REVIEW_REQUIRED"
                        if self._elapsed_seconds(started) > self.retry_policy.timeout_seconds:
                            timeout_status = "TIMED_OUT"
                            raise TimeoutError("timeout")
                        final_state = self._normalize_action_outcome(outcome)
                        reason = outcome
                        break
                    except TimeoutError:
                        final_state = "FAILED"
                        reason = "TIMEOUT"
                        timeout_status = "TIMED_OUT"
                        if attempt >= self.retry_policy.max_attempts:
                            break
                    except Exception as exc:
                        code = str(exc) or exc.__class__.__name__
                        reason = code
                        if code in self.retry_policy.non_retryable_errors or attempt >= self.retry_policy.max_attempts:
                            final_state = "FAILED"
                            break
                if final_state == "FAILED" and not reason:
                    reason = "scheduler_action_failed"
            result = self._result(run_id, input_, final_state, reason, attempt, lock_status, timeout_status, idempotency_key, status_path, report_path, alert_path)
            self._write_artifacts(result, decision)
            return result
        finally:
            self._release_lock(input_.component, idempotency_key)

    def _normalize_action_outcome(self, outcome: str) -> str:
        allowed = {"ELIGIBLE_NO_ACTION", "DATASET_REBUILD_REQUIRED", "TRAINING_REQUIRED", "PROMOTION_REVIEW_REQUIRED"}
        return outcome if outcome in allowed else "PROMOTION_REVIEW_REQUIRED"

    def _lock_path(self, component: str) -> Path:
        return self.state_root / "locks" / f"{component}.json"

    def _acquire_lock(self, component: str, owner: str) -> str:
        path = self._lock_path(component)
        path.parent.mkdir(parents=True, exist_ok=True)
        now = self._now()
        expires = now + timedelta(seconds=self.retry_policy.timeout_seconds)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            expires_at = datetime.fromisoformat(payload["expires_at"])
            if expires_at > now and payload.get("owner") != owner:
                return "CONTENDED"
            if expires_at <= now:
                stale_path = path.with_suffix(".stale.json")
                os.replace(path, stale_path)
        payload = {"owner": owner, "acquired_at": now.isoformat(), "expires_at": expires.isoformat(), "component": component}
        _atomic_write_json(path, payload)
        return "ACQUIRED"

    def _release_lock(self, component: str, owner: str) -> None:
        path = self._lock_path(component)
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("owner") == owner:
            path.unlink()

    def _elapsed_seconds(self, started: datetime) -> float:
        return (self._now() - started).total_seconds()

    def _result(self, run_id: str, input_: LifecycleSchedulerInput, final_state: str, reason: str, attempt: int, lock_status: str, timeout_status: str, idempotency_key: str, status_path: Path, report_path: Path, alert_path: Path) -> LifecycleSchedulerRunResult:
        return LifecycleSchedulerRunResult(run_id, input_.component, final_state, final_state, reason, attempt, lock_status, timeout_status, idempotency_key, str(status_path), str(report_path), str(alert_path))

    def _write_artifacts(self, result: LifecycleSchedulerRunResult, decision: LifecycleSchedulerDecision) -> None:
        status = {"schema_version": "ai_lifecycle_weekly_scheduler_status.v2", "created_at": self._now().isoformat(), "result": result.to_dict(), "eligibility": decision.to_dict()}
        report = {"schema_version": "ai_lifecycle_weekly_scheduler_operator_report.v1", **status}
        alert = {
            "schema_version": "ai_lifecycle_weekly_scheduler_alert.v1",
            "component": result.component,
            "run_id": result.run_id,
            "decision": result.decision,
            "severity": "INFO" if result.final_state in {"ELIGIBLE_NO_ACTION", "PROMOTION_REVIEW_REQUIRED"} else "WARNING",
            "reason": result.reason,
            "attempt": result.attempt,
            "lock_status": result.lock_status,
            "timeout_status": result.timeout_status,
            "required_operator_action": "review_promotion_request" if result.final_state == "PROMOTION_REVIEW_REQUIRED" else "none",
            "evidence_refs": [result.status_artifact_path, result.operator_report_path],
        }
        _atomic_write_json(Path(result.status_artifact_path), status)
        _atomic_write_json(Path(result.operator_report_path), report)
        _atomic_write_json(Path(result.alert_payload_path), alert)


def write_scheduler_status(path: Path, decision: LifecycleSchedulerDecision) -> None:
    payload = {
        "schema_version": "ai_lifecycle_weekly_scheduler_status.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        **decision.to_dict(),
    }
    _atomic_write_json(path, payload)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True, indent=2) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
