"""Runtime v2 Human Safety Review artifact contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HUMAN_REVIEW_SCHEMA_VERSION = "runtime_v2_human_safety_review_v1"
HIGH_RISK_REVIEW_DECISION = "SELL_HOLD_REVIEW_REQUIRED"
HIGH_RISK_REVIEW_ISSUE_CODE = "4591"
HIGH_RISK_REVIEW_GUARD = "INDIVIDUAL_CRASH"
HIGH_RISK_REVIEW_REASON = "HIGH_RISK_REVIEW"

EXPECTED_ACTION_SCOPE = {
    "buy_inference": "BLOCKED",
    "buy_planning": "BLOCKED",
    "sell_hold_inference": "ALLOWED_FOR_REVIEW",
    "sell_planning": "ALLOWED_FOR_REVIEW",
    "buy_submit": "BLOCKED",
    "sell_submit": "BLOCKED",
    "auto_sell": "BLOCKED",
    "broker_write": "BLOCKED",
    "human_review": "ALLOWED",
}


@dataclass(frozen=True)
class HumanReviewValidation:
    status: str
    reason: str
    artifact_path: str
    payload: dict[str, Any]
    missing_evidence: tuple[str, ...] = ()
    stale_artifacts: tuple[str, ...] = ()
    mismatched_fields: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.status == "READY"


def human_review_artifact_path(
    *,
    runtime_root: Path | str,
    business_date: str,
    issue_code: str = HIGH_RISK_REVIEW_ISSUE_CODE,
) -> Path:
    return (
        Path(runtime_root)
        / "runtime_state"
        / "human_review"
        / business_date
        / f"{issue_code}_high_risk_review.json"
    )


def validate_human_review_artifact(
    *,
    runtime_root: Path | str,
    business_date: str,
    issue_code: str = HIGH_RISK_REVIEW_ISSUE_CODE,
    safety_report_path: Path | str | None = None,
    now: datetime | None = None,
) -> HumanReviewValidation:
    path = human_review_artifact_path(
        runtime_root=runtime_root,
        business_date=business_date,
        issue_code=issue_code,
    )
    if not path.is_file():
        return HumanReviewValidation(
            status="REVIEW_REQUIRED",
            reason="human_review_artifact_missing",
            artifact_path=str(path),
            payload={},
            missing_evidence=("human_review_artifact",),
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return HumanReviewValidation(
            status="REVIEW_REQUIRED",
            reason=f"human_review_artifact_invalid_json:{exc.msg}",
            artifact_path=str(path),
            payload={},
            missing_evidence=("human_review_artifact",),
        )
    if not isinstance(payload, dict):
        return HumanReviewValidation(
            status="REVIEW_REQUIRED",
            reason="human_review_artifact_invalid_payload",
            artifact_path=str(path),
            payload={},
            missing_evidence=("human_review_artifact",),
        )

    mismatched: list[str] = []
    for key, expected in (
        ("schema_version", HUMAN_REVIEW_SCHEMA_VERSION),
        ("business_date", business_date),
        ("issue_code", issue_code),
        ("guard", HIGH_RISK_REVIEW_GUARD),
        ("safety_reason", HIGH_RISK_REVIEW_REASON),
        ("review_decision", HIGH_RISK_REVIEW_DECISION),
        ("review_status", "REVIEWED"),
    ):
        if str(payload.get(key) or "") != expected:
            mismatched.append(key)

    if bool(payload.get("automatic_trade_authorized")):
        mismatched.append("automatic_trade_authorized")
    if bool(payload.get("broker_write_authorized")):
        mismatched.append("broker_write_authorized")

    action_scope = {str(key): str(value).upper() for key, value in (payload.get("action_scope") or {}).items()}
    for key, expected in EXPECTED_ACTION_SCOPE.items():
        if action_scope.get(key) != expected:
            mismatched.append(f"action_scope.{key}")

    expected_event = _expected_safety_review_event(
        runtime_root=Path(runtime_root),
        business_date=business_date,
        issue_code=issue_code,
        safety_report_path=safety_report_path,
    )
    if expected_event:
        for key in ("event_id", "review_id"):
            expected = str(expected_event.get(key) or "")
            if expected and str(payload.get(key) or "") != expected:
                mismatched.append(key)
    else:
        mismatched.append("safety_review_event")

    expires_at = _parse_datetime(str(payload.get("expires_at") or ""))
    if expires_at is None:
        mismatched.append("expires_at")
    else:
        now_dt = now or datetime.now(timezone.utc)
        if expires_at <= _ensure_utc(now_dt):
            return HumanReviewValidation(
                status="REVIEW_REQUIRED",
                reason="human_review_artifact_expired",
                artifact_path=str(path),
                payload=payload,
                stale_artifacts=("human_review_artifact",),
            )

    if mismatched:
        return HumanReviewValidation(
            status="REVIEW_REQUIRED",
            reason="human_review_artifact_contract_mismatch",
            artifact_path=str(path),
            payload=payload,
            mismatched_fields=tuple(sorted(set(mismatched))),
        )
    return HumanReviewValidation(
        status="READY",
        reason="human_review_artifact_ready",
        artifact_path=str(path),
        payload=payload,
    )


def discover_valid_human_review_refs(
    *,
    runtime_root: Path | str,
    business_date: str,
    safety_report_payload: dict[str, Any],
    safety_report_path: Path | str | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in safety_report_payload.get("review_required_items") or ():
        if not isinstance(item, dict):
            continue
        issue_code = str(item.get("affected_issue_code") or item.get("issue_code") or "")
        reason = str(item.get("reason_code") or "").upper()
        if issue_code != HIGH_RISK_REVIEW_ISSUE_CODE or reason != HIGH_RISK_REVIEW_REASON:
            continue
        validation = validate_human_review_artifact(
            runtime_root=runtime_root,
            business_date=business_date,
            issue_code=issue_code,
            safety_report_path=safety_report_path,
            now=now,
        )
        if validation.ready:
            refs.append(
                {
                    "issue_code": issue_code,
                    "event_id": validation.payload.get("event_id") or "",
                    "review_id": validation.payload.get("review_id") or "",
                    "review_decision": validation.payload.get("review_decision") or "",
                    "artifact_path": validation.artifact_path,
                    "validation_status": validation.status,
                }
            )
    return refs


def _expected_safety_review_event(
    *,
    runtime_root: Path,
    business_date: str,
    issue_code: str,
    safety_report_path: Path | str | None,
) -> dict[str, Any]:
    path = Path(safety_report_path) if safety_report_path else _default_safety_report_path(runtime_root, business_date)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    for item in payload.get("review_required_items") or ():
        if not isinstance(item, dict):
            continue
        item_issue = str(item.get("affected_issue_code") or item.get("issue_code") or "")
        item_reason = str(item.get("reason_code") or "").upper()
        item_guard = str(item.get("guard") or "").upper()
        if (
            item_issue == issue_code
            and item_reason == HIGH_RISK_REVIEW_REASON
            and item_guard == HIGH_RISK_REVIEW_GUARD
        ):
            return item
    return {}


def _default_safety_report_path(runtime_root: Path, business_date: str) -> Path:
    base = runtime_root.parent if runtime_root.name == ".runtime" else Path(".")
    return base / "reports" / "safety" / "phase11" / f"{business_date}_safety_report.json"


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _ensure_utc(parsed)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
