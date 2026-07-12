from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.human_review import human_review_artifact_path
from tests.runtime_v2.test_phase15aq_runtime_data_readiness_gate import (
    BUSINESS_DATE,
    FEATURE_DATE,
    _load_json,
    _latest_manifest,
    _runtime_root,
    _write_broker_snapshot,
    _write_json,
    _write_policy,
)


NOW = datetime(2026, 7, 8, 1, 0, tzinfo=timezone.utc)


def test_phase15bg_high_risk_review_keeps_safety_review_required(tmp_path):
    runtime_root = _review_only_runtime(tmp_path)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning_sell_hold_review_only",
        feature_root=runtime_root / "operations" / "feature_artifacts",
        feature_date=FEATURE_DATE,
        now=NOW,
    )

    assert result.payload["safety_status"] == "REVIEW_REQUIRED"
    assert result.payload["effective_safety_status"] == "READY_FOR_REVIEW_ONLY"
    assert result.status == "READY"


def test_phase15bg_no_human_review_is_not_review_only_ready(tmp_path):
    runtime_root = _review_only_runtime(tmp_path, write_human_review=False)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning_sell_hold_review_only",
        feature_root=runtime_root / "operations" / "feature_artifacts",
        feature_date=FEATURE_DATE,
        now=NOW,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "human_review_artifact_missing" in result.payload["review_reasons"]
    assert result.payload["candidate_status"] == "NOT_REQUIRED"
    assert result.payload["opportunity_status"] == "NOT_REQUIRED"


def test_phase15bg_valid_human_review_allows_sell_hold_review_only(tmp_path):
    runtime_root = _review_only_runtime(tmp_path)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning_sell_hold_review_only",
        feature_root=runtime_root / "operations" / "feature_artifacts",
        feature_date=FEATURE_DATE,
        now=NOW,
    )

    assert result.status == "READY"
    assert result.payload["review_only_morning_readiness"] == "READY"
    assert result.payload["full_morning_readiness"] == "NOT_APPLICABLE"
    assert result.payload["human_review_status"] == "READY"
    permissions = result.payload["components"]["human_review"]["safety_action_permissions"]
    assert permissions["buy_inference"] == "BLOCKED"
    assert permissions["buy_planning"] == "BLOCKED"
    assert permissions["sell_hold_inference"] == "ALLOWED_FOR_REVIEW"
    assert permissions["sell_planning"] == "ALLOWED_FOR_REVIEW"
    assert permissions["sell_submit"] == "BLOCKED"
    assert permissions["broker_write"] == "BLOCKED"


def test_phase15bg_expired_human_review_requires_review(tmp_path):
    runtime_root = _review_only_runtime(tmp_path, expires_at="2026-07-07T23:59:59+00:00")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning_sell_hold_review_only",
        feature_root=runtime_root / "operations" / "feature_artifacts",
        feature_date=FEATURE_DATE,
        now=NOW,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "human_review_artifact_expired" in result.payload["review_reasons"]


def test_phase15bg_wrong_issue_date_or_event_is_unusable(tmp_path):
    runtime_root = _review_only_runtime(tmp_path, event_id="wrong-event")

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="morning_sell_hold_review_only",
        feature_root=runtime_root / "operations" / "feature_artifacts",
        feature_date=FEATURE_DATE,
        now=NOW,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "human_review_artifact_contract_mismatch" in result.payload["review_reasons"]
    assert "event_id" in result.payload["components"]["human_review"]["mismatched_fields"]


def test_phase15bg_cli_data_readiness_review_only_path(tmp_path):
    runtime_root = _review_only_runtime(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment.json")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "data_readiness",
            "--readiness-scope",
            "morning_sell_hold_review_only",
            "--business-date",
            BUSINESS_DATE,
            "--feature-date",
            FEATURE_DATE,
            "--feature-root",
            str(runtime_root / "operations" / "feature_artifacts"),
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
        ]
    )

    manifest = _latest_manifest(runtime_root, BUSINESS_DATE)
    artifact = _load_json(runtime_root / "runtime_state" / "data_readiness" / BUSINESS_DATE / "data_readiness.json")
    assert exit_code == 0
    assert manifest["data_readiness_status"] == "READY"
    assert artifact["readiness_scope"] == "morning_sell_hold_review_only"
    assert artifact["review_only_morning_readiness"] == "READY"


