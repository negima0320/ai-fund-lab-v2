import json
from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings
from tests.runtime_v2.test_phase15i_submit_guard_buy_sell_policy_manifest import (
    _attach_pending_safety_evidence,
    _approved_pending,
    _item,
    _runtime_root,
    _write_runtime_readiness_authorities,
    _write_current_state,
    _write_policy,
)


def test_phase15l_policy_match_allows_submit_guard_continuation(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1500,
                estimated_amount=150_000,
            ),
        ),
        policy_path=policy_path,
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "PASS"
    assert result.submitted_count == 1
    assert result.submit_policy_consistency["policy_consistency_status"] == "PASS"
    assert result.submit_policy_consistency["pending_policy_hash"] == result.submit_policy_consistency["active_policy_hash"]


def test_phase15l_policy_mismatch_blocks_submit_before_broker(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    morning_policy_path = _write_policy(tmp_path / "morning_policy.json")
    submit_policy_path = _write_policy(tmp_path / "submit_policy.json", max_buy_order_amount=120_000)
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1500,
                estimated_amount=150_000,
            ),
        ),
        policy_path=morning_policy_path,
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_BrokerShouldNotBeCalled(),
        capital_deployment_policy_path=submit_policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.demo_submit_executed is False
    assert result.submitted_count == 0
    assert result.pending_consumed is False
    assert result.submit_policy_consistency["policy_consistency_status"] == "REVIEW_REQUIRED"
    assert result.submit_policy_consistency["policy_mismatch_reason"].startswith("policy_mismatch:")


def test_phase15l_missing_pending_policy_evidence_blocks_submit(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1000,
                estimated_amount=100_000,
            ),
        )
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_BrokerShouldNotBeCalled(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submitted_count == 0
    assert result.pending_consumed is False
    assert result.submit_policy_consistency["policy_mismatch_reason"] == "missing_policy_evidence"


def test_phase15l_missing_approval_policy_evidence_blocks_submit(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1000,
                estimated_amount=100_000,
            ),
        ),
        policy_path=policy_path,
    )
    assert pending.approval is not None
    pending = replace(
        pending,
        approval=replace(
            pending.approval,
            policy_version="",
            policy_source="",
            pending_policy_hash="",
        ),
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_BrokerShouldNotBeCalled(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submitted_count == 0
    assert result.pending_consumed is False
    assert result.submit_policy_consistency["policy_mismatch_reason"] == "missing_approval_policy_evidence"
    assert result.submit_policy_consistency["active_policy_hash"].startswith("sha256:")


def test_phase15l_policy_consistency_manifest_fields_present(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    morning_policy_path = _write_policy(tmp_path / "morning_policy.json")
    submit_policy_path = _write_policy(tmp_path / "submit_policy.json", max_buy_order_amount=120_000)
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1500,
                estimated_amount=150_000,
            ),
        ),
        policy_path=morning_policy_path,
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_BrokerShouldNotBeCalled(),
        capital_deployment_policy_path=submit_policy_path,
    )

    evidence = result.to_stage_details()["submit_policy_consistency"]
    assert evidence["policy_consistency_status"] == "REVIEW_REQUIRED"
    assert evidence["pending_policy_hash"].startswith("sha256:")
    assert evidence["approval_pending_policy_hash"] == evidence["pending_policy_hash"]
    assert evidence["active_policy_hash"].startswith("sha256:")
    assert evidence["policy_mismatch_reason"]


def test_phase15l_cli_manifest_contains_policy_consistency_evidence(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    morning_policy_path = _write_policy(tmp_path / "morning_policy.json")
    submit_policy_path = _write_policy(tmp_path / "submit_policy.json", max_buy_order_amount=120_000)
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1500,
                estimated_amount=150_000,
            ),
        ),
        policy_path=morning_policy_path,
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)
    _attach_pending_safety_evidence(runtime_root, safety_decision_id="safety-phase15i-fixture")
    _write_runtime_readiness_authorities(runtime_root, business_date="2026-07-09")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "submit",
            "--business-date",
            "2026-07-09",
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
            str(submit_policy_path),
        ]
    )

    manifest = _latest_manifest(runtime_root, "2026-07-09")
    submit_stage = next(stage for stage in manifest["stages"] if stage["name"] == "runtime_v2_submit_pipeline")
    assert exit_code == 20
    assert manifest["final_state"] == "REVIEW_REQUIRED"
    assert manifest["prohibited_actions"]["demo_submit_executed"] is False
    assert manifest["submit_policy_consistency"]["policy_consistency_status"] == "REVIEW_REQUIRED"
    assert manifest["submit_policy_consistency"]["active_policy_hash"].startswith("sha256:")
    assert submit_stage["details"]["submitted_count"] == 0
    assert submit_stage["details"]["pending_consumed"] is False
    assert submit_stage["details"]["submit_policy_consistency"]["policy_mismatch_reason"].startswith("policy_mismatch:")


class _BrokerShouldNotBeCalled:
    def preflight(self, command):
        raise AssertionError("broker preflight must not be called on policy mismatch")

    def submit(self, command):
        raise AssertionError("broker submit must not be called on policy mismatch")


def _latest_manifest(runtime_root, business_date: str):
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / business_date).glob("*.json"))
    return json.loads(manifests[-1].read_text(encoding="utf-8"))
