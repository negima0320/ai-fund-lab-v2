import json
import subprocess
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli import run_daily_operation
from ai_fund_lab_v2.runtime_v2.pending.no_order_authority import materialize_empty_pending_no_order_authority
from ai_fund_lab_v2.runtime_v2.submit import pipeline as submit_pipeline
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from scripts.runtime_test import collect_runtime_cli_job_evidence

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import (
    _attach_pending_safety_evidence,
    _demo_settings,
    _read_jsonl,
    _runtime_root,
    _write_asset_state,
    _write_policy,
    _write_runtime_readiness_authorities,
)


def test_phase17_bf_empty_pending_submit_pipeline_returns_no_action_pass(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    pending_payload = _authorized_empty_pending_payload(
        runtime_root,
        business_date="2026-07-08",
        environment="demo",
    )
    _write_json(pending_path, pending_payload)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "PASS"
    assert result.reason == "pending_empty_no_action"
    assert result.submit_action == "NO_ACTION"
    assert result.pending_read_valid is True
    assert result.pending_classification == "EMPTY"
    assert result.pending_active is False
    assert result.pending_plan_present is False
    assert result.pending_item_count == 0
    assert result.no_action_reason == "NO_SIGNAL:phase17_bf_fixture"
    assert result.submitted_count == 0
    assert result.blocked_count == 0
    assert result.review_required is False
    assert result.halt_required is False
    assert result.demo_submit_executed is False
    assert _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl") == []
    assert json.loads(pending_path.read_text(encoding="utf-8")) == pending_payload


def test_phase17_bf_empty_pending_submit_cli_exits_zero_and_records_manifest(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    _write_runtime_readiness_authorities(runtime_root, business_date="2026-07-08")
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        _authorized_empty_pending_payload(
            runtime_root,
            business_date="2026-07-08",
            environment="demo",
        ),
    )

    exit_code = run_daily_operation.main(
        [
            "--mode",
            "demo",
            "--job",
            "submit",
            "--business-date",
            "2026-07-08",
            "--evaluation-time",
            "2026-07-08T09:00:00+09:00",
            "--submit-enabled",
            "true",
            "--notification-mode",
            "payload-only",
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

    manifest_path = next((runtime_root / "runtime_state" / "run_manifest" / "2026-07-08").glob("*.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    submit_stage = next(stage for stage in manifest["stages"] if stage["name"] == "runtime_v2_submit_pipeline")

    assert exit_code == 0
    assert submit_stage["status"] == "PASS"
    assert submit_stage["details"]["submit_action"] == "NO_ACTION"
    assert submit_stage["details"]["reason"] == "pending_empty_no_action"
    assert submit_stage["details"]["submitted_count"] == 0
    assert submit_stage["details"]["blocked_count"] == 0
    assert submit_stage["details"]["review_required"] is False
    assert submit_stage["details"]["halt_required"] is False
    assert manifest["pending_read_valid"] is True
    assert manifest["pending_classification"] == "EMPTY"
    assert manifest["pending_active"] is False
    assert manifest["pending_plan_present"] is False
    assert manifest["pending_item_count"] == 0
    assert manifest["no_action_reason"] == "NO_SIGNAL:phase17_bf_fixture"
    assert manifest["submit_action"] == "NO_ACTION"
    assert manifest["submitted_count"] == 0
    assert manifest["blocked_count"] == 0
    assert manifest["review_required"] is False
    assert manifest["halt_required"] is False
    assert manifest["prohibited_actions"]["demo_submit_executed"] is False


def test_phase17_bf_empty_pending_temporal_metadata_is_not_order_authority(tmp_path):
    result = _run_empty_payload_variant(
        tmp_path,
        {
            "target_session_date": "2026-07-09",
            "intended_submit_date": "2026-07-09",
        },
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submit_action == "BLOCKED"
    assert result.reason == "pending EMPTY no_order_authority missing"
    assert result.submitted_count == 0
    assert result.pending_consumed is False


def test_phase17_bf_empty_pending_missing_safety_authority_is_no_action(tmp_path):
    result = _run_empty_payload_variant(tmp_path, {"safety_context": {}})

    assert result.status == "REVIEW_REQUIRED"
    assert result.submit_action == "BLOCKED"
    assert result.reason == "pending EMPTY no_order_authority missing"
    assert result.submitted_count == 0


def test_phase17_bf_empty_pending_active_contradiction_fails_closed(tmp_path):
    result = _run_empty_payload_variant(tmp_path, {"active_pending": True})

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "authorized no-order order plan hash mismatch"
    assert result.demo_submit_executed is False


def test_phase17_bf_malformed_pending_schema_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", {"state": "APPROVED"})

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "BLOCKED"
    assert result.pending_read_valid is False
    assert result.pending_plan_present is False
    assert "pending current is missing or invalid" in result.reason


def test_phase17_bf_active_classification_without_plan_fails_closed(monkeypatch, tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")

    class ReadResult:
        path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
        exists = True
        valid = True
        classification = "VALID"
        plan = None
        payload = {"active_pending": True, "items": [{"pending_item_id": "x"}]}
        errors = ()
        warnings = ()

    monkeypatch.setattr(submit_pipeline, "read_pending_order_plan_path", lambda **_: ReadResult())

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "BLOCKED"
    assert result.reason == "pending current is missing or invalid: active pending plan missing"
    assert result.pending_classification == "VALID"
    assert result.pending_plan_present is False


def test_phase17_bf_runtime_test_collects_manifest_and_log_on_nonzero_exit(tmp_path):
    runtime_root = tmp_path / ".runtime"
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "run-bf"
    manifest_path = runtime_root / "runtime_state" / "run_manifest" / "2026-07-08" / "runtime-v2-submit-bf.json"
    log_path = runtime_root / "runtime_state" / "logs" / "2026-07-08" / "runtime-v2-submit-bf.log"
    _write_json(manifest_path, {"run_id": "runtime-v2-submit-bf", "job": "submit", "exit_code": 10})
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("exit_code=10\n", encoding="utf-8")
    completed = subprocess.CompletedProcess(
        args=["runtime"],
        returncode=10,
        stdout=json.dumps({"exit_code": 10, "manifest": str(manifest_path)}) + "\n",
        stderr="",
    )

    collect_runtime_cli_job_evidence(
        completed=completed,
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date="2026-07-08",
        job="submit",
    )

    job_dir = run_dir / "daily" / "2026-07-08" / "submit"
    cli_result = json.loads((job_dir / "cli_result.json").read_text(encoding="utf-8"))
    assert (job_dir / "runtime_manifest.json").is_file()
    assert (job_dir / "runtime_log.log").is_file()
    assert cli_result["exit_code"] == 10
    assert cli_result["runtime_manifest_copied"] is True
    assert cli_result["runtime_log_copied"] is True


def _run_empty_payload_variant(tmp_path: Path, updates: dict) -> object:
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    payload = _empty_pending_payload(business_date="2026-07-08", environment="demo")
    payload.update(updates)
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", payload)
    return run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        capital_deployment_policy_path=policy_path,
    )


def _empty_pending_payload(*, business_date: str, environment: str) -> dict:
    return {
        "schema_version": "1",
        "pending_plan_id": f"pending-empty-{business_date}",
        "state": "EMPTY",
        "status": "EMPTY",
        "environment": environment,
        "created_at": business_date,
        "updated_at": business_date,
        "plan_created_date": business_date,
        "intended_submit_date": business_date,
        "target_session_date": business_date,
        "source_order_plan": {
            "order_plan_id": f"order-plan-empty-{business_date}",
            "path": f".runtime/runtime_state/sell_pipeline/{business_date}/order_plan.json",
            "artifact_hash": "sha256:empty-order-plan",
        },
        "approval": None,
        "approved_item_ids": [],
        "items": [],
        "submit_constraints": {"expires_at": "", "allow_post_send_unknown_resubmit": False},
        "consume": {
            "consumed": False,
            "consume_reason": "",
            "consumed_at": "",
            "submitted_order_ids": [],
            "ledger_order_record_ids": [],
        },
        "active_pending": False,
        "no_action_reason": "NO_SIGNAL:phase17_bf_fixture",
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
        "safety_context": {
            "safety_decision": "ALLOW",
            "safety_decision_id": "safety-phase17-bf",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": "phase17_bf_fixture",
            "safety_reason": "phase17_bf no-signal fixture allow",
        },
        "safety_decision_id": "safety-phase17-bf",
        "safety_policy_version": "safety_policy_v1",
    }


def _authorized_empty_pending_payload(runtime_root: Path, *, business_date: str, environment: str) -> dict:
    _write_empty_authority_source_artifacts(runtime_root, business_date=business_date, environment=environment)
    return materialize_empty_pending_no_order_authority(
        _empty_pending_payload(business_date=business_date, environment=environment),
        runtime_root=runtime_root,
        business_date=business_date,
        target_session_date=business_date,
        environment=environment,
        authority_reason="empty_pending_no_executable_order_items",
        sell_order_plan_path=runtime_root / "runtime_state" / "sell_pipeline" / business_date / "order_plan.json",
        sell_approval_path=runtime_root / "runtime_state" / "sell_pipeline" / business_date / "approval_artifact.json",
        sell_reason="NO_SIGNAL:phase17_bf_fixture",
    )


def _write_empty_authority_source_artifacts(runtime_root: Path, *, business_date: str, environment: str) -> None:
    _write_json(
        runtime_root / "runtime_state" / "sell_pipeline" / business_date / "order_plan.json",
        {
            "schema_version": "1",
            "order_plan_id": f"order-plan-empty-{business_date}",
            "environment": environment,
            "business_date": business_date,
            "target_session_date": business_date,
            "status": "NO_ACTION",
            "items": [],
            "reason": "NO_SIGNAL:phase17_bf_fixture",
        },
    )
    _write_json(
        runtime_root / "runtime_state" / "sell_pipeline" / business_date / "approval_artifact.json",
        {
            "status": "NO_SIGNAL",
            "reason": "NO_SIGNAL:phase17_bf_fixture",
        },
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