def _review_only_runtime(
    tmp_path: Path,
    *,
    write_human_review: bool = True,
    expires_at: str = "2026-07-12T00:00:00+00:00",
    event_id: str = "safety-event-4591",
) -> Path:
    runtime_root = _runtime_root(tmp_path, business_date=BUSINESS_DATE, current_as_of=BUSINESS_DATE)
    _write_broker_snapshot(runtime_root)
    _write_feature_readiness(runtime_root)
    _write_high_risk_safety_decision(runtime_root)
    _write_safety_report(tmp_path, event_id="safety-event-4591")
    if write_human_review:
        _write_human_review(runtime_root, event_id=event_id, expires_at=expires_at)
    return runtime_root


def _write_feature_readiness(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "operations" / "feature_consumer_readiness" / f"{FEATURE_DATE}.json",
        {
            "schema_version": "runtime_v2_feature_consumer_readiness_v1",
            "feature_date": FEATURE_DATE,
            "consumer_ready": True,
            "candidate_schema_status": "READY",
            "opportunity_schema_status": "READY",
            "pm_schema_status": "READY",
        },
    )


def _write_high_risk_safety_decision(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase15bg",
            "safety_policy_version": "phase11_safety_report_v2",
            "safety_source": "fixture",
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "REVIEW_REQUIRED",
            "reason": "HIGH_RISK_REVIEW",
            "review_required": True,
            "block_buy": True,
            "block_sell": False,
            "block_submit": True,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": BUSINESS_DATE + "T00:00:00+00:00",
            "expires_at": "2026-07-09T00:00:00+00:00",
            "action_permissions": {
                "buy_inference": "BLOCKED",
                "buy_planning": "BLOCKED",
                "sell_hold_inference": "ALLOWED_FOR_REVIEW",
                "sell_planning": "ALLOWED_FOR_REVIEW",
                "buy_submit": "BLOCKED",
                "sell_submit": "BLOCKED",
                "auto_sell": "BLOCKED",
                "broker_write": "BLOCKED",
                "human_review": "ALLOWED",
            },
        },
    )


def _write_safety_report(tmp_path: Path, *, event_id: str) -> None:
    _write_json(
        tmp_path / "reports" / "safety" / "phase11" / f"{BUSINESS_DATE}_safety_report.json",
        {
            "schema_version": "phase11_safety_report_v2",
            "business_date": BUSINESS_DATE,
            "environment": "demo",
            "generated_at": BUSINESS_DATE + "T00:00:00+00:00",
            "expires_at": "2026-07-09T00:00:00+00:00",
            "overall_decision": "REVIEW_REQUIRED",
            "review_required_items": [
                {
                    "affected_issue_code": "4591",
                    "event_id": event_id,
                    "review_id": "human-review-4591",
                    "guard": "INDIVIDUAL_CRASH",
                    "reason_code": "HIGH_RISK_REVIEW",
                }
            ],
        },
    )


def _write_human_review(runtime_root: Path, *, event_id: str, expires_at: str) -> None:
    path = human_review_artifact_path(runtime_root=runtime_root, business_date=BUSINESS_DATE, issue_code="4591")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "runtime_v2_human_safety_review_v1",
                "business_date": BUSINESS_DATE,
                "issue_code": "4591",
                "event_id": event_id,
                "review_id": "human-review-4591",
                "guard": "INDIVIDUAL_CRASH",
                "safety_reason": "HIGH_RISK_REVIEW",
                "review_status": "REVIEWED",
                "review_decision": "SELL_HOLD_REVIEW_REQUIRED",
                "reviewed_at": BUSINESS_DATE + "T01:00:00+00:00",
                "expires_at": expires_at,
                "automatic_trade_authorized": False,
                "broker_write_authorized": False,
                "action_scope": {
                    "buy_inference": "BLOCKED",
                    "buy_planning": "BLOCKED",
                    "sell_hold_inference": "ALLOWED_FOR_REVIEW",
                    "sell_planning": "ALLOWED_FOR_REVIEW",
                    "buy_submit": "BLOCKED",
                    "sell_submit": "BLOCKED",
                    "auto_sell": "BLOCKED",
                    "broker_write": "BLOCKED",
                    "human_review": "ALLOWED",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
